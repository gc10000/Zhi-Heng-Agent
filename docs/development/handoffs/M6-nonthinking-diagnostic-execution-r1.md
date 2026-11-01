# 执行Prompt：M6显式非思考模式有界诊断 r1

你是本包执行Agent。仓库`D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag`，Windows／PowerShell，2026-11-01，Asia/Shanghai。任务是在不改检索、prompt和4096请求预算的条件下，仅显式请求关闭thinking，验证真实可见答案；不是恢复旧blocked批次。完成最小实现、相称验证及全部前置通过后的本包真实执行，不仅交计划。首失败全批封存，不自动换规则。

## 1．接续、角色及已关闭项

读取适用AGENTS、PROGRESS、REVIEW_STATUS、TODO、M6-evaluation任务、contracts、GIT_WORKFLOW，以及：

- `docs/development/reviews/M6-remaining-diagnostic-review-r1.md`及validation-r1.json：de4b118已由总控独立复核，清单准入／共享首停止和结算、两版047及版1 05-b限定效果明确关闭；
- `docs/development/reviews/M6-nonthinking-diagnostic-authorization-r1.json`：本包唯一条件授权，使用实际封存Git commit／path／SHA256，不用可变工作树冒充；
- 原`M6-remaining-diagnostic-execution-r1.md`／摘要及私有prepared-r1、consumer-preflight、旧批次已结算证据；按依赖读取，不重复整轮旧复审。

先核当前HEAD、工作区、origin及实际远程，有更新只核受影响部分，不回退提交。原新版版1 05-a、P2／p30／001／SQ／AF／组合／对象关系／continuation／n1及raw usage关闭保持，不找账号、PDF或重评分。

总控负责独立验收；本包执行自验与逐题来源诊断不自签独立通过。M6仍5/7，04保持验收，05／08未验收，M7未授权。不开子Agent。

## 2．唯一新变量及风险依据

旧17-b原流已证实正文0字符、4096输出全部reasoning、finish length；必要来源在精确prompt中，问题不在当前检索覆盖。唯一选择是固定有效wire增加`enable_thinking=false`；其他参数、输入、证据、排序、分组、引用与预算不变。

官方千问兼容API文档列出此参数，项目已有provider配置也支持该表达；这不证明当前私有网关或`qwen3.8-flash`别名一定支持／遵从。禁止把模型名或endpoint hash当厂商保证，不要求用户查账号。真实对照就是验证它能否在本固定设置下产出可见正文，不登记全域verified能力。

网关硬限、最大付费输出上界仍unknown；精确HTTP及费用null。总控仅对本固定清单、固定模式、串行首失败范围条件接受未知付费上界，不冒充用户能力声明。4096请求及客户端超时不是费用硬上界。

不再追加非产品探测，不试thinking_budget／effort、其他字段路由、`/no_think`、换模型或扩预算。如果网关拒绝参数、忽略参数或本次结果不合格，封存即停；不能在本包继续换参数试。

## 3．45个固定成员与旧状态保护

本包是新配置的有界对照：**旧失败版1 17-b一个新模式结果＋原44未执行成员＝45个答案job／stream上限**，无047，无旧05-b重跑，无旧版1 canary重跑。授权JSON逐成员绑定输入文件hash、prompt hash、题集身份、父旧槽及新固定槽，直接消费，不从聊天重建。

新批次固定`m6-nonthinking-diagnostic-r1`；新准入固定`diagnostic_nonthinking_manifest_r1`。新成员槽由授权冻结。旧`m6-remaining-diagnostic-r1`保持blocked、根halt不动、4个旧槽保持已消费；新17-b明确计新调用，不写成旧attempt续跑、退款或重复授权。旧canary和非产品探测槽也只读。

顺序：先新版版1 17-b。真实结果及来源诊断通过并结算，才接原44未执行成员，沿原dispatch_order余段，先048，再版2 05-a／05-b／17-b／048等。不得跳过17-b准入、跳过失败题继续或缩清单冒充完成；每成员最多一个新stream，失败也消耗，零自动重试。

