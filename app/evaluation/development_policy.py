"""助手开发验收的不可变政策、盲审封存及总控核验；独立于human发布门槛。"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import subprocess
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from .validate_dataset import fingerprint

ROOT=Path(__file__).resolve().parents[2]
POLICY_ID='assistant-development-v1'
CRITICAL=('unauthorized','wrong_model','wrong_object','fabricated_live_state','unsafe_procedure')
APPROVED_DOCUMENTS={
    'docs/evaluation/assistant-development-policy-proposal-v1.md':'51c98b78e8bd23f25b9489c602ca1f8c5d22926babff89d05eaed31802695b29',
    'docs/evaluation/assistant-development-policy-decision-v1.md':'3079da9ff9cc9e44418610d780aa89822b476b4b0c2f37196cd39c38c06ec519',
}


class PolicyReference(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    id: str = Field(pattern=r'^[0-9a-f]{64}$')
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class SourceIdentity(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    source_id: str = Field(min_length=1,max_length=500)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class BeginInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    client_request_id: str = Field(min_length=1,max_length=128)
    round: int = Field(ge=1,le=2)
    execution_id: str = Field(min_length=1,max_length=128)
    reviewer_model: str = Field(min_length=1,max_length=200)
    source_manifest: list[SourceIdentity] = Field(min_length=1,max_length=1000)


class Artifact(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    commit: str = Field(pattern=r'^[0-9a-f]{40}$')
    path: str = Field(pattern=r'^docs/development/reviews/[A-Za-z0-9_.-]+\.md$')
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class AttestInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    seal_ids: list[str] = Field(min_length=2,max_length=2)
    artifact: Artifact


class ResolutionInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    client_request_id: str = Field(min_length=1,max_length=128)
    resolutions: dict = Field(min_length=1,max_length=4)
    critical_errors: list[str] = Field(default_factory=list,max_length=5)
    source_manifest: list[SourceIdentity] = Field(min_length=1,max_length=1000)


def reject(message):
    raise APIError(409,'development_policy_invalid',message)


def verify_artifact(value):
    result=subprocess.run(['git','show',value['commit']+':'+value['path']],cwd=ROOT,capture_output=True,check=False)
    if result.returncode or hashlib.sha256(result.stdout).hexdigest()!=value['sha256']:
        reject('总控独立性核验产物的受控提交或hash未核实')


def policy_payload():
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=sha for p,sha in APPROVED_DOCUMENTS.items()):
        reject('已批准政策文档变化，不能沿用v1授权')
    return dict(policy_id=POLICY_ID,purpose='development_acceptance',rubric='question-purpose-v1',
        critical_categories=list(CRITICAL),documents=dict(APPROVED_DOCUMENTS),
        authorization_commit='723c66d32501de30e08928b04577825623dd2b3a',human_publication_unchanged=True)


class DevelopmentPolicy:
    def __init__(self,repo):
        self.repo=repo
        self.db=repo.db
        self.db.evaluation_review_executions.create_index('execution_id',unique=True)

    def store(self,name,key,payload):
        col=self.db[name]
        row=dict(payload,created_at=datetime.now(timezone.utc).isoformat())
        row.update(id=key,sha256=fingerprint(row))
        try: col.update_one({'_id':key},{'$setOnInsert':row},upsert=True)
        except DuplicateKeyError: pass
        saved=col.find_one({'_id':key})
        if not saved or fingerprint({k:v for k,v in saved.items() if k not in {'_id','id','sha256','created_at'}})!=fingerprint(payload):
            reject('不可变政策/审核执行身份冲突或内容变化')
        self.checked(saved)
        return {k:v for k,v in saved.items() if k!='_id'}

    def register(self,user,kb_id):
        if user.role!='admin' or kb_id not in user.kb_ids:
            raise APIError(403,'forbidden','须授权总控管理员登记已批准政策。')
        row=self.store('evaluation_quality_policies',fingerprint([POLICY_ID,kb_id]),
            policy_payload()|dict(kb_id=kb_id,registrar_id=user.user_id))
        return dict(id=row['id'],sha256=row['sha256'])

    def require(self,user,reference,kb_id):
        PolicyReference.model_validate(reference)
        row=self.db.evaluation_quality_policies.find_one({'_id':reference['id'],'kb_id':kb_id})
        if (reference['id']!=fingerprint([POLICY_ID,kb_id]) or kb_id not in user.kb_ids or not row or row.get('sha256')!=reference['sha256'] or
            fingerprint({k:v for k,v in row.items() if k not in {'_id','id','sha256'}})!=row['sha256'] or
            any(row.get(k)!=v for k,v in policy_payload().items())):
            reject('政策注册缺失、版本/授权文档或范围变化')
        return row

    def scope(self,user,eid):
        from .reviews import ReviewService
        exp,subjects=ReviewService(self.repo)._subjects(user,eid)
        if not exp.get('quality_policy'): reject('实验未显式冻结助手开发政策')
        if not subjects or len(subjects)!=exp.get('selected_questions'): reject('实验结果不完整')
        self.require(user,exp['quality_policy'],exp['kb_id'])
        return exp,dict(experiment_id=eid,kb_id=exp['kb_id'],policy=exp['quality_policy'],
            dataset_sha256=exp['dataset_sha256'],manifest_sha256=exp['manifest_sha256'],
            config_sha256=exp.get('config_sha256'),regression_source=exp.get('regression_source'),
            quality_execution_key=exp.get('quality_execution_key'),
            result_attempt=exp['result_attempt'],subjects={k:v[0] for k,v in subjects.items()})

    def validate_candidate(self,user,data,resolved):
        self.require(user,data['quality_policy'],data['kb_id'])
        baseline_id=data.get('baseline_experiment_id')
        calibration_id=data.get('quality_calibration_id')
        if not baseline_id and not calibration_id: return
        from .reviews import ReviewService
        from .runner import select_questions
        from .validate_dataset import validate_dataset
        reviews=ReviewService(self.repo)
        calibration=reviews.calibrations.find_one({'calibration_id':calibration_id,
            'experiment_id':baseline_id,'owner_id':user.user_id})
        if not baseline_id or not calibration: reject('开发候选须先有同政策有效预校准')
        baseline,quality=reviews._quality(user,baseline_id)
        selected=select_questions(validate_dataset(resolved['dataset_path'],manifest=resolved['manifest_path']),resolved['config'])
        if (baseline.get('quality_policy')!=data['quality_policy'] or calibration.get('quality_policy')!=data['quality_policy'] or
            baseline.get('regression_source')!=data.get('regression_source') or
            quality!=calibration['baseline'] or quality['incomplete'] or quality['critical'] or
            any(resolved[k]!=calibration[k] for k in ('dataset_sha256','manifest_sha256')) or
            baseline['kb_id']!=data['kb_id'] or set(quality['subjects'])!={q['id'] for q in selected} or
            (data.get('regression_source') and data.get('regression_calibration_id')!=calibration_id)):
            reject('开发预校准已变化或候选政策/范围不一致')

    def rows(self,name,eid):
        return list(self.db[name].find({'scope.experiment_id':eid}))

    def checked(self,row):
        if not row or fingerprint({k:v for k,v in row.items() if k not in {'_id','id','sha256'}})!=row.get('sha256'):
            reject('审核执行或封存账本内容变化')
        return row

    def begin(self,user,eid,values):
        values=BeginInput.model_validate(values).model_dump()
        exp,scope=self.scope(user,eid)
        key=fingerprint([eid,values['round']])
        prior=self.db.evaluation_review_executions.find_one({'_id':key})
        if not prior:
            from .reviews import ReviewService
            _,subjects=ReviewService(self.repo)._subjects(user,eid)
            generated_runs={s[1].get('result',{}).get('run_id') for s in subjects.values()}
            if self.db.evaluation_review_executions.find_one({'execution_id':values['execution_id']}) or values['execution_id'] in generated_runs or values['execution_id'] in {
                eid,exp.get('regression_execution_key'),exp.get('quality_execution_key')}:
                reject('审核执行不能重复或冒用生成执行')
            if values['round']==2 and len(self.rows('evaluation_review_seals',eid))!=1:
                reject('第二轮须在第一轮封存后单独开始，评分仍不可读取')
        return self.store('evaluation_review_executions',key,values|dict(scope=scope,reviewer_id=user.user_id,
            reviewer_kind='assistant',started_by=user.user_id))

    def execution(self,user,eid,key):
        _,scope=self.scope(user,eid)
        row=self.checked(self.db.evaluation_review_executions.find_one({'_id':key}))
        if row.get('repair_case_id') or row['scope']!=scope or row['reviewer_id']!=user.user_id: reject('审核执行不属于当前审核者或结果已变化；限定补证须用专门封存入口')
        return row

    def seal(self,user,eid,key,values):
        from .reviews import ReviewInput,DIMENSIONS
        from .review_protocol import review_dump
        from app.answering.image_selection import has_review_images
        execution=self.execution(user,eid,key)
        inputs=[ReviewInput.model_validate(r) for r in values]
        if len({r.question_id for r in inputs})!=len(inputs) or {r.question_id for r in inputs}!=set(execution['scope']['subjects']):
            reject('每轮须封存完整同范围判断，不能挑题')
        from .reviews import ReviewService
        _,subjects=ReviewService(self.repo)._subjects(user,eid)
        for r in inputs:
            if (r.quality_policy!=execution['scope']['policy'] or r.review_execution_id!=key or
                r.reviewer_kind!='assistant' or r.human_attested or
                r.rubric_version!='question-purpose-v1' or r.round!=execution['round'] or
                r.subject_sha256!=execution['scope']['subjects'][r.question_id] or
                set(r.dimension_evidence)!=set(DIMENSIONS)):
                reject('封存须含同政策、当前完整结果、真实助手身份及逐维依据')
            if r.scores.image_relevance=='not_applicable' and has_review_images(subjects[r.question_id][1].get('result') or {}):
                reject('实际答案图不能跳过审核')
        return self.store('evaluation_review_seals',key,dict(scope=execution['scope'],execution_id=key,
            execution_sha256=execution['sha256'],reviewer_id=user.user_id,round=execution['round'],
            reviews=sorted([review_dump(r) for r in inputs],key=lambda r:r['question_id'])))

    def sealed_review(self,user,eid,data):
        execution=self.execution(user,eid,data.review_execution_id)
        seal=self.checked(self.db.evaluation_review_seals.find_one({'_id':execution['id']}))
        from .review_protocol import review_dump
        if seal['execution_sha256']!=execution['sha256'] or review_dump(data) not in seal['reviews']:
            reject('评分必须与本执行已经封存的完整判断一致')
        return seal

    def visible(self,eid):
        return len(self.rows('evaluation_review_seals',eid))==2

    def attest(self,user,eid,values):
        values=AttestInput.model_validate(values).model_dump()
        if user.role!='admin': raise APIError(403,'forbidden','只有总控管理员可核验独立性。')
        from .review_repairs import ReviewRepairs
        if ReviewRepairs(self.repo).active(eid): reject('已有限定修复case，须核验明确的逐维来源，不能全签旧对')
        # 总控可在同知识范围读取，所有者仍来自实验，不以总控身份自造评分。
        exp=self.db.evaluation_experiments.find_one({'experiment_id':eid,'kb_id':{'$in':list(user.kb_ids)}})
        if not exp: reject('实验不在总控授权范围')
        from types import SimpleNamespace
        owner=SimpleNamespace(user_id=exp['owner_id'],kb_ids=user.kb_ids)
        _,scope=self.scope(owner,eid)
        seals=[self.checked(self.db.evaluation_review_seals.find_one({'_id':s})) for s in values['seal_ids']]
        if (len(set(values['seal_ids']))!=2 or {s['round'] for s in seals}!={1,2} or
            any(s['scope']!=scope or s['reviewer_id']==user.user_id for s in seals)):
            reject('总控不得自签审核独立性或混用结果/轮次')
        executions=[self.checked(self.db.evaluation_review_executions.find_one({'_id':s['execution_id']})) for s in seals]
        pairs=sorted(zip(seals,executions),key=lambda p:p[0]['round'])
        if (executions[0]['execution_id']==executions[1]['execution_id'] or
            any(s['execution_sha256']!=e['sha256'] for s,e in pairs) or
            not pairs[0][1]['created_at']<=pairs[0][0]['created_at']<=pairs[1][1]['created_at']<=pairs[1][0]['created_at']):
            reject('审核执行或盲审封存时间顺序不成立')
        verify_artifact(values['artifact'])
        resolutions=[self.checked(r) for r in self.rows('evaluation_policy_resolutions',eid)]
        resolution_hashes=sorted(r['sha256'] for r in resolutions)
        return self.store('evaluation_review_independence',fingerprint([eid,scope,resolution_hashes]),dict(scope=scope,
            seal_hashes=sorted([s['sha256'] for s in seals]),resolution_hashes=resolution_hashes,
            controller_id=user.user_id,artifact=values['artifact']))

    def resolve(self,user,eid,review_id,values):
        """只补本人未知；追加后独立性证明须重新核验，原封存及确定分数不变。"""
        from .review_followups import Resolution
        from .reviews import ReviewInput, ReviewService
        from app.answering.image_selection import has_review_images
        data=ResolutionInput.model_validate(values).model_dump()
        from .review_repairs import ReviewRepairs
        if ReviewRepairs(self.repo).active(eid): reject('修复case已冻结原来源，不能另行追加旧轮未知')
        if not self.visible(eid): reject('双轮封存前不得追加或读取旧判断')
        _,scope=self.scope(user,eid)
        original=self.db.evaluation_reviews.find_one({'experiment_id':eid,'review_id':review_id,'reviewer_id':user.user_id})
        if not original: reject('不能解决他人的未知')
        self.sealed_review(user,eid,ReviewInput(**{k:original[k] for k in ReviewInput.model_fields if k in original}))
        unknown={k for k,v in original['scores'].items() if v=='unknown'}
        if not unknown or set(data['resolutions'])!=unknown or set(data['critical_errors'])-set(CRITICAL):
            reject('追加只接受该轮全部未知及冻结错误类别')
        data['resolutions']={k:Resolution.model_validate(v).model_dump() for k,v in data['resolutions'].items()}
        scores=original['scores']|{k:v['score'] for k,v in data['resolutions'].items()}
        ReviewInput(**({k:original[k] for k in ReviewInput.model_fields if k in original}|dict(scores=scores)))
        _,subjects=ReviewService(self.repo)._subjects(user,eid)
        if scores['image_relevance']=='not_applicable' and has_review_images(subjects[original['question_id']][1].get('result') or {}):
            reject('实际答案图不可跳过')
        return self.store('evaluation_policy_resolutions',fingerprint([eid,review_id]),data|dict(scope=scope,
            review_id=review_id,reviewer_id=user.user_id,original_sha256=fingerprint({k:v for k,v in original.items() if k!='_id'})))

    def effective(self,user,eid,current):
        from .review_repairs import ReviewRepairs
        repairs=ReviewRepairs(self.repo)
        if repairs.active(eid): return repairs.effective(user,eid)
        _,scope=self.scope(user,eid)
        seals=[self.checked(r) for r in self.rows('evaluation_review_seals',eid)]
        resolutions=[self.checked(r) for r in self.rows('evaluation_policy_resolutions',eid)]
        resolution_hashes=sorted(r['sha256'] for r in resolutions)
        attest=self.db.evaluation_review_independence.find_one({'_id':fingerprint([eid,scope,resolution_hashes])})
        if not attest or len(seals)!=2: return [],[]
        self.checked(attest)
        if (attest['seal_hashes']!=sorted([s['sha256'] for s in seals]) or attest['scope']!=scope or
            attest['resolution_hashes']!=resolution_hashes or {s['round'] for s in seals}!={1,2} or
            attest['controller_id'] in {s['reviewer_id'] for s in seals}):
            reject('独立性证明不再绑定当前封存')
        verify_artifact(attest['artifact'])
        valid=[]
        from .review_protocol import review_dump
        for s in seals:
            e=self.checked(self.db.evaluation_review_executions.find_one({'_id':s['execution_id']}))
            if e['sha256']!=s['execution_sha256'] or s['scope']!=scope: reject('审核执行输入变化')
            for r in current:
                if r.get('review_execution_id')==s['execution_id'] and r['reviewer_id']==s['reviewer_id']:
                    from .reviews import ReviewInput
                    payload={k:r[k] for k in ReviewInput.model_fields if k in r}
                    if review_dump(ReviewInput.model_validate(payload)) not in s['reviews']: reject('已保存评分与封存不一致')
                    updated=dict(r)
                    for resolution in resolutions:
                        if resolution['review_id']==r['review_id']:
                            if (resolution['scope']!=scope or resolution['reviewer_id']!=r['reviewer_id'] or
                                resolution['original_sha256']!=fingerprint(r)):
                                reject('追加未知与原审核来源不符')
                            updated=updated|dict(scores=r['scores']|{k:v['score'] for k,v in resolution['resolutions'].items()},
                                critical_errors=sorted(set(r['critical_errors']+resolution['critical_errors'])))
                    valid.append(updated)
        pairs=sorted([(s,self.checked(self.db.evaluation_review_executions.find_one({'_id':s['execution_id']})))
            for s in seals],key=lambda p:p[0]['round'])
        if (pairs[0][1]['execution_id']==pairs[1][1]['execution_id'] or
            not pairs[0][1]['created_at']<=pairs[0][0]['created_at']<=pairs[1][1]['created_at']<=pairs[1][0]['created_at']):
            reject('独立执行及封存顺序变化')
        return valid,[attest['id']]
