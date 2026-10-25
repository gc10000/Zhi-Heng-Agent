# M5 第二轮执行提交 · 技术支持流程与有限 Agent

状态：**待总控审查**。本轮仅修复总控首轮 R1—R3，M5 核心任务 7/7 自验完成；可选 M5-06 延期，M6 未授权。本材料不代表总控通过。

## 交付范围

| 任务 | 第二轮结果 | 关键行为 |
| --- | --- | --- |
| M5-02 | R1 已修复 | 清单 CAS 写入前递归重新授权整个既有聚合及新引用；撤权旧操作/工具原文返回 404，版本、历史和操作列表不变。 |
| M5-05 | R2、R3 已修复 | 已占用 preparing 窗口按自身旧快照补偿，未占用窗口仍受版本门禁并可超时释放；`clear_slots` 和前端“设为未知”撤回确认事实，旧 run/草稿快照不变。 |
| M5-08 | 第二轮验收材料 | 新增正式反例回归、阶段回归、独立摘要和 manifest；原真实产物只读复核，不重复付费生成。 |

已完成任务为 M5-01、M5-02、M5-03、M5-04、M5-05、M5-07、M5-08；未完成任务为可选 M5-06（未启用外部 MCP）。代码、测试与文档变更的提交前文件快照见 [M5 第二轮 manifest](M5-artifact-manifest-r2.json)，结果账本见 [M5 第二轮验证摘要](M5-validation-summary-r2.json)。

## R1：清单撤权

首轮反例 `output/m5-r2-r1-red.txt` 为 2 个业务失败、3 个正常通过。失败场景是已有资料 A 的操作或工具输出留在支持聚合中，随后仅绑定仍有权的资料 B；撤回 A 后，旧入口仍会把 A 的原文保存并返回。

修复位于 `app/support/api.py`：清单变更在任何保存前递归检查当前聚合的全部 document/revision 来源，再检查新 run 引用。任一旧来源撤权都在 CAS 前返回 404，拒绝不会递增 version、改写 operations 或写入历史；未撤权的旧操作、工具输出和新引用仍可正常生成清单。

`output/m5-r2-r1-green.txt`/XML 为 9 项通过、退出码 0；`tests/integration/test_support_checklist_authorization.py` 覆盖旧操作、旧工具输出、新 run 合法、撤权拒绝和零写入。无模型调用。

## R2：占用中断恢复

首轮反例 `output/m5-r2-r2-red.txt` 为 5 个失败：active_run 已 CAS 占用但 claim 标记和用户消息尚未写入时进程退出，支持上下文随后纠正；旧实现每次恢复先因版本冲突跳过 pending，过期许可持续阻塞新轮。

修复位于 `app/runs/repository.py`、`app/runs/commands.py`。恢复按 `active_run_id` 是否精确指向自身分流：已占用 run 使用不可变 `support_snapshot` 完成幂等 claim/消息补偿，不读取纠正后的新上下文；未占用 preparing 仍拒绝领取但继续执行 pending 超时扫描。过期清理、迟到 heartbeat/finally 和最终发布都以自身 run_id/fencing 条件保护，不能删除或覆盖后续新 run。

`output/m5-r2-r2-green-final2.txt`/XML 为 21 项通过、退出码 0；`output/m5-r2-targeted-final.xml` 的合并定向回归为 49 项通过。中间 `green.xml` 中一次测试断言修正原件保留，未把测试脚本错误当业务通过。无模型调用。

## R3：确认槽位撤回

首轮后端红测 `output/m5-r2-r3-red-v2.txt` 为 2 个失败，浏览器红测 `output/m5-r2-r3-browser-red.txt` 保留清空已确认值后旧事实复现。原页面把空字符串过滤为 `values={}`，后端也拒绝空槽位，导致“留空表示未知”实际静默保留旧事实。

修复位于 `app/support/models.py`、`app/support/workflow.py`、`app/support/api.py`、`app/support/repository.py` 和 `frontend/src/features/cases/components/SupportContext.vue`。输入契约新增显式 `clear_slots`；撤回写入历史、时间和操作者，当前槽位变为 `unknown`/未确认并递增支持和上下文版本，未来 run 不继承旧事实。旧 run 与已确认草稿保留原快照，必需槽位撤回后重新进入澄清。页面提供“设为未知”按钮，空输入不会伪装成撤回。

修正一次将 `recorded_at` 纳入精确字典断言的测试后，`output/m5-r2-r3-green-final2.txt`/XML 为后端 15 项通过、退出码 0；前端离线浏览器 4 项通过。该修正原件及中间失败均保留，无模型调用。

## 阶段验证

- 后端阶段：`output/m5-r2-stage-backend/commands.json`，789 passed、2 deselected、0 skipped、7 warnings，退出码 0；JUnit 统计为 497 单元、128 契约、164 集成目录。集成测试使用隔离存储和注入服务，不能解释为供应商调用数。
- 既有重导入：3 项通过，退出码 0。
- 前端阶段：`output/m5-r2-stage-frontend/commands.json`，37 单元、28 离线浏览器，typecheck/build 均退出码 0；浏览器 0 skipped、0 unexpected、0 flaky。
- 合并定向：`output/m5-r2-targeted-final.xml`，49 passed，退出码 0。
- 历史真实产物：`output/m5-08-prior-live-readonly.json` 只读 8 项，`output/m5-08-live-recheck-final.json` 只读 16 项，均沿用首轮已通过结果；本轮新增付费调用 0，未重跑 heldout 或调参。

所有失败红测、中间测试断言修正和阶段首次前缀配置错误均保留，未删除、改写或覆盖首轮证据。单元/fake、隔离 Mongo/Milvus/MinIO 集成、离线浏览器和真实产物只读复核在摘要中分别列出；未宣称生产全库恢复、设备实际操作、整体答案质量或历史 Windows 原生模型问题已根治。

## 配置、兼容与数据边界

本轮无新增开发依赖、模型/CUDA升级、必填应用配置或公开 API 路由删除；OpenAPI、前端类型、[公共契约](../../plans/DEVELOPMENT_CONTRACTS.md)和[恢复手册](../../runbooks/support-recovery.md)已同步。测试使用已有 `.venv/Scripts/python.exe`、隔离测试库和本机 Docker 服务；不清理课程资料、原知识集合、对象桶、缓存、Mongo 账本、`output/`、`evidence/` 或 `evals/`，这些原始内容不上传。

回滚可分别撤回清单递归授权门禁、占用恢复分流和 `clear_slots`/页面接线，保留历史支持快照、旧消息和数据库现场；具体步骤见 [M5-08 记录](../records/M5-08.md) 与 [support-recovery runbook](../../runbooks/support-recovery.md)。

## Git 交接与后续

本轮基线为 `f1cd675df936d88eb8b14b72857a0f06d4b6acb7`，分支 `main`；manifest 记录提交前 HEAD 与基线相同。暂存时排除 `.env`、模型、课程原件、运行数据、原始 `evidence/`、`output/` 和 `evals/`；最终提交 SHA、推送结果及远程核头在交接回复补记，不强推。

下一步由总控独立复审本材料和新 manifest。**等待总控审查 M5；不进入 M6。**
