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
        return HostEmbedder(input_type='query')(texts)
    with model_lock:
        from app.lm.embedding_utils import generate_embeddings
        from app.infrastructure.providers.clients import local_call
        return local_call('embedding', lambda: generate_embeddings(texts,input_type='query'))


def rerank(question, docs):
    if not docs:
        return []
    with model_lock:
        from app.lm.reranker_utils import compute_rerank_scores
        from app.infrastructure.providers.clients import local_call
        # 标题是证据对象范围，供重排区分机身/配件；不改写原正文、来源或评分含义。
        def passage(doc):
            title=doc.get('title') or '/'.join(doc.get('metadata',{}).get('heading_path',[]))
            return ('章节：'+title+'\n' if title else '')+doc['text']
        scores = local_call('rerank', lambda: compute_rerank_scores([[question, passage(d)] for d in docs], normalize=True))
    from app.infrastructure.providers.policy import ProviderFailure
    import math
    if isinstance(scores, (int, float)):
        scores = [scores]
    try:
        if len(scores) != len(docs) or not all(math.isfinite(float(s)) for s in scores):
            raise ValueError()
        return sorted([d | {'score': float(s)} for d, s in zip(docs, scores)], key=lambda d: d['score'], reverse=True)
    except (ValueError, TypeError):
        raise ProviderFailure('provider_invalid_response') from None


