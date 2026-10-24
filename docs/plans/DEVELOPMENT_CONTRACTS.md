# 开发公共契约与任务交接边界

日期：2026-10-24。状态：M0/M1/M2/M3总控通过；M4获准按依赖执行，M5及以后未授权。关联：[开发总清单](DEVELOPMENT_TODO.md)、[原始优化方案](2026-10-22-technical-support-optimization.md)。

## 1. 稳定接口和文件归属

以下约定让阶段间能对齐，而不是提前生成所有业务代码。实现发现不适配时，先更新此文档、影响任务与决策记录，再改消费者；不能只改函数名让后续计划失效。

| 接口/对象 | 建立任务与文件 | 最小输入输出与不变量 | 主要消费者 |
| --- | --- | --- | --- |
| 历史窗口 | M0-03，`app/clients/mongo_history_utils.py` | 保留 `get_recent_messages(session_id: str, limit: int=10) -> list[dict]`；取最近 N 条后正序返回 | 旧图、M2/M4 会话适配 |
| 字符预算 | M0-04，`app/answering/context_budget.py` | `pack_prompt_inputs(docs, history, max_chars=12000)` 返回 context/history/used_chars/used_chunk_ids；不访问 IO | 输出节点；M4 扩展 token 预算 |
| 生成失败 | M0-07，`app/answering/errors.py` | `AnswerGenerationError` 包含 `partial_answer: str`；异常必须传播到外层任务终态 | 旧 API、M2 query_runner |
| 型号匹配 | M0-05，原 `step_5_align_item_names` | 保留 confirmed_item_names/options 字典；非精确的多个高分返回候选 | 原图；M4 规范产品解析器 |
| `SourceRef` | M1-01，`app/knowledge/models.py` | document_id/revision_id、kind、page/section_path/sheet/cell/bbox 可空；明确原件与描述来源 | 解析、切片、引用、PDF、评测标签 |
| `ParsedDocument` | M1-03，`app/ingestion/models.py` | pages/blocks/tables/images、原件 hash、parser/version、质量标记、source_refs | 切片/图像/索引 |
| 知识仓储 | M1-02，`app/knowledge/repository.py` | `register_document`、`create_revision`、`get_active_revisions`；显式接收 kb/owner 范围 | 上传、索引、发布、检索 |
| 发布服务 | M1-09，`app/knowledge/publishing.py` | `RevisionPublisher.validate(revision_id, attempt=...)`、`publish(revision_id, expected_active=...)`、`reconcile(document_id)`；范围由注入repo固定 | 后续维护者API、迁移 |
| 同步领域导入 | M1-11，`app/ingestion/service.py` | `IngestionService.import_file(path, request_id=..., expected_active=...)`；原件/切片/资产按修订回看 | 本机领域调用、M2后续适配 |
| 任务导入阶段 | M2-10，`app/ingestion/runner.py` | `run_import(job_id)`从Mongo领取attempt/token，按对象键和检查点执行；过期attempt不可发布 | Linux Celery worker |
| 问答运行 | M2-04/11，`app/runs/service.py`、`query_runner.py` | 创建、领取、恢复/中断、终态与幂等；旧图经适配器接入 | API、Vue SSE、观测 |
| SSE 消费 | M3-05，`useRunStream.ts` | 输入 run_id 与最后 seq，消费事件/快照，关闭订阅；取消单独调用后端 | ChatPage、Pinia run store |
| 检索候选 | M4-02，`app/retrieval/models.py` | `RetrievalHit`、`QueryPlan`、`EvidencePack`；保留范围、修订、分数来源与实际入选证据 | 检索各节点、引用、评测 |
| 评测最小入口 | M4-01，`app/evaluation/validate_dataset.py`、`runner.py` | 校验 JSONL，按固定配置运行基线；输出可复核逐题结果 | M4 消融；M6 扩展指标/工作台 |

函数参数与 Pydantic 类型在该任务实施时于单独规格中冻结；任务文件里未出现的内部方法不能被后续任务假定存在。对外 API/事件字段使用下述名称，变更需记录兼容方式。

## 2. ID、归属与版本

M1-01已冻结Pydantic实体契约，具体字段及UUID/SourceRef规则见[知识schema](../architecture/knowledge-schema.md)。空活动指针/未知定位允许null；非空ID严格字符串，禁止以整数暗中转换。业务ID独立随机UUID；修订内结构ID由stable_id(kind, revision_id, parts)的规范JSON UUID5确定。

- 所有对外 ID 使用字符串；Mongo ObjectId/Milvus 64 位 ID 不直接作为 JavaScript number。
- document_id 表示业务资料，revision_id 表示不可变修订，chunk_uid 表示稳定切片，asset_id 表示原件/图像。文件名与 hash 不替代业务 ID。
- 每个 run 保存用户、kb、产品与知识修订快照；授权既检查 owner，也检查当前知识访问范围。历史引用的精确修订不能被新版悄悄替换。
- Mongo standalone 不依赖多文档事务。跨集合一致性采用单文档条件更新、幂等键、派发账本和核对补偿；并发/崩溃窗口必须有测试。
- active_revision_id 条件发布与检索过滤使用同一份活动修订清单；指针切换不保证已经开始的查询立刻换版本，已开始 run 按自己的修订快照回答。

## 3. API 约定

统一前缀 `/api/v1`。以下为最小契约；M2-12 输出真实 OpenAPI 后前端生成类型。列表统一返回 `items`、`next_cursor`；错误返回 `error.code`、`error.message`、`error.details`、`request_id`。details 不含密钥或私有完整文档。

