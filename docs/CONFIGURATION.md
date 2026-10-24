# 配置核对与填写说明

请编辑项目根目录的 `.env`。`.env.example` 仅提供无密钥模板，不能代替实际配置。系统中同名环境变量优先于 `.env`，这是原代码 `load_dotenv()` 的行为。

当前本机 `.env` 已由用户填写两个个人凭据，并通过真实 PDF 导入、带图引用问答、多轮追问及浏览器验证；核心链路无需继续补必填配置，见 [完整链路验收记录](E2E_VALIDATION.md)。下文“需填写”也适用于在新机器从模板重新配置的情况。MCP 联网服务仍未配置。

## 你当前选择的部署方式

当前先在 Windows 本机调试：Python/FastAPI 和两个 BGE 模型直接在本机运行，Milvus、MinIO、MongoDB 使用本机 Docker Compose；百炼及 MinerU 使用你本人的云端 API。后期再迁移到服务器。

本次已将 BGE-M3 与 reranker 下载到 `.env` 默认模型目录，并通过真实推理验证。当前 `.env` 已包含本机服务地址及自动生成的本地 MinIO 密码；本机调试先填写 `OPENAI_API_KEY` 和 `MINERU_API_TOKEN` 即可，联网检索另需配置 MCP 地址。修改 `.env` 后重启两个服务。

本机数据库地址保持 `MILVUS_URL=http://127.0.0.1:19530`、`MINIO_ENDPOINT=127.0.0.1:19000`、`MONGO_URL=mongodb://127.0.0.1:27017`。MinIO 账号、密码由 `.env` 同时提供给应用和 Compose，当前保持一致即可。

## 一次问答中，各配置分别做什么

导入文档时：**PDF → MinerU 解析 Markdown 和图片 → 视觉模型解释图示 → MinIO 保存文件与图片 → 文本模型识别产品主体 → BGE-M3 生成双路向量 → Milvus 保存索引**。

提问时：**MongoDB 读取历史 → 文本模型改写问题并识别产品 → BGE-M3 编码问题 → Milvus 检索，结合 HyDE 和可选 MCP 联网检索 → 本地 reranker 重排 → 文本模型基于证据流式回答 → MongoDB 保存会话**。

因此，文本/视觉大模型、PDF 解析器、嵌入模型、重排模型承担不同工作，不能使用同一个“最新版模型名称”替换所有配置。

## 模型与接口更新核对（2026-10-21）

| 项目 | 官方当前信息 | 本项目处理 |
| --- | --- | --- |
| 文本模型 | 官方选型页列出 `qwen3.8-flash`、`qwen3.7-plus`、`qwen3.8-max`；分别面向低成本、均衡和较强推理需求 | 模板将 `LLM_DEFAULT_MODEL` 更新为 `qwen3.8-flash`；本地 `.env` 仅替换仍为课程默认值的字段 |
| 视觉模型 | 官方视觉选型页同样列出上述多模态型号，支持图像理解 | 模板将 `VL_MODEL` 更新为 `qwen3.8-flash`；复杂图表可选 Plus/Max，不要求名称带 `vl` |
| 百炼基础地址 | 共享 DashScope 域名仍可用，官方建议生产使用业务空间专属域名 | 本地保留北京共享地址；有专属地址时按控制台实际值替换，同时匹配 API Key 地域与业务空间 |
| MinerU 精准解析 | 官方仍提供 `/api/v4/file-urls/batch` 和结果轮询接口，推荐 `model_version=vlm` | 保持当前基础地址及代码中的 `vlm`；`v4` 是接口版本，不表示解析模型已经过时 |
| MinerU 轻量 Agent API | 新增 `/api/v1/agent/parse/*`，文件限制、输出与调用流程不同 | 不是仅改基础地址就能切换的替代品，当前保留精准解析流程 |
| BGE-M3 与 BGE reranker | 本项目是已验证的本地模型链路，未宣称为最新模型 | 保留。切换其他嵌入模型需匹配稠密维度、稀疏表示和 Milvus Schema；更换后需重新生成索引 |

新型号已按官方页面确认，但尚未使用你的 Key 验证账号权限、可用地域及真实效果。模板建议不是“已完成 API 联调”。客户端按 provider 能力配置思考开关，部分结构化调用要求 JSON Object；后续应分别验证文本 JSON 输出、答案流式增量和图片输入。

