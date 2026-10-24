# M4 阶段执行提交

2026-10-25。M4-01至M4-10执行自验10/10，未完成任务ID：无；核心53/76、可选0/2。**待总控独立审查，执行会话未标记通过，M5未授权。** 任务完成指实现、固定实验和透明证据交付，不表示全部题目答案正确或生产容量已验收。

## 修改与复用

| 任务 | 实际实现与证据 |
| --- | --- |
| M4-01 | 50题来源审核及35/15问题族冻结，三原件/595切片/53图独立语料、准确资产对应；原链路35dev及真实只读复核，历史34次逻辑答案生成，人工0 |
| M4-02 | retrieval模型/adapters、V2Index与QueryRunner保留各路rank/融合/重排/修订/来源、稳定复合身份及实际入选证据 |
| M4-03 | products/resolver、query_planner、conversation/context处理目录精确/近型号/指代/通用清空/逐产品比较；修复明确接口编号被当陌生型号 |
| M4-04 | search/rerank/V2Index独立候选与融合策略，九组真实dev检索；修正错误澄清/失败丢失召回分母，旧原件不回写 |
| M4-05 | routing/graph有限可选分支、一次汇合与超时/失败/忙降级；兼容旧图移除占位KG，正式入口受鉴权快照约束 |
| M4-06 | expansion/evidence同产品/权限/修订父子相邻扩展，必要前提原子组、有界预算及资料多样性，默认关闭 |
| M4-07 | answering完整渲染token预算、字符兜底、编号/asset/revision门禁与截断部分回答；实际SDK合成HTTP验证输出字段兼容 |
| M4-08 | 复用已有model_host，锁定加载/推理与小批，显式query/document编码；查询向量缓存完整范围/TTL/LRU/退出代际，默认关闭；真实1/2/4资源观测 |
| M4-09 | providers分能力timeout/retry/JSON/格式、实际SDK错误分类及外层状态传播；策略默认显式关闭，保留原参数 |
| M4-10 | 严格可配置评测适配、逻辑计数、真实阶段复用与超时原耗时门禁；当前七组dev、35dev问答、固定选择后15heldout、助手答案抽检和独立只读核验 |

逐任务文件/红测/命令见[01](../records/M4-01.md)、[02](../records/M4-02.md)、[03](../records/M4-03.md)、[04](../records/M4-04.md)、[05](../records/M4-05.md)、[06](../records/M4-06.md)、[07](../records/M4-07.md)、[08](../records/M4-08.md)、[09](../records/M4-09.md)、[10](../records/M4-10.md)。完整变动文件及hash以[独立快照](M4-artifact-manifest.json)为准，明确基线为M3审查头83dd1b11c2873d11b0795099abc81260097b1638。

保留课程RAG底座与上游来源/许可证；复用既有FastAPI/LangGraph/Milvus/MinIO/Mongo、pymilvus WeightedRanker/RRFRanker、已安装BGE接口和实际模型宿主，没有复制服务端融合或另建重复宿主。Vue 3技术方向不变，M4本轮仅修测试夹具，没有新增生产UI逻辑、依赖或模型升级。

## 本轮验证与原始证据

本机原件均在evidence/output/evals，受[实际摘要](M4-validation-summary.json)的439份本机文件hash绑定；不上传题目、回答、对象URL、私有配置和原始日志。摘要/快照检查器显式选择本轮报告与快照，旧partial/任务快照/审查探针/失败输出全部保留。

