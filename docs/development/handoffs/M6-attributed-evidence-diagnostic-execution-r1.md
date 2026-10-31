# M6 attributed_assertions_v1 有界真实诊断执行指令 r1

2026-10-31，Asia/Shanghai。执行角色：有界诊断执行方；技术独立复核已完成，质量尚未通过。本指令将原草案落为可执行范围，不增加M6阶段门槛。

## 启动与固定边界

仓库`D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag`，Windows／PowerShell。先读适用AGENTS.md、PROGRESS、REVIEW_STATUS、TODO、M6任务、contracts、GIT_WORKFLOW、本指令及[本轮独立报告](../reviews/M6-candidate-evidence-quality-review-r1.md)。核对当前HEAD、origin/main和远程；业务审查对象为b6ce85acf8ec9b7e9b8694ac573219f92f5c6169，文档后续提交不改变已核app／prompt树身份。

本轮已关闭：047授权公开状态／候选和历史只读呈现、最终逐维选源checked、attributed_assertions_v1内部配置／编号／恢复接线。不要再开同一技术补修包、重复独立审计、重签001／p30／P2、重做基线或校准。旧v2两gate blocked、30下降／9混合／5变化和原source_checked保持。

本包允许启动以下有界诊断所必需的正式新实验／Run／题级执行记录及模型调用，条件是所有调用前置真实满足；已有授权不再要求用户找账号、PDF或手工评分。它只产出诊断，不签审、不写新质量评分／校准／proof；不创建新子Agent，不切默认、不运行heldout或M7。前置不满足时保存具体失败停止，不绕校验或默默扩修。

## 唯一策略、范围与上限

只使用已核通用attributed_assertions_v1及现有source_branch_compare_v1组合；默认入口保持关闭。模型期望hash沿草案`565fbfe4c795fb52f84183f7b2708491fd7824fa07f2de9fd546e9d6d6e5bb90`，实际名称、参数、模型及runtime_versions启动前从正式runtime核验，不从hash猜测。app树SHA为`bcbc147ce1183fb5cf774099c8080838bc11284919bc2939d346f6e3de9932da`，全部prompt树SHA为`5c0cb39e58800fc437c1f32b48b05540363ea8dbb8a147f5e030aa84a59aa9dc`；冻结时用正式runtime定义重新核对，禁止手写旧versions。

完整矩阵去重23题及4对象／配件对照，共每版27题，严格为：

- m6-g540-02-a
- m6-g540-02-b
- m6-g540-03-a
- m6-g540-04-a
- m6-g540-04-b
- m6-g540-05-a
- m6-g540-05-b
- m6-g540-09-a
- m6-g540-09-b
- m6-g540-10-a
- m6-g540-10-b
- m6-g540-11-a
- m6-g540-17-a
- m6-g540-17-b
- m6-g540-18-a
- m6-g540-19-b
- m6-g540-20-a
- m6-g540-unknown-01-b
- m6-g540-unknown-03-b
- m6-g540-unknown-04-a
- m6-g540-unknown-04-b
- m6-g540-unknown-05-a
- m6-g540-unknown-05-b
- support-v1-008
- support-v1-030
- support-v1-047
- support-v1-048

两版各047只做正式澄清／呈现对照，不生成答案；其余每版26题，合计**最多52个新增逻辑stream**，不重试抽样到满意。保留weighted .5/.5和20／20／20／20／10、窗口32768、输出4096、预留256、max_chars12000；新增输出预算上限212992，输入保守计数上限1477632，这些是预算而非实际token。精确HTTP与费用不可观测时null，平台usage缺失保持未知。

先冻结一个主manifest（两版本、全部题目与顺序、原件、产品、修订、p30证明、旧实验／Run／subject／原prompt／答案hash、新规则／模型／源码／prompt身份、调用上限）。两派生版本及其反馈来源分别保留，不能合并或串用来源；旧记录只是provenance对照。

## 逐题执行，实现首个失败即停

