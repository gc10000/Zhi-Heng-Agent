# 启动实测记录

> 2026-10-21 全量更新：原课程 85 份 PDF + 1 份 Excel 全部完成入库，逐来源与图片检查通过，详见 [全量导入记录](COURSE_IMPORT.md)。当前本机 BGE 使用 CUDA/FP16。


**最新结论：本机 Docker 四项服务健康，两个个人 API 凭据已填写并通过实际调用；3 页 PDF 完整导入、带图引用的流式问答、多轮追问、模糊/未知型号分支和非流式问答均已验收。** 当前入口为导入 8002、问答 8001，详见 [完整链路验收记录](E2E_VALIDATION.md)。下文按执行阶段保留历史状态，早期“待填凭据”“容器未启动”“业务代码未改动”等记录不代表当前状态。MCP 联网搜索仍缺配置。

日期：2026-10-21。首次验证时按 Windows 本机运行 Python 服务与模型、基础设施使用已有服务器准备；用户随后调整为先在 Windows 本机调试，基础设施改用项目的 Docker Compose，后续再部署服务器。

最新配置核对：Docker 引擎现已可访问，版本为 29.5.2，Compose 配置检查通过；本次核对尚未启动本项目的基础设施容器。`.env` 仍为正确的本机地址，两个个人 API 凭据待填写。

配置说明后续更新：`.env` 与 `.env.example` 已改为逐项中文注释；按官方文档将模板文本/视觉模型建议更新为 `qwen3.8-flash`，本地只更新仍为课程默认型号的值，已有凭据与自定义值保留。该更新未使用真实 Key 联调云端 API，不能沿用上文的本地验证结果宣称新型号已经可调用。`app/conf/` 中只修正了三处错误注释，业务代码未改动。

## 迁移范围

- `app/`、`prompts/`、`test/` 的源代码、HTML、提示词，以及 `pyproject.toml` / `uv.lock` 已迁移。
- 原业务源文件保持内容一致，未进行算法优化或更名式改写。
- 原作者 `.env`、历史日志、解析输出、课程教案及产品手册未复制。
- 已补充 `.gitignore`、无密钥 `.env.example`、本地 `.env`、来源说明及部署文档。模型、日志和输出目录均忽略。

## 已通过的检查

| 检查项 | 实测结果 |
| --- | --- |
| Python | 使用已安装的 Python 3.12.7 创建独立 `.venv`，系统默认 3.10 不用于本项目 |
| 依赖安装 | `uv sync --locked --python .venv/Scripts/python.exe` 成功，安装原锁文件的 158 个包 |
| 依赖一致性 | `.venv/Scripts/python.exe -m pip check` 返回 `No broken requirements found.` |
| PyTorch | `2.10.0+cpu`，CUDA 不可用；当前使用 CPU |
| 模型封装导入 | `BGEM3EmbeddingFunction` 及 `FlagReranker` 相关模块可导入 |
| 模型下载与校验 | 两个模型已下载到 `models/`；主权重大小与 ModelScope 元数据一致，SHA256 均通过校验 |
| BGE-M3 真实推理 | 生成 1024 维稠密向量和 11 个非零稀疏项；稠密向量 L2 范数 1.0；测试含初始化约 9.3 秒 |
| Reranker 真实推理 | 两个测试候选打分约 `0.8449` / `-9.4807`，相关候选排名在前；测试含初始化约 3.6 秒 |
| 导入服务 | Uvicorn 在 `127.0.0.1:8000` 启动成功 |
| 问答服务 | Uvicorn 在 `127.0.0.1:8001` 启动成功 |
| 导入页面 | `/import.html` 返回 HTTP 200，HTML 内容通过检查 |
| 问答页面 | `/chat.html` 返回 HTTP 200，HTML 内容通过检查 |
| API 文档 | 两个 `/openapi.json` 均返回 HTTP 200，包含预期业务路由 |
| 问答存活检查 | `/health` 返回 `{"ok":true}` |
| 导入状态接口 | `/status/migration-check` 返回预期任务结构 |
| 离线真实节点 | Markdown 入口路由、文档切分、RRF 对重叠候选的排序通过断言 |
| 语法及迁移对照 | 所有 Python 源文件 AST 解析通过；迁移源码与原源码一致 |
| 敏感值扫描 | 迁移源码、提示词、课程测试和新增文档未发现继承自原 `.env` 的长密钥值 |
| 可选 Compose | `docker compose config --quiet` 通过；未启动本机数据库容器 |