| 接口 | 请求要点 | 响应/约束 | 建立任务 |
| --- | --- | --- | --- |
| `POST /auth/login` | username/password；Origin 校验与限流 | 登录 cookie，用户/角色/CSRF 令牌；不返回密码散列 | M2-02 |
| `POST /auth/logout`、`GET /me` | cookie，写请求 CSRF | 撤销登录；当前身份与允许范围 | M2-02 |
| `GET/POST /conversations` | title/kb_id/product_ids | 目录/新会话，owner 由服务端设置 | M2-03 |
| `PATCH /conversations/{id}` | title/archived，乐观版本 | 更新自身会话，禁止改 owner | M2-03 |
| `GET /conversations/{id}/messages` | cursor/limit | 正序历史分页；逐轮产品/引用快照 | M2-03 |
| `POST /conversations/{id}/runs` | client_request_id、question、product_ids、kb_id | 202持久快照；同幂等请求返回同 run；同键不同内容 409 | M2-04 |
| `GET /runs/{id}` | 已登录身份 | state、seq、answer（运行中为部分文本）、citations、candidates、resume_point | M2-05 |
| `GET /runs/{id}/events` | `Last-Event-ID` 或 `after_seq` | text/event-stream；游标失效 410，再读快照 | M2-05 |
| `POST /runs/{id}/confirm-product` | product_ids、expected_version | 只允许从持久候选中选，owner 与版本必须匹配 | M2-06 |
| `POST /runs/{id}/cancel` | expected_version，可重复请求 | 记录取消意图；终态不复活 | M2-06 |
| `GET /products`、`GET /products/{id}/documents` | 搜索/分页 | 返回授权目录和活动修订信息 | M2-07 |
| `POST /documents` | multipart 原件、kb_id、product_ids、client_request_id | 202 + document_id/revision_id/job_id；名称仅展示 | M2-07 |
| `GET /documents`、`GET /documents/{id}/revisions` | 过滤/分页 | 状态与解析质量，不将已上传视为已发布 | M2-07 |
| `GET /documents/{id}/revisions/{rid}/chunks` | cursor/limit | 维护者切片、来源和图片预览 | M2-07 |
| `POST /documents/{id}/revisions/{rid}/publish` | expected_active_revision_id | validated 修订才可发布；维护者权限与 CAS | M2-07/M1-09 |
| `POST /documents/{id}/rollback` | target_revision_id、expected_active_revision_id | 目标需是可用已验证版本；不删除当前修订 | M2-07/M1-09 |
| `POST /documents/{id}/withdraw` | expected_active_revision_id | 撤回活动指针；历史引用按授权仍可回看 | M2-07 |
| `GET /import-jobs/{id}`、`POST /import-jobs/{id}/retry` | job 与权限 | 阶段、attempt、错误码、是否可重试 | M2-07/09/10 |
| `GET /runs/{id}/citations/{cid}` | owner/kb 校验 | 原文、来源、定位、asset_ids、修订与解析质量 | M2-08 |
| `GET /assets/{id}` | 授权、Range | 图像/原件；PDF 支持 200/206/416 | M2-08 |
| `GET/POST /cases`、`PATCH /cases/{id}` | run_id、用户编辑、expected_version | draft→用户确认后 confirmed；只修改授权记录 | M5-03 |
| `POST /cases/{id}/confirm`、`GET /cases/{id}/export` | 用户确认/导出格式 Markdown | 不将 AI 步骤当已执行事实；导出受控引用 | M5-03/07 |
| `POST /feedback` | run_id、citation_ids、category、note | pending_review，不自动入库 | M5-07 |
| `GET/POST /eval-sets`、`POST /experiments` | 数据/配置版本 | 有权限的评测任务，独立队列预算 | M6-01/03 |
| `GET /experiments/{id}`、`POST /experiments/{id}/cancel` | 实验 ID | 逐题结果、统计、基线差异与真实状态 | M6-03 |
| `POST /feedback/{id}/review` | 审核结论/回归题或修订链接 | 只有维护者审核，记录理由 | M6-05 |

鉴权约定：未登录 401；已登录但无功能权限 403；访问不属于自己或无知识范围权限的具体资源返回不泄露存在性的 404；版本/占用/幂等内容冲突 409；游标过期 410；超限大小 413；不支持媒体 415；格式校验 422。前端显式处理，不将所有失败包装为“网络错误”。

## 4. 运行状态机与事件

状态：`pending`、`running`、`awaiting_input`、`cancel_requested`、`completed`、`failed`、`cancelled`、`interrupted`。前四者为非终态，同一会话只占用一个非终态 run。

- 创建后 pending→running。需要型号/补充信息进入 awaiting_input，确认后pending重新领取，再恢复running。
- 取消先进入 cancel_requested；阶段或生成器检查取消，最终 cancelled。浏览器断开不自动取消。
- 只有所有必要阶段成功且无取消意图才 completed。供应商在部分答案后失败为 failed，部分文本保留但不能当最终成功答案。
- 执行进程异常退出且运行租约过期时 interrupted；awaiting_input 没有活动 worker 时不能仅因执行租约过期误判中断。等待超时策略在 M2-06 明确配置。
- 终态互斥、不可复活；新请求创建新 run。释放会话占用采用条件匹配 run_id，旧 run 不能清除新占用。

每个事件字段：`run_id: str`、`seq: int`、`type: str`、`at: ISO8601 UTC`、`payload: object`。SSE `id` 为 seq；comment 心跳不分配 seq。seq 严格递增，可有间隙，禁止依赖相邻整数连续性。

