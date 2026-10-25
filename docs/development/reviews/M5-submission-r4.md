# M5 第四轮修复提交

日期：2026-10-25。当前分支 `main`；本轮起点为上一轮提交 `b273f6a66446f9d173cfa6be973a5a18b4e7ead0`，修复提交为 `b8a0aba`（本轮文档补记提交随后产生）。范围仅为 M5-05、M5-08 的 R2/R3，M5-06 延期，M6 未授权。

## 任务状态

- M5-01、02、03、04、07：此前自验完成并保留。
- M5-05：第四轮 R2/R3 修复自验完成，待总控审查。
- M5-08：阶段回归和材料完成，待总控审查。
- M5-06：可选官方 MCP 延期，未启用外部服务或真实凭据。

## R2：归档终态事件

修复前 `RunRepository._interrupt_archived()` 直接写 `interrupted`，造成 `seq=0`、outbox/公开事件为空。正式入口红测通过真实 `RunCommands.start()` 复现。修复后仓储归档出口复用注入的 `EventLedger`，以 `run_id + version + expected_state` CAS 同时保存终态、错误、序号和 outbox；事件由同一账本幂等 flush。并发冲突只在核验 `run.interrupted` 已存在后收敛；释放继续严格匹配自身 `active_run_id`。

红测：`$env:M1_TEST_DB='m1_test_m5_r4_red_actual'; .venv/Scripts/python.exe -m pytest tests/integration/test_support_claim_recovery.py::test_archived_worker_start_persists_replayable_terminal_event -q --tb=short`，修复前退出 1、`seq == 0` 失败；完整红测证据为 `output/m5-r4-r2-r3-red.txt`。绿测断言状态为 `interrupted`、`seq=1`、唯一 `run.interrupted`、重建恢复不重复，包含在 `output/m5-r4-r2-r3-green.xml` 的 70 项中。

## R3：撤回兼容与新选择

旧 r2 支持快照没有 `subject_withdrawn`，但合法撤回保留空设备槽位、`withdrawn_by` 和 `history.withdrawal`。`freeze_support()` 现在保留 history，`subject_withdrawn()`按这些明确事实兼容识别；普通从未填写设备不触发。撤回主体运行清空旧助手历史，当前显式 `product_ids` 仍传给计划器走 `explicit_selection`，未显式选择返回 `model_required_after_context_reset` 澄清。旧消息、run、草稿和 ordinal 不改写。

红测覆盖旧格式升级和选择器入口，修复前两项失败，完整红测为 3 failed/退出 1；修复后包含旧格式澄清、显式新选择完成、未撤回冲突对照的 70 passed 定向回归。

## 验证结果

| 类型 | 命令/证据 | 实际结果 |
| --- | --- | --- |
| 业务红测 | `output/m5-r4-r2-r3-red.txt` | 3 failed，退出 1；修复前反例保留 |
| 定向绿测 | `output/m5-r4-r2-r3-green.xml` | 70 passed，退出 0 |
| 后端阶段 | `output/m5-r4-stage-backend/commands.json`、`backend.xml` | 798 passed、2 deselected、0 skipped、7 warnings，退出 0 |
| 既有重导入 | `output/m5-r4-stage-backend/reimport.txt` | 3 passed，退出 0 |
| 前端 | `output/m5-r4-stage-frontend/commands.json` | 类型检查、构建退出 0；Vitest 37 passed；离线浏览器 28 passed、0 skipped/unexpected/flaky |
| 真实隔离产物 | `output/m5-r4-live-readonly.json` | 16 项只读检查通过；复核供应商调用 0 |
| Python语法 | `.venv/Scripts/python.exe -m compileall -q app tests` | 退出 0 |

阶段回归收集以 JUnit 为准：798 执行、2 排除；不沿用第三轮 795。首次未设置 `M1_TEST_DB` 的命令 3 errors、退出 1，脚本配置错误不计业务红测；真实只读脚本首次连接拒绝和旧字段适配错误另存于本机 output，不改写原证据。

## 数据、配置与付费边界

仅使用随机 `m1_test_` 测试库、合成/隔离资料和注入模型；Docker 存储服务保持原状。未删除或重建课程集合、对象桶、缓存、原始 evidence、output 或 `evals/`，未安装依赖、升级模型或修改 `.env`。本轮新增付费调用 0；不宣称生产规模灾备、整体答案正确率、MCP真实联调或历史 Windows 模型加载问题根治。

## 回滚与审查状态

回滚可撤回 `RunRepository` 归档事件接线、撤回兼容识别和 QueryRunner 主体边界，保留已写入历史/事件及旧运行，不清理账本。`REVIEW_STATUS.md` 已标记 M5“待审查”，M5-05/08自验勾选；本提交不代表总控通过。下一步等待总控审查 M5，不进入 M6。
