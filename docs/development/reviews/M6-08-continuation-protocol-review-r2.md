# M6-08 continuation R1/R2独立定向复审

日期：2026-10-28。审查提交`b7dfe03e0fbfb416b6a53bd348eca2f1d424dab3`，开始时HEAD、origin/main及GitHub远程一致，工作区仅tmp未跟踪。六个既有容器运行，Mongo ping通过。读取AGENTS、进度、审查状态、计划契约、[原审查](M6-08-continuation-protocol-review-r1.md)与[补修自验](M6-08-continuation-protocol-fix-r2.md)后顺序复审，无子代理。

结论：**R1/P1原缺陷定向核验通过；R2不通过，保留待修复**。新增分库组合探针证实R2实现使用错误的实验账本位置，影响正式工作台首题执行，严重性为P1。该结论是针对提交的独立技术核验，不标记M6阶段总控验收通过；M6仍4/7、M6-04/05/08未验收，M7未授权。

## R2-R（P1）：把Run目标库误当作实验控制账本，正式分库路径失败

位置：[execution_links.py:12](../../../app/evaluation/execution_links.py:12)，同类来源查询见该文件第39行；调用位置[query_adapter.py:209](../../../app/evaluation/query_adapter.py:209)。

正式拓扑中，[API资源](../../../app/main.py:22)和[模型宿主任务仓储](../../../app/evaluation/jobs.py:92)从`Settings.database/M2_DB_NAME`读取实验、attempt、worker及租约；[评测资源工厂](../../../app/evaluation/query_adapter.py:44)从冻结`config.target.database`读取隔离Run/知识。工作台手册也明确API与宿主共享M2控制账本，而target为独立评测目标。两者不要求同库。

补修后的job仅传递experiment/attempt/token/config身份值，未传递控制账本读取能力。adapter调用`bind_execution(self.resources['db'], ...)`，该db是Run目标库；`bind_execution`和`require_source_link`却在这个库查询`evaluation_experiments`。有效控制任务因此被误判为“当前实验执行身份或租约无效”，不能建立题级来源，也不能执行模型。创建Run在校验之前发生，故目标库已留下pending Run及会话占用。该Run应沿正式pending超时/恢复语义收敛，本轮不手工清理。

独立探针使用正式EvaluationService→execute_job→RealQueryExecutor→RunService→QueryRunner，仅资源/检索/模型注入隔离合成端口，未替换新关联函数。对同一测试分别选择控制与Run账本同库、分库，owner/kb及冻结参数保持匹配：

| 组合 | 实际结果 |
| --- | --- |
| 同库对照 | completed，模型调用1，completed Run1，execution link1 |
| 控制库与target分离 | failed、retryable=false；题级ValueError被分类为provider_invalid_response；模型调用0；target内实验0、pending Run1、link0 |

最终组合2项为1通过/1失败，失败在预期completed的业务断言，不是setup。补修自验中的正式组合测试把`EvaluationRepository`与adapter资源都放在`resources['db']`，因此107项通过不能覆盖真实分库路径。该问题同样会阻断completed checkpoint的正式观察复用：其状态也进入bind_execution；它不属于只有首次生成才会发生的限制。

建议保留控制账本与Run账本的职责：由正式job提供可信控制仓储/受控查询能力，当前worker和父来源的鉴权/租约检查访问真实控制账本，题级关联与目标Run按明确映射保存和核验。不能复制实验记录到target、关闭租约校验、改冻结target为控制库或回填历史关联来绕过。先验明执行身份再产生持久Run副作用；若跨存储窗口仍可能留下pending Run，须按正式恢复协议留证处理，不手动清占用。补充真实分库组合，覆盖首题、completed观察复用、合法continuation、错误父/旧attempt拒绝与重建幂等，再独立复审R2。本轮未修改业务源码或实施修复。

## R1原缺陷：本轮定向核验通过

M6结果现在读取持久Run的累计调用并标`logical_provider_calls_scope=run_total`，本次adapter差值另存`execution_logical_provider_calls`；缺少/无效累计保持null。澄清分支在等待事件同一次CAS中保存明确测得的零值。源码、107项定向中的真实counter包装/落盘前退出/恢复汇总测试以及原探针兼容副本均支持该修复：恢复累计1、本次0，无新增调用；正常复用不把累计改0或相加为2。未知精确HTTP、费用仍null。

原审查探针未改。本轮在新目录复制并核对补修方兼容副本，仅升级合法父关联夹具及累计/新增断言；原“恢复计数等于持久累计”和“未执行该题的父实验须调用前拒绝”核心断言保留。该副本3项独立重跑通过。同库来源关联拒绝能力有证据，不能由此推断跨库接线通过。R1定向结论不扩展为全部评测核账或质量验收。