| type | payload 关键字段 |
| --- | --- |
| `run.started` | conversation_id、message_id、策略/修订快照标识 |
| `stage.changed` | stage、state、进度可空、降级说明 |
| `product.candidates` | candidates、expected_version、澄清原因 |
| `product.confirmed` | product_ids、上下文版本 |
| `input.required` | 缺少的槽位、expected_version |
| `answer.delta` | text；重连后按 run_id/seq 去重 |
| `citation.selected` | 本次实际入选证据的 citation 列表 |
| `artifact.ready` | 处理清单/草稿的 ID 与类型 |
| `run.completed` | 最终答案/引用快照版本 |
| `run.failed` | 可公开错误码、阶段、partial_answer 标识 |
| `run.cancelled`、`run.interrupted` | 原因、是否有部分文本、可重试标识 |

终态持久化成功后再发事件；同一 run 只允许一个终态事件类型。考虑“状态写入后进程退出、事件尚未写入”窗口：在同一个 run 文档持久化待发终态 outbox，再幂等写入事件日志；客户端始终可以读快照，不能只靠进程内队列。

delta 约 50–100ms 合并，最终按压测调节；默认事件保留 24h，最终答案与引用按业务保留。服务端过期游标返回 410；Vue 关闭旧流，加载快照，再根据是否仍在运行决定订阅，不重放虚构增量。

## 5. 前端状态与复用

M3-08兼容补充：授权引用响应可空`original: {asset_id,media_type,name,url}`，从精确document/revision登记读取并重新授权；url仅`/api/v1/assets/{asset_id}`，无object_key/bucket/签名URL。历史未登记原件返回null，禁止前端推导原件ID或补造页码/bbox。PDF坐标采用SourceRef.normalized_top_left，叠加原页面旋转与用户旋转，未给bbox不绘制高亮。

M3实际消费说明：原生EventSource不暴露HTTP错误状态，onerror（含410）关闭旧流后GET持久快照，按新seq/非终态再订阅；401/403/404停止，暂态网络/5xx退避。终态事件、快照和命令响应按同run/seq折叠，旧回调epoch失效；取消是独立命令，断流不取消。输入schema由OpenAPI生成，当前动态响应未声明schema，响应TS类型按实际公开字段维护，不能声称完整响应全自动生成。

- Vue Query 管会话/资料/任务/实验等服务快照；query key 包含用户和知识范围。
- Pinia 管当前设备/抽屉等界面状态及按 run_id 隔离的流式状态。不得把相同完整会话数据长期再维护一份。
- run 结束后使对应 query 失效；退出登录清空查询缓存并关闭所有订阅。跨会话切换不复用 delta 缓冲。
- 默认自有 Vue 聊天组件；shadcn-vue 复用基础 UI；PDF.js 自封装。第三方库没有实际构建验证前不能写成“已集成”。
- M3-01 建立固定脚本：`typecheck`（vue-tsc）、`build`（Vite）、`test:unit`（Vitest）、`test:e2e`（Playwright）；测试名过滤语法随锁定版本实测并更新计划。

## 6. 验证、配置与可选范围

M1-11新增同步IngestionService接线已批准M1能力，无M2任务/API。import_file要求request_id/expected_active，支持同资料新修订；原件/解析JSON/原始配图快照写指定对象前缀，失败类型向外传播且仅当前staged attempt可置failed。恢复复用快照及摘要缓存；配置/图片输入变化须新修订。来源回看方法逐项复核仓储范围，完成旧请求不会自动激活已回滚版本。缺图/未解析远程图或摘要未就绪不能发布；PDF显式降级质量保留、标题跨段传播，结构版本为structure-2。V2Index验证完整字段类型，Mongo knowledge_chunk_claims唯一身份预留防止跨修订主键覆盖，要求同一v2集合对应同一注册表数据库；发布验证父关系同修订且无环，learned sparse必须正权重。公开任务接线与生产权限仍由M2承担。

M1-10迁移工具接受显式source_id/name/original_key/original_sha256/chunk_ids及images(url/object_key/sha256)清单。dry-run零服务写；无清单退出2、报告缺项。backup_selection只读选定源并保存完整本地快照；restore_sample要求独立空Mongo和新Milvus/对象前缀，读回一致才生成recovery-report。migrate_batch在任何注册前检查恢复报告/快照hash，只允许1–3份m1_test隔离小样，按快照hash＋源身份checkpoint恢复；同名不合并，旧绝对图URL映射asset://ID，源坐标缺失仍null。全库发现/全量迁移不在当前授权。

M1-09的RevisionPublisher(repo,index,read_original,asset_store)以validate(revision_id,attempt)校验原件、完整索引及图资产并转validated；publish(revision_id,expected_active)重验并CAS单资料活动指针，首次expected_active=None。指针文档内outbox可由reconcile(document_id)修复发布状态；历史validated/published目标可通过同入口回滚，不删新版。索引前冻结index_identity，载荷变化必须新建修订。无跨集合事务，旧公开查询图保持兼容，M2再接任务协议。

M1-08的V2Index使用显式新集合、INT32 ordinal、来源JSON和BGE dense/learned sparse；所有范围值严格字符串JSON转义。write_revision要求staged/attempt一致，同UID正文或元数据变化拒绝；索引清单含正文hash与完整业务载荷hash。search默认读取活动修订快照，空快照不编码；内部显式快照也须复核调用归属。旧集合不删不重建。

M1-07的chunk_document(parsed,max_chars=2000,default_product_ids=())返回Chunk；完整标题留元数据不重复占长标题正文预算，chunk_uid由修订/块/分片/内容hash及上限稳定生成，子片父指向同块首片。原子图片/表格单行超限显式失败，表头重复、行范围真实，Excel单元格refs原样保留；来源document/revision不匹配拒绝。按块不跨型号合并；字符预算不是token预算。旧splitter复用split_text完成N1兜底，原M0章节身份/表格边界不变。