验证仅覆盖 HTTP 响应与内容，未进行浏览器视觉检查。

模型验证使用原应用的 `generate_embeddings()` 与 `get_reranker_model()`，CPU 推理，测试进程限制为两个 PyTorch 线程；上述耗时是小样本验证结果，不是正式性能评估。模型未加载到 FastAPI 服务进程中，将在首次实际业务调用时按原代码懒加载。

主权重 SHA256：

```text
models/bge-m3/pytorch_model.bin
b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38

models/bge-reranker-large/model.safetensors
c5ae4e262c60ed2fb507ec587358285377ec36ee0a2e6da029f0534272b06d36
```

## 仍需用户配置

在项目根目录 `.env` 中填写：

1. 本人 `OPENAI_API_KEY`，确认文本与视觉模型有调用权限。
2. 本人 `MINERU_API_TOKEN`，用于 PDF 云端解析。
3. 按 [Windows 本机 Docker 说明](WINDOWS_DOCKER.md) 准备镜像并启动基础服务；`MILVUS_URL` 保持本机回环地址。
4. `MINIO_ENDPOINT` 保持本机回环地址；账号密码由现有 `.env` 同时提供给 Compose 和 Python，确认专用 `MINIO_BUCKET_NAME`。
5. `MONGO_URL` 保持本机回环地址，确认 `MONGO_DB_NAME`。
6. 如需联网搜索，填写百炼 WebSearch 的 `MCP_DASHSCOPE_BASE_URL`。

具体格式、权限和现有客户端限制见 [CONFIGURATION.md](CONFIGURATION.md)。当前文件的本地服务地址属于模板默认值，不能作为服务器已经连通的证明。

两个模型的默认路径现已就绪，无需重新下载或填写原作者的路径。修改 `.env` 后需重启两个服务，现有进程不会自动刷新模块级配置与客户端实例。

## 本轮观察到的外部连接错误

- 原项目中两个 D 盘模型目录不存在，Milvus / MinIO / MongoDB 原地址 TCP 连接均失败。
- 本机 Docker Desktop Linux 引擎未运行；用户随后明确选择已有服务器，因此未继续部署本机数据库。
- 使用模板配置试启动时，MongoDB `127.0.0.1:27017` 拒绝连接；原模块捕获预初始化异常，服务可继续启动。
- 同次试启动时，MinIO 模板端点返回非预期的 HTTP 404，客户端未初始化成功；这不是 MinIO 就绪验证。
- 两个服务当前能启动，不代表文档导入、模型推理或数据库读写已经成功。

## 完整业务验收尚未执行

真实 PDF 导入 → MinerU 解析 → 图片理解与 MinIO 上传 → 主体/切片入 Milvus → MongoDB 多轮会话 → 检索精排 → SSE 回答，需要上述用户配置就绪后再验证。

原项目的 Neo4j 节点只有占位行为，不能据此宣称已完成知识图谱检索。

## Ubuntu 基础设施准备更新（2026-10-21）

