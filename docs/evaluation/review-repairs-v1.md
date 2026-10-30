# 已封存助手审核的限定纠错 v1

本协议实现既有 `assistant-development-v1`／`question-purpose-v1`，不修改批准政策或human发布规则。总控实现自验与其他会话的独立技术检查分别记录；修复服务通过不代表新独立判断已经存在。

## 固定来源而不是覆盖分数

每个已完成实验最多一个不可变case，绑定完整85题结果scope、题集／manifest／配置／政策／反馈、原两seal及全部保存评分hash、Git裁定和固定替换维度。总控管理员仅在原kb范围登记；原审核者不能自签case。已有校准的实验拒绝新增case，原记录全部保留。

case区分两种处理：

- `correct_actionability_na=true`：仅纠正明确题意不适用的步骤维度，`actionability_applicable=false`，依据是总控裁定。有效分为N/A，不代填0或2，不声明原审核者改过分。
- `replace_dimensions`：缺少可信独立证据的维度，需要固定的两次实际独立补证。第一轮封存后才能开始第二轮；每轮完整覆盖case授权的题目及维度子集，不复制未受影响题目、不投第三票、不按新分数选优。

两类不能在同一维度重叠。新事实不可N/A，步骤按case固定题意，实际答案图不可跳过；unknown、未核来源、新N/A／数值分歧继续pending。原critical保留，新critical加入，双轮有效数值仍取最低。不能用纠错清理关键错误或借换源重新挑高分。

## 正式接口与恢复

所有路径均以 `/api/v1/experiments/{eid}` 开始：

| 方法／路径 | 用途 |
| --- | --- |
| POST `/review-repairs` | 总控提交 `RepairInput`，登记固定case；全等重发幂等，冲突409 |
| GET `/review-repairs` | 协调侧查询case、执行／封存回执和缺项，不回显补证评分 |
| POST `/review-repairs/{case_id}/executions` | 审核者提交 `BeginInput`；独立执行ID不得复用原审核或生成执行 |
| POST `/review-repairs/{case_id}/executions/{execution_id}/seal` | 提交 `RepairSealInput.judgments`，每项只有授权维度的分数和逐维依据 |
| POST `/review-repairs/{case_id}/independence` | 非审核者的受控总控提交 `RepairAttestInput`，核验原保留来源及新固定对 |

`execution_id` 路径参数是begin返回的64位账本ID，payload里的execution_id保存实际任务执行身份。封存回执仅含id／sha256／created_at；限定评分以不可变repair seal为正式来源，不再复制到原 `evaluation_reviews`。原保存评分的唯一轮次索引和原seal保持。

case存在即禁止旧 `/review-independence` 整签旧对及旧unknown追加；未完成新核验时，旧attestation不能绕过case。新核验绑定case、原seal和新seal的hash及受控Git报告。原结果、评分、来源、时间、政策或封存变化均拒绝消费。case／begin／seal／attest写入后应答丢失，使用原请求和固定键重发，不能换ID重来。补证评分未知或不一致时停止，不通过另起case反复抽到通过。

## 有效投影和源码身份

`ReviewService._quality`仍覆盖全部题目和四维，保留 `dimension_sources`：每一维每一轮明确来自原review、新repair seal或总控N/A纠错。内存合成记录使用 `repair-projection-*` 身份，不冒充新原审记录。校准绑定全部来源，gate／候选校验／proof继续重读正式质量；来源变化不会变成旧校准仍有效。无case时旧返回结构与旧校准保持，human路径不消费assistant修复。

case另存 `review_code_sha256`。开始／封存／新核验必须使用登记时审核源码，原答案仍绑定旧生成配置。读取已封存有效来源不要求把旧生成code改成当前code；生成入口原有runtime校验继续严格保留。

候选需要当前源码时，新增候选配置v2及新catalog条目，保留旧catalog、绑定原配置和不可变evaluation_sets descriptor。正式创建只需登记题集dataset／manifest相同，原descriptor的configs快照不要求覆盖新候选；不得覆盖descriptor或重生成基线。候选必须绑定实际有效校准并晚于它，配置／请求／Run与检查点使用新的真实身份，不继承原基线检查点。

## 本次固定收敛范围

旧12题全新双轮方案收缩：6处明确步骤N/A由总控追加；真实独立补证仅6个题级结果，双轮12条题轮记录／24个维度判断。版本1补001四维和11-a步骤；版本2补001四维、01-a步骤、11-a步骤及unknown-04-b引用。原001标签签审／绑定无需重做。

两版001的旧expected暴露问题仍必须有新的真实无标签输入判断，不能靠本轮总控改分消除。unknown-04-b提供完整正文和实际展示来源，不能以无[n]机械判N/A，也不能以来源数量判2。047合理澄清保留，不要求强行生成答案。退出是两版完整85题有效投影无unknown／混合适用性／critical后正式预校准，随后同范围独立候选及双轮→真实反馈proof；M6-04／05／08按正式合同各自验收，不自动加阶段数字，不运行heldout或M7。
