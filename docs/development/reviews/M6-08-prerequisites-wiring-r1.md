# M6-08：默认关闭的QueryRunner来源前提正式接线

日期：2026-10-28。接续`302df6fd3ee1378ed3b2fab8f0d010d4c033e896`，起始HEAD/origin/main/GitHub main一致，工作区仅tmp。依据前轮独立通过方案实施，顺序执行，无子代理。提交SHA与同步结果在最终交接补记。

**已实现内部显式、默认关闭的QueryRunner接线，固定配置/请求/Run/检查点身份、有界授权读取、最终分组/引用及关闭回切。** 25题保存weighted结果经正式选择消费者回放，context/groups/prompt/预算逐项一致，原21题均保留；没有新增真实检索/重排/答案生成。本次正式接线只完成执行自验，不能冒称独立验收或答案质量通过。

保留weighted .5/.5、20/20/20/20/10，不采用RRF。来源前提算法本身未改，SQ、continuation和图片关系协议已关闭结论保留。M6仍4/7，04/05/08未验收，M7未授权。

## 接线与请求身份

新增`SourcePrerequisitePolicy`严格配置：默认enabled=false，function_version="1"，max_added=4（0..4）、max_chars=6000（0..6000）、max_rows=1000（1..1000），未知字段/非法类型拒绝。启用必须给scope：组织、kb、确切隔离database/collection、完整document→revision映射和允许产品；数据库与集合必须m1_test_前缀。公开HTTP RunInput没有新增字段；不新增环境开关，不改实际.env，.env.example仅注明内部配置边界。

`InternalRunInput`只供受信执行器，规范化配置在RunRepository.prepare计算身份前进入字段；非缺省配置连同SHA保存至新Run。缺省关闭维持原请求指纹，旧Run不回填。QueryRunner在业务知识读取/检索/模型前对照已保存配置，启用/关闭/预算/范围不一致或SHA异常报execution_config_conflict，经原失败/租约协议收敛。相同内部请求重放同Run，改变配置不能复用同请求；重建adapter也复用同配置已完成Run。

`EvaluationStrategy`显式接受parameters.source_prerequisites；resource构造及RealQueryExecutor设置均传给QueryRunner，创建Run时用InternalRunInput。现有完整config→question检查点/请求键及continuation相同配置验证自然包含此项，配置不同创建新检查点，不迁移或继承旧19完成记录。合成adapter用例证明同配置1个检查点/1次合成输出，改预算后新Run/第2检查点，旧结果保持。没有创建真实候选或实验。

## 授权读取与组合顺序

启用只接受原weighted策略，并拒绝同时开启旧邻接扩展，避免两套selected/groups预算拼接。关闭继续旧expand_evidence路径，不读取前提；旧扩展既有能力未取消。QueryRunner逐产品和冻结资料/修订鉴权，核数据库及索引集合与scope精确相等；scope修订映射须与本次冻结快照相等，本题产品必须是scope子集。

`V2Index.prerequisite_rows`先核所有种子属于冻结doc/revision/产品，再逐修订查询。过滤包含owner/kb/document/revision及本题product_ids，仅读取种子所在资料，不读租户全库；每次limit=剩余max_rows+1，超过总上限即拒绝，不能截断后猜关系。所有装载行再经owner/kb、修订/产品、source_refs以及载荷冲突校验。实际索引字段product匹配为any；返回行若混有本题外产品会被二次边界拒绝，保持保守。

共用正式`QueryRunner.select_evidence`把原有top10种子交授权装载及已核验前提函数。新增关系沿source_prerequisite的cover_date/table_object trace保存，不冒称模型分数；新增证据进入EvidencePack/candidates后仍校验原文/metadata，实际选择只看最终prompt_used_docs。groups直接传现有prompt预算，前提/依赖整体保留或排除；引用取原文/refs/asset_ids，沿原资产修订校验、CitationGuard及图片context/answer关系协议。Run保存配置执行快照、SHA、分组、来源关系及排除原因。

## 实际检查与失败保留

