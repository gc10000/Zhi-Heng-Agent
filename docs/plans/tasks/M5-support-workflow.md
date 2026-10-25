# M5：技术支持流程与有限 Agent开发 ToDo

> 执行方式：按任务逐项开发；使用 superpowers:executing-plans 技能。任务中的步骤采用勾选框跟踪；不自行派发子代理。

**目标：**交付“技术支持流程与有限 Agent”阶段可独立验收的能力。
**架构：**沿现有 Python/FastAPI/LangGraph 链路做小步适配；Vue 3 前端只消费统一 API 与事件契约。保留旧入口与数据直至本阶段验收通过。
**技术栈：**Vue 3 / TypeScript / FastAPI / MongoDB / Milvus / MinIO；具体测试工具与依赖在对应任务中建立。
**设计依据：**[优化方案](../2026-10-22-technical-support-optimization.md)、[接口与数据契约](../DEVELOPMENT_CONTRACTS.md)、[开发总清单](../DEVELOPMENT_TODO.md)。

## 进入条件与执行约束

2026-10-25第二轮总控：**关闭R1，R2/R3仍需修复**。归档已占用会话后恢复递归至RecursionError；撤回设备后正式QueryRunner仍从旧会话确认AX-24。M5-05/08重开，当前5/7核心、总核心58/76；仅授权M5内修复及第三轮提交，MCP延期、M6未授权。详见[第二轮总控结论](../../development/reviews/M5-review-r2.md)。以下执行数值保留原时点，不代表当前总控验收状态。

2026-10-25首轮总控：**需修复R1—R3**，重开M5-02/05/08，当前4/7核心、总核心57/76。修复范围为清单聚合的撤权门禁、占用中断窗口叠加上下文纠正的恢复、将已确认字段撤回未知；先正式回归，再最小修复及完整阶段复验。M5-06延期、M6未授权。详见[总控结论](../../development/reviews/M5-review.md)。下段及文末执行数值保留为首轮提交时点历史，不代表当前验收状态。

当前第二轮执行状态：先执行R1，红测2失败/3正常通过后加入变更前完整聚合授权，正式9项通过。R2先注入active_run已占用但claim状态/用户消息未写的真实Mongo故障点，初版5项按已知问题失败；修复后领取恢复/超时/并发21项通过。R3后端撤回未知正式回归和旧运行/草稿快照边界15项通过，前端4个离线浏览器通过；初轮用例构造的重复时间字段断言与API输出不同，已修正该测试，原结果保留。最终相关回归、完整阶段后端/前端验收及第二轮材料已完成，任务内部步骤已勾选，阶段待总控审查，M6未授权。

2026-10-25：M4第2轮总控通过、R1关闭，已授权从M5-01按依赖完成M5-01至M5-08；M5-06仍为可选，可登记延期，保持未勾选且不计核心进度。当前M5第二轮执行自验完成（7/7核心、待总控审查，可选0/1延期），修复提交`9bd4c96`已推送，M6及后续未授权。见[M4授权与保留边界](../../development/reviews/M4-review-r2.md)。先状态/槽位、引用操作清单与用户确认草稿，再有界只读工具和恢复；保留M4默认及真实质量局限，不以历史heldout调参或冒称新盲测。

依赖 M3-11 与 M4-10，先确定支持状态机，再加入工具调用。

- 以下文件均为**计划创建/修改**，不表示已经存在；执行前用 `rg` 核对真实接口与源码。
- 本阶段遵守总清单中的 Vue 3、中文注释、数据隔离、配置脱敏和完成证据规则。
- 每个代码任务先增加能揭示错误的用例，再做最小实现；文档、样式等低影响变更按实际结果检查，不写镜像测试。
- 每完成一个任务，记录验证命令、输出摘要、涉及文件和遗留问题；验证通过后才勾选[总清单](../DEVELOPMENT_TODO.md)，并更新[进度](../../development/PROGRESS.md)与[变更记录](../../development/CHANGELOG.md)。
- 命令均从项目根目录运行；`pnpm -C frontend` 命令需 M3-01 建立对应 scripts 后才存在。依赖安装和测试数据准备不表示任务验收通过。
- 每个任务验证其直接影响的行为，阶段验收时再执行阶段回归；不要重复运行无关全量测试。

<a id="m5-01"></a>
### M5-01：支持状态机与结构槽位

**依赖：**M3-11,M4-10。
**文件：**`app/support/models.py`; `app/support/workflow.py`; `tests/unit/test_support_workflow.py`；实际补充持久化`app/support/repository.py`、`api.py`及独立Mongo测试`tests/integration/test_support_persistence.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M5-01.1** 问题/设备/现象/环境/错误码/已尝试步骤版本化。
- [x] **M5-01.2** 缺槽位询问、证据不足退出转交。
- [x] **M5-01.3** 一次只收集必要信息。
- [x] **M5-01.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_support_workflow.py -q。
- [x] **M5-01.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**等待输入持久化且可恢复；无进展/缺证据有出口；不把用户未确认信息当事实。

<a id="m5-02"></a>
### M5-02：引用绑定操作清单

**依赖：**M5-01。
**文件：**`app/support/checklist.py`; `frontend/src/features/cases/components/OperationChecklist.vue`; `tests/unit/test_operation_checklist.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M5-02.1** 步骤含前提、引用、风险提示和用户自报结果；清单前授权聚合旧操作/工具引用。
- [x] **M5-02.2** 允许标记未试/已试/无效。
- [x] **M5-02.3** 保留实际记录时间。
- [x] **M5-02.V** 总控R1：补清单聚合旧操作/工具撤权与零写入正式回归，再复验原单元及实际入口。
- [x] **M5-02.D** 在原记录后补修复与实际验证，更新总清单、进度和受影响文档；保留原首轮证据。