- 用户确认服务器使用 Ubuntu 22.04 / 24.04 或更新版本，当前采用服务器基础服务 + Windows SSH 隧道方案。
- 新增 `docs/SERVER_DOCKER.md`，记录 Docker 安装、上传部署文件、生成基础服务凭据、启动验证、隧道命令与后续迁移配置。
- Compose 增加自动恢复策略；etcd 调整为 Milvus 官方示例中的 3.5.25。
- 原 MinIO Docker Hub 仓库无法匿名拉取，官方说明社区版改为源码分发，因此增加 `deploy/minio/Dockerfile`，使用固定官方提交及 Go 模块校验构建镜像。未换用未经核对的第三方镜像。
- 已通过 `docker compose config --quiet`，核对注册表中的 etcd / Milvus / MongoDB 与构建基础镜像，以及 MinIO 固定提交和模块版本；尚未实际构建此 MinIO 镜像或在用户服务器启动服务。
- 尝试本机 `docker build --check deploy/minio`，在获取 Docker Hub 基础镜像清单时因 Docker Desktop 直连网络超时退出，未进入编译阶段。Python HTTP 客户端可读注册表不代表 Docker 引擎具有相同的网络通路；本次不宣称 Dockerfile 构建验证通过。
- 本地 `.env` 仅更新中文注释，保留所有现有配置值与凭据，等待同步服务器 MinIO 凭据。

## 当前方案改回 Windows 本机（2026-10-21）

- 用户明确暂不处理服务器，Docker 基础服务也改在 Windows 本机运行。此前服务器方案仅作为历史记录保留，不是当前操作要求。
- 新增 `docs/WINDOWS_DOCKER.md`，README、配置说明、Compose 注释及 `.env` / `.env.example` 注释已切回本机方案；配置值及凭据未改动。
- 本次检查 Docker Engine 29.5.2 可访问，运行 Linux 容器，Compose 版本 v5.1.4；项目四项镜像尚未在本机准备，Compose 容器列表为空。
- 现有本机 `.env` 和模板均通过 `docker compose config --quiet`，文档相对链接检查通过。
- 尚未重新执行镜像拉取、MinIO 构建或容器启动；此前 Docker 访问镜像仓库的网络超时仍需在实际准备镜像时确认是否已解决。

## Docker Hub 拉取超时定位（2026-10-21）

- 用户执行 Compose pull 后，etcd 从 Quay 拉取成功；Milvus 在访问 Docker Hub 镜像清单阶段直连超时，MongoDB 被中断。
- 只读检查发现 Windows 系统代理为 `127.0.0.1:7890` 且端口监听正常；Docker Desktop 保存同一地址，但 `ProxyHTTPMode=disabled`。
- 相同仓库地址绕过代理直连出现 ConnectTimeout；显式使用本机代理，注册表入口返回正常鉴权挑战，鉴权接口返回 200，Milvus v2.6.10 与 MongoDB 7.0 镜像清单均返回 200。
- 已提供 Docker Desktop 手动代理设置步骤，未修改全局 Docker 设置或重启当前运行的其他项目容器；实际 Docker 镜像拉取、构建及业务验证仍待完成。

## Buildx 鉴权修复与本地基础服务就绪（2026-10-21）

- 用户后续构建在 `auth.docker.io/token` 请求超时。新检查确认 Desktop 已使用手动代理，Milvus 与 MongoDB 镜像也已拉取；Windows Buildx 鉴权请求仍需要终端代理。
- 仅在执行命令的 PowerShell 进程设置 `HTTP_PROXY` / `HTTPS_PROXY=http://127.0.0.1:7890` 后，`docker build --check deploy/minio` 通过，随后 `docker compose build minio` 实际完成，镜像为 `product-knowledge-minio:2025-10-15`。未修改系统环境变量或项目 API 代理。
- 发现其他项目 `ethreatssources-mcp-1` 占用 Windows 9000，因此给 Compose 增加可配置的 `MINIO_API_PORT`；本地 `.env` 和模板设为 19000，`MINIO_ENDPOINT` 同步为 `127.0.0.1:19000`。未停止其他项目，未修改 MinIO 凭据。容器间仍使用 `minio:9000`。
- `docker compose up -d --wait --wait-timeout 300` 返回退出码 0；随后 `compose ps` 显示 etcd、MinIO、Milvus、MongoDB 四个容器均为 healthy。
- Windows Python 使用现有 `.env` 实测：MinIO 19000 健康接口和 Milvus 9091 健康接口均 HTTP 200；MongoDB SDK ping 成功；MinIO 建专用桶、写入/读取临时对象及清理成功；Milvus SDK 连接并列出集合成功，当前集合为空。
- 基础设施已就绪，完整 PDF 导入、知识索引、云端模型与流式问答仍未验收。其他项目还占用宿主机 8000，后续启动导入服务需另行处理该端口冲突，不能直接重复启动占用同端口的进程。

