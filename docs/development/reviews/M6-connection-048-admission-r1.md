# M6新连接模式单题风险准入与catalog预检实现报告

2026-11-03；任务`M6-connection-048-admission-r1`；分支`codex/m6-source-bound-comparison`，基点`17103bfb9a37c786185557f25fc4602b62cb682d`。当前总控实施并直接复核，**本报告为实现自验，不自签独立技术关闭**。

本包已补齐新连接模式的专属合同、登记前准入、独立CAS账本和正式Run结算；已在方案指定目录生成实际可解析的默认关闭catalog。静态预检passed，正式派发仍为`blocked_no_new_authorization`。新增真实模型调用、本地推理、真实业务库读写、正式实验/Run/槽/评分均0。

## 解决的具体卡点

此前`connection_comparison_v1`不能使用旧048授权，正式服务无条件拒绝登记，也没有新模式专属风险路由。本包增加`diagnostic_connection_comparison_048_v1`，只允许新批次/单题槽；旧比较合同不能进入新模式，新合同不能用于旧模式。启用时须有新固定Git授权与冻结清单，当前`AUTHORIZED_GIT=None`，关闭模板不伪造授权引用。缺授权在`repo.create`前422拒绝；require、客户端和清单准备均先拒绝，不占槽或创建正式目录。

预算固定32768窗口、4096输出、256保留、12000字符、10文档、输入28416；沿用冻结模型/SDK/端点身份，n=1、不思考、SDK无重试。历史56239/30516、新增和累计算术上界84655/34612分账，网关/付费硬限及费用unknown，HTTP/费用无依据时null。未改变浏览器API、默认模式或环境变量。

独立profile复用既有RemainingLedger/NonthinkingLedger生命周期，采用新collection/key；同/分库CAS唯一预留、并发一胜者、幂等结算、awaiting_review、拒绝及halt后不能重领。未来运行前只读核旧r8指定账户保持blocked、已settled、拒绝/halt且无pending或未知窗口；不修改旧账户。成功/失败正式Run实际结算新账户，重建实验观察同一Run，不再次生成。

## 实际发现并修复

新增正式执行链测试在同/分库均复现：返回思考内容仍进入awaiting_review，首轮19通过/2失败。根因是生成节点的思考输出观测版本列表遗漏新合同；账本虽已接线，收到的observed_reasoning却为false。只补新合同的观测接线后，两项及完整回归通过。红测与全部中间结果保留，不写成此前已通过。

本包未修改已独立通过的`comparison_context.py`、`connection_semantics.py`、`comparison_answers.py`，实际hash核对通过，既有独立技术结论保持。

## 验证与集中矩阵

| 边界 | 实际结果 | 结论范围 |
| --- | --- | --- |
| 合同/身份/无授权/合成授权来源/prompt与配置漂移/旧账户只读 | 新定向单元35通过，已包含在下述222中 | 实现自验；Git授权读取用合成资料替换，不是假正式授权 |
| 受影响离线/契约回归，含OpenAPI一致性 | 222 passed，1条既有Pydantic浮点用量警告 | 旧输出合同、模式配对、内部输入序列化及连接消费者 |
| 新账本和正式Run + 原连接模式接线 | 随机隔离Mongo 72 passed（新21、既有51） | 同/分库、并发、重用、未知usage、断流、异常结束、思考、超限及既有恢复 |
| 旧比较/非思考风险及输出边界 | 另组随机隔离Mongo 66 passed | 旧合同与生命周期受影响回归；不作真实业务库证明 |
| 指定目录实际prepare/resolve/预检 | passed | 完整150题85/65，只选dev048；4资料582成员冻结映射全等 |
| 实际准备catalog的服务拒绝与漂移反例 | passed | 无网络；关闭合同登记前422；题号、快照、合同和题集变异均拒绝 |
| 旧算法源码及固定来源配置 | hash匹配 | 不作全库现场保护扫描 |

