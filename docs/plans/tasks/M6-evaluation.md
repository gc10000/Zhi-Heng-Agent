# M6：评测、质量中心与反馈闭环开发 ToDo

> 执行方式：按任务逐项开发；使用 superpowers:executing-plans 技能。任务中的步骤采用勾选框跟踪；不自行派发子代理。

**目标：**交付“评测、质量中心与反馈闭环”阶段可独立验收的能力。
**架构：**沿现有 Python/FastAPI/LangGraph 链路做小步适配；Vue 3 前端只消费统一 API 与事件契约。保留旧入口与数据直至本阶段验收通过。
**技术栈：**Vue 3 / TypeScript / FastAPI / MongoDB / Milvus / MinIO；具体测试工具与依赖在对应任务中建立。
**设计依据：**[优化方案](../2026-10-22-technical-support-optimization.md)、[接口与数据契约](../DEVELOPMENT_CONTRACTS.md)、[开发总清单](../DEVELOPMENT_TODO.md)。

## 进入条件与执行约束

题集已在 M4 开始；完整工作台依赖 M5-08。

- 以下文件均为**计划创建/修改**，不表示已经存在；执行前用 `rg` 核对真实接口与源码。
- 本阶段遵守总清单中的 Vue 3、中文注释、数据隔离、配置脱敏和完成证据规则。
- 每个代码任务先增加能揭示错误的用例，再做最小实现；文档、样式等低影响变更按实际结果检查，不写镜像测试。
- 每完成一个任务，记录验证命令、输出摘要、涉及文件和遗留问题；验证通过后才勾选[总清单](../DEVELOPMENT_TODO.md)，并更新[进度](../../development/PROGRESS.md)与[变更记录](../../development/CHANGELOG.md)。
- 命令均从项目根目录运行；`pnpm -C frontend` 命令需 M3-01 建立对应 scripts 后才存在。依赖安装和测试数据准备不表示任务验收通过。
- 每个任务验证其直接影响的行为，阶段验收时再执行阶段回归；不要重复运行无关全量测试。

<a id="m6-01"></a>
### M6-01：题集扩充与证据映射

**依赖：**M4-10。
**文件：**本机冻结题集 `evals/datasets/support-v2-r2.jsonl` 与 manifest；`app/evaluation/datasets.py`; `scripts/verification/build_m6_dataset.py`; `scripts/verification/map_m6_dataset_chunks.py`; `tests/unit/test_eval_labels.py`。首个 `r1` 候选保留作修订证据，权威文件名因此使用 `r2`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M6-01.1** 从 50 扩约 150 题，覆盖已见失败/长文/图表/拒答；新增 100 条保持 `source_checked_assistant_draft/draft`，不计入标准真值。
- [x] **M6-01.2** 引用标签基于稳定来源跨度，可映射新切片；127 条文本跨度用真实 PDF 与 M1 `chunk_document` 离线映射通过，3 条图像跨度绑定资产哈希/物理页并完成领域对象投影复验。
- [x] **M6-01.3** 冻结 heldout；`support-v2-draft-r2` 固定 50 条 fresh heldout，使用未进入历史题集的 P5 原件，未运行、不用于调参。
- [x] **M6-01.V** 验证：定向回归 55 项通过；题集 CLI、冻结 manifest 和离线来源映射均通过。
- [x] **M6-01.D** 已保存 `docs/development/records/M6-01.md`，同步总清单、进度、变更、决策、公共契约和标注手册；原件、评测数据和运行证据仍仅本机。

**验收：**不把所有反馈直接当真值；改标签需理由与版本；无法映射的题明确失效而非按错算。

<a id="m6-02"></a>
### M6-02：实验运行器与检索指标

**依赖：**M6-01,M4-02。
**文件：**`app/evaluation/runner.py`; `app/evaluation/metrics.py`; `app/evaluation/validate_dataset.py`; `tests/unit/test_eval_metrics.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M6-02.1** Recall@k/MRR/nDCG 使用允许证据；多组必需、组内替代，无证据/草稿不计标准质量分。
- [x] **M6-02.2** 保存模型/数据/prompt/策略/hash/seed复现身份；seed只作为可复核元数据，不宣称控制所有供应商随机性。
- [x] **M6-02.3** 可按题型、失败阶段、逻辑调用/token与可用精确成本统计；未采集保持null。
- [x] **M6-02.V** 指标契约9项通过；包含M6-01标签门禁的完整评测单元回归134 passed、0 skipped。
- [x] **M6-02.D** 验证记录、总清单、进度、变更/决策、公共指标契约及评测报告说明已同步；未运行heldout/真实Mongo/供应商。

**验收：**合成确定性样例指标算对；真实报告区分命中/答案质量；多证据与无答案题有明确计算规则。

<a id="m6-03"></a>
### M6-03：实验 API、队列与结果对比

**依赖：**M6-02,M2-09。
**文件：**`app/evaluation/api.py`; `app/evaluation/jobs.py`; `frontend/src/features/evaluation/ExperimentsPage.vue`; `tests/contract/test_experiment_access.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M6-03.1** 独立队列/单并发宿主/所有者预算，拒绝与导入队列同名；Linux控制worker复用既有Windows模型宿主。
- [x] **M6-03.2** 前端选择服务端登记版本/配置，按题分页查看来源、答案和同题集基线差异，未知成本/语义分保持未知。
- [x] **M6-03.3** 版本化取消/失败重试，成功题检查点复用，显式失败题新run身份；结果attempt指针CAS保护迟到worker。
- [x] **M6-03.V** 相称后端176 passed（143单元/16契约/17隔离Mongo），前端37单元/3定向浏览器通过；真实API/Redis/Linux/宿主失败门禁7检查通过、模型调用0。
- [x] **M6-03.D** 已保存M6-03记录及全部本机红绿证据，配置、契约/OpenAPI、恢复文档和前端类型已同步。真实成功评测/反馈闭环留M6-08，不将传输失败门禁冒称模型评测成功。