## 已存r3及证据边界

本轮520项直接只读核验通过，45份历史证据hash未变；原manifest/attempts/results与r2备份一致。原实验仍failed/attempt2、retryable=false、provider_invalid_response、持久结果0；r3仍completed/attempt1/result_attempt1、85条结果，19继承+66执行，31审核标签/54草稿。Run分布80 completed、旧020 interrupted1、awaiting_input5；实验slot/token/lease已释放，5个澄清等待保留。

已存已完成Run结果调用与Run遥测一致，历史stream19与r3新增61、invoke0分列，未发现R1污染已存r3。目标库所有现有集合前后摘要和名称一致；没有新增execution link、continuation或human/followup/observation/calibration，不回填来源。R2分库失败由本轮随机测试库复现，不在真实目标生成或恢复任务。旧attempt2触发勘误保留，本轮不重新认证聊天工具来源；未知HTTP/费用不补零。

不重新执行旧准备/迁移/生成/导出脚本，不重跑历史1975/9838/9的持久/来源图像/浏览器全链路，不认证历史配置在当前源码下可运行。85条组合继续仅为已存技术对照，非同代码独立85题生成、反馈后新生成或答案质量达标。独立人工双轮、预校准、候选比较和反馈后人工复评仍缺；不复制已有聊天、不要求重复判断或网页重审。

## 本轮实际验证

| 组 | 本轮结果 |
| --- | --- |
| R1/R2及既有定向 | 107通过、0失败/错误/跳过；2条SWIG弃用warning及末尾swigvarlink提示 |
| 原探针兼容副本 | 3通过 |
| 分库独立组合 | 1通过、1失败；pytest退出1 |
| 共享查询/清槽/遥测 | 最终20通过 |
| 前端typecheck | 退出0 |
| 已存r3直接只读核验 | 520检查通过、45历史证据hash一致 |

组间覆盖重叠，不累计唯一总数。共享组首次测试库前缀过长，夹具第二次追加随机后缀超Mongo 63字符上限，6通过/14 setup错误；缩短显式前缀后20通过。分库探针首次也是库名64字符导致setup路径失败；缩短前缀后单项业务断言失败，再加同库对照得到上述1通过/1失败。各次JUnit/log原样保留，不把测试环境错误当产品缺陷或隐藏为通过。

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:M1_TEST_DB='m1_test_m4_continuation_rereview_20261028'
.venv/Scripts/python.exe -m pytest tests/integration/test_evaluation_continuation_regressions.py tests/integration/test_evaluation_run_adapter.py tests/integration/test_evaluation_jobs.py tests/integration/test_run_commands.py tests/unit/test_evaluation_query_adapter.py tests/unit/test_evaluation_dataset.py tests/unit/test_evaluation_catalog.py tests/unit/test_evaluation_host.py tests/unit/test_eval_metrics.py -q --junitxml=output/m6-continuation-rereview-20261028/targeted.xml
$env:M1_TEST_DB='m1_test_m4_rr_probes_20261028'
.venv/Scripts/python.exe -m pytest output/m6-continuation-rereview-20261028/test_original_probes_compatible.py -q --junitxml=output/m6-continuation-rereview-20261028/original-probes.xml
$env:M1_TEST_DB='m1_test_m4_rr_split_20261028'
.venv/Scripts/python.exe -m pytest output/m6-continuation-rereview-20261028/test_independent_boundaries.py -q -s --junitxml=output/m6-continuation-rereview-20261028/topology-comparison.xml
$env:M1_TEST_DB='m1_test_m4_rr_shared_20261028'
.venv/Scripts/python.exe -m pytest tests/integration/test_query_runs.py tests/integration/test_support_clear_slots.py tests/integration/test_run_telemetry.py -q --junitxml=output/m6-continuation-rereview-20261028/shared-final.xml
```

集成使用每例随机独立库，不删除库；合成模型计数不等于供应商调用。供应商/真实dev/heldout/真实人工/校准/真实目标写入均0。无服务重启、容器/卷变更、语料重导入或旧检查点写入。未重跑全量后端/前端单元/浏览器/build、Linux队列或重导入。原始输出留本机`output/m6-continuation-rereview-20261028/`，不上传；[脱敏验证摘要](M6-08-continuation-protocol-review-validation-r2.json)记录本轮与历史证据hash。

下一步修复R2的控制/目标账本接线并定向复审；R1原复现问题已获独立通过结论，M6阶段状态不变。正常提交本轮脱敏材料供原规划总控复核，不自行推进阶段，不启动M7。
