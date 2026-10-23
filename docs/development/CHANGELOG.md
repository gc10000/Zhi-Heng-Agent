# 开发变更记录

## 2026-10-23 · Git工作约定 · 用户仓库与持续同步

- 用户指定 `https://github.com/gc10000/Zhi-Heng-Agent.git`，授权按任务提交、正常推送，新授权覆盖旧文档中的不初始化/不推送限制，阶段审查及部署边界不变。
- 新增[Git工作流](GIT_WORKFLOW.md)，同步AGENTS、总清单、审查授权、进度和执行Prompt；明确基线、远程历史、文件排除、来源归属及SHA/推送记录。
- 本轮仅文档，未初始化或上传，首次Git接入由执行会话落实；业务78项/核心76项总数不变，无产品能力新增。

## 2026-10-23 · M0-REVIEW-03 · M0通过，授权M1

- 总控独立105项单元/契约（14.77s）及3项既有重导入通过，退出均0；提交时点38份Python语法、82哈希、23链接通过，42份代码/配置与6份prompt哈希一致。
- 总控只读匹配原图片响应并重新验证准确拓扑HTTP/hash/解码；核对冷启动脚本、原报告/控制台与持久化答案，R3接受。原图片异常/历史原生加载根因未知，不宣称根治，原失败保留。
- M0 9/9通过，核心9/76、可选0/2；授权M1-01至M1-11，M1尚未实现，阶段末再审；M2实现未授权。迁移遵守dry-run、备份恢复演练及隔离小样，不全量改写原库或发布。
- 本轮仅文档与独立审查证据，无业务代码/配置/依赖变更，无模型调用/真实存储写入。结论与边界见[第3轮总控审查](reviews/M0-review-r3.md)。

## 2026-10-23 · M0-09 / R3 · 真实验收完成，待总控审查

- 用户恢复现有Docker后复用原小样，仅续验失败图片题；业务图83.858秒成功、唯一final、助手一次。原命令退出1来自验收器拒绝历史image/jpg；未复现原43.085秒业务失败，不声称其根因已确定。
- 先红测1 failed/19 passed，限定image/jpg仅等价image/jpeg，增加PNG伪装反例，21 passed。同一真实响应只读复核HTTP/hash/完整解码/正文final通过、退出0，无重复模型调用/历史写入；不修改桶/对象元数据。
- 新正常配置冷启动脚本，无预热或线程覆盖，真实查询56.599秒、退出0、唯一final、助手一次。配置/实际设备及验证边界见M0-r3-cold-first.json；不宣称长期稳定或性能收益。
- 完整单元/契约105 passed（14.21秒）、既有重导入3 tests OK，退出均0。仅增加2项MIME测试，原103项保留。无依赖/真实配置/业务图代码变更；原件/缓存/原知识/隔离4对象不变，本轮只增4条隔离Mongo消息。
- M0任务9/9、核心9/76，审查状态待审查，提交[第3轮材料](reviews/M0-submission-r3.md)，不进入M1。旧提交、失败与宿主恢复记录保留；回滚见records/M0-09.md。

## 2026-10-23 · R3 宿主恢复尝试 · 仍阻塞

- 接受第2轮总控R1/R2通过结论，不重做已接受的离线修复/回归；无业务代码变更，无新增测试通过声明。
- 正常启动已有Docker Desktop，启动器退出0但backend再次在dockerInference访问处崩溃；只读fsutil报Error1920。官方disable model-runner退出1，backend管道缺失，未能更改设置。
- 未删除socket/卷、未重置/重装Docker或WSL，未重复Milvus预检/真实模型调用。数据写入0，图片题根因及正常冷启动仍未验收，M0维持8/9、需修复，M1未授权。
- 新证据M0-r3-host-recovery-20261023.json；宿主恢复后的具体接续命令仍按records/M0-09.md，不覆盖旧提交或失败记录。

## 2026-10-23 · M0-REVIEW-02 · R1/R2 离线接受，R3 待验收

- 总控独立复跑103项单元/契约（14.80s）及3项既有重导入，退出均0；提交时点36份Python语法、78哈希、22链接通过，40份代码/配置哈希一致。
- R1正常章节路径与可靠实例身份修复接受，M0-06保持完成；R2共享图片检查离线实现接受，总控目视确认拓扑并验证本地文件哈希/解码。真实图片HTTP未验收。
- 仅余R3原图片根因、准确图片真实HTTP与正常冷启动。M0保持8/9、整体需修复，M0-09未完成，M1未授权；不重做已接受修复、不覆盖旧提交快照。
- 仅文档及独立离线验证证据，无业务代码/依赖/配置/真实数据变更，无Docker或模型调用。见[第2轮总控审查](reviews/M0-review-r2.md)。

