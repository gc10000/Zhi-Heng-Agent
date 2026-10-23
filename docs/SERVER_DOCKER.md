# Ubuntu 服务器基础服务部署与 Windows 调试

适用于 Ubuntu 22.04 / 24.04 及 Docker 官方仍支持的较新版本。当前方案：服务器运行 Milvus、etcd、MinIO、MongoDB，Windows 运行两个 FastAPI 服务及本地 BGE 模型，通过 SSH 隧道访问服务器基础服务。百炼与 MinerU 继续调用云端 API。

本文不表示已在你的服务器完成部署。当前仅核对镜像注册表、官方源码版本和 Compose 配置；实际构建、容器健康和数据读写需要在服务器执行后验证。

本机尝试 `docker build --check deploy/minio` 时，Docker Desktop 在访问 Docker Hub 基础镜像清单阶段网络超时，未进入编译，尚不能据此确认镜像构建成功。

## 1. 需要哪些镜像

| 服务 | 镜像 / 构建结果 | 用途 | 宿主机端口 |
| --- | --- | --- | --- |
| Milvus | `milvusdb/milvus:v2.6.10` | 产品主体和知识切片的稠密、稀疏向量索引 | `127.0.0.1:19530`；健康接口 `127.0.0.1:9091` |
| etcd | `quay.io/coreos/etcd:v3.5.25` | Milvus 元数据与协调服务 | 不发布 |
| MinIO | 本地构建 `product-knowledge-minio:2025-10-15` | Milvus 底层对象存储，以及应用上传的原文件和图片 | API `127.0.0.1:9000`；控制台 `127.0.0.1:9001` |
| MongoDB | `mongo:7.0` | 多轮问答的会话消息 | `127.0.0.1:27017` |

MinIO 构建还需拉取 `golang:1.24.8-bookworm` 和 `debian:bookworm-slim`，它们不作为额外常驻服务运行。编译器只在构建阶段使用。

**MinIO 镜像变化：**2026-10-21 核对时，原 `minio/minio:RELEASE.2025-04-22T22-12-26Z` 无法匿名拉取，Docker Hub 仓库查询返回 404；官方固定版本 README 已说明社区版采用源码分发。因此本项目从官方 `RELEASE.2025-10-15T17-29-55Z` 对应提交 `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a` 构建，保留原 LICENSE / CREDITS。这个版本用于当前联调，不代表已完成最新安全版本选型。首次构建需下载 Go 依赖，时间取决于网络和 CPU；服务器需能访问 Docker Hub、Quay、Go 模块代理与 Debian 软件源。

当前不用安装 Neo4j、Redis、Elasticsearch、MySQL 或本地 MinerU。图谱检索节点仍是占位实现，BGE 模型先在 Windows 本地推理。

小规模调试建议准备至少 4 核 CPU、8 GB 内存和 40 GB 可用 SSD，编译 MinIO 或后续同机运行两个 Python / BGE 服务时建议 16 GB 或更多；这属于容量建议，实际用量需监测。x86_64 CPU 应支持 AVX，MongoDB 7 与 Milvus 对 CPU 指令集有要求。

## 2. 在 Ubuntu 安装 Docker

以下代码块均在服务器 Bash 中执行。已有可用 Docker Engine 和 Compose 插件时可跳过安装。如果已经装过 `docker.io`、`containerd` 等发行版软件包，先按 Docker 官方文档处理冲突，不要混装两套 Docker。

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

使用 `sudo docker` 即可，不要求先把账号加入 docker 组。

## 3. 将部署文件复制到服务器

在 **Windows PowerShell** 中，把下面两个值替换为真实 SSH 用户名和服务器地址。之后的隧道命令复用这两个变量。

```powershell
$RagSshUser = '你的SSH用户名'
$RagServer = '你的服务器IP或域名'
ssh "${RagSshUser}@${RagServer}" 'mkdir -p ~/product-knowledge-rag/deploy'
scp 'D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/compose.yaml' "${RagSshUser}@${RagServer}:~/product-knowledge-rag/compose.yaml"
scp -r 'D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/deploy/minio' "${RagSshUser}@${RagServer}:~/product-knowledge-rag/deploy/"
```

若 SSH 使用密钥或自定义端口，请在上述命令添加实际参数；`ssh -p` 与 `scp -P` 的大小写不同。这里只上传基础设施定义，不需要把百炼 Key 或 MinerU Token 上传服务器。