`LLM_DEFAULT_MODEL` 同时影响多个文本节点。若要只提高最终回答模型、而让改写等节点保持低成本，需要后续拆分配置，当前不能单靠一个变量分别控制。

## 必须填写或确认

| 变量 | 填写方式 | 用途 / 说明 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 本人的阿里云百炼 API Key | 主体识别、查询改写、HyDE、最终回答及图片理解共用。不要使用原课程文件中的密钥。 |
| `OPENAI_BASE_URL` | 默认中国内地百炼兼容接口；账号区域不同需同步修改 | M0 按 LLM_PROVIDER 能力传参；百炼默认 `enable_thinking=false`，通用接口不带专属字段。 |
| `LLM_DEFAULT_MODEL` | 默认 `qwen3.8-flash`，需账号可调用 | 产品主体识别、查询改写、指代解析、HyDE 和最终回答共用的文本模型。 |
| `VL_MODEL` | 默认 `qwen3.8-flash`，需账号可调用 | 给文档中的图示生成文字摘要；应支持 `image_url` 输入，与 MinerU 整份 PDF 解析职责不同。 |
| `MINERU_API_TOKEN` | 本人的 MinerU API Token | PDF 通过云端解析；纯文本 Markdown 可跳过 MinerU。 |
| `MINERU_BASE_URL` | 默认 `https://mineru.net/api/v4` | 代码调用 `/file-urls/batch` 和 `/extract-results/batch/{batch_id}`。 |
| `MILVUS_URL` | 本地 `http://127.0.0.1:19530` | 向量数据库连接地址，保存主体与切片索引。原实现未接入 Milvus 鉴权 token 配置。 |
| `MINIO_ENDPOINT` | 本地 `127.0.0.1:19000` | 保存原文件和图片；**不带** `http://`，本机 19000 转发到容器 S3 API 9000，9001 为控制台。 |
| `MINIO_ACCESS_KEY` | 本地默认 `raglocal` | Compose 与 Python 应用读取同一份 `.env`，保持一致即可。 |
| `MINIO_SECRET_KEY` | 本地 `.env` 已生成随机密码 | 当前本机方案可保留；不要改成 `.env.example` 中的占位密码，也不需要创建 `.env.infra`。 |
| `MINIO_BUCKET_NAME` | 建议使用专用测试桶 `product-knowledge` | 原代码启动时会检查/建桶并设置匿名读取策略。账号需要相应权限，请勿指向已有敏感业务桶。 |
| `MONGO_URL` | 本地 `mongodb://127.0.0.1:27017` | 保存会话消息。后续有鉴权时可用 `mongodb://用户名:密码@服务器:27017/?authSource=admin`，凭据特殊字符需 URL 编码。 |
| `MONGO_DB_NAME` | 建议 `product_knowledge_rag` | 会自动使用 `chat_message` 集合并创建会话索引。 |
| `BGE_M3_PATH` | 本机 BGE-M3 模型目录 | 默认 `./models/bge-m3`；需要下载权重、配置、分词器等完整文件。原作者的 D 盘模型路径不存在。 |
| `BGE_RERANKER_LARGE` | 本机 BGE reranker 模型目录 | 默认 `./models/bge-reranker-large`；原作者对应目录也不存在。 |

