# M6-05 regression来源闭环总控独立定向复审 r1

日期：2026-10-29。被审提交：`338507b6af950e127ac6f24cc665ad95a9199cb8`；开始时HEAD、origin/main与远程一致，工作区仅未跟踪`tmp/`。本轮为独立取证与审查文档，不修改业务源码，不执行真实反馈绑定或质量评测。

## 结论

**本次技术审查暂不关闭：RGL-R1／P1、RGL-R2／P2待补修。** 完整回答来源、不可变标签/版本、控制库与目标库分离、正式来源消费及服务端证明已有隔离通过证据；两个新问题集中在澄清结果的入口和故障恢复，不能以217项既有回归通过替代。

| 审查项 | 定位 | 独立观察及影响 |
| --- | --- | --- |
| RGL-R1／P1 | `app/evaluation/feedback_regression.py:73-74` | 正式接口允许对`awaiting_input` Run提交反馈并确认成regression；新来源服务仅接受`completed`，在完整标签候选创建前返回409 `regression_source_invalid`。不必要澄清类反馈无法进入新闭环。 |
| RGL-R2／P2 | `app/evaluation/query_adapter.py:99-101` | 评测外层合法`completed`、内部Run为`awaiting_input/clarify`，正常发布成功；在results落盘后、数据库完成发布前退出，同身份恢复被新检查器按“Run必须completed”拒绝，实验变成`failed / attempt 2 / retryable=false / provider_invalid_response`。 |

AF、SQ、continuation、图片协议及来源前提既有关闭结论保留。本轮未发现这些旧审查项需要重开；新恢复缺陷在新增regression接线范围内挂账，不追改历史实验。

## RGL-R1：已确认澄清反馈的来源入口

独立探针通过正式QueryRunner产生`awaiting_input` Run，随后调用正式`save_feedback()`和`review_feedback()`确认regression，再调用`RegressionService.candidate()`。反馈合法、已确认，但在`source()`的completed限定处失败；合成答案调用0，原Run未改，无需伪造状态即可复现。

历史材料`M6-08-001-live-continuation.md`记录过001“型号已知却继续澄清”的regression反馈。这说明该来源形态与既有问题相关；本轮没有读取真实业务库，不宣称已核实该反馈当前状态或完成绑定。

补修不能只删除状态判断：无引用的澄清还可能没有`source_revisions`，后续绑定的原件范围约束仍须满足。应保留原Run及实际澄清结果、输入和来源身份，为无生成引用的反馈提供受授权、可审阅、带原件修订哈希的证据关联；已存在原件范围不得任意扩大。当前`run_fields`不含澄清候选及恢复点，新增受支持结果形态时须明确实际使用的快照字段及变化拒绝规则。不能把运行中/任意失败Run一并放行，不能补造旧引用、把旧Run改成completed或用新成功Run冒充旧来源。

验收要求：正式“澄清Run→反馈确认→候选/独立审核→精确绑定或必要派生”可完成；无证据、撤权、来源变化和错误映射拒绝；正常completed来源保持。覆盖同库及分库，并证明不修改旧Run和旧反馈身份。

## RGL-R2：澄清成功检查点的结果发布恢复

独立成对探针使用同样的正式派生完整dev：一题正常回答、一题未知型号而合法澄清。测试模型与查询向量均明确合成，实际QueryRunner、job、检查点及关联服务执行。

1. 无故障对照：实验`completed / attempt 1`；澄清记录外层`status=completed`，内部`state=awaiting_input, behavior=clarify`。
2. 故障对照：results.jsonl写入后，在`repo.complete()`前抛出合成SystemExit；仅在随机测试库将本测试租约过期，然后由正式入口重新领取。
3. 恢复进入attempt 2，新检查器拒绝澄清Run，实验failed且不可重试。正常回答题有attempt 2观察关联，澄清题没有。目标Run仍3条（来源回答、dev回答、dev澄清），合成答案调用仍2次，无恢复新增调用。