## 4. 创建基础设施配置并启动

回到 **服务器 Bash**。第一次部署时执行下面命令，生成独立的 MinIO 账号和随机密码，保存在仅当前账号可读写的 `.env.infra` 中。**已有该文件时不要重复生成密码。**

```bash
cd ~/product-knowledge-rag
if [ ! -f .env.infra ]; then
  (umask 077
   printf '# MinIO 管理账号；应用和 Milvus 必须使用相同凭据。\nMINIO_ACCESS_KEY=ragadmin\nMINIO_SECRET_KEY=' > .env.infra
   od -An -N24 -tx1 /dev/urandom | tr -d ' \n' >> .env.infra
   printf '\n' >> .env.infra)
fi
chmod 600 .env.infra

# 校验配置，不输出展开后的密码。
sudo docker compose --env-file .env.infra config --quiet

# 拉取现成镜像；MinIO 使用下一条命令构建。
sudo docker compose --env-file .env.infra pull etcd milvus mongo
sudo docker compose --env-file .env.infra build minio

# 持久化数据保存到命名卷，容器自动随 Docker 服务恢复。
sudo docker compose --env-file .env.infra up -d --wait --wait-timeout 300
sudo docker compose --env-file .env.infra ps
```

首次构建若报镜像拉取超时或 Go 依赖下载失败，先处理服务器到对应仓库的网络；改模型 API Key 无法解决此类问题。部署目录名、Compose 项目名保持稳定，以便继续挂载原命名卷。

验证服务：

```bash
curl -fsS http://127.0.0.1:9000/minio/health/live
curl -fsS http://127.0.0.1:9091/healthz
sudo docker compose --env-file .env.infra exec -T etcd etcdctl endpoint health
sudo docker compose --env-file .env.infra exec -T mongo mongosh --quiet --eval 'db.adminCommand({ping: 1})'
```

MinIO 健康接口可能返回空响应体，以退出码 0 判断；MongoDB 应有 `ok: 1`。这些检查验证基础服务，仍需后续真实文档导入确认桶创建、Milvus 写入与查询都正常。

常用维护命令：

```bash
cd ~/product-knowledge-rag
sudo docker compose --env-file .env.infra logs --tail 100 milvus minio mongo
sudo docker compose --env-file .env.infra stop
sudo docker compose --env-file .env.infra up -d --wait --wait-timeout 300
```

`stop` 保留数据和容器配置。不要执行 `down -v`，它会删除数据库和对象存储的数据卷。

## 5. Windows 建立 SSH 隧道

Compose 只将端口绑定到服务器的 `127.0.0.1`，所以直接访问 `服务器公网IP:19530` 不会连接成功。保持此配置，通过 SSH 把本机端口转发到服务器：

在 **Windows PowerShell** 执行，命令保持单行：

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:19530:127.0.0.1:19530 -L 127.0.0.1:9000:127.0.0.1:9000 -L 127.0.0.1:9001:127.0.0.1:9001 -L 127.0.0.1:27017:127.0.0.1:27017 "${RagSshUser}@${RagServer}"
```

保持此终端打开，连接成功后不输出内容属于正常情况。云安全组只需允许你访问 SSH 端口，无需开放数据库和 MinIO 端口。若本机相同端口已被本地 Docker 容器占用，先停止对应容器，或者修改本地转发端口并同步修改 `.env`。

在另一 Windows 终端验证：

```powershell
Test-NetConnection 127.0.0.1 -Port 19530
Test-NetConnection 127.0.0.1 -Port 27017
Invoke-WebRequest http://127.0.0.1:9000/minio/health/live
```

MinIO 控制台：[http://127.0.0.1:9001](http://127.0.0.1:9001)，使用服务器 `.env.infra` 中的账号和密码登录。新版控制台可用功能以实际版本为准，桶和访问策略由项目 SDK 初始化。

## 6. 项目 .env 如何连接

编辑 **Windows 项目根目录的 `.env`**：

```dotenv
# 这些本机地址通过 SSH 隧道连接服务器，不是在 Windows 本地运行数据库。
MILVUS_URL=http://127.0.0.1:19530
MONGO_URL=mongodb://127.0.0.1:27017
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_SECURE=False

