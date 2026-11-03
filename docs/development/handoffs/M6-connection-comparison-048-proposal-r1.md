# M6新连接比较模式048单题条件方案

2026-11-03，分支`codex/m6-source-bound-comparison`。这是具体准备方案，**未登记、未预留、未授权、未执行**。独立技术结论以[独立报告](../reviews/M6-connection-comparison-independent-review-r1.md)为准；技术通过也不产生模型调用许可。旧r7/r8、已消费槽、blocked账户及原质量拒绝保持。

## 对象、来源和唯一变更范围

仅反馈题集`fb-07c584730833908571fe9dd7c7c890afa3cf9e66`的dev题`support-v1-048`，原问题逐字为：**LA2608与CB304n的上联方式相同吗？请分别引用资料比较。** 产品H3C LA2608、Aolynk CB304n，历史对话为空；原rubric只用于事后判断，不进入prompt。模型沿冻结配置的`qwen3.8-flash`，不思考、`n=1`；SDK固定`openai 2.28.0`、`langchain-openai 1.1.11`，不换embedding/reranker、检索或模型。

保存配置来源是本工作树`output/m6-comparison-answer-048-execution-r10/catalog/configs/m6-comparison-answer-048-execution-r8-final.json`，文件SHA256为`ac0a4178f91fa638fd13ea08c9f897e26bf396005aa3581216e6e82ce8095b50`。新正式范围须保留该配置冻结的4资料582成员；精确document/revision/original SHA256及模型/运行参数从该不可变保存配置逐字段复制、复核并进入新清单。私有对照索引为`output/m6-independent-review-dispatch-20261103-r1/conditional-validation-input-inventory-private.json`。本轮333成员双资料回放仅是明确投影，不能代替正式全scope核验。

唯一允许改变的处理范围是生成端方案包：`comparison_source_assembly_v1`装配和`connection_comparison_v1`消费者。相对r8同时改变了来源装配与语义，因此本次是端到端候选验证，**不宣称严格单变量模型实验**；本轮同一装配输入的新旧消费者离线对照才以消费者为唯一变量。采用修复后的`qualified_connection_medium_v2`和`connection_comparison_renderer_context_v2`，源码须钉独立通过的确切提交及源码hash，不得沿用失败候选。旧Run/proof不升级。

## 具体身份与落盘位置

| 项目 | 拟用新值（尚未创建） |
| --- | --- |
| batch | `m6-connection-comparison-048-r1` |
| slot | `m6-connection-comparison-048-r1-support-v1-048` |
| config_id / version | `m6-connection-comparison-048-r1` / `connection-r1` |
| client_request_id | `m6-connection-comparison-048-r1-request-01` |
| catalog绝对路径 | `D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.worktrees/m6-source-bound-comparison/output/m6-connection-comparison-048-r1/catalog` |
| 独立持久输出绝对路径 | `D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.worktrees/m6-source-bound-comparison/output/m6-connection-comparison-048-r1/execution` |

由执行端创建并配置这两个目录，用户无需手工拼路径。它们本轮未创建；使用排他创建，遇冲突即停。正式experiment_id、run_id和题级execution link只能由新正式服务分配并保存，不能预造为已经存在。新账本和专用准入合同必须先实现并验证；当前EvaluationService明确拒绝该模式登记，不得复用旧风险路由或仅改字符串绕过。

模型调用前须将精确问题、产品快照、4资料完整冻结成员、装配输入/输出、prompt全文、实际连续引用映射、来源载荷、模型/SDK/源码版本和预算身份落盘并交叉校验。需要重新实际装配才能得到本次正式prompt字节及hash；当前不虚构它们已经冻结。未分类条件子段、表格原文和原件版本同样受约束；图摘要不能供强连接事实。调用前`comparison_generation_inputs`独立持久锚成功后才可派发。

## 预算、结算和恢复

窗口32768、输出4096、保留256、正文12000字符、上下文10条；输入硬约束28416。最多1次provider stream，无重试。此前实际累计input/output为56239/30516，本批逻辑预留上界28416/4096，累计算术预算上界84655/34612；这不是实际usage，也不是费用保证。网关和付费输出硬上界unknown，费用上限unknown，须在后续单题授权中明确接受。

首次派发前新账本预留1槽，started后仅结算一次；本批新增与历史累计分别记录。供应商usage缺失留null，不估算0；reasoning、精确HTTP次数和费用未获证据时继续null/unknown。不能将1个逻辑stream说成恰好1次HTTP请求。断流、未知窗口或usage缺失不得自动重试、退款、解锁或换新槽。

同client_request_id与相同输入幂等为唯一题级Run；不同输入拒绝。缓存先核模式、原来源和输入锚，再展示。首次outcome前恢复也不得从已改写的Run补签输入记录；成功必须保存本次观察的stop、无异常终止/终止后正文、raw selection、事实/完整来源语境/result/answer证明。已完成恢复仅核证据，不追加调用；新版本证明漂移拒绝，不升级历史Run。

来源缺失/歧义、必要预算超限、锚写失败或身份漂移应在模型前失败。started后的断流、非法选择、异常/缺失结束、证据漂移或质量拒绝均停止本批，保留失败、settlement、review(false)与halt；不续跑43题或其他题。

## 完整回答的退出条件

自然语言须直接回答资料限定的连接介质比较，并分别解释LA的3G/4G至控制器管理连接及互通限制、CB的Cable/无线路由融合能力和Cable口—同轴—入户接口限定路径。客户端有线/无线访问另层说明；逐型号、逐关系有对应来源，完整条件不能只进prompt而不进答案。不能跨引用拼出Web用途、无线回程、全面上联能力或现场已连通结论。资料原文语境可以含Web字样，禁止的是关系错绑，不能增加全答案禁词要求。

仅摘录、缺一方关系或仅答“程序无法判定”不算完整比较通过；不得新增同角色/同用途、EoC、GM/GU字样门槛。程序给出的限定比较可达与真实模型调用后的答案质量分别评价，不宣称模型独立推理了程序结论。即使单题通过，也不直接关闭M6-05反馈复评proof或M6-08有效候选质量/阶段验收。

**下一唯一实施目标：**在独立技术通过的代码上实现并审查新模式专用风险/准入合同及新catalog预检；仍为零真实调用。它通过且获得明确的新单题授权后，才执行上述1次验证。本方案不新增heldout、Ragas或默认发布门槛。