M1-06的process_images返回新ParsedDocument及Asset列表，原文不写模型描述；派生块kind=image、description单独存，SourceRef.kind=image_description。稳定asset_id连接原图片及摘要，重试替换派生块。ImageSummaryService联合键包含原图/上下文hash、模型、prompt版本；MongoSummaryCache以owner/lease CAS，忙碌抛SummaryBusy，失败可再次领取。SharedRateLimiter通过同MongoRateStore/key预约全部导入的供应商slot，不是每线程限额。AssetStore要求注入已存在bucket客户端，只写指定前缀，不调用建桶或策略修改。租约是有界排重，不承诺外部计费跨硬崩溃exactly-once。

M1-05的ExcelParser(purpose=None)不计算公式，Cell分别记录value/formula/cached_value，来源保留sheet/cell/row，未知坐标不补；工作簿用途默认unknown，项目计划标记project_plan，只有显式用途才能当technical。MarkdownParser(purpose='unknown')保留原文图片语法和行/章节路径，本地安全相对图片登记ParsedImage，远程/缺图标记质量并不联网下载。两解析器由ParserRouter注入，不改旧Excel导入图。

M1-04提供MineruParser(provider,work_dir,max_pages,max_bytes,allow_native_fallback=False)。原件hash/修订/解析版本/限制/降级策略共同隔离检查点；保留segment_offset/hash/batch_id/result hash，成功段直接复用，超时恢复原batch。原始page_idx为0起，仅合法段内页码加offset+1；无页码时保持null和质量标记。缺content_list可用Markdown修复但显式structure_repaired/missing_page_refs；原生降级需显式选择并记录provider_timeout/provider_error。批次领取到上传之间进程中断不承诺供应商exactly-once，保留批次供核对，不伪造成功。

M1-03解析契约已实现：ParsedDocument含pages/blocks/images与tables视图、original_sha256/parser/parser_version/quality_flags/purpose；Block的text为原文、description为模型派生描述，source_refs/product_ids/asset_ids单独传播。ParserRouter注入按pdf/md/xlsx注册的Parser，先detect_format验证实际结构；缺适配器或格式不匹配明确失败。旧导入node_entry共用检测但不接Excel，不能宣称旧图完成XLSX；新流水线使用注入解析器。M2持久runner接线见下方M2-09/10契约。

- M0 单元与契约测试不连接真实服务。集成/供应商验证必须显式标记，缺条件不能悄悄跳过后宣称全链路通过。
- M0-02 定义 `unit`、`contract`、`integration`、`e2e`、`live_provider` 标记。integration 必须有独立库/集合/对象前缀；live_provider 明确会产生调用成本。
- M4-01 同步建立最小题集校验器/基线运行器；M6 扩展并提供 UI，不能让 M4 的实验依赖尚未实现的 M6。
- 最小运行器入口固定为 `python -m app.evaluation.runner --dataset <JSONL> --config <YAML> --output <结果目录>`；输出逐题 JSONL 和包含数据/模型/prompt/策略版本的 manifest。M4 的所有消融复用该入口，各次实际参数写入验收记录。
- Redis/Celery、登录会话、测试隔离、任务超时等新配置在相关实施任务中命名并附中文解释；不在规划阶段猜测实际密钥是否可用。
- 可选任务：M5-06 MCP 网页工具、M6-06 Ragas 评分。选择延期时记录原因、影响、重新评估条件，不虚构集成通过。
- 文档是执行依据；任务路径、接口、依赖随真实实现变化时在同一项工作里同步。兼容性或范围取舍追加到[决策记录](../development/DECISIONS.md)。


### M0-02 实施边界

离线测试使用正常模块导入，网络与真实客户端默认拒绝；测试标记不隐式开放网络。旧 API 的 `query_app` 默认 None，经 `get_query_app()` 首次调用建立，允许测试注入 invoke 对象。Mongo 与模型 SDK 延迟初始化；保持原业务接口。CUDA 环境不执行通用锁全量 sync，证据见 M0-02。


### M0-04 字符预算实施

`pack_prompt_inputs` 额外返回 `used_doc_indices: list[int]`，用于 chunk_id 为空的联网证据映射。`used_chars == len(context)+len(history)`，空输入为空串；不插入额外占位文本。预算只包含证据/历史，不含模板、问题与输出 token。图状态增加 used_chunk_ids/prompt_used_docs/prompt_input_chars；图片仅来自 prompt_used_docs，避免落选证据配图。


### M0-06 合并实施边界

`_merge_short_sections` 新增可选 max_length=2000，调用者传入真实 max_len。返回副本，缺来源/父标识不合并，来源/产品/结构/表格不同不合并；新增 merged_titles/merged_parts 保存完整标题和片段号。长块拆分保留输入元数据，尚不等同于 M1 SourceRef 实现。


### M0-07 旧接口兼容变化

生成异常 `AnswerGenerationError(RuntimeError)` 携带 partial_answer，通过实际节点/图调用传播。输出节点不发终态；旧 API 的 run_query_graph 在整图成功后设置 completed 并发送唯一 final，失败设置 failed、保留 partial_answer 和公开 error，不保存成功助手消息。非流式 POST /query 失败由原 200 改为 502（status=failed/answer 为空），成功保留原字段并增加 status=completed。每轮清空上一轮进程内结果；没有实现 M2 的持久运行协议。


### M0-09 外层补充

旧 GET /history 的 limit 必须 >=1，无效值返回 422（访问仓储前）。多主体匹配只要还有候选歧义，step_6 优先返回澄清，不基于另一已确认主体继续查询。SDK FlagEmbedding 1.3.5 的设备构造参数 devices 正确接收 BGE_RERANKER_DEVICE。

### M0 第 2 轮审查修复边界

