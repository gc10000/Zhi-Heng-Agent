# M4：RAG 质量与性能实验开发 ToDo

> 执行方式：按任务逐项开发；使用 superpowers:executing-plans 技能。任务中的步骤采用勾选框跟踪；不自行派发子代理。

**目标：**交付“RAG 质量与性能实验”阶段可独立验收的能力。
**架构：**沿现有 Python/FastAPI/LangGraph 链路做小步适配；Vue 3 前端只消费统一 API 与事件契约。保留旧入口与数据直至本阶段验收通过。
**技术栈：**Vue 3 / TypeScript / FastAPI / MongoDB / Milvus / MinIO；具体测试工具与依赖在对应任务中建立。
**设计依据：**[优化方案](../2026-10-22-technical-support-optimization.md)、[接口与数据契约](../DEVELOPMENT_CONTRACTS.md)、[开发总清单](../DEVELOPMENT_TODO.md)。

## 进入条件与执行约束

M3第2轮已通过总控审查，授权M4-01至M4-10按依赖连续执行，从M4-01开始，阶段末提交总控审查；M5及后续未授权，见[M3第二轮授权](../../development/reviews/M3-review-r2.md)。当前M4-01/M4-02/M4-03/M4-04/M4-05/M4-06/M4-07/M4-08/M4-09执行自验完成，M4为9/10，尚未阶段提交。实施前核对并保留现有未跟踪evals/，不覆盖或自动上传；先标注、冻结题集/划分和原链路基线，再做调参实验，heldout在策略选定后才最终评价。无稳定收益保留旧默认，不预设收益或覆盖课程数据。

真实实现依赖 M1-11/M2-12；固定题集和标注规则先于策略调参。

- 以下文件均为**计划创建/修改**，不表示已经存在；执行前用 `rg` 核对真实接口与源码。
- 本阶段遵守总清单中的 Vue 3、中文注释、数据隔离、配置脱敏和完成证据规则。
- 每个代码任务先增加能揭示错误的用例，再做最小实现；文档、样式等低影响变更按实际结果检查，不写镜像测试。
- 每完成一个任务，记录验证命令、输出摘要、涉及文件和遗留问题；验证通过后才勾选[总清单](../DEVELOPMENT_TODO.md)，并更新[进度](../../development/PROGRESS.md)与[变更记录](../../development/CHANGELOG.md)。
- 命令均从项目根目录运行；`pnpm -C frontend` 命令需 M3-01 建立对应 scripts 后才存在。依赖安装和测试数据准备不表示任务验收通过。
- 每个任务验证其直接影响的行为，阶段验收时再执行阶段回归；不要重复运行无关全量测试。

2026-10-24核对：正式工作台是`app/runs/query_runner.py`和`app/knowledge/index.py`，旧LangGraph仅兼容；M4-02起须接正式入口，不能只改旧节点。模型宿主复用实际`app/infrastructure/model_host.py`，不重复建计划目录。M4-01已有50题辅助草稿/35与15划分，人工复核0；用户后续已委托助手独立审核，50题核完，43可保留、4建议补充、3需修改，见[审阅结论](../../development/reviews/M4-01-dataset-review.md)。先新增修订版本并记录真实助手审阅身份，无需继续等待用户自行核读；本轮未运行真实基线或依赖实验。独立M4-09已完成执行自验，32项能力契约含SDK格式验证；既有回归437通过/2排除/0跳过、既有3、类型检查及只读8通过、付费0。M4-01整体及后续依赖仍未验收。

<a id="m4-01"></a>
### M4-01：首批 50 题与原链路基线