## 可以保留模板默认值

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_DEFAULT_TEMPERATURE` | `0.1` | 原代码直接转为浮点数，不要留空。 |
| `CHUNKS_COLLECTION` | `product_knowledge_chunks` | 切片集合，首次导入自动创建。避免填写已有业务集合，重新导入会删除同主体的旧数据。 |
| `ITEM_NAME_COLLECTION` | `product_knowledge_items` | 主体集合，首次导入自动创建。 |
| `BGE_DEVICE` / `BGE_RERANKER_DEVICE` | `cpu` | 先用 CPU 验证；CUDA PyTorch 就绪后再切换 `cuda:0`。 |
| `BGE_FP16` / `BGE_RERANKER_FP16` | `0` | CPU 阶段关闭半精度。 |
| `MINIO_IMG_DIR` | `images` | 图片对象前缀。 |
| `MINIO_PDF_DIR` | `pdf_files` | 原文件对象前缀；原 `.env` 未填，但代码有默认值。 |
| `MINIO_SECURE` | `False` | 原客户端建立连接时硬编码 HTTP，当前阶段先使用 HTTP 端点；HTTPS 端点需要修正客户端后再联调。 |
| `LOG_*` | 见 `.env.example` | 日志输出和保留时间。 |

## MCP 联网搜索

`MCP_DASHSCOPE_BASE_URL` 是百炼 WebSearch MCP 的 **SSE 服务地址**，不是大模型 `OPENAI_BASE_URL`。需要在自己的百炼账号中开通对应服务，代码调用工具名为 `bailian_web_search`，共用 `OPENAI_API_KEY`。

它属于问答中的补充检索。未配置时不能验证联网搜索能力；原节点会捕获搜索异常继续后续流程，并未提供显式的启用开关。先验证本地知识链路后，再用真实服务地址验证 MCP。

当前实现是 Python 直接通过 `MCPServerSse` 连接工具服务，与官方文档中通过 Responses API 让模型调用 MCP 的方案不同。不要将 Responses API 地址或 Streamable HTTP 端点直接填入 SSE 配置。

原节点发送 `Authorization: <Key>`，没有 Bearer 前缀；官方 MCP 示例使用 `Authorization: Bearer <Key>`。这是后续鉴权联调需核实的兼容性问题，不能通过把 `.env` 中的 Key 加上 Bearer 来处理，因为同一个 Key 还用于大模型客户端。本轮仅记录问题，未修改业务调用代码或宣称 WebSearch 已验证。

## 原文件中出现但不需要照搬的配置

- `NEO4J_*`：Neo4j 工具文件存在，但主流程的 `node_query_kg` 只有进度占位，没有真实图谱查询，不需要部署 Neo4j。
- `ENTITY_NAME_COLLECTION`：配置类读取但当前主流程未实际使用，原 `.env` 本身缺此项，对运行主链路没有影响。
- `EMBEDDING_DIM`：当前建集合代码根据实际向量长度计算维度；BGE-M3 为 1024，不依赖该环境变量。
- `MINERU_MODEL_SOURCE`、`MODELSCOPE_OFFLINE`、`MODELSCOPE_CACHE`、`HF_HOME`：旧机器的下载/缓存配置，不是云端 MinerU API 的必需项。特别是不要照搬 `MODELSCOPE_OFFLINE=1` 阻止首次下载。
- `MD_ROOT_DIR`、`ITEM_NAME_DIAG`：主链路未读取。
- `BGE_M3`：配置类读取，但当前嵌入实现选择 `BGE_M3_PATH`，为空才回退 `BAAI/bge-m3`，并未使用这个变量选择模型。
- `PROJECT_ROOT`：可选的项目根目录覆盖项；正常从当前项目根目录启动时无需设置。

## 本地基础设施及后续服务器部署要求

当前使用 [Windows 本机 Docker 调试说明](WINDOWS_DOCKER.md)，服务器部署暂不处理。

1. 当前选择 Windows 本机 Python + Docker Desktop，连接地址用回环地址，无需 SSH 隧道。
2. Milvus 支持 `SPARSE_FLOAT_VECTOR` / `SPARSE_INVERTED_INDEX`；Compose 选用 2.6.10，与原 SDK 主次版本对齐。MinIO 改为固定官方源码构建，首次启动前需执行构建命令。
3. MinIO 使用独立测试桶；原代码会设置该桶匿名只读，浏览器配图也必须能访问其地址。
4. MongoDB 账号有读写目标数据库、创建索引的权限。
5. 如服务器 Milvus 必须鉴权，或 MinIO 仅提供 HTTPS，告知实际要求后再做对应的最小客户端适配。

## 官方参考

以下内容于 2026-10-21 直接读取官方页面核对，模型清单随服务更新；不据此推断账号权限或具体计费金额。

- [百炼模型总览](https://help.aliyun.com/zh/model-studio/models)
- [文本生成模型选择](https://help.aliyun.com/zh/model-studio/text-generation-model)
- [视觉模型选择](https://help.aliyun.com/zh/model-studio/vision-model)
- [百炼基础地址与地域](https://help.aliyun.com/zh/model-studio/base-url)
- [结构化 JSON 输出](https://help.aliyun.com/zh/model-studio/json-mode)
- [视觉理解与思考模式](https://help.aliyun.com/zh/model-studio/vision)
- [百炼接入 MCP](https://help.aliyun.com/zh/model-studio/mcp)
- [MinerU 官方 API 文档](https://mineru.net/apiManage/docs)


## M0 离线测试与环境保护（2026-10-22）

默认 `.venv/Scripts/python.exe -m pytest` 只收集 tests/unit、tests/contract；真实测试另用显式脚本。单元测试不读取真实 .env，禁止网络与真实客户端构造。`uv` 实际位于 `C:/Users/10426/.local/bin/uv.exe`。现有 CUDA torch 为 2.10.0+cu128，不直接全量 uv sync；仅安装锁定 pytest==8.4.2 及必要依赖。已验证原依赖锁版本不变。独立测试命名空间见 development/baseline.md。API 导入不会预加载查询图，首次请求编译；Mongo 首次调用才连接。


## M0 型号分数阈值

可选 `PRODUCT_MATCH_HIGH_SCORE` 默认 0.85（严格大于），`PRODUCT_MATCH_MIN_SCORE` 默认 0.6（大于等于）；根目录 .env 填写，重启生效。须满足 0 <= min <= high <= 1，不是概率。精确标准名在候选阈值以上优先；否则单一高分自动确认、多个高分返回候选、中分澄清、低分无匹配。默认只是延续已有分数基线，不代表经评测校准。


## M0 大模型参数与日志基线

`LLM_PROVIDER` 可选 auto（默认）、dashscope、openai_compatible。auto 仅匹配 dashscope.aliyuncs.com 或其子域的主机名，代理域名需显式指定 dashscope。`LLM_ENABLE_THINKING` 可选 true/false，默认 false；只有 dashscope 才传 enable_thinking，通用供应商不带此字段。根目录 .env 填写，修改后重启；未修改现有模型。LLM_DEFAULT_TEMPERATURE=0 保留，缺省/空值为 0.1。

答案日志记录 session、阶段、字符数和图片数量，不写完整 prompt、知识正文、图片链接；MinerU 结果签名 URL 不记日志。文件日志关闭 Loguru diagnose，避免异常展开局部变量。历史日志未清理；其他旧节点仍需后续按阶段治理，M0 的合成标记检查覆盖本次变更路径。


M0-09 实测 SDK 核对：FlagEmbedding 1.3.5 的重排设备参数是 devices，现已正确映射 BGE_RERANKER_DEVICE，配置 cpu 不会自动改选 GPU；没有变更模型或真实 .env。整图原生加载异常与续验方式见 M0-09 记录。

## M0 第2轮验收运行说明

本轮不新增配置或安装依赖；使用环境已有 Pillow/PyMuPDF 做图像解码和来源页渲染。图片验收运行时以 MINIO_SECURE、MINIO_ENDPOINT、MINIO_BUCKET_NAME 绑定准确origin/bucket，key/hash来自原复制清单；不会把前缀相同的任意站点当成允许对象。预期拓扑身份见 `evals/datasets/m0-image-expectation.json`。下载禁自动重定向；正文/final/MIME/hash/可解码全部满足才通过，真实HTTP尚待R3。

阶段回归可运行 `.venv/Scripts/python.exe scripts/verification/run_m0_checks.py --prefix <本轮新M0前缀>`，保存实际退出码、数量及输出哈希；已有前缀拒绝覆盖。复审工具必须显式传 `--spec docs/development/reviews/M0-r2-artifacts.json`，分别运行 build_m0_review_artifacts.py 与 check_m0_submission.py；不再接受隐式旧报告/73项默认。新提交使用 baseline-manifest-r2.json、M0-r2-diff.patch和M0-r2-file-inventory.json，首轮文件保留为历史。

resume_m0_live 的 --cpu-threads/--prewarm-reranker 仅为既有图片失败诊断路径，不等于正常冷启动配置。Docker恢复后仅复用原隔离小样和会话；正常冷启动必须另起默认配置进程，无脚本专有线程覆盖/预热。精确续验命令与当前阻塞见 development/records/M0-09.md。

## M0 第3轮真实验收与审查运行说明

M1-04新增MINERU_SEGMENT_MAX_PAGES（默认50）、MINERU_SEGMENT_MAX_BYTES（默认100000000）、MINERU_POLL_TIMEOUT（默认600秒），填写根目录.env可调整供应商限制。按字节继续二分，单页超限报错；超时沿原batch恢复，供应商明确失败的下次调用可新批次，旧批次ID保留。allow_native_fallback默认false，仅由调用方显式开启，质量标记随结果传播，其缓存与严格模式隔离。M1_LIVE_PROVIDER=1仅在显式live_provider测试时启用付费调用，默认留空；只上传测试新建小样，不自动选择课程资料。输出/cache保持本地，不打印签名URL。

M1真实集成测试显式设置M1_TEST_DB为m1_test_开头独立库，测试读取根目录.env的MONGO_URL，缺独立库报错不跳过。默认单元/契约测试仍隔离网络；integration标记本身不开放网络，测试不删除库/集合。示例：`$env:M1_TEST_DB='m1_test_20261023_repository'` 后执行指定integration文件。测试变量不应填原业务库；M1_TEST_DB默认留空不影响应用。

M1-11真实新资料贯通测试`tests/integration/test_ingestion_live.py -m live_provider`另需M1_LIVE_PROVIDER=1、OPENAI_API_KEY/OPENAI_BASE_URL/VL_MODEL及MINERU_*。沿用现有配置不升级模型，仅合成图/新一页PDF；视觉原图使用data URL在内存传输，默认30rpm共享Mongo预算，摘要缓存重读不重复付费。测试明确匹配百炼provider时传enable_thinking=false，通用兼容接口不传。非付费阶段回归用`-m 'not live_provider'`；全量集成BGE_M3_PATH必须是已有本地目录，禁止自动下载。单个v2集合应绑定同一Mongo注册表数据库，以便唯一chunk身份预留覆盖所有写入。

2026-10-23用户恢复已有Docker后，原图片题续验及正常配置新进程冷启动已自验完成，105项单元/契约和3项既有回归通过。上节“真实HTTP尚待R3”是第2轮时点，当前见 `development/reviews/M0-submission-r3.md`。本轮没有新增环境变量、改写.env或安装/升级依赖，因此.env.example无新增项。

共享图片验收仅兼容历史image/jpg→image/jpeg别名，继续以准确hash和实际JPEG格式解码验证，PNG伪装不能通过；既有对象元数据、桶访问策略不变。`recheck_m0_images.py --source <原真实报告> --output <新路径>`只读原隔离Mongo响应，以正文hash唯一匹配和原final证据核对，再真实HTTP获取准确对象；不调用模型，不写历史，旧图调用退出1与复核退出0分别保留。`verify_m0_cold_start.py --source <原真实报告> --output <新路径>`必须以新Python进程运行，读取根目录.env中的正常模型/设备配置，仅覆盖隔离集合/库、关闭日志和禁止模型下载；不设置线程或预热。该脚本会进行真实模型/云服务调用，并在原隔离Mongo库新会话新增两条消息，不作为离线测试运行。

精确实测命令、退出码及设备见 `development/records/M0-09.md`。r3审查文件生成/检查分别运行 `.venv/Scripts/python.exe scripts/verification/build_m0_review_artifacts.py --spec docs/development/reviews/M0-r3-artifacts.json` 与同参数的 `check_m0_submission.py`。选用本轮105/3实测摘要、真实图片复核和正常冷启动报告，生成独立baseline-manifest-r3.json/M0-r3-diff.patch/M0-r3-file-inventory.json，不覆盖原或r2文件。脚本输出存在时不要重跑真实问答覆盖；需要重验应选新输出名并保留历史。

## M2统一API入口

使用`.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。启动阶段读取根目录.env，必填MONGO_URL与M2_DB_NAME（独立新账本库，不默认沿用旧课程库）；缺配置只报告变量名。API_ALLOWED_ORIGINS默认http://localhost:8000，逗号分隔明确来源、不允许通配符；API_COOKIE_SECURE默认true，只有本机HTTP调试显式false。当前健康检查/api/v1/health，资源在lifespan创建/关闭，import不连接服务或加载模型。旧query_service/file_import_service独立入口保留，不挂载到新API，不承诺旧无鉴权接口有新鉴权保护。