两派生题集仍各完整150题＝85 dev＋65 heldout，题目只取dev授权成员。旧版1前五题保存输入适用性按已封存结论引用；03-a／04-a／04-b不再适用的缺口保留，不自动补生成或把旧结果算最新模式通过。

## 4．最小接线与红绿验证

复用已审正式EvaluationService／execute_job／默认RealQueryExecutor、配置／Run／题级关联、精确缓存、CAS账本与固定槽机制。新增默认关闭的本包授权路由；封存授权、两控制库共享唯一账户、全部45成员及最终源码／runtime／输入／配置／请求身份。新账前值来源为旧账户结算快照，不能清零或两版各领一份。

不要改旧授权常量来复用旧槽，不放开普通v2 unknown，不把旧Run静默升级，不用私有SDK直连或临时monkeypatch绕过正式门禁。尽量复用账本核心，避免复制一套调度／供应商框架；若提取公共逻辑，保持旧批身份、目录、账本与已消费单题语义，并定向验证受影响旧路由。旧profile的无thinking参数约束保持，只对本授权精确允许false。

允许改动集中在`app/infrastructure/providers/output_contract.py`、新限定授权handler及必要的既有准入公共逻辑，和answer_budget／Run类型、正式适配器／QueryRunner接线；修改哪些文件据实际最小路径决定，不能顺带修改检索、parser、chunker、prompt、评分或原件。

先写合成红测再修绿：默认关闭／缺Git授权、非本成员、首次冻结改题／改prompt／跨版本、thinking缺失／true／冲突、有效wire只有false及原4096/n1、SDK真实MockTransport流、两库共享前值及跨进程唯一在途、CAS／started／settled／来源决定崩溃窗口、成功恢复不重发、旧blocked批次不能重开、原单题及普通v2等值。

增加输出模式失败测试：网关400、返回非空reasoning_content、报告正reasoning_tokens、length／空答、usage缺失／矛盾、断流及未知窗口全部阻断后续；不能把reasoning当答案。未提供reasoning计数保持null，不补0；只有实际出现正计数或非空reasoning内容才声称观测到thinking，不能凭缺字段证明服务端硬关闭。

合成数据库用随机短`m1_test_m4_`；不写真实旧质量状态。使用项目`.venv\Scripts\python.exe`运行实际相关测试，记录最终源码范围；中途结果另列。API有变同步类型／OpenAPI，新增配置同步说明；不加无用环境变量或修改.env默认。前置自验通过后可沿本授权执行，无需再次申请同一授权；失败不能绕过。

## 5．全清单无推理预检及固定运行

使用`output/m6-remaining-diagnostic-20261101/prepared-r1/`和`consumer-preflight/`、原受审`output/m6-diagnostic-subject-usage-fix-20261031/replay-final/requests/`、已封存编码／分数／检索响应，先一次完成45成员预检，不先创建45个实验。通过正式消费者重建精确prompt／context／reference_map／groups／budget，逐项全等；只允许合同policy身份的预期变化，其他预算内容不变。安装SDK Mock核实际请求messages完全一致，wire只增加`enable_thinking=false`。

固定：qwen3.8-flash，endpoint SHA256 `7cbf2306d7facc55fd08ea52e1d6891e0dc6bc6af6d5442df34f17403670ad2a`；不输出URL或凭据。langchain-openai1.1.11／openai2.28.0；n1、temperature0.1、stream及usage、SDK retries0、timeout120、无fallback／redirect。只发`extra_body.max_completion_tokens=4096`和`extra_body.enable_thinking=false`，不同时发max_tokens，不加effort／budget。

保持source_branch_compare_v1、attributed_assertions_v1、已审关系、weighted .5/.5、20／20／20／20／10、32768窗口／4096输出请求／reserve256／max_chars12000、单题保守输入上限28416。保留25题35必要单元、048双方和p30，以及LAN旧行unknown，表级页码不升格行定位。

