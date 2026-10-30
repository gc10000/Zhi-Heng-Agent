# M6 两版已校准独立候选与真实双轮执行 r1

日期：2026-10-30至31（Asia/Shanghai）。接续 `673d4b4e2621d9081f9c96a07f6a2d36203affe8`，开始及接续复核 HEAD／origin/main／GitHub main一致，开始仅未跟踪tmp/；本包不改业务源码、前端或历史答案。按用户附件和[正式交接](../handoffs/M6-calibrated-candidate-execution-r1.md)实际执行。

**两版候选均已完成，各85题；两名全新无父上下文助手顺序完成340条判断，4份seal及正式submit成功。质量仍pending。** 本包没有自签候选独立性，没有运行development gate或创建反馈proof。M6核心5/7、04已验收保持，05／08未验收，M7未授权。低分与下列范围问题均保留，不能以执行成功替代质量验收。

## 真实候选与冻结身份

| 版本 | 候选实验 / attempt | dev版本 | 配置 / 固定请求键 | 原基线 / 正式校准 |
| --- | --- | --- | --- | --- |
| 1 | `ba08ba1f-ba61-4b8d-8dc4-3e76c0703216` / 1 | `fb-07c584730833908571fe9dd7c7c890afa3cf9e66` | `m6-final-1-candidate/v2` / `m6-final-1-candidate-review-fix-v2` | `2b4307e3-2f03-46d7-850c-7d1054b1f8d2` / `69a95e6b-c3b1-4ee1-8523-bab605451a2b` |
| 2 | `8dfc2b43-584e-43d7-bb13-b1be764bfa72` / 1 | `fb-a3fa87c1adb2a6dc4e9638214164eb5f343ad008` | `m6-final-2-candidate/v2` / `m6-final-2-candidate-review-fix-v2` | `29d405dc-81c9-4b63-a35f-5abdcbea081c` / `379c925f-3bd9-4f2a-9607-e5a9679f0a2f` |

配置SHA分别为 `20fbcf3e47e7275b1dd01b24a2309ceaba287a5cbf77b76587866c0fc3e5aa26`、`b49c1bd7bf0689935bc13f0cb975f28029525e990ae09899d4c783733c981424`；effective config含本候选执行键，SHA见[脱敏摘要](M6-calibrated-candidate-execution-validation-r1.json)。两控制库分别为 `m1_test_m4_m6_review_562c2209ba994a1892074da324cc3025`、`m1_test_m4_m6_review_c1486a0a19d84c069d66d6abeff4709a`；共用冻结目标库 `m1_test_m4_m6_heads_fb825179effd4f0f`。正式完整请求原样消费，政策、regression_source、校准及权限不跨版本交换。

请求模型 `qwen3.8-flash`；已有本地BGE-M3及reranker按冻结配置调用，无自动下载，进程内禁用模型桥接，未改.env。runtime code=`6c241d6a82e0a395bc0ff665dfd7abb759dcb72267f5346a7aaef7a3dbe1aff0`；prompt=`f0fe0cc92fca8715957120515588f239ee15d1e4b3e0ba6c4c411dd176d5c52d`；model=`565fbfe4c795fb52f84183f7b2708491fd7824fa07f2de9fd546e9d6d6e5bb90`。保留source_terms→branch_heads→compare_context、weighted .5/.5及20/20/20/20/10预算。

复用的四修订如下，原文SHA全量见摘要，未重导入或切默认。

| 来源 | document_id | revision_id |
| --- | --- | --- |
| D1 | `4676940c-be2d-5142-a366-ea201c95a2bf` | `3dee2caf-2964-5de5-8742-78feb7705343` |
| D3 | `f82f3ec8-e6e6-5130-98a4-86d37155d3ce` | `b76f3252-8a62-58af-aace-aefe45b13d82` |
| D4 | `651e644d-19a3-53e4-b6af-1bb07970d90d` | `63964dd3-4321-5154-9599-744aea13956e` |
| D5 | `536d3f2f-8d4d-5d08-bc71-8ab7cca18562` | `55a81645-af3b-5ef4-ab07-cf6366dccf1c` |

