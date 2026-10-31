# 执行Prompt：M6限定风险准入与新版05-a单题验证 r1

你是本包执行Agent。仓库`D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag`，Windows／PowerShell，2026-10-31，Asia/Shanghai。总控已完成本次独立复核，**不要再次等待同一两项保护的总控裁决**。先只读确认当前提交是否更新，读取适用AGENTS、PROGRESS、REVIEW_STATUS、TODO、M6任务、contracts、GIT_WORKFLOW；不回退旧提交。

## 权威材料与已关闭结论

执行提交`aa63cf943a230976f301ec6a6e5444678762ce2d`已由总控定向复核。读取：

- `docs/development/reviews/M6-output-contract-boundaries-review-r1.md`及对应validation JSON；原执行报告、红测及中途失败保留。
- `docs/development/reviews/M6-single-product-risk-authorization-r1.json`：本包唯一新增产品调用授权。使用包含此文件和本Prompt的实际Git提交／blob hash，不猜提交SHA，不读取工作树可变文件冒充封存Git来源。
- 私有总控证据`output/m6-output-contract-boundaries-review-20261031/`，固定已消费探测槽`output/m6-authorized-probes/m6-output-cap-4096-probe-r1/`。

已明确关闭：n1生成份数有效身份；SDK归一化前usage合法性／一致性、正式job／Run／账本持久阻断。此前已关闭的受审对象关系消费、P2、p30、001、组合与恢复结论保持。不要整体重审、找PDF、找账号或要求用户评分；不重做54输入／25题整轮审查。

唯一真实探测已有input102／含reasoning总output4096／reasoning4096、finish=length，**原流可见正文0字符**。这是固定设置一次经验，既不是产品质量证据，也不是全域硬限。固定槽已消费，禁止再发任何非产品探测。

## 本包角色、权限与硬边界

本包允许最小内部准入接线、合成验证，以及前置全部通过后**最多一个新版产品答案stream**。这是总控显式接受单次实际付费输出上界unknown的限定诊断，不需再次请求用户授权；不是允许放宽通用能力合同或批量恢复。

唯一对象：**版1`m6-g540-05-a`**。版2不跑，其他题不跑，原48 job（46答案＋2澄清）全部暂停。该新单题独立计账，不修改／假装续跑旧05-a；不把它从旧未执行列表中悄悄划掉。不运行正式质量候选、评分、attest、校准、gate或反馈proof，不切默认，不跑heldout、不进入M7。M6保持5/7、04保持验收、05／08未验收。

不开子Agent。不读private-identity，不输出.env值、端点或凭据。tmp保留，原件／output／evals／日志／缓存不上Git。旧Run、分数、blocked、state／lease／slot／retryable及失败材料不改；新故障测试仅随机短`m1_test_m4_`合成库。旧私有脚本先审阅再复制适配到全新output目录，禁止原地执行覆盖。

## A．实现显式单题风险准入，保留正常v2门禁

当前正常`diagnostic_total_output_v2`只接受适用verified硬限证据，unknown拒绝。这条通用分支**保持原义**；不要把一次观测写成`verified`／`server_hard_limit=true`，不要临时monkeypatch、关闭cap校验或用产品私有直连SDK脚本绕过正式job。

在现有output_contract／正式配置与Run机制内，落实最小显式内部身份`diagnostic_single_product_risk_v1`，消费上述Git授权。风险准入与能力事实分别保存：能力仍unknown，单次准入理由是总控封存授权。默认关闭，不增加公开API或新通用供应商／调度框架；旧非诊断及正常v2路径等值。旧显式v1／v2 Run不静默升级，不给旧Run追加策略。

必须绑定：授权Git commit／path／blob hash、固定槽`m6-05a-product-canary-r1`、唯一题目及版1dataset／manifest、prompt与受审关系来源、固定control／target库与owner／kb范围、运行profile、当前源码／新配置及生效发参hash。最后代码hash与新请求／Run／题级身份在调用前封存于新execution manifest，允许的代码变化只限本准入消费及必要合成测试／文档。漂移拒绝，不能改题号、target库、nonce、ledger_id或目录再领一次授权。