实时只读核当前服务、授权、修订、两旧批账户与已消费槽、正式主体／输入；与封存来源匹配。无缓存miss才可发出，新增编码／重排／导入／图摘要预算0，不能补缓存。历史582／867全量审计只核封存hash复用则说明限制，不冒充本轮全量扫描。

如Docker／Mongo未就绪，按既有runbook恢复本项目基础服务并等健康；不得清库／prune／重建卷或启动worker，保持20m×3轮转。没有真实派发前置通过，不创建真实job；运行前source／profile漂移则停止。

## 6．预算、幂等及逐题闸门

本包最多45个新产品stream／正式单题job；非产品探测、模型审核、本地编码、重排、导入0。前值input37541／output28633，只计一次，由原六流＋探测＋canary＋本次05-b／17-b结算hash证明，不能把失败输出扣除。累计观测预算input1477632／output212992不扩大；45×4096＋28633＝212953，仅余39，仍须逐题真实预留与结算，不称付费上界。

共享唯一账户须跨两控制库／进程固定，联网前原子占成员slot、唯一在途及预算，started持久后才发模型。最多一个在途，逐题结算并保存来源决定后推进；已发出即消费。新请求、实验、Run及题级幂等身份绑定新模式和源码，保留旧父来源，不重跑首次创建脚本，不手清state／lease／retryable／slot。

raw usage在SDK归一化前留证。缺失／非法／矛盾、输出>4096、累计超限、超时／断流／未知窗口、空答、length／截断、参数拒绝或观测到thinking均封存停止整批。reasoning已含output，不能重复加减，visible token／HTTP／费用不可观测仍null。已知合法计量照记；未知调用量及费用不写0。started未结算不换request重发；成功只按正式检查点读回，持久结算重试不能调用模型。

先17-b必须有真实可见正文、finish stop、未截断、实际wire false、没有观测到非空reasoning／正reasoning计数、usage合法且计量闭合，并且正确具名归属MateDock 3、回答USB-C充电／不支持数据传输并引用实际p14证据，才允许下一成员；不是要求供应商必须上报可见token或reasoning0字段。若计数未提供保留unknown，不声称已证明内部推理硬关闭。

其余题逐题对照已审来源，特别核048是否完整回答同轴／EoC、对象／配件归属、条件与引用，不能用证据入prompt代替答案完整。来源不支持、明确错答／缺答、critical或实质歧义即停止，不加词／改prompt／换模型／加预算／再抽。执行来源诊断不代替独立双轮，不写正式评分。

## 7．证据、交付与退出

全新私有`output/m6-nonthinking-diagnostic-20261101/`，存在则用不覆盖后缀。旧脚本先读后复制适配，尤其旧audit_stop含来源决定写入，不得当只读审计原地重跑。旧blocked账户、根halt、已消费槽、原流、失败、评分与全部历史保护先存hash并在末次复核；任何异常如实保留，不恢复旧批。

输出脱敏执行报告／JSON、45成员状态、请求／Run／attempt／slot及来源身份、最终测试范围、全预检、真实调用分账、原始usage及未知项、首停止／中途失败、保护hash、证据限制；私有HTML列实际输入来源／回答／引用和未执行清单。只检查本轮实际消费的已审来源，不找PDF、不重建标签身份。

更新导航与必要契约／CHANGELOG／DECISIONS，保留历史，不自签05／08验收。显式暂存允许源码／测试／脱敏文档，检查diff和JSON后提交、普通push，并实核HEAD／origin／远程；私有output／evals／PDF／缓存／日志不上Git，tmp保留，private-identity不读，凭据不输出。

退出条件：45成员全部闭合或首停止，二者都回交总控独立复核。本包不做正式评分／attest／校准／gate／反馈proof、heldout、默认切换、M7或子Agent。新模式效果尚未证明；即使诊断成功，也不跨配置复用旧校准／质量结论，不能替代有效新候选、独立双轮／gate及001真实复评proof。
