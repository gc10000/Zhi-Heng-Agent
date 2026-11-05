## 2026-11-05 · 本提案已授权执行，r2已STOP

用户已明确批准本提案8stream与1位新审查者。正式资料导入后发生准备读取取消，随后发现自动接管attempt2，r2已永久停止，provider0。补修不解锁；不得再以以下历史申请文字重领未消费额度。见[实际出口](../reviews/M7-operational-r2-execution-r1.md)与[独立报告](../reviews/M7-operational-r2-independent-review-r1.md)。

以下为授权前提案原文，按历史保留。

# 修正来源的M7真实演示新批提案（尚未授权/登记）

本提案供一次明确授权决策，不是调用授权。r1已因准备资料丢事实而STOP/halt，即使provider0也不能复用；旧M6和r1账户/manifest/Run/宿主SQLite保留，未消费额度不转移。

## 唯一产品输入变化与可审阅目标

只将错误的删行来源替换为保留全部产品事实的CC0 `examples/preview/manual-operational-v1.md`，不调整模型、检索、预算、提示或质量要求。精确UTF-8/LF字节SHA256 `249c38af8708bb62cd15f058b70ddd31fc72ddfd0674c9eb70252c1e9a766b6e`，由.gitattributes固定LF；离线正式解析/切片6chunk、0图片、无外链，无推理。制作器只删原文唯一“本机预览禁用新增模型生成。”状态句，其他字符全保留。不能修改已导入错误原件来冒充新修订。

目标是自制资料的真实检索、1/2/4会话问答、恢复后的第08问及实际浏览器确认/待审反馈；不是M6候选质量验收。产品失败条件保持错对象、数量、前提/时序、引用错误或回答不完整；展示相关原文不能替代回答。

## 拟新增上界及已有消费

- 本批r1已有：provider0、本地embedding5文本/rerank0/pair0，usage/HTTP/费用null；不退款、不改旧账本。
- 新批最多8provider stream/8attempt，固定 `qwen3.8-flash`、n=1、不思考、temperature0.1、extra_body.max_completion_tokens4096且不带max_tokens、stream+usage、SDK retries0、timeout120、无fallback/redirect。每次输入28416，新增输入/输出预算227328/32768，context_window32768/output4096/reserve256/max_chars12000/context10。
- 新正式导入一次：1份资料/6chunk，document embedding6文本；8题每题单产品/原始单query embedding1，共8文本，合计新增14文本。源与恢复目标每题最多6候选，逻辑rerank最多8次、pair最多48，单次少于64无需分批；检索20/20/20/20/10和weighted0.5/0.5不变。未命中可少于上界，不能临时多查、多编码或warmup。HyDE/分解/规划/视觉等其他模型角色关闭；缓存命中减少实算但不释放预留。
- 跨两批可证本地文本上界5+14=19、逻辑rerank8、pair48；r1和r2分别记录，不用相加结果冒充r1剩余额度。新授权宿主上限应按14/8/48收紧；现实现固定64/8/512不能直接带旧授权运行，须先作最小版本化适配并定向复核。
- 接受网关遵从、付费输出硬上界及费用上限仍unknown；stream上限不等于精确HTTP次数。usage、reasoning、HTTP、费用缺失时null，reasoning若已包含output不重复相加。

## 拟新身份与准入规则

拟版本 `m7_operational_demo_v2`、batch `m7-operational-closure-r2`、槽01–08，均为提案名，尚未创建/登记/预留。现代码只接受v1/r1，不能只改环境绕过。授权后先最小适配、合成故障验证及不同实现身份复核，再生成不可覆盖私有证据目录；应用hash/镜像按届时实际新身份冻结，不能沿用r1技术签字充新差异通过。

创建新随机短 `m1_test_m4_` 合成源库/对象桶/向量集合、独立恢复目标和外置新控制账户；由prepare_preview按现有规则定位空闲回环端口，不要求用户填写路径或接触生产库。owner/kb/product、正式document/revision及hash均以新登记返回值填写清单，不预造已登记ID。独立控制账户不能被源/目标备份恢复回滚，也不能复用r1控制账户领取新额度。

每题采用原Prompt固定题文及波次 `[0,1,1,2,2,2,2,3]`；01–07查源，08按预定问题01查恢复目标。每题新会话/request键=`batch:slot`，Run UUID5(namespace URL, `batch:slot`)，正式API创建；无评测experiment/job，不伪称存在ID。正式导入job由API生成且attempt最多1。每波全部完成结算且无停止条件才进入下一波。

完整manifest冻结：实际来源登记/字节hash、权限、两组三元绑定、模型/SDK/端点hash、配置、8题身份和源码；每次执行再持久精确prompt、选中原文/排名/引用映射、保守输入估计、执行租约及合同。首题派发前独立核所有必要事实，尤其06整句；实际现场候选/分数由真实索引决定，不以离线静态数冒充已保存精确prompt。

## 幂等、恢复与停止

新目录/输入/原流均x-open；已存在Run/request只读复用，不能换request重发。模型前先冻结输入与正式Run关联，再控制库CAS保守预留；原始wire/SSE/usage/finish、结果/引用/终态和结算全留证。已开始/未知窗口只观察；同结算全等幂等，冲突拒绝。知识备份/恢复不带调用控制账户回滚，失败目标/claim不释放。

恢复08前只切新项目API/worker/dispatcher完整绑定，独立核新目标来源/索引/权限及控制账户不变；finally回切、停消费者/模型、generation=false。首技术失败、计量未知/矛盾/超限、思考、异常finish、断流、关键产品错误或来源丢失即持久halt并停止新派发，记录在途，不能承诺网络硬取消；本批不重试/补抽/退款。

## 授权前环境条件与请求

当前Docker间歇失败、WSL最后操作超时；原生Ubuntu仍未测。执行方先只读核依赖稳定，核r1 halt/无未知窗口、修正来源及新镜像/技术复核，不满足则停在具体前置，不耗模型；不以重启旧服务或机器解决。现有工程独立工作已完成或实证封存，不把M6全量复评当准入。

申请的具体新增范围为上述新批8stream、14本地embedding文本/8逻辑rerank/48pair、一次6chunk正式导入及相应恢复/浏览器链；仍仅本机合成空间，不含生产、heldout、旧题、公开发布。新的不同实现身份审查安排需明确授权，不能唤醒旧审查者或自行再派Agent。没有新授权不运行本提案。
