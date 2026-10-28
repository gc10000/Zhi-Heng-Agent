# M6-08 continuation R1/R2补修与定向自验

日期：2026-10-28。起点 `715f63992f12bd3a3dd3e5873f86710d926f02c0`，开始时 HEAD 与 origin/main 一致，仅未跟踪 tmp；tmp 保留。本轮落实[只读审查](M6-08-continuation-protocol-review-r1.md)的 R1/P1、R2/P2，执行自验完成，待原规划总控独立定向复审；不自行关闭审查项。M6 仍 4/7，M6-04/05/08 未验收，M7 未授权。

## R1：恢复结果保留持久Run累计调用

问题窗口为 Run 已完成、题级结果尚未落盘。原 adapter 重建后以当前进程新增调用差值 0 生成结果，覆盖已经持久化的 stream 1，实验汇总随之漏计。

M6 的 `logical_provider_calls` 现在来自 Run 的持久 telemetry，并声明 `logical_provider_calls_scope=run_total`；`execution_logical_provider_calls` 单列本次 adapter 调用的进程计数差值。新调用可为累计 1 / 本次 1，复用及该崩溃窗口恢复为累计 1 / 本次 0。题级结果白名单保留这两个字段与范围，汇总继续只读取 Run 累计，恢复读取和已有结果日志复用不会再相加本次差值。前端结果类型与契约同步，不改变请求 schema。

持久调用计数缺失或无效时累计为 null，不能以新进程 0 补零。新澄清分支在进入 awaiting_input 的同一次事件 CAS 中保存已观测 telemetry，测得的调用 0 可重复读取为 0；旧缺测仍为 null。M4 原调用差值行为保持。精确 HTTP 次数、费用和旧失败窗口仍未知；逻辑调用次数不转换成付费金额，也不承诺中断窗口的 exactly-once。

## R2：派生前验证父实验的题级来源

原实现仅验证父实验终态及冻结身份，未验证声明的父 experiment/attempt 是否实际关联所选中断 Run。正式 M6 job 现在向 adapter 传入当前 experiment/attempt、worker token 与注册配置 hash；adapter 在执行 QueryRunner 之前检查当前 owner/kb、有效租约及 worker 身份，通过 setOnInsert 持久 `evaluation_execution_links`。worker token 只用于当次验证，不保存进关联文档。

关联固定 experiment/attempt/question、输入 hash、canonical config hash、注册配置字节 hash、checkpoint、Run 与 conversation；同键不同身份拒绝覆盖。pending Run 标为 `execution`，表示已准备执行，不能据此认定已调用或已付费；对已有 running/completed/awaiting_input 的实际观察复用标为 `observed_reuse`，不能冒充其最初生成归属。直接注入而无正式任务身份的 adapter 不创建已认证来源。

为 interrupted 检查点准备新请求时，必须重新核验父终态、attempt/version、owner/kb，并找到同父 experiment/attempt/question 的关联，逐项匹配输入、配置、checkpoint 与源 Run。合法关联的 id/hash 进入不可变 continuation 身份。重复执行始终核验原 source Run 的关联；原固定 request key 和创建后崩溃幂等路径保留。completed 无需派生时正常复用，非 retryable 失败继续拒绝，再次中断不自动派生第三条 Run。

历史缺少该题关联、错误父实验/attempt 或冻结输入不符，均在新 Run/模型之前明确拒绝。未增加历史证明导入入口，未为 r3 或旧020回填关联；如未来确需历史证明，须另行留证审核。仍仅支持相同冻结 config，不认证源码变化后的旧配置真实执行兼容性。

## 实际证据与范围

原始文件仅留在本机 `output/m6-continuation-fix-20261028/`，不上传。脱敏[验证摘要](M6-08-continuation-protocol-fix-validation-r2.json)绑定日志、JUnit、核验脚本与证据 hash。不同组有覆盖，不累计唯一总数。