正式runner没有语义诊断后的自动逐题暂停钩子。**不要将27题整批交给execute_job后才检查失败。** 本包沿既有`question_ids`子集能力，在主manifest下预先冻结单题子配置／catalog条目；同一通用规则和预算，仅题目选择及实验身份不同。每完成一个正式单题job，保存调用与完整结果，完成限定原件／prompt／输出核对后才派发下一题。遇第一个技术或明确诊断失败，保存原输出、失败与余下未执行清单并停止；不改规则、重抽或增加调用。该粒度实现原草案停止条件，不需修改业务调度器。

请求稳定键使用fingerprint([master_source_sha, version, question_id, 'attributed-diagnostic-v1'])；逐题子配置hash、实际experiment UUID／attempt、Run和checkpoint由正式服务创建并封存。显式序号与执行顺序来自主manifest；同键重发必须幂等。每题调用前持久记录planned身份／来源／预算，调用后核started／completed与保存结果；未知窗口先按正式恢复查既存Run，不自动再调用，不重跑首次创建脚本，不手改state／lease／retryable。

使用EvaluationCatalog→EvaluationService→execute_job→正式QueryRunner。新配置／请求明确无quality_policy、quality_calibration_id、regression_source、regression_calibration_id和baseline_experiment_id；这是非验收诊断，不能对正式85题候选删字段后冒充通过。新题集不改原descriptor，完整85 dev／65 heldout范围保留，仅使用显式dev子集。原基线／校准和旧v2既不改写也不作为本次父候选或continuation来源。

只读预检必须核真实题集版本、来源／授权、四原件、隔离修订／chunk／p30、产品及新内部策略与当前快照一致。复用向量、已存双路候选及合格重排缓存；在正式消费者上证明所选范围全部可命中相同输入／模型缓存，再允许生成。任何缓存缺失立即停，不补编码、重排或导入；新推理仅限上述答案stream。新prompt独立身份的答案不能用旧v2输出冒充。

## 每题核验与退出

047须保持真实澄清、公开授权型号候选与运行状态；历史补充明确不是旧审核者已见材料，不回填评分。其他题分别核：实际模型prompt与映射；回答的完整断言、对象／配件／版本／实时未知边界；正文[n]与打印chunk_id的实际对应；附加步骤不得输出图标残片；缺资料声明限定当前摘录。048检查双方上联比较实际消费同轴／EoC／Cable正文及p30，不按词是否出现就判正确。

矩阵中6／21／3为执行方诊断分类，不是新评分。02-a原话是物理遮挡后“避免摄像头被使用”，不能重新表述为模型明确声称软件／硬件禁用；事实支持范围仍需核查。11-a／008打印标识错配及18-a残缺操作已被独立复现；18-a的[6]/[7]本身对应正确。不得因原页有图／正文就宣称模型收到整页，也不得按页级列表位置重编正文编号。

这一步是执行方有来源的诊断，不是第三票或真实双轮。不得预填2分、修改封存分、消除旧blocked或创建proof。完成全部固定范围时报告每题原输出、原件／输入／展示边界和失败；部分运行就保留未执行范围。无论成功或失败，本包都不自动扩大到170题生成。

调用记账分原基线／旧候选历史、本包累计、本次新增；已有已核范围336次逻辑stream、input644642／output355857是历史已保存口径，不是全项目总量。本包逐题新增usage有则记录，精确HTTP／费用未知为null；0只能用于真实证明未调用的047或缓存复用新增路径，不能覆盖旧未知费用。

退出后交总控评估新配置是否值得进入正式85题同范围候选质量链，并通过原服务核定基线／校准与新候选的可比性，不默认重生成基线、不跨身份套proof。M6仍5/7，04保持，05待真实反馈proof，08待有效候选质量链及阶段验收；human发布门槛独立，M7未授权。

## 证据与交付

本包用全新output目录；只读真实旧状态，任何故障注入仍用随机短m1_test_m4_合成库。不碰private-identity，不输出.env值。原PDF、完整答案／日志／缓存、output／evals不上Git，tmp保留。保存来源与调用manifest、失败和恢复证据，生成脱敏报告／JSON／逐题本机对照；更新导航保留历史，显式暂存、普通push并核对HEAD／origin／远程。技术测试数、词命中数和检索覆盖均不作为答案质量分。