标题拆分为每轮调用生成随机运行前缀、每个章节实例分配 `section_instance_id`，包括同名标题的独立实例；长块通过副本传播。合并须具备非空且相同的实例 ID，或调用方显式可靠 section_id，并满足原来源/产品/父标题/结构/大小约束。heading_path/标题文字/part 相等不能单独作身份；本字段只在当前切片处理内使用，不是 M1 持久知识 ID，也不迁移既有 Milvus 数据。原有无分隔符长串/超长标题超预算边界交 M1-07，M0 不宣称所有长块严格限长。

图片验收由 `scripts/verification/image_acceptance.py` 共享实现。准确对象清单以真实配置绑定 origin/bucket/key/复制时 SHA256，不从答案 URL 推断允许范围；未知 URL 在请求前拒绝，GET 禁止自动重定向。正文须包含人工确认的预期拓扑图、final 须含同图，final.answer 与实际答案一致，正文引用图均在 final 中；可额外携带其他已记录合法入选图。所有引用/final 图响应均须 HTTP 200、image/* Content-Type、SHA256 相符、可完整解码且实际格式与 MIME 一致。校验结果只记 key/hash/类型/尺寸/状态，不回显 URL 或异常正文。离线 fake 通过不代表真实图 HTTP 通过。

每轮审查生成器必须使用 --spec 选择实际报告、测试结果与新输出前缀；测试数和状态从实际证据/清单读取，检查器不固定 73 或特定失败状态，不覆盖旧提交快照。原已知题/追问证据可保留；R3 须另有正常配置且无脚本专有预热/线程覆盖的全新进程冷启动证据。

### M0 第3轮验收补充

允许既有HTTP元数据image/jpg作为image/jpeg的限定别名，仍须实际JPEG、复制时精确SHA256、verify/load完整解码；PNG/其他类型不能借此通过。不修改对象元数据或桶策略。只读复核必须用原响应正文SHA256唯一匹配真实持久化助手消息，且原报告已证明唯一final、正文/final一致及图集合合法；再比对持久化图集合与原final并真实下载。复核退出码与源命令退出码分别记录，不把重新构造参数当新final事件。正常冷启动报告须说明隔离/日志/下载保护覆盖及实际线程环境，不把图片诊断预热结果当冷启动。第三轮自验见M0-submission-r3.md，总控已通过，授权与验证边界见M0-review-r3.md及REVIEW_STATUS.md；提交快照的待审查字段按原时点保留。

## M1审查修复：表格物理来源与处理版本

Markdown解析器版本2按实际标题级别维护路径；表格rows不含分隔语法，row_numbers与每一数据行一一对应原文件物理行（含表头）。拆片SourceRef首项指正文范围，重复表头使用独立SourceRef。Excel短横线是数据，保留sheet/cell/实际row；PDF未知行/列不推算。切片版本2进入pipeline_identity，升级解析/切片需新请求修订，不回写已发布旧产物；历史回看使用已存载荷。
## M1审查修复：自包含恢复与目标保护

backup_selection输出version=2，milvus_schema/milvus_indexes纳入snapshot_sha256；restore_sample不得读取源服务，仅使用本地快照及目标客户端。旧v1缺元信息明确拒绝，保留旧快照并另建新版。恢复保留原主键、全部业务/动态字段、向量与对象引用。Mongo/Milvus/MinIO所有目标检查在任何写入前完成；拒绝源目录重叠、已有对象/非空前缀及非规范路径，默认不覆盖或续跑失败目标。测试使用新隔离目标，不删除真实源来模拟不可用。

## M2-01实际入口与生命周期

app.main:create_app(settings=None,resource_factory=open_resources)建立/api/v1；默认lifespan读取Settings并建立Mongo连接，退出关闭，import不建资源。健康/api/v1/health。错误含error.code/message/details和request_id；验证错误仅返回字段位置、不回显输入，未知异常统一500脱敏。旧查询/导入服务继续作为独立本机兼容入口，不挂载新路由、不新增弃用日期；不把旧服务误称受新鉴权保护。后续M2路由仅加入新application。

## M2-02实际身份契约

POST /api/v1/auth/login校验明确Origin与Mongo持久来源限流，返回user（user_id/username/role/kb_ids）和csrf_token及support_session HttpOnly/SameSite Strict Cookie；GET /me恢复公开身份与CSRF；POST /auth/logout需Origin和X-CSRF-Token并撤销会话。账号/会话/限流在users/login_sessions/login_attempts，密码scrypt含随机salt，原始会话令牌不入库。401登录失效、403同源/CSRF/功能权限、404具体资源越权；字段验证不回显输入。viewer无维护权限，所有角色的kb范围仍必须显式授权。账号仅本机create_user.py交互创建，无默认账号密码，不改真实.env。

## M2-03实际会话与消息契约

GET/POST /api/v1/conversations、PATCH /conversations/{id}（expected_version）、GET /conversations/{id}/messages。目录按字符串ID游标，消息按原子ordinal游标，limit为1–100，消息cursor非负整数；允许序号间隙，不以时间戳分页。每次查询按owner及当前kb授权，越权404。消息message_id由run_id和role稳定生成；同ID不同快照409，product_snapshot/citations持久后不可变。会话创建的product_ids为默认选择，实际逐轮快照在创建run时冻结，不改旧消息。

## M2-04实际运行领取契约

POST /conversations/{id}/runs接受question/client_request_id/kb_id/product_ids，返回202持久快照；GET /runs/{run_id}复核owner及当前kb。幂等键(owner,conversation,client_request_id)，同键不同输入409；消息ID由run/role稳定派生。先持久preparing运行再CAS会话active_run_id，之后标claimed并幂等写用户消息；请求重试或RunRepository.reconcile可核对补足任一步中断。竞争失败请求持久rejected且同键仍409；完成重试不会重新占用。终态释放仅匹配本run，不能清除新run。无Mongo多文档事务、无全局内存锁。执行/事件在后续任务接线。

## M2-05实际事件与恢复契约

GET /runs/{id}/events接受非负after_seq及Last-Event-ID（取较大值），返回text/event-stream，每条id为seq、event为type、data为完整信封；15秒注释心跳不分配seq，禁止代理缓冲。先验证身份/资源/游标再返回200，流中继续检查当前账号和kb；断流不取消后台运行。EventLedger.emit在run文档CAS增加版本/seq、状态/答案及outbox，再幂等投递run_events，保存失败向外传播、不伪成功；新实例read/flush补投。允许序号间隙，终态互斥。每条事件独立24h TTL，读取显式核对真实游标事件（初始0核对首事件），不依赖TTL即时清理；缺失/过期410，前端读GET快照。超出当前seq或格式错误422。DeltaBuffer约75ms/8Ki字符或显式终态前flush。

## M2-06实际命令与租约契约

POST /runs/{id}/confirm-product要求expected_version/product_ids，校验当前awaiting_input、owner/kb/候选/人工期限；保存新产品快照及恢复点后pending，重新领取执行token，旧token不能结束新执行。POST /runs/{id}/cancel按版本保存cancel_requested，同一expected_version重复取消幂等；运行边界收敛cancelled，取消后拒绝completed。终态不可复活。执行租约续约也增加version，扫描不能按旧版本中断已续约任务；人工等待独立超时。run.input_product_snapshot冻结创建时用户消息选择，run.product_snapshot可随确认变化，避免原请求重发篡改旧消息。默认执行60秒、排队300秒、人工86400秒，每10秒CAS扫描恢复；新run占用不会被旧run释放。

取消意图存在但原执行租约失效时标interrupted（未获得执行器停止确认）；未开始执行/人工等待无租约的取消可由扫描直接收敛cancelled。

M2-07知识数据使用显式M2_KNOWLEDGE_OWNER_ID的单组织归属，用户当前kb授权仍必须匹配；个人会话/运行不共享。产品需knowledge_product_kbs显式绑定kb。上传接收multipart file/kb_id/product_ids(JSON列表)/client_request_id，可指定document_id建立新修订；purpose默认unknown。请求绑定原件hash和元数据，先登记不可变修订/任务，再保存随机对象键，成功后202；实际导入/发布在后续执行任务或维护API完成。旧课程资料不自动接管。

## M2-08实际资产契约

上传响应新增original_asset_id。GET /assets/{id}先授权组织owner+当前kb+修订，原件/图片验SHA256；PDF返回Accept-Ranges及单段bytes 206，无效/多段416含Content-Range bytes */size，完整200。撤回不删历史原件。GET /runs/{rid}/citations/{cid}需个人run和该轮入选citation，复核资料/图片修订，返回原文与display_text/asset_urls（仅登记asset://）；不对任意外部图片发请求。旧图映射只接受维护者显式对象/hash清单，完整解码后登记稳定ID；旧桶策略不改。旧get_minio_client不再在import或首次调用建桶/设置公开策略，运维需事先准备桶。


