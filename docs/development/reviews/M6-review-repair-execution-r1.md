# M6 六结果限定独立补证执行 r1

日期2026-10-30。接续 `82b8020c6b552e82fe501203912e534379855636`，HEAD／origin／GitHub main一致，开始仅未跟踪tmp/。实现为 `6cc20409120e586cd14c542505535199ba423e61`，其后为同包文档；不回退。按[固定交接](../handoffs/M6-review-repair-execution-r1.md)及用户明确授权，**两个全新、无父会话继承的审核任务顺序完成六结果补证，12条题轮／24维判断已正式封存；仍须总控核验实际provenance，执行方未代签。**

## 实际来源与隔离

- 第一轮 `/root/repair_blind_round1_fresh`、第二轮 `/root/repair_blind_round2_fresh` 均实际使用 `fork_turns="none"` 创建。先发等待消息，正式begin后才给本轮纯包和独占输出目录；第一轮两个case均seal后才创建第二任务。不是协调方改ID评分，也未复用原大轮任务。
- 只给各自 `prepared-r4/blind-round-{1,2}/` 的README／items／original-sources及列明PDF；第二轮未收到第一轮判断、摘要、目录或回执。原件布局由审核者直接渲染查看，实际文件清单、hash、原页与时间保存在各轮provenance。精确模型ID无法确认，两者均null，begin使用明确unknown标识。
- 两轮items的SHA256均为 `d7f304f32ef46c070ce14e5aa8441982e1972d4c48df6d08a261fc1dc6ddf388`；README为 `c08a461b4e832f897de943f2d8e3a72396231f65257081f786e7d833c35e3528`；原件清单为 `ecf6f84559e78a7b872d45d2d66e75a6b135207ddff963cc6ad5193678899d9c`。逐题hash、授权维度及完整结果均核对，递归未发现expected／annotation／allowed_evidence／scores字段。
- `fork_turns=none`和限定发包是真实平台操作；文件系统没有OS级隔离，不能以审核者声明证明工具后台绝无其他访问。执行方只报告实际provenance，不自签独立性。原始判断不改语义，仅运输器按baseline拆分并去除运输字段baseline。

## 逐题实际结果（assistant身份）

| 基线 | 题目 | 第一轮授权维度 | 第二轮授权维度 |
| --- | --- | --- | --- |
| 1 | `support-v1-001` | 事实 2；引用 2；步骤 N/A；答案图 N/A | 事实 2；引用 2；步骤 N/A；答案图 N/A |
| 1 | `m6-g540-11-a` | 步骤 2 | 步骤 2 |
| 2 | `support-v1-001` | 事实 2；引用 2；步骤 N/A；答案图 N/A | 事实 2；引用 2；步骤 N/A；答案图 N/A |
| 2 | `m6-g540-01-a` | 步骤 2 | 步骤 2 |
| 2 | `m6-g540-11-a` | 步骤 2 | 步骤 2 |
| 2 | `m6-g540-unknown-04-b` | 引用 2 | 引用 2 |

001两份独立答案分别核对D1物理第1／4页版本与兼容范围，步骤及答案图按实际不适用说明；两版11-a依据D3物理第9／20页安全处置；第二版01-a直接查看D3外观图及物理第4页指示灯条目。unknown-04-b核对完整实际拒答及实际展示来源，不把未消费的候选当答案引用，也未用静态手册断言当前固件值。逐维原文依据、完整回答及展示引用仅留本机，不上传。两轮unknown 0项、未核来源 0项、critical 0项；分值不等于独立性通过，未改变原1／2或1／0取最低规则。

## 正式运输与恢复边界

沿用既有两个case：基线1 `2f555874f0571693639f78f156dc76d3cef000b386422021c7053afb30d2c851`，基线2 `941d22cd51e9afca2d93ecdf55bba812701ccd6ccb7e0623c38559c2dd1b3ed3`。没有重新register、prepare、重生成基线、全量重审或修改旧评分。新增4个限定执行、4个repair seal；两case共12条题轮判断内嵌seal，未复制到evaluation_reviews。

每轮正式begin、seal的命令退出0；任务ID加入版本／轮次后缀仅用于账本身份，不冒称后缀独立。原始JSON与正式封存逐项全等，case、原170评分／两seal、源码及完整85题结果身份由正式case读取复核。source manifest固定本轮纯包和原PDF。若应答丢失应按原任务／请求／判断重发、另取本机回执文件名；本轮未发生写入应答丢失或重发，不造故障统计。

## 实际检查与失败保留

所有命令在仓库根目录运行，实际完整参数、回执及stdout／JUnit保存在新output目录。