**验收：**普通用户不能访问他人私有题集；线上问答不被评测挤占；无 mock 指标混入真实结果。

<a id="m6-04"></a>
### M6-04：人工审阅与发布质量门槛

**依赖：**M6-03。
**文件：**`app/evaluation/reviews.py`; `frontend/src/features/evaluation/ReviewPage.vue`; `docs/evaluation/release-gates.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M6-04.1** 四维0/1/2、未知和不适用分别持久化，完整结果指纹绑定。
- [x] **M6-04.2** human/assistant/model分开，账号由服务端授予，人工须本人原件核对声明。
- [x] **M6-04.3** 不可变双轮审阅及先基线校准再建候选；越权/型号零容忍、逐题零退化，缺人工/未知待审。
- [ ] **M6-04.V** 验证：双人复核或同一审核者分轮复核的样例记录；固定评估报告人工抽检。
- [ ] **M6-04.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**无法验证的答案标未知；关键越权/型号错误阻止发布；门槛先在基线上校准并记录。

<a id="m6-05"></a>
### M6-05：反馈审核转测试与资料修订

**依赖：**M6-04,M5-07。
**文件：**`app/evaluation/feedback_triage.py`; `frontend/src/features/evaluation/FeedbackQueue.vue`; `tests/contract/test_feedback_triage.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M6-05.1** 待审→确认/驳回→可追溯草稿，单文档CAS/不可覆盖，不写标准题集或知识。
- [x] **M6-05.2** 精确原run/revision及待发布新修订/受影响题绑定，validated候选隔离评测不改活动指针。
- [x] **M6-05.3** Publisher最终门禁要求先受影响题、再完整开发集回归，证明绑定实验/校准/当前修订验证内容，缺真实人工拒绝。
- [ ] **M6-05.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_feedback_triage.py -q。
- [ ] **M6-05.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**错误反馈不会自动污染知识；回归问题可追溯原 run；资料修订遵循验证后发布。

<a id="m6-06"></a>
### M6-06：Ragas 辅助评审（可选）

**依赖：**M6-02,M4-09。
**文件：**`app/evaluation/judges/ragas_adapter.py`; `pyproject.toml`; `docs/evaluation/judge-policy.md`; `tests/unit/test_judge_adapter.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M6-06.1** 独立评测依赖组。
- [ ] **M6-06.2** 固定评审模型/提示词/版本、费用上限与可外发范围。
- [ ] **M6-06.3** 失败不替代人工结论。
- [ ] **M6-06.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_judge_adapter.py -q；启用时单独运行少量真实评分。
- [ ] **M6-06.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**可禁用不影响主流程；模拟评审与真实评分标识清楚；费用和敏感内容策略可见。

<a id="m6-07"></a>
### M6-07：运行可观测性与质量面板

**依赖：**M6-03。
**文件：**`app/runs/telemetry.py`; `frontend/src/features/evaluation/RunsPage.vue`; `tests/unit/test_telemetry_redaction.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M6-07.1** run/stage 耗时、模型、token、失败/降级和修订统计；评测题级保留stage_timings/token_usage。
- [x] **M6-07.2** 缺失/失败/未观测保持null，明确0不被改写。
- [x] **M6-07.3** 默认不存完整私有内容，模型和错误只过安全白名单。
- [x] **M6-07.V** 验证：最终20项遥测/正式适配器回归通过；完整阶段913后端、37前端单元/34离线浏览器、既有重导入3项及typecheck/build通过，退出均0。
- [x] **M6-07.D** 已保存任务记录，同步总清单、进度、变更、契约、OpenAPI/类型及遥测手册；真实供应商费用/GPU仍未知。

**验收：**失败能定位阶段和策略；日志无密钥/签名 URL；面板指标可追到真实 run；采样不会伪装全量。

<a id="m6-08"></a>
### M6-08：M6 阶段验收

**依赖：**M6-05,M6-07。
**文件：**`docs/development/records/M6-08.md`; `docs/evaluation/release-report.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M6-08.1** 固定版本重跑并对比。
- [ ] **M6-08.2** 一条真实反馈经审核→回归题/修订→复评。
- [ ] **M6-08.3** 可选 Ragas 明确启用或延期。
- [ ] **M6-08.V** 验证：按实验 manifest 的命令重跑；pnpm -C frontend test:e2e -- experiments.spec.ts feedback-loop.spec.ts。
- [ ] **M6-08.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**实验可复现且差异有解释；最终评估集未用于调参；质量报告没有把 LLM 分数等同事实准确率。