## M2-09/10持久导入执行契约

Mongo import_jobs为事实账本，先发broker再确认dispatch_pending，消息仅job_id。至少一次投递由pending/过期running条件领取及attempt/token/期限fencing收敛；completed重复投递不执行。心跳续任务和资料发布许可，旧attempt/过期许可不能保存或切换活动指针。对象仅相对key，禁止Windows路径、URL、穿越。Redis Lua跨worker原子预约供应商预算。

原件验hash，parsed/原图对象、摘要缓存、分批嵌入检查点复用；MinerU分段batch挂持久卷。429/超时/5xx可重试，格式/鉴权/配置先处理，公开错误仅code/stage。验证来源/索引后才发布；已发布终态中断可核对修订收敛。供应商响应至检查点保存窗口不承诺付费exactly-once。Linux强停仅独立测试worker，生产灾备未验收。


## M2-11实际问答适配契约

API生命周期每200ms扫描claimed/pending，进程最多4个运行，Mongo start CAS防多进程重复领取；每租约三分之一续约。SSE断连不影响执行。型号仅显式组织/kb产品；无选择且多候选时awaiting_input，最多50，确认后新token继续。当前用户启用/kb在执行边界复核，撤权停止输出并记脱敏失败。

v2检索冻结活动修订，产品过滤，真实重排保留完整来源元数据，旧回答节点预算选出实际入选证据；无入选证据明确回答并不调LLM。ContextVar出口将旧delta转持久answer.delta，不创建session队列/旧history。引用为本run稳定citation_id及原文/来源/资产快照。输出仅允许本轮入选asset的受控图片路径，分段图片与HTML在写事件前过滤。

completed CAS同时保存completion_snapshot，assistant消息稳定ID幂等落库，恢复扫描补偿CAS后消息丢失；错误保留部分答案/阶段且无成功assistant。取消/失联按M2-06收敛，旧执行不能迟到completed。旧整图仍独立保留，不将旧课程检索挂到新权限体系。

### M2复审错误分类

导入供应商超时（含OpenAI APITimeoutError/httpx.TimeoutException）公开upstream_timeout；连接失败（含OpenAI APIConnectionError/httpx.NetworkError）公开upstream_connection_failed，均retryable=true。429/5xx可重试，401/403及400/格式错误不可自动重试。普通文件OSError不作为网络超时；维护者与expected_version门禁不变。

M2复审许可补充：跨job仅原子接管import_lease_until已过期的许可；同job更高attempt/同代异token保护，旧heartbeat/finally完整permit匹配，不影响接管者。最终发布fencing不变。

### M2复审完成消息与下一轮顺序

