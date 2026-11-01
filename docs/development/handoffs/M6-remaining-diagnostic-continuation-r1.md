# 执行Prompt：M6剩余诊断受控串行接续 r1

你是本包执行Agent。仓库：`D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag`；Windows／PowerShell；2026-11-01，Asia/Shanghai。请完成本包实现、相称验证和符合前置的实际诊断，不仅交付计划；任何停止条件触发后封存退出，不换规则继续试。

## 一、先读现状，保留已经关闭的结论

读取适用AGENTS.md及PROGRESS、REVIEW_STATUS、DEVELOPMENT_TODO、M6-evaluation任务、DEVELOPMENT_CONTRACTS、GIT_WORKFLOW；核本地HEAD、工作区、origin/main及实际远程，不回退旧提交。执行提交3017a61573f2e6d34edd95f9bb39e88824e0e4b7与总控复审0b0a913b719b900aa232c4d88f454190e077f3d6已于2026-11-01补推、远程核验一致。若有更新，仅核影响本包的差异。

本包权威材料：

- `docs/development/reviews/M6-single-product-result-review-r1.md`及同目录validation-r1.json；
- `docs/development/reviews/M6-remaining-diagnostic-authorization-r1.json`：本包总控限定授权，须消费实际封存Git commit／path／SHA256；
- `docs/development/handoffs/M6-diagnostic-cache-completion-execution-r1.md`；
- 受审对象关系、输出保护及单题准入的既有关闭报告，按实际依赖定位读取，不重新整轮复审。

新版版1 `m6-g540-05-a`的真实归属效果和该次执行／计量结算已由总控独立通过。它的固定槽`m6-05a-product-canary-r1`已started／settled，只能只读引用，绝不重用、改名重领或再次生成。原六流、旧05-a失败、旧候选blocked、旧评分及历史未知费用全部保留。P2、p30、001消费、SQ／AF、continuation、检索组合、对象关系、n=1及raw usage保护等关闭结论保持。

M6仍5/7；04保持验收，05／08未验收，M7未授权。001已绑定valid，不找账号、不重签审或重绑，不让用户查PDF或重评分。

## 二、本包范围与授权，不能沿用旧单题额度

总控在既有M6开发诊断委托内作出本包新的**有界风险准入裁定**：前置通过后，仅接续原清单剩余48个job＝46个答案＋2个047澄清。授权来源是本包封存总控决定，不是用户已证明网关硬限或批准任意批量的声明。

网关全域硬限及最大付费输出上界仍unknown，费用及精确HTTP次数仍null。总控仅接受本清单、固定profile、逐题串行、首失败即停范围的未知付费上界风险；请求4096、客户端取消／超时及累计观测预算均不构成供应商费用硬上界。禁止登记verified，普通`diagnostic_total_output_v2` unknown拒绝保持。

本包包括默认关闭的限定准入实现、合成验证、全清单无推理预检，以及全部前置通过后的串行执行。不得另设“再申请同一授权”或仅准备交接一轮；但前置失败不能绕过。实现自验不是总控独立技术验收，本包成果仍须回交独立复核。

固定来源：

- 原主清单：`output/m6-attributed-evidence-diagnostic-20261031/prepared-r2/master-source-manifest.json`，文件SHA256 `e479481dec4be520d673d561975ab7a068d8298bbc85ea4ce72bcb5ed3d4e0e0`；
- 原54请求：同目录`execution-manifest.json`，文件SHA256 `1e50c370a38d2668e3d409a1099949f801704b0b5363d9ee4caa3444900e6a81`；
- 最新受审输入：`output/m6-diagnostic-subject-usage-fix-20261031/replay-final/requests/`；
- 既存缓存：`output/m6-diagnostic-cache-completion-20261031/`及其已封存来源；
- 两版本：`fb-07c584730833908571fe9dd7c7c890afa3cf9e66`、`fb-a3fa87c1adb2a6dc4e9638214164eb5f343ad008`，各完整150题＝85 dev＋65 heldout，不能误把85当总题数或缩题集。

成员精确定义：原54 entries中，版1排除已执行ordinal1至6，保留ordinal7至27共21；版2保留ordinal1至27共27。授权JSON已逐成员冻结输入文件hash、题目／版本／原序号、prompt或澄清结果hash及题集身份。不要从文字摘要重建题目或期望答案。新版版1 canary不从原剩余48中扣除；版2 05-a仍是本包一个独立待执行成员。

