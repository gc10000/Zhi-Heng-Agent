"""旧回答能力接持久run；新检索仅访问显式授权v2快照。"""
import copy
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from app.api.errors import APIError
from app.identity.models import Principal
from app.knowledge.models import stable_id
from app.runs.events import DeltaBuffer

model_lock = threading.Lock()


class ExecutionStopped(Exception):
    pass


def encode(texts):
    import os
    if os.getenv('MODEL_HOST_URL') and os.getenv('MODEL_HOST_TOKEN'):
        from app.infrastructure.queue.model_client import HostEmbedder
        return HostEmbedder()(texts)
    with model_lock:
        from app.lm.embedding_utils import generate_embeddings
        return generate_embeddings(texts)


def rerank(question, docs):
    if not docs:
        return []
    with model_lock:
        from app.lm.reranker_utils import get_reranker_model
        scores = get_reranker_model().compute_score([[question, d['text']] for d in docs], normalize=True)
    if isinstance(scores, (int, float)):
        scores = [scores]
    if len(scores) != len(docs):
        raise ValueError('重排数量与证据不一致')
    return sorted([d | {'score': float(s)} for d, s in zip(docs, scores)], key=lambda d: d['score'], reverse=True)[:10]


class QueryRunner:
    def __init__(self, repo, commands, knowledge, *, identity_store=None, embedder=encode, ranker=rerank, llm_factory=None):
        self.repo, self.commands, self.events, self.knowledge = repo, commands, commands.events, knowledge
        self.identity_store, self.embedder, self.ranker, self.llm_factory = identity_store, embedder, ranker, llm_factory
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='持久问答')
        self.futures, self.lock, self.stopping = {}, threading.Lock(), threading.Event()

    def scan(self):
        with self.lock:
            self.futures = {rid: f for rid, f in self.futures.items() if not f.done()}
            if self.stopping.is_set():
                return
            for row in self.repo.runs.find({'state': 'pending', 'claim_state': 'claimed'}).limit(100):
                if len(self.futures) >= 4:
                    break
                if row['run_id'] not in self.futures:
                    self.futures[row['run_id']] = self.pool.submit(self.execute, row['run_id'])

    def close(self):
        self.stopping.set()
        self.pool.shutdown(wait=True, cancel_futures=True)

    def user(self, row):
        if self.identity_store is not None:
            current = self.identity_store.users.find_one({'user_id': row['owner_id'], 'enabled': True})
            if current is None or row['kb_id'] not in current.get('kb_ids', []):
                raise APIError(403, 'authorization_revoked', '运行权限已撤回。')
            return Principal(**{k: current[k] for k in Principal.model_fields})
        return Principal(user_id=row['owner_id'], username='运行执行', role='viewer', kb_ids=(row['kb_id'],))

    def execute(self, rid):
        row = self.repo.runs.find_one({'run_id': rid})
        if row is None:
            return
        # 内部主体仅用于保存撤权失败终态；所有业务IO前仍须校验当前账号。
        user = Principal(user_id=row['owner_id'], username='运行执行', role='viewer', kb_ids=(row['kb_id'],))
        try:
            token = self.commands.start(user, rid)
        except APIError as exc:
            if exc.status == 409:
                return
            raise
        done, lost = threading.Event(), threading.Event()
        stage = 'authorization'
        def boundary():
            if self.stopping.is_set() or lost.is_set():
                raise ExecutionStopped()
            self.user(row)
            if not self.commands.boundary(user, rid, token):
                raise ExecutionStopped()
        def heartbeat():
            while not done.wait(max(.1, self.commands.lease_seconds / 3)):
                try:
                    boundary()
                except Exception:
                    lost.set()
                    return
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        def emit(kind, payload, **kwargs):
            boundary()
            return self.events.emit(user, rid, kind, payload, expected_token=token, expected_states={'running'}, **kwargs)
        buffer = DeltaBuffer(lambda kind, payload: emit(kind, payload))
        try:
            boundary()
            g = self.knowledge()
            current = self.repo.get(user, rid)
            stage = 'product'
            selected = list(current['product_snapshot']['product_ids'])
            ids = g.product_kbs.distinct('product_id', {'owner_id': g.owner_id, 'kb_id': row['kb_id']})
            products = list(g.products.collection.find({'owner_id': g.owner_id, 'product_id': {'$in': ids}}))
            if not selected and len(products) > 1:
                if len(products) > 50:
                    raise APIError(422, 'product_selection_required', '请先在产品目录选择型号。')
                self.commands.wait_input(user, rid, token, candidates=[{k: p[k] for k in ('product_id', 'model')} for p in products],
                                         resume_point={'stage': 'retrieve'})
                return
            if not selected and len(products) == 1:
                selected = [products[0]['product_id']]
            for pid in selected:
                g.product(user, pid, row['kb_id'])
            product_snapshot = copy.deepcopy(current['product_snapshot']) | {'product_ids': selected}
            emit('stage.changed', {'stage': 'retrieve'}, fields={'stage': 'retrieve', 'product_snapshot': product_snapshot})
            stage = 'retrieve'
            repo = g.repo(row['kb_id'])
            revisions = repo.get_active_revisions()
            emit('stage.changed', {'stage': stage, 'revision_count': len(revisions)}, fields={'revision_snapshot': revisions})
            hits = g.index().search(repo, row['question'], embedder=self.embedder, revision_snapshot=revisions, product_ids=selected, limit=20)
            docs = []
            for hit in hits:
                entity = dict(hit.get('entity', hit))
                if entity['revision_id'] not in {r['active_revision_id'] for r in revisions}:
                    raise ValueError('检索结果超出冻结修订范围')
                g.revision(user, entity['document_id'], entity['revision_id'])
                metadata = entity.get('metadata', {})
                docs.append(entity | {'chunk_id': entity['chunk_uid'], 'source': 'local',
                    'title': '/'.join(metadata.get('heading_path', [])), 'asset_ids': metadata.get('asset_ids', []),
                    'source_refs': metadata.get('source_refs', [])})
            stage = 'rerank'
            emit('stage.changed', {'stage': stage}, fields={'stage': stage})
            docs = self.ranker(row['question'], docs)
            stage = 'answer'
            from app.query_process.agent.nodes.node_answer_output import step_2_construct_prompt, step_3_generate_response
            from app.knowledge.citation_api import controlled_markdown
            state = {'session_id': rid, 'is_stream': True, 'original_query': row['question'],
                     'item_names': [p['model'] for p in products if p['product_id'] in selected],
                     'reranked_docs': [d | {'text': controlled_markdown(d['text'], set(d['asset_ids']))} for d in docs],
                     'history': self._history(user, current)}
            prompt = step_2_construct_prompt(state)
            used = {d['chunk_id'] for d in state['prompt_used_docs']}
            citations = []
            for d in docs:
                if d['chunk_id'] in used:
                    citations.append({k: copy.deepcopy(d[k]) for k in ('chunk_uid', 'document_id', 'revision_id', 'text', 'asset_ids', 'source_refs')} |
                        {'citation_id': stable_id('citation', rid, [d['chunk_uid']])})
            emit('citation.selected', {'citations': citations}, fields={'citations': citations, 'stage': stage})
            from app.utils.sse_utils import run_event_sink
            from app.runs.answer_filter import AnswerFilter
            safe_answer = AnswerFilter({aid for c in citations for aid in c['asset_ids']}, buffer.add)
            def sink(sid, kind, payload):
                boundary()
                if kind == 'delta':
                    safe_answer.write(payload['delta'])
                elif kind == 'progress':
                    emit('stage.changed', {'stage': stage})
            binding = run_event_sink.set(sink)
            try:
                if used:
                    client = self.llm_factory() if self.llm_factory else None
                    step_3_generate_response(state, prompt, client=client)
                else:
                    state['answer'] = '当前授权知识库中没有找到可用证据，请补充资料或明确设备型号。'
                    safe_answer.write(state['answer'])
            finally:
                run_event_sink.reset(binding)
            safe_answer.write('', final=True)
            buffer.flush()
            boundary()
            answer = safe_answer.answer
            if not answer.strip():
                raise ValueError('模型没有生成有效答案')
            completion = {'text': answer, 'citations': citations, 'product_snapshot': product_snapshot}
            self.commands.finish(user, rid, token, 'completed', {'answer': answer, 'citations': citations, 'message_id': row['assistant_message_id']},
                fields={'answer': answer, 'citations': citations, 'stage': 'completed', 'completion_snapshot': completion})
            self.repo.conversations.append_message(user, row['conversation_id'], run_id=rid, role='assistant', **completion)
        except ExecutionStopped:
            # 合作取消已由boundary落终态；关机/失联由原租约扫描收敛interrupted。
            pass
        except Exception as exc:
            logging.getLogger(__name__).error('问答执行失败，阶段：%s，异常类型：%s', stage, type(exc).__name__)
            try:
                if self.commands.boundary(user, rid, token):
                    # 旧生成节点会包装事件出口异常；沿原因链保留内部错误码，绝不回显正文。
                    cause = exc
                    while not isinstance(cause, APIError) and cause.__cause__ is not None:
                        cause = cause.__cause__
                    code = cause.code if isinstance(cause, APIError) else 'query_execution_failed'
                    if code != 'authorization_revoked':
                        buffer.flush()
                    error = {'code': code, 'stage': stage}
                    self.commands.finish(user, rid, token, 'failed', {'error': error}, fields={'error': error, 'stage': stage})
            except Exception:
                # 存储/租约失败不伪造终态，保留账本供恢复扫描。
                logging.getLogger(__name__).error('问答终态暂未收敛，阶段：%s', stage)
        finally:
            done.set()
            thread.join(timeout=2)

    def _history(self, user, current):
        # 只取当前会话最近已持久消息；不读取旧课程history。
        rows = list(self.repo.conversations.messages.find({'conversation_id': current['conversation_id'],
            'owner_id': user.user_id, 'run_id': {'$ne': current['run_id']}}).sort('ordinal', -1).limit(30))
        return [{'role': r['role'], 'text': r['text']} for r in reversed(rows)]