根因是把“题级评测已完成”误等同于“内部Run completed”。首次执行本来支持clarify，恢复却增加更窄条件。应按合法结果形态校验同一Run、输入、状态及实际输出/澄清内容，同时保留已有source/config/题级关联、累计调用和本次新增记录。不能删除来源校验、强改Run state或retryable，也不能通过另建Run规避恢复。

验收要求：两种合法结果的正常/故障对照均完成；恢复沿用相同Run，当前attempt正式观察关联齐全；重复恢复不增调用，累计遥测不丢，缺测仍null。输入、来源、Run或结果被更改仍拒绝。

## 本轮实际验证

| 检查 | 实际结果 |
| --- | --- |
| 原17文件共享回归（含执行方新增链路） | **217 passed**，退出0，254.53秒；2条既有SWIG弃用warning，进程另有swigvarlink warning。 |
| 最终独立探针 | **2 failed / 1 passed**，退出1，20.38秒；RGL-R1入口及RGL-R2故障恢复失败，无故障对照通过。 |
| 前端typecheck | 退出0。没有UI行为变更，未重复浏览器验证。 |
| OpenAPI | 与`create_app().openapi()`一致，55条路径。未改类型文件，未重新声称运行generate:api。 |
| 历史文件保护 | 三份既有清单**821/821、404/404、294/294**匹配；组间可重叠，不累计。 |

原始命令、JUnit、独立探针、诊断和日志在本机`output/m6-reg-lineage-review-20261029/`，不上传。共享命令为`shared-command.ps1`；最终探针可在仓库根目录执行（须现有隔离测试Mongo可用）：

```powershell
$env:M1_TEST_DB='m1_test_m4_regression_review_final'
.\.venv\Scripts\python.exe -m pytest -q -p tests.conftest -p tests.integration.conftest output/m6-reg-lineage-review-20261029/test_independent_recovery.py --basetemp=output/m6-reg-lineage-review-20261029/final-probe-work --junitxml=output/m6-reg-lineage-review-20261029/final-probes.xml
```

复审已存上述目录；补修方运行时另选新basetemp、JUnit及日志路径，不覆盖原失败现场。两个`-p`为output目录外探针显式加载正式夹具。最初缺少mongo_db夹具产生2个setup error，属于取证脚本准备错误，不计为业务反例；`probes2`诊断曾触发已有本地编码器的两条候选文本编码，无供应商调用或下载。后续`probes3`及最终三探针显式注入合成向量，仍复现缺陷；原错误和中间日志均保留。新闭环中的审核artifact通过路径为明确的合成夹具，不冒充真实独立审阅。

## 保护、验收与执行交接

本轮只对随机隔离Mongo库执行合成反馈、标签审核、实验及故障窗口；未访问真实业务集合，不宣称历史集合摘要已重新核验。无供应商调用、真实dev/heldout、真实human/观察/校准/candidate/证明写入，无语料导入或默认修订切换。真实r3的19继承＋66执行、旧失败、未知窗口调用及费用保持原身份；没有把缺测写成0。原始证据、output/evals及tmp保留。

下一步由执行方先将本机3项独立探针纳入合适回归，用最小改动补修上述两处，不追加供应商运行。补修交付须包含红绿对照、同库/分库、来源变化拒绝、正常/发布崩溃恢复及调用账本证据，再交总控定向复核。通过后继续匹配既有真实regression反馈与已审dev，精确绑定或必要派生；不要求用户重找PDF、重复已有判断或手工修状态。

M6-04的有效正式双轮/未知处理/预校准、M6-05真实反馈后复评、M6-08同范围有效候选与有序质量证明仍未满足。四题对象/配件和019/021/022/048召回缺口继续保留。当前既有质量前置，也有本轮可由执行方补修的技术边界，不能只归因于人工评分。**M6仍4/7，04/05/08未验收，M7未启动。** 本轮源码未改，正常反向提交审查文档即可回退本轮导航；不得删除或重写历史证据。
