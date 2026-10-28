# M6-08 R2控制账本与Run目标分库补修自验

日期：2026-10-28。起点 `34a98da5838526851bcb81da2a8310f8a27317e5`，开始时 HEAD/origin/main 一致，仅 tmp 未跟踪，保留不清理。落实[独立复审](M6-08-continuation-protocol-review-r2.md)的 R2 剩余 P1 分库接线问题；R1 原缺陷已有独立定向通过结论，本轮保留。R2 补修自验完成，待原规划总控独立复审，不自行标记关闭。M6 仍 4/7，04/05/08 未验收，M7 未授权。

## 根因与接线

正式工作台的实验/attempt/worker/lease 在 `M2_DB_NAME` 控制账本，Run/知识/checkpoint 在冻结 `config.target.database`。原 job 只传身份字段，adapter 用目标库查询控制实验，同库测试掩盖了分库失败；有效首题被拒绝，模型0、目标遗留pending Run1。未改业务源码先直接重跑原分库探针，得到同库1通过/分库1失败，原失败窗口重现。

现在正式 job 将现有 `repo.db` 显式赋给 adapter 的 `control_db`，该能力仅在进程内传递，不写配置/队列/来源。当前 experiment/attempt/worker/config、owner/kb 及未过期 lease 均到控制账本核验；校验前置到 conversation/checkpoint/Run 写入之前，绑定来源前再次校验。缺少控制能力时明确拒绝，不能隐式使用 target 的同名实验记录。没有复制实验记录、改冻结 target、关闭租约检查或新增控制库环境配置。

Run/checkpoint、`evaluation_execution_links` 和 continuation 仍存目标库。新 link 固定 `control_database`、`target_database` 与原题级身份；读取父来源时，父实验在可信控制库核验终态/attempt/version，父 link 在目标库按同题输入、配置、checkpoint、Run 和两个库映射核验。父 link 的 id/hash 继续固定进 continuation；worker token 和连接不进入持久来源。历史缺映射或缺关联拒绝，不回填、不自动认证 r3。

completed 观察复用仍只记 `observed_reuse`，不冒充最初生成归属或新增计费；首个 pending 准备执行记 `execution`，不证明已付费。R1 的 Run 累计/本次新增计数分列、缺测 null 及精确 HTTP/费用未知契约保持，无 API schema 或前端类型变化。

## 跨库窗口与幂等边界

控制校验、目标Run创建和关联持久化之间没有跨库事务。身份已失效时在目标副作用前拒绝；若恰在校验后、Run创建后失效，关联前的重验会拒绝模型调用，但可能留下 pending Run。新增测试通过注入恢复时钟，验证正式 `RunCommands.recover()` 将其收敛为 interrupted、写入事件并释放会话占用，不手改 state/lease/slot，不删Run。该测试只作用于随机测试库；不执行真实目标恢复。

合法子任务在新Run创建后、关联前退出，或关联后、模型前退出，重建 job 由正式 claim 获取新 attempt，continuation 的原固定请求取得同一 pending Run，再建立当前 attempt 关联后执行。三种分库链路（正常、创建后退出、关联后退出）均完成，最终只保留父/子两个Run、两次合成生成；重复投递 completed job 不增加Run或调用。旧父实验全文保留，不追认来源、不递归派生第三条。

## 实际验证

| 组 | 本轮结果 |
| --- | --- |
| 原同库/分库探针，补修前直接复现 | 1通过、1失败，退出1 |
| 新分库回归最初红测 | 9失败，退出1；覆盖新映射、分库路径及校验前置契约 |
| 首轮实现（上述9项） | 9通过，退出0 |
| 最终定向：既有107项及新增14项 | 121通过，0失败/错误/跳过，退出0；2条SWIG弃用warning及末尾swigvarlink提示 |
| 原同库/分库探针原件 + 旧兼容探针新副本 | 5通过，退出0；拓扑两项均completed、合成调用各1、completed Run各1/link各1，分库target实验0 |
| 共享查询/清槽/遥测 | 20通过，退出0 |
| 前端typecheck | 退出0 |
| OpenAPI、变更Python语法 | 见[验证摘要](M6-08-continuation-protocol-fix-validation-r3.json)，当前工厂与导出一致 |
| r3已存结果只读 | 520检查通过，45历史证据hash不变，真实目标所有现存集合名称/前后摘要不变 |