## 2026-10-23 · M0 审查第2轮 · R1/R2 修复，R3 阻塞

- R1：step_2→step_4 使用本轮章节实例ID区分同名独立章节，缺可靠身份不合并，保留合法同章子块、表格/来源/产品/大小和输入副本边界。红测5 failed/17 passed，修复后23 passed；M0-06恢复验收，待总控复审。
- R2：两条真实脚本共用准确origin/bucket/key/hash、Content-Type/解码/禁止重定向、正文/final对应检查。先离线红测10 failed/2 passed，再修复及补充边界，19 passed。目视完整手册图1并核对准确缓存/复制对象hash；未冒充真实HTTP通过。
- 最新完整阶段103 passed、14.68秒，既有重导入3 tests OK，退出均0。新增30项，未删除旧用例；实际数量与退出码写M0-r2-validation.json。
- N2：生成/检查工具要求--spec，实际状态/数量读取报告与清单，新快照独立r2命名，保留原提交与失败证据。
- R3：本轮一次有超时限制的Docker只读检查退出1，Linux引擎管道不存在；未重试Milvus/云调用，未重置宿主/清卷。原图片根因、真实正确图片与默认冷启动保持未完成，M0-09不勾选，M1不进入。
- 无新增配置/依赖、无真实数据写入或模型升级。兼容新增过程内section_instance_id和验收工具--spec参数；不修改业务API或旧知识schema。回滚/接续见records/M0-06.md、records/M0-09.md，新材料reviews/M0-submission-r2.md。

## 2026-10-23 · M0-REVIEW-01 · 总控需修复

- 独立重跑：73 项单元/契约通过（14.95s），3 项既有重导入通过；原提交语法/哈希/链接核对通过。
- R1：同名独立章节可串合，M0-06 重开；R2：图片检查可假通过，纳入 M0-09 修复；R3：真实图片与默认冷启动未验收，Docker 恢复不能代作原失败根因证明。
- 当前 M0 7/9，核心 7/76；M1 未授权。先离线修复 R1/R2，再真实续验 R3，提交 M0-submission-r2.md。
- 原有连续长文本超限归 M1-07 已知边界，不扩大本轮逻辑重构。审查仅更新文档/合成证据，无业务代码、真实配置或服务数据操作。
- 结论与证据：[M0-review](reviews/M0-review.md)、[合成探针](evidence/M0-review-probes.json)。

## 2026-10-23 · M0-09 · 部分验收，外部阻塞

- 新增阶段回归、隔离真实小样与复用会话续验脚本、未完成基线 manifest、审查差异/哈希工具与 [M0 提交](reviews/M0-submission.md)。未新增占位产品模块。
- 自查修复 history HTTP limit（无效值 422）、多主体任一歧义优先澄清、FlagEmbedding 1.3.5 devices 正确映射设备；先红后绿，有正式回归。没有模型或依赖升级。
- 完整阶段 pytest 73 passed、退出 0；既有重导入 3 passed、退出 0。两道真实题通过（76.795/48.524 秒），图片题失败；默认冷启动有原生异常历史，未验收。旧不完整 EE 输出不计通过。
- Docker Desktop 因 dockerInference socket 初始化错误停止 Linux 引擎，图片续验在 Milvus 预检失败，退出 1。保持 M0-09 未完成，REVIEW_STATUS 仅待审查，未进入 M1。
- 兼容：旧问答非流式失败 502、history 无效 limit 422；新增可选配置见 CONFIGURATION。数据只写独立测试库/集合/对象前缀，原数据/策略不变。回滚与恢复后精确命令见 [M0-09](records/M0-09.md)；不删除小样，不重建数据卷。

## 2026-10-22 · PLAN-02 · 长执行与总控审查交接

- 新增可直接复制的新会话启动 Prompt，明确先连续执行 M0、证据与文档维护、上下文接续和真实阻塞处理。
- 新增 REVIEW_STATUS：开发会话实现与自验，原规划会话独立审查，批准后进入下一阶段；不承诺自动监听新会话。
- 同步 AGENTS、总清单和进度页。没有启动功能开发、服务操作或新会话。

## 2026-10-22 · PLAN-01 · 开发计划细化

