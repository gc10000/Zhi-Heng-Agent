"""评测通过正式持久运行入口执行；不将标准答案传入生成上下文。"""
from contextlib import contextmanager, ExitStack
import copy
import os
import re
from .validate_dataset import fingerprint, file_sha


def validate_target(config):
    target = config['target']
    for key, pattern in [('database', r'm1_test_m4_[a-z0-9_]+'),
                         ('collection', r'm1_test_m4_[a-z0-9_]+'),
                         ('owner_id', r'm4-test-[a-z0-9-]+'), ('kb_id', r'm4-test-[a-z0-9-]+'),
                         ('object_prefix', r'm4-test/[a-z0-9_-]+/')]:
        if not isinstance(target.get(key), str) or not re.fullmatch(pattern, target[key]):
            raise ValueError('评测目标必须是独立M4小样，拒绝访问课程目标')
    if not target.get('bucket'):
        raise ValueError('须显式选择既有测试桶，不自动建桶或修改策略')


@contextmanager
def open_evaluation_resources(config):
    """独立账本连接真实服务，但不运行API后台扫描其他实验。"""
    from dotenv import load_dotenv
    load_dotenv()
    from app.settings import Settings
    from pymongo import MongoClient
    from app.conversations.repository import ConversationRepository
    from app.runs.repository import RunRepository
    from app.runs.events import EventLedger
    from app.runs.commands import RunCommands
    from app.runs.service import RunService
    from app.runs.query_runner import QueryRunner
    from app.knowledge.resources import KnowledgeResources
    from .versions import runtime_versions
    if config['versions'] != runtime_versions():
        raise ValueError('实际源码、prompt或模型指纹与冻结基线配置不一致')
    if not os.getenv('MONGO_URL'):
        raise ValueError('请填写根目录.env的MONGO_URL，用于独立评测账本')
    t = config['target']
    client = MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000, tz_aware=True)
    knowledge, runner = None, None
    try:
        db = client[t['database']]
        conv = ConversationRepository(db)
        repo = RunRepository(db, conv)
        commands = RunCommands(repo, EventLedger(repo))
        settings = Settings(os.environ['MONGO_URL'], t['database'], knowledge_owner_id=t['owner_id'],
            object_bucket=t['bucket'], object_prefix=t['object_prefix'], milvus_collection=t['collection'])
        knowledge = KnowledgeResources(db, settings)
        # 已冻结原链路显式使用原默认，不能被宿主实验环境变量悄悄覆盖。
        from .strategy import strategy_policies
        from app.lm.runtime import ModelRuntimePolicy
        from .provider_counts import LogicalProviderCounts
        from app.lm.lm_utils import get_llm_client
        policies=strategy_policies(config)
        if policies.runtime!=ModelRuntimePolicy.load():raise ValueError('本机模型运行策略与冻结实验不一致')
        provider_counts=LogicalProviderCounts()
        runner = QueryRunner(repo, commands, knowledge.get, retrieval_policy=policies.retrieval,
            expansion_policy=policies.expansion,answer_budget=policies.answer_budget,enhancement_policy=policies.enhancement,
            source_prerequisites=policies.source_prerequisites,
            llm_factory=lambda:provider_counts.wrap(get_llm_client()))
        yield {'db': db, 'conversations': conv, 'runs': repo, 'run_service': RunService(repo),
               'commands': commands, 'query_runner': runner, 'knowledge': knowledge.get, 'provider_counts':provider_counts}
    finally:
        if runner: runner.close()
        if knowledge: knowledge.close()
        client.close()