**验收：**AI 建议与执行事实分开；每个具体操作可追溯；后续追问不重复无效步骤。

<a id="m5-03"></a>
### M5-03：处理记录与转交草稿

**依赖：**M5-02。
**文件：**`app/support/cases.py`; `app/support/api.py`; `frontend/src/features/cases/CasesPage.vue`; `tests/contract/test_case_confirmation.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M5-03.1** 从 run/操作结果生成草稿。
- [x] **M5-03.2** 用户修改/确认保存，未知字段显式未知。
- [x] **M5-03.3** 记录 owner/版本/引用快照。
- [x] **M5-03.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_case_confirmation.py -q。
- [x] **M5-03.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**未经确认只为 draft；重新生成不覆盖用户编辑；转交草稿可追溯对应问题和实际结果。

<a id="m5-04"></a>
### M5-04：有限工具注册与执行预算

**依赖：**M5-01。
**文件：**`app/support/tools.py`; `app/support/budget.py`; `tests/unit/test_tool_budget.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M5-04.1** 白名单工具、输入输出 schema、调用轮数/时长/token 上限。
- [x] **M5-04.2** 工具失败/重复结果退出。
- [x] **M5-04.3** 默认只读工具。
- [x] **M5-04.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_tool_budget.py -q。
- [x] **M5-04.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**恶意文档不能触发越权工具；最多达到预算即停止并说明；不引入自主设备控制。

<a id="m5-05"></a>
### M5-05：澄清恢复与上下文纠正

**依赖：**M5-03,M5-04。
**文件：**`app/conversations/context.py`; `app/support/commands.py`; `frontend/src/features/cases/components/SupportContext.vue`; `tests/contract/test_support_resume.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M5-05.1** 持久 awaiting_input 与上下文摘要版本；支持显式撤回已确认槽位。
- [ ] **M5-05.2** R3：撤回设备须阻止旧会话选择/助手历史/目录唯一项自行重确认；跑到正式产品计划与问答入口，保留旧快照。
- [ ] **M5-05.3** R2：归档等领取失败须有界恢复/终止，不能自递归阻塞扫描；保留已验收的未归档恢复和fencing。
- [ ] **M5-05.V** 加入第二轮两个正式入口反例，再复验澄清恢复、并发恢复、未来运行与实际Vue路径。
- [ ] **M5-05.D** 追加修复记录和第三轮契约/恢复说明；保留两轮原始失败证据。

**验收：**刷新可继续，取消后不复活；纠正只影响未来轮次；旧处理记录保留原快照。

<a id="m5-06"></a>
### M5-06：官方网页 MCP 工具（可选）

2026-10-25范围决定：延期，未启用外部工具/真实凭据联调，不勾选；见records/M5-06.md。核心阶段不依赖该可选项。

**依赖：**M5-04,M4-09。
**文件：**`app/support/web_tool.py`; `app/query_process/agent/nodes/node_web_search_mcp.py`; `tests/contract/test_web_tool.py`; `docs/runbooks/mcp-search.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M5-06.1** 显式启用与用户允许，配置鉴权、域名白名单、短超时。
- [ ] **M5-06.2** 保留网页时间/URL。
- [ ] **M5-06.3** 引用区分外部与内部。
- [ ] **M5-06.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_web_tool.py -q；无服务时登记延期理由，不标成已集成。
- [ ] **M5-06.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**未配置时跳过；官方页面冲突说明版本；超时降级不阻断本地；实际启用前真实凭据联调。

<a id="m5-07"></a>
### M5-07：反馈分类与草稿导出

**依赖：**M5-03。
**文件：**`app/support/feedback.py`; `app/support/export.py`; `frontend/src/features/cases/components/FeedbackForm.vue`; `tests/contract/test_feedback_export.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M5-07.1** 反馈按型号/证据/缺资料/步骤/配图分类。
- [x] **M5-07.2** 关联 run/citation。
- [x] **M5-07.3** 导出 Markdown 时转义并含资料版本。
- [x] **M5-07.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_feedback_export.py -q。
- [x] **M5-07.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**反馈不自动成为知识；导出只含授权资料；用户编辑和实际操作记录保留。

<a id="m5-08"></a>
### M5-08：M5 阶段验收

**依赖：**M5-05,M5-07。
**文件：**`frontend/tests/e2e/support-case.spec.ts`; `docs/development/records/M5-08.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M5-08.1** 真实演示未解决追问→记录已试→新建议或转交→确认草稿→导出→反馈。
- [ ] **M5-08.2** 保留R1验收，关闭R2归档递归/R3正式问答继承已撤回设备的遗漏。
- [ ] **M5-08.V** 正式反例和完整阶段复验；历史实时事件已过TTL须如实区分原报告与本轮可核对产物。
- [ ] **M5-08.D** 新增M5-submission-r3.md及独立新摘要/manifest；不覆盖两轮快照、不自标总控通过。

**验收：**可选 MCP 即使延期也有明确范围决定；核心流程有真实引用与用户确认；无伪造已完成操作。


第二轮阶段结果：789后端（动态JUnit统计）、既有重导入3项、前端37单元/28离线浏览器与类型/构建通过；R1 9项、R2 21项、R3后端15项/前端4项通过。沿用首轮真实产物只读8+16检查，新增付费0。M5-06延期不计完成，M5待总控审查，M6未授权。详见[M5第二轮提交](../../development/reviews/M5-submission-r2.md)、[摘要](../../development/reviews/M5-validation-summary-r2.json)及[记录](../../development/records/M5-08.md)。