## M2账号管理与会话

单组织角色viewer/maintainer/admin，账号创建不暴露HTTP注册口。配置M2_DB_NAME后运行`.venv/Scripts/python.exe scripts/admin/create_user.py --username <用户名> --role admin --kb <授权kb_id>`，密码通过getpass两次输入，至少12字符，不放命令行/环境日志。该操作只写显式M2数据库。不可把原课程库默认当账号库。

登录POST /api/v1/auth/login必须携带允许的Origin，成功设置support_session（HttpOnly/SameSite=Strict，Path=/api/v1，默认Secure）；返回CSRF令牌，后续写请求携带Origin及X-CSRF-Token。GET /me可恢复身份和CSRF；POST /auth/logout撤销服务端会话。会话8小时，Mongo只存令牌SHA256且显式检查过期/撤销，TTL仅清理；账号禁用或移除kb立即按当前账号拒绝。固定5分钟窗口每来源最多10次登录，Mongo原子计数跨实例共享；不信任X-Forwarded-For，反向代理需单独配置可信代理。未提供公开密码重置/跨组织管理；维护操作需maintainer/admin，具体资源同时检查owner与kb。

## M2运行超时与恢复

RUN_LEASE_SECONDS默认60秒，执行器需定期续约；RUN_PENDING_SECONDS默认300秒，未领取运行超时中断；RUN_INPUT_WAIT_SECONDS默认86400秒，为等待型号确认的独立期限，不按执行心跳误判。均为正整数秒，填写根目录.env。新API生命周期每10秒核对超时和终态outbox/占用，多个进程通过版本CAS避免相互覆盖；重启可恢复候选、恢复点及取消意图。改动默认配置不写回历史消息/课程数据。

