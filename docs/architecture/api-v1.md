# 统一API v1 · M2交付

日期：2026-10-24。实际实现见[OpenAPI](openapi-v1.json)、[事件示例](run-events-example.json)和[公共契约](../plans/DEVELOPMENT_CONTRACTS.md)。OpenAPI从create_app().openapi()离线导出，24个路径/27个操作；事件文件为明确标注的合成协议示例，不是执行证据。M3已授权实施，未进入M4。

M3-08兼容补充：引用返回可空`original`，包含精确修订已登记原件的asset_id/media_type/name/url；与引用同权限复核，不公开对象键或签名URL，旧未登记原件返回null。PDF前端按物理页与已知normalized_top_left坐标定位，无bbox只跳页。

统一入口为`app.main:app`，前缀`/api/v1`。导入模块不连服务或加载模型；lifespan建立资源，后台领取持久问答并恢复超时运行。旧查询/导入服务独立保留，不能把旧无鉴权入口暴露为新API。新运行查询仅用显式组织owner、当前kb、产品和冻结活动修订的v2索引；旧整图课程检索不挂到此入口。

浏览器先POST /auth/login（username/password及允许的Origin），服务端设置support_session Cookie并返回user/csrf_token；GET /me恢复身份。Cookie默认HttpOnly、Secure、SameSite=Strict、Path=/api/v1；仅本机HTTP调试显式API_COOKIE_SECURE=false。所有写请求带Origin和X-CSRF-Token，POST /auth/logout撤销会话。viewer只读，maintainer/admin可维护资料；具体个人run/会话同时按owner和当前kb校验。未登录401、功能权限403、具体资源越权404、版本或幂等冲突409。

POST /conversations创建会话（kb_id，product_ids可空），PATCH按expected_version。消息GET /conversations/{cid}/messages用cursor/limit分页，按ordinal正序，允许间隙。POST /conversations/{cid}/runs传question/client_request_id/kb_id/product_ids，202返回持久快照；同键同内容同run，不同内容409，同会话一次只能占用一个非终态运行。用户消息保存创建时选择，后续确认不会改旧消息。

GET /runs/{rid}公开`state`、`seq`、`version`、`answer`、`citations`及可选`stage/error/candidates/resume_point`；answer运行中为部分文本，不能据非空判成功。pending/running/awaiting_input/cancel_requested为非终态；completed/failed/cancelled/interrupted互斥。无产品且多个候选时等待确认；POST /confirm-product按expected_version和候选product_ids，恢复pending后再领取，最多50候选，更多需先从目录选。POST /cancel仅记录意图，执行边界确认停止；失联不能假称已取消。浏览器断流不取消。

GET /runs/{rid}/events为SSE，Cookie同源认证；Last-Event-ID及after_seq取较大者，id=seq，event=type，data为完整run_id/seq/type/at/payload。seq严格递增但允许间隙；心跳为15秒注释，不分配seq。每个事件24小时，游标失效410先读快照；不能依赖TTL即时删除。浏览器按run_id/seq去重，切会话关闭旧订阅，退出清理流与身份缓存。型号等待不结束订阅。终态送完退出，断流重连不重新创建run。

实际事件为run.started、stage.changed、product.candidates、product.confirmed、citation.selected、answer.delta及四种run终态。citation.selected保存预算实际入选证据，包含稳定citation_id、chunk_uid、document_id/revision_id、原文、source_refs、asset_ids。run.completed含answer/citations/message_id；run.failed含脱敏error.code/stage，部分文本保留在快照，无成功assistant消息。完成CAS与completion_snapshot同时保存，消息写入中断可恢复幂等补偿；异常会话归属记内部recovery_issue后跳过，不接管异常数据或阻断其他运行。

GET /runs/{rid}/citations/{citation_id}仅回本轮入选快照并重新授权修订/资产，返回display_text和受控asset_urls。GET /assets/{aid}验hash，PDF支持单段Range及200/206/416；不向前端传存储签名URL。生成答案的分段图片仅允许本轮入选资产路径，外部图片/HTML不交给浏览器直接解释。前端仍须禁用Markdown原始HTML并使用安全渲染器。

资料目录GET /products、/documents及资料修订；维护者POST /products绑定kb。POST /documents为multipart file/kb_id/client_request_id/product_ids(JSON数组)，可带document_id建立新修订，202返回document_id/revision_id/job_id/original_asset_id；上传成功不等于索引发布。GET /import-jobs/{jid}读真实stage/attempt/retryable/error，retry需维护者及expected_version。发布/回滚/撤回复用验证与活动指针CAS，历史产物保留。

生产代理必须透传Cookie、Origin、X-CSRF-Token、Last-Event-ID，保持浏览器同源；不得对鉴权API做公共缓存。SSE配置`proxy_buffering off`、`proxy_cache off`，读取超时大于心跳周期（建议75秒），禁止压缩聚合；服务端已发送Cache-Control: no-cache,no-transform及X-Accel-Buffering:no。HTTPS终结后仍使用Secure Cookie。若代理改写来源/路径，须单独复核显式允许Origin与Cookie Path，不信任任意X-Forwarded-For。M2没有部署服务器或实施生产代理变更。

本次真实链路以新API独立进程、隔离Linux worker、真实BGE/重排/LLM完成登录→上传/发布→澄清确认→回答→引用；51.593秒，回答调用1次，11检查通过。默认回归排除2项付费测试，模型注入集成与真实供应商区分见[阶段提交](../development/reviews/M2-submission.md)。无前端/生产灾备/全库迁移验收结论。

导入错误补充：upstream_timeout表示供应商超时，upstream_connection_failed表示连接失败，均可重试；429/5xx可重试，401/403及格式/配置错误不可自动重试。重试仍需维护者权限与expected_version。

完成消息顺序：终态快照保存后先持久assistant再释放会话；新轮创建会补偿旧终态，写入失败保留原占用并允许相同请求重试。历史按首次ordinal顺序，跨轮消息与下一轮生成上下文均保持上一轮答案在下一轮问题之前。终态事件可先保存，不能仅据它假定会话占用已释放。
