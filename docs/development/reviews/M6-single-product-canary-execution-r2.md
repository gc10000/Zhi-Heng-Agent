# M6唯一05-a接续：执行驱动前置失败，未调用产品

日期：2026-10-31，Asia/Shanghai。执行方接续`1cceb9e`，启动实际HEAD／缓存origin为运维提交`031ba1d`；会话中总控另提交`d41b3a4`，已读取其差异并保留。用户明确确认“维护已结束，继续原授权范围”。没有启动Docker或服务，没有委派子Agent。

## 实际退出

**版1新版`m6-g540-05-a`没有实际执行，没有产品答案。** 本包新私有驱动沿正式catalog／EvaluationService准备创建单题job，在创建实验之前误将完整题集`question_count`断言为85而停止。85是dev题数；完整dataset实际150行，dev85。只读复核实际descriptor、完整dataset及manifest hash均与冻结身份一致，失败来自本轮驱动新增的错误常量，不是正式题集登记错误、维护阻断或产品准入源码失败。

原驱动、执行日志、失败收据及现场全部保留。离线提取原断言得到红测exit1；修正版改为依据完整冻结dataset验证总行数及dev行数，3个计数边界绿测exit0。修正版另存`execute_canary_r2.py`，**本轮未再次执行**，遵守明确前置失败即停止。修正版离线通过不代表它已经贯通实际正式job，更不代表有答案改善。

失败发生在`create_experiment`之前；本轮没有创建真实实验或Run，没有账户预留和固定started。末次只读复核固定请求／配置、账户key／合同、checkpoint及执行关联均无本包记录；不是仅凭结果行缺失推断没有调用。固定slot仍为`m6-05a-product-canary-r1`，首份planned及追加code-plan保持，started／settled均不存在。必要题集描述符只读精确复用，尚未走到保存本题登记收据；无新登记服务、无手工插库或提权。

## 实际验证与最新关闭结论

| 范围 | 本轮结果与限制 |
| --- | --- |
| 最终源码定向隔离集成 | 用户指定5个文件全量75 passed，exit0，无`-k`；随机短前缀`m1_test_m4_sc_79742d`保留，不删除旧库。 |
| 当前源码／配置／输入 | 业务源码仍为`b50b1f5b0eab66d7a4eb2a32314bcd415dba2624354cfb0ece59d2efce17ab8b`；prepared-r2、Git封存授权、prompt及runtime身份一致，无app源码变更。 |
| 单题实时消费者预检 | exit0，编码缓存命中1、pair分数20、检索响应3，miss0、新本地推理0；候选、排序、context、reference_map、groups、prompt全等，input12293／limit28416。保留机身RJ45独立及HUAWEI MateDock 3配件LAN关系，LAN旧行unknown不升格。 |
| 安装SDK与保存输入 | 实时预检附带MockTransport wire通过，固定n1／max_completion_tokens4096／默认thinking／retry0／timeout120／无redirect。只是序列化核验，不证明真实网关硬限或产品输出。 |
| 私有驱动检查 | AST／单题catalog／正式专用客户端观察口离线核验通过；完整题集计数红绿另存，修正版未真实执行。 |
| 历史保护 | 138／336／597／1314各组文件hash匹配，组间重叠不累计；未重扫全库向量、默认指针或run_events／TTL，不读private-identity。 |

原报告中的169项离线／契约属于此前最终源码结果，8项集成属于中途源码，均不冒充本轮重跑。会话中收到并读取总控`M6-single-product-canary-review-r1.md`及摘要：**总控已经独立关闭单题风险准入、最终源码集成和单题精确预检技术项**。本轮私有驱动计数错误不重开这些关闭项。其他n1、raw usage、对象关系、SQ／AF／continuation、P2／p30／001及组合／比较关闭均保持。

## 身份与分账

授权仍只读取`bcee5395604bcd7169c907ddcf146f163ccc2d14`封存Git来源；不是工作树JSON充当授权。prepared-r2 config canonical为`22d0e525ba1074336a6d7af973cc50427eb96e4c3f5ad28d9a3c60e37ff65efc`，manifest为`0e94544429f865b2f2e35193f9f915e06282de9c1faf85fafe27d4891bb85533`。

请求键`0b0d21e83dbdc7ef28605dec2f35c3790a3d043252b9b5cd23c1cc0ddb70b790`，请求canonical hash为`f3f16112c23330b0a5c142c3a64559d6cbd79f5e82ac00cd617529b5fc9526d9`，两者分别保存。checkpoint为`9dc35acea3b1133b409e403caa2eea8bfea70cf4e91d8e0ba3c01da47f243301`。旧05-a仅作父来源，未续跑或从原48未执行清单划掉。

| 计量 | 本轮新增 | 本诊断累计／边界 |
| --- | --- | --- |
| 真实逻辑产品stream | 0 | 原六流保持，新单题尚无答案。 |
| 本地编码／重排推理 | 0／0 | 精确缓存复用，无fallback。 |
| input／含reasoning output | 0／0 | 仍23582／20602；预算1477632／212992不变。 |
| 精确HTTP／费用 | null／null | 驱动request／response hook均0，不据此填精确计费HTTP为0。 |
| 单次实际付费输出上界 | unknown | 请求4096不充当硬保证，能力status／semantics仍unknown。 |

原六流23480／16506和旧非产品探测102／4096原样保留；reasoning包含于output，不重复相加。本轮未追加探测、未跑版2或其他题、未重抽05-a、未恢复原48 job、未写评分／候选／attest／校准／gate／feedback proof、未跑heldout或切默认。

## 交接

证据仅在本机`output/m6-single-product-canary-20261031/continuation-r2/`，包括完整命令及退出码、实时预检、启动与末次核账、原驱动副本、计数红绿、失败及修正版文件hash。原本机冻结、旧失败、output／evals／PDF／缓存／tmp均保留，不提交私有配置／日志／答案。

唯一下一条执行方动作：在后续接续中，只读核同一请求／账户／固定槽仍无消费、当前源码和精确输入未漂移，再沿已封存原授权使用修正版驱动创建并执行唯一正式单题job；不需要用户重找资料、重评分或重新授权同一次调用。不重复整轮准备，不能因该修正版离线通过自动扩大调用范围。网络同步结果按提交后回执单列，不把缓存origin冒充GitHub实际状态。

没有真实产品结果，**不具备扩大范围依据**。M6保持5/7，04保持验收，05缺有效反馈proof，08缺有效新候选质量及阶段验收，M7未启动。本报告是执行方自验及前置失败记录，不冒充总控独立结论或阶段验收。
