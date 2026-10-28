# M6-08 R2分库接线独立定向复审

日期：2026-10-28。审查提交`f92f6ec68999986fa1037294a4f57f0edca0d37e`，开始时HEAD、origin/main、GitHub远程一致，工作区仅tmp未跟踪。六个既有容器运行，Mongo ping通过。按AGENTS顺序读取进度、审查状态、计划/契约、[上轮复审](M6-08-continuation-protocol-review-r2.md)和[补修材料](M6-08-continuation-protocol-fix-r3.md)，无子代理。

结论：**本轮独立定向复审通过，关闭R2及其R2-R/P1分库接线技术审查项**；R1原缺陷独立通过结论保留。未发现本轮范围内新的阻塞问题。该结论仅覆盖恢复/来源协议定向复审，不是M6阶段验收或答案质量通过。M6仍4/7，M6-04/05/08未验收，M7未授权。

## 源码与正式链路

正式[execute_job](../../../app/evaluation/jobs.py:60)将现有控制库能力显式传入adapter；不是将数据库名、连接或worker token持久化成客户端配置。当前experiment/attempt/worker/注册配置hash、owner/kb及有效租约在控制库校验，父实验也从该控制库读取。Run、checkpoint、execution link与continuation继续保存在冻结目标库。link明确绑定control_database/target_database、题目、输入/config、Run与conversation；派生固定父link ID/hash，缺链或映射不符拒绝。

[当前身份校验](../../../app/evaluation/query_adapter.py:170)在conversation/checkpoint/Run写入之前执行；[绑定关联](../../../app/evaluation/execution_links.py:26)前重验。原分库探针原件直接重跑，同库和分库均completed、合成调用1、completed Run1/link1；分库目标实验数0，没有向目标复制控制实验。该结果直接解除上轮“target查不到控制实验导致首题误拒”的复现。

121项定向包含14项分库/故障回归，支持completed观察复用、合法continuation、错误父实验/旧attempt、错误控制或目标映射、缺控制能力/无效worker/过期租约在相应边界拒绝。正式job在子Run创建后、关联后两个进程退出窗口重建并claim新attempt，固定请求复用同一pending Run，没有第三条Run或重复调用。父实验原文不变，completed重投无新调用。

独立增补4项分库来源探针通过：子Run完成又正式recover为interrupted后重建任务，停止而不派生第三条Run；子Run已关联但尚未调用模型时退出，若父link内容hash变化、同题关联不再匹配或父version变化，重建均在模型前拒绝，原continuation全文不变。测试中的损坏与租约推进仅发生在新随机库，不改变真实历史证据。

控制校验和目标写入之间没有跨库事务，仍可能在身份校验后恰好失效而遗留pending Run。这是已明确记录的窗口；本轮定向验证关联前重验阻止模型调用，再通过正式RunCommands.recover持久化interrupted事件并释放会话占用。没有以手工删除Run或清state/lease/slot解决。该窗口不构成exactly-once或已知费用承诺。

## 本轮独立验证

| 验证 | 实际结果 |
| --- | --- |
| 补修及既有定向 | 121通过，0失败/错误/跳过；2条SWIG弃用warning及末尾swigvarlink提示 |
| 原拓扑探针原件及旧兼容探针新副本 | 5通过；兼容副本与补修材料副本字节一致 |
| 独立分库来源变化/再次中断探针 | 4通过 |
| 共享查询、清槽及遥测 | 20通过 |
| 前端typecheck | 退出0 |
| r3已存结果与历史证据直接只读 | 520检查通过、45历史证据hash未变 |

各组重叠，不累计唯一总数。原探针文件保持不变；本轮兼容副本仅显式设置控制库能力，原核心断言保留，不将补修方的自验当成本轮独立结果。OpenAPI、Python语法、补修证据hash、原探针hash与文档链接另由[脱敏摘要](M6-08-continuation-protocol-review-validation-r3.json)记录核验。

本轮第一次复制副本时新目录尚未建立，FileNotFoundError；随后两条重定向命令也因目录不存在而未启动pytest，包装退出码0不代表测试通过。建立新目录后重新执行，实际121/5/4/20结果均以本轮JUnit及进程退出0确认；目录准备失败另存setup-note，不覆盖历史证据。

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:M1_TEST_DB='m1_test_m4_sr3_all'
.venv/Scripts/python.exe -m pytest tests/integration/test_evaluation_split_ledger.py tests/integration/test_evaluation_continuation_regressions.py tests/integration/test_evaluation_run_adapter.py tests/integration/test_evaluation_jobs.py tests/integration/test_run_commands.py tests/unit/test_evaluation_query_adapter.py tests/unit/test_evaluation_dataset.py tests/unit/test_evaluation_catalog.py tests/unit/test_evaluation_host.py tests/unit/test_eval_metrics.py -q --junitxml=output/m6-split-review-20261028/targeted.xml
$env:M1_TEST_DB='m1_test_m4_sr3_probes'
.venv/Scripts/python.exe -m pytest output/m6-continuation-rereview-20261028/test_independent_boundaries.py output/m6-split-review-20261028/test_original_probes_compatible.py -q -s --junitxml=output/m6-split-review-20261028/original-probes.xml
$env:M1_TEST_DB='m1_test_m4_sr3_extra'
.venv/Scripts/python.exe -m pytest output/m6-split-review-20261028/test_independent_sources.py -q --junitxml=output/m6-split-review-20261028/independent-sources.xml
$env:M1_TEST_DB='m1_test_m4_sr3_shared'
.venv/Scripts/python.exe -m pytest tests/integration/test_query_runs.py tests/integration/test_support_clear_slots.py tests/integration/test_run_telemetry.py -q --junitxml=output/m6-split-review-20261028/shared.xml
```

随机测试库保留不删除，模型/检索为合成端口，不能作为供应商全链路或质量数据。本轮未改业务源码、未重启服务、未重导入语料、未运行真实dev/heldout或供应商模型，未写真实human/observation/校准，未回填历史关联。前端只重跑typecheck，未重跑前端单元/浏览器/build；未重跑全量后端、重导入或Linux队列。原始日志、JUnit、脚本仅留本机`output/m6-split-review-20261028/`，不上传。

## 历史材料与下一步

r3仍为`79b3cc58-cfd4-4da5-84c0-890d92a9be06`的85条completed组合结果，19继承+66执行，31审核标签/54辅助草稿；历史stream19与r3新增61、invoke0分列。原实验仍failed/attempt2、retryable=false、provider_invalid_response、持久结果0；原manifest/attempts/results与r2备份一致，失败窗口及精确HTTP/费用未知。

Run状态仍80 completed、旧020 interrupted1、awaiting_input5；实验worker token/lease与owner slot已释放，澄清等待正常保留。r3目标所有现有集合名称和前后摘要未变，无新增execution link/continuation或评分/校准；不把本轮合成恢复作用于真实目标。旧attempt2触发勘误保留，不重新认证聊天工具来源。

历史1975持久/9838来源图像/9浏览器全链路本轮未重跑，只复核已存文件与证据hash；不认证历史冻结配置在当前代码下可执行，不把组合报告认定为独立同代码85题新生成、反馈后新生成、性能或答案质量提升。

接续点：R1/R2技术审查项已获独立定向通过，后续按M6原授权处理新规则独立人工双轮、预校准、候选比较及反馈后人工复评，阶段材料仍交原规划总控。已有聊天判断不重复索取、不复制成双轮，不要求用户回网页重审；未完成门槛保持未验收，不自行进入M7。
