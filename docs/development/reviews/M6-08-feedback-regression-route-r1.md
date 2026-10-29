# M6-08 regression反馈路径核实与分支状态修正

日期：2026-10-29。核验基线：`9d66bcb829439918d9ef93969c5ad821deb7a514`；开始时HEAD、`origin/main`一致，工作区只有既有未跟踪`tmp/`。本轮新增反馈草稿分支状态修正、前后端回归与脱敏文档；未改旧反馈、旧实验、冻结题集、原始答案、真实评分或默认catalog。M6仍4/7，M6-04/05/08未验收，M7未启动。

## 已有接口与实际断点

实际源码确认现有流程分成两条：

1. `POST /feedback`保存一个待审条目，绑定来源Run和引用；`GET /feedback`及审核入口每次重新核验当前KB授权。`POST /feedback/{id}/review`经维护者审核后，仅在反馈记录内保存confirmed/rejected及草稿。草稿保留feedback、run、kb、资料修订、问题和拟议预期，但`annotation_status`为`draft`，不是标准标签。
2. `kind=revision`可使用`POST /feedback/{id}/bind-revision`绑定staged/validated资料修订和受影响题；`POST /feedback/{id}/quality-proof`验证已校准实验与受影响题/完整dev的有序证明。两接口明确只接受revision草稿。

`kind=regression`没有题目标注审核端点，也没有反馈草稿转JSONL题目/新manifest/目录版本的接口。`revise_label()`只修订已有题目的`expected`或`allowed_evidence`；新题须具备完整Question字段、精确原件证据、dev划分和有效标注来源。题集由本机JSONL与manifest冻结，`EvaluationCatalog`从静态catalog读取受控版本；`POST /eval-sets`只登记已有目录项，不生成新版本。`ExperimentInput`/实验账本没有受支持的`feedback_id`或回归题来源关联，baseline只绑定相同题集版本。故当前不能称为已接通的“真实反馈→标注审阅→版本化dev→反馈后复评”。

若人工或独立助手完成了有效题目标注，当前可执行但仍需维护者离线整理的步骤是：从已审反馈构造完整题目；以新dataset/manifest/config身份冻结且只进入dev；通过`validate_dataset`与catalog校验后登记该版本；对完全相同的冻结题集建立baseline并满足M6-04全题双轮与预校准；之后才可创建同题集同范围candidate并执行复评。任何题目/标签改变都会改变dataset指纹，旧实验不会自动继承到新版本。该路径仍缺少反馈来源在题目/manifest到实验的正式关联和独立的regression复评证明接口；不能用revision的affected/full接口代替。heldout不进入回归流程。

历史材料显示旧单题001的候选创建时间晚于该反馈和校准，但那是旧单题身份；时间先后不建立题目来源关联，也不满足当前85题新规则审阅/全dev门槛。保存材料还将该candidate记录为无human评分、release gate pending。本轮未用运行数据库复核这些历史记录：当前本机缺`M2_DB_NAME`，以`MONGO_DB_NAME`连接虽能ping，但目标集合未找到这些评测记录；不能将该库空查询解释为M6账本无记录。历史报告按其核验时点保留。

## 本轮修正

`review_feedback()`此前给regression与revision新草稿都写入`requires_affected_then_full_regression`。该发布状态只适用于资料修订，构成对regression流程的错误暗示。本轮按草稿类型修正：新regression草稿的`publication_state`为`not_applicable`；revision仍为`requires_affected_then_full_regression`。旧草稿与旧记录不回填或迁移。

`FeedbackQueue.vue`现在按`draft.kind`分别说明当前路线：regression显示标注待审、尚无题集/实验自动接线，并隐藏revision绑定及质量证明表单；revision继续展示资料修订与affected→full流程。回归题的界面提示明确标注流程缺口，不声称当前页面已经能创建版本或复评。

## 四题语义与召回状态

- `m6-g540-04-a`、`05-a`、`05-b`、`17-b`仍是已存答案的对象范围/具名配件表达问题。通用prompt约束及prompt-builder定向测试已存在；没有本轮新答案，约束的实际模型效果仍未知。旧assistant-side判断保留，不改评分身份。
- `support-v1-019/021/022`必要正文在weighted融合候选前未进入（既存稀疏排名分别为7/9/11）；`support-v1-048`的CB304n Cable/EoC正文在双路top-20之外（既存dense 153、sparse 57）。更细召回原因未知。保留weighted与原参数，不启用RRF、不扩top-k或放宽阈值。
- 本轮未生成答案、未运行真实检索、未改检索链路；上述问题仍按既有逐题证据记录，不能由提示词构造或来源指标推断答案质量。