顺序：先版1、版2各自047零生成呈现检查；再依次执行版1 05-b、17-b、048，版2 05-a、05-b、17-b、048。均未触发停止条件后，其余39个答案按原version／ordinal顺序串行执行。这个顺序仅用于尽早暴露关键失败，原序号与来源不改；每成员最多一个新答案stream，无自动重抽。旧版1前五题仅只读判断保存输入是否仍适用，不自动补生成，也不把旧结果说成最新配置全量通过。

## 三、实现最小限定准入与跨进程账本

沿现有output_contract、product_risk、正式EvaluationService／execute_job／RealQueryExecutor、Run及题级执行关联实现默认关闭的`diagnostic_remaining_manifest_r1`。不要改已消费单题合同的授权文件／槽，不把旧v2静默升级，不关闭通用校验、不用私有SDK直连代替正式job。避免另造通用调度平台。

在本包新目录冻结执行manifest：Git授权来源、48个成员、实际control／target库与owner／kb、完整题集及split hash、源码／prompt／模型／SDK／endpoint身份、每题保存输入／引用／分组／预算、配置canonical hash与catalog文件hash、请求及题级稳定键。新的准入／源码身份须用新诊断配置和稳定请求，不重跑旧首次创建脚本、不修改旧Run；保留原父请求来源。配置文件hash和canonical用途分开。

一个批次身份绑定两个原控制库及唯一清单，不能换库／nonce／ledger／目录获得另一份额度。每成员固定slot；共享总量控制须跨进程和两库原子互斥，最多一个在途流。旧六流＋探测＋canary的已结算前值只计一次，共享账本不能在两版各自重置。磁盘started与数据库账户／执行关联共同约束，不能凭一个地方查空认定从未调用。

调用前原子占用成员slot、批次唯一在途位和预算预留，再联网；记录planned／started／settled。已成功只读复用；started无结算、超时、断流、usage未知或提交窗口不明时，全批暂停，保留占用，禁止换请求重试。恢复沿正式lease／continuation，只允许已证明无模型发出的恢复或成功检查点读回；不能手工清Run state／lease／retryable／slot。首次有实际发出即计一次额度，失败也不补额度。写入重试不能重新发模型请求。

先写揭露问题的合成红测，再修绿：未授权成员／跨版／改输入拒绝、重复／并发与同分库消费、跨库总额绕过、登记／关联及预留前后崩溃、发出后断流和结算窗口、成功恢复不重发、raw usage缺失／非法／矛盾／超限持久阻断全批、默认关闭与旧v2／已消费单题等值。使用随机短`m1_test_m4_`合成库；不写真实旧质量账本测试。覆盖实际SDK wire归一化前后的n=1及冲突参数入口，API变更时同步类型／OpenAPI。仅跑相关回归，不重跑已关闭整轮检查来凑数量。

## 四、全范围预检与固定profile

先对48成员一次枚举精确缓存、来源、授权、输入及恢复状态，不调用推理、不预创建全部job。通过正式消费者重建最新受审prompt／context／reference_map／groups／budget，与成员锚逐项全等。047只沿正式目录候选／澄清路径复用缓存，不用硬塞旧top3代替真实消费者；任何模型调用额度均为0。

完整52输入已有20份仅增加受审关系、32份不变；保留25题35必要单元、048比较双方／p30和原23次补充context未知引用。关系证明不等于行定位：LAN行unknown保持，不能把表p14升级为行页码。未在本批消费的旧5题只说明输入适用性，不偷补调用。

实时核本包目标及当前正式授权／修订／账户／固定槽／绑定；封存582／867全量审计可核hash复用，未重新扫描须明确限制，不冒充全量现场证明。精确缓存任何miss、身份或输入漂移均停止，新增编码／重排／导入／扩词／图摘要预算均为0。

固定运行：qwen3.8-flash；endpoint SHA256 `7cbf2306d7facc55fd08ea52e1d6891e0dc6bc6af6d5442df34f17403670ad2a`，不输出URL或凭据；langchain-openai1.1.11／openai2.28.0；n=1、temperature0.1、stream及stream_usage、SDK retries0、timeout120秒、无fallback／redirect。只发`extra_body.max_completion_tokens=4096`，不同时发max_tokens；thinking保持网关默认，不加开关、effort或budget。