class RealQueryExecutor:
    def __init__(self, config, *, resource_factory=None):
        validate_target(config)
        if resource_factory is None and not config.get('corpus', {}).get('snapshot'):
            raise ValueError('真实评测须冻结完整语料快照，不能只记录原件和活动指针')
        if resource_factory is None:
            acceptance = config.get('dataset_acceptance', [])
            if not acceptance or any(file_sha(a['path']) != a['sha256'] for a in acceptance):
                raise ValueError('须绑定真实题集接受结论，拒绝缺失或被改动的审阅材料')
        from .strategy import strategy_policies
        strategy_policies(config)
        self.config = copy.deepcopy(config)
        self.factory = resource_factory or open_evaluation_resources
        self.retry_key = None
        self.continuation = None
        self.execution = None
        self.control_db = None

    def verify_completed_checkpoint(self, question, record):
        """结果文件发布前崩溃：只读核实已完成Run，并登记当前attempt观察复用。"""
        from .execution_links import bind_execution, validate_execution
        validate_execution(self.control_db,self.execution,self.config)
        key = fingerprint([self.config,question['id']])
        saved = self.checkpoints.find_one({'_id':key})
        inputs = {k:question[k] for k in ('id','question','product_names','history')}
        if not saved or saved['input_sha256'] != fingerprint(inputs) or not saved.get('run_id'):
            raise ValueError('成功检查点缺少正式题级输入或Run，不自动回填')
        run = self.resources['runs'].get(self.user,saved['run_id'])
        self.check_corpus()
        from .execution_identity import run_input, outcome_identity, result_subject
        result = self.project_result(run)
        frozen = self.resources['db'].evaluation_outcomes.find_one({'_id':fingerprint([key,run['run_id']])})
        if (run['question'] != inputs['question'] or not frozen or
                any(frozen.get(k) != v for k,v in outcome_identity(self.resources['db'],self.config,key,run,result).items()) or
                frozen['result_sha256'] != fingerprint(result_subject(record['result']))):
            raise ValueError('成功检查点与冻结输入/完整执行结果不一致')
        prior = self.resources['db'].evaluation_execution_links.find_one(dict(
            experiment_id=self.execution['experiment_id'],question_id=question['id'],run_id=run['run_id'],
            config_sha256=fingerprint(self.config),regression_source=self.config['regression_source'],
            checkpoint_key=key,input_sha256=saved['input_sha256'],run_input_sha256=fingerprint(run_input(run,self.resources['db'])),
            control_database=self.control_db.name,target_database=self.resources['db'].name))
        if not prior:
            raise ValueError('成功检查点没有此前正式执行关联，不追认来源')
        bind_execution(self.resources['db'],self.control_db,self.execution,self.config,question['id'],key,
                       saved['input_sha256'],run)
        counts=self.resources.get('provider_counts')
        # attempts.jsonl中的历史调用数不动；本次发布结果反映观察复用新增0，缺测仍为null。
        record['result'].update(self.call_accounting(run,counts.snapshot() if counts else {}))

    def call_accounting(self, row, counts_before):
        counts = self.resources.get('provider_counts')
        local = {k: v-counts_before[k] for k, v in counts.snapshot().items()} if counts else None
        if self.config.get('metric_schema_version') != 1:
            return {'logical_provider_calls': local if local is not None else {}}
        # 题级/实验累计来自Run，不可用恢复进程新增0覆盖已持久化的调用1。
        persisted = (row.get('telemetry') or {}).get('logical_provider_calls')
        keys = ('invoke_started', 'stream_started')
        total = ({k: persisted[k] for k in keys} if isinstance(persisted, dict) and
                 all(type(persisted.get(k)) is int and persisted[k] >= 0 for k in keys) else None)
        return dict(logical_provider_calls=total, logical_provider_calls_scope='run_total',
                    execution_logical_provider_calls=local)

    def __enter__(self):
        self.stack = ExitStack()
        try:
            self.resources = self.stack.enter_context(self.factory(self.config))
            from .strategy import strategy_policies
            policies=strategy_policies(self.config)
            runner=self.resources.get('query_runner')
            if runner is not None:
                runner.capture_evaluation = self.config.get('metric_schema_version') == 1
                runner.retrieval_policy=policies.retrieval;runner.expansion_policy=policies.expansion
                runner.answer_budget=policies.answer_budget;runner.enhancement_policy=policies.enhancement
                runner.source_prerequisites=policies.source_prerequisites
            self.check_corpus()
            from app.identity.models import Principal
            t = self.config['target']
            self.user = Principal(user_id=t['owner_id'], username='M4隔离评测', role='maintainer', kb_ids=(t['kb_id'],))
            self.checkpoints = self.resources['db'].evaluation_items
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def check_corpus(self):
        g = self.resources['knowledge']()
        repo = g.repo(self.config['target']['kb_id'])
        self.documents = {r['document_id']: r for r in self.config['corpus']['documents']}
        if not self.documents:
            raise ValueError('真实基线须冻结非空语料快照')
        expected = {(r['document_id'], r['revision_id']) for r in self.documents.values()}
        current = {(r['document_id'], r['active_revision_id']) for r in repo.get_active_revisions()}
        candidates = self.config['corpus'].get('candidate_revisions', [])
        overrides = {r['document_id']: r for r in candidates}
        if len(overrides) != len(candidates) or (candidates and self.config.get('metric_schema_version') != 1):
            raise ValueError('候选修订须显式使用M6评测模式且每资料唯一')
        comparison = set(current)
        for candidate in candidates:
            old = (candidate['document_id'], candidate['expected_active_revision_id'])
            new = (candidate['document_id'], candidate['revision_id'])
            if old not in current or new not in expected or old == new:
                raise ValueError('候选修订不属于冻结活动资料')
            revision = repo.get_revision(candidate['revision_id'])
            if (revision['document_id'] != candidate['document_id'] or revision['status'] != 'validated' or
                    revision.get('validation') != candidate['validation'] or
                    g.publisher(self.config['target']['kb_id']).inspect(revision) != candidate['validation']):
                raise ValueError('候选修订验证失效，拒绝评测')
            comparison.remove(old)
            comparison.add(new)
        if expected != comparison:
            raise ValueError('活动修订与冻结语料不一致，拒绝混入其他知识')
        for item in self.documents.values():
            revision = repo.get_revision(item['revision_id'])
            allowed_status = 'validated' if item['document_id'] in overrides else 'published'
            if revision['original_sha256'] != item['original_sha256'] or revision['status'] != allowed_status:
                raise ValueError('冻结语料原件指纹/发布状态不符')
        if 'snapshot' in self.config['corpus']:
            from .corpus import corpus_snapshot, validate_asset_equivalences
            actual = corpus_snapshot(g, self.config['target'], list(self.documents.values()),
                                     expected=self.config['corpus']['snapshot'])
            if fingerprint(actual) != fingerprint(self.config['corpus']['snapshot']):
                raise ValueError('实际语料完整载荷/向量/图片/产品与冻结快照不一致')
            validate_asset_equivalences(actual, self.config['corpus'].get('asset_equivalences', []))
        if candidates and self.resources.get('query_runner') is not None:
            self.resources['query_runner'].evaluation_revisions = [
                {'document_id': d, 'active_revision_id': r} for d, r in sorted(expected)]
        self.products = {p['model']: p['product_id'] for p in g.products.collection.find({'owner_id': g.owner_id})}

    def __call__(self, question):
        if self.execution:
            from .execution_links import validate_execution
            # 先验明控制任务，再写conversation/checkpoint/Run；不把target当控制库。
            validate_execution(self.control_db, self.execution, self.config)
        self.check_corpus()
        counts=self.resources.get('provider_counts')
        counts_before=counts.snapshot() if counts else {}
        # 只传输入字段；标准答案、证据和评审关键点不进入真实执行上下文。
        inputs = {k: question[k] for k in ('id', 'question', 'product_names', 'history')}
        key = fingerprint([self.config, question['id']])
        saved = self.checkpoints.find_one({'_id': key})
        conv = self.resources['conversations']
        kb = self.config['target']['kb_id']
        if saved is None:
            from app.conversations.models import ConversationInput
            product_ids = [self.products[name] for name in inputs['product_names']]
            cid = conv.create(self.user, ConversationInput(kb_id=kb, title='M4隔离评测', product_ids=product_ids))['conversation_id']
            self.checkpoints.update_one({'_id': key}, {'$setOnInsert': {'conversation_id': cid, 'input_sha256': fingerprint(inputs)}}, upsert=True)
            saved = self.checkpoints.find_one({'_id': key})
        if saved['input_sha256'] != fingerprint(inputs):
            raise ValueError('题目输入与已持久运行不一致')
        cid = saved['conversation_id']
        for index, message in enumerate(inputs['history']):
            conv.append_message(self.user, cid, run_id=fingerprint([key, 'history', index]), role=message['role'],
                                text=message['text'], product_snapshot={'product_ids': [], 'version': 0})
        from app.runs.models import RunInput,InternalRunInput
        request_key = saved.get('request_key', key)
        followup = None
        if self.continuation and self.config.get('metric_schema_version') == 1 and saved.get('run_id'):
            from .continuations import prepare_continuation
            previous = self.resources['runs'].get(self.user, saved['run_id'])
            followup = prepare_continuation(self.resources['db'], self.continuation,
                checkpoint_key=key, input_sha256=saved['input_sha256'], previous=previous,
                request_key=request_key, question_id=question['id'], config=self.config,
                control_db=self.control_db)
            if followup:
                request_key = followup['request_key']
        if not followup and self.retry_key and self.config.get('metric_schema_version') == 1 and saved.get('run_id'):
            previous = self.resources['runs'].get(self.user, saved['run_id'])
            if previous['state'] == 'failed' and previous.get('error', {}).get('retryable') is True:
                request_key = fingerprint([key, 'explicit_retry', self.retry_key])
        request_type=InternalRunInput if 'source_prerequisites' in self.config.get('parameters',{}) else RunInput
        extra=({'source_prerequisites':self.config['parameters']['source_prerequisites']} if request_type is InternalRunInput else {})
        run = self.resources['run_service'].create(self.user, cid, request_type(kb_id=kb, question=inputs['question'], client_request_id=request_key,**extra))
        rid = run['run_id']
        # RunService返回公开快照；输入冻结使用正式持久记录，不能把被裁剪的快照当完整身份。
        persistent_run = self.resources['runs'].get(self.user,rid)
        if persistent_run['question'] != inputs['question']:
            raise ValueError('正式Run题目与冻结输入不同')
        if self.execution and run['state'] in {'pending', 'running', 'completed', 'awaiting_input'}:
            from .execution_links import bind_execution
            bind_execution(self.resources['db'], self.control_db, self.execution, self.config, question['id'], key,
                           saved['input_sha256'], persistent_run)
        self.checkpoints.update_one({'_id': key}, {'$set': {'run_id': rid, 'request_key': request_key}})
        if followup:
            from .continuations import observe_continuation
            observe_continuation(self.resources['db'], followup, self.resources['runs'].get(self.user, rid))
        try:
            if run['state'] == 'pending':
                self.resources['query_runner'].execute(rid)
        finally:
            if followup:
                observe_continuation(self.resources['db'], followup, self.resources['runs'].get(self.user, rid))
        row = self.resources['runs'].get(self.user, rid)
        accounting = self.call_accounting(row, counts_before)
        result = self.project_result(row) | accounting
        if self.config.get('regression_source'):
            from .execution_identity import freeze_outcome
            freeze_outcome(self.resources['db'],self.config,key,row,result)
        return result

    def project_result(self, row):
        """首次执行和恢复共用受控投影，状态/行为/引用/图片映射不另设较窄规则。"""
        rid = row['run_id']
        if row['state'] == 'awaiting_input':
            return {'run_id': rid, 'state': row['state'], 'behavior': 'clarify', 'answer': '', 'citations': [],
                    'candidates': row.get('candidates', [])} | (
                        {'retrieval_candidates': {'candidates': [], 'reranked': [], 'context': []}}
                        if self.config.get('metric_schema_version') == 1 else {})
        if row['state'] != 'completed':
            # 不自动新建run重付费，保留持久账本供恢复/明确重试。
            if self.config.get('metric_schema_version') == 1 and row.get('error', {}).get('retryable') is not None:
                from app.infrastructure.providers.policy import ProviderFailure
                failure = ProviderFailure(row['error']['code'], row['error']['retryable'])
                failure.stage = row['error'].get('stage', 'unknown')
                raise failure
            raise ValueError('真实运行未完成；请按本机检查点核对运行状态')
        citations = []
        g = self.resources['knowledge']()
        for c in row['citations']:
            source = self.documents[c['document_id']]
            if c['revision_id'] != source['revision_id']:
                raise ValueError('引用跨出冻结修订')
            for ref in c['source_refs']:
                if ref.get('page'):
                    citations.append({'document_sha256': source['original_sha256'], 'page': ref['page'],
                                      'chunk_uid': c['chunk_uid'], 'revision_id': c['revision_id']})
            for aid in c['asset_ids']:
                asset = g.db.knowledge_assets.find_one({'asset_id': aid, 'document_id': c['document_id'], 'revision_id': c['revision_id']})
                if asset:
                    for ref in asset['source_refs']:
                        if ref.get('page'):
                            image = {'document_sha256': source['original_sha256'], 'page': ref['page'], 'asset_sha256': asset['sha256']}
                            if c.get('image_selection_version') == 1:
                                image['image_usage'] = 'answer' if aid in c['answer_asset_ids'] else 'context'
                            citations.append(image)
        extra = {}
        if row['citations'] and all(c.get('image_selection_version') == 1 for c in row['citations']):
            extra['image_selection_version'] = 1
        if self.config.get('metric_schema_version') == 1:
            telemetry = row.get('telemetry') or {}
            if telemetry.get('schema_version') == 1:
                extra['stage_timings'] = dict(telemetry.get('stage_seconds', {}))
                extra['token_usage'] = telemetry.get('token_usage', {'input': None, 'output': None})
            from app.retrieval.models import RetrievalHit
            from .retrieval_grid import ranked_source_candidates
            groups = row.get('evaluation_candidates')
            if groups is None:
                raise ValueError('M6正式运行缺少分阶段来源，不能伪造检索指标')
            assets = {a['asset_id']: a for a in g.db.knowledge_assets.find({
                'document_id': {'$in': list(self.documents)}})}
            extra['retrieval_candidates'] = {name: ranked_source_candidates(
                [RetrievalHit(**item, text='') for item in group], self.documents, assets)
                for name, group in groups.items()}
        return extra | {'run_id': rid, 'state': row['state'], 'behavior': 'answer' if citations else 'insufficient',
                'answer': row['answer'], 'citations': citations,
                'behavior_notice': '行为为协议与证据的保守辅助判定；部分回答/比较须人工复核',
                'answer_support':row.get('answer_support'), 'prompt_budget':row.get('prompt_budget'),
                'output_truncated':row.get('output_truncated'), 'retrieval_branches':row.get('retrieval_branches',[])}