- 类型：文档规划，非产品能力交付。
- 新增：开发 ToDo 总表、M0–M7 分阶段任务、公共契约、进度页与验收记录模板。
- 维护机制：固定任务 ID、证据后勾选、会话结束交接、配置/API/复用文档同步。
- 检查结果：78 项任务、394 个内部步骤，编号唯一、依赖无环、文档链接有效；当前核心 0/76、可选 0/2 已验收。
- 本轮应用变更：无。原服务、真实配置和已入库资料未修改。
- 文档验证记录：[PLAN-01](records/PLAN-01.md)。

## 后续记录方式

每条使用“日期 · 任务 ID · 结果”，写明新增/修复/兼容影响/验证/遗留与回滚。业务任务完成时链接独立验收记录；尚未通过验收的代码记录为进行中，不能列入已完成能力。


## 2026-10-22 · M0-01 · 已验收

状态：已验收。目标/改动：scripts/verification/check_environment.py、docs/development/baseline.md；记录 Python/依赖/硬件/API、配置名称存在性及只读集合/桶清单。

环境：Windows，Python 3.12.7，torch 2.10.0+cu128，CUDA 可用。命令：`.venv/Scripts/python.exe scripts/verification/check_environment.py --redact --live-inventory --output docs/development/evidence/M0-01-environment.json`，退出码 0；检查脚本非测试用例（测试数 0）。证据 JSON 中有完整版本、只读实测清单；报告与历史课程记录已区分。

数据/配置：原库只读列名，写入 0；独立命名空间见 baseline.md；缺失可选配置名称与用途同页。无必填新增应用配置；.env.example 未改。同步总清单、阶段、进度、变更记录。

遗留：metadata 读取有弃用提示，不影响检查结果；不会据此声称真实问答通过。回滚：撤回本任务新增脚本与文档；原数据无变化。下一步 M0-02 建立开发测试依赖，不运行全量 uv sync。



## 2026-10-22 · M0-02 · 已验收

状态：已验收。改动：pyproject.toml/uv.lock、tests/conftest.py、tests/unit/test_io_isolation.py、mongo_history_utils.py、query_service.py、embedding_utils.py、reranker_utils.py。建立默认 unit/contract 入口、五种标记、禁止 socket/gRPC/真实客户端的作用域边界、history_store.seed/last_sort；Mongo 连接及查询图延迟到调用处，重模型 SDK 也延迟导入。

环境沿 M0-01。先执行 `.venv/Scripts/python.exe -m pip install --dry-run pytest==8.4.2`，退出 0；再同命令去除 --dry-run，退出 0，新增四个包，未改变 torch。uv 不在 PATH，实际命令为 `& C:/Users/10426/.local/bin/uv.exe lock --offline` 退出 1（pytest 未缓存），随后 `& C:/Users/10426/.local/bin/uv.exe lock` 退出 0。锁定差异见 evidence/M0-02-dependency-diff.json，已有包版本无变化。没有执行 uv sync。

回归命令：`.venv/Scripts/python.exe -m pytest tests/unit/test_io_isolation.py -q`；修复前 2 failed/2 passed，退出 1（M0-02-red.txt）。首次完整导入触发重依赖耗时，已中断，不计通过；单独历史回归 1 failed，退出 1（M0-02-history-red.txt）。修复后增加正常节点导入验证，最终 5 passed，退出 0（M0-02-green.txt）。未把 ImportError 计为缺陷复现。真实业务模块通过常规模块导入；未使用 AST 抽函数。单元不访问数据库/云服务，不下载模型。

对照：原导入会构造 Mongo 客户端和查询图；现在 API/节点导入不连接服务、嵌入与重排实例仍为 None，意外联网明确 AssertionError。标记仅分类，不授予网络权限，真实集成单独运行显式脚本。

数据与配置：仅测试内存 fake；无 .env 或原知识库写入；无新应用配置。同步总清单、阶段、进度、CHANGELOG、DECISIONS、CONFIGURATION、公共契约。回滚：originals 中对应文件恢复，撤回新增 tests；不卸载或替换 GPU 依赖。限制：旧手工脚本不纳入默认 pytest，真实集成尚未执行。下一步 M0-03。



## 2026-10-22 · M0-03 · 已验收

状态：已验收。改动：app/clients/mongo_history_utils.py、tests/unit/test_history_window.py。20 取 10 原返回 1–10，现返回 11–20；ts/_id 倒序限制后正序返回。同时间戳、会话隔离、空/不足窗口、六种非法 limit 均覆盖；参数在访问仓储前拒绝。

