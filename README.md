# 知衡 · Zhi-Heng

设备技术支持与知识工作台。Vue 3 / TypeScript、FastAPI / LangGraph、MongoDB、Milvus、MinIO、Redis / Celery；基于课程底座演进，来源和再分发限制见[NOTICE](NOTICE.md)、[第三方许可](THIRD_PARTY_NOTICES.md)、[复用映射](docs/reuse/manifest.json)。

当前交付为**内部预览候选**：应用镜像、同源入口、持久Run/SSE、受控引用与PDF定位、资料修订、用户确认草稿和待审反馈。新生成在本轮预览中明确关闭；工程合成流程不代表真实模型答案。对象边界、操作顺序、数量限定及引用消费的质量债务仍存在，不能用于无人核对的操作指引。

## 运行

按[快速开始](docs/runbooks/quickstart.md)用scripts/operations/preview.py一次生成随机配置、构建并启动独立项目。无需课程PDF或真实供应商凭据，不下载模型、不触碰旧数据。Windows使用主仓库现有Python，不全量sync替换CUDA。前端只访问同源入口；密码仅在本机私有配置，可通过copy-password复制。

- [实际候选、入口与证据限制](docs/development/reviews/M7-delivery-first-r1.md)
- [依赖与CPU/GPU路径](docs/runbooks/dependencies.md) · [同源部署与回滚](docs/runbooks/ubuntu-deploy.md)
- [备份/独立恢复](docs/runbooks/backup-restore.md) · [故障处理](docs/runbooks/failure-recovery.md)
- [演示路径](docs/demo/scenarios.md) · [配置](docs/CONFIGURATION.md) · [贡献](CONTRIBUTING.md)

## 验证边界

M0至M5既有验收保持。M6当前5/7，04保持，05缺有效真实反馈proof，08缺有效新候选完整质量及阶段证据；原168真实stream/170结果/340判断、usage809676/30791、两blocked gate与halt账本保持。用户授权M7工程依赖例外，不降低旧质量门禁。

构建完成、本机预览、目标Ubuntu/GPU实测、公开发布分别记录。外部部署、合并main、公开Release、新付费调用和新Agent委派本轮均未授权。公开开放相关能力前需定向真实确认或明确接受受限范围；完整回答要求不降为摘录，旧评分不改。

## 结构

```text
frontend/                 Vue工作台与单元/浏览器用例
app/main.py               统一FastAPI入口（旧课程入口保留）
app/runs/                 持久运行、租约、SSE与恢复
app/knowledge/            资料、原件、修订与授权引用
app/support/              用户确认、支持草稿与待审反馈
app/evaluation/           受控正式评测（本轮预览关闭）
deploy/ + compose.delivery.yaml  独立应用拓扑
scripts/operations/       隔离预览、备份与防覆盖恢复
examples/preview/         自制CC0样例
```

课程原件、解析缓存、权重、真实.env、日志、output/evals和原始判断不在交付文件中；历史来源及运行记录保留在docs。本项目不声称课程底座全部原创，也未擅自给全仓库增加开源许可证。当前任务及授权以[PROGRESS](docs/development/PROGRESS.md)、[REVIEW_STATUS](docs/development/REVIEW_STATUS.md)和[总清单](docs/plans/DEVELOPMENT_TODO.md)为准。