## M2知识目录与上传

M2_KNOWLEDGE_OWNER_ID指定当前单组织知识owner，用户的kb_ids仍限定读取范围；不默认接管旧资料owner。M2_OBJECT_BUCKET指定已存在桶，M2_OBJECT_PREFIX指定独立相对前缀（例如knowledge-api-v2/），新API不建桶/改策略；原件随机key，名称仅展示。M2_MILVUS_COLLECTION须为独立v2集合且不同于CHUNKS_COLLECTION，复用MILVUS_URL；上传不要求Milvus或模型在线，索引/发布时才连接。MINIO_ENDPOINT/MINIO_ACCESS_KEY/MINIO_SECRET_KEY及可选MINIO_SECURE沿用连接变量，但绝不打印值。缺配置仅相关端点503列变量名/用途/根目录.env，身份/会话等仍可用。UPLOAD_MAX_BYTES默认100000000字节，正整数；multipart元数据最多另64KiB，文件不支持路径名。

POST /products为维护者注册产品及显式kb关联；GET目录限当前组织+kb。POST /documents接受file、kb_id、client_request_id、product_ids（JSON列表）、purpose及可选document_id（同资料新修订），成功202返回document_id/revision_id/job_id；job pending/uploaded不表示已索引或发布。GET import-jobs返回阶段/attempt/可重试标记，retry需维护者/版本及错误可重试。修订发布/回滚复用M1真实产物验证和CAS；withdraw只撤活动指针，历史不删。

