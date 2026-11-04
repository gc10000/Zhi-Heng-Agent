## 2026-11-04 · 完整候选补修完成自验，独立技术与新真实质量仍open

已针对本批实际错误补修对象/配件/示例及限定/时序提示、内部规则与产品证据隔离、输出发布前整体验证和澄清呈现快照。最终389离线/契约、101随机短隔离Mongo、62前端单元、6浏览器、typecheck/build通过；早一轮67相关Mongo与最终轮重叠，不累计。170保存输入/582保存标量回放保留完整上下文、连续引用和分组，166提示改变、两份048保持；最大输入估算14327/28416，不是新实际usage或临发现场核验。

此补修由总控实现自验；既有三连接算法未改，原独立技术结论只保持原范围，新差异尚无不同身份独立通过。原168真实stream、170结果、340判断、两blocked gate及proof存量0不变；原批已halt且调用/委派范围已执行，不重领槽、不改旧分。补修新增真实provider/本地推理/真实业务库访问/委派均0。提示修订不证明真实对象/完整性错误已解决；澄清快照不回填旧结果或评分。

下一整包须对具体补修定向独立复核，并准备新批独立身份/准入与现场完整输入，再依对应新授权完成真实候选→结算→两轮独立质量→正式gate/proof→05/08判定。M6仍5/7，04保持，05/08open；heldout/M7/旧43/基线不启动。没有新增环境变量或API，OpenAPI一致；来源关系回答现在检查后整体发布。详见[补修交付及限制](../reviews/M6-candidate-quality-repair-r1.md)，以下历史按原时点保留。

## 2026-11-04 · 完整候选与340独立判断已完成，两gate阻断，M6保持5/7

两版各85真实结果/170 Run，168stream+2零调用澄清全部完成，实际输入809676/输出30791。新范围独立技术通过；两个全新Agent依次独立170判断，共340条正式记录/4seal/2attest。正式gate均blocked：22/21下降维度、各8题不完整，第二版2题wrong_object；两proof正式409拒绝且存量0。001/048两版双轮事实/引用均2，已成立边界保持。

两版completed恢复仅观察，新增stream0、账本hash不变；正式halt后cursor170/settled170/168stream、pending=null、unknown=[]，旧两个停止账户全等。05缺有效反馈proof，08缺有效完整候选质量和阶段退出；04保持，M6仍5/7。原低分/unknown/适用性分歧与critical不改；047候选与前端固定澄清文案的审核呈现限制单列，不据此放行。heldout/M7/旧43/基线不运行，human发布pending独立。下一项为证据驱动的完整质量修复；本批168授权已消费并封存，不能重试或重领。

详见[本批最终报告](../reviews/M6-feedback-candidate-execution-r1.md)。以下历史按原时点保留，不作为当前未运行状态。

# M6两版完整候选至反馈proof/阶段验收执行指令 r1

2026-11-04接续：用户已明确授权本文完整包（168stream及一个技术复核、两个新Agent顺序盲审），无需再次确认。新范围准入与生产消费者已实现，r5完整582标量/168prompt/2澄清冻结，最终309离线及152隔离Mongo通过；独立最终技术仍open，真实新调用/正式候选/评分/proof均0。当前源码、输入及执行入口见[本轮报告](../reviews/M6-feedback-candidate-execution-r1.md)，以下2026-11-03准备状态按原时点保留。

2026-11-03。固定方案由总控选择，不要求用户另选架构或查路径。本包当前为**关闭的完整范围准备**，尚无168流真实派发或新Agent授权。43题旧批次继续暂停，不借用其剩余槽；heldout/M7不运行。

本批独立170成功链已在补修前源码完整通过；随后整题后处理/发布出口4+6红测已补绿，最终源码309离线/152隔离Mongo通过，既定页面5项通过。最终r5已完整重冻，独立最终故障差异和输入重算已通过，95离线/77隔离Mongo/4正式故障绿；真实新调用/质量/proof仍0。

## 已完成且保持的证据

阅读[现场报告](../reviews/M6-feedback-stage-closure-r1.md)、[摘要](../reviews/M6-feedback-stage-closure-r1-validation.json)、[阶段矩阵](../reviews/M6-stage-acceptance-matrix-r1.md)。两feedback/binding/001/85题基线校准现场有效；旧两候选blocked（8/22下降，5/6未完整）与原分保留。048 r2真实单题通过及其review/halt/恢复保持，不能追认成反馈proof。政策LF补修只有总控实现自验，不扩签旧独立报告。

## 已配置的真实路径与身份

工作树：`D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.worktrees/m6-source-bound-comparison`。

