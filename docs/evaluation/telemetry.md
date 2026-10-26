# 运行质量统计

`GET /runs/{run_id}/telemetry` 返回单次运行的持久统计；`GET /run-telemetry?kb_id=...` 返回当前账号和知识库范围的分页统计。接口先经过登录、知识库和 run owner 授权，不能用猜测的 run ID 读取他人数据。

安全投影包括状态、创建/终态时间、总耗时、阶段耗时、失败阶段/安全错误码、模型名（通过白名单格式）、修订计数、HyDE/分解等可选分支的 timeout/busy/failed 降级，以及逻辑 provider invoke/stream 次数。阶段和终态在 `EventLedger` 同一版本 CAS 更新中写入 `telemetry.schema_version=1`、累计 stage_seconds 和 terminal_at；因此事件回放 TTL 或 outbox 清理不会抹掉已持久的耗时。

模型客户端通过 `ObservedClient` 只计 invoke/stream 启动次数和响应 usage 的 input/output token。流式 usage 只使用最后可用的总量；缺失、异常或请求失败返回 null，明确的 0 保留为 0。未采集费用、精确HTTP调用、供应商端队列耗时不猜成 0。模型响应、prompt、引用正文、异常正文、签名 URL、API key 和完整日志永不写入 telemetry。

`RunsPage.vue` 仅显示当前维护者范围的运行统计和“未采集”，不把样本统计冒充全量性能或质量提升。评测结果仍按 M6 manifest 保存题级 stage_timings/token_usage；运行耗时不能替代答案人工正确率。回滚只移除页面/API/观测投影，不删除已有 run/event/结果。