class QueryRunner:
    def __init__(self, repo, commands, knowledge, *, identity_store=None, embedder=encode, ranker=rerank, llm_factory=None, retrieval_policy=None, expansion_policy=None, answer_budget=None, enhancement_policy=None, source_prerequisites=None, retrieval_combination=None,evidence_attribution=None):
        self.repo, self.commands, self.events, self.knowledge = repo, commands, commands.events, knowledge
        self.identity_store, self.embedder, self.ranker, self.llm_factory = identity_store, embedder, ranker, llm_factory
        from app.retrieval.search import RetrievalPolicy
        self.retrieval_policy = RetrievalPolicy.load() if retrieval_policy is None else RetrievalPolicy.model_validate(retrieval_policy)
        from app.retrieval.expansion import ExpansionPolicy
        self.expansion_policy = ExpansionPolicy.load() if expansion_policy is None else ExpansionPolicy.model_validate(expansion_policy)
        from app.answering.service import AnswerBudget
        self.answer_budget=AnswerBudget.load() if answer_budget is None else AnswerBudget.model_validate(answer_budget)
        from app.retrieval.routing import EnhancementPolicy
        self.enhancement_policy=EnhancementPolicy.load() if enhancement_policy is None else EnhancementPolicy.model_validate(enhancement_policy)
        from app.retrieval.prerequisites import SourcePrerequisitePolicy
        self.source_prerequisites=SourcePrerequisitePolicy.model_validate({} if source_prerequisites is None else source_prerequisites)
        from app.retrieval.combination import CombinationPolicy
        self.retrieval_combination=CombinationPolicy.model_validate({} if retrieval_combination is None else retrieval_combination)
        from app.answering.evidence_attribution import EvidenceAttributionPolicy
        self.evidence_attribution=EvidenceAttributionPolicy.model_validate({} if evidence_attribution is None else evidence_attribution)
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='持久问答')
        self.futures, self.lock, self.stopping = {}, threading.Lock(), threading.Event()
        self.capture_evaluation = False
        self.evaluation_revisions = None

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
        from app.runs.telemetry import ProviderTelemetry, ObservedClient
        telemetry = ProviderTelemetry()
        def emit(kind, payload, **kwargs):
            boundary()
            return self.events.emit(user, rid, kind, payload, expected_token=token, expected_states={'running'}, **kwargs)
        buffer = DeltaBuffer(lambda kind, payload: emit(kind, payload))
        try:
            boundary()
            from app.retrieval.prerequisites import validate_run_policy
            source_policy=validate_run_policy(row,self.source_prerequisites)
            from app.retrieval.combination import validate_run_combination,validate_policies
            combination=validate_run_combination(row,self.retrieval_combination)
            from app.answering.evidence_attribution import validate_run_attribution
            attribution=validate_run_attribution(row,self.evidence_attribution)
            if attribution.enabled and (not combination.enabled or attribution.scope!=combination.scope or
                    attribution.corpus_snapshot_sha256!=combination.corpus_snapshot_sha256):
                raise ValueError('证据归属与组合授权范围不一致')
            from app.retrieval.expansion import ExpansionPolicy
            from app.retrieval.routing import EnhancementPolicy
            from app.retrieval.search import RetrievalPolicy
            validate_policies(combination,RetrievalPolicy.model_validate(self.retrieval_policy),source_policy,
                ExpansionPolicy.model_validate(self.expansion_policy),EnhancementPolicy.model_validate(self.enhancement_policy))
            # 两种扩展不能隐式拼接预算或丢组；本次只授权weighted隔离路径。
            if source_policy.enabled and (self.expansion_policy.enabled if hasattr(self.expansion_policy,'enabled') else self.expansion_policy.get('enabled',False)):
                raise ValueError('来源前提与可选邻接扩展不能同时启用')
            from app.retrieval.search import RetrievalPolicy
            if source_policy.enabled:
                frozen_retrieval=RetrievalPolicy.model_validate(self.retrieval_policy)
                if frozen_retrieval.model_copy(update={'exclude_image_descriptions':False,'query_projection':'original','comparison_context':'global'})!=RetrievalPolicy():
                    raise ValueError('来源前提本轮固定weighted及原检索预算')
            g = self.knowledge()
            if source_policy.enabled and g.db.name!=source_policy.scope.database:
                raise ValueError('来源前提只允许显式隔离命名空间')
            current = self.repo.get(user, rid)
            stage = 'product'
            selected = list(current['product_snapshot']['product_ids'])
            ids = g.product_kbs.distinct('product_id', {'owner_id': g.owner_id, 'kb_id': row['kb_id']})
            products = list(g.products.collection.find({'owner_id': g.owner_id, 'product_id': {'$in': ids}}))
            for pid in selected:
                g.product(user, pid, row['kb_id'])
            from app.retrieval.query_planner import plan_query
            from app.support.commands import product_context, subject_withdrawn
            support_ids = product_context(current.get('support_snapshot'), products)
            withdrawn_subject = subject_withdrawn(current.get('support_snapshot'))
            plan_messages = self._recent_messages(user, current)
            planning_question = row['question']
            context_reset = False
            if withdrawn_subject and not current.get('resumed_at'):
                # 设备主体已被用户撤回；旧助手快照不能参与本轮主体判断。
                # 显式product_ids来自本轮选择器，保留它交由计划器确认；没有显式
                # 型号时清空隐式选择，交由计划器返回澄清。
                plan_messages = []
                context_reset = True
                if not current.get('requested_product_ids'):
                    selected = []
            elif support_ids is not None and not current.get('requested_product_ids'):
                # 显式用户纠正构成新的主体边界，不用旧助手型号将其覆盖。
                selected = list(support_ids)
                plan_messages = []
                if not support_ids:
                    planning_question = '型号：' + current['support_snapshot']['slots']['device']['value'] + '\n' + row['question']
            plan = plan_query(planning_question, products, selected_ids=selected,
                requested_ids=current.get('requested_product_ids', current['input_product_snapshot']['product_ids']),
                messages=plan_messages, confirmed=bool(current.get('resumed_at')), context_reset=context_reset,
                candidate_search=self._product_candidates)
            plan = plan.model_copy(update={'original_query': row['question']})
            emit('stage.changed', {'stage': 'product', 'reason': plan.reason}, fields={'query_plan': plan.model_dump(mode='json')})
            if plan.route == 'clarify':
                if len(plan.candidates) > 50:
                    raise APIError(422, 'product_selection_required', '请先在产品目录选择型号。')
                self.commands.wait_input(user, rid, token, candidates=[{k: p[k] for k in ('product_id', 'model')}
                    for p in products if p['product_id'] in plan.candidates],
                    resume_point={'stage': 'retrieve', 'reason': plan.reason}, telemetry_measurements=telemetry.snapshot())
                return
            selected = list(plan.product_ids)
            for pid in selected:
                g.product(user, pid, row['kb_id'])
            product_snapshot = copy.deepcopy(current['product_snapshot']) | {'product_ids': selected, 'context_route': plan.route}
            emit('stage.changed', {'stage': 'retrieve'}, fields={'stage': 'retrieve', 'product_snapshot': product_snapshot})
            stage = 'retrieve'
            repo = g.repo(row['kb_id'])
            revisions = repo.get_active_revisions()
            # 仅由隔离评测适配器在完整校验validated候选后授予，不修改线上活动指针。
            if self.capture_evaluation and self.evaluation_revisions is not None:
                revisions = copy.deepcopy(self.evaluation_revisions)
            emit('stage.changed', {'stage': stage, 'revision_count': len(revisions)}, fields={'revision_snapshot': revisions})
            from app.retrieval.adapters import from_index_hits, stable_key
            from app.retrieval.models import EvidencePack
            from app.retrieval.search import RetrievalPolicy, retrieve
            policy = RetrievalPolicy.model_validate(self.retrieval_policy)
            plan = plan.model_copy(update={'revision_ids': tuple(r['active_revision_id'] for r in revisions)})
            if policy.query_projection == 'scoped_subject_v1':
                from app.retrieval.query_projection import project_scoped_subject
                plan = project_scoped_subject(plan, products)
            if source_policy.enabled:
                from app.retrieval.prerequisites import validate_scope
                validate_scope(source_policy,owner_id=repo.owner_id,kb_id=repo.kb_id,revisions=revisions,product_ids=selected)
            combination=self.authorize_combination(g,user,repo,plan,revisions,combination)
            from app.answering.evidence_attribution import authorize
            authorize(attribution,repo=repo,products=products,revisions=revisions,product_ids=selected,
                database=g.db.name,collection=g.index_factory().collection if attribution.enabled else '')
            from app.lm.runtime import ModelRuntimePolicy
            from app.retrieval.cache import QUERY_EMBEDDINGS,configured_model_identity
            runtime_policy=ModelRuntimePolicy.load()
            cache_scope=dict(user_id=user.user_id,permissions=dict(role=user.role,kbs=sorted(user.kb_ids)),
                owner_id=g.owner_id,kb_id=row['kb_id'],products=sorted(plan.product_ids),
                revisions=sorted((r['document_id'],r['active_revision_id']) for r in revisions),
                model=configured_model_identity(),strategy=dict(retrieval=policy.model_dump(),plan=plan.model_dump(mode='json')))
            if combination.enabled:
                cache_scope["strategy"]["retrieval_combination"]=combination.model_dump(mode="json")
            scoped_embedder=lambda texts:QUERY_EMBEDDINGS.get_or_compute(cache_scope,texts,self.embedder,runtime_policy)
            from app.retrieval.graph import run_retrieval_graph
            from app.retrieval.routing import EnhancementPolicy
            enhancement_policy=EnhancementPolicy.model_validate(self.enhancement_policy)
            def hyde(query,enhancement):
                from app.core.load_prompt import load_prompt
                from app.lm.lm_utils import get_llm_client
                from app.infrastructure.providers.clients import output_limit_options
                client=ObservedClient(self.llm_factory() if self.llm_factory else get_llm_client(), telemetry)
                result=client.invoke(load_prompt('hyde_prompt',rewritten_query=query),
                    timeout=enhancement.timeout_seconds,**output_limit_options(client,enhancement.hyde_output_tokens,self.answer_budget.output_token_field))
                return result.content
            graph_result=run_retrieval_graph(plan,lambda branch:retrieve(g.index(),repo,branch,
                embedder=scoped_embedder,revision_snapshot=revisions,policy=policy,combination=combination),
                policy=enhancement_policy,hyde=hyde,boundary=boundary)
            hits=graph_result.hits
            emit('stage.changed',{'stage':stage},fields={'retrieval_branches':graph_result.branches,
                'enhancement_policy':enhancement_policy.model_dump(),'retrieval_merge_count':graph_result.merge_count})
            candidates = from_index_hits(hits)
            retrieved_candidates = list(candidates)
            pack = EvidencePack(plan=plan, candidates=candidates)
            docs = []
            for hit in candidates:
                entity = hit.document()
                if entity['revision_id'] not in {r['active_revision_id'] for r in revisions}:
                    raise ValueError('检索结果超出冻结修订范围')
                g.revision(user, entity['document_id'], entity['revision_id'])
                metadata = entity.get('metadata', {})
                docs.append(entity | {'chunk_id': entity['chunk_uid'], 'source': 'local',
                    'title': '/'.join(metadata.get('heading_path', [])), 'asset_ids': metadata.get('asset_ids', []),
                    'source_refs': metadata.get('source_refs', [])})
            stage = 'rerank'
            emit('stage.changed', {'stage': stage}, fields={'stage': stage, 'retrieval_trace': pack.trace(),
                'query_plan': plan.model_dump(mode='json'), 'retrieval_policy': policy.model_dump(), 'model_runtime':runtime_policy.model_dump()})
            from app.retrieval.rerank import rank_hits
            ranked = rank_hits(row['question'], candidates, ranker=self.ranker, policy=policy)
            pack = EvidencePack(plan=plan, candidates=candidates, reranked=ranked)
            expansion_policy = ExpansionPolicy.model_validate(self.expansion_policy)
            context_seeds,combination_trace=self.context_seeds(ranked,candidates,plan,combination)
            if combination.enabled:
                emit('stage.changed',{'stage':stage},fields={'retrieval_combination_execution':combination_trace})
            expansion = self.select_evidence(g,user,repo,context_seeds,revisions,selected,source_policy)
            for hit in expansion.expanded:
                g.revision(user,hit.document_id,hit.revision_id)
                if hit.identity not in {h.identity for h in candidates}:candidates.append(hit)
            docs = [h.document() for h in expansion.selected]
            stage = 'answer'
            from app.query_process.agent.nodes.node_answer_output import step_3_generate_response
            state,prompt=self.evidence_prompt(row['question'],docs,expansion.groups,plan,
                item_names=[p['model'] for p in products if p['product_id'] in selected],
                history=self._history(user,current),session_id=rid)
            used = {d['chunk_id'] for d in state['prompt_used_docs']}
            used_keys = {stable_key(d) for d in state['prompt_used_docs']}
            pack = EvidencePack(plan=plan, candidates=candidates, reranked=ranked,
                expanded=expansion.expanded, selected=[h for h in expansion.selected if h.identity in used_keys])
            citations = []
            original_docs={stable_key(d):d for d in docs}
            for selected_doc in state['prompt_used_docs']:
                d=original_docs[stable_key(selected_doc)]
                if d['chunk_id'] in used:
                    citations.append({k: copy.deepcopy(d[k]) for k in ('chunk_uid', 'document_id', 'revision_id', 'text', 'asset_ids', 'source_refs')} |
                        {'citation_id': stable_id('citation', rid, [d['chunk_uid']])})
            from app.answering.citations import validate_citation_sources, CitationGuard
            def asset_lookup(aid):
                return (g.db.knowledge_assets.find_one({'asset_id':aid}) or
                    g.db.knowledge_legacy_assets.find_one({'asset_id':aid}))
            validate_citation_sources(citations,revisions,asset_lookup=asset_lookup)
            from app.answering.image_selection import select_answer_images
            citations = select_answer_images('', citations)
            covered={pid for d in state['prompt_used_docs'] for pid in d.get('metadata',{}).get('product_ids',[])}
            missing_models=[p['model'] for p in products if p['product_id'] in plan.product_ids and p['product_id'] not in covered] if plan.route=='compare' else []
            evaluation_fields = {}
            if attribution.enabled:
                evaluation_fields['prompt_reference_map']=copy.deepcopy(state['prompt_reference_map'])
            if self.capture_evaluation:
                # 仅评测运行保存候选来源，不复制检索正文或标准答案。
                evaluation_fields['evaluation_candidates'] = {name: [
                    {'document_id': hit.document_id, 'revision_id': hit.revision_id,
                     'chunk_uid': hit.chunk_uid, 'metadata': {
                         'source_refs': copy.deepcopy(hit.metadata.get('source_refs', [])),
                         'asset_ids': list(hit.metadata.get('asset_ids', []))}}
                    for hit in group] for name, group in (
                        ('candidates', retrieved_candidates), ('reranked', ranked), ('context', pack.selected))}
            emit('citation.selected', {'citations': citations}, fields=evaluation_fields | {'citations': citations, 'stage': stage,
                'retrieval_trace': pack.trace(), 'expansion_policy': expansion_policy.model_dump(),
                'expansion_excluded': expansion.excluded, 'evidence_groups': expansion.groups,
                'source_prerequisites_execution': source_policy.model_dump(mode='json'),
                'source_prerequisites_excluded': expansion.excluded if source_policy.enabled else [],
                'prompt_budget':state['prompt_budget'], 'missing_evidence_models':missing_models,
                'answer_support':'insufficient' if not used else 'partial_scope' if missing_models else
                    'partial_context' if state['prompt_budget']['omitted_documents'] else 'evidence_available'})
            from app.utils.sse_utils import run_event_sink
            from app.runs.answer_filter import AnswerFilter
            safe_answer = AnswerFilter({aid for c in citations for aid in c['asset_ids']}, buffer.add)
            citation_guard=CitationGuard(range(1,len(citations)+1),safe_answer.write)
            def sink(sid, kind, payload):
                boundary()
                if kind == 'delta':
                    citation_guard.write(payload['delta'])
                elif kind == 'progress':
                    emit('stage.changed', {'stage': stage})
            binding = run_event_sink.set(sink)
            try:
                if used:
                    if self.llm_factory:
                        client = ObservedClient(self.llm_factory(), telemetry)
                    else:
                        from app.lm.lm_utils import get_llm_client
                        client = ObservedClient(get_llm_client(), telemetry)
                    step_3_generate_response(state, prompt, client=client)
                else:
                    state['answer'] = '当前授权知识库中没有找到可用证据，请补充资料或明确设备型号。'
                    safe_answer.write(state['answer'])
            finally:
                run_event_sink.reset(binding)
            citation_guard.write('', final=True)
            if state.get('output_truncated'):
                safe_answer.write('\n\n（回答达到输出长度上限，以上为部分内容，可继续追问。）')
            safe_answer.write('', final=True)
            buffer.flush()
            boundary()
            answer = safe_answer.answer
            if not answer.strip():
                raise ValueError('模型没有生成有效答案')
            citations = select_answer_images(answer, citations)
            completion = {'text': answer, 'citations': citations, 'product_snapshot': product_snapshot}
            self.commands.finish(user, rid, token, 'completed', {'answer': answer, 'citations': citations, 'message_id': row['assistant_message_id']},
                fields={'answer': answer, 'citations': citations, 'stage': 'completed', 'completion_snapshot': completion,
                    'output_truncated':bool(state.get('output_truncated'))} |
                    ({'answer_support':'partial_output'} if state.get('output_truncated') else {}) |
                    {'telemetry_measurements': telemetry.snapshot()})
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
                    retryable = None
                    if not isinstance(cause, APIError):
                        from app.infrastructure.providers.policy import classify
                        classified, retryable = classify(cause)
                        if classified != 'provider_unknown_error': code = classified
                    if code != 'authorization_revoked':
                        buffer.flush()
                    error = {'code': code, 'stage': stage}
                    if retryable is not None and code != 'query_execution_failed':
                        error['retryable'] = retryable
                    self.commands.finish(user, rid, token, 'failed', {'error': error}, fields={'error': error, 'stage': stage,
                        'telemetry_measurements': telemetry.snapshot()})
            except Exception:
                # 存储/租约失败不伪造终态，保留账本供恢复扫描。
                logging.getLogger(__name__).error('问答终态暂未收敛，阶段：%s', stage)
        finally:
            done.set()
            thread.join(timeout=2)

    def authorize_combination(self,g,user,repo,plan,revisions,combination=None):
        """在编码/索引读取前校验授权，随后重新核对术语及已审出处载荷。"""
        from app.retrieval.combination import CombinationPolicy,authorize_combination
        policy=CombinationPolicy.model_validate(self.retrieval_combination if combination is None else combination)
        if not policy.enabled:return policy
        # 先验证范围，随后才创建索引并读取正文；不使用目标库充当控制账本。
        from app.retrieval.prerequisites import validate_scope
        validate_scope(policy,owner_id=repo.owner_id,kb_id=repo.kb_id,revisions=revisions,product_ids=plan.product_ids)
        if g.db.name!=policy.scope.database:raise ValueError('组合数据库越界')
        for did,rid in policy.scope.revisions.items():g.revision(user,did,rid)
        for pid in policy.scope.product_ids:g.product(user,pid,repo.kb_id)
        index=g.index()
        def rows():
            result=[]
            for did,rid in sorted(policy.scope.revisions.items()):
                result.extend(index.revision_rows(repo,rid,max_rows=1000-len(result)))
                if len(result)>1000:raise ValueError('组合语料超过读取预算')
            return result
        return authorize_combination(policy,loader=rows,owner_id=repo.owner_id,kb_id=repo.kb_id,
            database=g.db.name,collection=index.collection,revisions=revisions,product_ids=plan.product_ids)

    def context_seeds(self,ranked,candidates,plan,combination=None):
        """正式Run与禁推理回放共用，不另建比较选择分支。"""
        from app.retrieval.combination import CombinationPolicy,payload
        from app.knowledge.repository import fingerprint
        from app.retrieval.search import RetrievalPolicy
        policy=RetrievalPolicy.model_validate(self.retrieval_policy)
        combo=CombinationPolicy.model_validate(self.retrieval_combination if combination is None else combination)
        if combo.enabled:
            from app.retrieval.compare_context import select_compare_branch_context
            choice=select_compare_branch_context(ranked,candidates=candidates,plan=plan,limit=policy.context_limit)
            return choice.selected,dict(policy_sha256=fingerprint(payload(combo)),applied=choice.applied,
                protected=choice.protected,missing_heads=choice.missing_heads)
        from app.retrieval.selection import select_context
        return select_context(ranked,limit=policy.context_limit,
            scope_groups=plan.scope_groups if plan.route=='compare' else (),mode=policy.comparison_context),{}

    def evidence_prompt(self,question,docs,groups,plan,*,item_names,history,session_id):
        """共享正式prompt消费者；不生成答案，不改变调用方的主体/历史。"""
        from app.knowledge.citation_api import controlled_markdown
        from app.query_process.agent.nodes.node_answer_output import step_2_construct_prompt
        state=dict(session_id=session_id,is_stream=True,original_query=question,item_names=item_names,
            reranked_docs=[d|{'text':controlled_markdown(d['text'],set(d['asset_ids']))} for d in docs],
            history=history,answer_budget=self.answer_budget,evidence_groups=groups)
        from app.answering.evidence_attribution import EvidenceAttributionPolicy
        attribution=EvidenceAttributionPolicy.model_validate(getattr(self,'evidence_attribution',None) or {})
        if attribution.enabled:
            state['evidence_attribution']=attribution.model_dump(mode='json')
        if plan.route=='compare':
            state['evidence_scope_note']='比较只能依据本轮参考内容，未提供某型号证据时必须明确资料不足，不得推断其参数。'
        return state,step_2_construct_prompt(state)

    def select_evidence(self,g,user,repo,seeds,revisions,product_ids,source_policy=None):
        """正式消费者共用选择边界；回放直接调用此入口，不另建一套选择逻辑。"""
        from app.retrieval.prerequisites import SourcePrerequisitePolicy,authorized_source_selection
        from app.retrieval.expansion import ExpansionPolicy,expand_evidence
        source_policy=SourcePrerequisitePolicy.model_validate(self.source_prerequisites if source_policy is None else source_policy)
        expansion_policy=ExpansionPolicy.model_validate(self.expansion_policy)
        if source_policy.enabled:
            if expansion_policy.enabled:raise ValueError('来源前提与可选扩展不能同时启用')
            if g.db.name!=source_policy.scope.database:raise ValueError('来源前提只允许冻结隔离命名空间')
            for did,rid in source_policy.scope.revisions.items():g.revision(user,did,rid)
            for pid in product_ids:g.product(user,pid,repo.kb_id)
            index=g.index()
            if getattr(index,'collection',None)!=source_policy.scope.collection:
                raise ValueError('来源前提索引必须等于冻结隔离集合')
            result=authorized_source_selection(seeds,loader=lambda **kw:index.prerequisite_rows(repo,**kw),
                policy=source_policy,owner_id=repo.owner_id,kb_id=repo.kb_id,revisions=revisions,product_ids=product_ids)
            for h in result.expanded:g.revision(user,h.document_id,h.revision_id)
            return result
        return expand_evidence(seeds,loader=lambda seeds,**kw:g.index().related_rows(repo,seeds,**kw),
            owner_id=repo.owner_id,kb_id=repo.kb_id,policy=expansion_policy)

    def _recent_messages(self, user, current):
        # 只取当前会话最近已持久消息；不读取旧课程history。
        rows = list(self.repo.conversations.messages.find({'conversation_id': current['conversation_id'],
            'owner_id': user.user_id, 'run_id': {'$ne': current['run_id']}}).sort('ordinal', -1).limit(30))
        return list(reversed(rows))

    def _history(self, user, current):
        from app.conversations.context import support_history
        return [{'role': r['role'], 'text': r['text']} for r in self._recent_messages(user, current)] + support_history(current.get('support_snapshot'))

    def _product_candidates(self, question, products):
        """目录相似度仅排序澄清候选，精确命中不调用本机编码。"""
        if len(products) > 50:
            return [p['product_id'] for p in products]
        try:
            import math
            labels = [(p['model'] + ' ' + ' '.join(p.get('aliases', [])[:3]))[:1000] for p in products]
            vectors = self.embedder([question, *labels])['dense']
            if len(vectors) != len(products) + 1:
                raise ValueError('目录向量数量不符')
            query = vectors[0]
            norm = lambda v: math.sqrt(sum(float(x)**2 for x in v))
            qnorm = norm(query)
            if not qnorm: raise ValueError('目录查询向量为空')
            scored = []
            for product, vector in zip(products, vectors[1:]):
                if len(vector) != len(query) or not norm(vector): raise ValueError('目录向量不兼容')
                score = sum(float(a)*float(b) for a, b in zip(query, vector)) / (qnorm * norm(vector))
                if not math.isfinite(score): raise ValueError('目录相似度非法')
                scored.append((score, product['product_id']))
            return [pid for _, pid in sorted(scored, key=lambda r: (-r[0], r[1]))[:3]]
        except Exception as exc:
            logging.getLogger(__name__).warning('目录候选向量不可用，保留待确认目录，异常类型：%s', type(exc).__name__)
            return [p['product_id'] for p in products]
