# M6 受控政策登记、最终冻结与正式无生成预检闭合 r1

2026-10-30，总控。审查起点5024984，启动实际核对HEAD／origin/main／GitHub main一致；起始仅tmp/。本轮不修改业务源码，不重做既有技术回归或标签语义审阅。

**passed：两库政策登记、两份完整题集descriptor、四份精确v1配置及整体正式无生成预检已经闭合。** 本轮承担受控登记操作，登记后另起只读进程从正式服务和实际存储重验；不把这一进程称作第二位独立评分者。既有P2／p30／001／组合接线及其他技术关闭结论保留。

## 真实卡点与本轮消项

此前重复技术补修改善了出处、检索和上下文，但4/7统计的是整项阶段验收，不能累计测试数。5024984已无新的检索或接线缺陷；最后两项登记缺失使正式catalog拒绝空政策hash、get_set返回not_found。本轮直接处理这两项，而非再生成准备包。

| 子项 | 本轮实际结果 | 状态 |
| --- | --- | --- |
| assistant-development-v1 | 两控制库分别由DevelopmentPolicy.register生成真实引用；立即require并同主体重复请求幂等 | closed |
| 原owner下两派生题集登记 | 各150题，85 dev／65 heldout；完整configs含本版基线、候选和原绑定配置，一次正式登记、重复请求全等 | closed |
| 精确四配置 | 仅补入本库真实政策引用，v1取代入口pending版本；原pending及父／派生文件原字节保留 | closed |
| 正式无生成预检 | 不删quality_policy；正式catalog.resolve、策略、政策、来源／绑定、85题范围、真实语料检查通过 | closed |
| M6-04 | 尚无当前两版有效基线的真实独立双轮、总控独立性核验和预校准 | open |
| M6-05 | 001签审消费valid保持，真实候选复评proof仍absent | open |
| M6-08 | 最终冻结／预检已关，仍缺同范围独立候选答案质量证据及阶段验收 | open |

M6仍4/7，04／05／08不勾选。下一步是质量链执行，不是另一包检索开发，也不要求用户找PDF、账号或手工重评分。

## 正式登记范围与身份

依据既有C04技术独立通过及正式登记授权（M6-convergence-execution-review-r1），结合当前接续的受控登记范围执行。两控制库各通过IdentityService.add_user新增实际总控登记主体，role=admin、kb_ids仅原kb；从持久公共身份构造Principal。没有修改原maintainer／标签审核主体、伪造admin Principal或直接写政策。随机密码只在内存，未保存或输出，没有创建登录会话；不读取private-identity。

正式政策ID：`a511cc6341b832d7af86cf900b29ffac33319ed9f8c85faeb31c42cf8d91b107`。

| 控制库尾段 | 本库政策引用SHA256 |
| --- | --- |
| 562c2209ba994a1892074da324cc3025 | `8a4fa95f898ddc362e55c505674e71c22508c5fe1cc77bd6d6668da78e7e703f` |
| c1486a0a19d84c069d66d6abeff4709a | `62eb176019f78fe4e5d442d8f8a8a150db3b4b83eaa49d1fbf64acee135cd2b3` |

服务端created_at及实际registrar_id参与hash，两库引用不可互换；只读篡改／跨库引用均拒绝。完整公共身份与回执留新私有目录。批准政策文档与payload hash未变，human发布规则保留。

实际业务记录新增为2主体＋2政策＋2题集，另有正式构造器所需索引初始化；不能写成“真实数据库写入0”。新实验／Run／评分／校准／proof均0。原owner登记完整descriptor，非登记主体另建题集范围。

## 最终身份与配置

私有正式入口：`output/m6-policy-freeze-closure-20261030/catalog/catalog.json`。未设为默认工作台入口；执行需显式选此冻结catalog及对应控制库。旧catalog、pending和历史题集不覆盖。

| 派生版序号 | 角色 | 配置／版本 | 文件SHA256 |
| --- | --- | --- | --- |
| 1 | baseline | m6-final-1-baseline / v1 | `d50d1909342a3eb02fbce42682b5fc286e36f0ddae21822a9f8d43f43018658e` |
| 1 | candidate | m6-final-1-candidate / v1 | `740d112820004532ebe898f4110cd600e0e73c649adbc4d1060f52153f61ca20` |
| 2 | baseline | m6-final-2-baseline / v1 | `02adc87c4da3cbcac3ed890805282a8fc0250e3e94e3022560d27cf1af0ecaa6` |
| 2 | candidate | m6-final-2-candidate / v1 | `2256e6263f47b46fc1723f7ec1b5a286ae75b65742c4ba77cc9afefa2789f88c` |

