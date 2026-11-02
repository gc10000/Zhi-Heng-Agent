# M6来源约束比较回答 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在默认关闭的M6比较路径中，用冻结来源帧选择、保守程序分类、同层比较和确定性中文渲染，为用户生成完整且逐句有据的比较答复。

**Architecture:** 查询规划器将用户明确要求的比较方面放入`QueryPlan`；仅在新内部策略启用时将该字段写入运行身份，旧路径的序列化与缓存身份保持原样。模型只能选择已冻结来源帧，程序重新派生帧事实、分类比较结果并渲染最终答复；任何不能依合同分类或比较的情况都给出有引用的澄清／证据不足，不回退自由文本。

**Tech Stack:** Python 3.12、Pydantic v2、pytest、现有 LangGraph 查询节点、Mongo隔离集成测试。

**Spec:** `docs/superpowers/specs/2026-11-02-m6-comparison-answer-design.md`

## Global Constraints

- 新比较策略默认关闭，并要求冻结`EvidenceAttributionPolicy`及启用的`source_relations`。
- 模型输出只能是版本化帧编号选择JSON；模型不得生成事实字段、分类、比较结论或面向用户的自由文本。
- 证据不足与协议完整性失败必须分开处理；不得静默回退`assertion_binding_v1`摘录或旧自由文本路径。
- 新字段缺省时保持旧Run、旧缓存、旧execution identity及公开API序列化不变。
- 本计划执行只允许离线测试和隔离合成Mongo测试；模型/供应商调用、真实业务库写入、正式答案Run、质量记录均为0。
- 不恢复43题、不运行heldout、不创建候选或proof、不启动M7；M6保持5/7，04保持验收，05/08保持未验收。
- 未经后续独立技术复核及新的明确授权，不执行048真实验证。

---

## File Map

- `app/retrieval/models.py`：给`QueryPlan`增加可选比较目标，默认排除在旧序列化之外。
- `app/retrieval/query_planner.py`：只从用户原问题的唯一显式比较术语解析目标；不从检索结果或答案反推。
- `app/answering/evidence_attribution.py`：在现有冻结来源策略内增加可选、默认关闭的比较策略；启用时强制冻结载荷与`source_relations`。
- `app/answering/comparison_answers.py`：构建帧目录、校验模型帧选择、按固定规则派生事实、比较和渲染；保存版本化证明。
- `prompts/answer_comparison_v1.prompt`：只要求严格选择帧编号的内部提示。
- `app/query_process/agent/state.py`：声明比较proof和受控失败状态。
- `app/query_process/agent/nodes/node_answer_output.py`：按策略选择新路径，缓冲结构输出，避免向客户端泄漏；旧路径保持不变。
- `app/runs/query_runner.py`：绑定新策略、显式比较目标和proof；缺少必要证据时生成程序不足答复，不调用模型。
- `app/evaluation/execution_identity.py`、`app/evaluation/query_adapter.py`、`app/evaluation/repository.py`：保存、恢复、投影和验证新proof，不改变公开Run快照。
- `tests/unit/test_query_plans.py`：查询目标识别和旧计划兼容。
- `tests/unit/test_comparison_answers.py`：JSON协议、冻结帧来源、分类、比较、答案与proof。
- `tests/integration/test_comparison_answer_wiring.py`：Run/答案节点的调用、失败、恢复和旧路径接线。
- `tests/integration/test_comparison_answer_persistence.py`：同库与分库Run/outcome、恢复和失败证明持久化。

## Task 1: Resolve the Requested Comparison Target

**Files:**
- Modify: `app/retrieval/models.py`
- Modify: `app/retrieval/query_planner.py`
- Test: `tests/unit/test_query_plans.py`

**Interfaces:**
- `QueryPlan.comparison_target` is `device_uplink` or `None` in this version.
- `QueryPlan.comparison_target_reason` is one of `explicit_single_target`, `ambiguous_targets`, `unsupported_or_missing_target`, or `not_comparison`.
- `serialize_query_plan(plan, include_comparison=False)` returns the legacy dump unless explicitly asked to include the new target fields.

- [ ] **Step 1: Add failing planner tests**

