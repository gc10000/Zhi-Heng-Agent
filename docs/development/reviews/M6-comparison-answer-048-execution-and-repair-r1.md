# M6：048唯一真实调用与零调用补修

日期：2026-11-03。分支：codex/m6-source-bound-comparison。本报告是总控临时承担实现方后的执行记录与自验，不是独立技术验收。

## 结论

唯一授权的provider stream已消费，技术执行完成，真实完整比较答案未通过。已继续修复明确代码缺陷，未再次调用模型。新comparison_answer_v2显式开启；默认仍为v1，旧Run、答案和proof不升级。不能把原文呈现或离线候选写成048答对。

## 真实执行与计账

- 题：support-v1-048；题集：fb-07c584730833908571fe9dd7c7c890afa3cf9e66（150题，85 dev／65 heldout）；只执行048。
- 风险批次m6-comparison-answer-048-risk-r7，槽m6-comparison-answer-048-r7-support-v1-048。授权提交1381cb0448be5e9f84060f8d1256c37084a10622，执行源码提交d5760d605208f756a3533189403165f656aad637。
- experiment 47a30deb-12d9-41bc-8345-ecbae15e5165及Run 9d241bee-c2e6-443b-849a-001a5602b8ba均completed；正式result与outcome各1。completed不代表产品质量通过。
- stream1、invoke0，finish=stop，未截断。SDK原始usage有效完整：新增input1575／output37；历史53089／30412；累计54664／30449。reasoning明细、精确HTTP次数和费用null；网关硬限、付费输出上界unknown。
- 本机BGE-M3与reranker已实际加载，r6与r7均发生BGE编码，存在rerank阶段，精确rerank推理计数未提供。不能将执行包写为本地推理0。后续本补修和保存输入回放新增provider调用、本地推理均0。正式执行及结算存在真实库写入。
- 已通过正式ledger.review(accepted=False)和halt封存，state=blocked、pending=None、unknown_windows空、预留1／结算1／来源拒绝1。角色为实现方质量拒绝，不是独立验收；旧source-relation blocked账本只读核验未变。

精确输入身份：代码指纹a5e797fa886ed50df13bf04b798e40ec815d3384692c4e9aa5405a773222b1ed；config SHA256 83348ecd804f7202f78d029b95cd4fecce13b2645f92d1224edb2577ada823fe；manifest SHA256 c1ec5df3d5d52cd1448cb925c065d214bd3afb90c571c0ac1ecbeb6138a4e335；prompt SHA256 bfde72968f529a24e20d5fd1fbbe3626a512fb4e808441e8116f4f64a3bc8772。原始10份冻结输入留本机，不上传。

## 实际错误与修复矩阵

| 层次 | 反例 | 本次处置与退出条件 | 状态 |
| --- | --- | --- | --- |
| 分类 | H3C LA2608不能匹配完整端点LA2608 | v2在唯一产品冻结来源内匹配精确简称，拒绝LA26080、其他LA2608、LA2608-GM和多产品简称升级 | 实现自验通过 |
| 分类 | 用户通过有线／无线连接CB304n被判unknown | v2识别为客户端接入，仍禁止推成设备上联 | 实现自验通过 |
| 条件 | 条件位于完整scope，clause未包含条件 | v2检查完整scope的条件／否定，保守保持unknown | 实现自验通过 |
| 呈现 | 只说内部规则无法确定，用户看不到依据 | v2展示完整scoped_text；长代码围栏保留条件、HTML、图片、指令与资料编号为惰性文本 | 实现自验通过 |
| 缓存 | 已有自由答案可直接推送绕过比较证明 | 推送前重建冻结目录并核问题、策略hash、解释版本及完整proof，缺失或漂移拒绝且不泄漏 | 实现自验通过 |
| 恢复 | 新算法可能改变旧答案或协调降级 | 缺省v1；生成、完成核验、评测投影、缓存和失败记录均消费冻结版本；v2下协调替换v1答案与proof拒绝 | 实现自验通过 |
| 已识别关系覆盖 | 真实选择遗漏管理帧和Cable检查帧 | v2从同一冻结目录补入已识别关系；proof分别记录模型选择、补入帧、实际呈现帧及目录hash；空选择也不漏已识别关系 | 实现自验通过，真实质量仍open |

