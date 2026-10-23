# Windows 本机 Docker 调试

当前全部在 Windows 本机调试：FastAPI 和两个 BGE 模型在 Windows Python 虚拟环境中运行；Milvus、etcd、MinIO、MongoDB 在 Docker Desktop 的 Linux 容器中运行。百炼和 MinerU 仍使用云端 API。无需服务器地址、SSH 隧道或额外 `.env.infra`。

## 1. Docker Desktop

本机已经安装 Docker Desktop，2026-10-21 检查显示 Linux 引擎可访问。若以后重新安装，使用 [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) 并启用 WSL 2 后端；确认使用 Linux containers。

建议给 Docker 可用内存预留至少 8 GB，整机同时运行 BGE 和两个 Python 服务建议有 16 GB 或更多内存。WSL 2 后端的 CPU / 内存上限按 Docker Desktop 对 WSL 2 的资源配置方式设置，不能仅依赖 Hyper-V 模式的资源滑块。镜像、Go 构建缓存、模型及文档会占用较多空间，建议预留数十 GB 磁盘。

所有后续命令在 PowerShell 的项目根目录执行：

```powershell
Set-Location 'D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag'
docker info --format '{{.OSType}}'
docker compose version
```

第一条检查应输出 `linux`。如果 Docker 引擎不可达，先启动 Docker Desktop 并等待引擎就绪。

## 2. 需要准备的镜像

| 角色 | 镜像 | 用途 |
| --- | --- | --- |
| 向量数据库 | `milvusdb/milvus:v2.6.10` | 产品主体及知识切片的稠密、稀疏检索 |
| Milvus 依赖 | `quay.io/coreos/etcd:v3.5.25` | 保存 Milvus 元数据，无需在应用中填连接地址 |
| 会话数据库 | `mongo:7.0` | 保存多轮问答消息 |
| 对象存储 | 本地构建 `product-knowledge-minio:2025-10-15` | 保存原文件、图片与 Milvus 对象数据 |

MinIO 构建额外需要 `golang:1.24.8-bookworm` 和 `debian:bookworm-slim` 两个基础镜像，它们不会作为额外常驻服务运行。Compose 已配置好依赖、网络、端口和持久化卷，不需要逐个手写 `docker run`。

2026-10-21 核对时，原 MinIO Docker Hub 镜像无法匿名拉取，官方说明社区版改为源码分发，所以使用 `deploy/minio/Dockerfile` 从固定官方提交构建。首次构建需下载 Go 依赖，耗时取决于网络、CPU 和磁盘。本机现已完成构建、四项服务健康检查和 Windows SDK 连接验证，详见 `STARTUP_STATUS.md`。

当前无需 Redis、MySQL、Elasticsearch、Neo4j、Ollama 或本地 MinerU 镜像。BGE 已下载在项目 `models/` 中，由 Python 加载。

## 3. 本地 .env

现有 `.env` 已有本机地址和随机 MinIO 密码，保留即可。不要再次用 `.env.example` 覆盖现有 `.env`。

```dotenv
# Windows Python 通过 Docker 发布到本机的端口连接容器。
MILVUS_URL=http://127.0.0.1:19530
MONGO_URL=mongodb://127.0.0.1:27017
MONGO_DB_NAME=product_knowledge_rag

# S3 API 地址不带协议；本机使用19000避开其他项目，9001 是控制台。
MINIO_ENDPOINT=127.0.0.1:19000
MINIO_API_PORT=19000
MINIO_SECURE=False
MINIO_ACCESS_KEY=raglocal
# MINIO_SECRET_KEY：保留现有 .env 中已生成的密码，此处不展示。
MINIO_BUCKET_NAME=product-knowledge

CHUNKS_COLLECTION=product_knowledge_chunks
ITEM_NAME_COLLECTION=product_knowledge_items
```

Compose 用 `.env` 中的 MinIO 账号密码创建服务，Python 应用读取同一份配置连接，因此不需要手动到控制台再建同名账号。存储桶由应用初始化创建，无需提前手工创建。

你需要自行填写的云端凭据是 `OPENAI_API_KEY` 和 `MINERU_API_TOKEN`，并确认 `LLM_DEFAULT_MODEL` / `VL_MODEL` 在账号中可调用；`MCP_DASHSCOPE_BASE_URL` 可留待联网搜索联调。无需把密钥发到聊天里。

本地模型保持 `BGE_M3_PATH=./models/bge-m3`、`BGE_RERANKER_LARGE=./models/bge-reranker-large`，设备先用 `cpu`，两个 FP16 设置保持 `0`。

## 4. 准备镜像与启动

依次执行，每条成功后再继续：

```powershell
docker compose config --quiet
docker compose pull etcd milvus mongo
docker compose build minio
docker compose up -d --wait --wait-timeout 300
docker compose ps
```

`config --quiet` 没有输出且退出码为 0 表示配置语法通过。最后应看到四项服务正常运行，健康状态为 `healthy`。

