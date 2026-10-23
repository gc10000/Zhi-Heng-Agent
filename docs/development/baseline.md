# M0 环境与数据保护基线

日期：2026-10-22。实测证据：`evidence/M0-01-environment.json`。本目录没有 Git 仓库，不初始化、不推送；原代码备份在 `evidence/originals/`，不含 .env、知识原件、模型或解析缓存。

Python 3.12.7；PyTorch 2.10.0+cu128，CUDA 12.8 可用；RTX 4050 Laptop。完整依赖版本及现有 API 路由见 JSON。历史 86 份课程资料/6612 切片属于既有记录，本次未重新统计或导入。

本次直接调用 SDK 只读列举：Mongo chat_message；Milvus product_knowledge_items/product_knowledge_chunks；MinIO a-bucket/product-knowledge。没有调用应用的 MinIO 初始化，没有创建索引、修改桶策略或写原数据。

独立验证命名空间：Mongo m0_test_20261022；Milvus m0_test_20261022_chunks 和 m0_test_20261022_items；MinIO 复用桶但对象仅允许 m0-test/20261022/ 前缀。测试脚本运行前强制检查独立名称；不清理原集合/桶，不对生产注入故障。

配置仅记录名称与存在性。缺失 ENTITY_NAME_COLLECTION、NEO4J_URI/USERNAME/PASSWORD、MCP_DASHSCOPE_BASE_URL、PROJECT_ROOT：分别为预留集合、未使用图谱、可选联网、可选路径覆盖；均不阻塞 M0 本地知识链路。若需启用，填写根目录 .env；M0 不启用这些能力。

禁止直接 uv sync 当前 GPU 环境：锁文件依赖不代表当前 CUDA 构建；开发工具仅安装 pytest 及其必要依赖并保存安装前后 torch 版本。模型不升级、不下载。

## M0-09实际小样与R3验收（2026-10-23）

上文是初始命名方案，实际已建立且持续复用：Mongo数据库 `m0_test_20261022_213750_933c22`（chat_message）；Milvus集合 `m0_test_20261022_213750_933c22_chunks`（4切片）与 `_items`（完整名同前缀，1主体）；MinIO对象前缀 `m0-test/20261022_213750_933c22/`（4对象）。原课程数据、缓存与桶策略不变。R3无新增导入/对象上传，原会话历史5→7，新冷启动会话0→2；只读HTTP复核无写入。

R3真实图片/正常配置新进程冷启动通过，总控独立105+3回归及真实图片只读复核通过，接受冷启动证据；M0第3轮总控通过，M1已授权。设备/线程/耗时、准确图hash与实际退出码见 `evidence/M0-r3-cold-first.json`、`evidence/M0-r3-live-image-verified-final.json`、`evidence/M0-r3-validation.json`，审查边界见 `reviews/M0-review-r3.md`。无环境/依赖升级；旧失败保留，不声称原异常根治或性能改进。