复用现有正式配置、授权、Run／执行关联／题级检查点和OutputLedger，固定授权槽须在持久原子独占后才联网；最大逻辑stream=1，在全部相关进程和同分库路径上不可再领。只认同一个控制库／目标库，不因换库重获额度。保存planned／started／settled或项目等价持久关联；started未结算禁止自动重试，已settled只读复用。正常lease／continuation按正式协议，绝不手工清state／slot。

新诊断账前值必须来源可核：旧六流23480／16506＋已消费探测102／4096＝**23582／20602**。这只是本诊断范围，不是全项目历史总usage。新合同／新ledger不能把此前消耗变0；保留旧超4096事实，不改原账户。固定槽与账户／题级关联应能在崩溃后证明未发出、已发未知、已完成三类状态，不能凭未写最终结果重发。

先写能揭露未授权放行／重复消费的合成红测，再完成实现与绿测。允许在该前置自验通过后执行下面唯一一次产品验证；不是要再交一包纯准备后等待重复授权。若不能安全实现或有未结算窗口则封存停止，产品新增0。

## B．固定产品输入、runtime和预算

唯一输入锚：`output/m6-diagnostic-subject-usage-fix-20261031/replay-final/requests/v1-m6-g540-05-a.json`，文件SHA256=`95a287a3a882aa6b7c3f16eed56a013db7b19b1031e6de035c11420b8ac1aeee`。其`result.prompt`：

- 项目canonical fingerprint=`c975587079e01a747990468487ac01c700137bc48578f130008e24ed676b5498`。
- 原始UTF-8 SHA256=`05f47209a2bfe1aaa5b5d5d58344e6ac3112e55742790fc34034116383758e9f`。不要混淆这两个hash算法。
- 受审binding文件`output/m6-diagnostic-subject-usage-fix-20261031/subject-binding.json` SHA256=`6b7b6e9062e1ca566008515a542cba0bb90daa1085f09ef81eb1ae015f00dabf`。
- 版1dataset SHA256=`c72a78955afe86503fbb37cc7293fa54287b0427877af4616bb762dfb57656c9`；split manifest SHA256=`3f2b3c3413da98773b600623200deb399f91da3e9c8b1b6dd0be3fc2d83109f9`。

正式消费者应从精确缓存及已审关系重建这个prompt／context／reference_map，不能直接把期望答案塞给模型。LAN归HUAWEI MateDock 3、机身RJ45独立；表级审核页码与旧行unknown分开。源码准入变化导致新配置及请求身份变化，但prompt正文必须与上述锚全等。source_branch_compare_v1、attributed_assertions_v1及已审对象关系保持；weighted .5/.5、20／20／20／20／10、原分数／排序／引用／分组不改。

固定profile（任何差异停止）：

| 项 | 唯一允许值 |
| --- | --- |
| endpoint hash | `7cbf2306d7facc55fd08ea52e1d6891e0dc6bc6af6d5442df34f17403670ad2a`；不输出实际URL。 |
| model／SDK | qwen3.8-flash；langchain-openai1.1.11／openai2.28.0。 |
| 份数／温度 | n=1／temperature0.1。 |
| 限额字段 | extra_body.max_completion_tokens=4096；不得同时带max_tokens。 |
| thinking | 保持网关默认，无开关、budget或reasoning_effort新增参数。 |
| 调用 | stream＋usage，SDK retries0，timeout120秒，无fallback／redirect。 |
| 答案预算 | context32768、请求output4096、reserve256、max_chars12000；不扩大。 |
| 输入预留 | 按正式保守计数；保存输入为12293，单次输入上限28416。计数／输入变化停止，不能放宽。 |
| 本诊断累计预算 | input1477632／output212992；前值23582／20602，不扩大、不重置。 |

4096只是请求限制，**实际最大付费输出unknown**。本授权只对这一次产品stream接受该风险，不能说取消／超时能保证费用。若usage缺失／非法／矛盾、总output超过4096、超时或中断，保留原始字段及未知窗口并阻断；不截数字、不补0、不二次试验。reasoning已含在output中，不重复相加；精确HTTP及费用未观测就null。

## C．前置一次完成，之后只执行这一题