每版均为84个completed Run＋1个awaiting_input Run，85条正式结果；各85条题级关联和检查点均与本实验、输入、来源、配置及输出hash一致。继承0，不复用基线答案或旧r3的19检查点。正式create回执先保存，再execute_job，未显式重试、恢复或换请求键。已完成job不可盲重跑。

## 调用核账

| 范围 | 逻辑stream开始 / 返回 | 观测input / output token | 精确HTTP / 费用 |
| --- | --- | --- | --- |
| 候选1本次新增 | 84 / 84 | 161358 / 85843 | null / null |
| 候选2本次新增 | 84 / 84 | 161358 / 101724 | null / null |
| 本次两版合计 | 168 / 168 | 322716 / 187567 | null / null |
| 原正式基线历史 | 168 | 321926 / 168290 | null / null |
| 上述范围累计 | 336 | 644642 / 355857 | null / null |

两版新增invoke均0，有持久Run实测与旁录支持；各85结果不等于85次stream。047保留合法澄清、0逻辑答案调用。所有本次产品及本地调用意图均匹配终态，无未结算窗口；这不证明底层HTTP无重试，HTTP／费用继续未知。

336仅为表中正式基线＋本次候选范围，不是全项目调用总数。旧r3 `79b3cc58-cfd4-4da5-84c0-890d92a9be06`的19继承＋66执行、历史stream19/新增61及未知HTTP/费用身份保持；旧失败`a5607e05-de22-4b24-9570-e85b7e09b521`的failed/attempt2/provider_invalid_response/retryable=false/results0及调用/费用未知保持，不据0行结果推断调用0。

每版本地encode为88次开始/返回、95条输入，rerank为84次开始/返回、1654个pair，异常0；本次共176次encode、190条输入、168次rerank、3308个pair。复用既有向量和进程内模型单例，未注入查询/重排结果缓存或固定分数。历史本地调用未知，不以本次计数回填历史。两个平台审核任务及其待命/审阅回合另计，精确模型、底层调用、token、HTTP和费用均null。

## 双轮来源与正式运输

每个新任务负责一轮跨两版170条，不虚称四个独立任务。两次spawn均明确fork_turns=none。先begin冻结纯输入，再开始实际审核；第一轮两版均seal后，才创建第二任务、begin第二轮。各轮只收到自己的纯输入与原PDF，未向第二轮提供第一轮问题、评分或回执。完整时序及4个执行/封存hash见摘要。

| 审核轮 | 实际审核任务 | 原始判断SHA256 | provenance SHA256 |
| --- | --- | --- | --- |
| 第1轮（含两版） | `/root/candidate_blind_round1_fresh` | `f7fe854f017b582a7b52f445b87595da140f376ecff2e2fd34ee59285d0a0759` | `8d5616714b4ecdbe2f9762a1bf0325f0ec2102996304d0cfac48c08a0655c0b6` |
| 第2轮（含两版） | `/root/candidate_blind_round2_fresh` | `2235ae2a87d757287588c4372a7ce58342d296dacd07a7be37f59385b95c1340` | `2cd7250ff43c61fd60e90452b26d8be520d6f19fbfea1ae5ee53874c1ceda3d4` |

上表每轮同一文件含两版，实际逐条baseline／question／subject绑定不同。纯输入无expected、annotation、基线/另一轮评分，四原件77个物理页；全部170条实际答案无展示图，context图片未充当答案图。原始输出、逐批初稿、实际提取/渲染页与工具访问记录本机保留。第一轮有输出截断与PowerShell引号失败，第二轮有控制台编码失败及其重读/修正，均由实际审核者留证，未删除失败。

正式begin、seal和submit均使用assistant身份、human_attested=false。340条逐题原始判断与seal及正式评分记录全等；协调端仅补正式服务身份，不产生或改动评分。独立性总控裁定为0，尚不声明新来源有效；任务声明与访问清单也不等于OS沙箱或完整平台后台轨迹证明。

## 已保留的质量结果与停止条件

