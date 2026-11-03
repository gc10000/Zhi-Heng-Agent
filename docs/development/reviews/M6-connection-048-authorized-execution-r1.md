# M6连接048完整授权执行、零供应商调用失败及顺序补修

2026-11-03，分支codex/m6-source-bound-comparison。用户已明确授权048完整流程并接受网关/付费输出/费用上限unknown；本轮连续完成授权Git绑定、全量输入准备、现场核验、正式job、失败审计、停止封存及根因补修。正式任务在供应商前失败，**没有新答案或真实质量通过**。M6保持5/7；04已验收，05反馈复评proof与08候选质量/阶段证据open，43题暂停、heldout65/M7未启动。

## 授权与实际执行

授权正文commit=`fafd2ca5dea8a987b71bc93add1db31149269430`，引用启用commit=`5a73e3e90ea3ff7c2dcaf9064d38dcdeaf4dab9e`；正文及引用路径为本目录M6-connection-comparison-048-authorization-r1.json、authorization-reference-r1.json。固定引用须与HEAD原字节一致且只指本批GitEvidence；缺引用关闭，未提交/漂移/旧路径拒绝；限定LF属性防止Windows自动CRLF使原字节核验失效。该接线避免源码hash→输入anchor→授权Git→源码hash循环，没有放宽配置、来源或prompt全等要求。catalog默认仍关闭。接线为总控实施自验，不追记成旧独立报告已审。

固定qwen3.8-flash、n=1、thinking=false、SDK零自动重试、4096输出/28416输入约束，单dev048，无扩题。实际重新hash模型权重及runtime匹配；四次Strong标量查询取得4资料582成员，与r4完整装配全等；运行时又实际走检索/重排和来源校验。本轮不是零本地推理或零真实业务读写；本地embedding/reranking已实际执行，未单独计数。真实写入限定本次正式实验/结果、会话/Run/events/checkpoint/link与comparison_generation_inputs，不手改失败Run或旧账户。

experiment_id=`0c3c2f9c-811f-475f-a418-3f42c20f32b3`，run_id=`0eeb1e48-b010-4eec-b129-31aa88226d10`，attempt=1；Run/实验均failed。持久遥测invoke_started=0、stream_started=0，token input/output=0/0。执行脚本最初因无settled文件把provider/usage写null；最终只读Run审计核清是调用前已知零，不能当成已调用但未知usage。旧累计56239/30516保持；精确HTTP/费用/reasoning明细仍null。没有新账户、started、逻辑预留或settlement，不能伪造结算或ledger.review；通过正式halt方法封存停止文件，确认旧r8指定账户blocked/settled/拒绝/halt保持。失败审阅为“执行拒绝、无答案”，不是产品答案质量评分。

## 实证根因与补修

离线freezer使用封存r8的检索后product_snapshot顺序（CB304n、LA2608）写item_names；正式adapter按题目product_names创建input_product_snapshot，QueryRunner先按原输入顺序（LA2608、CB304n）展示。实际Run与冻结输入的来源文档、引用映射、装配、分组和去policy预算均相同，仅型号展示顺序导致精确prompt不同，validate_prompt在账本预留/stream前拒绝。粗粒度终态码为provider_invalid_response/stage=answer；不把该码误解为供应商已返回坏答案。

调用时冻结prompt SHA256=`9c1f2941f40f274aeba9d03453f5724c5ccea3135b7ab728f5c44af24319c2fe`；根据真实Run保存输入重算的正式prompt为`dd72ee38868e3b0780d5fcc670ecad3f01e10aebb4a004bd85884c69f099b225`。保存输入双分支实测：正式顺序被旧准入拒绝，改回旧selected顺序则通过；其他四项输入全等。未再次执行真实任务来诊断。

补修仅令connection_048_inputs.assemble_input依原题产品名顺序呈现已选产品，再补检索新增产品；比较product_ids、来源装配及算法不变。新增正/逆序定向反例，首轮1失败/1通过；补后83离线通过。新增4项同/分控制库、正/逆原题产品顺序的正式job合成验证，直接把真实QueryRunner捕获的prompt与freezer产物比较，4通过；资源及模型为合成，Mongo实际执行，不冒称真实模型质量。三已审算法hash保持。

## 修后完整候选与证据身份

新候选`output/m6-connection-comparison-048-input-r5/`：完整4资料582保存标量重放、10文档连续1–10、10340/28416保守输入，无省略。pool取本轮临发实际四次只读结果；修后未新查现场或运行检索/模型。anchor SHA256=`0ef711349aac0628e89051a7b7eed9a61d265f873d2a3886763b171d1bcf62ef`；code canonical=`765f62502e3aef14016567547ec164ab961aebadc0370d4a751f22761d245ef9`；prompt SHA256=`dd72ee38868e3b0780d5fcc670ecad3f01e10aebb4a004bd85884c69f099b225`。修后prompt与真实失败Run保存输入重算结果一致；调用前独立comparison_generation_inputs记录hash亦已重算匹配，原记录未补签。r1–r4与失败证据全部保留。

原独立报告M6-connection-048-independent-review-r1的结论/身份及三算法关闭保持。本轮新增授权引用接线与freezer顺序补修只有总控实施自验，**尚无不同实现身份对这两项补充变更的独立复核**，不借旧结论签新候选。真实答案质量继续open。

本次授权已按首失败停止封存；不自动重派、不退款/重领/解锁或更换槽。r5为关闭catalog的新准备材料，不是第二次调用授权。下一项是对两项补充变更定向技术复核，并在新单题明确授权下验证真实完整答案；不重开既有算法关闭项，不扩到43题/heldout/M7。用户未授权新的委派，本轮未唤醒/启动Agent。

## 验证与失败历史

- reference-red：5失败，缺失加载器的真实红测。
- reference-green首轮：30失败/35通过，PROJECT_ROOT误沿主区，缺prompt文件；修正工作树环境后65通过，原日志保留。
- order-red：1失败/1通过、16 deselected；order-green：83通过。
- order-formal：4通过/51 deselected，随机短m1_test_m4_隔离Mongo；不删除测试现场。
- r4/r5完整输入冻结、临发核验、失败审计/停止封存及最终保存输入审计均完成；原正式失败不改写为成功。

私有证据`output/m6-connection-048-authorized-execution-20261103-r1/`；机器摘要记录各日志/XML/hash。原始output、账号元数据、来源全文、模型/日志及PDF均不提交。证据范围没有全库新扫向量/TTL/质量库或重新前端审计；没有前端/API/环境变量变更。
