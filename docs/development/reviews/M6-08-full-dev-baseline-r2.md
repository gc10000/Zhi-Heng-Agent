# M6-08 完整 dev 接续：基础服务恢复与租约收敛

日期：2026-10-27。关联实验 `a5607e05-de22-4b24-9570-e85b7e09b521`，此前中断报告见[第一轮报告](M6-08-full-dev-baseline-r1.md)。本次只处理服务恢复后的状态核对和正式 Run 恢复，不运行完整 dev 或 heldout。

## 恢复后核账

Docker Engine 29.5.2 可响应；六个容器均运行，其中 Mongo、Milvus、MinIO、Redis、etcd 报告健康，Attu处于运行状态。Mongo独立 `ping` 返回成功。没有删除卷、重建容器、重导入资料或重启现有服务。

首次只读查询发现评测实验仍是 `running/attempt 1`，评测租约已过期，owner slot 仍占用。题目020对应的持久 Run 也是 `running`，执行租约过期，会话仍由该 Run 占用。19个完成题目的Run和020的检查点均存在。尝试捕获数据库快照时，后台状态发生变化：实验变为 `failed/attempt 2`、`retryable=false`、错误 `provider_invalid_response`，slot变为空；没有评测结果行。状态变化发生在本执行端未调用任务恢复或生成入口的核查期间，具体触发进程及 attempt 2 的供应商调用次数/费用无法确定。未将未知错误改成可重试。

评测结果目录的原 `manifest.json`、`attempts.jsonl`、`results.jsonl` 已复制到本机 `output/m6-dev-readiness-r2/pre-recovery/`，三个SHA256逐一与原件一致。原目录文件未改动。

## 正式 Run 收敛

只读核实目标隔离库中唯一非终态 Run 属于题目020且执行租约过期后，调用应用的 `RunCommands.recover()`。它将该 Run 转为 `interrupted`，追加持久 `run.interrupted` 事件并释放对应 conversation 的 `active_run_id`。评测实验仍为 `failed/attempt 2`、不可自动重试，owner slot 为空；没有手工删除 state、lease、token 或 slot 字段。Run 文档保留过期 execution lease/token，但状态已为终态，且活动 Run 数为0。

最终只读检查确认：85题中20个持久运行检查点为19个completed、020一个interrupted；其他65题无检查点。该评测实验的 `evaluation_results` 仍为0行，attempt 2 的完整结果和调用清单不可从持久结果恢复。原本地19题成功记录仍在，备份哈希一致；此前观测到的19次逻辑 `stream_started` 保持历史事实，不能将 attempt 2 的调用或费用写成0。

## 结论与接续限制

基础设施已恢复，过期 Run 已按正式协议收敛；完整 dev **仍未完成**。实验 attempt 2 当前 `failed` 且 `retryable=false`，失败原因及调用窗口不支持自动安全重试。为保留幂等、旧失败和费用账目，本轮没有重启新 attempt，也没有重跑19题或剩余题目。后续若要补足020，须先明确一个具有来源关联的新尝试协议，不得直接篡改可重试标记或覆盖旧Run。任何后续任务仍复用原冻结题集、配置和19个已完成 Run 检查点。

本轮模型调用、真实评分、聊天观察、校准写入均为0；heldout未运行；未重跑pytest、前端全量或重导入。M6-04/05/08继续未验收，核心4/7、总核心64/76，M7未授权。用户已有聊天判断不需重复提交。

只读核验和备份哈希见[验证摘要](M6-08-full-dev-baseline-validation-r2.json)，原始本机状态文件保留于 `output/m6-dev-readiness-r2/`，不上传。