raw critical=0、unknown评分=0，但不等于质量通过。两版047第一轮source_checked=false；第二轮true，两轮均给事实/步骤0、引用/图片N/A。两版Run实际均为awaiting_input，query_plan为clarify/model_required并保留产品候选；正式评分投影只有空answer、clarify标记及空citations，未包含query_plan/candidates/state。**当前低分针对该投影，不能据此认定合理澄清路由本身错误，更不能为凑答案数强行补答。** 只读对应证据在本机clarification-projection-diagnostic.json；保留原分，由总控核验材料与呈现范围。

9处维度N/A混合如下，不以第三票或改分消除，也不套用基线的旧纠错case。

| 版本 | 题目 | 维度 | 第一轮 | 第二轮 |
| --- | --- | --- | --- | --- |
| 1 | `m6-g540-unknown-01-b` | `actionability` | `not_applicable` | `2` |
| 1 | `m6-g540-unknown-03-b` | `actionability` | `not_applicable` | `1` |
| 1 | `m6-g540-unknown-04-b` | `citation_support` | `not_applicable` | `2` |
| 1 | `m6-g540-unknown-05-b` | `actionability` | `not_applicable` | `1` |
| 2 | `m6-g540-unknown-01-b` | `actionability` | `not_applicable` | `2` |
| 2 | `m6-g540-unknown-03-b` | `actionability` | `not_applicable` | `1` |
| 2 | `m6-g540-unknown-04-a` | `citation_support` | `not_applicable` | `1` |
| 2 | `m6-g540-unknown-04-b` | `citation_support` | `not_applicable` | `1` |
| 2 | `m6-g540-unknown-05-b` | `actionability` | `not_applicable` | `2` |

关注的019／021／022及四个对象/配件04-a、05-a、05-b、17-b，在两版两轮中事实与引用均为2；这只是当前未attest原始助手判断。048两版两轮事实与引用均为1：LA2608部分正确，但仍将CB304n上联写成依据不足，遗漏原件可完成的同轴/EoC比较；D5物理8／30页、D1物理4页已列于逐题依据。已关闭的检索/上下文技术结论不重开；必要正文到prompt不保证生成答案完整。不将非劣化或局部2分写成绝对高质量。

两版均因来源未核及上述混合停止后续证明。未正式调用gate，不能断言已退化或非劣化；未创建新attestation、calibration、candidate修复case或反馈proof。两条001绑定保持valid，既有签审/派生/绑定不重做。

## 实际检查与证据边界

调用前48项只读预检通过；两次真实候选与逐题核账退出0。收口5640项断言通过，包含原始/seal/正式记录全等、纯输入与实际原件hash、审核时序和历史保护，各组重叠不累计为质量分。

