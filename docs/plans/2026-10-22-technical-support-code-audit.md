# 技术支持产品化：现有代码审查记录

日期：2026-10-22。用途：为优化计划提供证据。状态：未修复、未更改业务代码。关联：[主计划](2026-10-22-technical-support-optimization.md)。

本轮阅读导入图、问答图、历史、嵌入、重排、SSE、上传、MinIO 与配置实现，并用 AST 抽取现有函数做六项隔离复现。隔离测试使用自造输入、提示词替身、内存游标或假流式客户端，不访问真实数据库、模型 API 或课程原件。完整结果在 [local-reproductions.json](../brainstorming/2026-10-22/support-research/local-reproductions.json)。

“确定行为”不等于“所有真实问答已经出现错误”；“风险”不等于“已发生事故”。以下刻意区分证据强度。

## A. 已隔离复现的行为

| 编号 / 优先级 | 源码位置 | 输入与现象 | 原因 | 修复方向与回归标准 |
| --- | --- | --- | --- | --- |
| A01 / P0 | `app/clients/mongo_history_utils.py:193`，具体排序在 211 | 20 条按时间递增的消息，取最近 10 条，实际得到 1–10，预期 11–20 | 升序后 limit 得到最早 N 条 | 按 `(ts,_id)` 倒序取 N 条，再反转；测试超过窗口、多条同时间戳、空历史 |
| A02 / P0 | `app/query_process/agent/nodes/node_answer_output.py:66`，89–90 | 首候选正文 12,001 字、第二候选为“短证据”，最终上下文为“无参考内容” | 第一条超预算就 break，后续候选不再检查 | 保留块边界与引用映射；超长块压缩/分段，其他候选继续尝试；不把图片链接切断 |
| A03 / P0 | 同文件 97–119 | 单条历史 13,000 字，实际拼进 13,005 字，超过 12,000 字预算 | 先加入再判断，且每轮反复累加整个 history_str；字符预算也不等于模型 token 预算 | 按单条增量计数；先预算再加入；系统提示、问题、历史、证据、输出预留分别管理；覆盖中英混合和长历史 |
| A04 / P0 | `app/query_process/agent/nodes/node_item_name_confirm.py:157`，192–208 | M3070DHF=0.91、M3070DXF=0.90，提取名为 M3070，直接确认 DHF，未返回候选 | 多个高分时默认选最高项；向量分数不等于经过校准的概率 | 精确标准型号/已确认上下文优先；别名与系列匹配；多个近邻用差值和标注集校准，歧义必须确认 |
| A05 / P0 | `app/import_process/agent/nodes/node_document_split.py:192`，214–225 | 两个不同标题的短章节均无 parent_title，被合并成一块，保留第一个标题 | `None == None` 被解释为同父章节；短章节在长块拆分前未必拥有父标识 | 切片前赋 section_id、heading_path；仅同一结构祖先且不跨适用型号/表格的块可合并；同时限制合并后大小 |
| A06 / P0 | `app/query_process/agent/nodes/node_answer_output.py:139`，159–175 | 假流先产生“部分答案”再 TimeoutError，函数发出 error 后正常返回部分答案 | 捕获错误但未传播失败/部分失败状态 | 明确 completed、failed、cancelled、interrupted；部分答案可留作草稿，但不能作为已成功回答 |

A06 的外层代码证据：`app/query_process/api/query_service.py:59` 的 `run_query_graph` 在 `query_app.invoke()` 正常返回后会标记 completed；输出节点也会发送 completed 的 final。隔离实验未实际调用整个线上图，因此完整故障注入回归仍应在实施阶段覆盖。

## B. 从源码确定的架构或实现缺口

