# M6-08 continuation与r3组合材料只读审查

日期：2026-10-28。审查提交：`636b1a2b7761c53184b4cd371fe2865a1dcaed66`，开始时HEAD、origin/main、GitHub远程一致，仅tmp未跟踪。六个既有容器运行、Mongo ping通过。本轮为执行端顺序源码审查及独立故障探针，供原规划总控复核；不代表总控阶段验收。M6保持4/7，M6-04/05/08未验收，M7未授权。

结论：既有88项回归重新通过；新增探针2失败/1通过，确认以下两处协议缺口。本轮只记录发现和建议，未修改业务源码、重启服务或启动真实模型。协议尚不能据本轮结果视为完成审查。

## R1（P1）：完成后崩溃恢复会漏计题级已观测逻辑调用

位置：[query_adapter.py](../../../app/evaluation/query_adapter.py:259)，另见澄清返回路径第206行和[结果汇总](../../../app/evaluation/metrics.py:157)。适配器返回的`logical_provider_calls`来自本次进程内counter差值；continuation账本从持久Run遥测读取，两者含义不同。

复现：给隔离正式QueryRunner注入合成模型及与真实资源相同的LogicalProviderCounts包装。中断源Run通过正式recover收敛；continuation新Run完成后、适配器返回及题级attempt日志写入前注入退出。重建执行器使用相同continuation/request_key，正确复用同一completed Run，没有新增调用；但返回`stream_started=0`，持久Run和continuation账本均为1。运行器会把这个0写入后续题级结果并参与实验汇总，丢失本实验在崩溃前已经观察到的调用。现有重建测试未配置provider_counts，未覆盖生产counter包装下的该差异。

正常复用时“本次恢复新增调用0”属实，但不能用它覆盖“该题Run已观测调用1”。建议分别记录本次新增与Run累计范围，按持久来源核账；未知继续null。补充Run完成而结果尚未落盘、重建执行器及最终汇总的回归，确认不新增调用、不漏计、不重复计数。精确HTTP/费用仍未知，不将逻辑计数修复扩展成费用承诺。

证据：本机`output/m6-continuation-review-20261028/test_review_probes.py`的`test_completed_run_crash_recovery_preserves_observed_call_count`在0与1的断言处失败；正常完成/复用对照探针通过。

## R2（P2）：声明的父实验与所选父Run缺少题级关联验证

位置：[continuations.py](../../../app/evaluation/continuations.py:17)及[选择检查点](../../../app/evaluation/query_adapter.py:160)。创建服务检查父实验owner/kb、终态、attempt/version与冻结hash；执行器之后直接从全局`fingerprint([config, question_id])`检查点选择previous Run，并将调用方context.source与该Run一起写入来源账本。这里没有证据证明该Run由声明的父experiment/attempt执行或继承，也没有“来源关联未核实”的区分。

复现：同一隔离库中先通过正式执行器生成题级Run，合成过期后正式recover为interrupted；再经正式EvaluationRepository创建并claim另一个相同冻结配置的实验，使其在未执行题目前正式fail。以这个真实终态父实验创建continuation，父实验代际/冻结门禁全部通过。把服务端保存的来源原样交给执行器，执行器接受此前另一执行留下的interrupted Run，建立新Run并调用合成模型，没有在来源不匹配时拒绝。探针预期调用前拒绝，实际DID NOT RAISE。此场景未篡改历史检查点、旧Run身份或父实验retryable；测试中的状态写入仅用于隔离合成过期。

影响是来源完整性：两条分别存在的experiment与Run被并排保存，不能由此证明父题级执行关联。它不是跨所有者越权，也不推翻现有nonretryable Run拒绝测试。建议为题级执行/继承保存可核实的experiment/attempt/question/input→Run关联，continuation调用前核对；历史记录缺少这种关联时明确保留未知并走显式留证流程，不自动认定或回填已认证来源。新增正式来源与真实adapter组合回归，覆盖同配置不同父实验及父attempt变化。

## r3组合技术结果的适用范围

独立只读脚本未执行历史准备、创建、迁移、生成、导出或旧审计脚本；直接核对已存文件与Mongo。520项检查通过，包括45份历史原始证据hash、原三文件与r2备份、19条继承原文/检查点绑定、85题集合/持久投影/Run与答案、已完成Run调用遥测、020新旧身份、汇总及目标库全部现有集合前后摘要不变。

当前仍为：原实验failed/attempt2、retryable=false、provider_invalid_response、持久结果0；r3实验`79b3cc58-cfd4-4da5-84c0-890d92a9be06`completed/attempt1/result_attempt1、85条completed结果。86个Run分别80 completed、1旧020 interrupted、5 awaiting_input；实验worker token/lease与owner slot已释放，5个正常澄清等待保留。该隔离目标human/followup/observation/calibration仍0，未回填continuation。

85题仍是19继承+66执行，31审核标签/54辅助草稿；逻辑stream历史19、新增61，invoke均0。本轮已完成Run结果中的调用计数与Run遥测一致，未发现R1已污染这些历史结果；R1仍是未来恢复场景的有效缺陷。R2不用于回溯否定或重新认证r3的独立继承证据。旧attempt2触发勘误保留原r3表述，本轮未重新认证聊天工具来源；失败窗口HTTP/费用未知。

45份证据hash一致包含先前检索、图像与离线固定报告原件；本轮没有重新进行全部切片/图像读取、浏览器或完整语料向量核验，不能将历史1975/9838/9写成本轮重跑。当前源码身份已变化，不以历史r3配置冒称当前运行时校验通过，也不修改冻结config。r3可继续作为来源明确分列的85题技术对照材料，不能作为同代码85题独立重生成、反馈后新生成、答案质量或性能提升证明。

## 实际命令与下一步

```powershell
$env:M1_TEST_DB='m1_test_m4_continuation_review_20261028'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m pytest tests/integration/test_evaluation_run_adapter.py tests/integration/test_evaluation_jobs.py tests/integration/test_run_commands.py tests/unit/test_evaluation_query_adapter.py tests/unit/test_evaluation_dataset.py tests/unit/test_evaluation_catalog.py tests/unit/test_evaluation_host.py -q --junitxml=output/m6-continuation-review-20261028/targeted.xml
$env:M1_TEST_DB='m1_test_m4_continuation_review_probes_20261028'
.venv/Scripts/python.exe -m pytest output/m6-continuation-review-20261028/test_review_probes.py -q --junitxml=output/m6-continuation-review-20261028/probes-final.xml
.venv/Scripts/python.exe -c "import runpy; runpy.run_path('output/m6-continuation-review-20261028/audit_saved_results.py',run_name='__main__')"
```

原组88 passed/退出0；新增最终探针2 failed/1 passed/退出1，均为预期行为断言失败而非setup错误；较早探针1 failed/1 passed保留，覆盖重叠不累计。Mongo使用显式测试前缀与每例随机后缀，不删除库。供应商模型/heldout/真实human/新校准/真实目标写入均0。未重跑全量后端、前端、类型/build、重导入或Linux队列。原件、日志、脚本只在本机；[脱敏摘要](M6-08-continuation-protocol-review-validation-r1.json)登记结果与hash。

下一步先修复并定向复审R1/R2，再按新规则处理独立人工双轮、预校准、候选比较与反馈后复评。不得通过继承、复制已有聊天、助手评分或回填时间替代人工与先校准顺序，不要求用户重复已有判断或回网页重审。M6阶段材料仍交原规划总控，不自行勾选04/05/08，不进入M7。