Dockerfile 构建时会拉取两个基础镜像，无需手动拉取或在 Windows 安装 Go。若构建失败，先读具体错误：本机此前在 Docker Hub 基础镜像清单请求阶段遇到网络超时，尚未进入编译。浏览器可以联网不代表 Docker 引擎可以访问仓库；如果使用代理，需要在 Docker Desktop 的代理设置中配置实际可用的代理。镜像仓库访问失败与模型 API Key 无关。

### 本机已定位的 Docker Hub 超时

2026-10-21 排查确认：Windows 系统代理为 `127.0.0.1:7890`，该端口有进程监听；Docker Desktop 虽保存了该代理地址，但代理模式是禁用。绕过代理直连 Docker Hub 超时，通过该代理可成功读取 Milvus 和 MongoDB 镜像清单（HTTP 200）。

在 Docker Desktop 打开 **Settings → Resources → Proxies**（版本不同也可在设置中搜索 `proxy`），启用 **Manual proxy configuration**，HTTP 和 HTTPS 两栏均填写 `http://127.0.0.1:7890`，保存并应用。HTTPS 栏使用 `http://` 表示连接本地 HTTP 代理后转发 HTTPS 请求。不要把 Docker Hub 加入代理排除列表；本机和容器网络的排除项按现有配置保留。应用设置若要求重启，会短暂影响其他正在运行的 Docker 容器。

保持代理软件运行，然后重新执行 `docker compose pull etcd milvus mongo`。Docker Desktop 的代理负责引擎的网络请求；Buildx 在 Windows 客户端获取 Docker Hub 鉴权令牌时，还可能需要当前 PowerShell 进程的代理设置。

本机后续检查确认 Docker Desktop 已切到手动代理，Milvus 和 MongoDB 镜像已存在，但 `docker compose build minio` 仍在 `auth.docker.io/token` 超时。在当前终端设置下面两项后，`docker build --check deploy/minio` 已成功，且实际构建已越过鉴权阶段开始下载基础镜像：

```powershell
# 仅影响当前 PowerShell 及它启动的程序，关闭终端后失效。
$env:HTTP_PROXY = 'http://127.0.0.1:7890'
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
docker compose build minio
```

以上变量不要写入项目 `.env`。代理地址应以本机实际代理端口为准；本机已验证的是 7890。构建容器内部执行 `go install` 或 `apt-get` 又属于另一条网络路径，如果后续在这些步骤报错，需要依据具体错误排查，不能将鉴权恢复等同于整个镜像构建成功。

本机本轮实际构建最终成功，四个容器均为 healthy；MinIO 对象读写与 MongoDB / Milvus SDK 连接也已验证。关闭 PowerShell 不会停止这些容器，无需反复构建。

本机 9000 已被 ethreatssources-mcp-1 占用，所以本项目已通过 MINIO_API_PORT=19000 发布到 19000，MINIO_ENDPOINT 同步指向该端口。容器内部端口仍为 9000，不影响 Milvus 与 MinIO 的容器间连接。若其他端口冲突，同样先识别占用来源，不要直接结束不明进程。

## 5. 检查服务并运行 Python

```powershell
Invoke-WebRequest http://127.0.0.1:19000/minio/health/live
Invoke-WebRequest http://127.0.0.1:9091/healthz
docker compose exec -T etcd etcdctl endpoint health
docker compose exec -T mongo mongosh --quiet --eval 'db.adminCommand({ping: 1})'
```

MinIO 控制台地址为 [http://127.0.0.1:9001](http://127.0.0.1:9001)，登录使用 `.env` 的 `MINIO_ACCESS_KEY` 与 `MINIO_SECRET_KEY`。新版控制台功能以实际版本为准。

在项目根目录分别打开两个 PowerShell 终端。已经运行的旧 Python 服务应先在原终端按 Ctrl+C 停止，避免端口冲突，并让客户端在 Docker 就绪后重新初始化。

```powershell
# 终端一：文档导入
.venv/Scripts/python.exe -m uvicorn app.import_process.api.file_import_service:app --host 127.0.0.1 --port 8002
```

```powershell
# 终端二：检索问答
.venv/Scripts/python.exe -m uvicorn app.query_process.api.query_service:app --host 127.0.0.1 --port 8001
```

- 导入页面：[http://127.0.0.1:8002/import.html](http://127.0.0.1:8002/import.html)
- 聊天页面：[http://127.0.0.1:8001/chat.html](http://127.0.0.1:8001/chat.html)

健康检查只能确认基础服务。本机另外已完成真实 PDF 导入、带图引用问答、多轮会话和浏览器验收，见 [完整链路验收记录](E2E_VALIDATION.md)。

## 6. 日常启停

```powershell
# 查看日志
docker compose logs --tail 100 milvus minio mongo

# 停止容器，保留数据
docker compose stop

# 下次启动，无需重新下载和编译已存在的镜像
docker compose up -d --wait --wait-timeout 300
```

数据保存在 Docker 命名卷，普通启停不会清空。不要执行 `docker compose down -v`，它会删除数据卷；Docker Desktop 的清理/恢复出厂设置也可能删除数据。
