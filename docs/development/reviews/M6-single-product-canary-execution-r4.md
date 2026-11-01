# M6唯一新版05-a实际执行：限定诊断成功，封存停止

日期：2026-11-01，Asia/Shanghai。执行方接续总控当前服务核验提交`6960af72c8bf7b541acce638ac654053cd9f4750`；启动时HEAD与缓存origin/main一致，工作区仅tmp。保持`d41b3a4`独立关闭的单题风险准入、最终源码集成及精确消费者预检，不重跑整轮准备，不重复申请既有授权。

## 实际结果

**唯一版1新版`m6-g540-05-a`已实际执行，达到本题限定诊断成功条件，现已封存停止。** 有272字符可见正文，finish为`stop`，Run记录`output_truncated=false`；机身RJ45与具名配件HUAWEI MateDock 3的LAN接口明确分开，引用[1]／[2]与实际选中证据对应，没有把配件LAN写成机身接口。LAN旧行页码仍为unknown，受审表级p14没有升格为该行精确页码。

这只是执行方对一个实际产品结果的来源诊断，不是正式评分、双轮质量通过、总控独立复审或M6阶段验收。私有答案、原流、实际配置、引用与完整结果不提交Git，正文仅在本机对照页保存。

| 对象 | 实际状态 |
| --- | --- |
| 正式实验 | `281d874c-0a8c-4520-b214-a69c54b0b0be`，attempt1，completed，仅1题。 |
| 正式Run | `d3649c7a-e79b-4b91-9165-b83462634cb4`，completed，未截断。 |
| 固定slot | `m6-05a-product-canary-r1`已started并settled；不得再次消费，只能依正式协议只读复用。 |
| 账户 | 单次CAS预留、单次结算，pending为空、unknown_windows为空；账户open仅表示本次合法结算，不能据此绕过已消费固定槽再次调用。 |
| 完整题集与配置 | 正式descriptor精确复用，完整150题／dev85不缩水；本机受控catalog解析本题诊断配置，由EvaluationService冻结到正式实验。 |
| 对象关系 | 直接消费既有Git证明及完整成员；无新registry、不重签001、不提权。 |

## 一次正式链路与身份

紧邻发起前只读核同一请求／配置实验、目标账户key／合同、控制库同key账户、检查点与关联均无消费记录；固定slot无started／settled，当前源码／runtime／输入／封存授权及预检收据hash一致。随后仅运行已审`execute_canary_r2.py`一次，沿`EvaluationService.create_experiment`、`execute_job`默认`RealQueryExecutor`，没有传`executor_factory`或用私有SDK绕过门禁。

缓存适配仅替换embedding／rank／保存检索响应读取口，保留正式只读索引授权及原消费者。实际命中1个查询向量缓存、20个pair分数、3个检索响应，miss0，本地推理0，无fallback。原候选、排序、context、groups、reference_map与prompt保持；正式输入保守预留12293、limit28416，未扩大预算。

正式账户pending预留、Run执行关联与固定started在网络之前持久完成；started时点为2026-11-01 10:32:31（Asia/Shanghai）。HTTP request hook封存的账户状态为pending、input_reservation12293、logical_reservations1，与同一Run／实验关联；实际wire与安装SDK先前Mock封存输入全等。正式成功检查点及完整outcome已只读核验，与唯一完整attempt结果hash一致；未做真实重放试验或改写旧state／lease。

- 业务源码：`b50b1f5b0eab66d7a4eb2a32314bcd415dba2624354cfb0ece59d2efce17ab8b`，本轮app源码未改。
- 配置canonical：`22d0e525ba1074336a6d7af973cc50427eb96e4c3f5ad28d9a3c60e37ff65efc`；manifest：`0e94544429f865b2f2e35193f9f915e06282de9c1faf85fafe27d4891bb85533`。
- 请求键：`0b0d21e83dbdc7ef28605dec2f35c3790a3d043252b9b5cd23c1cc0ddb70b790`；checkpoint：`9dc35acea3b1133b409e403caa2eea8bfea70cf4e91d8e0ba3c01da47f243301`。
- prompt canonical：`c975587079e01a747990468487ac01c700137bc48578f130008e24ed676b5498`；原始UTF8 SHA256仍为`05f47209a2bfe1aaa5b5d5d58344e6ac3112e55742790fc34034116383758e9f`，两种算法分开保存。
- 实际wire canonical：`b7d1614fe243432097896a533dc7ad0c1364de4e89fb95f487bfcbebeeea6640`；原响应字节SHA256：`52005c2445c2ff21aaebd88be00f8dfdfaffe522e150e586ae99c51a7700d462`。