版本1为fb-07c584730833908571fe9dd7c7c890afa3cf9e66；版本2为fb-a3fa87c1adb2a6dc4e9638214164eb5f343ad008。各自题集／manifest／binding／政策身份保留，不跨版本或控制库复用。

基线组合关闭，候选启用已审source_branch_compare_v1；除experiment_id标签和组合外其余配置全等。weighted .5/.5、20／20／20／20／10及32768窗口／4096输出／256预留／12000字符不变。runtime cache_enabled=false；25题486分数回放不成为本版新答案。旧r3仍19继承＋66执行，可直接复用为本版正式基线0，不能继承19项检查点；旧失败及未知调用费用原样保留。

## 实际验证与限制

1. register_and_freeze.py：exit0。先核上轮47个私有文件hash，保存写入计划、默认／数据库before；两库正式登记与同请求幂等；四配置完整解析；实际语料预检后一次登记题集，get_set重验。
2. readonly_review.py：exit0，3190项检查。独立进程只读重验两政策／实际公共主体／完整descriptor、四配置、来源与两001 valid／proof absent、父原字节、跨库和篡改拒绝、历史保护及登记差异；不累计为答案质量。
3. 两次实际正式check_corpus及组合授权重验：4原件、582条切片完整载荷和向量、67资产及产品／修订snapshot一致；p30证明与来源行匹配。未搜索、编码、重排或生成。
4. 四数据库全部当时非TTL集合按记录摘要检查，旧记录无变化；仅许可的六条新增。users摘要排除password_hash，不读取或输出旧凭据。run_events、login_sessions、login_attempts列为TTL排除。登记后只读审计前后摘要全等。
5. 历史867向量未重扫，依封存且hash匹配的历史证据；默认指针hash和默认catalog文件字节不变。没有创建实验或Run，本轮不声称实际生成及恢复已运行，继续引用先前已独立关闭的技术接线审查。

没有重跑180／77整轮检查。本轮两个执行进程首次均exit0，无新失败；历史失败脚本和日志经保护核验保留。新只读审计仅验证实际登记与预检，不是答案语义独立双轮。

## 唯一下一包：按版本生成有效基线并真实双轮

执行方使用新目录formal-experiment-requests.json中的固定请求模板；实际实验UUID／Run／calibration ID尚为null，由正式服务创建后保存，不预造。候选请求必须等本版有效基线及预校准，填真实baseline_experiment_id、quality_calibration_id及regression_calibration_id才提交，不提前排队。

创建幂等键固定为`m6-final:{datasetSHA前12}:{role}:{最终configSHA前12}:v1`。响应不明时先读或以完全同键重放，保存实际回执；正式job注入quality_execution_key／regression_execution_key=服务端实验UUID及对应binding，题级checkpoint及Run键为fingerprint([effective_config,question_id])，无额外前缀。按正式continuation／retry恢复，retryable=false即停，不手改state／lease／slot。

下一次真实调用前先列清实际对象／85 dev范围、请求／实验／Run／题级身份、精确题集与来源、幂等检查点、恢复、调用账本及累计／新增分账。每版基线85，规划基线上限170答案；候选须预校准后才运行，另最多170。本轮未启动任何这些调用。可观测usage据实记，HTTP／token／费用未知记null，崩溃窗口不写0。

按“有效本版基线→真实独立助手双轮及封存／总控核验→正式预校准→同范围独立候选及真实双轮→真实反馈服务端proof”执行。两轮必须独立来源和实际执行，当前聊天不能复制两份或换ID充当双轮；unknown／关键错误按批准政策pending／blocked，如实停止，不改标准。heldout65仅保留范围，未授权运行；M7未启动。执行前无需用户重复政策决策或查找原件账号。

本轮新增实际编码／重排／供应商／答案推理0，精确HTTP／token／费用null。完整证据、日志及catalog只保存在新output目录，提交仅脱敏文档，tmp/保留。
