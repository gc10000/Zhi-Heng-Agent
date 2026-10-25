# M5 第五轮修复提交

日期：2026-10-25。范围仅为总控第四轮重开的 M5-05、M5-08 / R3；M5-06 可选 MCP 延期，M6 未授权。基线为本地 `7e60d51d498b2a8215894de5485ed5a2aaa5f337`，远程当时仍为 `3a75c324627101393c2e8c4b1697b87fa793a983`。修复与材料提交为 `a98e12df2082d22e0e99537730fe87fe35aeb083`，已正常推送 `origin/main`，远程核头一致。

## 任务状态

- M5-01、M5-02、M5-03、M5-04、M5-07：此前完成，R1保持关闭。
- M5-05：R2保持关闭；R3本轮完成执行自验，当前设备事实优先于旧撤回历史。
- M5-08：第五轮阶段回归和材料完成，待总控独立审查。
- M5-06：可选官方网页 MCP 延期，未启用外部服务或真实凭据。

## R3 问题与修复

总控第四轮正式复现：AX-24 完成旧问答后通过 `clear_slots=['device']` 撤回，用户使用正式 `SupportRepository` 重新确认 AX-48；新的支持快照已有非空 `device.value`、`confirmed=true`、`subject_withdrawn=false`，但 `subject_withdrawn()` 扫描完整 history 的任意撤回记录，导致下一轮无显式 `product_ids` 仍返回 `clarify/model_required_after_context_reset`。缺少 `subject_withdrawn` 的旧 r2 格式同样复现。

修复前先增加正式隔离入口红测：新格式重新确认、旧格式重新确认、再次撤回、未确认候选四组边界及既有对照。红测输出 `output/m5-r5-r3-red.txt`，退出码 1，2 个重新确认用例失败、7 项对照通过；该文件未覆盖前三轮或第四轮失败证据。

最小修复在 `app/support/commands.py::subject_withdrawn()`：当前设备槽位非空且 `confirmed=true` 时立即返回 `False`，表示最新确认已经成为现行主体；当前明确未知且带 `withdrawn_by`、`subject_withdrawn=true` 或旧格式明确撤回历史时仍返回 `True`。不删除 history，不改旧消息、run、草稿、ordinal，不改变再次撤回或未确认候选的阻断语义。

新增回归位于 `tests/integration/test_support_query_context.py`，通过真实隔离 Mongo、`SupportRepository`、`RunService` 和 `QueryRunner.execute()` 验证：

1. 新格式撤回后重新确认 AX-48，无显式型号的“它的电源呢”使用 AX-48 完成问答。
2. 删除 `subject_withdrawn` 的旧 r2 快照仍以当前 AX-48 为主体。
3. 再次撤回 AX-48 后下一轮仍要求型号澄清。
4. 仅提交 `confirmed=false` 的 AX-48 候选不能解除主体撤回边界。

## 验证结果

精确定向命令：

```powershell
$env:M1_TEST_DB='m1_test_m5_r5_targeted'
.venv/Scripts/python.exe -m pytest tests/unit/test_query_plans.py tests/unit/test_support_workflow.py tests/contract/test_support_resume.py tests/integration/test_support_claim_recovery.py tests/integration/test_support_context_runs.py tests/integration/test_support_clear_slots.py tests/integration/test_support_query_context.py tests/integration/test_run_claim.py tests/integration/test_run_commands.py -q --tb=short
```

退出码 0，**84 passed**，证据由本轮终端输出及阶段 JUnit 保留。

阶段回归实际结果：

| 类型 | 命令/证据 | 实际结果 |
| --- | --- | --- |
| 业务红测 | `output/m5-r5-r3-red.txt` | 2 failed、7 passed，退出码 1；修复前证据 |
| 后端 | `output/m5-r5-stage-backend/commands.json`、`backend.xml` | **802 tests，0 failures，0 errors，0 skipped**；另排除2项 `live_provider`，退出码0 |
| 既有重导入 | `output/m5-r5-stage-backend/reimport.txt` | **3 passed**，退出码0 |
| 前端 | `output/m5-r5-stage-frontend/commands.json`、`unit.json`、`browser.json` | typecheck/build退出0；Vitest **37 passed**；离线 Playwright **28 passed、0 skipped/0 unexpected/0 flaky** |
| 历史真实产物 | `output/m5-r4-live-readonly.json` | 历史 **16 项只读通过**，本轮不覆盖 |

本轮尝试重新运行 `recheck_m5_live.py` 生成新只读报告时，历史临时 API `127.0.0.1:58277` 已停止，连接被拒绝、退出码1；未写入新报告、未改变账本、未调用供应商。该环境失败与业务红测分开记录，历史16项仍仅作为原真实产物证据，不宣称本轮真实HTTP复验。

## Mock、真实集成与未验证项

- 定向/阶段后端使用随机 `m1_test_m4_m5_stage_*` Mongo 及现有注入模型/检索夹具；这是正式隔离集成，不是供应商端到端。
- 前端浏览器是离线 mock API 回归；typecheck、单元和构建均真实运行。
- 本轮新增付费调用 0；不重复生成答案、不运行 dev/heldout 调参。
- 既有真实供应商产物仅只读复核范围沿用第四轮16项；本轮HTTP端口未恢复。
- 未验证生产规模灾备、整体答案正确率、精确 SDK HTTP/费用、MCP真实凭据、历史 Windows 原生模型加载问题根治。

## 数据、配置、兼容与回滚

未安装依赖、未升级模型/CUDA、未修改 `.env`，未删除或重建课程集合、MinIO桶、缓存、原始 evidence、output 或 `evals/`。新增代码只改变撤回主体判断优先级，不改变公开 API 字段；历史快照和旧 r2 记录继续兼容。回滚可撤回 `subject_withdrawn()` 当前有效事实优先分支和新增四个回归，不清理已保存 history、run 或草稿。

## 阶段交接

M5-05、M5-08 已达到执行自验条件，清单已勾选，`REVIEW_STATUS.md` 保持 M5“待审查”。本材料不代表总控通过；请独立复核 R3 四条边界、完整回归动态数量和环境失败区分。下一步为等待总控审查 M5，不进入 M6。