## M2受控原件和旧图映射

GET /assets/{asset_id}先复核组织资料/当前kb/修订再取对象并验hash，PDF支持单段Range的200/206/416；无签名URL外传。POST documents返回original_asset_id，引用通过GET /runs/{run_id}/citations/{citation_id}读取该run实际持久入选快照，外部图片不自动抓取，登记asset://转换受控路径。旧图片用`.venv/Scripts/python.exe scripts/admin/map_legacy_asset.py --manifest <本地JSON> --kb <授权知识库>`显式核验并映射；清单为document_id/revision_id/bucket/object_key/expected_sha256五个字段，不上传内部清单。脚本只读源图/完整解码并写映射，不改对象或策略。旧get_minio_client首次使用才创建客户端，不再自动建桶/公开桶；需预先准备原有桶，现有策略保持原状。禁止提前收紧课程图片桶。


## M2导入队列与宿主模型桥接

REDIS_URL指定队列与全worker共享限流，宿主默认回环6379；REDIS_PORT为compose映射，M2_QUEUE_NAME默认knowledge-import。JOB_LEASE_SECONDS默认60，JOB_HEARTBEAT_SECONDS默认10且须小于租约。VISION_REQUESTS_PER_MINUTE默认30，按模型跨worker原子预约。均填写根目录.env，不打印连接值。

MODEL_HOST_PORT默认8011，MODEL_HOST_URL为worker可达宿主地址，MODEL_HOST_TOKEN需自行生成且不可为空。宿主启动`.venv/Scripts/python.exe -m uvicorn app.infrastructure.model_host:app --host 0.0.0.0 --port 8011`，仅允许本机Docker访问，禁止公网。桥接复用现有CUDA模型，不自动下载；Linux worker不装PyTorch，不接收Windows模型路径。

先运行`docker compose --profile tasks up -d --no-deps redis`，再按compose构建/启动worker，宿主运行`.venv/Scripts/python.exe scripts/admin/dispatch_jobs.py`扫描任务。容器覆盖Redis/模型地址，存储连接须容器可达。M2_WORK_DIR默认/var/lib/knowledge-worker，挂worker-cache保留MinerU分段batch。禁止down -v或清缓存重试，详见[恢复手册](runbooks/worker-recovery.md)。