| 编号 / 优先级 | 代码位置 | 当前实现与影响 | 计划 |
| --- | --- | --- | --- |
| B01 / P0 | `app/utils/sse_utils.py:19`，`query_service.py:94` | 一个 session_id 对应一个内存队列；同一会话再次 create 会覆盖；消息与运行无独立主键 | conversation / message / run 分离；同一会话默认一项活动任务，冲突返回 409；不同会话隔离 |
| B02 / P0 | `app/utils/task_utils.py:7`，`sse_utils.py:19` | 任务结果、状态、SSE 事件在进程内；重启丢失，不能跨 worker 共享 | Mongo 运行账本、事件顺序与持久状态；SSE 重放；后台任务租约 |
| B03 / P1 | `app/query_process/agent/nodes/node_search_embedding.py:92` 与 110；HyDE 默认 top_k=5 | 每路双向量请求 limit=10，但混合结果先截成 5；两路融合最终最多 10，再交给重排 | 将初召回、融合候选、重排、上下文数量分别配置；扩大候选是否有效由评测决定 |
| B04 / P1 | 同文件 113；`node_search_embedding_hyde.py` 的 expr 构造 | 按 item_name 字符串精确过滤，直接插值名称，未统一使用已有转义工具 | 使用规范产品 ID 和后端过滤构造器；所有检索分支共享授权/范围/版本条件，测试引号和特殊字符 |
| B05 / P1 | `node_rrf.py:159`、172、182 | 实际融合普通检索与 HyDE 两路；计算出的融合分数在返回时丢弃 | 标准候选对象保留 source rank、dense/sparse、rrf、rerank；不混用为置信度 |
| B06 / P1 | `node_rerank.py:77`、163 | 重排转换时没保留 file_title、文档版本、产品、页码等来源字段；已有 title 回退到产品名 | 全链路透传来源对象；结构化引用来自最终入选证据，不靠答案字符串反推 |
| B07 / P1 | `node_rerank.py:197` | 分差阈值硬编码，至少保留一条；原始 logits 可为负，不能据此当答案可信度 | 证据充足性与 topK 分开；用已标注集校准阈值；证据不足支持拒答 |
| B08 / P1 | `node_answer_output.py:192` 与 final | 图片从全部 reranked_docs 提取，而上下文预算可能只纳入部分文档；final 未返回结构化引用 | 图片仅从本次已使用证据解析；使用 asset_id，返回 citation_id 与图文关系 |
| B09 / P1 | `node_item_name_confirm.py:245` | 确认当前型号时，回写此前缺 item_names 的多条历史 | 不改写旧消息的事实归属；记录会话当前主体及逐轮主体快照，支持显式切换设备 |
| B10 / P1 | `app/query_process/agent/main_graph.py:63` | 默认展开普通检索、HyDE、MCP 和占位图谱四路 | 默认本地证据路径；HyDE 与联网按策略触发；占位 KG 不进生产执行图 |
| B11 / P1 | `node_query_kg.py:12`；`node_web_search_mcp.py:33` | KG 仅 sleep(1)；MCP 超时 300 秒，鉴权与服务配置仍需实际验证 | 移除无产出等待；联网有开关、短超时、来源级别；不把未配置工具作为成功能力 |
| B12 / P0 | `node_import_milvus.py:205`、243 | 先按 file_title 删除旧数据，再 insert 新数据；失败时有不可检索窗口；自增 chunk_id 会变化 | 不可变文档修订与待发布索引；验证完再切发布指针；保留旧版回滚与引用快照 |
| B13 / P1 | `node_import_milvus.py:123`；其他 schema | 主键自增、part 为 INT8；无 document_id / revision / section_id / page_refs | v2 schema 使用业务稳定 ID、INT32 序号、结构化来源；新集合迁移，保留旧集合 |
| B14 / P1 | `node_entry.py:36`、44；导入图路由 | 只识别小写 .pdf/.md；不支持类型会结束图但 API 可能仍 completed | 入口拒绝不支持的格式、规范大小写；Excel 接入统一解析器；不同错误状态明确 |
| B15 / P1 | `node_pdf_to_md.py:57` | 常规导入仍单文件上传 MinerU、600 秒轮询；分段、续传等经验在 output 批脚本 | 抽取已验证的长文分段、缓存、恢复和 Excel 转换到正式模块；服务限制可配置，不沿用“600页”注释 |
| B16 / P1 | `node_md_img.py:195` | 默认串行、局部每分钟 9 次限制，缺跨任务限流与可恢复图像缓存 | 按图像 hash / 上下文 / 模型 / prompt 版本缓存；有限并发和统一速率预算；失败显式标记 |
| B17 / P1 | `app/lm/embedding_utils.py:8`、68；`reranker_utils.py:6` | 懒初始化缺并发控制；所有查询也走 encode_documents；多个进程有各自模型副本 | lifespan/单模型宿主；区分 query/document 编码并验证实际 BGE SDK；小批、限流与显存测量 |
| B18 / P1 | `app/lm/lm_utils.py:48`、60 | 所有兼容供应商都带 enable_thinking；temperature=0 会被 or 0.1 覆盖；超时/重试未按任务显式设定 | provider 能力配置、保留合法零值、结构化输出校验、分阶段超时、重试错误分类 |

