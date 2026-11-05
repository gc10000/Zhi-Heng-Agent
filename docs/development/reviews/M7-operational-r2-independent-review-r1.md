# M7 r2运行接续：独立定向复核

本轮审查者为新建的 `/root/m7_r2_independent_review`，未参与源码实现，未调用供应商、embedding或reranker，未修改实际导入任务、旧批账本或控制账户，未委派其他Agent。审查证据位于本机 `output/m7-r2-independent-20261105-r1/`，不上传私有运行材料。

**结论：r2/v2供应商准入与宿主预算的限定技术检查通过；r2在准备阶段发生首失败并停止，真实演示未执行。另发现正式导入自动接管可超过本包一次attempt的约束，已完成限定源码补修及定向复核，尚未部署；不能把既有38/13项检查扩写成覆盖该边界。** 本报告不签M7阶段验收或产品质量通过。

## 通过与未完成

| 范围 | 独立结果 | 证据和限制 |
| --- | --- | --- |
| 正式Run准入、波次、预留、流与结算 | 38项通过，exit0 | `initial-independent-v2-r1.log/json`；随机短 `m1_test_m4_ir2_` 合成Mongo，正式RunRepository/RunCommands/QueryRunner及已安装SDK的MockTransport，无真实provider。包含正常、缺usage、finish后迟到正文、中断及模型前失败。 |
| r2增量身份及14/8/48预算 | 13项通过，exit0 | `v2-delta-r1.log/json`；源/恢复/control隔离、桶/集合互异、request固定、重算hash仍不能借r1授权；逻辑rerank与pair分别到限、已预留后不能换旧大额度。 |
| 导入上限补修的静态语义及离线外显边界 | passed limited | 独立审claim/requeue/retry/dispatcher的CAS、持久冻结及普通模式兼容；另有独立12项离线检查、exit0，耗尽时不展示可重试、不改原row/error，非规范上限在DB操作前拒绝。实际Mongo12项为执行方自验，分列。 |
| 完成/失败Run再次execute仅观察 | 未完成 | `terminal-observe-v2-r1.log/json`为1 failed/3 setup errors、exit1；Mongo操作取消/超时发生在准备或setup，未到provider或第二次execute，既不是该断言的反例，也不能计通过。 |
| 修正来源与一次正式导入准备准入 | passed limited | 原件字节SHA `249c38af8708bb62cd15f058b70ddd31fc72ddfd0674c9eb70252c1e9a766b6e`；离线解析6chunk/0image，八题必要事实逐项可见。`admission-approved.json`只准导入准备，不准provider。 |
| 构建镜像与受审来源 | passed at import gate | 镜像 `sha256:4e8fb4cac8f1903002bb2c74f1e5e05be82fffc34fb87de4b4dbb20fac2ea1f8` 中210个app/prompts文件独立重算，来源身份 `29c8f4f6ebe4cd58c412db6f49a23714e8b9027aa409fefe1bc09d0c9c042280`。不是后续补修镜像。 |
| provider临发manifest、真实答案、恢复08及真实容量 | not executed | 无manifest-approved，执行manifest/budget不存在，streams目录空；源Run0，control账户未建立。不能拿合成SDK结果或相关摘录代替产品回答。 |
| 最终安全停止 | passed at observation | 独立只读见宿主PID不存在、worker/dispatcher exited、generation=false；STOP保留。瞬时停态不证明daemon持续稳定或Linux目标部署。 |

38和13项以应用来源身份 `29c8…280` 为锚，二者分列；不与历史r1或实现自验累计成质量分。无原始usage的本轮计量保持null，HTTP/费用unknown，不能登记为0。网关硬限和实际付费上界没有被验证。

## 首失败与导入边界矩阵

| 根因 | 保存反例 | 退出条件与当前状态 |
| --- | --- | --- |
| Mongo读取消使准备观察提前失败 | 私有 `prepare-demo-r1.log` 在读取import job时 `_OperationCancelled`；STOP为prepare/no_automatic_retry。 | r2永久停止新准备和provider派发；即使Mongo随后可读，也不恢复或重领旧额度。该故障不等于产品答案失败。 |
| 普通持久导入的自动租约恢复未冻结本包attempt上限 | 初次观察job为running/attempt1/embedding_pending；最终只读为failed/attempt2/embedding_pending/upstream_connection_failed/retryable=true。旧claim允许expired running，dispatcher的requeue_expired允许再pending；私有驱动终态assert attempt==1过晚。 | 源码补修受审范围通过：正式register冻结1至10次上限，claim/requeue/retry/dispatcher拒绝越限，不抢有效租约、保留普通恢复。旧r2 job不回填、不修改；本批违规事实不因补修消失，补修未部署。 |

