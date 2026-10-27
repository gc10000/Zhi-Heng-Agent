# M6-08 完整dev有来源后续实验与检查点继承

日期：2026-10-27。起点`5fa74ebbacbe6a91749ea635490166f2c7669f86`。原实验`a5607e05-de22-4b24-9570-e85b7e09b521`保持`failed/attempt 2`、`retryable=false`；新后续实验为`79b3cc58-cfd4-4da5-84c0-890d92a9be06`。M6仍4/7，M6-04/05/08未验收，M7未授权。

## 来源勘误与旧证据

[r2报告](M6-08-full-dev-baseline-r2.md)保留原样。回溯本聊天工具记录可确认：上一轮执行助手曾调用正式`execute_job`，原实验由过期租约领取attempt2；命令漏传首次脚本的`MODEL_HOST_URL/TOKEN`清空及离线环境覆盖，冻结runtime校验在执行器初始化阶段失败，正式失败路径记录`provider_invalid_response`。原20条本地尝试和manifest未变化、持久result_attempt为空，不据此把历史失败窗口的精确SDK请求或费用写成0；旧未知费用保留。r2记录的“触发来源未知”由本段追加说明，不修改历史原件。

原19条成功Run与020 interrupted Run、原实验失败均保留。上一轮`failure-snapshot-r2-20261027T1504Z`与r2的`pre-recovery`各自保留，不清理、不上传。原19条已完成结果只作为继承检查点，不能冒充本轮独立生成。

## 恢复实现与派生配置

正式M6 job将`client_request_id:experiment_id:attempt`传入适配器作为来源执行键；显式执行面对已收敛interrupted Run时，用原检查点身份、旧Run ID及执行键派生新幂等请求。completed仍复用、非retryable失败仍拒绝、普通调用不会自行重跑。旧state/token/lease/slot不手工清除。该机制不承诺失败窗口exactly-once。

代码指纹涵盖`app/`所有Python文件，修改恢复实现后不能继续假称原冻结版本。新配置从原配置派生，仅修改实验名称和runtime code指纹；模型/prompt指纹、原冻结题集/manifest、四文档语料及所有策略参数不变。新目录`output/m6-dev-readiness-r2-followup/`，未重备语料、未云解析或重新生成图片摘要、未运行首次创建脚本。

正式服务创建新实验，client_request_id含完整源实验ID；新eval_set/config登记为r2。逐题核对源attempts/results内容、completed持久Run、输入hash与conversation后，仅把19条completed日志迁入新实验目录和新配置检查点键。迁移清单保存原manifest/attempts/results哈希；020失败行排除、65题无检查点。迁移后独立66项只读审计通过，旧文件哈希未变，模型/人工/校准/观察写入0。020已在新配置下创建独立Run，旧新Run ID与实验ID另存绑定。

## 实际验证

adapter interrupted红测：配置缺失一次setup失败、测试库前缀错误一次验证失败均保留；修正运行命令后在明确后续键处失败，修复后通过。job首attempt键红测在`{None}`与预期来源键不同处失败，修复后通过。

最终定向命令（独立`m1_test_m4_followup_checks`前缀，每例随机后缀，不删库）：

```powershell
$env:M1_TEST_DB='m1_test_m4_followup_checks'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -c "from dotenv import load_dotenv; load_dotenv('.env'); import os; os.environ.update(LOG_CONSOLE_ENABLE='False',LOG_FILE_ENABLE='False'); import pytest; raise SystemExit(pytest.main(['tests/integration/test_evaluation_run_adapter.py','tests/integration/test_evaluation_jobs.py','tests/integration/test_run_commands.py','tests/unit/test_evaluation_query_adapter.py','tests/unit/test_evaluation_dataset.py','tests/unit/test_evaluation_catalog.py','-q','--junitxml=output/m6-dev-readiness-r2-followup/targeted-tests.xml']))"
```

实际81 passed，退出0；模型端口注入的隔离测试，不计真实模型评测。独立继承审计66项通过，退出0；两组覆盖不同且重叠，不累计唯一总数。本轮未重跑完整后端、前端、既有重导入或类型/build。

## 后续实验执行与待验收

