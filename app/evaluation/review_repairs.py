"""封存后限定纠错：保留原始账本，按固定维度选择来源，未知仍阻塞。"""
from copy import deepcopy
import hashlib
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.api.errors import APIError
from . import development_policy as dp
from .reviews import DIMENSIONS, Score, Scores, ReviewInput
from .review_protocol import review_dump
from .validate_dataset import fingerprint
from app.answering.image_selection import has_review_images

Dimension = Literal['factuality', 'citation_support', 'actionability', 'image_relevance']


def audit_code_identity():
    """审核源码另记身份；不改写原答案生成配置，也不加载模型权重。"""
    return fingerprint({p.relative_to(dp.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((dp.ROOT/'app').rglob('*.py'))})


class RepairTarget(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    question_id: str = Field(min_length=1, max_length=128)
    subject_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    replace_dimensions: list[Dimension] = Field(default_factory=list, max_length=4)
    correct_actionability_na: bool = False
    actionability_applicable: bool | None = None
    rationale: str = Field(min_length=1, max_length=4000, pattern=r'\S')

    @model_validator(mode='after')
    def bounded(self):
        if len(set(self.replace_dimensions)) != len(self.replace_dimensions):
            raise ValueError('替换维度不能重复')
        if not self.replace_dimensions and not self.correct_actionability_na:
            raise ValueError('须指定规则纠错或实际补证维度')
        if self.correct_actionability_na and ('actionability' in self.replace_dimensions or self.actionability_applicable is not False):
            raise ValueError('规则纠错仅允许明确的不适用，不得代填数值')
        if 'actionability' in self.replace_dimensions and self.actionability_applicable is None:
            raise ValueError('步骤补证须先按题意固定适用性')
        if not self.correct_actionability_na and 'actionability' not in self.replace_dimensions and self.actionability_applicable is not None:
            raise ValueError('不得修改范围外适用性')
        return self


class RepairInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    client_request_id: str = Field(min_length=1, max_length=128)
    original_seal_ids: list[str] = Field(min_length=2, max_length=2)
    artifact: dp.Artifact
    targets: list[RepairTarget] = Field(min_length=1, max_length=1000)


class RepairJudgment(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    question_id: str = Field(min_length=1, max_length=128)
    subject_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    scores: dict[Dimension, Score] = Field(min_length=1, max_length=4)
    dimension_evidence: dict[Dimension, str] = Field(min_length=1, max_length=4)
    source_checked: bool
    critical_errors: list[Literal['unauthorized', 'wrong_model', 'wrong_object', 'fabricated_live_state', 'unsafe_procedure']] = Field(max_length=5)

    @field_validator('scores', mode='before')
    @classmethod
    def strict_scores(cls, values):
        if isinstance(values, dict):
            for value in values.values(): Scores.explicit_score(value)
        return values

    @model_validator(mode='after')
    def evidence(self):
        if set(self.scores) != set(self.dimension_evidence) or any(not s.strip() or len(s)>4000 for s in self.dimension_evidence.values()):
            raise ValueError('补证须逐维提供依据或未知原因')
        if self.scores.get('factuality') == 'not_applicable':
            raise ValueError('事实不可标不适用')
        return self


class RepairSealInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    judgments: list[RepairJudgment] = Field(min_length=1, max_length=1000)


class RepairAttestInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    seal_ids: list[str] = Field(default_factory=list, max_length=2)
    artifact: dp.Artifact


class ReviewRepairs:
    def __init__(self, repo):
        self.repo, self.db = repo, repo.db
        self.policy = dp.DevelopmentPolicy(repo)

    def active(self, eid):
        return self.db.evaluation_review_repairs.find_one({'_id':fingerprint(['review-repair-v1', eid])})

    def _scope(self, user, eid, *, controller=False):
        if controller:
            if user.role != 'admin': raise APIError(403, 'forbidden', '限定纠错须由授权总控登记／核验。')
            exp = self.db.evaluation_experiments.find_one({'experiment_id':eid, 'kb_id':{'$in':list(user.kb_ids)}})
            if not exp: dp.reject('实验不在总控授权范围')
            user = SimpleNamespace(user_id=exp['owner_id'], kb_ids=user.kb_ids)
        return self.policy.scope(user, eid)

    def _originals(self, scope, seal_ids):
        """先验证原对及保存评分；不能通过修复把原篡改合法化。"""
        eid = scope['experiment_id']
        seals = [self.policy.checked(self.db.evaluation_review_seals.find_one({'_id':s})) for s in seal_ids]
        if len(set(seal_ids)) != 2 or {s['round'] for s in seals} != {1, 2} or any(s['scope'] != scope for s in seals):
            dp.reject('原封存必须是当前完整双轮')
        pairs = []
        originals = []
        for seal in seals:
            execution = self.policy.checked(self.db.evaluation_review_executions.find_one({'_id':seal['execution_id']}))
            if (execution.get('repair_case_id') or execution['scope'] != scope or execution['round'] != seal['round'] or
                execution['reviewer_id'] != seal['reviewer_id'] or execution['sha256'] != seal['execution_sha256']):
                dp.reject('原执行身份变化')
            pairs.append((seal, execution))
            rows = list(self.db.evaluation_reviews.find({'experiment_id':eid, 'review_execution_id':execution['id']}))
            if len(rows) != len(scope['subjects']) or {r['question_id'] for r in rows} != set(scope['subjects']):
                dp.reject('原双轮保存评分不完整')
            payloads = []
            for row in rows:
                payload = review_dump(ReviewInput.model_validate({k:row[k] for k in ReviewInput.model_fields if k in row}))
                if (row['reviewer_id'] != seal['reviewer_id'] or row['round'] != seal['round'] or
                    row['subject_sha256'] != scope['subjects'][row['question_id']]): dp.reject('原评分身份变化')
                payloads.append(payload)
                originals.append({k:v for k,v in row.items() if k != '_id'})
            if sorted(payloads, key=lambda r:r['question_id']) != seal['reviews']: dp.reject('原评分与封存不一致')
        self._order(pairs)
        if self.policy.rows('evaluation_policy_resolutions', eid) or self.db.evaluation_review_followups.find_one({'experiment_id':eid}):
            dp.reject('已有追加未知／跟进，须另行核定来源，不能静默叠加')
        return pairs, sorted(originals, key=lambda r:r['review_id'])

    @staticmethod
    def _order(pairs):
        if len(pairs) != 2: dp.reject('须有固定两轮')
        pairs = sorted(pairs, key=lambda p:p[0]['round'])
        if (pairs[0][1]['execution_id'] == pairs[1][1]['execution_id'] or
            not pairs[0][1]['created_at'] <= pairs[0][0]['created_at'] <= pairs[1][1]['created_at'] <= pairs[1][0]['created_at']):
            dp.reject('限定审核须为先后封存的独立执行')

    def register(self, user, eid, values):
        data = RepairInput.model_validate(values).model_dump()
        _, scope = self._scope(user, eid, controller=True)
        pairs, originals = self._originals(scope, data['original_seal_ids'])
        if user.user_id in {s['reviewer_id'] for s, _ in pairs}: dp.reject('原审核者不能自签修复case')
        targets = data['targets']
        if len({t['question_id'] for t in targets}) != len(targets): dp.reject('修复题目重复')
        for target in targets:
            if scope['subjects'].get(target['question_id']) != target['subject_sha256']: dp.reject('修复须绑定当前题级结果')
        dp.verify_artifact(data['artifact'])
        key = fingerprint(['review-repair-v1', eid])
        if not self.active(eid) and self.db.evaluation_calibrations.find_one({'experiment_id':eid}):
            dp.reject('已校准来源不能静默追加修复')
        data['targets'] = sorted(targets, key=lambda t:t['question_id'])
        return self.policy.store('evaluation_review_repairs', key, data | dict(scope=scope, controller_id=user.user_id,
            original_seal_hashes=sorted(s['sha256'] for s, _ in pairs), original_reviews_sha256=fingerprint(originals),
            review_code_sha256=audit_code_identity()))

    def case(self, user, eid, case_id, *, controller=False):
        _, scope = self._scope(user, eid, controller=controller)
        case = self.policy.checked(self.active(eid))
        if case['id'] != case_id or case['scope'] != scope: dp.reject('修复case不属于当前完整范围')
        pairs, originals = self._originals(scope, case['original_seal_ids'])
        if (case['original_seal_hashes'] != sorted(s['sha256'] for s, _ in pairs) or
            case['original_reviews_sha256'] != fingerprint(originals)): dp.reject('原来源已变化')
        dp.verify_artifact(case['artifact'])
        return case, pairs, originals

    def begin(self, user, eid, case_id, values):
        data = dp.BeginInput.model_validate(values).model_dump()
        case, _, _ = self.case(user, eid, case_id)
        if case['review_code_sha256'] != audit_code_identity(): dp.reject('补证执行前审核源码已漂移，保留现场')
        if not any(t['replace_dimensions'] for t in case['targets']): dp.reject('仅规则纠错不需要新审核')
        if user.user_id == case['controller_id']: dp.reject('总控裁定主体不能冒充独立补证者')
        key = fingerprint(['repair-execution-v1', case_id, data['round']])
        prior = self.db.evaluation_review_executions.find_one({'_id':key})
        if not prior:
            if data['round'] == 2 and not self.db.evaluation_review_repair_seals.find_one({'_id':fingerprint(['repair-execution-v1',case_id,1])}):
                dp.reject('第二轮补证须在第一轮封存后开始')
            from .reviews import ReviewService
            exp, subjects = ReviewService(self.repo)._subjects(user, eid)
            generated = {s[1].get('result',{}).get('run_id') for s in subjects.values()}
            if (self.db.evaluation_review_executions.find_one({'execution_id':data['execution_id'], '_id':{'$ne':key}}) or
                data['execution_id'] in generated | {eid, exp.get('quality_execution_key'), exp.get('regression_execution_key')}):
                dp.reject('补证执行不能复用原审核或生成身份')
        return self.policy.store('evaluation_review_executions', key, data | dict(scope=case['scope'], repair_case_id=case_id,
            case_sha256=case['sha256'], reviewer_id=user.user_id, reviewer_kind='assistant', started_by=user.user_id))

    def _execution(self, case, key):
        execution = self.policy.checked(self.db.evaluation_review_executions.find_one({'_id':key}))
        if (execution.get('repair_case_id') != case['id'] or execution.get('case_sha256') != case['sha256'] or
            execution['scope'] != case['scope'] or key != fingerprint(['repair-execution-v1',case['id'],execution['round']])):
            dp.reject('补证执行不属于当前case／轮次')
        return execution

    def seal(self, user, eid, case_id, key, values):
        data = RepairSealInput.model_validate(values).model_dump()
        case, _, _ = self.case(user, eid, case_id)
        if case['review_code_sha256'] != audit_code_identity(): dp.reject('补证封存前审核源码已漂移，保留现场')
        execution = self._execution(case, key)
        if execution['reviewer_id'] != user.user_id: dp.reject('不能封存其他审核者的判断')
        targets = {t['question_id']:t for t in case['targets'] if t['replace_dimensions']}
        judgments = data['judgments']
        if len(judgments) != len(targets) or {r['question_id'] for r in judgments} != set(targets):
            dp.reject('须完整覆盖授权补证子集，不得扩大或缺题')
        from .reviews import ReviewService
        _, subjects = ReviewService(self.repo)._subjects(user, eid)
        for judgment in judgments:
            target = targets[judgment['question_id']]
            scores = judgment['scores']
            if judgment['subject_sha256'] != target['subject_sha256'] or set(scores) != set(target['replace_dimensions']):
                dp.reject('补证题目／维度越界')
            if 'actionability' in scores and ((scores['actionability']=='not_applicable') == target['actionability_applicable']):
                dp.reject('新步骤判断须符合已固定题意适用性')
            if scores.get('image_relevance') == 'not_applicable' and has_review_images(subjects[judgment['question_id']][1].get('result') or {}):
                dp.reject('实际答案图不能跳过')
        return self.policy.store('evaluation_review_repair_seals', key, dict(scope=case['scope'], repair_case_id=case_id,
            case_sha256=case['sha256'], execution_id=key, execution_sha256=execution['sha256'],
            reviewer_id=user.user_id, round=execution['round'], judgments=sorted(judgments,key=lambda r:r['question_id'])))

    def _repair_pairs(self, case):
        if not any(t['replace_dimensions'] for t in case['targets']): return []
        pairs = []
        for n in (1, 2):
            key = fingerprint(['repair-execution-v1',case['id'],n])
            seal = self.policy.checked(self.db.evaluation_review_repair_seals.find_one({'_id':key}))
            execution = self._execution(case, key)
            if (seal['case_sha256'] != case['sha256'] or seal['repair_case_id'] != case['id'] or seal['scope'] != case['scope'] or
                seal['execution_sha256'] != execution['sha256'] or seal['round'] != n or seal['reviewer_id'] != execution['reviewer_id']):
                dp.reject('补证封存不再匹配当前来源')
            pairs.append((seal, execution))
        self._order(pairs)
        return pairs

    def attest(self, user, eid, case_id, values):
        data = RepairAttestInput.model_validate(values).model_dump()
        case, originals, _ = self.case(user, eid, case_id, controller=True)
        if case['review_code_sha256'] != audit_code_identity(): dp.reject('核验前审核源码已漂移，保留现场')
        pairs = self._repair_pairs(case)
        if set(data['seal_ids']) != {s['id'] for s, _ in pairs} or len(data['seal_ids']) != len(pairs): dp.reject('核验须绑定固定补证双轮')
        if user.user_id in {s['reviewer_id'] for s, _ in originals + pairs}: dp.reject('不能自签审核独立性')
        dp.verify_artifact(data['artifact'])
        return self.policy.store('evaluation_review_repair_attestations', case_id, dict(scope=case['scope'],
            repair_case_id=case_id, case_sha256=case['sha256'], original_seal_hashes=case['original_seal_hashes'],
            repair_seal_hashes=sorted(s['sha256'] for s, _ in pairs), controller_id=user.user_id, artifact=data['artifact']))

    def effective(self, user, eid):
        active = self.active(eid)
        case, original_pairs, originals = self.case(user, eid, active['id'])
        att = self.db.evaluation_review_repair_attestations.find_one({'_id':case['id']})
        if not att: return [], []
        self.policy.checked(att)
        pairs = self._repair_pairs(case)
        if (att['scope'] != case['scope'] or att['case_sha256'] != case['sha256'] or
            att['original_seal_hashes'] != case['original_seal_hashes'] or
            att['repair_seal_hashes'] != sorted(s['sha256'] for s, _ in pairs) or
            att['controller_id'] in {s['reviewer_id'] for s, _ in original_pairs + pairs}): dp.reject('总控核验已失效')
        dp.verify_artifact(att['artifact'])
        targets = {t['question_id']:t for t in case['targets']}
        supplements = {(s['round'],j['question_id']):(s,j) for s,_ in pairs for j in s['judgments']}
        projected = []
        for original in originals:
            row = deepcopy(original)
            qid, n = row['question_id'], row['round']
            target = targets.get(qid)
            # 核验属于实际来源，而不是题目永不改变的标签；规则纠错不替代原件核验。
            checked = {d: original['source_checked'] for d in DIMENSIONS}
            sources = {d:dict(kind='original_review', review_id=row['review_id'], execution_id=row['review_execution_id'],
                reviewer_id=row['reviewer_id'], round=n) for d in DIMENSIONS}
            if target:
                if target['replace_dimensions']:
                    seal, judgment = supplements[n, qid]
                    for dimension in target['replace_dimensions']:
                        row['scores'][dimension] = judgment['scores'][dimension]
                        row['dimension_evidence'][dimension] = judgment['dimension_evidence'][dimension]
                        checked[dimension] = judgment['source_checked']
                        sources[dimension] = dict(kind='repair_review', seal_id=seal['id'], seal_sha256=seal['sha256'],
                            execution_id=seal['execution_id'], reviewer_id=seal['reviewer_id'], round=n)
                    row['critical_errors'] = sorted(set(row['critical_errors'] + judgment['critical_errors']))
                if target['correct_actionability_na']:
                    row['scores']['actionability'] = 'not_applicable'
                    sources['actionability'] = dict(kind='controller_rule_correction', case_id=case['id'], case_sha256=case['sha256'],
                        controller_id=case['controller_id'], artifact=case['artifact'], original_review_id=original['review_id'], round=n)
                if target['actionability_applicable'] is not None:
                    row.update(actionability_applicable=target['actionability_applicable'], applicability_rationale=target['rationale'])
            # 仅内存投影，不伪装成新的原审核记录；逐维保存真实来源。
            row['source_checked'] = all(checked.values())
            row['dimension_sources'] = sources
            row['review_id'] = 'repair-projection-' + fingerprint([case['sha256'], sources])
            projected.append(row)
        return projected, [att['id']]

    def status(self, user, eid):
        """协调侧读取缺项；任何阶段均不回显补证评分。"""
        self._scope(user, eid, controller=user.role == 'admin')
        active = self.active(eid)
        if not active: return dict(case=None, executions=[], seals=[], attestation=None)
        case, _, _ = self.case(user, eid, active['id'], controller=user.role == 'admin')
        executions, seals = [], []
        for n in (1, 2):
            key = fingerprint(['repair-execution-v1',case['id'],n])
            row = self.db.evaluation_review_executions.find_one({'_id':key})
            if row:
                self._execution(case, key)
                executions.append({k:row[k] for k in ('id','sha256','created_at','round','execution_id','reviewer_model')})
            row = self.db.evaluation_review_repair_seals.find_one({'_id':key})
            if row:
                self.policy.checked(row)
                seals.append({k:row[k] for k in ('id','sha256','created_at','round')})
        att = self.db.evaluation_review_repair_attestations.find_one({'_id':case['id']})
        if att: self.policy.checked(att)
        return dict(case={k:case[k] for k in ('id','sha256','scope','targets','artifact')}, executions=executions,
            seals=seals, attestation={k:att[k] for k in ('id','sha256','created_at')} if att else None)