completed CAS持久保存completion_snapshot后，先幂等写assistant再释放会话。RunRepository.release从账本重读快照，各终态出口/事件flush/恢复复用；新轮reconcile先补偿active旧终态再CAS领取。写失败不释放旧占用，不插入下一轮user，可用相同client_request_id恢复。跨实例并发补偿只保留同一稳定消息，ordinal保持首次写入的值，不重排或改时间；释放仅匹配本run。正常QueryRunner每次completed均保存快照；历史低层无快照终态保留兼容，不推测生成答案。

## M3工作台消费与恢复契约

浏览器只请求同源/api/v1，Cookie身份与CSRF；不读供应商密钥，不把签名对象URL或内部对象键交给浏览器。输入类型来自版本化OpenAPI；无响应schema的动态字段按真实公开接口补充，不能声称完全自动响应生成。

Vue Query按用户/kb隔离目录与历史；401/退出清Query、设备/证据UI并关流。Pinia只保存活动run与UI；历史以持久message_id/ordinal为准。EventSource按run/seq去重，断连/410先回快照再订阅；终态不重连。确认带展示version，冲突后重选；取消独立POST，失败保留部分答案而不显示完成。

引用编号关联该run稳定citation_id，原图仅登记资产白名单；HTML和危险链接禁用。引用可空original由精确修订登记与授权产生；PDF.js本地固定版本、坐标换算、无bbox只定位页，取消旧渲染并拒绝迟到结果。

上传接收、导入完成与活动发布是不同状态；client_request_id处理网络重试，维护操作带版本或活动指针CAS。前端隐藏按钮只改善体验，后端鉴权仍是边界。旧课程入口保留；生产部署、压力/长期与全库迁移不属M3验收。

### M3首轮复审：恢复与设备范围

缓存历史允许先显示，当前run的恢复须协调本次目录与历史刷新。新的active_run_id或末页运行身份不能被旧完成快照锁住；异步读取以会话epoch和请求代次胜出，目标不变时不重开流。创建运行同时更新本会话目录/历史，避免旧指针盖住新轮。未读末页且无活动指针时不能据首历史页允许发送。

目录选择保存设备描述及其用户/kb身份。问答首100项未含所选ID时，以已有型号做一次授权搜索（最多100条）并精确匹配ID，成功才补充可见option/提交。无描述、搜索不含该ID、错误或等待均明确禁发，不无限加载目录、不静默清ID；用户可主动清空/重新从目录选择。描述不是授权事实，不能单靠旧描述跳过核对。退出/401/切范围清ID和描述；后端仍独立校验权限。


## M4评测接续约定（未验收）

JSONL逐题固定id/group/split、问题/产品/历史、期望行为、必需证据组及替代原文页/资产。辅助草稿、用户委托的独立助手原件审核、真实人工三种身份分开。新增annotation.method=independent_assistant_review；reviewed必须有reviewer及review的artifact/文档sha256/40位commit/independent_source_audit/subject_sha256。subject绑定不含annotation的原始对象规范JSON指纹，改内容后不能继承旧已审；修订草稿可关联旧review但不能宣称已审。schema校验引用形状/内容绑定，实际来源文件与Git提交字节由交付检查复核，不假称认证身份。human_reviewed只记真实人工。support-v1-r2保留原35/15及稳定ID，43题原内容助手已审、7题修订草稿，真实人工0；原版字节不变。澄清题允许空证据，来源组召回null，不强迫引用某型号。用户不必再逐题核50题，修订先定向回交；本轮不执行基线或heldout。运行器不依赖M6，输出尝试日志/结果/参数manifest，按相同配置恢复；heldout需最终阶段与精确策略列表、题集/开发报告hash。真实适配器只传输入字段，标准答案不进上下文；范围限定m1_test_m4数据库/集合和m4-test归属/对象前缀，以冻结原件与活动修订拒绝串库。正式工作台基线为QueryRunner/V2Index，旧图保留兼容。尚未建立实际baseline.yaml和三资料语料，不把单元注入当真实基线。见[evaluation手册](../evaluation/labeling-guide.md)。

## M4供应商能力与失败传播

`app/infrastructure/providers/policy.py`提供ProviderPolicy.load/capabilities/classify/invoke_json；clients.py接文本invoke/stream、视觉摘要、本机推理边界。`PROVIDER_POLICIES_ENABLED=false`默认保留旧SDK请求参数，显式启用才加载对应策略；不因可选工具或视觉缺配置阻断文本问答。能力描述与真实探针分离，配置存在不标verified。JSON同步对象有限格式重试，JSON流拒绝；部分文本流失败不重新打开流，完整外层失败/无助手成功消息。

问答error保留code/stage并可新增retryable布尔；上游超时/连接/429/5xx可重试，鉴权/模型/格式/未知不统一改可重试。只传播安全码，不回显供应商正文/地址。旧APIError原因链与撤权安全逻辑优先保留。导入既有错误码与许可/维护权限/版本门禁不弱化，ProviderFailure可沿现有分类入口传播。配置见[说明](../CONFIGURATION.md)，本机timeout只在同步推理返回边界检测，不承诺抢占CUDA。


### M4-01 独立真实基线冻结（2026-10-24）

题集七题总控定向复核已通过，外部接受结论绑定当前subject及冻结版hash，累计50题来源审核、真实人工0。冻结JSONL/manifest不回写review计数。真实baseline-r2配置已建立，仅dev35题运行；heldout15题不执行。新增corpus.snapshot冻结三资料完整切片payload与dense/learned sparse向量hash、原件字节、图片归属/对象字节/摘要及缓存identity/来源与kb产品。RealQueryExecutor默认入口必须完整快照与dataset_acceptance文件hash；每题在创建/恢复run前重新只读校验，变化即拒绝，不以原件/活动指针相同放行。runtime_versions.code包含app/evaluation实现，避免评分变更冒充同版本。

