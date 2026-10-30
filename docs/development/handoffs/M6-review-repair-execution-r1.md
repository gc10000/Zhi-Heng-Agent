# 交给执行Agent的完整指令：M6限定审核补证及质量链接续

以下作为用户转交执行会话的工作指令。当前总控已经完成代码修复、隔离自验、两个正式case登记和六处N/A裁定；执行端不再开发同一接口、不重跑基线、不把明确规则纠错重送双轮。本指令仅为本次六个结果的真实限定补证授权两个独立审核子Agent，顺序执行，纯输入、无父会话继承；不授权其他开发并行或进入M7。总控本轮没有启用子Agent，也未替这两名审核者填分。

## 1. 先确认接续材料，不重做旧大轮

仓库 `D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag`。只读确认AGENTS、PROGRESS、REVIEW_STATUS和HEAD／origin／远程；保留tmp/，不清理历史。实现提交为 `6cc2040`（读取实际完整SHA），其后的同包文档提交是正常收尾，不回退。

先读：

- `docs/development/reviews/M6-review-correction-fix-r1.md`及脱敏JSON：本轮是总控承担实现的自验，执行端负责独立检查其限定接入边界，不将其误称另一位独立技术验收。
- `docs/evaluation/review-repairs-v1.md`：typed API、固定来源、封存与恢复。
- 本机 `output/m6-review-correction-fix-20261030/prepared-r4/coordinator.json`、`register-receipt.json`、`readback-result.json`及候选请求模板。

52项定向／契约、1项实际答案图边界、79项相关原协议回归均通过，各组重叠。真实676项只读读回通过。保留最初红测、并发失败、夹具配置错误和三次准备失败记录。只检查本包改动及直接失败矩阵，不重跑旧245／4077等整轮，不重开P2、p30、001消费、组合策略或continuation。

不重新运行prepare.py、旧创建脚本或register；所有正式case已经存在。可执行只读状态检查：

```powershell
Set-Location -LiteralPath 'D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag'
.venv/Scripts/python.exe output/m6-review-correction-fix-20261030/transport.py status
```

两个case已冻结原85题scope、原170评分和两seal、政策、反馈、配置和本轮审核源码。旧生成配置身份不同于新审核源码是预期行为，不因此重生成基线。候选v2已经在新的本机catalog准备好，旧descriptor／旧catalog不覆盖。

## 2. 固定范围，不再讨论或全量重审

| 版本 | 已由总控登记的步骤N/A纠错（无需新评分） | 需要真实新独立判断 |
| --- | --- | --- |
| 第一版 | 05-b | 001四维；11-a步骤 |
| 第二版 | 030、03-a、05-b、09-b、19-b | 001四维；01-a步骤；11-a步骤；unknown-04-b引用 |

真实新判断每轮仅6个题级结果，两轮12条题轮／24维度判断。001步骤按兼容识别固定不适用；01-a和11-a步骤适用，实际0／1／2／unknown由审核者判断。unknown-04-b引用不预定分数；同时给实际回答及完整展示来源。原数值1／2、1／0分歧继续取最低，不扩大复审范围。

协调Agent可以读取本交接和case。两名盲审者只读下列纯输入包与其中列明的PDF，不能读本交接、case、旧评分／expected／annotation、导航／执行报告、另一轮目录或其回执，连hash核验都由协调方完成：

- 第一轮：`output/m6-review-correction-fix-20261030/prepared-r4/blind-round-1/`
- 第二轮：`output/m6-review-correction-fix-20261030/prepared-r4/blind-round-2/`

每个目录已含中性README、六项完整真实items.json、原件路径及hash。四原件就在本机，不要求用户找PDF。六项正式答案和引用与旧包完全相同；新包额外保留原载荷retrieval_candidates和stage_timings，审核引用仍以实际回答和实际展示引用为准，不能把未消费检索候选冒充回答已用证据。数据本身无expected／annotation／allowed_evidence／评分字段。

## 3. 顺序完成限定真实双轮并正式封存

使用两个全新独立上下文，禁止继承本协调聊天（使用 `fork_turns="none"` 或等效隔离）；同模型允许，精确provider ID未知保持null。不得让当前协调聊天换ID写成两个新判断。

先建立第一轮审核任务，只发送“等协调方给纯输入包，不自行读项目文件”的启动消息，记录实际task ID和模型，再通过正式begin冻结输入清单。`<真实第一轮任务ID>`及`<实际模型名或明确未知标识>`必须填实际值：

```powershell
.venv/Scripts/python.exe output/m6-review-correction-fix-20261030/transport.py begin --round 1 --task-id '<真实第一轮任务ID>' --reviewer-model '<实际模型名或明确未知标识>' --receipt round-1-begin.json
```

begin成功后，给该审核者第一轮包的绝对路径和本轮独占输出目录。严格按包内README，阅读原PDF物理页；图标／指示灯等布局信息需要查看原页。不得附旧结论、预期答案或本交接的分歧表。

审核者直接产出JSON数组，每项必须含：`baseline`、`question_id`、`subject_sha256`、`scores`（仅授权维度）、`dimension_evidence`（同维度）、`source_checked`、`critical_errors`。另存provenance：实际task／模型／开始结束时间、实际输入清单及hash、独立性声明和无法核实的访问轨迹限制。原始输出先保存；协调方只能运输，不能改语义、代填2或删除critical。schema错误退回本轮作者修正并保留初稿。