环境：沿 baseline，内存 history_store，无真实 IO。精确命令：`.venv/Scripts/python.exe -m pytest tests/unit/test_history_window.py -q`；修复前退出 1，8 failed/1 passed（evidence/M0-03-red.txt）；修复后退出 0，9 passed（evidence/M0-03-green.txt）。

数据/配置：内存合成数据，无库写入、无配置新增。兼容：原函数签名不变，非法 limit 从隐式行为改为 ValueError；旧 /history 路由参数验证将在阶段自查覆盖。同步总清单、阶段、进度、CHANGELOG。回滚：originals 对应历史模块；不得回滚其他任务的延迟初始化。遗留：真实 Mongo 窗口在 M0-09 隔离集成验证。下一步 M0-04。



## 2026-10-22 · M0-04 · 已验收

状态：已验收。改动：app/answering/context_budget.py、node_answer_output.py、QueryGraphState、test_context_budget.py。按完整块先检查再打包，超长块跳过后继续；历史从最近完整消息挑选后恢复正序；头部、分隔符与实际历史只累计一次。返回 used_chunk_ids、额外 used_doc_indices 供无 ID 的联网证据映射。输出节点不插入未计费占位文本，图片只从实际入选证据提取。

环境：baseline，同步/流式外部能力均为局部 fake。命令 `.venv/Scripts/python.exe -m pytest tests/unit/test_context_budget.py -q`；原逻辑退出 1，3 failed（M0-04-red.txt）；提取后 10 passed，退出 0；新增图片范围回归 1 failed/10 passed，退出 1（M0-04-images-red.txt），修复后 11 passed，退出 0（M0-04-green.txt）。包含 12001 字首块、13000 字历史、重复计数、图片 URL 完整性、元信息/精确预算边界、空数据、非法预算、原输出节点接线和图片范围。

数据/配置：仅内存合成输入，无真实 IO，无新配置。兼容：预算仍为字符，12000 仅包含 context/history；模板/问题/输出 token 尚非统一 token 预算，留 M4。返回字典新增 used_doc_indices，原字段保留；图状态同步。公共契约、阶段任务、总清单/进度/变更/决策已同步。回滚：撤回纯函数接线及图状态新增字段，恢复对应 originals 片段，保留其他任务修复。遗留：token 预算与结构拆分属 M4；不声称整个提示词最多 12000。下一步 M0-05。



## 2026-10-22 · M0-05 · 已验收

状态：已验收。改动：node_item_name_confirm.py、test_product_resolution.py、.env.example、docs/CONFIGURATION.md。多个高分非精确命中不再选第一；精确名称在最低候选阈值以上优先；去重、稳定排序且不修改输入。中分候选、低分无匹配、单个高分兼容旧行为；step_6 澄清传播有断言。

环境：baseline；常规模块导入，外部 IO 禁止。命令 `.venv/Scripts/python.exe -m pytest tests/unit/test_product_resolution.py -q`，旧逻辑退出 1，4 failed/2 passed（M0-05-red.txt）；修复后退出 0，6 passed（M0-05-green.txt）。包括 0.91/0.90、精确型号即使分数低于相似型号、低分/空/中分/单高分、重复和输入不可变。

配置：新增可选 PRODUCT_MATCH_HIGH_SCORE=0.85、PRODUCT_MATCH_MIN_SCORE=0.6，仅为归一化检索分数阈值，不是概率；约束与用途见 CONFIGURATION。未改真实 .env；未写原数据。同步总清单、阶段、进度、CHANGELOG、配置说明。兼容：返回字段/签名保持；多个高分现在要求澄清，符合既定设计。回滚只恢复对应对齐函数及新增阈值说明，不覆盖 M0-02 懒加载。遗留：阈值未经过标注集校准，M4 处理。下一步 M0-06。



## 2026-10-22 · M0-06 · 已验收

状态：已验收。改动：node_document_split.py、test_chunk_structure.py；同时把 history/chunk 测试中的应用导入移入 fixture 生效后的调用处，防止收集阶段读取真实 .env。

修复前两个无父标题章节被合并；现在缺父标识、缺来源均保守不合并。同来源同父相邻短块可合并；资料/修订/章节/产品/表格等结构不同保持分离；合并前校验总大小和自定义 max_len，不原地修改输入。保留 merged_titles/merged_parts 及原来源字段，长块拆分透传元数据。