| 命令 | 实际结果 |
| --- | --- |
| `.venv/Scripts/python.exe output/m6-review-correction-fix-20261030/transport.py status` | exit 0，先只读确认已登记case |
| `transport.py begin --round 1 --task-id /root/repair_blind_round1_fresh --reviewer-model unknown --receipt round-1-begin.json` | exit 0，两库真实begin |
| 第一轮只读schema／六题身份检查；`transport.py seal --round 1 --judgments <本机第一轮judgments.json绝对路径> --receipt round-1-seal.json` | 均exit 0，两库seal |
| `transport.py begin --round 2 --task-id /root/repair_blind_round2_fresh --reviewer-model unknown --receipt round-2-begin.json` | exit 0，晚于第一轮两个seal |
| 第二轮只读schema／六题身份检查；`transport.py seal --round 2 --judgments <本机第二轮judgments.json绝对路径> --receipt round-2-seal.json` | 均exit 0，两库seal |
| `M1_TEST_DB=m1_test_m4_repair_exec_<随机8位>`，`.venv/Scripts/python.exe -m pytest tests/unit/test_review_repair_schema.py tests/integration/test_review_repairs.py -q --junitxml=output/m6-review-repair-execution-20261030/scoped-regression.xml` | exit 0，44 passed，137.39秒；合成随机隔离库，无真实模型，检查固定子集、拒绝、顺序、幂等、应答丢失、源码漂移、原critical、同／分库候选消费 |
| `.venv/Scripts/python.exe output/m6-review-repair-execution-20261030/audit_execution.py capture`及`verify` | exit 0；只读verify 4212项，原始判断与4个seal全等 |
| `.venv/Scripts/python.exe output/m6-review-repair-execution-20261030/validate_provenance.py` | exit 0；91项可见文件allowlist／hash／begin-审核-seal时间／限定维度适用性检查，不签独立性 |

这是执行方对本包限定接入边界的实际检查，不将总控实现自验称为另一位技术验收，也不重开旧P2／p30／001／组合策略／continuation。组间不累计为质量分数。协调初读曾按交接列表误到prepared-r4下寻找register-receipt/readback，发现实际在上级后改用真实文件，只读失败无数据写入。两审核者均记载一次本机stdout的GBK编码失败后改用UTF-8；平台工具输出和其轨迹保留，第二轮明确声明首次脚本版本未单独保存，不宣称失败日志／OS轨迹完整外部审计。两轮判断初稿均保留，没有覆盖旧失败或为了同分追加审核。

## 数据保护、调用与正式门槛

只读核验609份历史保护文件及3547个既有Mongo行hash，均匹配。与登记后快照比较，真实相关库变化仅允许限定executions和repair seals；四库其余非TTL集合摘要不变。run_events／login_sessions／login_attempts的时效差异继续排除，users仅核公开身份投影，不读取private-identity或凭据值。未重扫live向量，未据此宣称582／867向量全量复核；默认语料／指针未执行切换。tmp／output／evals和原始PDF／日志均保留且不上传。

本轮有2个新平台审核任务，推理token／HTTP／费用不可观测为null。产品答案生成stream／invoke、编码、重排均未执行，新增0；**历史168逻辑stream、input321926／output168290及HTTP／费用null原样保留**，不被本轮零答案调用覆盖。没有写human评分、本人声明、正式独立性attestation、校准、候选或proof。

| 正式项 | 本轮实际满足 | 尚缺 |
| --- | --- | --- |
| M6-04 | 固定六结果新双轮已seal，原来源与规则纠错保留 | 总控新来源核验及有效attestation，完整85题四维质量投影后正式预校准 |
| M6-05 | 001既有标签／绑定保持，本包不重做 | 有效校准后同版本候选、双轮及服务端反馈proof |
| M6-08 | 原冻结／预检关闭保持，本轮限定补证完成运输 | 候选真实质量证据、proof及阶段总控验收 |

**唯一下一动作：总控核验本轮两份真实provenance及保留原来源，提交真实Git核验报告后调用既有attest。** 执行方不持admin代签。核验有效且完整门槛满足后，按交接正式命令直接`calibrate`、`candidate-request`，再说明调用身份启动候选；没有理由再开发同一纠错接口或重生成基线。现在两版attestation均空、各85题incomplete，故未越过该门禁。

脱敏逐题hash、任务／seal／输入及原始文件hash见[验证摘要](M6-review-repair-execution-validation-r1.json)；完整本机对照为`output/m6-review-repair-execution-20261030/index.html`，无需用户找原件或重填判断。

**M6仍4/7，M6-04／05／08未验收，M7未启动；不运行heldout，不增加Ragas或默认发布前置。**