组间有覆盖，不累计唯一总数。14项新增回归覆盖同库/分库首题及completed复用、分库正常continuation及两个进程退出窗口、缺控制能力/错误worker/过期lease/错误当前attempt在副作用前拒绝、错误父实验/当前父attempt无题级link/控制或目标库映射不符在新Run前拒绝，以及Run创建后失效的正式pending恢复。直接adapter既有测试仅显式设置其同库控制能力，旧断言保持。原分库探针与原审查文件均未改；旧兼容探针副本只增加显式 `control_db` 设置，断言不改；只读审计副本仅更换输出目录。兼容副本通过仍是执行自验，不代替独立复审。

主要命令：

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:M1_TEST_DB='m1_test_m4_sf_all'
.venv/Scripts/python.exe -m pytest tests/integration/test_evaluation_split_ledger.py tests/integration/test_evaluation_continuation_regressions.py tests/integration/test_evaluation_run_adapter.py tests/integration/test_evaluation_jobs.py tests/integration/test_run_commands.py tests/unit/test_evaluation_query_adapter.py tests/unit/test_evaluation_dataset.py tests/unit/test_evaluation_catalog.py tests/unit/test_evaluation_host.py tests/unit/test_eval_metrics.py -q --junitxml=output/m6-split-fix-20261028/targeted.xml
$env:M1_TEST_DB='m1_test_m4_sf_probe'
.venv/Scripts/python.exe -m pytest output/m6-continuation-rereview-20261028/test_independent_boundaries.py output/m6-split-fix-20261028/test_original_probes_compatible.py -q -s --junitxml=output/m6-split-fix-20261028/review-green.xml
$env:M1_TEST_DB='m1_test_m4_sf_shared'
.venv/Scripts/python.exe -m pytest tests/integration/test_query_runs.py tests/integration/test_support_clear_slots.py tests/integration/test_run_telemetry.py -q --junitxml=output/m6-split-fix-20261028/shared.xml
.venv/Scripts/python.exe -m output.m6-split-fix-20261028.audit_saved_results
# frontend目录
npm run typecheck
```

随机测试库保留不删除；合成状态故障和超时只在这些库构造，不写真实课程或历史评测。脱敏验证摘要记录本轮日志/JUnit/核验脚本、原探针与历史证据hash；原始文件仅保存在本机 `output/m6-split-fix-20261028/`，不上传。没有把测试模型计数当供应商调用或费用。

## 历史与接续

本轮未调用供应商模型，未执行真实dev/heldout、human/observation/校准、重导入、服务重启、历史迁移或真实Run恢复。原实验仍failed/attempt2、retryable=false、provider_invalid_response、持久结果0；未知HTTP/费用不补零。r3仍85条组合结果，19继承+66执行，历史stream19与r3新增61/invoke0分列，80 completed/旧020 interrupted1/awaiting_input5，历史manifest/attempts/results及备份一致。r3无新关联回填，真实目标集合摘要不变；未重跑历史1975/9838/浏览器全链路，不认证旧配置在当前源码的真实执行兼容性或答案质量。

已同步公共契约、API文档、workbench、ADR-072、进度/清单与本轮记录。按AGENTS顺序开发自审，无子代理。下一步正常提交推送并核对完整SHA，交原规划总控独立定向复审R2分库接线与来源拒绝/幂等边界。复审后再按原门槛接续M6独立人工/预校准/候选/反馈复评；不重复索取已保存判断，不重跑首次创建/派生迁移脚本，不进入M7。