模型只选引用1帧0、引用2帧0、引用5帧0。真实管理关系在引用2帧1，Cable条件检查在引用4帧0，均未被选中。引用5所选帧缺发起端和用途，不跨帧补字段。模型原始选择保持不变；v2由程序补入已识别关系，未把补入帧谎报为模型选择。Cable检查仍不能推成链路已建立。

v2不是通用语义校验器，只在冻结关系内派生事实，条件检查保持保守。旧专属授权只接受v1，本包未修改风险档案、授权或正式配置来运行v2。

## 验证与失败保留

最终离线429 passed、1条既有Pydantic序列化警告，含OpenAPI一致性、归属、比较、原句绑定、输出合同、恢复和答案过滤。随机短m1_test_m4_前缀隔离Mongo29 passed，涵盖v1/v2同库／分库完成与复用、断流、非法选择、空证据、风险账本和原句绑定恢复；合成模型不计产品调用。

保存输入回放：10份冻结文档、原模型选择不变；旧v1答案和proof重算一致。v2识别客户端接入，并由known_frozen_relations_v1覆盖规则补入引用2帧1、引用3帧1／2和引用4帧0。proof新增catalog_sha256、supplemental_frames及rendered_frames，恢复重新派生并核验。答案明确客户端接入与管理连接不是同层关系，同时呈现Cable检查条件及完整原段；同一引用原段只显示一次。仍无满足当前比较器的device_uplink帧，v2仍为insufficient_comparison；它是离线候选，不是新正式答案。CitationGuard与AnswerFilter处理完整原文后内容一致。

3项行为红测、版本红测、缓存绕过红测、完整scope条件红测和空选择漏关系红测均保留。覆盖条件测试初稿使用未被现有抽取器覆盖的句法而失败（428通过／1失败），改用既有冻结语法验证同一条件边界后通过；不扩展已关闭抽取协议。阶段性24／139／20／38等通过数不累加成唯一测试数。r3源码指纹、r4审阅CRLF、r5内部Run合同、r6产品顺序前置失败保留；r4无Run，r5有conversation/checkpoint而无Run/link/outcome/provider，r6有failed Run且provider0但本地编码已发生。原summary中的null不覆盖为0，调用前错误名provider_invalid_response不代表供应商返回。初次集成前缀错误造成7项目标门拒绝已保留，修正前缀后通过，不是Docker服务阻塞。

私有证据：本工作树output/m6-comparison-answer-048-execution-r9/及output/m6-comparison-quality-repair-20261103-r1/。Run、输入、日志、候选原文及账本不上传。没有重跑历史1313断言整轮回放，不复用旧计数作为本包结果；未全量核真实向量、默认指针、TTL或旧质量库。

## 未关闭项

代码补修自验passed；独立技术复审open；真实048完整比较质量open；阶段验收open。M6保持5/7，04保持验收，05缺真实反馈复评proof，08缺有效候选质量和阶段证据；43题暂停，heldout65未运行，M7未启动。

本包已继续零调用修复已识别关系覆盖，保存输入中管理用途、客户端接入和Cable条件均能进入程序比较解释，模型漏选不再直接造成这些已识别关系缺失。该覆盖仅保证当前冻结目录内已识别关系，不保证未解析的unknown语义已经解决；不能把更完整的离线答复判成真实048质量通过。下一步唯一目标是对v2的覆盖／恢复直接边界做独立技术复审，并复评保存答案是否完整解释产品问题；不强行给same/different结论、不降低门槛。当前消费槽永久停止，本包不请求或执行再次调用。