## M2持久问答运行

`.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`启动统一API，生命周期后台领取持久pending，与SSE订阅分离。默认使用现有Windows BGE/重排配置，MODEL_HOST_URL和MODEL_HOST_TOKEN同时存在时嵌入走同一受控桥接；重排仍使用已有宿主配置。不新增模型、不自动下载。多型号未选择时等待确认；超过50候选需先从目录选型号。缺配置按相关run失败阶段显示变量用途，不影响其他已配置端点。旧独立query_service继续作为兼容基线，新API不调用其无鉴权路由。
# M3 前端本机配置

`API_PROXY_TARGET`仅Vite开发代理使用，默认`http://127.0.0.1:8000`；通过进程环境设置，不进入浏览器bundle。后端`API_ALLOWED_ORIGINS`须明确加入`http://127.0.0.1:5173`，本机HTTP用`API_COOKIE_SECURE=false`，HTTPS保持true。前端不读取根.env、不向VITE_变量复制任何供应商密钥。依赖、启动和隔离浏览器验证见[前端说明](../frontend/README.md)。

## M4按能力供应商策略

在根目录.env配置`PROVIDER_POLICIES_ENABLED`，默认false保留原SDK参数，不提前改变原链路基线。true后按下表独立加载，仅所用能力缺配置/配置错误时失败；不因缺VL_MODEL或MCP工具阻断本地文本问答。SDK内部重试只处理其可重试网络/HTTP状态；流已开始后不重新打开流。修改后重启API/worker；不自动改写.env，不升级模型或依赖。

|变量前缀|TIMEOUT_SECONDS默认|MAX_RETRIES默认|JSON_SUPPORTED默认|JSON_RETRIES默认|
|---|---|---|---|---|
|PROVIDER_TEXT_|60|2|true|1|
|PROVIDER_VISION_|120|2|false|1|
|PROVIDER_EMBEDDING_|300|0|false|0|
|PROVIDER_RERANK_|300|0|false|0|

完整变量名由前缀加列名组成，均同步.env.example。秒数为有限正数且不超过3600；额外重试/JSON格式额外调用均0..3；布尔只接受true/false。本机嵌入/重排不生成JSON，禁止启用JSON或设置非零JSON重试。temperature沿用LLM_DEFAULT_TEMPERATURE，合法零值保留。视觉摘要是纯文本，不启用JSON；视觉JSON声明供能力描述，当前未提供JSON视觉调用口，不能称该能力已验证。JSON模式仅同步invoke返回合法对象，拒绝数组/null/NaN/代码围栏，格式错误有限重试；JSON流式明确拒绝，避免将未验证片段交给调用方。

文本/视觉SDKtimeout限制网络请求；MODEL_HOST桥接使用embedding超时和受限重试。本机同步嵌入/重排仅在调用返回边界检测超时，**不能强制中断CPU/CUDA推理**，返回超时后不再自动发起第二次推理；仍需M4-08资源实验决定进程隔离。默认0重试，显式本机重试只针对已分类可重试异常，未知GPU故障不盲重试。嵌入数量/有限向量、重排数量/有限分数错误拒绝为provider_invalid_response，不能写成功结果。

`Settings.provider_capabilities()`仅本机配置检查，不访问模型列表、不发付费探针；configured不等于verified，verified始终false。返回变量名、策略和布尔状态，不返回密钥/端点/本地模型路径。默认不开新公开HTTP端点。真实调用的错误模型、鉴权、限流、5xx、连接和超时明确分类；问答外层保存安全code/stage/retryable，仍保持failed且保留部分答案，不自动复活run。

公共错误码：upstream_timeout、upstream_connection_failed、provider_rate_limited、provider_unavailable可重试；provider_authentication_failed、provider_model_not_found、provider_invalid_request、provider_invalid_response、provider_capability_unsupported、provider_json_stream_unsupported与未知错误不可盲重试。任务重试仍需原维护权限、版本与新运行请求协议，不代表SDK或本地推理可无限重试。该策略实验需在M4冻结开发集验证后才决定是否启用默认；当前.env不变、付费调用0。


## M4检索阶段独立配置

