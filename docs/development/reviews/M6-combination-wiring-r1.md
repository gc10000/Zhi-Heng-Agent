# M6内部组合正式接线与零新增推理验证 r1

本包完成默认关闭的 `source_branch_compare_v1` 正式内部接线，**执行自验通过、待总控独立定向核验**。沿正式消费者复用25题后端响应及486个保存分数，35/35必要单元到达最终context与prompt，原24题的完整variant逐项相等。没有新答案质量结论，不自行关闭M6子项。

接续 `b2acaf501ed49d571e9ad72c56287c66b6735e8f`，开始HEAD、origin/main、GitHub main一致，仅未跟踪tmp/。顺序执行，无子代理。原P2、p30消费、001标签及SQ/AF/continuation等既有关闭结论保留。必要报告、测试和源码正常提交推送；本机output/evals/evidence未提交。提交SHA在最终交接补记。

## 正式接线路径和身份

`EvaluationStrategy → RealQueryExecutor → InternalRunInput → RunRepository → QueryRunner` 明确传递同一规范组合。配置版本固定为source_network_terms_v1、branch_heads_v1、compare_branch_context_v1；不新增选择规则、不更改分数、不扩词或按题号分支。配置要求来源前提同scope，固定weighted .5/.5、20/20/20/20/10、摘要隔离与scoped_subject_v1、scope_first_v1，关闭其他增强/扩展。

| 消费位置 | 实际绑定与拒绝行为 |
|---|---|
| 实验配置 | target的database/collection、owner/kb、document→revision与corpus.snapshot hash一致；正式adapter仍复核原件、向量、资产完整快照 |
| 授权装载 | 先核冻结revision snapshot及全部文档/产品授权、数据库/集合，再有界读取≤1000行；整批正文/结构/出处hash、owner/kb/product/source_refs重验；术语从授权正文重提并与冻结目录相等 |
| 已审出处 | p30已封存消费证明SHA绑定document/revision/chunk及目标载荷SHA；不新签审、不改变旧unknown或未审行。受信配置授予来源，不将任意客户端hash解释为审阅 |
| 请求/Run | public RunInput不增加字段；内部规范完整payload和hash进入请求幂等身份及持久Run。缺省关闭保持旧指纹，同key换配置409；旧Run不能事后启用 |
| 实验/题级 | config hash、evaluation_items及evaluation_execution_links保存同组合payload/hash，并绑定完整run_input hash；保留原题/历史/行为/反馈来源，不回填旧关联 |
| 恢复 | 创建前/创建后/关联后重建复用固定请求；running中断经正式recover。显式continuation先核父Run组合，成功检查点快速恢复也重新核Run、输入、结果及原关联；漂移拒绝 |
| 正式检索/选择 | V2Index用同次真实dense/sparse/weighted响应进行branch_heads；retrieve逐scope投影来源术语；rank_hits消费原输入；QueryRunner共用context_seeds、select_evidence与evidence_prompt，组预算和图片授权仍走原链 |

本次缓存目标数据库/集合均为 `m1_test_m4_m6_heads_fb825179effd4f0f`，保持原隔离修订，未导入或切默认。四份文档的精确document/revision见脱敏摘要。代码身份 `ebf6b6891139b2caa8ed7abb06abc3fbd56a35a7cbea76896d4422545252cb4f`；prompt `f0fe0cc92fca8715957120515588f239ee15d1e4b3e0ba6c4c411dd176d5c52d`；模型配置 `565fbfe4c795fb52f84183f7b2708491fd7824fa07f2de9fd546e9d6d6e5bb90`。保存的处理版本另列，源码变化不冒充旧处理身份或继承旧19题。

本包配置hash `9fdfab9e1854327ad89fe337d8761e8acb270c9a9bdae8e752031e3b8938a40d`，组合hash `fe33a7f8200e68f78cd4f8eef84c9394a53f83c795cd6e40ec98867b136f5b0d`。它是接线缓存验证身份，**不是最终生成配置冻结**。语料snapshot、载荷、术语及p30消费证明hash均在本机执行前配置和摘要中绑定。

## 实际验证

| 组 | 结果 | 边界 |
|---|---|---|
| 12份相关离线/契约 | 180 passed，exit0 | 包含22项新组合单元；版本、范围、语料、来源漂移、默认端口及hash/有界读取 |
| 6份随机隔离Mongo集成 | 77 passed，exit0 | 包含26项新组合集成；正式job/adapter、同分库、创建/关联/完成快照窗口、显式continuation、官方recover、缺缓存、比较双方低分首证；合成模型 |
| 禁联网25题正式消费者缓存回放 | 25题、35单元、486分数，exit0 | V2Index实际方法消费保存响应，校验向量缓存SHA及请求参数；不连接真实Milvus/DB，不重新编码、重排或生成 |
| 保存证据/源码/保护hash审计 | 3092断言，exit0 | 821/404/127/294及历轮清单均匹配；组间重叠，不累计唯一文件或质量分 |
| OpenAPI全等 | exit0 | public schema不变；无前端改动 |

确切命令、日志路径、退出码和哈希见[脱敏验证摘要](M6-combination-wiring-validation-r1.json)。读取了实际源码与原审批范围，并按先红后绿补齐身份、恢复和读取边界。新增源码已自查暂存差异；本包独立核验由总控承担，不自称独立通过。

