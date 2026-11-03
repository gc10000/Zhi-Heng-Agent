# M6两版反馈复评与阶段收敛工作包 r1

2026-11-03，Asia/Shanghai。接续ee3b5a7，用户授权完整工作包。本轮完成**一个实际平台阻塞补修、两版正式链现场只读核验、170项保存输入回放和下一完整候选关闭执行包**。没有生成新候选答案或反馈proof，M6仍5/7，04保持，05/08尚未验收。

## 实际补修

当前Windows工作树将两份已批准assistant-development-v1政策检出成CRLF，`policy_payload`原字节hash因此拒绝合法政策，并阻断真实基线质量/校准的重新核验。主工作区与Git批准版本均为LF，规范化后正文逐字相同；不是政策内容变更。新增真实Git `core.autocrlf=true`检出回归，先2失败/2通过，再在`.gitattributes`仅固定两份政策为LF并恢复批准原字节，最终4通过。未改政策hash、批准身份、rubric、旧质量记录或业务算法；篡改任一文档仍409拒绝。

该修复与本轮准备均为**总控实施自验**，未新增不同身份独立签字。原算法、准入及候选独立结论按原提交/范围保留，不把它们扩签本轮差异。

## 现场正式消费者结论

| 版 | 原反馈 | 已执行候选 | binding／calibration／execution links | 正式gate | proof |
| --- | --- | --- | --- | --- | --- |
| 1 | `c34496c4-c065-5765-93a5-4ba9a9167e55` | `ba08ba1f-ba61-4b8d-8dc4-3e76c0703216` | 有效／有效／85 | blocked；8下降，5未完整 | absent，正式409拒绝 |
| 2 | `ff45ecf4-4b82-5f3b-a31d-808ec5ae485e` | `8dfc2b43-584e-43d7-bb13-b1be764bfa72` | 有效／有效／85 | blocked；22下降，6未完整 | absent，正式409拒绝 |

两版基线均无incomplete/critical；现有001签审、派生、binding及校准有效，无需重签或重跑。各85条真实题级关联匹配当前attempt、Run、反馈来源、政策及控制/目标库。当前gate逐字段等于原封存gate，原因仍为applicability_changed、quality_regression、review_pending_or_changed；原分和分歧不改变。

实际调用`RegressionService.proof`均在409 `regression_proof_invalid`拒绝，未尝试绕过。来源hash漂移和85题校准套单题反例也被真实消费者拒绝。048 r2实际记录为completed/单题、无regression_source/质量政策/回归校准，不能倒填成反馈候选；其已有真实单题质量结论保持。

两已知质量命名空间前后40集合/1121条保护hash一致；这仅覆盖实际列明的evaluation_/regression_/support_feedback集合，**不是全业务库、向量、TTL或默认指针重扫**。所有正式服务使用只读代理，构造器索引不落库，意外写入硬拒绝。

## 完整范围与准备结果

两份完整150题逐项比较，只有support-v1-001的annotation身份不同；每份85 dev/65 heldout保持，不能把两条不同反馈来源合并成一条proof。已冻结两版各85题、输入hash、旧Run/subject、源码/prompt/来源、请求身份、题级checkpoint身份和全部170个拟派发槽。每版实际确定性规划为82 answer、1 series、1 compare（048）、1 clarify（047），与封存路由一致。

固定候选使用当前已审`attributed_assertions_v1`/`source_relation_spans_v1`，比较进入`connection_comparison_v1`完整来源装配，普通/系列保持现有回答链。完整4资料582冻结成员映射与旧同范围语料相同，不改变模型、embedding/reranker、weighted .5/.5、20/20/20/20/10或原题。**这套完整85题组合本轮只做保存输入自验，不宣称新独立或真实质量通过。**

170条保存输入回放最终通过：166条普通/系列prompt在实际保存正文/元数据/ordinal下保留全部原证据，编号连续且预算内；2条048从完整582标量重装配，与r6精确prompt/上下文匹配；2条047确认澄清，无生成prompt。输入来源为历史保存检索种子与r6标量，不是本轮真实检索、runtime临发核验或新生产输入冻结：**production_prompts_frozen=0**。

新关闭配置分别能通过正式来源、校准、政策消费者；正式服务对缺新范围准入及挪用已消费048合同各拒绝，共4个422，均发生在repo.create前。配置保持关闭，没有创建实验、Run、预留槽或授权。

下一完整范围最多168个provider stream，输入预算4773888、输出预算688128；这是新预算，不是usage/费用保证。固定qwen3.8-flash、n=1、不思考、SDK自动重试0、32768窗口、4096输出、256保留、输入28416、12000字符/10文档；首失败停止，无失败profile重抽。精确HTTP/费用/reasoning明细null，网关/付费输出/费用硬限unknown。诊断历史59589/30583和旧基线+候选644642/355857分账保留，不未经核重相加成全项目总量。

## 验证与失败记录

- 政策Git检出/内容保护：红2失败/2通过，绿4通过；严格原字节校验保持。
- 随机短m1_test_m4_隔离Mongo：68通过，覆盖政策、反馈谱系、正式job/proof、不可变审核修复。供应商及评分均明确合成；1条anyio已导入的pytest重写警告，非产品失败。
- 170条保存输入回放、两版真实链与4个正式准入拒绝均实际完成，不能相加成真实质量题数。
- 保留state-r1命名空间脚本错误；state-r2是真实CRLF阻塞；隔离启动器首轮库名前缀长度断言错误；prepare前三轮分别为合法Git读取钩子/Windows命令表示、错误要求85题均满足检索标签资格（原目录是32，质量审核仍85）；replay首轮遗漏保存ordinal导致166拒绝，补回实际字段后通过。除CRLF外均为本轮证据脚本错误，不写成业务红测或隐藏失败。

## 仍需完成的整个后续链

先在固定完整范围落实新的有限清单准入（不能套单题合同），定向独立技术复核后，按明确扩大到两版85题的调用/审核授权临发核来源、runtime、持久输入，顺序执行两版候选；同Run恢复只观察，首失败封存。再由两个新、彼此盲隔离的审阅身份各审核170结果，共340判断，按现有封存/独立性协议运输，保留unknown/critical/分歧。正式gate实际通过后由服务端生成两条反馈proof；未通过就按证据修复新候选，保留旧失败，不承诺首包必通过。

用户现有供应商授权明确落在已消费048单题；43题仍暂停。因此本轮没有自动扩大到168个stream或唤醒Agent。已备好范围/预算/关闭配置，下一次确认应一次覆盖新的有界调用与必要独立审查，**不是让用户选择架构、补路径或重评旧基线**。完整执行及验收材料见[后续指令](../handoffs/M6-feedback-stage-execution-r1.md)、[验收矩阵](M6-stage-acceptance-matrix-r1.md)。

私有证据：`output/m6-feedback-stage-closure-20261103-r1/`，最终准备目录`prepared-r4/`，原轮次不覆盖；脱敏机器摘要见[validation](M6-feedback-stage-closure-r1-validation.json)。本轮新provider/本地推理/真实质量写入/正式实验/Run/槽/proof均0；真实只读访问非0。未重复前端整轮审计或重hash权重。human发布门槛独立，heldout/Ragas/默认发布不增加为M6前置，M7未启动。