| 实际命令或材料 | 本轮结果 |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -m 'not live_provider' -q --junitxml=docs/development/evidence/M4-final-stage-r2.xml` | 697 passed、2 deselected、0 skipped，退出0，562.82秒；456单元/115契约/126集成目录 |
| 同入口`tests/integration/test_evaluation_run_adapter.py`，JUnit M4-10-strategy-wiring.xml | 后续4 passed、22.37秒、退出0，含1个收集后新增用例；3项重叠，合计698唯一用例，不能将两次相加为701或声称一次698 |
| `.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -v` | 3 passed，0.006秒，退出0 |
| `pnpm -C frontend test:unit` / `test:e2e` | 37 passed/9文件，29.74秒；24 passed，56.3秒；退出均0。浏览器为离线协议模拟，不冒充新真实供应商浏览器验收 |
| `pnpm -C frontend typecheck` / `build` | 退出均0，构建12.73秒；18份构建文本未匹配本机敏感配置值 |
| `scripts/verification/recheck_m3_live.py`显式原config/flow | 原真实UI产物只读8检查通过、4消息有序，新调用0 |
| 当前质量网格 | 七组各35完成/0失败、245题次，退出0；4次逻辑HyDE invoke，没有生成答案 |
| 当前控制35dev | 35执行成功/0失败，33答案/2澄清、68消息、33 stream，p50/p95 22.43/51.82秒 |
| 固定选择后15heldout | 15执行成功/0失败，14答案/1澄清、31消息、14 stream，p50/p95 17.03/39.39秒 |
| 新真实问答只读核验 | [dev](M4-dev-readonly.json)与[heldout](M4-heldout-readonly.json)通过；分别23/19份引用图片hash/完整解码、消息顺序/答案/唯一终态、准确引用/修订/图片与完整语料通过；无模型调用 |

集成目录含真实隔离Mongo/Milvus/MinIO及端口注入，不能把所有127项都称为真实供应商全链路。2项付费导入回归按选择排除，未运行不算通过；已有供应商产物只读复核，未重复解析/摘要。新真实问答和4次假设调用单独计量。另有99项定向、25项导入隔离与3次分页重复等重叠结果，不再累加唯一数。

真实实验精确入口：`PYTHONUTF8=1`、`PYTHONPATH=.`，`.venv/Scripts/python.exe output/evals/run_m4_10.py quality --dataset evals/datasets/support-v1-r2.jsonl --manifest evals/datasets/support-v1-r2-manifest.json --config evals/configs/m4-10-quality.yaml --output output/evals/support-v1-r2-m4-10-quality`。35dev/15heldout使用同入口mode=answer，分别显式选择m4-10-dev-control.yaml/m4-10-heldout-control.yaml与相应新输出。包装只在本进程禁模型桥接、开启离线权重、关闭日志，不改.env；本机脚本与145份执行字节副本均hash绑定。真实只读核验命令`python scripts/verification/recheck_m4_evaluation.py --config <本轮YAML> --output <已结束结果目录> --report <新报告>`，没有写入型仓储或模型构造。

正式M4-10红测保留：原适配器拒绝可配置策略（1失败）、缓存加速让原超时HyDE重新被接纳（1失败）、缓存耗时未校验（1业务失败）。修复后99项定向通过，最终完整与补充验证如上。首轮完整696通过/1失败来自旧图测试模块污染，改为新进程保持原断言；浏览器23通过/1失败来自有限SSE夹具的合法断流回读，保留严格一次快照并新增一次正确订阅断言。材料摘要首次自收集正在写的日志导致hash不一致，旧候选原字节留本机，避免循环后新摘要独立检查通过。上述测试/材料问题均未冒充业务红测；其他历史夹具/命令错误见各记录。

## 默认选择、质量与成本

继续Weighted(.5,.5)、20/20/20/20/10，增强/扩展/查询缓存默认关闭，完整预算32768/4096/256和12000字符兜底。新七组控制/扩展/HyDE/分解/组合/宽窗口来源覆盖80.88%，RRF86.76%；RRF仅提高来源覆盖，不足以证明稳定答案收益。九组历史候选与1/2/4资源数据见[实验报告](../../evaluation/retrieval-report.md)，复用后的wall不能当生产时延，也不能据单波次增加模型进程。

dev结束和13题执行助手抽检后于本地02:42:45冻结选择及开发报告hash，策略指纹`350a61ad7b2d025401c01c1912930bdbdb792e71afd450565b6650d5f998a91a`；之后才运行heldout，未调参。heldout后只记录4题助手抽检，不回写选择/评分/标准。默认配置与选择文件只存本机，其hash在摘要；回滚使用正常反向提交，或显式保持增强/扩展/缓存关闭，不删除任何知识或实验现场。

**本轮新增51次供应商逻辑调用：4 invoke + 47 stream；精确SDK HTTP重试数及金额未知。** 历史M4-01的34次答案生成单列，未重复计为当前。模型/依赖/原件/解析缓存/活动修订/桶策略未改；新写入仅原M4隔离账本的本次实验会话/run及本机结果，集成故障验证使用独立合成目标。

人工0、human_answer_correctness=null。执行助手抽检dev13/heldout4，未生成全题集正确率。保留失败例：004/006/009/019缺命令/配置，012释义不全，048比较缺一侧；042 MAC归属不明确，043虽准确图入引用仍缺采集端字段。049/050语义拒答基本正确，但保守behavior因有引用判answer而误判，050还缺官方资料建议。001/027误澄清在来源分母计0。来源覆盖、执行成功率、辅助行为匹配均不等于语义正确率。heldout缺歧义/跨型样本、dev分解真实未触发，不声称这些分支已有真实质量收益。

## 边界、回滚与总控接续

数据仍为三资料595切片/53图，语料hash保持dd01944db688807c158923c0d21d272f1f45aa4304aa9012efada71c2c18b810；旧课程集合/桶策略及原文件不动。历史Windows原生模型加载异常与图片未知根因未宣称根治，原失败证据保留。资源1/2/4只为小样，不代表生产容量、Ubuntu部署或灾备验收。

Git main实现5517224、测试/网格2563182已正常推送核对。最终材料提交自身SHA及远程核对在最终交接补记，不循环amend；原始evidence/output/evals不暂存。后续修复用正常新提交，保留原件与旧快照，不reset/强推。总控可使用显式summary/manifest/base的build_m4_artifacts检查本轮材料，依据本次实际命令和语义失败独立审查；审查前不进入M5。后续质量提升应新建开发/评价版本，不继续用已评价heldout调参。