**依赖：**M0-09,M1-11,M2-12。
**文件：**原`evals/datasets/support-v1.jsonl`及`split-manifest.json`保留；新增`evals/datasets/support-v1-r2.jsonl`及`support-v1-r2-manifest.json`；基线配置`evals/configs/baseline-r2.yaml`（本机已冻结，35dev执行及只读复核通过）；`app/evaluation/validate_dataset.py`; `app/evaluation/runner.py`; `docs/evaluation/labeling-guide.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M4-01.1** 覆盖参数/配置/故障/型号歧义/图示/跨型/无答案。
- [x] **M4-01.2** 标标准证据与适用型号，按真实身份区分用户委托的独立助手审阅与人工；r2七题修订总控定向复核通过，结合原43题累计50题审核完成，人工0（ADR-040）。七题新内容由独立结论与指纹另存绑定，不覆盖冻结r2。
- [x] **M4-01.3** 建立最小 JSONL 校验器和基线运行器，固定调参/评估划分再跑原链路。
- [x] **M4-01.V** 验证：.venv/Scripts/python.exe -m app.evaluation.validate_dataset evals/datasets/support-v1.jsonl。
- [x] **M4-01.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**每题有来源/允许证据/期望行为；保留多个正确证据；没有捏造提升指标或提前用 heldout 调参；M4 不依赖 M6 尚未建立的运行器。

2026-10-24修订接续：新增`evals/datasets/support-v1-r2.jsonl`与`support-v1-r2-manifest.json`，不覆盖原版，三项必改及四项建议均落实；完整可读稿本机`output/evals/support-v1-r2-review.md`。新CLI需显式`--manifest evals/datasets/support-v1-r2-manifest.json`，未来基线也须传新manifest与新的独立输出目录，不能默认读取旧split-manifest。当前只回交修订，未执行模型、基线或heldout；M4-01依然未验收。见[回交与验证](../../development/reviews/M4-01-dataset-revision-r2.md)。

2026-10-24总控定向复核：关闭三项必改及四项补充，M4-01.2通过。独立39项离线测试、八种内容变更拒绝、原件/裁图/冻结及溯源检查通过；见[复核结论](../../development/reviews/M4-01-dataset-review-r2.md)。r2保留原字节及回交标注计数，本次结论补足七题新内容的独立审核；无需为更新计数改写冻结文件。M4-01.3与整体任务仍未完成，可继续以下基线准备。

首次基线执行入口（七题复核已通过；三资料595切片/53图片独立语料及真实配置已冻结，dev执行中，结果待补）：

```powershell
.venv/Scripts/python.exe -m app.evaluation.validate_dataset evals/datasets/support-v1-r2.jsonl --manifest evals/datasets/support-v1-r2-manifest.json
.venv/Scripts/python.exe -m app.evaluation.runner --dataset evals/datasets/support-v1-r2.jsonl --manifest evals/datasets/support-v1-r2-manifest.json --config evals/configs/baseline-r2.yaml --output output/evals/support-v1-r2-baseline
```

运行器须遵循冻结划分，仅在允许的 split 上开展调参实验。把脱敏后的结果清单与参数记录到验收文件；`output/` 中的原始问题与回答不默认公开。

<a id="m4-02"></a>
### M4-02：统一候选与分阶段追踪

**依赖：**M4-01。
**文件：**`app/retrieval/models.py`; `app/retrieval/adapters.py`; `app/knowledge/index.py`; `app/runs/query_runner.py`; `app/query_process/agent/nodes/node_rrf.py`; `app/query_process/agent/nodes/node_rerank.py`; `tests/unit/test_retrieval_provenance.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M4-02.1** 定义 RetrievalHit/QueryPlan/EvidencePack。
- [x] **M4-02.2** 保留 dense/sparse rank、RRF、rerank、revision 和来源。
- [x] **M4-02.3** 融合去重稳定 ID。
- [x] **M4-02.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_retrieval_provenance.py -q。
- [x] **M4-02.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**所有来源经过重排仍可回溯；不同阶段分数不混同；图片不再从未纳入上下文的候选提取。

<a id="m4-03"></a>
### M4-03：产品目录、改写与主体约束