```python
def test_explicit_uplink_comparison_has_structured_target():
    products = [{'product_id': 'la', 'model': 'LA2608', 'aliases': []},
                {'product_id': 'cb', 'model': 'CB304n', 'aliases': []}]
    plan = plan_query('比较LA2608与CB304n的上联方式是否相同', products)
    assert plan.route == 'compare'
    assert plan.comparison_target == 'device_uplink'
    assert plan.comparison_target_reason == 'explicit_single_target'


def test_ambiguous_or_unsupported_comparison_target_is_not_guessed():
    products = [{'product_id': 'la', 'model': 'LA2608', 'aliases': []},
                {'product_id': 'cb', 'model': 'CB304n', 'aliases': []}]
    plan = plan_query('比较LA2608与CB304n的客户端访问和上联方式', products)
    assert plan.route == 'compare'
    assert plan.comparison_target is None
    assert plan.comparison_target_reason == 'ambiguous_targets'
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_query_plans.py -q --tb=short`

Expected: the new fields and explicit-target parsing are absent.

- [ ] **Step 3: Implement deterministic target extraction**

Add `_comparison_target(question, route)` in `query_planner.py`. Detect `device_uplink` from `上联方式|上联链路|uplink`, `client_access` from `客户端访问|用户访问|访问方式`, `management_link` from `管理连接|管理链路|management link`, and `diagnostic_check` from `排障检查|物理检查|检查条件`. In this version only a single `device_uplink` target resolves; one single unsupported target returns `unsupported_or_missing_target`, multiple distinct targets return `ambiguous_targets`, and no marker returns `unsupported_or_missing_target`. Do not infer from product names, retrieved documents, or conversation history. Run target resolution only when `route == 'compare'`.

Declare the two `QueryPlan` fields with `exclude=True`, then implement `serialize_query_plan`. Its default result must equal the old `QueryPlan.model_dump(mode='json')` shape after removing only the newly added excluded fields; with `include_comparison=True`, append both comparison fields. Use it only for the new policy's query-plan persistence and cache identity.

- [ ] **Step 4: Verify target parsing and legacy shape**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_query_plans.py -q --tb=short`

Expected: explicit uplink targets resolve; zero/multiple/unsupported markers remain unresolved; all prior plan-routing tests pass; disabled serialization omits the new fields.

- [ ] **Step 5: Commit the task**

```powershell
git add app/retrieval/models.py app/retrieval/query_planner.py tests/unit/test_query_plans.py
git commit -m "feat(M6): 显式记录比较目标"
```

## Task 2: Select Frozen Frames and Derive Conservative Facts

**Files:**
- Modify: `app/answering/evidence_attribution.py`
- Create: `app/answering/comparison_answers.py`
- Create: `prompts/answer_comparison_v1.prompt`
- Create: `tests/unit/test_comparison_answers.py`

**Interfaces:**
- `ComparisonAnswerPolicy(enabled: bool = False, function_version='comparison_answer_v1')` is an optional child of `EvidenceAttributionPolicy`; `enabled=True` requires enabled frozen source relations.
- `build_frame_catalog(reference_map, docs, attribution)` returns stable frame records identified by `(reference_number, frame_index)` and binds each to its existing source/frame hash.
- `validate_frame_selection(raw_json, catalog)` accepts only `{"schema_version":"comparison_frame_selection_v1","frames":[{"reference":1,"frame":0}]}` with unique in-range integer pairs and no extra fields.
- `derive_facts(selection, catalog, product_ids)` recomputes every fact from the frozen frame and source text; the model cannot submit a category or fact value.
- `classify_frame(frame, clause, product_id, source_product_ids)` returns one source-derived relation category and never reads a model-supplied category.

- [ ] **Step 1: Add failing policy, selection, and classification tests**

```python
from app.answering.comparison_answers import classify_frame


def test_generic_connection_is_not_upgraded_to_uplink():
    frame = {'kind': 'connection', 'direction': 'origin_to_destination',
             'fields': {'origin': {'text': 'CB304n'}, 'medium': {'text': '同轴'},
                        'destination': {'text': '网络'}, 'purpose': None}}
    fact = classify_frame(frame, 'CB304n可以通过同轴连接到网络。', 'cb304n', ['cb304n'])
    assert fact['category'] == 'unknown'