新实验正式`execute_job`退出0，Mongo和磁盘均completed，attempt/result_attempt均1，85条题级结果全部completed、失败0、缺失0；行为辅助判定80 answer/5 clarify。它是19继承+66后续执行组合结果，不是85题同代码独立重生成。历史继承19次逻辑stream，本轮新增61次stream/0 invoke；组合汇总80次stream/0 invoke。SDK HTTP次数、费用及原失败窗口继续未知，不能把合并汇总当本轮80次新调用。耗时亦包含继承历史，不提供本轮独立全量性能结论。

正式完成已释放评测worker token/lease和owner slot。数据库保留86个Run：80 completed、旧020一个interrupted、5 awaiting_input；澄清Run有正常等待输入语义，不手工终止或清会话占用。原失败实验仍failed/attempt2、retryable=false、结果0。

独立持久核验1975项通过（85题集合、31审核/54草稿、Run/答案/引用绑定、公开持久结果与原日志一致、分组汇总独立重算、slot释放、完整语料与受保护账本不变）；检索/切片/图像核验9838项通过（4020候选出现记录、800文本引用、139图片引用、310唯一候选身份、238被引切片、36唯一图片字节hash及完整解码）。冻结目标语料SHA仍`81cd5d7583f6671a3ed66f85f4fa81e37cada0a79ae4d6d612533b4f81bb1481`。这些分组含重复/重叠检查，不累计唯一总数，也不是答案质量评分。

固定报告已从85条实际结果与冻结切片/图像只读导出，逐题标记继承或本轮执行；不含标准答案、heldout或评分入口。Edge离线9检查通过、139图像出现完整解码，关联图默认折叠，无HTTP/云读取；截图已核看。报告原件仅本机：[完整dev基线回答与切片对照](../../../output/m6-dev-readiness-r2-followup/完整dev基线回答与切片对照.html)。该报告是技术对照材料，语义相关性仍待独立审阅。

```powershell
.venv/Scripts/python.exe -c "import runpy; runpy.run_path('output/m6-dev-readiness-r1/prepare_followup_r2.py', run_name='__main__')"
.venv/Scripts/python.exe -c "import runpy; runpy.run_path('output/m6-dev-readiness-r1/migrate_followup_checkpoints_r2.py', run_name='__main__')"
.venv/Scripts/python.exe -c "import runpy; runpy.run_path('output/m6-dev-readiness-r1/run_followup_r2.py', run_name='__main__')"
.venv/Scripts/python.exe -c "import runpy; runpy.run_path('output/m6-dev-readiness-r2-followup/audit_inheritance.py')"
.venv/Scripts/python.exe -c "import runpy; runpy.run_path('output/m6-dev-readiness-r2-followup/verify_full_dev.py')"
.venv/Scripts/python.exe -c "import runpy; runpy.run_path('output/m6-dev-readiness-r2-followup/verify_retrieved_sources.py')"
.venv/Scripts/python.exe -c "import runpy; runpy.run_path('output/m6-dev-readiness-r2-followup/export_full_dev.py')"
node output/m6-dev-readiness-r2-followup/verify_fixed_report.cjs
```

上述准备/迁移/执行是一次性动作，后续不得重跑首次/派生创建或迁移脚本。原准备脚本首次直接执行因Python路径失败、迁移首次因错误import失败，都在写入前退出；已修正调用/import，实际成功退出0，旧工具失败记录保留。本轮服务未重启、卷未删除、语料未重导入。完整dev技术组合结果已完成，只代表执行与来源可核验，不代表阶段验收。

新规则独立人工双轮、预校准、候选比较和反馈后人工复评仍未完成。已有聊天判断不重复、不复制成双轮、不冒填human；来源召回或答案生成成功不等同质量达标。阶段材料完成后交总控审查，不自行标记M6通过，不进入M7。

实际结果、原始文件hash和本轮未执行范围见[脱敏验证摘要](M6-08-full-dev-baseline-validation-r3.json)；提交文件/链接/语法与本机密钥值扫描见[独立快照](M6-08-full-dev-baseline-manifest-r3.json)。原始配置、日志、答案/切片/图像固定报告及失败快照只留本机，不上传；`tmp/`未清理。后续不得以检查点复用当作反馈后新生成或独立人工复评。