本轮正式上传确已创建1份文档、原件、修订及导入job，不能声称“真实库写入0”或“导入未开始”。独立最终快照 `final-readonly-r2.json` 确认attempt2，原job状态不改。SQLite只有一条embedding预留，累计6文本/0rerank/0pair；这是预留证据，实际完成embedding文本数unknown，不能宣称完整完成6文本推理。无完成的embedding检查点，停止宿主后出现连接失败也不能倒推出原调用从未执行。

本轮provider逻辑stream为0，依据是正式准备尚未到manifest/合同冻结、无Run/控制账户/流文件、generation=false及宿主停止的组合证据，不仅是结果行0。控制账户不存在不能写成“已持久halt”；实际限制为文件STOP、未具备provider准入材料和停止消费者。旧r1账户独立只读确认halt/0消费，未借额度。

Docker首次compose stop和inspect返回500，失败收据保留；后续按本轮精确容器名stop成功，独立只读确认worker/dispatcher exited。`final-readonly-r2.json`首脚本使用错误环境变量名而将generation记录为null，补充 `final-generation-key-correction.json`核正确键 `M7_GENERATION_ENABLED=false`，原错误证据保留，未改变运行状态。

## 最终补修及交付边界

最终应用来源身份为 `912c8a9960ca2271c271e472681860364af6afa5230782d92e7d4f1adc7be6b9`，覆盖210个app/prompts文件。独立只在内存将两个导入补修文件替换为本包HEAD的旧版本，重算恰好得到准入锚 `29c8f4f6ebe4cd58c412db6f49a23714e8b9027aa409fefe1bc09d0c9c042280`，证明原38/13受审的provider范围未变化；未checkout或覆盖工作树。完整文件字节SHA封存在 `final-source-reconciliation-r1.json`。

新增导入补修的独立12项离线检查为 `import-view-offline-r1.log/json`，0.48秒、exit0。另已阅读执行方 `import-limit-red-r2.log`（7 failed/1 passed，exit1）及 `import-limit-green-r2.log`（12 passed，1.46秒，执行方报告exit0），后者使用新随机合成Mongo，包含10项新上限边界及2项旧租约兼容；保留为实现自验，不能冒充独立Mongo执行。首次红测含5个Mongo setup errors；首次绿测为7 passed/5 setup errors，均保留而不计全绿。独立未重复写库失败组。

补修在登记时以setOnInsert冻结max_attempts，随后环境删除或扩大都不改变既有上限；原子claim同时检查额度及pending/过期状态，requeue只封存耗尽的pending/过期running，dispatcher过滤耗尽任务，显式retry也带额度CAS。有效租约不被封存，未配置上限保持普通恢复语义。外显job_view在耗尽时返回retryable=false并保留原始错误。此结论是限定代码边界通过，不能证明本批曾符合一次attempt约束。原导入attempt2、STOP、预留和所有失败日志保留，不再导入或调用；运行镜像仍为补修前版本，不作为最终修复镜像。

最终收据补记：执行方合并定向命令 `final-targeted-r1.log` 实际为37 passed／4 skipped／6 Mongo setup errors，111.44秒、exit1，**最终合并检查未全绿**，未重跑失败组。4项skip是 `test_m7_demo_budget.py` 中历史v1参数下不适用的r2专属分支，由直接return改为显式pytest.skip；先前包含这些空分支的通过数不能视为新增边界已验证。本报告原9个文件hash未包含该测试，现补登记其最终字节SHA，仅标注此测试差异，不改变上述独立38／13／12项结论或应用来源身份。

补修镜像构建 `build-attempt-limit-r1.json/log` 实际exit1，Docker API `_ping`返回500；没有生成可用的新补修镜像，也未部署。该运行前置缺口与最终合并Mongo错误继续open，不能以限定源码通过替代运行验证。收据及测试最终hash已加入本报告JSON。

本次不新增正式评分、校准、候选、gate或feedback proof。M6保持5/7，04保持验收；05缺真实反馈复评proof，08缺有效新候选质量及阶段证据。旧168stream/170结果/340判断、blocked gate/0proof/halt及43题暂停均保持。M7工程依赖例外不等于允许公开上线，Linux目标实测、完整真实QA浏览器闭环和公开分发义务仍分别保留缺口。

下一项执行方动作是封存本批STOP及最终技术补修证据，准备目标运行环境中的新身份方案；不得直接重启r2准备或复用未消费槽位。来源事实已经修正，本次环境失败不足以说明回答效果改善或退化。