| 验证 | 实际结果 |
| --- | --- |
| 未改动的原审查探针，修复前复现 | 2失败、1通过，pytest退出1 |
| 新增回归最初红测 | 5失败、1通过，退出1 |
| 首次实现验证 | 32通过、1失败，退出1；失败为测试调用 run_experiment 时未提供冻结 execution_mode，修复测试夹具后纳入最终组 |
| R1/R2及既有adapter/job/Run/题集/目录/宿主/指标 | 107通过、0失败/错误/跳过，退出0；pytest列出2条SWIG弃用警告，进程末另有swigvarlink弃用提示 |
| 原审查探针兼容副本 | 3通过、退出0；属于执行自验，不是独立总控复审 |
| 共享查询、清除产品槽、Run遥测 | 20通过、退出0 |
| 前端 vue-tsc | npm run typecheck退出0 |
| 当前OpenAPI/变更Python语法 | 见验证摘要；无OpenAPI结构变化 |
| r3已存结果及历史证据只读核验 | 520检查通过、45份历史证据hash未变；真实目标所有现存集合名称和前后摘要不变 |

新增正式回归覆盖完成后落盘前退出、重建 executor、结果日志/汇总不漏计或重计、正常复用累计/本次分列、缺测 null 与澄清实测零；错误父实验/attempt/输入/缺失历史关联在创建新 Run 前拒绝。正式 EvaluationService → execute_job → adapter 组合测试验证模型前已有父关联、合法子链路可执行、旧父实验未改，以及其他任务实际复用 completed 时只登记 observed_reuse。

原审查脚本与探针未改。兼容副本仅把合法来源夹具升级为正式 adapter 预先建立关联，正常复用的旧“差值0”断言调整为“累计1、本次0”，并取消测试中已准备的合法子任务以释放隔离预算、匹配题集描述。R1“恢复结果必须等于持久累计”和 R2“未执行该题的正式父实验须在新Run/调用前拒绝”的核心断言保留；本机 `recheck-adaptations.json` 记录修改范围。只读审计副本仅更换输出目录。

主要定向命令如下；每个集成用例使用指定前缀下的随机测试库，资源和模型为合成注入，不访问供应商：

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:M1_TEST_DB='m1_test_m4_continuation_fix_targeted_20261028'
.venv/Scripts/python.exe -m pytest tests/integration/test_evaluation_continuation_regressions.py tests/integration/test_evaluation_run_adapter.py tests/integration/test_evaluation_jobs.py tests/integration/test_run_commands.py tests/unit/test_evaluation_query_adapter.py tests/unit/test_evaluation_dataset.py tests/unit/test_evaluation_catalog.py tests/unit/test_evaluation_host.py tests/unit/test_eval_metrics.py -q --junitxml=output/m6-continuation-fix-20261028/targeted.xml
$env:M1_TEST_DB='m1_test_m4_continuation_fix_query_20261028'
.venv/Scripts/python.exe -m pytest tests/integration/test_query_runs.py tests/integration/test_support_clear_slots.py tests/integration/test_run_telemetry.py -q --junitxml=output/m6-continuation-fix-20261028/query-telemetry.xml
# frontend目录
npm run typecheck
```

r3 仍是实验 `79b3cc58-cfd4-4da5-84c0-890d92a9be06` 的85条组合结果：19继承 + 66执行，历史stream19 / r3新增stream61、invoke0分列。旧 `a5607e05-de22-4b24-9570-e85b7e09b521` failed/attempt2、retryable=false、0 evaluation_results 与费用未知保留。原 manifest/attempts/results 与恢复前备份 hash 一致；未发现已存 r3 受本次 R1 计数缺陷影响。本轮没有重新运行历史1975持久检查、9838检索/图片检查或浏览器全链路，不把历史结果认证为当前源码下的独立85题新生成或答案质量证明。

本轮没有供应商模型调用、真实dev/heldout执行、human/observation/校准写入、语料重导入、服务重启、旧检查点迁移或手工修改 state/lease/slot/retryable。隔离故障测试中的合成状态仅在随机测试库内构造。按AGENTS顺序自审，未派发子代理；已同步API文档、workbench、开发契约、ADR-071、进度与M6接续清单。

下一步交原规划总控独立定向复审R1/R2及其与已存r3的边界，再按原授权接续M6人工/预校准/候选/反馈复评。现有已保存判断不重复索取，不重跑首次创建或迁移脚本，不进入M7。
