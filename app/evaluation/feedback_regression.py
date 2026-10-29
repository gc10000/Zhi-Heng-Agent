"""回归反馈来源与复评账本；标签审核独立于答案human双轮，不执行资料发布。"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.api.errors import APIError
from .datasets import is_label_eligible
from .regression_versions import derive_version
from .validate_dataset import Question, fingerprint, validate_dataset


def reject(message, code='regression_source_invalid'):
    raise APIError(409, code, message)


def content(row):
    return {k: deepcopy(v) for k, v in row.items() if k not in {'_id', 'id', 'sha256', 'created_at'}}


def verify_review_artifact(annotation):
    """审阅来源须存在于明确提交的受控仓库，不能仅接受客户端给出的hash字符串。"""
    review = annotation['review']
    result = subprocess.run(['git','show',review['commit']+':'+review['artifact']],
        cwd=Path(__file__).resolve().parents[2],capture_output=True,check=False)
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != review['artifact_sha256']:
        reject('独立标签审核的提交或文档hash未核实')


class RegressionService:
    digest = staticmethod(fingerprint)

    def __init__(self, repo, catalog):
        self.repo, self.catalog = repo, catalog

    @staticmethod
    def reference(row):
        return dict(id=row['id'], sha256=row['sha256'])

    def store(self, collection, key, payload):
        identity = fingerprint(payload)
        row = dict(payload, id=key, sha256=identity, created_at=datetime.now(timezone.utc).isoformat())
        try:
            saved = collection.find_one_and_update({'_id':key}, {'$setOnInsert':row},
                upsert=True, return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:
            saved = collection.find_one({'_id':key})
        if saved.get('sha256') != identity or fingerprint(content(saved)) != identity:
            reject('不可变来源请求已绑定其他内容', 'regression_conflict')
        return {k:v for k,v in saved.items() if k != '_id'}

    def scoped(self, user, collection, key):
        row = collection.find_one({'_id':key, 'kb_id':{'$in':list(user.kb_ids)}})
        if row is None or row.get('owner_id') != user.user_id:
            raise APIError(404, 'not_found', '回归来源不存在或不在授权范围。')
        if fingerprint(content(row)) != row['sha256']:
            reject('来源内容指纹变化')
        return row

    def source(self, user, fid):
        db = self.repo.db
        feedback = db.support_feedback.find_one({'feedback_id':fid, 'kb_id':{'$in':list(user.kb_ids)}})
        if not feedback or feedback.get('state') != 'confirmed' or feedback.get('draft', {}).get('kind') != 'regression':
            reject('须使用已确认的regression反馈')
        from .feedback_triage import feedback_source_db
        source_db = feedback_source_db(db,feedback)
        run = source_db.runs.find_one(dict(run_id=feedback['run_id'], owner_id=feedback['owner_id'], kb_id=feedback['kb_id']))
        if not run or run.get('state') not in {'completed','awaiting_input'}:
            reject('反馈来源Run缺失或不是已回答/等待澄清结果')
        revisions = []
        identities = set()
        def collect(value):
            if isinstance(value, dict):
                if value.get('document_id') and value.get('revision_id'):
                    identities.add((value['document_id'], value['revision_id']))
                for nested in value.values(): collect(nested)
            elif isinstance(value, list):
                for nested in value: collect(nested)
        collect([feedback, run.get('citations', []), run.get('revision_snapshot', [])])
        for did, rid in sorted(identities):
            doc = source_db.knowledge_documents.find_one({'document_id':did, 'kb_id':{'$in':list(user.kb_ids)}})
            rev = source_db.knowledge_revisions.find_one({'document_id':did, 'revision_id':rid})
            if not doc or not rev or doc['kb_id'] != feedback['kb_id'] or rev.get('owner_id') != doc.get('owner_id'):
                reject('反馈资料来源已撤权或修订不匹配')
            revisions.append(dict(document_id=did, revision_id=rid, owner_id=doc['owner_id'],
                kb_id=doc['kb_id'], original_sha256=rev['original_sha256']))
        # 只绑定结果及输入快照，不把租约、事件TTL等操作状态当作答案内容。
        run_fields = {k:run[k] for k in ('run_id','conversation_id','owner_id','kb_id','state','input',
            'identity','question','requested_product_ids','input_product_snapshot','product_snapshot',
            'source_prerequisites_sha256','answer','final_answer','result','citations','revision_snapshot') if k in run}
        if run['state'] == 'awaiting_input':
            run_fields.update({k:deepcopy(run[k]) for k in ('candidates','resume_point') if k in run})
        return dict(feedback_id=fid, feedback_sha256=fingerprint({k:v for k,v in feedback.items() if k != '_id'}),
            feedback_version=feedback.get('version',0), run_id=run['run_id'], run_sha256=fingerprint(run_fields),
            source_database=source_db.name, source_revisions=revisions, kb_id=feedback['kb_id']), feedback

    def evidence_revisions(self,user,source,references):
        """独立审核补充证据，库映射来自原反馈，绝不向旧Run补造引用。"""
        db = self.repo.db.client[source['source_database']]
        mappings = []
        seen = set()
        for ref in references:
            did,rid = ref['document_id'],ref['revision_id']
            if (did,rid) in seen:
                reject('补充原件修订不得重复')
            seen.add((did,rid))
            doc = db.knowledge_documents.find_one({'document_id':did,'kb_id':source['kb_id']})
            rev = db.knowledge_revisions.find_one({'document_id':did,'revision_id':rid,'kb_id':source['kb_id']})
            if not doc or not rev or source['kb_id'] not in user.kb_ids or rev.get('owner_id') != doc.get('owner_id'):
                reject('补充原件未授权或修订映射无效')
            mappings.append(dict(document_id=did,revision_id=rid,owner_id=doc['owner_id'],
                kb_id=doc['kb_id'],original_sha256=rev['original_sha256']))
        if source['source_revisions'] and any(r not in source['source_revisions'] for r in mappings):
            reject('已有反馈证据范围不能通过补充映射扩大')
        return sorted(mappings,key=lambda r:(r['document_id'],r['revision_id']))

    def check_evidence(self,user,row):
        references = row.get('evidence_revisions',[])
        if references and self.evidence_revisions(user,row['source'],references) != references:
            reject('独立审核的补充原件修订变化或撤权')
        return references or row['source']['source_revisions']

    def candidate(self, user, fid, question, evidence_revisions=None):
        source, feedback = self.source(user, fid)
        Question.model_validate(question)
        if question['split'] != 'dev' or question['annotation']['status'] != 'draft':
            reject('新候选须是dev标签草稿，不接受客户端直接标为已审')
        if question['question'] != feedback['draft']['question']:
            reject('候选完整题目与反馈草稿不一致')
        payload = dict(owner_id=user.user_id, kb_id=source['kb_id'], creator_id=user.user_id,
                       source=source, question=deepcopy(question))
        if evidence_revisions:
            payload['evidence_revisions'] = self.evidence_revisions(user,source,evidence_revisions)
            payload['evidence_mapping_sha256'] = fingerprint(dict(source=source,question=question,
                proposed_expectation=feedback['draft']['proposed_expectation'],evidence_revisions=payload['evidence_revisions']))
        return self.store(self.repo.db.regression_candidates, fingerprint(payload), payload)

    def review(self, user, candidate_id, annotation, evidence_mapping_sha256=None):
        # 审阅者可在同知识范围读取候选；不能以候选所有者身份自签独立审阅。
        candidate = self.repo.db.regression_candidates.find_one({'_id':candidate_id,'kb_id':{'$in':list(user.kb_ids)}})
        if not candidate or fingerprint(content(candidate)) != candidate.get('sha256'):
            reject('标签候选不存在或已变化')
        source, _ = self.source(user, candidate['source']['feedback_id'])
        if source != candidate['source'] or candidate['creator_id'] == user.user_id:
            reject('须由另一合法审核者核对未变的候选及来源')
        evidence = self.check_evidence(user,candidate)
        if not evidence or not set(candidate['question']['source_scope']) <= {r['original_sha256'] for r in evidence}:
            reject('独立审核须有覆盖题目的授权原件修订')
        if candidate.get('evidence_mapping_sha256') and candidate['evidence_mapping_sha256'] != evidence_mapping_sha256:
            reject('须明确确认完整题目、反馈预期及补充原件映射hash')
        question = deepcopy(candidate['question'])
        question['annotation'] = deepcopy(annotation)
        Question.model_validate(question)
        if (not is_label_eligible(question) or annotation.get('reviewer') != user.user_id or
                annotation.get('method') != 'independent_assistant_review'):
            reject('此入口只接受具名独立助手标签审核，不接受human声明')
        verify_review_artifact(annotation)
        payload = dict(owner_id=candidate['owner_id'], kb_id=candidate['kb_id'], creator_id=candidate['creator_id'],
            reviewer_id=user.user_id, candidate_id=candidate_id, candidate_sha256=candidate['sha256'],
            source=source, question=question)
        if candidate.get('evidence_revisions'):
            payload.update(evidence_revisions=candidate['evidence_revisions'],
                           evidence_mapping_sha256=candidate['evidence_mapping_sha256'])
        return self.store(self.repo.db.regression_annotations, candidate_id, payload)

    def resolve(self, target, kb_id):
        try:
            return self.catalog.resolve(target['dataset_id'],target['dataset_version'],target['config_id'],
                                        target['config_version'],kb_id=kb_id)
        except (ValueError, OSError, KeyError):
            reject('冻结题集或配置无效')

    def status(self,user,fid):
        """只读接续状态；已保存证明不等于本次重新执行质量门槛。"""
        source,_ = self.source(user,fid)
        row=self.repo.db.regression_bindings.find_one({'owner_id':user.user_id,
            'kb_id':source['kb_id'],'source.feedback_id':fid})
        value=dict(binding_status='unbound',source=None,proof_status='absent',quality_passed=None)
        if row is None:
            return value
        value['source']=self.reference(row)
        try:
            self.validate(user,value['source'])
        except APIError:
            return value | dict(binding_status='invalid')
        proof=self.repo.db.regression_proofs.find_one({'_id':row['id'],'owner_id':user.user_id,
            'kb_id':source['kb_id']})
        return value | dict(binding_status='valid',question_id=row['question_id'],
            dataset_id=row['dataset_id'],dataset_version=row['dataset_version'],
            proof_status='recorded_not_revalidated' if proof else 'absent')

    def bind(self, user, fid, target):
        source, feedback = self.source(user, fid)
        parent = self.resolve(target, source['kb_id'])
        rows = validate_dataset(parent['dataset_path'],manifest=parent['manifest_path'])
        old = next((q for q in rows if q['id']==target['question_id']),None)
        question, annotation = old, None
        if target.get('annotation_id'):
            annotation = self.scoped(user,self.repo.db.regression_annotations,target['annotation_id'])
            if annotation['source'] != source:
                reject('标签审核未绑定当前反馈来源')
            question = annotation['question']
            if question['id'] != target['question_id']:
                reject('题目身份与审核不一致')
        if not question or question['split'] != 'dev' or not is_label_eligible(question):
            reject('只允许绑定已审核的完整dev题目')
        if question['question'] != feedback['draft']['question']:
            reject('题目与反馈草稿不匹配')
        if annotation is None:
            expectation = feedback['draft']['proposed_expectation']
            try:
                exact = json.loads(expectation) == question['expected']
            except (ValueError,TypeError):
                exact = False
            # 仅接受字面匹配，不由服务端猜测两个不同预期的语义等价；否则须独立审核映射。
            if not exact and ' '.join(expectation.split()) != ' '.join('\n'.join(question['expected']['key_points']).split()):
                reject('反馈预期与已审标签不精确匹配，须独立审核完整题目及反馈映射')
        evidence = self.check_evidence(user,annotation) if annotation else source['source_revisions']
        originals = {r['original_sha256'] for r in evidence}
        if not originals or not set(question['source_scope']) <= originals:
            reject('题目原件范围未绑定反馈精确修订')
        identity = {k:target[k] for k in ('dataset_id','dataset_version','config_id','config_version')}
        parent_identity = None
        if old != question:
            if annotation is None:
                reject('变化题目须先独立审核')
            parent_identity = identity
            identity = derive_version(self.catalog,parent,question,dataset_id=target['dataset_id'],
                parent_version=target['dataset_version'],kb_id=source['kb_id'])
        resolved = self.resolve(identity,source['kb_id'])
        from .runner import select_questions
        selected = select_questions(validate_dataset(resolved['dataset_path'],manifest=resolved['manifest_path']),resolved['config'])
        if question['id'] not in {q['id'] for q in selected}:
            reject('配置未选择反馈题目')
        payload = dict(owner_id=user.user_id,kb_id=source['kb_id'],source=source,**identity,
            parent=parent_identity, question_id=question['id'],question_sha256=fingerprint(question),
            question=deepcopy(question),annotation_sha256=fingerprint(question['annotation']),
            annotation_id=annotation['id'] if annotation else None,
            annotation_record_sha256=annotation['sha256'] if annotation else None,
            dataset_sha256=resolved['dataset_sha256'],manifest_sha256=resolved['manifest_sha256'],
            config_sha256=resolved['config_sha256'],
            binding_request=deepcopy(target))
        key = fingerprint([user.user_id,fid])
        return self.store(self.repo.db.regression_bindings,key,payload)

    def validate(self, user, reference, resolved=None):
        row = self.scoped(user,self.repo.db.regression_bindings,reference['id'])
        if row['sha256'] != reference['sha256']:
            reject('回归来源hash不匹配')
        source,_ = self.source(user,row['source']['feedback_id'])
        if source != row['source']:
            reject('反馈审核或原Run结果及资料来源变化')
        if row.get('annotation_id'):
            audit = self.scoped(user,self.repo.db.regression_annotations,row['annotation_id'])
            self.check_evidence(user,audit)
            if (audit['sha256'] != row['annotation_record_sha256'] or
                    fingerprint(audit['question']) != row['question_sha256']):
                reject('独立标签审核记录变化或缺失')
        actual = self.resolve(row,row['kb_id'])
        if any(actual[k] != row[k] for k in ('dataset_sha256','manifest_sha256','config_sha256')):
            reject('回归冻结版本变化')
        rows = validate_dataset(actual['dataset_path'],manifest=actual['manifest_path'])
        if not any(q['id']==row['question_id'] and fingerprint(q)==row['question_sha256'] for q in rows):
            reject('回归题级指纹变化')
        if resolved:
            from .runner import select_questions
            selected = select_questions(rows,resolved['config'])
            if (any(resolved[k] != row[k] for k in ('dataset_sha256','manifest_sha256')) or
                    row['question_id'] not in {q['id'] for q in selected}):
                reject('实验没有消费绑定的冻结版本和题目')
        return row

    def validate_calibration(self,user,resolved,baseline_id,calibration_id):
        if not baseline_id and not calibration_id:
            return
        from .reviews import ReviewService
        reviews = ReviewService(self.repo)
        calibration = reviews.calibrations.find_one({'calibration_id':calibration_id,'owner_id':user.user_id,
            'kb_id':{'$in':list(user.kb_ids)}})
        if not baseline_id or not calibration or calibration['experiment_id'] != baseline_id:
            reject('反馈候选须先绑定同范围基线的有效预校准','regression_calibration_required')
        baseline,quality = reviews._quality(user,baseline_id)
        from .runner import select_questions
        rows = validate_dataset(resolved['dataset_path'],manifest=resolved['manifest_path'])
        selected = select_questions(rows,resolved['config'])
        if (quality != calibration['baseline'] or quality['incomplete'] or quality['critical'] or
                any(resolved[k] != calibration[k] for k in ('dataset_sha256','manifest_sha256')) or
                baseline['kb_id'] != resolved['config']['target']['kb_id'] or
                set(quality['subjects']) != {q['id'] for q in selected}):
            reject('预校准已变化或与反馈候选版本/范围不一致','regression_calibration_required')

    def proof(self, user, reference, experiment_id, calibration_id):
        binding = self.validate(user,reference)
        from .reviews import ReviewService
        reviews = ReviewService(self.repo)
        experiment, quality = reviews._quality(user,experiment_id)
        gate = reviews.gate(user,experiment_id,calibration_id)
        calibration = reviews.calibrations.find_one({'calibration_id':calibration_id,'owner_id':user.user_id})
        resolved = self.resolve(dict(dataset_id=experiment['eval_set_id'],dataset_version=experiment['eval_set_version'],
            config_id=experiment['config_id'],config_version=experiment['config_version']),experiment['kb_id'])
        self.validate(user,reference,resolved)
        from .runner import select_questions
        selected = select_questions(validate_dataset(resolved['dataset_path'],manifest=resolved['manifest_path']),resolved['config'])
        if (gate['status'] != 'passed' or experiment.get('regression_source') != reference or
                experiment['kb_id'] != binding['kb_id'] or experiment['created_at'] <= binding['created_at'] or
                experiment.get('baseline_experiment_id') != calibration['experiment_id'] or
                experiment.get('regression_calibration_id') != calibration_id or
                set(quality['subjects']) != {q['id'] for q in selected}):
            reject('复评未通过正式质量门槛、范围、顺序或来源校验','regression_proof_invalid')
        # 证明只能认可正式题级接线，不追认旧结果或客户端报告。
        target = resolved['config']['target']
        db = self.repo.db.client[target['database']]
        links = []
        for q in selected:
            link = db.evaluation_execution_links.find_one(dict(experiment_id=experiment_id,
                attempt=experiment['result_attempt'],question_id=q['id']))
            result = self.repo.results.find_one(dict(experiment_id=experiment_id,attempt=experiment['result_attempt'],question_id=q['id']))
            if (not link or link.get('regression_source') != reference or link.get('control_database') != self.repo.db.name or
                    link.get('target_database') != db.name or not result or link['run_id'] != result['result'].get('run_id')):
                reject('当前结果缺少正式题级来源关联','regression_proof_invalid')
            links.append(fingerprint({k:v for k,v in link.items() if k != '_id'}))
        payload = dict(owner_id=user.user_id,kb_id=binding['kb_id'],regression_source=reference,
            experiment_id=experiment_id,result_attempt=experiment['result_attempt'],calibration_id=calibration_id,
            calibration_sha256=fingerprint({k:v for k,v in calibration.items() if k != '_id'}),
            quality_sha256=fingerprint(quality),subjects=quality['subjects'],execution_links_sha256=fingerprint(links),
            gate_sha256=fingerprint(gate),automatic_publish=False)
        # 跨集合读后的最后一道核验；当前attempt/来源/评分变化不能用旧快照保存新证明。
        latest,current_quality = reviews._quality(user,experiment_id)
        self.validate(user,reference,resolved)
        if (latest['result_attempt'] != experiment['result_attempt'] or
                fingerprint(current_quality) != payload['quality_sha256']):
            reject('保存前结果或评分变化','regression_proof_invalid')
        return self.store(self.repo.db.regression_proofs,reference['id'],payload)
