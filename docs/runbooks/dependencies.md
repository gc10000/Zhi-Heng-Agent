# 交付依赖与CPU/GPU路径

2026-11-04。本机Windows 11 / Docker Desktop Linux容器。依赖基点和实际构建身份见[M7候选报告](../development/reviews/M7-delivery-first-r1.md)。不执行全量uv sync替换现有CUDA。

| 层 | 固定来源 | 本轮证据 |
| --- | --- | --- |
| API/worker/dispatcher | Python3.12 slim digest、deploy/api/requirements.lock全部传递依赖及hash | 独立Linux CPU轻量镜像安装和启动；无torch/FlagEmbedding |
| Vue构建 | .node-version=22.17.1，pnpm11.25.0，frontend/pnpm-lock.yaml | frozen install/typecheck/build；仅放行oxide/esbuild/vue-demi构建脚本 |
| 前端运行 | Nginx1.29固定digest | 仅静态资源、同源代理，无供应商配置 |
| 存储 | compose.delivery.yaml固定Mongo7/Milvus2.6.10/etcd3.5/Redis7 digest；MinIO固定源码、候选固定本地image ID（完整源码重建本轮未测） | 全新卷与随机命名空间；不使用课程数据 |
| 完整本机模型环境 | pyproject.toml + uv.lock；已有torch2.10.0+cu128、vision0.25.0+cu128、audio2.10.0+cu128 | 主环境只读保持；另建Windows CPU/GPU171包环境安装/导入通过，GPU设备可见；未加载权重 |

API轻量锁的更新方式（维护者变更依赖时重新审阅差异）：

```powershell
uv pip compile deploy/api/requirements.in --python-version 3.12 --python-platform x86_64-manylinux_2_28 --generate-hashes --no-emit-index-url -o deploy/api/requirements.lock
docker compose --env-file output/local-preview/runtime.env -f compose.delivery.yaml build api web minio
```

完整CPU/GPU模型宿主沿既有`uv.lock`及模型路径配置，不能在当前CUDA虚拟环境盲目`uv sync`。需要验证新GPU安装时，另建虚拟环境，先从锁文件导出除torch三件套外依赖，再明确从PyTorch cu128索引安装精确三件套并核`torch.version.cuda`/设备，最后核依赖一致性；本轮在Windows/Python3.12.7实际完成该路径的独立CPU/GPU安装与组件导入，不能外推成Linux安装通过。API CPU安装与完整模型依赖安装分别留证，均没有模型推理。

## Windows独立模型环境安装命令

在开发工作树导出共同依赖；新环境放在主仓库短路径output内，不能放在深层worktree/output下。已复现260字符Windows路径导致Transformers文件存在但常规open失败；不改系统注册表，不删除失败环境。以下只安装依赖、检查版本及导入，不加载权重/不执行推理。

```powershell
$m7Repo = Split-Path (git rev-parse --path-format=absolute --git-common-dir) -Parent
$m7InstallRoot = Join-Path $m7Repo 'output/m7i-new'
uv export --frozen --no-dev --no-emit-project --no-emit-package torch --no-emit-package torchvision --no-emit-package torchaudio --format requirements-txt -o output/model-dependencies-new.txt
uv venv --python (Join-Path $m7Repo '.venv/Scripts/python.exe') (Join-Path $m7InstallRoot 'cpu')
$m7CpuPython = Join-Path $m7InstallRoot 'cpu/Scripts/python.exe'
uv pip install --python $m7CpuPython --require-hashes --no-deps -r output/model-dependencies-new.txt
uv pip install --python $m7CpuPython --no-deps --require-hashes --index-url https://download.pytorch.org/whl/cpu -r deploy/model-host/windows-cpu.lock
uv pip check --python $m7CpuPython
& $m7CpuPython -c "import torch,torchvision,torchaudio,FlagEmbedding; print(torch.__version__,torch.version.cuda,torch.cuda.is_available())"
```

GPU使用另一个全新`gpu`目录，同样先安装共同依赖；三件套改为`--index-url https://download.pytorch.org/whl/cu128 -r deploy/model-host/windows-cu128.lock`，并核torch=2.10.0+cu128、vision=0.25.0+cu128、audio=2.10.0+cu128、torch.version.cuda=12.8及设备可见。两个torch lock只覆盖Windows x64/CPython3.12官方wheel，包含官方索引SHA256；不冒充Linux或其他Python版本锁。共同依赖用uv.lock导出完整hash，`--no-deps`防止通用索引替换已选CUDA构建；随后pip check不能省略。已有目标目录不得覆盖或复用，换新的短目录并保留失败。

容器向量与重排使用现有受token保护模型宿主：`MODEL_HOST_URL`、`MODEL_HOST_TOKEN`，只服务端设置。Windows容器地址为host.docker.internal，Linux为受防火墙限制的host-gateway。`/embeddings`和新增`/rerank`均复用原模型；重排normalize=True，返回分数数量/类型/有限值校验，拒绝重定向，不fallback下载。`/health/ready`只观察加载状态，不能唤起模型。

本轮预览生成关闭、宿主/供应商凭据为空，不下载或执行模型。Windows CPU/GPU安装已验证；文本供应商连通性/硬限、模型推理容量及目标Ubuntu主机仍无本轮证据。PyMuPDF与MinIO的AGPL义务及课程底座授权须在公开再分发前核清，见[许可](../../THIRD_PARTY_NOTICES.md)。

## operational-r1库存与许可候选

本包实际加载既有embedding模型完成5文本，未替换主CUDA/权重、未下载，rerank0；API新轻量镜像构建，web/MinIO复用既有固定身份。API锁105全部与实际106包匹配（额外基底pip），另有实际API Debian87包/copyright hash、前端许可索引及六份上游原文，见[候选库存](../development/releases/M7-operational-dependencies-r1.json)。Windows宿主177记录另存私有证据，不能代替API。7个API声明许可unknown、模型/课程底座及AGPL/SSPL义务仍open；不签完整SBOM或公开再分发批准。