## 用户填写凭据后的实际检查（2026-10-21）

- `OPENAI_API_KEY` 与 `MINERU_API_TOKEN` 已填写；未展示或更改凭据。用户将模型地址设为第三方 OpenAI 兼容接口 `https://maas.qianwenaiapi.com/compatible-mode/v1`，本次按该实际地址验证，不视为阿里云官方直连验证。
- 使用项目原 `get_llm_client()`，保留 `enable_thinking=false`，仅给测试请求限制超时、重试和输出长度：`qwen3.8-flash` JSON Object 输出可解析，且断言 `ok=true` 通过；流式响应收到 5 个块，拼接内容为 `OK`。
- 使用项目相同的多模态客户端，对本地生成的纯红色测试图片发送 data URL 输入，`VL_MODEL=qwen3.8-flash` 回答“红”，视觉输入验证通过。
- MinerU 使用用户 Token 请求 v4 `/file-urls/batch`，`model_version=vlm`，成功返回业务码 0、批次标识和上传凭证。未上传文件、未执行实际 PDF 解析，因此尚未验证解析额度、耗时、结果 ZIP 下载和后续文档处理。
- MongoDB SDK ping、Milvus SDK 列出集合、MinIO 凭据及专用桶访问通过；Compose 显示四项基础服务均 healthy。Milvus 当前没有集合，尚无已导入知识。
- 本地两个模型目录与权重存在，设备仍为 CPU；本次未重复进行此前已完成的模型推理检查。
- `MCP_DASHSCOPE_BASE_URL` 仍为空，联网搜索未验证；第三方模型 Key 不能据此推断有百炼 MCP 服务权限。
- 导入服务默认 8000 仍被其他项目占用，页面 API_BASE 也硬编码为 8000；本次只检查配置，没有修改页面、应用端口或停止其他项目。两个 Python API 当前没有在 8001/8002 监听。
- 不含密钥的逐项结果保存在忽略目录 `output/config-research/config-validation.json`。此次结论为核心配置可调用，尚不是 PDF 导入至 RAG 回答的完整链路验收。

## 真实 PDF 与完整业务链路验收（2026-10-21）

- 使用原 H3C LA2608 手册第 4—6 页（3 页约 124 KiB）执行真实 PDF 导入，最终 1 个产品主体、4 个知识切片、4 张图示摘要和图片，任务 completed；重复导入后数量稳定。
- 修复实测阻塞：导入页面写死 8000 改为同源，使用 8002；MinIO URL 缺少路径分隔符改为正确拼接并编码对象名；答案提示词补引用要求；未知/模糊型号助手消息改为输出节点统一写入，避免重复。
- SSE 明确型号问答与同会话指代追问通过：答案增量等于 final，引用切片存在，配图 GET 成功，追问准确给出 display wlan ap / R/M，MongoDB 两轮为四条记录。未知型号拒答一轮两条，非流式模糊型号澄清一轮两条，非流式明确型号检索回答通过。
- 用 Edge headless 真实加载页面验证 API 状态、历史、引用、图片和导入同源地址，截图位于 `output/e2e/chat-page.png`。
- Python AST、两页 JavaScript 语法、Compose 配置检查通过；未展示密钥，原课程目录未修改。两个 API 保持运行（导入 8002、问答 8001）。
- MCP 联网地址仍为空，实际联网分支未验收；Neo4j 为占位。详见 [完整链路验收记录](E2E_VALIDATION.md)。
