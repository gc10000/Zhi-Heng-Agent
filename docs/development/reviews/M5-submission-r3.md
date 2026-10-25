# M5 第三轮修复提交

日期：2026-10-25。状态：**执行自验完成，待总控审查**。本轮仅处理 M5-05/M5-08 的 R2、R3，不进入 M6。基线为总控第二轮提交 `8b0ad61`；原始 `output/`、`evidence/`、`evals/` 和数据库/对象现场保留本机，不上传。

## 1. 任务状态

- 已完成：M5-01、M5-02、M5-03、M5-04、M5-05、M5-07、M5-08（第三轮执行自验）。
- 可选延期：M5-06，未启用外部网页 MCP，也未使用真实凭据联调。
- 未授权：M6及服务器部署、公开 Release。

## 2. R2 修复

归档会话保留 `active_run_id` 时，领取 CAS 必然因 `archived=False` 失败；旧实现又因自身指针相等而递归 `reconcile()`，最终抛出 `RecursionError` 并中断恢复扫描。

修复后，`RunRepository.reconcile()`先识别归档会话，按 `run_id + version + 非终态` CAS 写入 `state=interrupted`、`claim_state=rejected` 和 `error.code=conversation_archived`，之后 `release()` 只匹配仍指向该 run 的活动指针。CAS 失败的自身占用窗口直接有界补齐 claimed/用户消息，不再自递归。`RunCommands.recover()`对归档活动账本使用同一幂等终态并继续扫描其他会话。

正式覆盖：占用 CAS 后 preparing 归档、已 claimed/pending 归档、重复恢复、跨会话恢复、迟到旧 run 不能清理新 run 占用，以及既有未归档版本门禁和 fencing。

## 3. R3 修复

设备撤回后，旧实现只返回“无支持设备约束”，正式 `QueryRunner`仍可能消费旧助手快照、旧会话选择或唯一目录项，直接以 AX-24 回答。

修复后，支持聚合增加 `subject_withdrawn`：`clear_slots=['device']`设置并记录历史，显式确认新设备时清除；`freeze_support()`传播该边界。`QueryRunner`将撤回边界传给 `plan_query(context_reset=True)`，无本轮显式型号时清空本轮隐式选择并返回 `model_required_after_context_reset` 澄清；显式 AX-48 等新型号仍按目录精确路径回答。旧消息、旧 run、确认草稿和 ordinal 均不改写。

正式覆盖：有旧助手确认、有旧会话产品选择、目录仅一个型号、无 `product_ids` 的撤回后问答，以及随后明确新型号的正常执行；另有单元状态边界和实际产品计划入口测试。

## 4. 修改文件

源码：`app/runs/repository.py`、`app/runs/commands.py`、`app/runs/query_runner.py`、`app/retrieval/query_planner.py`、`app/support/commands.py`、`app/support/workflow.py`。

测试：`tests/integration/test_support_claim_recovery.py`、`tests/integration/test_support_query_context.py`、`tests/unit/test_query_plans.py`、`tests/unit/test_support_workflow.py`。

文档：M5-05/M5-08记录、恢复手册、公共契约、决策记录、CHANGELOG、PROGRESS、REVIEW_STATUS、DEVELOPMENT_TODO及M5第三轮摘要/manifest。

## 5. 验证证据

修复前正式反例：`output/m5-r3-r2-r3-red.txt`，3 failed，退出码1；未清理现场。未设置独立库的组合命令另存 `output/m5-r3-targeted-config-error.txt`，43 passed/34 errors，退出码1，属于测试配置错误，不计业务红测。

定向绿测：`output/m5-r3-targeted-green.txt`，77 passed，退出码0；补充 R2/R3 入口回归10 passed，退出码0。R2/R3均使用真实隔离 Mongo、合成资料和注入模型，未调用付费供应商。

阶段后端：`output/m5-r3-stage-backend/commands.json`，pytest **795 passed、2 deselected、0 skipped、7 warnings**，退出码0；JUnit 实际目录组成以 `backend.xml` 为准。既有重导入 **3 passed**，退出码0。

阶段前端：`output/m5-r3-stage-frontend/commands.json`，typecheck/unit/build/browser均退出0；Vitest **37 passed**，Playwright 离线浏览器 **28 passed、0 skipped、0 unexpected、0 flaky**。

## 6. 验证分类与边界

- 真实隔离集成：R2/R3 Mongo 状态、CAS、恢复扫描和 QueryRunner 入口；模型为注入实现，不代表供应商质量。
- 离线单元/契约：查询计划、支持状态及现有前端协议。
- 真实供应商：本轮0次付费调用；M5既有真实小样和M3产物仅沿用只读报告，不重复生成答案。
- 未验证：生产规模恢复、长期容量、整体答案正确率、精确SDK费用/HTTP调用计数、可选MCP及历史Windows原生模型问题根治。

## 7. 兼容、数据范围与回滚

不新增依赖、配置或模型，不删除/重建课程资料、知识集合、对象桶或原始证据。新增字段对旧支持聚合按缺省 `false` 兼容；查询计划新增可选 `context_reset` 参数。回滚只需撤回归档终态分流、`subject_withdrawn`传播和 `context_reset`消费者，保留历史、旧 run、草稿和撤回记录，不清理测试账本。

## 8. 后续门禁

本材料提交给总控独立复审。M5状态保持“待审查”，不自行标记通过；在总控复审前不进入 M6。