## 验证与边界

本轮在核对现有接续修改后重新执行了相称检查：隔离Mongo/API与契约共8项、离线浏览器2项、TypeScript检查及`git diff --check`均退出0。最新JUnit与Playwright产物分别为`output/m6-feedback-route-r2-backend.xml`和`output/m6-feedback-route-r2-e2e-artifacts/`，仅保存在本机。此重跑未执行正式M6数据库核账或模型评测。

| 命令 | 结果 |
|---|---|
| `pnpm -C frontend exec playwright test feedback-loop.spec.ts --reporter=list --output=../output/m6-feedback-route-r1-red-artifacts` | 修复前1失败/1通过，退出1；regression分支缺少正确路线说明，红测证据保留 |
| `$env:M1_TEST_DB='m1_test_m6_feedback_route_r1_state_red'; .\.venv\Scripts\python.exe -m pytest tests/integration/test_feedback_triage_workflow.py::test_confirm_creates_traceable_draft_only_and_is_idempotent -q --tb=short --junitxml=output/m6-feedback-route-r1-state-red.xml` | 修复前1失败，退出1；回归草稿被赋予revision发布状态 |
| `$env:M1_TEST_DB='m1_test_m6_feedback_route_r1_final'; .\.venv\Scripts\python.exe -m pytest tests/integration/test_feedback_triage_workflow.py tests/contract/test_feedback_triage.py -q --tb=short --junitxml=output/m6-feedback-route-r1-backend-final.xml` | 8 passed，退出0；包括regression/revision状态差异及错误revision/quality-proof路径被拒绝且草稿不变 |
| `pnpm -C frontend exec playwright test feedback-loop.spec.ts --reporter=list --output=../output/m6-feedback-route-r1-final-artifacts` | 2 passed，退出0；覆盖regression提示/无revision表单及revision原绑定路径 |
| `.\.venv\Scripts\python.exe -m pytest tests/unit/test_answer_prompt_scope.py -q --tb=short --junitxml=output/m6-feedback-route-r1-prompt-scope.xml` | 1 passed，退出0；只证明prompt构造保留通用具名配件约束，不证明生成质量 |
| `pnpm -C frontend typecheck` | 退出0 |

测试组有重叠，不合并成唯一总数。集成HTTP仅用显式隔离M1测试库和合成数据。运行Mongo ping及评测集合只读查询未写正式账本；无供应商调用、无答案生成、无真实dev/heldout、无human/观察/校准/candidate写入、无资料导入/发布或默认切换。旧输出和证据未覆盖；新增失败/通过浏览器与JUnit产物保存在本机`output/m6-feedback-route-r1-*`，不提交。

## M6阻塞与下一条执行

| 项目 | 已满足 | 仍缺/责任方 |
|---|---|---|
| M6-04 | 审阅/unknown追加/校准协议实现；001旧单题结果材料保留 | 当前85题的有效human双轮及固定报告人工抽检、基线预校准未满足；正式审核者负责真实声明，执行端不得代填。|
| M6-05 | feedback审核草稿及revision专用发布门禁保留；错误的regression发布状态已修正 | 执行端负责新增的regression题目审核/版本化目录与反馈来源关联/反馈后复评证明接线；随后仍需有效的同题集dev比较。当前实时账本未核实。|
| M6-08 | r3的85条结果身份、19继承+66执行和既有逐题assistant分析保留；本轮分支提示/状态定向自验完成 | 85题正式双轮、预校准、同范围candidate、反馈后复评闭环和固定报告仍缺；heldout未运行。总控独立审查与阶段验收未发生。|

下一条执行由本执行端承担：单独设计并实现有CAS/幂等/权限和完整内容指纹的regression草稿→新dev版本→实验来源关联；不得调用revision发布证明。实现完成后用隔离库验证拒绝/恢复/哈希链，再由总控独立复审。实际模型复评须另先固定请求身份、父结果来源与调用/费用账本，并满足正式质量前置；本轮没有启动。G540生成边界和四题weighted召回仍保持未解决，不用新模型答案或放宽检索配置掩盖。