**依赖：**M4-02。
**文件：**`app/products/resolver.py`; `app/conversations/context.py`; `app/retrieval/query_planner.py`; `app/runs/query_runner.py`; `app/runs/repository.py`; `tests/unit/test_query_plans.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M4-03.1** 标准型号/系列/别名先精确后向量。
- [x] **M4-03.2** 原问题/结构槽位与改写分开。
- [x] **M4-03.3** 显式切换、泛化和双型号比较独立路由。
- [x] **M4-03.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_query_plans.py -q。
- [x] **M4-03.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**不回写旧消息；改写不新增未确认事实；近型号必须澄清；跨型比较分范围取证。

<a id="m4-04"></a>
### M4-04：候选池、融合与重排消融

**依赖：**M4-02。
**文件：**`app/retrieval/search.py`; `app/retrieval/rerank.py`; `app/knowledge/index.py`（直接复用Milvus的WeightedRanker/RRFRanker，不重复实现fusion.py）；`app/evaluation/retrieval_grid.py`/`readonly.py`; `evals/configs/retrieval-grid.yaml`; `tests/integration/test_scope_filters.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M4-04.1** 分别配置 dense/sparse 初召回量、RRF 池、重排量、上下文数。
- [x] **M4-04.2** 同源产品/权限/活动修订过滤共用。
- [x] **M4-04.3** 保留原策略可回切。
- [x] **M4-04.V** 验证：.venv/Scripts/python.exe -m pytest tests/integration/test_scope_filters.py -m integration -q；固定题集运行配置网格。
- [x] **M4-04.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**learned sparse 不标成 BM25；每组实验记录检索指标/延时/资源；没有实验支持不升默认候选数。

<a id="m4-05"></a>
### M4-05：条件 HyDE 与图汇合

**依赖：**M4-03,M4-04。
**文件：**`app/retrieval/routing.py`; `app/retrieval/graph.py`; `app/query_process/agent/nodes/node_query_kg.py`; `tests/unit/test_retrieval_graph.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M4-05.1** 明确类型才触发 HyDE/有限分解。
- [x] **M4-05.2** 占位 KG 移出正式路径。
- [x] **M4-05.3** 不同分支延时/跳过/空/超时使用受控 reducer 与汇合。
- [x] **M4-05.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_retrieval_graph.py -q。
- [x] **M4-05.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**每次请求只汇合一次；HyDE 文本只作查询不作证据；禁用增强仍可本地回答；分支故障可记录降级。

<a id="m4-06"></a>
### M4-06：父子相邻扩展与图表证据

**依赖：**M4-02,M1-07。
**文件：**`app/retrieval/expansion.py`; `app/answering/evidence.py`; `tests/unit/test_evidence_expansion.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M4-06.1** 只扩展同修订/型号父子与相邻块。
- [x] **M4-06.2** 预算内保留必要前提、表头和原图。
- [x] **M4-06.3** 评估去重和多样性。
- [x] **M4-06.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_evidence_expansion.py -q。
- [x] **M4-06.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**不把整章无差别塞入；扩展不会越权或跨版本；图片与当前引用证据对应。

<a id="m4-07"></a>
### M4-07：token 预算与引用校验

**依赖：**M4-06。
**文件：**`app/answering/context_budget.py`; `app/answering/citations.py`; `app/answering/service.py`; `tests/unit/test_answer_grounding.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M4-07.1** 模型可用 token 减系统/问题/历史/输出预留。
- [x] **M4-07.2** 真实 tokenizer 或记录保守估计。
- [x] **M4-07.3** 编号白名单/asset/revision 校验，支持不足/部分/澄清。
- [x] **M4-07.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_answer_grounding.py -q。
- [x] **M4-07.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**中英混合长输入不越预算；不存在的引用被拒绝或修正；无证据不自动留一条当可信；保留字符兜底。

<a id="m4-08"></a>
### M4-08：模型宿主、并发与缓存

**依赖：**M4-04。
**文件：**`app/infrastructure/model_host.py`（复用实际宿主，不新建重复目录）; `app/lm/embedding_utils.py`; `app/lm/reranker_utils.py`; `app/retrieval/cache.py`; `tests/unit/test_model_lifecycle.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M4-08.1** 核实 SDK query/document 编码。
- [x] **M4-08.2** 锁定模型加载、预热和小批推理。
- [x] **M4-08.3** 缓存含权限/产品/修订/模型/策略。
- [x] **M4-08.4** 测显存后再决定独立推理进程。
- [x] **M4-08.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_model_lifecycle.py -q；受控 1/2/4 会话资源测量。
- [x] **M4-08.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**并发首次调用仅一份模型；退出/修订后缓存不串权限；记录 GPU/CPU 性能与显存，不预设吞吐。