source_branch_compare_v1＋attributed_assertions_v1＋已审对象关系不改；weighted .5/.5、20／20／20／20／10不改；context32768、请求output4096、reserve256、max_chars12000、每请求保守输入上限28416。禁止改prompt、分数／排序、预算或截短问题以通过。

Docker／Mongo若未就绪，可按既有runbook恢复本项目基础服务并等待健康；不得清库／prune／重建数据卷或启动worker，保持20m×3日志轮转。服务暂不可用记录为环境前置，不重开已关闭代码项。

## 五、预算与调用核账

本包最多46个新产品答案stream、48个单题job，其中2个047为0答案；非产品探测／额外模型审核／本地编码／重排／导入均0。上限不是必须用满的目标。

诊断累计前值input **28747**、output **22304**，由旧六流＋非产品探测＋已结算05-a各来源hash证明，不当作全项目总量。累计观测预算仍input **1477632**、output **212992**，不扩大。46×请求4096＝188416，加前值22304＝210720；这只是请求及观测预算安排，不是实际供应商付费上界证明。按每题真实保守输入预留，逐题结算后方可派发下一题；不把两个版本各当一份预算。

保留原始SSE usage，在SDK归一化前验证。缺失、负数、布尔冒整数、互相矛盾、output含reasoning后>4096、累计超限、finish=length／截断、正文为空、断流／异常均阻断全批后续，保留已用与未知窗口，不能补0或扣除reasoning。reasoning已含在output，不重复相加；visible token、精确HTTP和费用不可观测时null。观测到一次请求hook不宣称完整HTTP总次数。

## 六、逐题诊断与停止条件

每题真实完成并结算后，对照本题封存来源检查：对象／具名配件归属、限制与适用范围、连续引用、实际选中来源、完整性及截断。05-b／17-b不把配件特性套给机身；048须实际回答同轴／EoC比较，不以证据已进prompt代替答案完整；047只核澄清材料与授权候选，不沿旧低分认定路由错。不得把来源检索覆盖或测试数写成答案质量分。

这只是执行方来源诊断，不能代替独立双轮或改正式评分。若存在明确语义错误／缺答、来源不支持、critical、无法在已审来源内判定的实质歧义，先记录具体断言及输入→证据→输出链，封存当前题并停止全部后续。不得临场补词／改prompt／改模型参数／放宽标准／继续换规则或同题再抽。

若故障发生在模型发出前且可以证明调用0，可在新本包子目录修正驱动并完成相关无推理验证后继续同一未消费身份；保存失败，不改输入和额度。若已发出或是否发出未知则不得按此例外重试。语义失败时交付一个集中根因矩阵和下一项有证据的选择，不再自行开启修复生成循环。

## 七、交付与后续边界

私有材料只写全新`output/m6-remaining-diagnostic-20261101/`；若存在用不覆盖后缀。旧脚本先读后复制适配，绝不原地写旧证据；tmp保留，private-identity不读，.env只核变量名不输出值。output／evals／PDF／原流／缓存／日志均不上Git。

交付脱敏执行报告和验证JSON，含48成员逐项状态、真实新增调用／前值及累计、request／实验／Run／attempt／slot身份、精确输入与账本hash、已完成及未执行清单、source_checked限制、首失败／中间失败／红绿测、可复用证据与live扫描限制。私有逐题HTML展示问题、输入来源、答案／引用及原件证明；不重新找原件。检查数分别报告，不累计唯一总数、不充质量分。

更新PROGRESS、REVIEW_STATUS、TODO、M6任务、contracts、CHANGELOG／DECISIONS相关当前导航，保留历史。只显式暂存本包源码／测试／必要脱敏文档，检查diff和JSON后提交、普通push，核HEAD＝origin/main＝实际远程；失败如实记录，不强推。

所有48成员按合同闭合且无停止项，仅意味着本包诊断完成，回交总控独立复核真实效果、provenance和调用结算；不能自行验收05／08。后续正式新候选、政策／配置一致的独立双轮、有效gate及001真实feedback proof另按正式质量链推进，不复用诊断冒充正式质量证据。本包禁止评分、attest、校准、gate、feedback proof、heldout、默认切换、M7及子Agent。
