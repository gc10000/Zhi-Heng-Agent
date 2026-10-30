# M6 最终冻结与正式无生成预检 r1

2026-10-30，执行方，顺序执行。接续 `94408f653de6837cf20bcc1868de49186cf6d877`，开始HEAD／origin/main／GitHub main一致，仅未跟踪tmp/。既有技术审查关闭结论全部保留。本轮未修改业务源码。

**结果：题集、语料、基线／候选策略和恢复方案已形成固定产物；正式精确冻结尚未完成，无生成预检未整体通过。** 实际只读预检发现两控制库均尚无正式政策登记，也无两派生版本的evaluation_sets登记。当前四份配置明确标为pending-policy，以null政策hash由正式catalog拒绝；没有填假引用、删政策回落human或绕过门禁。不是新增技术缺陷，也不重开已关闭接线。

## 已完成的实际冻结工作

私有目录：`output/m6-final-freeze-preflight-20261030/`。完整矩阵为`freeze-matrix-final.json`，可执行前的登记及恢复顺序为`formal-registration-and-execution-plan-final.json`；草案catalog位于`catalog/catalog.json`，不设置为工作台默认。每条题目输入指纹见`question-input-identities.json`。

原题集、manifest、原绑定config和entry全部原字节复制；不覆盖原件，不派生第三个版本。两条001签审、绑定valid及proof absent经正式RegressionService只读重验；不重签、不重绑。每版150题，正式选择85 dev，65 heldout仅保留范围、未运行。

| 反馈 | 精确版本 | 001题级SHA | 基线／候选 |
| --- | --- | --- | --- |
| c34496c4-c065-5765-93a5-4ba9a9167e55 | fb-07c584730833908571fe9dd7c7c890afa3cf9e66 | 4b475a731a379c87d3f087a4f1d3d9cf0043801bfb2be87f85b1c072ef65774b | m6-final-1-baseline / m6-final-1-candidate |
| ff45ecf4-4b82-5f3b-a31d-808ec5ae485e | fb-a3fa87c1adb2a6dc4e9638214164eb5f343ad008 | 5d7785651c80268d538216393e6c7ea5d4f6da596688745b96940c8514aea07b | m6-final-2-baseline / m6-final-2-candidate |

两派生版本分别使用各自控制账本、来源binding/hash、annotation和题集manifest；不跨版本共享结果或校准。父配置留在新catalog供不可变绑定验证；最终实验可以使用不同config，但dataset/manifest必须与对应binding逐值匹配。四份草案的文件SHA及strategy SHA列于脱敏JSON，版本均为`v1-pending-policy`；这些SHA不能当作最终正式配置SHA。

基线／候选共同固定当前源码、prompt、模型与四文档隔离语料、来源前提、摘要隔离、scoped_subject_v1、scope_first_v1、weighted .5/.5及20/20/20/20/10。基线关闭内部组合；候选启用已审source_network_terms_v1→branch_heads_v1→compare_branch_context_v1；除本地experiment_id标签和组合载荷外，所有配置字段全等。生成预算32768窗口／4096输出／256预留／12000字符。策略差异已明确，答案效果未知。

## 实际只读预检结果

| 核验 | 结果及边界 |
| --- | --- |
| 当前源码／prompt／本地模型文件与配置 | passed；逐文件hash，不加载模型、不下载、不健康探针 |
| 正式RealQueryExecutor.check_corpus及corpus_snapshot | passed；实际四原件字节、582片完整载荷及向量、67资产字节与摘要身份、产品及活动修订匹配 |
| 组合授权、范围、术语、已审p30目标行 | passed；实际读取行重算载荷／术语，p30证明文件hash与目标载荷匹配 |
| 两反馈来源、annotation、题级指纹和已绑定版本 | passed；正式RegressionService.validate/status，valid、proof absent |
| 四配置的题集／策略结构、85题产品映射 | passed，**仅结构分项**；使用不保存的无政策投影隔离校验，不代表正式配置解析通过 |
| 正式EvaluationCatalog.resolve完整草案 | blocked；PolicyReference拒绝quality_policy.sha256=null，4份均不能执行 |
| 正式DevelopmentPolicy.require | blocked；两控制库政策记录均0。现有enabled admin均0；真实maintainer调用register在写入前403拒绝 |
| 正式EvaluationRepository.get_set | blocked；两派生版本均not_found，尚未有最终descriptor |
| 实验创建／排队／Run／实际评分／校准／proof | 未执行，本包禁止真实写入，不能声称预检已覆盖这些运行结果 |
| 当前保护 | 四数据库24个指定非TTL集合前后摘要一致；默认环境指针hash及其配置catalog字节hash一致；不外推为所有历史集合均未变 |

只读数据库包装明确拒绝非白名单方法。使用正式读取方法时跳过会create_index的构造函数；未调用正常资源初始化、导入、恢复或首次创建脚本。实际Milvus只读query_iterator，MinIO只读get_object。未重新扫描历史867条向量；旧现场全量保护依封存hash，run_events TTL继续单列。六Docker容器运行，Mongo ping通过。

## 旧85题有效性裁定