旧05-a实验／Run／分数仅作父来源，不冒充续跑，也没有从旧48未执行清单中扣除。授权仍来自`bcee539`封存Git blob，实际端点仅核hash、不输出URL；模型qwen3.8-flash、langchain-openai1.1.11／openai2.28.0、n1、temperature0.1、extra_body.max_completion_tokens4096、不带max_tokens、默认thinking、stream＋usage、SDK retries0、timeout120秒、无redirect／fallback保持。

## 计量与未知项

| 分账 | input | 含reasoning总output | 边界 |
| --- | --- | --- | --- |
| 原六个诊断流 | 23480 | 16506 | 历史原账与超限事实不改。 |
| 已消费非产品探测 | 102 | 4096 | 未重跑，不充作产品答案。 |
| 本题调用前值 | 23582 | 20602 | 不归零、不移作旧05-a续跑。 |
| 本次唯一产品流 | 5165 | 1702 | reasoning1510已包含其中，usage total6867一致，合法且output≤4096。 |
| 本诊断累计观测 | 28747 | 22304 | 非全项目累计；预算1477632／212992不变。 |

原SSE有530个JSON事件、1个usage事件、1个DONE，finish仅stop；可见正文272字符，reasoning正文3022字符。字符数不是token计量；output减reasoning的192只作算术差值，不当作实测可见token，visible_tokens仍null。供应商额外usage细节原样封存，不据其text_tokens推断可见token。

本地观察到1个request hook、1个200 response hook，**精确HTTP请求总数及费用仍null**，不把本机hook数冒充供应商端到端请求／付费计量。请求4096只是一项请求限制，本单次实际付费输出上界及网关全域硬限仍unknown；不登记verified或server_hard_limit=true。此次未出现usage缺失／非法／矛盾、超限或中断；合法结算先于来源诊断。

## 实际核验与保留失败

正式单题命令exit0；末次只读核当前Run、账户、实验、checkpoint及正式outcome，结算与磁盘settled全等。执行后来源／文件／状态审计2423项通过、exit0，含138／336／597／1314组历史文件hash匹配；组间重叠，不累计为唯一总数或质量分。实际语料与索引读取属于本题正式消费者，不声称另行重扫全量历史集合、默认指针或run_events／TTL。private-identity未读取。

已关闭最终源码169项离线、75项集成、12项总控独立边界沿用既有证据，本轮未重跑；中途8项集成不替代最终源码检查。此前r2驱动断言失败和r3服务不可用保持原时点记录，不因本次成功覆盖。

本轮私有审计首版误将数据库裁剪后的公开result与完整冻结result比较，失败日志保留；只读定位唯一完整attempt hash与正式冻结完全一致。第二版导出Mongo日期时遇序列化错误，亦保留。第三版按同一公开／完整投影区分并序列化日期后审计通过。这两次是执行后只读审计脚本失败，没有修改业务源码、正式数据或再次发出模型请求。

本机新诊断、核账、命令及审计收据在`output/m6-single-product-canary-20261031/continuation-r4/`；正式驱动按既定路径将实际job保存于`continuation-r2/formal-job-r2/`。可读对照为`continuation-r4/单题实际结果与来源对照.html`。固定slot原计划、追加冻结、started／settled、原流、旧失败、output／evals／原件／缓存／tmp均保留本机，不上传、不清理。

## 退出与下一动作

本题实际结果可供总控判断后续范围，但**尚不构成扩大范围依据或批量授权**。本包已停止；不再调用版2、其他题或非产品探测，不恢复原48 job，不跑heldout、不切默认，不写正式质量候选／人工或助手评分／attest／校准／gate／feedback proof。正式诊断job既有自动来源指标不冒充质量评分。

M6保持5/7，04保持验收，05仍缺有效真实反馈复评proof，08仍缺有效新候选质量及阶段验收，M7未启动。唯一下一动作由执行方承担：保持固定槽只读封存，向总控交付此次真实结果与来源／结算材料供独立复核和后续范围裁定；在新的范围裁定前不生成下一题。提交及远程核验结果另以实际回执交接。