| 实际核心命令（仓库根目录） | 退出码 | 范围 |
| --- | --- | --- |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/preflight.py` | 0 | 调用前48项只读检查，已执行不重跑 |
| `.venv/Scripts/python.exe -u output/m6-calibrated-candidate-execution-20261030/execute_candidate.py 1` | 0 | 真实85 dev候选1，非stub |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/audit_candidate.py 1` | 0 | 85题Run/配置/来源/投影/调用旁录全等 |
| `.venv/Scripts/python.exe -u output/m6-calibrated-candidate-execution-20261030/execute_candidate.py 2` | 0 | 真实85 dev候选2，非stub |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/audit_candidate.py 2` | 0 | 85题Run/配置/来源/投影/调用旁录全等 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/build_packets.py` | 0 | 两轮各170条纯输入，4原件77页，无答案图 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/review_transport.py begin --round 1 --task-id /root/candidate_blind_round1_fresh --model unknown --receipt round-1-begin.json` | 0 | 正式begin；第一轮两seal之后才创建第二任务 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/validate_raw.py --round 1 --judgments output/m6-calibrated-candidate-execution-20261030/reviewer-round-1/judgments.json --receipt round-1-validation.json` | 0 | 仅结构与身份，不改分 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/review_transport.py seal --round 1 --judgments output/m6-calibrated-candidate-execution-20261030/reviewer-round-1/judgments.json --receipt round-1-seal.json` | 0 | 原始判断正式运输 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/review_transport.py submit --round 1 --judgments output/m6-calibrated-candidate-execution-20261030/reviewer-round-1/judgments.json --receipt round-1-submit.json` | 0 | 原始判断正式运输 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/review_transport.py begin --round 2 --task-id /root/candidate_blind_round2_fresh --model unknown --receipt round-2-begin.json` | 0 | 正式begin；第一轮两seal之后才创建第二任务 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/validate_raw.py --round 2 --judgments output/m6-calibrated-candidate-execution-20261030/reviewer-round-2/judgments.json --receipt round-2-validation.json` | 0 | 仅结构与身份，不改分 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/review_transport.py seal --round 2 --judgments output/m6-calibrated-candidate-execution-20261030/reviewer-round-2/judgments.json --receipt round-2-seal.json` | 0 | 原始判断正式运输 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/review_transport.py submit --round 2 --judgments output/m6-calibrated-candidate-execution-20261030/reviewer-round-2/judgments.json --receipt round-2-submit.json` | 0 | 原始判断正式运输 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/final_audit.py` | 0 | 5640项断言：原始/封存/正式记录全等与保护，不是质量门禁 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/clarification_diagnostic.py` | 0 | 047仅只读检查已保存Run与正式评分投影 |
| `.venv/Scripts/python.exe output/m6-calibrated-candidate-execution-20261030/build_readable_report.py` | 0 | 本机报告；分别保存原版与补充047材料边界的r2版 |

交付前检查首次将messages集合行数误报为消息正文，退出1，原脚本及delivery-validation.log保留；按字段结构确认仅为338整数计数后，r2检查退出0、3956项断言通过，170条本机对照及原件链接有效。一次只读inline Python引号诊断也失败，平台原输出保留；组合shell退出0不冒充内部Python成功。此处仅修正本机检查辅助脚本，未改业务源码、原始判断、封存或数据库。后续发布核对记录另存补充清单，不累计为质量分。

本包无业务/前端/API变更，未以额外全量测试代替实际质量链。240份本轮历史清单与609份既有保护清单分别匹配，两组可重叠；指定四库3557条旧记录中3555条非槽位记录逐行hash匹配，两条evaluation_slots正式job生命周期变化另列前后hash。新写入为2实验、170结果、170目标Run/关联/检查点、4审核执行、4seal、340条assistant评分及正式消息等；旧r3、旧失败、政策/基线/校准/001绑定均保留，无human／observation写入。run_events TTL、登录集合和凭据hash单列排除，不声称跨历史22集合全等，也未重扫live582／867向量。

本机目录：`output/m6-calibrated-candidate-execution-20261030/`。完整逐题报告为`两版候选与双轮原件对照-r2.html`（保留前版），含170完整回答、340判断、原PDF页链接与各维依据；用户无需重找原件。私有证据清单572份，SHA256 `b7018f4be514f92d4a1adde96eb6db7ba8ce7a1c6535bdb69f61766fdf6a2057`；这是生成时目录快照，不自包含清单本身或后续发布核对记录。原页、答案、流、日志、解析缓存、数据库快照和private-identity不进Git；tmp保留。

## 下一项动作与退出条件

**总控一次核验两任务的实际provenance，并集中裁定047材料/呈现边界与表中9维来源/适用性范围。** 若需纠错，使用已实现的不可变协议限定处理当前结果，保留原分，不能自动复用基线case、重生成基线、全量重审或第三票。执行方不代签。

有效来源与质量阻塞处理满足后，才对各自版本运行正式development gate；通过后分别为反馈`c34496c4-c065-5765-93a5-4ba9a9167e55`与`ff45ecf4-4b82-5f3b-a31d-808ec5ae485e`生成服务端复评proof。M6-05待真实proof，M6-08待候选有效质量链、05闭环及阶段报告总控验收；M6-04已验收保持。未新增human、heldout、Ragas或默认发布门槛，M7不启动。
