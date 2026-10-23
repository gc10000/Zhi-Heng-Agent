# M2：统一 API、持久运行与长任务开发 ToDo

> 执行方式：按任务逐项开发；使用 superpowers:executing-plans 技能。任务中的步骤采用勾选框跟踪；不自行派发子代理。

**目标：**交付“统一 API、持久运行与长任务”阶段可独立验收的能力。
**架构：**沿现有 Python/FastAPI/LangGraph 链路做小步适配；Vue 3 前端只消费统一 API 与事件契约。保留旧入口与数据直至本阶段验收通过。
**技术栈：**Vue 3 / TypeScript / FastAPI / MongoDB / Milvus / MinIO；具体测试工具与依赖在对应任务中建立。
**设计依据：**[优化方案](../2026-10-22-technical-support-optimization.md)、[接口与数据契约](../DEVELOPMENT_CONTRACTS.md)、[开发总清单](../DEVELOPMENT_TODO.md)。

## 进入条件与执行约束

M0/M1均已通过总控审查；2026-10-23授权M2-01至M2-12按依赖连续执行，当前逐项实现。阶段末提交M2-submission.md，等待总控审查后再进入M3；范围见[M1第二轮总控结论](../../development/reviews/M1-review-r2.md)。

- 以下文件均为**计划创建/修改**，不表示已经存在；执行前用 `rg` 核对真实接口与源码。
- 本阶段遵守总清单中的 Vue 3、中文注释、数据隔离、配置脱敏和完成证据规则。
- 每个代码任务先增加能揭示错误的用例，再做最小实现；文档、样式等低影响变更按实际结果检查，不写镜像测试。
- 每完成一个任务，记录验证命令、输出摘要、涉及文件和遗留问题；验证通过后才勾选[总清单](../DEVELOPMENT_TODO.md)，并更新[进度](../../development/PROGRESS.md)与[变更记录](../../development/CHANGELOG.md)。
- 命令均从项目根目录运行；`pnpm -C frontend` 命令需 M3-01 建立对应 scripts 后才存在。依赖安装和测试数据准备不表示任务验收通过。
- 每个任务验证其直接影响的行为，阶段验收时再执行阶段回归；不要重复运行无关全量测试。

<a id="m2-01"></a>
### M2-01：API 与生命周期入口

**依赖：**M0-09。
**文件：**`app/main.py`; `app/settings.py`; `app/api/errors.py`; `tests/contract/test_app_lifecycle.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M2-01.1** 统一 /api/v1 与错误信封。
- [x] **M2-01.2** 配置加载与资源初始化进入 lifespan。
- [x] **M2-01.3** 旧入口保留兼容适配并明确弃用边界。
- [x] **M2-01.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_app_lifecycle.py -q。
- [x] **M2-01.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**import app.main 不连数据库、不加载模型、不更改桶策略；缺配置在启动检查说明变量名。

<a id="m2-02"></a>
### M2-02：登录、会话与角色

**依赖：**M2-01。
**文件：**`app/identity/models.py`; `app/identity/service.py`; `app/identity/api.py`; `tests/contract/test_auth.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M2-02.1** 单组织 viewer/maintainer/admin。
- [x] **M2-02.2** 密码哈希、可撤销登录会话、HttpOnly cookie。
- [x] **M2-02.3** 写请求 CSRF/Origin 校验与登录限流。
- [x] **M2-02.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_auth.py -q。
- [x] **M2-02.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**登录/退出/过期均可测；普通用户不能发布资料或执行管理动作；接口不回传密码散列。

<a id="m2-03"></a>
### M2-03：会话、消息与逐轮主体

**依赖：**M2-02,M1-01。
**文件：**`app/conversations/models.py`; `app/conversations/repository.py`; `app/conversations/api.py`; `tests/contract/test_conversation_ownership.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M2-03.1** 拆 conversation/message ID。
- [x] **M2-03.2** 按 owner 和 kb 授权，历史游标分页。
- [x] **M2-03.3** 设备选择保存逐轮 snapshot，不回写旧消息。
- [x] **M2-03.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_conversation_ownership.py -q。
- [x] **M2-03.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**用户 B 无法读 A 的目录/历史；同时间历史分页无遗漏；切换设备后旧消息主体不改变。

<a id="m2-04"></a>
### M2-04：运行幂等与会话占用

**依赖：**M2-03。
**文件：**`app/runs/models.py`; `app/runs/repository.py`; `app/runs/service.py`; `tests/integration/test_run_claim.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M2-04.1** run_id/message_id/client_request_id 分离。
- [x] **M2-04.2** 条件领取 conversation.active_run_id，唯一幂等键。
- [x] **M2-04.3** 独立状态机处理跨文档补偿。
- [x] **M2-04.V** 验证：.venv/Scripts/python.exe -m pytest tests/integration/test_run_claim.py -m integration -q。
- [x] **M2-04.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**同请求重发返回同 run；同会话新请求返回 409；跨会话隔离；领取后崩溃可核对，不依赖 replica set 事务。

<a id="m2-05"></a>
### M2-05：持久事件与 SSE 重放

