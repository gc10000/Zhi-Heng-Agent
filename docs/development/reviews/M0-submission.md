# M0 提交总控审查 · 2026-10-23

**提交状态：待审查；M0 尚未全部完成。** M0-01 至 M0-08 已实现并通过对应定向验证；M0-09 阶段离线测试通过，但真实图片题失败，当前 Docker Desktop 启动故障阻断续验。请独立审查代码与现有证据；本提交不请求跳过图片验收，不代表允许进入 M1。

## 1. 任务与验收状态

| 任务 | 实际结果 | 记录 |
| --- | --- | --- |
| M0-01 | 环境、依赖、硬件、路由、配置名称与原集合/桶只读基线完成；备份原文件 | [M0-01](../records/M0-01.md) |
| M0-02 | pytest 独立离线入口；常规模块导入无客户端/模型初始化；5 项定向通过 | [M0-02](../records/M0-02.md) |
| M0-03 | 最新历史窗口及稳定顺序、limit 校验；9 项定向通过，另补 HTTP 边界 | [M0-03](../records/M0-03.md) |
| M0-04 | 完整块字符预算、超长跳过、最近历史、入选证据图片；11 项定向通过 | [M0-04](../records/M0-04.md) |
| M0-05 | 多高分型号澄清、精确匹配、阈值配置；初始 6 项通过，另补混合主体边界 | [M0-05](../records/M0-05.md) |
| M0-06 | 保守短章节合并、大小/表格/来源边界、输入不污染；16 项定向通过 | [M0-06](../records/M0-06.md) |
| M0-07 | 生成失败带部分文本传播至外层、唯一终态；12 项定向通过 | [M0-07](../records/M0-07.md) |
| M0-08 | temperature=0、provider 参数、缓存和本次范围日志脱敏；8 项定向通过 | [M0-08](../records/M0-08.md) |
| M0-09 | **未完成**；73 项阶段测试、3 项既有重导入通过；真实已知题/追问通过，图片题失败，默认冷启动未验收 | [M0-09](../records/M0-09.md) |

总清单 8/9，M0-09 保持未勾选；内部步骤 09.1、09.2、09.V 已完成，09.3、09.D 未完成。REVIEW_STATUS 仅标待审查，执行会话未自签通过。

## 2. 修改文件与关键行为

完整可审阅代码差异：[M0-diff.patch](../evidence/M0-diff.patch)；文件 SHA256、原文件 SHA256 与文档快照：[M0-file-inventory.json](../evidence/M0-file-inventory.json)。本目录无 Git，未初始化或推送；差异从执行前备份生成，后续用户修改须逐片核对。

- `pyproject.toml`、`uv.lock`、`tests/conftest.py`、`tests/unit/*.py`、`tests/contract/*.py`：新增 pytest 开发组与标记；默认仅 unit/contract，dotenv/外部网络/真实客户端拦截。Windows 只放行标准库 socketpair 的直接内部调用，业务回环连接仍拒绝。
- `app/clients/mongo_history_utils.py`：移除导入期初始化；最新窗口排序后反转；非法 limit 先拒绝。
- `app/answering/context_budget.py`、`app/query_process/agent/nodes/node_answer_output.py`、`app/query_process/agent/state.py`：完整块预算及 used_chunk_ids/used_doc_indices/实际入选文档；图片仅取入选证据。预算为证据与历史的字符数，不含模板/问题/输出 token。
- `app/query_process/agent/nodes/node_item_name_confirm.py`：唯一精确型号优先；多个高分非精确命中返回候选；任一主体歧义优先澄清。澄清助手消息由输出节点统一保存，防止重复。
- `app/import_process/agent/nodes/node_document_split.py`：同源同产品、明确同父结构的相邻短块才允许合并，保留元数据；表格和总大小边界禁止合并。
- `app/answering/errors.py`、输出节点、`app/query_process/api/query_service.py`：失败抛 AnswerGenerationError(partial_answer)，外层统一 failed/error；成功整图返回后唯一 final；每轮清空旧结果。图懒加载；history HTTP limit 校验。
- `app/conf/lm_config.py`、`app/lm/lm_utils.py`、`app/core/logger.py`、`app/import_process/agent/nodes/node_pdf_to_md.py`：保留合法零温度；按 provider 传思考参数；缓存包含有效配置；移除输出 prompt/图片/解析签名下载 URL 日志，关闭 diagnose。
- `app/lm/embedding_utils.py`、`app/lm/reranker_utils.py`：SDK 延迟加载；FlagEmbedding 1.3.5 `devices` 正确接收设备配置，附正式构造回归。没有升级模型或改向量维度。
- `scripts/verification/*.py`：只读环境核查、显式隔离真实小样、复用小样的失败题续验、任务记录工具与离线审查差异生成。续验包装真实图仅采集脱敏异常代码位置，不替换业务结果。
- `.env.example`、`docs/CONFIGURATION.md`、README、契约、清单、阶段步骤、records、进度、变更、决策、审计与复用补记同步；基线清单 `evals/datasets/baseline-manifest.json` 明确未完成与失败结果。