红测和中间失败全部留在新output：配置12失败、正式接线1失败、Run8失败、adapter3失败、hash/上限2失败、continuation2失败、成功检查点1失败；对应修后组通过。期间提取公共函数误移除expansion_policy局部导致55项集成失败，已恢复且77项整组重跑通过。另有初次测试文件名错误、回放夹具的修订列表顺序与封存过滤字符串不同、审计夹具编码名/异构清单错误；均保留原日志，未改策略凑结果。早期PowerShell尾部Get-Content可能返回0，子pytest失败以原日志/结果为准；最终组另存显式退出码。

## 25题同口径结果

以下是必要正文到达情况，不是答案正确率或正式评分。原24的种子、context、prompt、groups、excluded、budget和排除项逐值相等。048保留已审换入原14/18、换出9/10；目标仍18/20，分数不改。双方首证、p30、context10及五层预算保持；旧23次补充unknown不变，新增unknown为0，必要依据均有可靠出处。

| 原题 | 必要单元最终到达 | 与已审结果 | 种子数 |
|---|---|---|---|
| m6-g540-02-a | 1/1 | 不变 | 10 |
| m6-g540-02-b | 1/1 | 不变 | 10 |
| m6-g540-04-a | 1/1 | 不变 | 10 |
| m6-g540-04-b | 1/1 | 不变 | 10 |
| m6-g540-05-a | 1/1 | 不变 | 10 |
| m6-g540-05-b | 1/1 | 不变 | 10 |
| m6-g540-17-a | 1/1 | 不变 | 10 |
| m6-g540-17-b | 1/1 | 不变 | 10 |
| m6-g540-18-b | 1/1 | 不变 | 10 |
| m6-g540-20-a | 2/2 | 不变 | 10 |
| support-v1-003 | 1/1 | 不变 | 10 |
| support-v1-004 | 1/1 | 不变 | 10 |
| support-v1-006 | 1/1 | 不变 | 10 |
| support-v1-007 | 1/1 | 不变 | 10 |
| support-v1-008 | 1/1 | 不变 | 10 |
| support-v1-009 | 2/2 | 不变 | 10 |
| support-v1-010 | 2/2 | 不变 | 10 |
| support-v1-019 | 1/1 | 不变 | 10 |
| support-v1-020 | 2/2 | 不变 | 10 |
| support-v1-021 | 2/2 | 不变 | 10 |
| support-v1-022 | 1/1 | 不变 | 10 |
| support-v1-034 | 2/2 | 不变 | 10 |
| support-v1-037 | 2/2 | 不变 | 10 |
| support-v1-038 | 2/2 | 不变 | 10 |
| support-v1-048 | 3/3 | 保持已审置换 | 10 |

原始逐题响应、分路请求、分数来源、最终prompt、出处、预算和关联见本机 `output/m6-combination-wiring-20261030/formal-replay-final/results/`；可直接阅读 `output/m6-combination-wiring-20261030/25题内部组合正式消费者对照.html`，无需重新查PDF。本包回放使用封存QueryPlan及原调用者主体/历史；共用正式消费者方法，不创建25个持久Run。正式QueryRunner.execute和RealQueryExecutor/job整链由独立合成Mongo夹具验证，两个层次分别记录，不以缓存伪称实时新检索/真实答案。

## 调用、数据保护与回切

缓存回放设网络/子进程拒绝、模型和Mongo入口拒绝，触发记录为空；缺缓存直接停止。新增实际embedding、rerank、供应商、答案推理均0；合成模型只测试协议。HTTP、token、费用保持null，不用缓存命中推断历史调用为0。真实数据库、正式评分/观察/政策/候选/校准/proof、001、默认指针均未写入；Mongo写入仅随机m1_test_m4_合成库。未重新扫描真实582/867或默认指针，依赖hash匹配的封存审计，不扩大为当前实时现场证明。

r3仍为85条结果、19继承+66执行、历史stream19/新增61，精确HTTP和费用未知。原失败实验仍failed/attempt2/provider_invalid_response/retryable=false/results0，调用与费用未知。tmp/output/evals及原件证据保留。未手改历史state/lease/slot；新合成故障通过正式commands/claim及测试时钟推进，旧共享故障夹具的合成库改动不外推真实。

关闭回切使用新配置/请求移除组合，恢复原weighted和原来源前提策略；要回全部旧默认，再关闭来源前提。缺省Run指纹与旧路径全等；不删除旧索引/修订/结果、不复用启用Run。源码回切正常反向提交，默认catalog未动。

## 收口与唯一下一动作

本包接线、缓存覆盖和隔离恢复自验已满足；**下一步由总控独立定向核验本包配置/授权/身份/恢复矩阵和25题证据**。通过后执行方再冻结最终题集、两个反馈派生版本各自的精确修订/配置/政策，正式无生成预检，然后基线助手独立双轮→预校准→同范围独立候选双轮→服务端反馈proof。不得跨版本复用或把旧19检查点当新结果。

M6-04仍缺正式有效双轮及预校准/同范围质量证据；M6-05仍缺有序真实反馈复评proof（001签审/绑定已关闭）；M6-08仍缺最终冻结/预检与独立候选质量链，四题对象/配件新答案效果仍待验证。human发布门槛单独保留，不要求用户重找原件或填分。**M6保持4/7，04/05/08未验收，M7未启动。**