r3 `79b3cc58-cfd4-4da5-84c0-890d92a9be06` 的85条保留19继承＋66执行，历史stream19／新增61，HTTP及费用未知。其原题集、源码／prompt、目标／修订与最终两版不同，且没有正式助手政策身份，**可直接作为当前两版正式基线的结果数为0**。19个检查点不跨配置继承；完整答案仅为历史参考，不导入新实验、不改为新双轮。此裁定依据文件及合同差异，不等于本包授权或执行重跑85题。

旧失败 `a5607e05-de22-4b24-9570-e85b7e09b521` 保持failed／attempt2／provider_invalid_response／retryable=false／results0，调用与费用unknown；不能由0结果推断0调用。

## 正式登记与恢复的具体接续

当前只读范围不能生成政策的真实不可变引用：正式政策SHA含服务端created_at及实际registrar_id。已封存批准政策payload、文档hash及预期政策ID于`policy-registration-intent.json`，但没有伪造SHA。当前账号均maintainer，不静默提权、不让用户查账号；受控总控登记能力应由执行／总控一侧解决。

1. 在允许真实登记的受控步骤，由授权总控admin在两控制库调用`POST /api/v1/evaluation-quality-policies/{kb_id}`，保存真实返回引用；使用已批准政策，不重新讨论评分路线。
2. 新目录产出四份精确v1配置，仅填正式政策引用并保存新hash；原pending产物不覆盖。沿同一正式catalog／策略／来源／政策／实际语料预检复核。通过后通过`POST /api/v1/eval-sets`一次登记两最终descriptor及完整configs列表，不重签001或改变绑定。register_set的configs是不可变身份，不能先登记半份再覆盖。
3. 固定创建请求键为`m6-final:{datasetSHA前12}:{role}:{最终config文件SHA前12}:v1`。实验UUID由服务端返回，先保存回执，响应丢失用完全相同键重放。候选只有在本版基线完成、双轮及预校准有效后才能创建，不能提前伪填baseline／calibration ID。
4. 正式job注入quality_execution_key及regression_execution_key（本实验UUID）和对应binding；有效config参与题级key＝fingerprint([effective_config, question_id])。Run请求键就是该key，无额外前缀；题级输入包含id/question/product_names/history。服务端关联控制／目标库、Run、attempt及来源，按既有中断恢复协议复用，不手改state。retryable=false停止。
5. 25题保存响应／486分数仅供禁推理回放，不能作为新答案或新Run结果；本次runtime cache_enabled=false，不虚报后续缓存复用率。两版不同来源不能自动共享检查点。后续如需全部新答案，规划上限为两版基线170＋候选170，**本包未授权自动启动这340次，也未作付费调用**；调用前还须说明实际范围、路由逻辑调用、累计与本次新增、token／HTTP／费用及崩溃未知窗口，未知保持null。

前一私有脚本的初始方案中API路径与Run键描述已在final版本校正（eval-sets；无m4前缀）；初版保留，不作为当前规范。

## 实际命令、失败及保护

- `.venv/Scripts/python.exe output/m6-final-freeze-preflight-20261030/preflight.py`：exit0。完成实际读取，结果明确是政策open，**退出码0表示审计完成，不表示正式预检通过**。
- `.../finish_audit.py`：exit1。正式登记门禁及方案已保存，最后读取保护清单时误将无冒号的历史路径当作两段键，ValueError；原脚本和失败日志保留，无业务副作用。
- `.../final_audit.py`：exit0。新脚本按清单格式核验，父文件及全部保护hash通过；配置差异、实际摘要及门禁结论核对完成，不覆盖初版。
- 首次stdin环境读取未显式传.env路径，find_dotenv AssertionError发生在连接数据库前；改用显式路径读取，未输出值。其失败记录保留。

未改业务源码／API／前端，没有理由重复此前180／77等已关闭技术回归；本轮证据为实际预检读取、正式拒绝路径和产物审计。详细命令、退出码和日志hash见摘要，不累计历史测试为本轮进度。此前821／404／294／127及各轮私有清单均匹配，组间重叠不累计。

本轮新增实际embedding／重排／供应商／答案推理均0；真实数据库、正式评分、观察、校准、候选和proof写入0；HTTP／token／费用字段保持null。不清tmp，不上传output、PDF、缓存、完整答案或原日志。

## 分项验收矩阵

| 子项 | 已满足 | 未满足／责任与先决 |
| --- | --- | --- |
| M6-04 | 助手政策实现与设计已通过，已有原件分析保留 | 正式政策登记后，有效本版基线真实独立两轮、总控独立性核验与正式预校准；执行助手／受控总控承担 |
| M6-05 | 两001正式消费valid，出处／绑定不重做 | 本版校准后候选完整执行、独立双轮及服务端反馈proof；执行方依正式服务完成 |
| M6-08 | 技术组合关闭；实际语料／来源／题集结构预检分项通过 | 正式政策引用、精确四配置／descriptor、整体无生成预检及同范围质量链和阶段总控验收；不以缓存25/25代替答案正确率 |

**唯一下一动作：执行受控正式登记步骤，消费已批准政策返回的真实引用并完成两版最终配置／descriptor及同一预检闭合，之后直接按既定质量链推进。** 不安排新技术包，不等用户查PDF、账号或重评分。助手真实独立两轮不能由当前单轮换ID或复制生成，需保留实际独立来源。M6保持4/7，04／05／08未验收，M7未启动。