**依赖：**M2-04。
**文件：**`app/runs/events.py`; `app/runs/api.py`; `tests/contract/test_sse_replay.py`; `tests/integration/test_event_outbox.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M2-05.1** 持久 run_id/seq/type/at/payload，增量批量写。
- [x] **M2-05.2** 事件游标、心跳、24h TTL 和快照恢复。
- [x] **M2-05.3** 终态与待发事件在 run 文档条件更新后投递。
- [x] **M2-05.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_sse_replay.py tests/integration/test_event_outbox.py -q。
- [x] **M2-05.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**同 run seq 严格递增且允许间隙；断流重连不重复；游标过期返回 410 恢复信号；数据库写失败不伪造成功。

<a id="m2-06"></a>
### M2-06：型号确认、取消与中断恢复

**依赖：**M2-05。
**文件：**`app/runs/state_machine.py`; `app/runs/commands.py`; `app/conversations/context.py`; `tests/contract/test_run_transitions.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M2-06.1** awaiting_input 持久化候选与恢复点。
- [ ] **M2-06.2** 确认校验候选/owner/run version。
- [ ] **M2-06.3** 取消置 cancel_requested，阶段边界检查。
- [ ] **M2-06.4** 租约失效标记 interrupted。
- [ ] **M2-06.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_run_transitions.py -q。
- [ ] **M2-06.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**刷新后可继续确认；迟到确认不能复活已结束运行；取消后不 completed；completed/failed/cancelled/interrupted 互斥。

<a id="m2-07"></a>
### M2-07：知识目录、上传与任务 API

**依赖：**M2-02,M1-11。
**文件：**`app/knowledge/api.py`; `app/knowledge/upload.py`; `tests/contract/test_document_upload.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M2-07.1** 产品/资料分页、上传与 revision 查询。
- [ ] **M2-07.2** 随机对象键，原文件名只展示。
- [ ] **M2-07.3** 限制大小/MIME/扩展名并拒绝路径穿越。
- [ ] **M2-07.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_document_upload.py -q。
- [ ] **M2-07.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**同名上传不覆盖；不支持格式明确 4xx；用户无权发布；接口返回 job_id 与 revision_id。

<a id="m2-08"></a>
### M2-08：受控原件与引用访问

**依赖：**M2-02,M2-07。
**文件：**`app/knowledge/asset_api.py`; `app/knowledge/citation_api.py`; `app/clients/minio_utils.py`; `tests/contract/test_asset_access.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M2-08.1** 按 kb/revision 授权图片/PDF/引用。
- [ ] **M2-08.2** PDF Range/206/416。
- [ ] **M2-08.3** 先映射旧图片并验证，再单独管理桶策略。
- [ ] **M2-08.4** 限制外部图片来源。
- [ ] **M2-08.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_asset_access.py -q。
- [ ] **M2-08.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**越权引用/原件均被拒绝；旧图映射可回看；服务 import 不改桶策略；只在测试桶验证收紧访问。

<a id="m2-09"></a>
### M2-09：Redis/Celery 派发与租约

**依赖：**M2-07。
**文件：**`app/infrastructure/queue/celery_app.py`; `app/ingestion/jobs.py`; `app/ingestion/dispatcher.py`; `compose.yaml`; `tests/integration/test_job_leases.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M2-09.1** Mongo job 账本 dispatch_pending，Linux worker 至少一次投递。
- [ ] **M2-09.2** 条件领取/续约/重试与 attempt fencing；将供应商速率预算接入 Redis 原子协调，避免多个 worker 各自限流却合计超额。
- [ ] **M2-09.3** 对象键传递，禁止 Windows 绝对路径。
- [ ] **M2-09.V** 验证：.venv/Scripts/python.exe -m pytest tests/integration/test_job_leases.py -m integration -q。
- [ ] **M2-09.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**重复投递不重复发布；停止 worker 后可恢复；旧 attempt 无法覆盖新 attempt；容器能访问模型宿主。

<a id="m2-10"></a>
### M2-10：导入阶段恢复与供应商错误分类

**依赖：**M2-09,M1-07。
**文件：**`app/ingestion/runner.py`; `app/ingestion/checkpoints.py`; `tests/integration/test_import_resume.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M2-10.1** 将解析/图像/嵌入阶段接入持久任务。
- [ ] **M2-10.2** 复用 batch_id/hash/完成批次。
- [ ] **M2-10.3** 区分 429/超时可重试与格式/鉴权不可盲重试。
- [ ] **M2-10.V** 验证：.venv/Scripts/python.exe -m pytest tests/integration/test_import_resume.py -m integration -q。
- [ ] **M2-10.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**worker 中断后仅补失败段；不会重新消耗成功图像额度；阶段状态与真实产物一致。

<a id="m2-11"></a>
### M2-11：旧问答图适配新运行

**依赖：**M2-06,M2-08。
**文件：**`app/runs/query_runner.py`; `app/query_process/agent/main_graph.py`; `tests/contract/test_query_run_adapter.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M2-11.1** 用适配器把旧图事件转为新 run 协议。
- [ ] **M2-11.2** 剥离按 session 的全局 SSE 队列依赖。
- [ ] **M2-11.3** 引用和答案统一到消息快照。
- [ ] **M2-11.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_query_run_adapter.py -q。
- [ ] **M2-11.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**新 API 能真实问答；旧 API 基线仍可比；不同会话图并发不串流；外部错误有阶段与终态。

<a id="m2-12"></a>
### M2-12：M2 阶段验收

**依赖：**M2-10,M2-11。
**文件：**`docs/development/records/M2-12.md`; `docs/architecture/api-v1.md`; `docs/runbooks/worker-recovery.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M2-12.1** 导出 OpenAPI/事件样例。
- [ ] **M2-12.2** 执行幂等/并发/取消/重放/越权/恢复矩阵。
- [ ] **M2-12.3** 记录 cookie 与 SSE 代理设置。
- [ ] **M2-12.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract tests/integration -m 'not live_provider' -q。
- [ ] **M2-12.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**真实新 API 可覆盖登录→导入→问答→澄清→引用；故障矩阵通过；前端可据固定契约开发。