`RETRIEVAL_POLICY_JSON`填写根目录.env，空值保持已接受的默认。修改后重启API；正式持久run内部保存实际策略，公开API请求不允许浏览器任意覆盖服务端资源上限。非法JSON、未知字段、非整数数量、非有限权重及越界组合拒绝，不输出输入值。

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| dense_limit / sparse_limit | 20 / 20 | dense与learned sparse各自初召回数，后者不是BM25 |
| fusion_limit | 20 | 融合池上限 |
| rerank_limit | 20 | 实际送入本机重排的数量 |
| context_limit | 10 | 重排后允许参与字符预算的数量，最终可更少 |
| fusion | weighted | weighted / rrf / dense / learned_sparse |
| dense_weight / sparse_weight | 0.5 / 0.5 | Milvus加权融合参数，各0..1，不能同时为0 |
| rrf_k | 60 | Milvus RRF参数，1..16384 |

数量均1..1000，context_limit≤rerank_limit≤fusion_limit，融合池不超过所用初召回总量。所有分路共用组织/知识库/产品/冻结修订过滤，不从客户端接收过滤表达式。weighted保留Milvus原分数，rrf明确标为倒数排名分，不混成重排相关度。默认不提高候选量；清空配置可回切原加权策略。

固定dev检索网格入口为`.venv/Scripts/python.exe -m app.evaluation.retrieval_grid --dataset evals/datasets/support-v1-r2.jsonl --manifest evals/datasets/support-v1-r2-manifest.json --config evals/configs/retrieval-grid.yaml --output output/evals/support-v1-r2-retrieval-grid`。本机配置绑定实际源码/权重/prompt、题集接受结论和完整独立语料，源码变化必须另建新配置/输出，不改旧报告。网格只允许dev，答案供应商调用0，图/页来源命中不等同答案正确。查询嵌入按问题在同一进程共享，独立保存原编码时间；汇报检索/重排时间及含共享编码的估算时间，冷加载单列，非隔离性能结论。只读客户端不create_index或写run/消息；退出前再核完整语料。输出原始问题/检索正文留本机，不上传。


## M4证据扩展

`EVIDENCE_EXPANSION_JSON`在根目录.env可选，默认空/禁用，未确认dev收益前保持此值。可选enabled（严格布尔）、max_chars（1..12000，默认6000完整证据渲染字符）、max_added（0..20，默认4）、radius（0..2，默认1）、max_seeds（1..20，默认10）。修改后重启API；原基线评测显式禁用。非法值仅报变量名与用途，不打印JSON内容；不改实际.env。

启用后仅按同组织/kb/资料/修订/型号的明确父块与有限邻居读取，不递归整章。父块缺失/完整组越预算则省略后半块，避免丢前提；不同资料种子优先获得预算，随后才补可选邻居。元数据/原文/asset来源均保留；查询关系单独记expansion，不能称实际模型相关分。正式run内部保存expansion_policy/expansion_excluded/evidence_groups，公开API不新增任意范围参数。清空变量即可回切；字符预算沿用原兜底，最终token预算由M4-07接入，不把本项称完整token约束。

## M4完整提示词与输出预算

`ANSWER_BUDGET_JSON`填写根目录.env；空值使用context_window=32768、output_tokens=4096、reserve_tokens=256、max_chars=12000、output_token_field="max_tokens"。窗口256..2000000、输出1..262144、安全余量0..8192、字符0..12000，均严格整数，输出加余量须小于窗口。字段只允许max_tokens或max_completion_tokens；未知字段/非法JSON拒绝且不打印值。部署者须按所用供应商的真实模型窗口配置，默认值不代表已探测能力。修改后重启API，实际.env未改。

完整模板、型号、问题、历史和证据渲染后计数，再预留输出与协议余量。没有准确生成tokenizer时按每UTF-8字节1 token保守估计并记录utf8_bytes_upper_bound；该值不是供应商usage，安全余量用于消息封装。可内部注入实际token计数器，不新增浏览器参数。字符预算继续兜底，完整父子组不可拆，固定输入超过窗口在调用模型前失败prompt_budget_exceeded；无可用证据沿原正式入口返回资料不足，不强留首条。

输出上限经当前LangChain/OpenAI SDK的extra_body显式传送选定字段，同时保留原enable_thinking等供应商参数，不修改client字典；已用合成HTTP核对流/非流两字段，尚无新供应商真实调用。finish_reason=length/max_tokens时保留部分回答并在流/历史/final一致提示达到长度上限。引用白名单及asset/revision检查接正式QueryRunner；旧兼容节点共享预算/输出限制，但未宣称完成同等引用编号校验。
