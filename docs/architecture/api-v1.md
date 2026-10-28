# 统一API v1 · M2底座与M5支持扩展

## M6图片判定R1/R2兼容补充（2026-10-27）

无新增路由或字段，沿用image_selection_version=1。列表/转义反引号中的实际图片按同源Markdown解析记入answer_asset_ids及image_usage=answer，终态、历史与评测一致。正文存在受控图时，配图N/A写入返回422；即使旧context误标也复核正文，历史N/A导致新校准409/质量pending，旧账本不修改。无新版标记的聊天引用图默认折叠且提示关系未知，展开后才读取。新增两个纯Python包，安装要求见[配置说明](../CONFIGURATION.md)；OpenAPI结构未变，未重新生成无差异类型。

日期：2026-10-27。实际实现见[OpenAPI](openapi-v1.json)、[事件示例](run-events-example.json)和[公共契约](../plans/DEVELOPMENT_CONTRACTS.md)。OpenAPI从create_app().openapi()离线导出，当前50个路径/60个操作（M2交付时24个路径/27个操作）；事件文件为明确标注的合成协议示例，不是执行证据。M0至M5已通过，M6仍实施，M7未授权。

M3-08兼容补充：引用返回可空`original`，包含精确修订已登记原件的asset_id/media_type/name/url；与引用同权限复核，不公开对象键或签名URL，旧未登记原件返回null。PDF前端按物理页与已知normalized_top_left坐标定位，无bbox只跳页。

M4-09兼容补充：run.failed及运行快照error可增`retryable`布尔。供应商超时/连接失败/429/5xx分别为upstream_timeout/upstream_connection_failed/provider_rate_limited/provider_unavailable；鉴权、错误模型、请求及格式错误分别为provider_authentication_failed/provider_model_not_found/provider_invalid_request/provider_invalid_response，不统一标可重试。部分答案保留但仍failed，无成功助手消息；客户端不能据retryable直接复活终态。未改变路由或鉴权/版本门禁，错误不回显上游正文。timeout/retry/JSON策略显式开启，默认保留既有SDK参数，见[配置](../CONFIGURATION.md)。

M6-04审阅补充：POST `/experiments/{eid}/reviews/{review_id}/followups`仅由原人工审核者追加其原轮次全部unknown维度；每项必须填写结论与原件依据。追加记录与原review分开不可变保存，具结果SHA/原review内容指纹及Mongo唯一键；当前内容不一致拒绝写入。用户先前已保存的真实001两个unknown轮次需要逐轮对照原件追加复核；此机制/隔离回归通过本身不修改它们、不建立校准或代表阶段验收。

M6-04配图补充：GET `/experiments/{eid}/results/{question_id}/images/{document_sha256}/{page}/{asset_sha256}`仅返回已完成实验当前结果attempt引用的精确图片字节；验证实验owner、知识库、题目、引用三元组后，再限定实验知识库中的原件SHA及资产物理页并重新授权资料修订，读取时验证图片字节SHA。响应`Cache-Control: private, no-store`、ETag为图片SHA、`X-Content-Type-Options: nosniff`；不暴露对象键、签名URL或新的资产ID。未登录401、无维护权限403；结果或来源/权限不匹配404、字节损坏502。已有结果与审阅指纹不变，无数据迁移；图片失败在UI明确显示，不能代替人工判分。

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

M4-02内部run新增query_plan/retrieval_trace用于受控评测和追踪，不在GET /runs公开快照中增加字段；citation.selected仍只包含实际入选引用。候选去重和重排身份校验不改变现有终态、版本、租约及权限协议。

M4-03不改变RunInput；product_snapshot可额外返回context_route（answer/compare/general/series），general清空后续隐式设备继承。原请求选择和query_plan为内部持久元数据；近型号与选择/指代冲突沿现有product.candidates和版本确认接口处理，候选相似度不当已确认事实。旧消息及其快照保持原字节语义。

M4-07保持公开API字段与事件协议不变。问题/固定提示超窗以prompt_budget_exceeded失败；来源或图片跨修订为citation_scope_invalid，流式未知引用为answer_citation_invalid，均不写成功助手消息。合法输出达到模型上限则保存部分内容并统一追加中文说明，answer.delta拼接、历史和run.completed.answer保持一致。预算/支持程度仅内部持久化用于评测；引用编号与citation.selected顺序一致。旧兼容API共享预算和输出限制，尚无同等流式编号门禁保证。

M4-08不改变公开问答API。退出仍先撤销会话，再清该用户查询向量缓存并递增代际；迟到计算不能污染下一代。内部模型桥接POST /embeddings新增可选input_type（query/document，默认document），新查询客户端需要同步新版宿主；现有document worker请求保持原形。此桥接沿原令牌保护，不对外部署。


