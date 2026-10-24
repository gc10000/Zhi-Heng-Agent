# Product Knowledge RAG

> 正在将课程底座演进为“设备技术支持与知识工作台”。M0、M1、M2、M3已通过总控审查。M3交付Vue 3工作台：登录、设备/会话、持久流式问答、图文来源与PDF定位、资料导入及修订管理；第二轮复审已关闭缓存会话恢复与跨页设备选择问题。[前端运行说明](frontend/README.md)、[M3第二轮总控审查](docs/development/reviews/M3-review-r2.md)、[完整优化计划](docs/plans/2026-10-22-technical-support-optimization.md)与[可视化路线图](docs/brainstorming/2026-10-22/support-plan.html)。

> 开发以[总清单](docs/plans/DEVELOPMENT_TODO.md)、[进度](docs/development/PROGRESS.md)和[阶段审查](docs/development/REVIEW_STATUS.md)为准。M3第二轮独立346后端、37前端单元、24离线浏览器、既有3项与真实产物只读8检查通过，本轮付费0；M3 11/11、核心43/76。授权从M4-01开始连续完成M4-10，先冻结题集/划分并跑基线，M5及后续未授权。新接口见[API v1](docs/architecture/api-v1.md)，旧公开导入/查询入口仍保留原链路。

> 原课程全部产品资料已完成入库：85 份 PDF + 1 份 Excel，6,612 个切片。范围、验证与续传记录见 [全量导入记录](docs/COURSE_IMPORT.md)。


面向设备技术支持与运维文档的知识问答系统。以培训配套「掌柜智库 RAG」代码为基础，保留课程来源及原知识数据，逐阶段增加可追溯和可恢复能力。

来源与授权情况见 [NOTICE.md](NOTICE.md)。

## 当前结构

```text
app/
  import_process/       # FastAPI 导入服务、上传页面、导入 LangGraph
  query_process/        # FastAPI 问答服务、聊天页面、检索 LangGraph
  clients/              # Milvus / MinIO / MongoDB 客户端等
  conf/                 # 环境变量配置
  lm/                   # 文本/视觉 LLM、嵌入、重排
  tool/                 # 原课程模型下载示例（含旧机器路径，勿直接运行）
  utils/                # SSE、任务状态、路径及格式工具
prompts/                # 原课程提示词
test/                   # 原课程手工测试脚本，部分需要真实 API / 模型 / 数据
docs/CONFIGURATION.md   # 配置项、缺项和服务器要求
docs/WINDOWS_DOCKER.md  # 当前使用：Windows 本机 Docker 调试步骤
docs/SERVER_DOCKER.md   # Ubuntu Docker 部署、SSH 隧道及后续迁移说明
docs/STARTUP_STATUS.md  # 本轮实测结果及阻塞项
docs/E2E_VALIDATION.md  # 真实 PDF 导入、问答、配图与会话验收记录
.env.example            # 可提交的配置模板
.env                    # 本地真实配置，已忽略，不提交
compose.yaml            # 本地或服务器 Milvus / MinIO / MongoDB / etcd
deploy/minio/           # 基于官方固定源码构建 MinIO 镜像
```

原课程 85 份 PDF 和 1 份 Excel 已复制到本机 `doc/`，全部完成知识库导入；文件、解析缓存和派生图片按现有规则忽略。课程教案和历史日志未纳入运行项目。完整范围与验证结果见 [全量导入记录](docs/COURSE_IMPORT.md)。

## 1. 准备 Python 环境

推荐 Python 3.12。原依赖文件标注 Python >=3.11，但其中 NumPy >=2.4.3 与 Pandas >=3.0.1 实际要求 Python >=3.11，使用已安装的 3.12 可避免系统默认 3.10。

