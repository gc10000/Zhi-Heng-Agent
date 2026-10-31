# M6单题风险准入总控定向复审 r1

日期：2026-10-31，Asia/Shanghai。身份：总控独立技术复审；不是执行自验转述、答案评分或阶段验收。

## 裁定

独立核验执行提交`1cceb9ee09807725c8a800fb0f18e72c3c7480b4`，启动HEAD与origin/main均为运维提交`031ba1de27a32666120512c6285cdcf5a893b743`，工作区仅tmp。Docker维护已结束，5个基础服务均healthy。本次独立关闭**单题风险准入技术实现、最终源码集成、05-a精确缓存消费者预检**，不再停留在“等待维护／待最终集成”状态。既有n1、raw usage、对象关系、P2、p30及001关闭结论保持。

唯一产品槽仍未消费，本总控未代执行产品调用。执行方可按既有封存授权与原handoff直接进入唯一新版05-a正式单题job的必要登记及执行；不重复请求模型授权，不重跑整轮准备。任何身份／输入漂移、登记失败或未结算窗口仍应停止，不能把本次预检当成永久有效。

## 独立证据矩阵

| 边界 | 实际核验 | 裁定 |
| --- | --- | --- |
| 准入与能力事实分开 | 固定Git授权、版本1单题、完整题集、输入、scope、源码、预算、账户及manifest逐项核验；普通v2 unknown仍拒绝 | passed，技术关闭 |
| 最终正式job及恢复 | 同库／分库，正常、坏usage、断流、快照前中断、槽前／后退出、只读重放与共享恢复回归 | 最终源码75项隔离集成通过，关闭维护所留缺项 |
| 份数／wire／原始usage | 169项相关离线／契约通过；1条既有非法float合成夹具Pydantic告警保留 | passed，旧关闭保持 |
| 独立直接边界 | 新增12项合成检查：history／product_names漂移，各context／引用映射／groups／输入预算漂移，SDK retries／n／timeout／redirect变化，普通v2不可借道 | 12通过；随机本地合成来源，无真实槽消费 |
| 精确消费者 | 真实只读Mongo与必要Milvus读取，正式策略／选证／prompt消费者；1编码缓存、20个pair分数、3个检索响应命中，miss为0，推理入口禁止 | passed，关闭该题实时预检缺项 |
| 输入与发参 | input12293，prompt、context、groups、reference_map及已审关系全等；安装SDK＋MockTransport核n1、max_completion_tokens4096、固定profile | passed，不充当供应商能力证明 |
| 历史保护与来源 | 2447项文件／来源／身份／收据审计；138／336／597／1314份历史保护清单hash匹配；检索／切片／AF／prompt相关保护与OpenAPI全等 | passed，各组重叠，不累计唯一总数 |
| 05-a新答案效果 | 尚无新产品输出 | open，需唯一正式stream实际结果 |
| 网关全域硬限 | 仅有旧固定profile一次观测 | unknown保持；仅该一次风险准入有效 |

私有证据位于`output/m6-single-product-canary-review-20261031/`，含unit／integration／independent的日志与JUnit XML、readonly-preflight、consumer-preflight、sdk-mock-wire、audit及脚本改编收据。先审阅旧脚本，再复制到新目录；预检副本将prepare_manifest改为只核已有require，不写真实槽计划，所有新输出位于新目录。原脚本、旧维护失败、中间红测及证据未覆盖。

## 精确身份

- 最终业务源码：`b50b1f5b0eab66d7a4eb2a32314bcd415dba2624354cfb0ece59d2efce17ab8b`。
- 配置canonical：`22d0e525ba1074336a6d7af973cc50427eb96e4c3f5ad28d9a3c60e37ff65efc`。
- manifest：`0e94544429f865b2f2e35193f9f915e06282de9c1faf85fafe27d4891bb85533`。
- 请求稳定hash：`f3f16112c23330b0a5c142c3a64559d6cbd79f5e82ac00cd617529b5fc9526d9`。
- 题级key：`9dc35acea3b1133b409e403caa2eea8bfea70cf4e91d8e0ba3c01da47f243301`。
- prompt canonical：`c975587079e01a747990468487ac01c700137bc48578f130008e24ed676b5498`。
- 固定槽：`m6-05a-product-canary-r1`；started／settled均不存在。

本次仅文档复审，不改业务源码，故以上app源码身份保持，不应因文档提交重建不同产品输入。

## 计账与证据限制

本轮新增编码、重排、供应商／产品推理、正式质量写入均0；Mongo写入仅随机短m1_test_m4_合成测试库。真实状态经只读包装访问，未登记产品诊断配置／创建产品实验，原48 job保持暂停。前值23582／20602保持；它不是全项目累计。精确HTTP、费用与该次未来最大付费输出均null／unknown；请求4096不充当硬保证，不追加探测。

没有重扫现场582／867全量向量、全库文档、默认指针或TTL历史；保护结论限于上述文件hash、最终消费者实际所读资料和隔离测试。覆盖及测试通过不代表新答案正确。private-identity未读取，PDF、缓存、日志、原始证据、tmp均保留本机。

远程核验遇网络故障：本机默认代理127.0.0.1:7890不可用，单命令禁用代理后GitHub443亦不可达。启动仅核实本地HEAD与缓存origin/main一致，不能声称本轮已核远程main；提交推送结果以最终交接为准，不改永久Git网络配置、不强推。

## 唯一下一包与退出

执行方遵循[原完整授权Prompt](../handoffs/M6-single-product-canary-r1.md)与[维护后接续](../handoffs/M6-single-product-canary-resume-r1.md)。复用本次最终集成与单题预检证据，只核临发时身份未漂移及固定槽／账本无未知窗口；经正式接口完成本题必需登记后，最多发一次版1m6-g540-05-a产品stream。无论成功、纯reasoning／截断、归属失败、usage异常或前置失败均封存即停；不重试、不放行原48题，不评分、gate或proof。

成功只记该题限定诊断成功：可见未截断答案、LAN具名归MateDock3、机身RJ45独立、引用合法、raw usage合法且总output≤4096。正式M6仍5/7；04保持验收，05缺有效反馈proof，08缺有效新候选质量及阶段验收，M7未授权。后续批量范围须依据这一次真实结果裁定，不能在本包自动扩展。