收到第一轮实际判断后，用其真实文件路径封存两个case（运输器按baseline拆分，不修改评分）：

```powershell
.venv/Scripts/python.exe output/m6-review-correction-fix-20261030/transport.py seal --round 1 --judgments '<第一轮实际JSON文件绝对路径>' --receipt round-1-seal.json
```

两个case第一轮都封存成功后，才建立第二个全新审核任务。第二轮只给第二轮纯输入包；不要给第一轮回执、任务评分或补正。用实际第二轮task ID和模型begin，再由第二名审核者独立产出，正式seal：

```powershell
.venv/Scripts/python.exe output/m6-review-correction-fix-20261030/transport.py begin --round 2 --task-id '<真实第二轮任务ID>' --reviewer-model '<实际模型名或明确未知标识>' --receipt round-2-begin.json
.venv/Scripts/python.exe output/m6-review-correction-fix-20261030/transport.py seal --round 2 --judgments '<第二轮实际JSON文件绝对路径>' --receipt round-2-seal.json
```

这两个命令之间必须实际完成第二轮独立审阅，不能连跑空占位文件。实际执行ID由运输器记录任务ID＋版本／轮次后缀；后缀不代表独立性，真实两个任务及隔离provenance才是依据。

如写入后应答丢失，先只读status，再用完全相同任务／请求／判断重发，另选新的本机receipt文件名；不要换ID、换分数、手改数据库或覆盖旧证据。新unknown、未核来源、N/A混合或critical按实际保留；不重复抽审到同分，不追加规则或改预算。

## 4. 交总控一次核验实际来源，不代签

两轮完成后提交脱敏执行报告与JSON，列出两版实际题目／维度覆盖、原始输出和封存是否全等、任务隔离、输入hash、所有失败及真实调用记录。新平台审核推理与产品答案生成分账；精确token／HTTP／费用缺观测就null。不要把本轮产品答案调用0改写到历史168次stream。

执行方在此交回总控核验真实provenance。执行端不能仅因持有既有admin主体就自签新独立性；不要用本次代码修复报告代替尚未发生的新独立审阅核验。总控需要核验的是固定六项及保留原来源的合法性，不重做340条语义评分、不要求用户评分、不新发开发包。

总控通过后应提交真实Git核验报告，使用实际commit／路径／blob SHA调用已实现的attest入口。以下是总控操作模板，三个参数只能来自实际报告：

```powershell
.venv/Scripts/python.exe output/m6-review-correction-fix-20261030/transport.py attest --artifact-commit '<实际总控报告完整commit>' --artifact-path 'docs/development/reviews/<实际总控报告>.md' --artifact-sha256 '<该commit中报告blob的SHA256>' --receipt scoped-attestation.json
```

## 5. 核验有效后，直接校准与候选，不再修接口

取得有效attestation后，正式质量须两版各85题、四维全部有明确来源，无unknown／适用性混合／critical。满足才可执行：

```powershell
.venv/Scripts/python.exe output/m6-review-correction-fix-20261030/transport.py calibrate --receipt baseline-calibrations.json
.venv/Scripts/python.exe output/m6-review-correction-fix-20261030/transport.py candidate-request --receipt candidate-v2-requests.json
```

前一命令创建两份真实校准，后一命令只读生成绑定实际calibration ID的候选请求，不创建候选。若任一门禁失败，保留失败题／维度、实际来源和具体原因，停止该版本，不修改分数来过关；不要再把状态笼统写成“审核证据无效”。

候选使用本机 `prepared-r4/catalog/catalog.json` 中两个 `m6-final-{1,2}-candidate/v2`，控制库／owner／题集／反馈／政策分别按coordinator及请求回执，不跨版本共享校准。旧evaluation_sets descriptor和旧绑定配置原样保留，不重新register_set。模型桥接环境与原冻结一致，本轮准备明确禁用MODEL_HOST_URL／MODEL_HOST_TOKEN，其他模型身份按正式配置核对；不改.env或输出凭据。

真正开始候选调用前，先说明两版各85 dev的精确版本、config SHA、请求／实验／Run／题级身份、来源、检查点和恢复、累计与新增账本，以及可观测usage和未知费用。用正式EvaluationService创建并保存真实回执，再由正式job执行；不重跑首次创建脚本，不沿用旧19个检查点，不把基线检查点充作独立候选。按已授权质量顺序推进同范围独立候选及真实双轮→总控来源核验→development gate→反馈服务端proof。两版分别证明，不跨版本复用。

本包没有运行heldout65题、切默认或进入M7的授权。M6-04／05／08仍按各自合同实际证据验收，不能因接口测试或覆盖提高就自动勾选；也不新增human／heldout／Ragas／默认发布前置。

## 6. 本执行包交付及停止条件

最小完整交付：12条真实限定题轮正式seal及两份provenance链、逐维结果／失败矩阵、旧来源保护、调用分账、脱敏报告和JSON、导航更新及显式暂存／普通push／远程核对。原始答案、PDF、缓存、日志和审核原始输出仅留本机新output目录，private-identity不读不上传，tmp/保留。

在新独立性总控核验之前不创建校准／候选／proof。该核验通过后按第5节直接继续既定质量链，不再安排“实现审核纠错接口”的循环。若发现真实代码缺陷，给出最小反例和对应固定边界，由当前总控负责修复；不要擅自改case／源选择／分数／身份或扩大质量门槛。