def test_physical_check_stays_conditional_and_is_never_link_success():
    frame = {'kind': 'physical_check', 'direction': 'undirected_check',
             'fields': {'origin': {'text': 'CB304n的LAN口'}, 'medium': {'text': '网线'},
                        'destination': {'text': '路由器'}, 'purpose': None}}
    fact = classify_frame(frame, '请检查CB304n的LAN口网线是否连接，另一端与路由器是否连接。', 'cb304n', ['cb304n'])
    assert fact['category'] == 'diagnostic_check'
    assert fact['operational_status'] == 'unknown'
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_comparison_answers.py -q --tb=short`

Expected: the comparison policy and frame-selection module do not exist.

- [ ] **Step 3: Implement policy, prompt, and source-derived classification**

Create strict Pydantic models with `extra='forbid'`. The required payload shape is `{"schema_version":"comparison_frame_selection_v1","frames":[{"reference":1,"frame":0}]}`. `validate_frame_selection` must reject duplicate JSON keys, free text, unknown fields, boolean/string/float indices, duplicate frame pairs, empty lists, and indices outside the catalog. In `classify_frame`, map `physical_check` only to conditional `diagnostic_check`; map `access`/`login` to `client_access` only when the frame itself names the accessed object; map `service` to `management_link` only when its literal purpose includes `管理` and both endpoints exist; for `connection`, first map to `management_link` when its literal purpose includes `管理` and endpoints exist, otherwise map to `device_uplink` only when the same clause contains literal `上联` or case-insensitive `uplink`, the frame's frozen `source_product_ids` contains exactly the target product unless the clause names the target product explicitly, and medium and destination exist. If a source frame is tagged to multiple products and the clause does not name the target product, its origin remains unknown. A connection clause with negation or a conditional marker is `unknown` in this version. All other frames become `unknown`. Keep each fact tied to one frame; never merge frames.

The prompt lists stable frame identifiers and complete scoped original sentences, requests only the versioned JSON selection shape above, and forbids explanation or user-facing text. It must not ask the model to provide labels or normalized values.

- [ ] **Step 4: Verify selection and category boundaries**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_comparison_answers.py tests/unit/test_source_relations.py tests/unit/test_assertion_binding.py -q --tb=short`

Expected: new frame protocol and classifier cases pass; existing source relation and assertion-binding contracts remain unchanged.

- [ ] **Step 5: Commit the task**

```powershell
git add app/answering/evidence_attribution.py app/answering/comparison_answers.py prompts/answer_comparison_v1.prompt tests/unit/test_comparison_answers.py
git commit -m "feat(M6): 从冻结原句派生比较事实"
```

## Task 3: Compare Only Supported Fields and Render a Complete Answer

**Files:**
- Modify: `app/answering/comparison_answers.py`
- Test: `tests/unit/test_comparison_answers.py`

**Interfaces:**
- `compare_facts(target, product_ids, facts)` returns a strict result with `status` in `same`, `different`, `insufficient_comparison`; per-product facts; compared field; and explicit missing reasons.
- `render_comparison_answer(result, product_labels)` returns user-facing Chinese text with direct conclusion, product-by-product evidence, limits, and citations carried by each derived fact.
- `create_comparison_proof(...)` binds target, policy and implementation versions, prompt-used identity, catalog/selection/facts/result/answer hashes, and cited source identities.

- [ ] **Step 1: Add failing comparison and rendering tests**

```python
def test_missing_uplink_on_one_side_renders_full_insufficient_comparison():
    facts = [
        {'product_id': 'la2608', 'category': 'management_link', 'medium': 'Wi-Fi',
         'summary': '资料记载到无线控制器的管理连接', 'citation': '[1]',
         'source_text': '设备通过无线连接到控制器进行管理。'},
        {'product_id': 'cb304n', 'category': 'client_access', 'medium': '同轴',
         'summary': '资料记载用户访问设备', 'citation': '[2]',
         'source_text': '用户可通过同轴访问CB304n。'},
    ]
    result = compare_facts('device_uplink', ['la2608', 'cb304n'], facts)
    answer = render_comparison_answer(result, {'la2608': 'LA2608', 'cb304n': 'CB304n'})
    assert result.status == 'insufficient_comparison'
    assert '不能据此认定' in answer
    assert 'LA2608' in answer and 'CB304n' in answer
    assert '管理连接' in answer and '客户端访问' in answer
    assert '原文不代替比较' not in answer
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_comparison_answers.py -q --tb=short`

Expected: comparison and complete-answer functions are not implemented.

- [ ] **Step 3: Implement strict comparator and deterministic renderer**