环境沿 baseline；纯内存，不加载模型。命令 `.venv/Scripts/python.exe -m pytest tests/unit/test_chunk_structure.py -q`；旧逻辑退出 1，13 failed/2 passed（M0-06-red.txt）；修复后 15 passed，增加长块元数据验证后最终 16 passed，退出 0（M0-06-green.txt）。无跳过、无真实存储调用。

数据/配置：不重新切分或写入既有知识；仅未来新切片行为变化；无新配置。同步阶段、总清单、进度、CHANGELOG、契约。兼容：原参数保留，新增可选 max_length；合并记录保留所有标题/片段号；缺来源时切片可能更多，是正确性优先。回滚：恢复该模块对应合并/拆分片段，不动已有知识数据。遗留：M1 再建立稳定 section/source_ref 体系；M0 不冒称已完成结构化全解析。下一步 M0-07。



## 2026-10-22 · M0-07 · 已验收

状态：已验收。改动：AnswerGenerationError、node_answer_output.py、query_service.py、QueryGraphState、generation/legacy API 测试，以及 Windows socketpair 测试边界。

前后对照：原流式超时被吞掉，部分答案写成功历史并 final/completed；现在流式/非流式/客户端初始化失败统一抛 AnswerGenerationError，partial_answer 保留，异常到 API 后标 failed，仅 error，不写助手成功消息。旧会话重试先清除上一轮结果，防止旧答案回用；整图成功后外层才发送唯一 final。非流式失败返回 HTTP 502、status=failed，成功响应兼容保留原字段并新增 status。

环境沿 baseline；常规模块与实际 FastAPI TestClient，供应商/图 IO 为 fake。命令 `.venv/Scripts/python.exe -m pytest tests/unit/test_generation_failure.py tests/contract/test_legacy_query_failure.py -q`：首次 8 failed/1 passed，退出 1（M0-07-red.txt），其中 HTTP 用例被 Windows socketpair 内部回环拦截，不计缺陷复现。仅放行标准库 socketpair 直接代码对象，业务回环仍拒绝；再次 8 failed/1 passed，退出 1（M0-07-red-confirmed.txt），均为行为失败。修复后 9 passed，补充首 delta 前失败/图级类型异常/HTTP 正常响应后 12 passed，退出 0（M0-07-green.txt）。

数据/配置：仅内存状态与 fake 保存列表，无真实库写入、无新增配置。兼容与契约见 DEVELOPMENT_CONTRACTS.md；错误只公开通用文案，异常详情不回显；旧内存任务仍不持久，M2 处理。回滚：恢复本项错误传播/终态接线片段并撤回新增异常模块，保留前面任务修复。同步总清单/阶段/进度/CHANGELOG/契约/决策。下一步 M0-08。



## 2026-10-22 · M0-08 · 已验收

状态：已验收。改动：lm_utils.py、lm_config.py、node_answer_output.py、logger.py、node_pdf_to_md.py、test_llm_options.py、.env.example、CONFIGURATION。保留合法 temperature=0；按 provider 能力传 enable_thinking；缓存包含实际配置避免跨 provider 复用。默认日志只记阶段/ID/长度/数量，输出节点不记完整 prompt/图片 URL，MinerU 下载不记签名 URL，Loguru 文件日志关闭 diagnose。

环境沿 baseline；fake 构造器、合成日志标记，不调用供应商。命令 `.venv/Scripts/python.exe -m pytest tests/unit/test_llm_options.py -q`；修复前退出 1，6 failed/1 passed（M0-08-red.txt）；首轮核心修复 7 passed，退出 0；增加 MinerU 下载签名 URL 回归 1 failed/7 passed，退出 1（M0-08-parser-red.txt）；修复后 8 passed，退出 0（M0-08-green.txt）。正常缓存、provider 切换/hostname 欺骗边界、JSON 参数、缺变量名称、prompt 与签名标记不出现于 DEBUG 日志均验证。

配置：新增可选 LLM_PROVIDER=auto、LLM_ENABLE_THINKING=false；解释见 CONFIGURATION；旧百炼域名自动保持 enable_thinking=false，通用接口不再传专属字段，温度 0 不回退。未修改真实 .env 或模型版本，无真实数据写入。同步阶段/总清单/进度/CHANGELOG/配置/决策。回滚：恢复本项构造参数与日志片段，撤回新增配置字段；不恢复其他任务修复。遗留：其他旧节点日志仍待后续阶段按范围治理；不声称全项目日志已完成保密审计。下一步 M0-09 阶段回归与真实隔离小样。