## M5 支持流程与用户确认

| 端点 | 输入与行为 |
| --- | --- |
| GET/POST `/conversations/{cid}/support` | 持久支持聚合；expected_version、values、confirmed、action和可选已完成run_id。槽位候选不当事实；更正只影响未来run |
| POST `/conversations/{cid}/support/checklist` | expected_version/run_id；从实际引用整段生成未试清单，保留前提和风险，重复来源不使无效步骤复活 |
| POST `/conversations/{cid}/support/operations/{oid}` | expected_version/status/note；用户自报追加服务器时间，全部无效转交 |
| POST `/conversations/{cid}/support/tools` | expected_version/tool/arguments；仅3种固定只读工具及后端范围，预算先预留，失败/重复/超限转交 |
| GET/POST `/cases` | owner/kb分页和完成run生成draft；expected_support_version门禁，同run幂等且不覆盖编辑 |
| GET/PATCH `/cases/{id}` | 草稿字段编辑采用expected_version；历史引用与支持快照不回写 |
| POST `/cases/{id}/confirm` | 用户确认服务端版本；确认后冻结，重复确认幂等 |
| GET `/cases/{id}/export` | 仅confirmed，重新授权全部嵌套精确修订；返回filename/markdown/case_version，浏览器本地下载 |
| POST `/feedback` | run/citation_ids/category/note/client_request_id；五类pending_review，幂等冲突409，不发布知识 |

支持聚合state独立于问答run.state，不借用执行租约伪造人工等待。刷新读取支持快照，不改SSE序号；原型号确认/取消/消息补偿仍沿M2/M3协议。新run冻结support_snapshot，旧run迟到引用更新须核对context_version；已取消/已解决不复活。support/case读取包含嵌套历史和工具输出的资料重新授权，撤权404不返回内容。可选外网MCP不注册，详见[支持恢复手册](../runbooks/support-recovery.md)。
# M6评测接口补充

评测API均要求登录和maintainer/admin，具体资源再次按owner/current kb核验；写操作沿用同源与CSRF。`GET /eval-catalog?kb_id=`只给维护者受控登记选项；`GET/POST /eval-sets`读取/登记私有题集版本；`GET/POST /experiments`列表/创建；`GET /experiments/{id}`读取真实状态；`GET /experiments/{id}/results?cursor=&limit=`按题身份分页，最大100；`POST /experiments/{id}/cancel`与`/retry`带`expected_version`，重试返回202。基线ID只接受同所有者/知识范围/冻结题集的已完成实验。未知成本/标准语义分保持null。

创建仅接受题集/配置ID版本、可选基线、可选continuation和client_request_id，拒绝路径、伪造结果等额外字段。continuation严格包含source_experiment_id/source_attempt/source_version/reason，服务端核对同owner/kb、终态、当前代际及相同dataset/manifest/config指纹；未知来源404、状态或身份不符409、字段不合法422。响应continuation追加父state/retryable/error和配置/请求hash快照。相同请求重发保持身份，相同请求ID内容变化409；continuation省略/null等价。取消在题边界合作完成，不中断已发出的供应商请求。题级对比仅表示文本/状态差异，不能当质量提升。登记后冻结指纹漂移或目录错误明确拒绝；错误不回显路径/配置正文。OpenAPI及前端声明已同步，详见[评测工作台](../evaluation/workbench.md)。

## M6聊天来源、适用性与图片使用关系（2026-10-27）

GET/POST `/experiments/{eid}/observations`：维护者、owner/kb、同源/CSRF；仅completed当前题结果可写。请求`question_id/subject_sha256/source_message_id/statement/scores/rubric_version/actionability_applicable/applicability_rationale`，拒绝`round/reviewer_id/human_attested`等额外字段。同来源同内容幂等、冲突409、校准仍要求独立human。`ReviewInput.observation_id`可引用同账号当前结果来源，不能自动继承评分。新版审阅`question-purpose-v1`要求逐题步骤适用性及理由并与分值一致，省略版本兼容legacy-v1；新校准绑定版本，跨版本pending。

新run引用增加`image_selection_version=1/answer_asset_ids`；原asset_ids保留全部检索关联，生成前事件为空答案图，终态/完成快照/历史一致。评测结果增加image_selection_version和图像citation.image_usage=answer/context，完整进入题级指纹。旧结果不迁移，前端标为历史关系未知并折叠图像来源；旧配图门禁保守保留。详见[审阅与恢复协议](../evaluation/release-gates.md)。OpenAPI和生成类型已同步，无新增环境变量或依赖。