## 3. 六项原缺陷对照

| 原缺陷 | 修复前 | 当前结果与证据 |
| --- | --- | --- |
| A01 最近历史 | 正序 limit 取得最早十条 | ts/_id 倒序取最新 N 后反转；同时间戳、会话隔离、空窗与无效 limit 覆盖。M0-03 red 8 failed/1 passed，green 9 passed |
| A02 首证据超预算 | 首块过长即停止，后续短证据丢失 | 跳过过长完整块并继续；元信息/分隔符计费，返回实际入选索引/ID。M0-04-red 与 green |
| A03 历史越预算 | 先追加历史再检查，超长消息突破限制 | 先计算整条成本，最近可容纳完整消息入选后恢复正序；图片 Markdown/URL 不截断。M0-04 11 passed，used_chars 等于实际打包文本长度 |
| A04 型号歧义 | 0.91/0.90 非精确近分时自动取第一 | 两个候选澄清；精确名确认、单高分/中分/低分/重复命中边界覆盖；混合主体歧义不被已确认主体掩盖。M0-05 与 M0-09-self-review-green |
| A05 短章节串合 | 缺父标题的不同章节被合并，元数据可能丢失 | 缺来源/父标识保守不合并；同父/表格/来源/型号/大小/输入副本覆盖。M0-06 red 13 failed/2 passed，green 16 passed |
| A06 失败假成功 | 流中超时被吞掉，部分文本保存成功并 final | 生成失败抛有 partial_answer 的类型异常；外层 failed/error，无成功助手保存/final；非流式 502，成功唯一 final。M0-07 行为 red 8 failed/1 passed，green 12 passed |

单元正常路径、错误路径、必要边界及 A06 外层 HTTP/SSE 终态均覆盖；没有删除有效测试、削弱断言或使用 ImportError 作为原缺陷复现。真实图片题的失败不能由这些 fake 回归替代。

## 4. 实际命令与结果

命令工作目录为项目根目录，使用现有 `.venv/Scripts/python.exe`。

| 命令 | 退出码 | 实际结果/证据 |
| --- | --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/unit tests/contract -q` | 0 | **73 passed，14.99s**；[stage-retry](../evidence/M0-09-stage-retry.txt) |
| `$env:LOG_CONSOLE_ENABLE='False'; $env:LOG_FILE_ENABLE='False'; .venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q` | 0 | **3 passed**；[reimport-final](../evidence/M0-09-reimport-final.txt) |
| `.venv/Scripts/python.exe -m pytest tests/contract/test_history_api.py tests/unit/test_product_resolution.py -q` | 0 | 11 passed；[self-review-green](../evidence/M0-09-self-review-green.txt)，原红测 3 failed/8 passed |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_reranker_options.py -q` | 0 | 1 passed；[reranker-options-green](../evidence/M0-09-reranker-options-green.txt)，原红测 1 failed |
| `.venv/Scripts/python.exe scripts/verification/verify_m0_live.py --run-live --output docs/development/evidence/M0-09-live-first.json` | -1073741819 | 原生加载崩溃，无题通过；[first](../evidence/M0-09-live-first.json) |
| `.venv/Scripts/python.exe scripts/verification/resume_m0_live.py --source docs/development/evidence/M0-09-live-first.json --output docs/development/evidence/M0-09-live-resume.json --cpu-threads 1` | -1073741819 | 同类原生崩溃；[resume](../evidence/M0-09-live-resume.json) 与 faulthandler 栈 |
| `.venv/Scripts/python.exe scripts/verification/resume_m0_live.py --source docs/development/evidence/M0-09-live-first.json --output docs/development/evidence/M0-09-live-prewarm.json --cpu-threads 1 --prewarm-reranker` | 未采集 | 报告 failed；两题通过/图片失败；[prewarm](../evidence/M0-09-live-prewarm.json) |
| `.venv/Scripts/python.exe scripts/verification/resume_m0_live.py --source docs/development/evidence/M0-09-live-prewarm.json --output docs/development/evidence/M0-09-live-image-retry.json --cpu-threads 1 --prewarm-reranker --only image` | 1 | Milvus 连接超时，图片题未执行；[image-retry](../evidence/M0-09-live-image-retry.json) |