在项目根目录执行 PowerShell：

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install uv
uv sync --locked --python .venv/Scripts/python.exe
```

如果 uv 命令未在 PATH 中，但安装到了上述虚拟环境，也可以用 `.venv/Scripts/uv.exe` 替代 `uv`。

如果 uv 未加入 PATH，但已通过官方安装器安装，可以使用：

```powershell
& "$env:USERPROFILE/.local/bin/uv.exe" sync --locked --python .venv/Scripts/python.exe
```

原 `pyproject.toml` 与 `uv.lock` 先按课程版本保留。安装过程中可能涉及 PyTorch 等大文件，实际兼容性结论以 [启动记录](docs/STARTUP_STATUS.md) 为准。

## 2. 填写配置

本次迁移已生成本地 `.env`。若在新机器上使用，先执行：

```powershell
Copy-Item .env.example .env
```

按 [配置说明](docs/CONFIGURATION.md) 填写个人百炼 Key、MinerU Token。当前全部在 Windows 本机调试，按 [本机 Docker 说明](docs/WINDOWS_DOCKER.md) 启动基础服务；连接地址保留 `127.0.0.1`，MinIO 账号密码由同一份 `.env` 提供给应用与 Compose。

## 3. 下载两个本地模型

本次迁移已下载模型到 `.env` 的默认目录，并完成真实推理验证。若在新机器重新准备，在项目根目录执行以下命令。所需主权重合计约 4.5 GB，需要可用的网络与磁盘空间。

```powershell
.venv/Scripts/modelscope.exe download --model BAAI/bge-m3 --local_dir ./models/bge-m3 --include '*.json' '*.model' '*.pt' 'pytorch_model.bin' '1_Pooling/*' 'README.md'
.venv/Scripts/modelscope.exe download --model BAAI/bge-reranker-large --local_dir ./models/bge-reranker-large --include '*.json' '*.model' 'model.safetensors' 'README.md'
```

也可以使用已有完整模型目录，直接修改 `.env` 中的两个路径。下载后先使用 CPU 和 FP32 验证。

## 4. 启动两个服务

确认配置和外部服务就绪后，在项目根目录分别打开两个终端：

```powershell
# 终端一：导入
.venv/Scripts/python.exe -m uvicorn app.import_process.api.file_import_service:app --host 127.0.0.1 --port 8002
```

```powershell
# 终端二：问答
.venv/Scripts/python.exe -m uvicorn app.query_process.api.query_service:app --host 127.0.0.1 --port 8001
```

- 导入页面：[http://127.0.0.1:8002/import.html](http://127.0.0.1:8002/import.html)
- 聊天页面：[http://127.0.0.1:8001/chat.html](http://127.0.0.1:8001/chat.html)
- 导入 API：[http://127.0.0.1:8002/docs](http://127.0.0.1:8002/docs)
- 问答 API：[http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

使用单个 worker，原项目的任务状态和 SSE 队列保存在进程内。请从项目根目录运行，保证相对模型路径可解析。

## 5. 验证完整链路

1. 导入一份小型 PDF，观察 `/status/{task_id}` 最终是否为 `completed`。
2. 在 Milvus 检查主体集合与切片集合是否有实际数据。
3. 在聊天页使用该文档的明确产品型号提问，检查 SSE 增量、来源与配图。
4. 使用同一会话追问，检查 MongoDB 历史记录与指代处理。

问答 `/health` 只返回进程状态。当前已通过 3 页 PDF 的真实导入、检索问答、配图和多轮会话验证，详见 [完整链路验收记录](docs/E2E_VALIDATION.md)；MCP 联网分支仍缺服务配置。

## 本机 Docker 基础设施

当前使用 Windows 本机 Docker Desktop，详细步骤见 [本机 Docker 说明](docs/WINDOWS_DOCKER.md)。确认 Linux 引擎运行，在项目根目录执行：

```powershell
docker compose config --quiet
docker compose pull etcd milvus mongo
docker compose build minio
docker compose up -d --wait --wait-timeout 300
docker compose ps
```

该部署仅绑定回环地址，数据保存在 Docker 命名卷。MinIO 控制台为 [http://127.0.0.1:9001](http://127.0.0.1:9001)，本机 API 端口为 19000（容器内部为 9000），避开其他项目占用。

## M0 开发验证与兼容变化（2026-10-23）

在项目根目录执行 `.venv/Scripts/python.exe -m pytest tests/unit tests/contract -q`，默认离线，使用当前用例注入的 fake，不读真实配置或调用服务。既有重导入回归执行 `.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q`。当前 GPU 环境仅补装 pytest 开发依赖；不要直接全量同步通用依赖锁，详见 [配置说明](docs/CONFIGURATION.md)。

旧问答非流式失败现在返回 HTTP 502、`status=failed` 与 `partial_answer`；流式生成失败仅发送 error，成功在整图返回后发送唯一 final。历史 limit 小于 1 返回 422。旧进程内单 worker 限制仍适用。

以下M0状态为历史时点，当前状态以上方进度与阶段审查为准。上文完整链路记录属于历史验证。M0当时01–09已通过[第三轮总控审查](docs/development/reviews/M0-review-r3.md)，授权进入M1，尚未实现M1能力；原部分交付保留于[M0原提交](docs/development/reviews/M0-submission.md)。实际命令、证据与验证边界见[M0-09](docs/development/records/M0-09.md)。

总控已在第2轮接受同名章节身份与图片验收的离线修复，[第2轮提交](docs/development/reviews/M0-submission-r2.md)保留。Docker恢复后仅续验R3，准确拓扑真实HTTP/hash/完整解码/正文final关联、正常配置新进程冷启动均通过；原图片业务失败本次未复现，原因仍未知。总控独立105项、既有3项回归及真实图片只读复核通过，接受冷启动证据，见[第3轮审查结论](docs/development/reviews/M0-review-r3.md)。审查工具需显式--spec选取提交证据，使用方法见[配置与运行说明](docs/CONFIGURATION.md)。M1已授权，阶段末另审，不代表全量迁移或公开发布获准。