<a id="m4-09"></a>
### M4-09：供应商能力与超时策略

**依赖：**M0-08,M2-01。
**文件：**`app/infrastructure/providers/`; `app/settings.py`; `.env.example`; `docs/CONFIGURATION.md`; `tests/contract/test_provider_capabilities.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M4-09.1** 按文本/视觉/嵌入/重排能力配置 timeout/retry/JSON。
- [x] **M4-09.2** 验证格式并分类错误。
- [x] **M4-09.3** 能力检测与真实调用分离。
- [x] **M4-09.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_provider_capabilities.py -q。
- [x] **M4-09.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**温度零保留；错误模型/鉴权失败明示；JSON 不合法可控重试；缺工具配置不阻断本地问答。

<a id="m4-10"></a>
### M4-10：M4 实验报告与默认策略选择

**依赖：**M4-05,M4-07,M4-08,M4-09。
**文件：**`docs/evaluation/retrieval-report.md`; `evals/results/manifest.json`; `docs/development/records/M4-10.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M4-10.1** 同题集固定版本比较每个单因素、组合与基线。
- [ ] **M4-10.2** 按题型列失败例、成本、p50/p95。
- [ ] **M4-10.3** 保留无需增强的低成本路径。
- [ ] **M4-10.V** 验证：运行实验记录的固定配置，并人工抽检标准引用与答案；无真实结果时任务不可勾选。
- [ ] **M4-10.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**heldout 只在策略选定后评价；没有稳定收益保留旧默认；报告给出可重复命令与回滚配置。



2026-10-24 M4-01执行自验完成：三资料595切片/53图，完整语料指纹/精确图对应/实际代码版本冻结；35dev真实一次执行成功，34逻辑生成/1澄清、69消息，heldout0；72离线+3真实Mongo端口注入通过。真实只读复核通过，未知HTTP次数/金额与原解析/摘要元数据限制保留，不宣称答案正确率或收益。见[基线交付](../../development/reviews/M4-01-baseline-delivery.md)。此前“尚未执行/未验收”段落为历史时点，当前按本段与进度接续M4-02。

M4-02已接正式QueryRunner/V2Index，30项定向通过、付费0；原加权融合默认和候选量不变，追踪增加两次同范围只读分路检索。旧RRF仅兼容路径，保留复合身份/分数/来源。见[记录](../../development/records/M4-02.md)。

2026-10-25 M4-03正式入口63项通过，原问题/槽位/改写分离，近型号仅澄清，成功上下文继承及通用清空，逐产品比较取证；本项付费0、无新dev/heldout。见[记录](../../development/records/M4-03.md)。

2026-10-25 M4-06独立依赖自验45项通过；正式入口扩展默认关闭，来源/预算/父块前提及真实Milvus窗口通过，实际dev收益仍由M4-10验证。04冻结网格不切新实现，继续等9组结果。见[记录](../../development/records/M4-06.md)。

2026-10-25 M4-07自验135项通过，完整token预算/原字符兜底、实际SDK输出字段、父子组/引用顺序、错误传播及流/历史/final部分回答通过；无新付费/dev/heldout。M4为6/10，04原冻结9组仍执行中，05/08待04验收。见[记录](../../development/records/M4-07.md)。

2026-10-25 M4-04九组真实dev检索完成、每组35成功/0失败，付费/heldout0；独立分析修正错误澄清分母，34题适用，原件不改。最终45定向通过，保留原加权默认；来源覆盖不作答案正确率。见[报告](../../evaluation/retrieval-report.md)。

2026-10-25 M4-05最终62项通过，正式入口与实际编译旧图受控汇合有效，HyDE/分解默认关闭，假设不作证据。见[05记录](../../development/records/M4-05.md)。

2026-10-25 M4-08最终112项通过；真实模型/隔离索引1/2/4会话观测7检索成功、0付费、语料前后不变，进程单模型对，保留现有架构不新增进程。见[08记录](../../development/records/M4-08.md)。
