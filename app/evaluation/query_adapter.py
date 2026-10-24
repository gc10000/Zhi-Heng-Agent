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
        runner = QueryRunner(repo, commands, knowledge.get)
        yield {'db': db, 'conversations': conv, 'runs': repo, 'run_service': RunService(repo),
               'commands': commands, 'query_runner': runner, 'knowledge': knowledge.get}
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
        if config['strategy'] != 'm3-baseline':
            raise ValueError('基线适配器仅支持既有正式策略，不能静默忽略实验参数')
        if config.get('parameters'):
            raise ValueError('原链路基线不接受未实现的检索参数覆盖')
        self.config = copy.deepcopy(config)
        self.factory = resource_factory or open_evaluation_resources

    def __enter__(self):
        self.stack = ExitStack()
        try:
            self.resources = self.stack.enter_context(self.factory(self.config))
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
        if expected != current:
            raise ValueError('活动修订与冻结语料不一致，拒绝混入其他知识')
        for item in self.documents.values():
            revision = repo.get_revision(item['revision_id'])
            if revision['original_sha256'] != item['original_sha256'] or revision['status'] != 'published':
                raise ValueError('冻结语料原件指纹/发布状态不符')
        if 'snapshot' in self.config['corpus']:
            from .corpus import corpus_snapshot, validate_asset_equivalences
            actual = corpus_snapshot(g, self.config['target'], list(self.documents.values()),
                                     expected=self.config['corpus']['snapshot'])
            if fingerprint(actual) != fingerprint(self.config['corpus']['snapshot']):
                raise ValueError('实际语料完整载荷/向量/图片/产品与冻结快照不一致')
            validate_asset_equivalences(actual, self.config['corpus'].get('asset_equivalences', []))
        self.products = {p['model']: p['product_id'] for p in g.products.collection.find({'owner_id': g.owner_id})}

    def __call__(self, question):
        self.check_corpus()
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
        from app.runs.models import RunInput
        run = self.resources['run_service'].create(self.user, cid, RunInput(kb_id=kb, question=inputs['question'], client_request_id=key))
        rid = run['run_id']
        self.checkpoints.update_one({'_id': key}, {'$set': {'run_id': rid}})
        if run['state'] == 'pending':
            self.resources['query_runner'].execute(rid)
        row = self.resources['runs'].get(self.user, rid)
        if row['state'] == 'awaiting_input':
            return {'run_id': rid, 'state': row['state'], 'behavior': 'clarify', 'answer': '', 'citations': [],
                    'candidates': row.get('candidates', [])}
        if row['state'] != 'completed':
            # 不自动新建run重付费，保留持久账本供恢复/明确重试。
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
                            citations.append({'document_sha256': source['original_sha256'], 'page': ref['page'], 'asset_sha256': asset['sha256']})
        return {'run_id': rid, 'state': row['state'], 'behavior': 'answer' if citations else 'insufficient',
                'answer': row['answer'], 'citations': citations,
                'behavior_notice': '行为为协议与证据的保守辅助判定；部分回答/比较须人工复核'}
