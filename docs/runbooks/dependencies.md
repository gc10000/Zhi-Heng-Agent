# 交付依赖与CPU/GPU路径

2026-11-04。本机Windows 11 / Docker Desktop Linux容器。依赖基点和实际构建身份见[M7候选报告](../development/reviews/M7-delivery-first-r1.md)。不执行全量uv sync替换现有CUDA。

| 层 | 固定来源 | 本轮证据 |
| --- | --- | --- |
| API/worker/dispatcher | Python3.12 slim digest、deploy/api/requirements.lock全部传递依赖及hash | 独立Linux CPU轻量镜像安装和启动；无torch/FlagEmbedding |
| Vue构建 | .node-version=22.17.1，pnpm11.25.0，frontend/pnpm-lock.yaml | frozen install/typecheck/build；仅放行oxide/esbuild/vue-demi构建脚本 |
| 前端运行 | Nginx1.29固定digest | 仅静态资源、同源代理，无供应商配置 |
| 存储 | compose.delivery.yaml固定Mongo7/Milvus2.6.10/etcd3.5/Redis7 digest；MinIO固定源码、候选固定本地image ID（完整源码重建本轮未测） | 全新卷与随机命名空间；不使用课程数据 |
| 完整本机模型环境 | pyproject.toml + uv.lock；已有torch2.10.0+cu128、vision0.25.0+cu128、audio2.10.0+cu128 | 只读盘点，未重新安装、未加载权重；不称GPU安装通过 |

API轻量锁的更新方式（维护者变更依赖时重新审阅差异）：

```powershell
uv pip compile deploy/api/requirements.in --python-version 3.12 --python-platform x86_64-manylinux_2_28 --generate-hashes --no-emit-index-url -o deploy/api/requirements.lock
docker compose --env-file output/local-preview/runtime.env -f compose.delivery.yaml build api web minio
```

完整CPU/GPU模型宿主沿既有`uv.lock`及模型路径配置，不能在当前CUDA虚拟环境盲目`uv sync`。需要验证新GPU安装时，另建虚拟环境，先从锁文件导出除torch三件套外依赖，再明确从PyTorch cu128索引安装精确三件套并核`torch.version.cuda`/设备，最后核依赖一致性；未实际执行该路径前不宣称可复现。完整CPU模型路径同样须独立环境验证，API CPU安装不能替代模型CPU安装。

容器向量与重排使用现有受token保护模型宿主：`MODEL_HOST_URL`、`MODEL_HOST_TOKEN`，只服务端设置。Windows容器地址为host.docker.internal，Linux为受防火墙限制的host-gateway。`/embeddings`和新增`/rerank`均复用原模型；重排normalize=True，返回分数数量/类型/有限值校验，拒绝重定向，不fallback下载。`/health/ready`只观察加载状态，不能唤起模型。

本轮预览生成关闭、宿主/供应商凭据为空，不下载或执行模型。文本供应商连通性/硬限、GPU安装、完整CPU模型安装及目标Ubuntu主机仍无本轮证据。PyMuPDF与MinIO的AGPL义务及课程底座授权须在公开再分发前核清，见[许可](../../THIRD_PARTY_NOTICES.md)。