## C. 产品化必须补的访问与数据边界

这些来自当前代码的具体行为，不是对本机已暴露到公网的判断。现有 Compose 绑定回环地址；本轮不更改访问策略。

| 编号 | 证据 | 产品化动作与验证 |
| --- | --- | --- |
| C01 | `app/clients/minio_utils.py:31` 导入模块即设置整桶匿名 GetObject | 单独初始化管理；受控原件与图片 API；历史绝对图片链接先映射 asset_id 后再切换桶策略，避免直接断图 |
| C02 | 上传 API 使用 `os.path.join(task_local_dir, file.filename)`，对象键按日期+文件名 | 随机/业务 ID 存储键；文件名仅作展示；限制大小、扩展名/MIME、解析类型，拒绝路径穿越和重名覆盖 |
| C03 | 当前 query、history、upload 无用户归属校验，CORS 为通配 | 基础账号、角色与会话归属；服务端统一验证知识库范围、文件、引用与运行；收紧允许来源 |
| C04 | `node_answer_output.py:134` 日志打印完整 prompt；解析日志可能包含签名下载 URL | 默认只记录 ID、长度、阶段、状态；可选脱敏调试采样；不能把完整知识内容和临时访问凭据默认写入日志 |
| C05 | 原课程代码尚无明确再分发许可；云端模型/解析服务已使用 | 计划保留来源与第三方清单；公开展示用允许使用的样例资料；“私有知识库”不宣传成现状下的完全离线处理 |

## D. 需要实验后才能决定的事项

1. HyDE 是否改善当前中文型号问题，而不是增加延时和跨型号噪声。
2. 稠密/稀疏权重、候选数、RRF 常数、父子片段、多样性去重、语义缓存是否收益足够。
3. 当前 BGE-M3 的 query/document 编码接口差别在所装版本中是否影响结果；不能仅根据函数名断言现网向量错误。
4. 不同分支变成条件执行后，LangGraph 的合并屏障与 reducer 如何避免重复汇合、共享键覆盖；当前不声称四分支必然执行重复，先做带不同延时的图回归。
5. 页码与 bbox 能否从已有 MinerU 缓存恢复；不可恢复的资料只做按需重解析，不伪造坐标。
6. 更换嵌入/重排模型是否值得额外内存、显存、重索引和供应商依赖。先固定现有模型基线。

## E. 实施次序

先 A01–A06 与 B01/B02/B12 的基础隔离，再做数据与产品界面。B03–B11 等检索策略变化在受控题集上实验。C01–C04 与账号、文件接口一起设计，必须在远程部署或多人验收前完成。

以上审查没有修改 `.env`、运行图、存储策略或已入库数据，也不构成“已修复”的声明。

## F. M0 实施补记（2026-10-23）

上文保留原始审计时点。A01–A06 已在真实业务模块落地并经离线红绿回归；最新 unit/contract 共 73 passed，既有重导入 3 passed。B 类仅实现本次导入隔离、零温度/provider 参数及重排 devices 修正，C04 仅治理输出节点/解析签名 URL/diagnose，不声称所有日志或其他 B/C 项完成。真实已知题/追问通过、图片题失败，Docker Desktop 启动故障阻断续验，M0-09 未完成。实现映射、原始失败、兼容与未验证项见 [M0 提交](../development/reviews/M0-submission.md)。后续策略、数据/安全/前端等任务未提前实现。

### 第3轮当前结果（2026-10-23）

第2轮总控已接受R1同名独立章节身份修复及R2准确图片离线实现。用户恢复Docker后仅续验R3，原隔离会话图片题成功，准确拓扑真实HTTP200/hash/完整解码/正文final对应通过；验收器补image/jpg限定兼容，两项反例/正常测试加入，完整阶段105 passed、既有3 tests OK。正常配置无预热/线程覆盖新进程冷启动通过。原业务图片失败未复现/原因未知，历史原生崩溃不声称根治。M0任务9/9自验完成、待总控第3轮审查，见[M0第3轮提交](../development/reviews/M0-submission-r3.md)；原记录保留，M1未授权。