Use this exact versioned `COMPARABLE_VALUES_V1` table and no additional entries: `以太网` and `Ethernet` map to `ethernet`; `同轴` and `coaxial` map to `coaxial`; `光纤` and `fiber` map to `fiber`. Only English values are case-folded and trimmed. Do not infer synonyms at runtime. This version compares only `device_uplink`; both products need independently classified uplink facts and one recognized medium. Equal canonical media yield `same`; distinct canonical media yield `different`; an unrecognized or composite value yields `insufficient_comparison`. A `diagnostic_check`, `client_access`, or `management_link` fact may be described with its source but never enters uplink comparison. A relation category mismatch is a reason for insufficiency, not proof that device capability differs.

Render a direct conclusion first, then one cited sentence per product containing only program-derived facts and complete original citations, then the exact missing target/field or semantic boundary. Use a fixed citation renderer based on the existing citation/source mapping; never interpolate model text outside original evidence.

- [ ] **Step 4: Verify positive, negative, and incomplete comparisons**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_comparison_answers.py -q --tb=short`

Expected: matching known media yield `same`; distinct known media yield `different`; one-sided, mismatched-category, ambiguous, or unknown media yield `insufficient_comparison`; all returned claims cite their own source frame.

- [ ] **Step 5: Commit the task**

```powershell
git add app/answering/comparison_answers.py tests/unit/test_comparison_answers.py
git commit -m "feat(M6): 程序比较并渲染完整答复"
```

## Task 4: Wire the New Path Through Run, Streaming, and Recovery

**Files:**
- Modify: `app/query_process/agent/state.py`
- Modify: `app/query_process/agent/nodes/node_answer_output.py`
- Modify: `app/runs/query_runner.py`
- Modify: `app/evaluation/execution_identity.py`
- Modify: `app/evaluation/query_adapter.py`
- Modify: `app/evaluation/repository.py`
- Create: `tests/integration/test_comparison_answer_wiring.py`
- Create: `tests/integration/test_comparison_answer_persistence.py`

**Interfaces:**
- New policy off or absent calls the existing answer path byte-for-byte with respect to prompt, stream, state, and identity.
- Enabled policy on `route='compare'` and a unique target uses the frame-selection prompt; unresolved target returns a deterministic clarification without model invocation.
- Enabled policy on a resolved target with an empty frame catalog returns a deterministic insufficient-evidence answer without model invocation.
- A valid selection is buffered until proof validation and deterministic rendering complete; streaming sends only the final rendered answer.
- Failed streams persist only bounded selection material and failure metadata, preserve failed/unknown usage settlement, and never create a success outcome.

- [ ] **Step 1: Add failing integration tests**

Cover disabled legacy routing; enabled comparison with a mocked valid frame selection; no-target clarification with zero model calls; empty-catalog insufficiency with zero model calls; malformed/truncated selection with no JSON delta or success outcome; changed frozen source rejected during initial projection and recovery; and the same valid recovery reused without another model call.

- [ ] **Step 2: Run focused integration tests and confirm the new path is absent**

Run: `$env:M1_TEST_DB='m1_test_m6cmp_' + [guid]::NewGuid().ToString('N').Substring(0,6); .\.venv\Scripts\python.exe -m pytest tests/integration/test_comparison_answer_wiring.py tests/integration/test_comparison_answer_persistence.py -q --tb=short`

Expected: new integration modules fail before their implementation is added. The command uses a fresh short database prefix for this run.

- [ ] **Step 3: Integrate conditional strategy and proof persistence**

In `node_answer_output.py`, branch only on the explicit nested policy. Keep the existing prompt/output path unchanged when it is absent or disabled. For the new path, build the frozen frame catalog from the exact prompt-used docs, buffer the selection response, validate it, derive facts, compare, render, create proof, then expose only rendered answer text. Emit bounded failure metadata through the existing failed-Run route.

In `query_runner.py`, serialize comparison target only when the new policy is enabled, include the same fields in checkpoint/cache/execution identity, and persist `comparison_answer` proof alongside the answer. Update evaluation projection and recovery validation to recompute the frozen catalog, selected-frame facts, comparison result, citations, and answer hash before accepting an outcome. Do not add internal selection/facts to public snapshots or event payloads.

- [ ] **Step 4: Run integration, contract, and OpenAPI checks**

Run: `$env:M1_TEST_DB='m1_test_m6cmp_' + [guid]::NewGuid().ToString('N').Substring(0,6); .\.venv\Scripts\python.exe -m pytest tests/integration/test_comparison_answer_wiring.py tests/integration/test_comparison_answer_persistence.py tests/integration/test_query_runs.py tests/integration/test_assertion_binding_wiring.py tests/contract/test_query_run_adapter.py tests/unit/test_prerequisite_contract.py::test_openapi_still_matches_checked_contract -q --tb=short`

Expected: new mode boundaries pass in isolated Mongo; old run contracts and public OpenAPI remain unchanged; no test contacts a model provider.

- [ ] **Step 5: Commit the task**

```powershell
git add app/query_process/agent/state.py app/query_process/agent/nodes/node_answer_output.py app/runs/query_runner.py app/evaluation/execution_identity.py app/evaluation/query_adapter.py app/evaluation/repository.py tests/integration/test_comparison_answer_wiring.py tests/integration/test_comparison_answer_persistence.py
git commit -m "feat(M6): 持久化来源约束比较答复"
```

## Task 5: Run the Zero-Call Matrix and Prepare Independent Review

**Files:**
- Create: `docs/development/reviews/M6-comparison-answer-implementation-r1.md`
- Create: `docs/development/reviews/M6-comparison-answer-validation-r1.json`
- Modify: `docs/development/PROGRESS.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/development/records/M6-comparison-answer-r1.md`

**Interfaces:**
- The implementation report separates code tests, synthetic selection checks, saved-input replay, and claims that remain unproven without a real answer.
- The validation JSON contains only sanitized hashes, test totals, scope, and zero-call/zero-write counters; private prompts, saved inputs, raw selections, and logs remain under a new `output/` directory and are not committed.

- [ ] **Step 1: Run the focused offline test set**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_query_plans.py tests/unit/test_comparison_answers.py tests/unit/test_assertion_binding.py tests/unit/test_source_relations.py tests/contract/test_query_run_adapter.py -q --tb=short`