| 检查组 | 结果 |
| --- | --- |
| 首轮红测 | 离线14失败，隔离Run 3失败/1通过，保留日志/XML；暴露缺失配置、身份、读取和接线 |
| 相关离线共享回归 | 131通过：新配置/读取、前提函数、扩展、预算、adapter配置、检索策略/来源与图片选择 |
| OpenAPI/缺省边界 | 2通过；现有OpenAPI逐项相等、HTTP字段未增、环境不能启用；不涉及前端源码/类型变更，未重复前端构建 |
| 保存25题正式消费者回放 | 禁联网夹具下25通过；全部context、groups、excluded、实际prompt、预算及引用投影一致；保存逐题新JSON，未改旧结果 |
| Mongo/Milvus及相关Run协议 | 66通过，覆盖新来源接线、旧扩展/真实隔离Milvus读取、Run/预算/引用/图片、幂等领取、adapter及continuation回归 |
| 新增接线补充集成 | 15通过，与66组重叠；覆盖跨组织/修订/产品/refs/asset、数据库/集合错配拒绝、旧扩展互斥、两级整组预算、adapter配置/检查点重放 |
| 历史文件/数据只读审计 | 1135检查通过；前轮162封存文件、502前轮保护文件、297语义保护和145早期文件有重叠，不累计唯一总数；582新索引/867冻结切片、67资产映射保持 |

首轮“green-unit-first”13通过/1失败为合成索引集合名不合法，修正夹具。较大集成首轮42通过/24失败：启动的m1_test_m6前缀不符合既有M4 adapter门禁导致23失败，另1新合成Chunk漏section_id。改用独立m1_test_m4_m6前缀并补夹具，未放宽业务门禁；原失败文件及数据库/集合现场保留。最终66组通过，无跳过；原依赖SWIG弃用警告2项非本轮新增行为，不据此重跑全量。第一次25回放未显式装载全局禁联网夹具，随后明确-p tests.conftest两次核验通过，最终25产物写新目录；不将早轮声称有socket guard。

所有集成Run、请求、合成输出、checkpoint和小向量写入新测试库/集合，未删除现场。合成供应商只返回合成验证短句，不能当作真实质量；合成Milvus写入使用2维固定测试向量，不计真实embedding或检索效果。保存25题真实weighted载荷的回放索引为有范围断言的snapshot端口，不冒称本轮又做了真实Milvus召回。

本轮真实模型/外部供应商/编码/真实重排/真实答案调用均未启动，无新调用未知崩溃窗口；前轮18次真实本地重排/74新对、426历史pair复用及未知HTTP/token/费用继续保留，不重新记0。合成遥测与真实调用分开。25题必要PDF到达仍21/25，019/021/022/048及历史图摘要命名污染未解决；037/038日期与05-a/b、17-b对象前提保持，17-a/18-b原限制保持。不是新答案评分或正式质量结果。

## 现场与本机交付

只读审计沿已核验隔离目标m1_test_m6_sq5_aad3135569bb44baaaf8f786cea680fd：四修订/582实时载荷和数据库完整摘要等于前轮，67资产映射不变，无真实答案Run/正式评测记录或默认指针写入。未重导入、编码、改变源处理、创建新修订或切catalog；前轮三处图标转写保留assistant身份。资产对象字节/全部模型文件本轮不重新下载hash；不重复扫描12246非目标知识集合/5554库。

冻结r3的867切片与历史导出相同，21非TTL集合保持，r3仍85结果/19继承+66执行/stream19+61及未知HTTP费用。旧失败仍failed/attempt2/provider_invalid_response/retryable=false/results0，不能推断调用0。run_events历史2315与当前1675差异继续单列，仅本次审计窗口前后保持，不声称跨历史22集合均不变；不恢复过期事件、不改历史state/lease/slot/retryable/题级来源。

新证据`output/m6-prerequisites-wiring-20261028/`：红测/中间失败/通过XML日志、25题正式入口回放JSON、只读审计、源配置/请求/源码身份与本机`25题正式消费者回放对照.html`。页面直接链接已保存真实链路和36原页，无需用户查PDF或重填。清单final-evidence-files.json与seal.json按收口时点一次性登记，不预填动态总数；Git只提交源码、合成回归、必要维护文档和脱敏报告/摘要，原始输出/evals/evidence/tmp保留。

## 回切和下一条动作

回切：独立新执行配置关闭来源前提并用新请求/配置身份，回到原weighted种子选择；缺省关闭不查前提。不能在已启用旧Run上改开关、SHA或历史检查点冒称完成；保留所有修订、索引、旧Run/结果/证据，工作台catalog不动。源码撤销使用正常反向提交。

**唯一下一动作：由原总控独立定向核验本次正式接线的内部身份、授权装载、groups/引用及关闭回切。** 来源前提算法本身和SQ已关闭项不重开；本次已交实际接线和无模型证据，不再退回空材料准备。正式接线未独立验收前不默认启用或发布；本次也没有新真实答案质量验证资格。正式人工双轮→预校准→同范围候选→反馈后复评依赖保留，不代填human或assistant observation，不把原件查证交回用户。

见[脱敏验证摘要](M6-08-prerequisites-wiring-validation-r1.json)。阶段保持M6 4/7，04/05/08未验收，M7未启动；提交和推送核对见最终交接。