各任务定向红绿命令详见对应 records。旧 stage-final 仅 EE、无退出结果，保留但不计通过；本次 73 项完整复跑是阶段结论依据。审查文件生成/语法检查结果见 [artifact-check](../evidence/M0-09-artifact-check.txt)。

## 5. fake、真实与未验证范围

离线 73+3 项使用 fake/内存状态/合成日志，未访问真实数据库、供应商或下载模型，不冒充真实链路。三道真实题经完整旧图的 API runner 执行，模型与仓储均真实，HTTP 服务未启动；协议另由 TestClient/fake 验证。

| 真实题 | 状态 | 耗时 | 核对结果 |
| --- | --- | --- | --- |
| 已知题：如何验证 LA2608 与无线控制器连通 | 通过 | 76.795s | display wlan ap、R/M；completed/一个 final/无 error/助手保存一次 |
| 追问：R/M 分别含义 | 通过 | 48.524s | Run、Master；沿用同一会话，终态和保存均正确 |
| 图片题：连接网络与拓扑图 | **失败** | 43.085s | 无 final/成功助手消息；异常原因链当时未保存，需重新定位 |

未验证：图片正文与正确拓扑图对应、真实图片 HTTP 200、默认无预热冷启动、真实 HTTP `/query` 全流程、MCP、KG 实现、Redis/Celery、Vue 前端、Ubuntu、性能提升。不是跳过后算通过；M0-09 因前两项必需验收未完成而保持未勾选。

## 6. 配置、依赖、数据与兼容

新增可选 `PRODUCT_MATCH_HIGH_SCORE`、`PRODUCT_MATCH_MIN_SCORE`、`LLM_PROVIDER`、`LLM_ENABLE_THINKING`，默认值/范围/用途已在 .env.example 和 CONFIGURATION 用中文说明；真实 .env 未修改。核心配置已在前轮可用，本轮不是缺 Key。MCP_DASHSCOPE_BASE_URL 缺失，仅影响可选联网，不阻塞已有知识路径。

开发依赖仅 pytest 8.4.2、iniconfig 2.3.1、pluggy 1.7.0、pygments 2.21.0；先 dry-run 再安装，torch/CUDA 及原依赖版本保留，未全量 uv sync。锁更新结果见 [依赖差异](../evidence/M0-02-dependency-diff.json)。无上游源码 vendoring，无前端框架或模型更换。

真实数据范围限定于 Mongo `m0_test_20261022_213750_933c22`、同前缀 Milvus chunks/items、MinIO `m0-test/20261022_213750_933c22/` 的四个对象。原资料/缓存/集合/桶策略未改，未清理小样。哈希/对象大小/模型/prompt 哈希见 [baseline-manifest](../../../evals/datasets/baseline-manifest.json)。

可见兼容变化：旧非流式失败返回 HTTP 502，成功增加 status；history 非法 limit 返回 422；流式 final 归整图外层成功路径。原内存任务和 SSE 单 worker 限制保留，未提前实现 M2 持久运行协议。预算仍为字符，不能宣称 token 总预算已受控。

## 7. 阻塞、风险、回滚与后续

**当前外部阻塞：**Docker Desktop 启动时 `initializing Inference manager ... dockerInference ... The file cannot be accessed by the system`，Linux 引擎停止，Milvus 无法连接。只尝试启动已有 Desktop，未恢复出厂、重装、删除 socket/卷、清空桶或重建集合。脱敏证据：[infrastructure-blocker](../evidence/M0-09-infrastructure-blocker.json)。此类宿主基础设施修复不混入 M0 逻辑修复。

其他风险：两次 torch_cpu.dll 原生加载异常只完成参数修正及显式 CPU 独立加载探针，未证明默认启动稳定；图片失败未知根因；旧历史写入仍可能吞存储异常，本轮未重构事务持久化；其他旧节点日志未全面治理；小样仅四切片三题，不是质量评测或性能基准。

回滚时先保护后续用户改动，对照 M0-diff.patch 恢复 originals 对应代码片段；新增代码/测试清单见 M0-file-inventory。撤回新增配置不需修改原 .env；保留隔离数据，停用脚本即可退出测试命名空间，无数据迁移回退。不要对整个工作区做覆盖或对知识集合/桶执行清理。

接续顺序：恢复现有 Docker Linux 引擎与原容器健康 → 复用原小样/会话，按上表 --only image 命令换新输出路径 → 捕获脱敏原因链，按根因补红绿回归 → 验证正确拓扑图/HTTP 200/终态/历史 → 补默认冷启动 → 更新实际结果并重新提交。M0-09 验收前不进入 M1；后续阶段建议仅供总控决定，M1 授权尚不存在。

**等待总控审查 M0。**