Expected: all focused tests pass with no skipped database tests in this offline command.

- [ ] **Step 2: Run the preserved-input zero-call replay**

Create a new private directory under `output/` with `$outDir = Join-Path 'output' ('m6-comparison-answer-implementation-' + (Get-Date -Format 'yyyyMMdd-HHmmss')); New-Item -ItemType Directory -Path $outDir -ErrorAction Stop`. Adapt the saved-input replay harness without overwriting any earlier evidence. The replay may assert frame/source identity and deterministic answer structure; all selected frames are synthetic or replayed protocol fixtures, never formal Runs or quality records.

- [ ] **Step 3: Write the implementation report and sanitized validation summary**

Record exact commands and results, all intermediate failures, the R1/R2/R3 recovery boundaries exercised, unchanged legacy contracts, and explicit limits: model frame-selection completeness, semantic coverage outside the fixed classifier, and actual 048 answer quality remain unproven. State zero real calls/writes and retain M6=5/7.

- [ ] **Step 4: Update navigation without changing stage status**

Append the dated implementation handoff to `PROGRESS.md`; add the change to `CHANGELOG.md`; create the task record. Do not check off M6-05/M6-08, create quality proofs, authorize 048, or modify historical reports.

- [ ] **Step 5: Commit and hand off for independent review**

```powershell
git add docs/development/reviews/M6-comparison-answer-implementation-r1.md docs/development/reviews/M6-comparison-answer-validation-r1.json docs/development/PROGRESS.md CHANGELOG.md docs/development/records/M6-comparison-answer-r1.md
git commit -m "docs(M6): 记录比较答复零调用验收"
```

After implementation, the current control agent performs independent technical review. Do not represent implementation self-validation as independent closure.

## Plan Self-Review

- **Spec coverage:** Query target, source-frame-only model protocol, conservative category derivation, same-layer comparison, complete natural-language rendering, proof identity/recovery, failure persistence, legacy compatibility, zero-call validation, and authorization limits each map to a task.
- **Compatibility:** Query target fields are excluded by default and serialized only under the new policy. New policy is optional and nested in the existing frozen attribution contract. Public Run snapshots and OpenAPI remain unchanged.
- **Evidence limits:** Passing synthetic tests proves implementation behavior only. It does not prove model frame-selection completeness, broad semantic coverage, 048 user answer quality, M6-05 feedback proof, or M6-08 candidate quality.
- **Known conservative behavior:** Unknown target, unknown relation, unsupported medium term, or one-sided evidence yields clarification/insufficient comparison. This is an intentional correctness choice, not a new M6 acceptance criterion.