# 从服务器 .env.infra 本地查看并复制对应值，不要将密码发到聊天或提交 GitHub。
MINIO_ACCESS_KEY=ragadmin
MINIO_SECRET_KEY=填写服务器.env.infra中的MINIO_SECRET_KEY

# 同一个知识库继续使用这些名称，无需改成服务器地址。
MINIO_BUCKET_NAME=product-knowledge
MONGO_DB_NAME=product_knowledge_rag
CHUNKS_COLLECTION=product_knowledge_chunks
ITEM_NAME_COLLECTION=product_knowledge_items
```

服务器上可用 `nano .env.infra` 查看密码，再手动填入本地配置。不要用模板占位值替换真实密码。改完后重启两个 Python 服务，它们会在模块导入时初始化配置和客户端。

其他配置与数据库部署相互独立：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`LLM_DEFAULT_MODEL`、`VL_MODEL` 用于百炼；`MINERU_API_TOKEN` 用于 PDF 云端解析；BGE 模型路径和设备仍指向 Windows 本机。基础服务启动不代表这些 API 已配置或 RAG 链路已经验证。

当前 Milvus / MongoDB 没有启用数据库账号鉴权，依赖回环端口与 SSH 的访问控制。不要直接把端口绑定改成 `0.0.0.0` 后开放公网。若必须走服务器私网地址直连，需要另行配置监听地址、私网访问控制及对应鉴权；仅改 `.env` 无法让回环端口对远程主机可见。

## 7. 后续部署应用，哪些配置可以沿用

| 应用运行位置 | Milvus | MongoDB | MinIO API | 是否改地址 |
| --- | --- | --- | --- | --- |
| 当前 Windows + SSH 隧道 | `http://127.0.0.1:19530` | `mongodb://127.0.0.1:27017` | `127.0.0.1:9000` | 按本文填写 |
| 以后同一 Ubuntu 宿主机直接运行 Python | 与上行相同 | 与上行相同 | 与上行相同 | 这三项可不变，服务器无需 SSH 隧道 |
| 以后应用加入同一个 Compose 网络 | `http://milvus:19530` | `mongodb://mongo:27017` | `minio:9000` | 需要改；容器中的 localhost 指向容器自身 |

账号密码、数据库名、集合名、桶名可以继续使用；云端 API 配置通常也可以沿用。相对模型路径在服务器存在相同目录时可保留，但模型权重需要重新下载/复制，虚拟环境需在 Linux 重建，`cpu` / `cuda:0` 取决于服务器硬件与 PyTorch 安装。

**配图地址不能承诺原样沿用：**当前代码直接用 `MINIO_ENDPOINT` 生成图片链接，并把链接随切片写入知识库。通过隧道导入时会存入 `http://127.0.0.1:9000/...`，仅能被连着隧道的本机浏览器访问；公开部署后，其他用户的浏览器不能使用这个地址。容器服务名 `minio` 同样不能直接供外部浏览器访问。

正式上线应先确定稳定的图片域名和 HTTPS 入口，再将“内部 S3 连接地址”与“浏览器图片访问地址”拆成独立配置。当前原代码尚无该拆分，且 MinIO SDK 的 `secure=False` 是硬编码，不能只把 `MINIO_SECURE` 改为 `True` 就启用 HTTPS。后续修正这些配置后，已入库的旧图片地址需要更新，或重新导入测试文档。因此可以复用同一批数据库和数据卷，但无法保证所有应用配置与已入库 URL 永久不变。

## 官方参考与核对范围

- [Docker 官方 Ubuntu 安装](https://docs.docker.com/engine/install/ubuntu/)
- [Milvus v2.6.10 源码中的 standalone Compose](https://github.com/milvus-io/milvus/blob/v2.6.10/deployments/docker/standalone/docker-compose.yml)：etcd 版本参考该文件；其内容里的 Milvus 镜像仍为 2.6.9，本项目显式使用已在注册表核对存在的 2.6.10。
- [MinIO 固定版本 README 与源码分发说明](https://github.com/minio/minio/blob/RELEASE.2025-10-15T17-29-55Z/README.md)
- [MinIO 固定源码提交](https://github.com/minio/minio/commit/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a)

已核对 etcd / Milvus / MongoDB 及两个构建基础镜像的注册表清单；尚未在你的服务器执行镜像构建和启动。若 `up --wait` 失败，以容器日志判断原因，不能将静态配置校验等同于部署成功。