1. 在新output目录封存原材料及历史保护清单；核本次授权Git来源与所有输入锚。读取当前正式身份／受审binding状态时默认只读；如binding尚未登记，按既有已审证明与最小权限正式登记本题必需的binding／诊断配置，保存创建或精确复用收据，不重签001、不提升账号权限。若身份缺项须使用已授权的现有受控正式接口；不读private-identity或让用户查账号。
2. 先用实际安装SDK＋MockTransport核最终wire。只允许上述profile及精确prompt，保留n1、raw_usage_v2及未知风险身份；不得以Mock宣称网关硬限已验证。
3. 用原向量、检索响应、pair分数、目录与正式消费者做**该题**缓存预检；miss即停，不编码、不重排、不重导入。核input12293及prompt／context／reference_map／关系与输入锚；无须重跑54题或旧25题整轮。
4. 完成下表全部合成边界；冻结新配置、源码hash、授权、请求稳定键、实验／Run／题级及账本身份。仅创建一个正式单题诊断job；不重跑首次批量创建脚本，不把原85题正式版本缩水成1题质量题集。
5. 持久预留和fixed slot started之后发唯一产品stream。原始请求、流、finish、raw usage、过滤后答案、引用、Run／job终态及结算分列封存。先结算，再作来源诊断，结束本包。即便成功也不继续48题。

| 合成边界 | 必须结果 |
| --- | --- |
| 无授权、授权hash或题目／版本／prompt／profile／target变化 | 请求前拒绝；unknown不能被普通调用借道。 |
| 两次申请、并发、换nonce／目录／ledger／target／控制库 | 固定槽最多一次；不能通过改身份重领。 |
| started前／后崩溃、settled后重放、正式创建／关联窗口 | 按正式恢复辨别，未知不自动重发；settled只读复用。 |
| n和raw usage直接保护 | 原关闭矩阵保持；坏usage沿正式job持久blocked，拒绝后续派发。 |
| 旧合同、关闭、默认、回切、同分库与continuation | 原路径等值；新风险身份漂移拒绝；旧blocked与评分不动。 |
| 累计与授权次数 | prior23582／20602保留；全域费用unknown；requested4096不充当硬保证。 |

只运行受影响的定向回归，不为增加数量重跑M6全套；保存所有红测／中间失败与修后日志。真实业务状态不是故障夹具。

## D．唯一产品结果的诊断与退出

本题目标来自既有封存审阅，不重新评分：机身RJ45有资料支持；LAN与MateDock3具名关联要在回答中正确消费，不能把配件LAN说成机身接口或只写泛称扩展坞。引用应与实际选中证据相符，LAN旧行unknown不得被偷偷升为精确页码。只诊断一次产品行为，不填正式质量分。

- 有可见、未截断答案，具名归属／机身边界及来源正确，raw usage合法且总output≤4096：记该题限定诊断成功，仍非双轮质量通过／批量授权。
- 有合法usage但空答／纯reasoning、length截断或语义／引用失败：记本固定设置的具体失败，保留输入→输出→来源链；不换thinking、不加output、不改prompt再抽。
- usage缺失／非法／超限或中断：先持久阻断、保留unknown及可证下界，不重试，不把部分输出当完成。
- 前置或实际正式身份登记失败：停止于明确接口／字段，新增产品调用0，不重做已关闭保护，不编造登记成功。

所有分支都在一次结果或前置失败处结束。交付应给出下一范围是否具备依据，不能自动继续或把测试数充质量。新结果不替换旧05-a，不修改封存分数、旧候选blocked或基线。

## 交付

新私有目录保留来源／计划／新配置／exact wire／缓存预检／红绿／固定槽／调用账／原流／逐题可读对照及48未执行清单，原件不上传。报告分别写实现自验、单题实际结果、网关能力仍unknown、旧结果保留与正式质量链未推进。维护7份导航保留历史；仅显式暂存业务源码、合成测试和脱敏文档，普通commit／push并核本地／origin／远程，工作区tmp保留。

不等待用户重新确认同一授权，不再追加探测；也不因为拿到本Prompt就越过前置放行。技术实现完成后仍由总控独立复核，执行方不自行宣布阶段验收。