corpus.asset_equivalences仅接受原件目视核对、两端图片hash与物理页绑定的精确对应，并核对比对证据hash。指标可据此匹配标准裁图，不修改实际引用hash，也不将同页邻图视为命中。allowed_evidence_group_recall是辅助来源覆盖，human_answer_correctness仍null；行为为协议/证据保守判定，不是答案质量分。配置文件字节hash与规范JSON config_sha256分别记录。模型/依赖/课程数据不升级，历史摘要模型/prompt未知明确保留；新解析和视觉供应商调用0，文本调用待真实账本核对。基线执行期间不改app源码或冻结配置，版本变更另建实验。


### M4-02 候选与阶段溯源

RetrievalHit以document_id/revision_id/chunk_uid组成身份，保存原text/metadata与独立StageScore(stage/rank/score/score_kind/query_id)。dense和learned_sparse为真实IP分路，weighted_fusion为Milvus加权分；原策略不称RRF/BM25，未知分数null且backend_unspecified。QueryPlan保留原问题/实际检索输入/产品/修订；EvidencePack校验候选、重排和实际上下文子集及原文/来源不变。重排不得新增或重复候选，不同修订的旧同名ID不得融合。

V2Index.search新增trace=True（默认）补同向量/同范围分路排名，多2次只读RPC；trace=False返回原融合响应，不改原融合/候选量。正式QueryRunner在持久run内部保存query_plan/retrieval_trace及selected标记；公开snapshot字段和citation.selected事件保持原接口，不暴露调试正文。实际citation只来自prompt_used_docs，未进上下文的图片不纳入引用。旧图适配无损保留原元数据/RRF/重排分；错误/取消/撤权继续通过原run协议收敛。


### M4-03 主体与查询计划

目录按NFKC/大小写/分隔符规范化的完整标准名/别名精确匹配，数字品牌不当单一设备，近/未知型号（含显式纯数字及全角）只给待确认候选。可选本机目录向量最多50项/前三候选，精确命中不编码，向量分不当确认概率；不可用仍澄清，超过50要求UI目录先选。错误码、协议编号和环境版本不当设备。用户确认后按同run/版本门禁恢复，不再解析原未知名强迫重复确认。

QueryPlan增加rewritten_query/slots/scope_groups/candidates/unconfirmed_tokens/reason，route区分answer/clarify/compare/insufficient/general/series。原问题不变，指代改写只加本目录已确认设备，槽位来自用户原文，不信助手猜测。比较每个产品独立过滤取证、共用权限与修订快照；后续证据缺失/预算仍须M4-06/07约束。内部requested_product_ids保留请求显式选择；旧run缺字段兼容旧输入快照。product_snapshot.context_route为可选新增字段，general表示继承清空边界；只从成功助手消息继承有效设备，取消/失败的用户快照不能覆盖，UI明确选择与指代冲突需澄清。不修改旧消息、ordinal或原始问题。


### M4-04 检索策略与dev网格

正式入口复用`app/retrieval/search.py`的RetrievalPolicy/retrieve、`rerank.py`的rank_hits及实际V2Index；融合复用已安装pymilvus的WeightedRanker/RRFRanker，不重复实现同名fusion.py以免与服务端分数失配。dense/sparse初召回、融合池、重排输入和上下文候选独立有界；默认20/20/20/20/10与原加权保持。独立参数在run内部retrieval_policy留存；公开API字段不变。各分路共用后端scoped_filter，重排只接受本次真正送入的候选身份，保留复合身份/阶段分数/原文来源。

`real_retrieval_grid`仅表示真实本机模型/索引检索实验，不表示答案生成或人工质量通过。固定grid只允许冻结dev；完整语料/接受结论/运行指纹在写报告前核验，使用独立输出和可恢复attempts，结束再核语料。原m3-baseline适配器显式使用RetrievalPolicy原默认，不受宿主实验环境覆盖；运行版本变化不能续写旧基线。保留课程数据和全部旧证据，不运行heldout调参。


### M4-06 有界证据扩展

V2Index.related_rows按后端owner/kb/document/revision/product范围与种子ordinal窗口/parent_uid定点读取，不递归或整章追加。ExpansionPolicy默认禁用；expanded在EvidencePack中显式区分，必须可溯源候选并保持正文/metadata；不能伪造rerank分。完整父块+种子组在字符预算内原子加入，缺父/超预算省略后半块；相邻证据同样不能绕前提。先按资料轮流给种子预算，再有界补邻居，按复合身份去重，不按相同文本删合法位置。run内部新增expansion_policy/expansion_excluded/evidence_groups用于复核，公开snapshot不增加底层调试正文。所有引用/图像仍来自实际prompt_used_docs，基线适配器显式禁扩展；默认策略须等真实dev实验后决定。

### M4-07 完整生成预算与引用门禁

AnswerBudget包含模型窗口/输出/安全余量/字符兜底/供应商输出字段；build_budgeted_prompt在完整模板渲染后计数，记录计数方式及舍弃数量，前提组原子选取。固定输入过大不调用模型。正式run内部prompt_budget、answer_support、missing_evidence_models、output_truncated用于复核，不扩展公开请求或快照调试字段。引用编号顺序严格按实际prompt_used_docs，不按原候选顺序；资产/来源须属于本次已授权资料修订。未知/残缺/非法编号在流式边界拒绝为answer_citation_invalid；原本已输出的有效部分可保留，不能写成功助手消息。代码反引号和图片alt数字不误当证据编号。

answer_support区分insufficient、partial_scope、partial_context、evidence_available、partial_output，evidence_available仅表示有入选证据而非答案正确。比较缺型号证据时提示资料不足；输出达到上限时中文部分回答说明与流/历史/final一致。来源不符citation_scope_invalid，固定输入超窗prompt_budget_exceeded均不可自动重试。引用门禁只保证本次编号/来源身份，不能替代语义事实正确性审查。