- catalog：`output/m6-feedback-stage-closure-20261103-r1/prepared-r4/catalog/catalog-new.json`。
- 全170成员/预算/停止规则：`output/m6-feedback-stage-closure-20261103-r1/prepared-r4/dispatch-closed-private.json`，SHA256 `f9a6efe5a14f5cb87a720cb1fbbc7c8180f2bc6a6dc08ca394dd7012d9694d19`。
- 两完整请求：同目录`requests-closed.json`，SHA256 `ca66b7ecad1dbe4c9eb3512dc97066fe0bc1afc782c7d74dc917d160fcfa1230`。
- 配置：`stage-configs/1-candidate-closed.json`、`stage-configs/2-candidate-closed.json`（catalog内相对路径）；config_id `m6-feedback-stage-1-candidate`/`m6-feedback-stage-2-candidate`，version `r1-closed`。
- request_id：`m6-feedback-stage-1-candidate-r1-request01`、`m6-feedback-stage-2-candidate-r1-request01`，尚未消费。
- 各成员槽为`m6-feedback-stage-r1-v{1|2}-{question_id}`；实际170槽/hash/顺序已在清单，不需用户填写。experiment_id/run_id均null。
- 保存输入回放：`output/m6-feedback-stage-closure-20261103-r1/saved-input-replay-r2/`，170记录通过，尚非临发生产输入。

最终执行配置须在新的有限scope准入落地后新建版本/请求，并更新所有受影响hash；不能把r1-closed改写后还称已冻结版本或复用已消费槽。原目录只读保留，不原地运行排他脚本覆盖。

## 一次连续完成的实施与执行链

1. **新范围准入**：围绕上列完整两版85题/170槽/168流上限，扩展正式服务、客户端、CAS预留/usage/review/halt、调用前持久输入和恢复消费者。047计划各0stream；任何漂移或未知usage/思考输出阻断后续，首失败停止，无SDK自动重试。不能复制单题048授权、改旧账户、先创建实验再绕过校验。先红测并覆盖同/分库、并发单胜、断流/usage未知、持久输入失败、停止及恢复无新流。新包独立技术委派需明确授权，不唤醒原Agent冒充既审新包。
2. **固定一次最终候选**：复用当前普通/系列来源归属与原句关系、连接比较来源装配，模型/预算/检索固定。不得扩词/改检索/按题号注入答案。app/prompt变动后真实重算版本，新的授权引用与输入身份分离，批准政策原字节/hash保持。
3. **临发与执行**：扩大范围明确授权后，核实际4资料582标量/修订/产品及runtime/wire；每题实际输入先持久再调用。两版各85题，不减少同范围质量要求；每版048优先，其余固定顺序。预计各84stream+1澄清，总上限168。旧基线/001/校准不重做，服务端重新验证当前有效范围。首失败保存原件并halt，不“剩余预算”续抽。正式实验/Run/outcome/账本/控制槽经正式业务链，不手改state/lease。
4. **双轮真实质量**：两个新审阅身份依次独立盲审，每轮170结果，共340判断。第二轮不能读取第一轮评分；审核完整输入、实际呈现、原件及来源语境，不暴露expected。按question-purpose-v1与批准assistant-development-v1提交并封存；不假签human、不将总控实施自验当独立评分，不删unknown/critical/低分或用第三票消分歧。新委派须本批明确授权；不要求用户重做既有基线分。
5. **正式proof与阶段退出**：真实gate通过才逐版调用`RegressionService.proof`。核源绑定、基线校准、创建顺序、current attempt、题级Run链接、质量及保存前重核。blocked则保留失败并定位有证据根因，不改rubric/容差。proof实际存成后补固定对比/恢复与原要求页面流程，按矩阵验收05/08；不自动进入M7或发布。
6. **完整交付**：更新实际usage（未知保留null）、审查身份、原件hash和阶段结论；导航/记录/脱敏摘要齐备，显式提交普通push并核远程。原始输出/PDF/模型/账号不提交，tmp保留。

## 固定预算与边界

qwen3.8-flash，n=1，thinking=false，SDK自动重试0；每次请求输出4096、输入上限28416，窗口32768、保留256、12000字符/10文档。最多168个provider stream，**不保证精确168次HTTP**；新增输入预算4773888、输出预算688128，预算不等于实际或费用上界。网关硬限、付费输出硬上限、费用上限unknown；精确HTTP、费用、reasoning细目无证据则null。模型输入仅题目/历史/正式来源，不给expected。

当前诊断累计59589/30583、旧基线+候选644642/355857分别保留；不得直接相加成全项目历史总量。两数据版本仅001 annotation身份不同，但来源/policy/正式执行关联各自绑定，不能未经新协议用一批答案复制追认两份proof。

## 当前未完成

新的有限范围准入实现/独立复核、168流及新独立审阅明确授权、临发生产输入、真实完整候选/340判断/gate/两proof及最终阶段验收均未完成。关闭包已实际通过来源/校准消费者和4个准入拒绝，170回放不能替代这些证据。