单元35指`test_connection_048_admission.py`32项与`test_connection_048_preflight.py`3项；其余组不累加成质量分。正式Run集成模拟准入来源、runtime和wire端口，实际运行job/QueryRunner/usage/新Mongo账本；生产准入消费者另由合成授权单元实际执行，不把模拟模型当供应商能力或真实答案证据。

中间记录：合同首轮3失败/16通过；接线27通过；来源夹具首轮1失败/29通过，系小预算夹具未按固定profile装配，修夹具后30通过；新账本首轮13通过；正式链19通过/2失败为上述实际业务遗漏，补修后通过。preflight名为red的日志实际3通过（启动期间文件已就绪），**未形成该文件的红测证据**。本机catalog实核脚本首次使用错误的异常属性`status_code`而失败，改用实际`status`后通过，原日志保留。旧proto/r1等历史不覆盖。

## 已准备配置，用户无需手工配置路径

- catalog文件：`D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.worktrees/m6-source-bound-comparison/output/m6-connection-comparison-048-r1/catalog/catalog.json`
- 独立持久输出：`D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.worktrees/m6-source-bound-comparison/output/m6-connection-comparison-048-r1/execution`
- config_id/version：`m6-connection-comparison-048-r1` / `connection-r1`；client_request_id：`m6-connection-comparison-048-r1-request-01`。
- batch/ledger：`m6-connection-comparison-048-r1`；slot：`m6-connection-comparison-048-r1-support-v1-048`。均为配置身份；正式experiment_id/run_id/checkpoint_id仍null，未预留。

执行入口`scripts/verification/prepare_m6_connection_048.py`缺省即准备上述路径，不读.env、不建客户端、不访问数据库；目录排他创建，重复运行拒绝，不能覆盖本次证据。新增的是内部合同和本机准备脚本，无新增环境变量，不替换正在使用的服务目录。

完整原题集/manifest与冻结r8配置、模型指纹保留；技术来源钉17103bf独立报告及三算法hash，累计量钉封存r8结算报告。私有目录还含static-preflight和prepared-identity；原题、配置原件、日志及反例仅本机，不提交。

## Passed、open及证据限制

**Passed（实现自验）**：上述专属合同、正式接线、故障结算、无授权拒绝和实际catalog静态预检。此前算法独立通过保持；**新风险/准入包尚无另一实现身份的独立通过**。

**Open**：正式派发前须完成本包定向技术复核，并按既定单题方案实际取得完整582成员标量资料、装配并冻结精确生产prompt和来源/预算锚；取得明确新单题调用授权后方能登记、预留和执行。当前没有伪造授权文件、精确prompt hash或正式清单。不能使用333成员双资料投影补签全scope锚。完整标量复核/输入冻结是既定前置工作，静态映射核验并未完成它。

静态预检只读取冻结文件及Git材料，未全量重读真实582/867载荷、向量、默认指针/TTL或质量全库；保留模型保存指纹，未新读模型权重或启动embedding/reranker。它不证明运行时资料仍一致，未来运行仍需实际来源、旧账户、runtime/wire和调用前持久输入锚核验。无前端行为改动，未重复整轮前端审计。

**真实质量未证明**：本轮无新产品答案；原失败、评分、旧r7/r8消费槽/blocked/halt保留。完整原文摘录不能代替完整比较，限定比较的退出条件仍按[既定单题方案](../handoffs/M6-connection-comparison-048-proposal-r1.md)判断，不降低为“列出摘录”，不承诺发现所有问题。

M6保持5/7：04验收；05缺真实反馈复评proof；08缺有效候选质量及阶段证据。43题暂停，heldout65/M7不启动。下一唯一目标是对本包准入/账本和catalog做定向独立复核，同时将完整生产输入冻结准备落实；不以新增调用代替该核验，不要求用户审代码或填路径。真实累计仍56239/30516。

私有证据：`output/m6-connection-048-admission-20261103-r1/`；脱敏摘要见[validation JSON](M6-connection-048-admission-r1-validation.json)。提交及普通push在验证后完成，实际SHA由最终交接给出。
