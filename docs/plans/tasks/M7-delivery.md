# M7：部署、恢复与个人项目交付开发 ToDo

> 执行方式：按任务逐项开发；使用 superpowers:executing-plans 技能。任务中的步骤采用勾选框跟踪；不自行派发子代理。

**目标：**交付“部署、恢复与个人项目交付”阶段可独立验收的能力。
**架构：**沿现有 Python/FastAPI/LangGraph 链路做小步适配；Vue 3 前端只消费统一 API 与事件契约。保留旧入口与数据直至本阶段验收通过。
**技术栈：**Vue 3 / TypeScript / FastAPI / MongoDB / Milvus / MinIO；具体测试工具与依赖在对应任务中建立。
**设计依据：**[优化方案](../2026-10-22-technical-support-optimization.md)、[接口与数据契约](../DEVELOPMENT_CONTRACTS.md)、[开发总清单](../DEVELOPMENT_TODO.md)。

## 进入条件与执行约束

基础交付依赖 M3/M5/M6 验收；生产发布按实际用户指令执行。

- 以下文件均为**计划创建/修改**，不表示已经存在；执行前用 `rg` 核对真实接口与源码。
- 本阶段遵守总清单中的 Vue 3、中文注释、数据隔离、配置脱敏和完成证据规则。
- 每个代码任务先增加能揭示错误的用例，再做最小实现；文档、样式等低影响变更按实际结果检查，不写镜像测试。
- 每完成一个任务，记录验证命令、输出摘要、涉及文件和遗留问题；验证通过后才勾选[总清单](../DEVELOPMENT_TODO.md)，并更新[进度](../../development/PROGRESS.md)与[变更记录](../../development/CHANGELOG.md)。
- 命令均从项目根目录运行；`pnpm -C frontend` 命令需 M3-01 建立对应 scripts 后才存在。依赖安装和测试数据准备不表示任务验收通过。
- 每个任务验证其直接影响的行为，阶段验收时再执行阶段回归；不要重复运行无关全量测试。

<a id="m7-01"></a>
### M7-01：可重复 CPU/GPU 环境

**依赖：**M6-08。
**文件：**`pyproject.toml`; `uv.lock`; `frontend/pnpm-lock.yaml`; `.env.example`; `docs/runbooks/dependencies.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M7-01.1** 固定依赖/镜像和 Node。
- [ ] **M7-01.2** 分别验证 CPU/GPU 安装，不让 uv 意外替换 PyTorch 构建。
- [ ] **M7-01.3** 配置模板中文说明和必选/可选能力。
- [ ] **M7-01.V** 验证：分别在干净 CPU 环境与目标 GPU 环境执行锁定安装并保存版本清单。
- [ ] **M7-01.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**新环境能按文档安装；无真实凭据；文本/视觉/检索能力缺项提示准确。

<a id="m7-02"></a>
### M7-02：Ubuntu 同源部署

**依赖：**M7-01。
**文件：**`deploy/api/Dockerfile`; `deploy/frontend/Dockerfile`; `deploy/nginx.conf`; `compose.yaml`; `docs/runbooks/ubuntu-deploy.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M7-02.1** FastAPI、前端静态资源、worker 与现有基础设施明确拓扑。
- [ ] **M7-02.2** 代理 SSE 禁缓冲，PDF Range。
- [ ] **M7-02.3** 内部 DNS/Windows host 地址分别配置。
- [ ] **M7-02.V** 验证：docker compose config --quiet；隔离部署的 /health/live 与 /health/ready 检查。
- [ ] **M7-02.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**浏览器仅访问同源入口；密钥不进前端镜像；Windows/Ubuntu 配置差异清楚，禁止承诺 env 永不改变。

<a id="m7-03"></a>
### M7-03：健康检查与启动故障

**依赖：**M7-02。
**文件：**`app/api/health.py`; `scripts/verification/check_readiness.py`; `tests/contract/test_health.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M7-03.1** live 仅进程存活。
- [ ] **M7-03.2** ready 分类 Mongo/Milvus/MinIO/模型与可选工具。
- [ ] **M7-03.3** 配置缺项/模型未加载/供应商错误分开。
- [ ] **M7-03.V** 验证：.venv/Scripts/python.exe -m pytest tests/contract/test_health.py -q。
- [ ] **M7-03.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**探针不反复发收费 LLM 请求；可选 MCP 关闭不影响 ready；依赖断开准确报告。

<a id="m7-04"></a>
### M7-04：备份、恢复与索引回切

**依赖：**M7-02,M1-10。
**文件：**`docs/runbooks/backup-restore.md`; `scripts/operations/backup.py`; `scripts/operations/restore.py`; `tests/integration/test_restore_manifest.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M7-04.1** Mongo、MinIO、Milvus 产物与活动修订清单一起备份。
- [ ] **M7-04.2** 校验 hash/版本/权限。
- [ ] **M7-04.3** 在独立目标恢复后问答和回看引用。
- [ ] **M7-04.V** 验证：独立恢复命名空间实操并保存源/目标统计与问答证据。
- [ ] **M7-04.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**不是只生成压缩包；恢复后的原件/向量/注册表一致；可回切旧集合；恢复命令要求显式目标并防误覆盖。

<a id="m7-05"></a>
### M7-05：故障与容量测试

**依赖：**M7-03,M7-04。
**文件：**`scripts/verification/load_support.py`; `docs/evaluation/capacity-report.md`; `docs/runbooks/failure-recovery.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M7-05.1** 逐级 1/2/4 会话、导入+问答。
- [ ] **M7-05.2** 注入 worker 停止、模型 429、存储不可用、SSE 断开。
- [ ] **M7-05.3** 记录硬件/峰值内存/显存/延时。
- [ ] **M7-05.V** 验证：受控测试环境运行负载与故障矩阵；不在当前已入库集合做破坏测试。
- [ ] **M7-05.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**数据不丢且终态正确；明确实测容量和排队策略；不把未测高并发写进简历。

<a id="m7-06"></a>
### M7-06：访问、渲染与凭据交付检查

**依赖：**M7-05。
**文件：**`tests/e2e/security-boundaries.spec.ts`; `docs/development/records/M7-06.md`; `.gitignore`; `deploy/`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M7-06.1** 复核越权、路径穿越、CSRF、危险 Markdown、签名资源、镜像层/构建产物。
- [ ] **M7-06.2** 核对测试数据与课程原件排除范围。
- [ ] **M7-06.V** 验证：运行已定义权限/XSS 用例和待发布文件清单检查；只记录检查结果不输出敏感值。
- [ ] **M7-06.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**用户 B 无法访问 A 的任何 run/citation/asset；仓库/前端/日志无真实凭据；旧图受控访问仍可用。

<a id="m7-07"></a>
### M7-07：产品名称与来源贡献文档

**依赖：**M7-06。
**文件：**`README.md`; `NOTICE.md`; `THIRD_PARTY_NOTICES.md`; `docs/reuse/manifest.json`; `pyproject.toml`; `frontend/package.json`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M7-07.1** 名称在实现期结合用户选择统一。
- [ ] **M7-07.2** 说明课程底座/开源复用/独立贡献。
- [ ] **M7-07.3** 提炼可验证的 AI 应用开发成果。
- [ ] **M7-07.V** 验证：文件/页面/包名一致性检查；复用清单逐项对比实际依赖与源码。
- [ ] **M7-07.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**品牌与功能一致；无未经支持的企业合作/性能声明；所有实际复制源码有许可证与来源。

<a id="m7-08"></a>
### M7-08：可分享演示与新环境复现

**依赖：**M7-07。
**文件：**`examples/`; `docs/runbooks/quickstart.md`; `docs/demo/scenarios.md`; `docs/demo/`; `README.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M7-08.1** 准备自制或可再分发少量样例。
- [ ] **M7-08.2** 录制问答/澄清/引用/任务/闭环。
- [ ] **M7-08.3** 另一干净环境按文档部署。
- [ ] **M7-08.V** 验证：按 quickstart 完整实操；保存截图/视频路径、样例许可证与失败恢复步骤。
- [ ] **M7-08.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**演示真实后台，课程原件/缓存/模型权重不默认公开；新环境可重复走核心流程。

<a id="m7-09"></a>
### M7-09：M7 最终交付验收

**依赖：**M7-08。
**文件：**`docs/development/records/M7-09.md`; `docs/development/PROGRESS.md`; `docs/development/CHANGELOG.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M7-09.1** 核对所有核心任务证据、可选延期理由与遗留问题。
- [ ] **M7-09.2** 汇总回归/质量/容量/恢复。
- [ ] **M7-09.3** 给出可公开文件清单。
- [ ] **M7-09.V** 验证：逐项审阅总清单和阶段记录；从干净环境复现至少一次核心演示。
- [ ] **M7-09.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**完成标准是可运行、可恢复、可解释来源与贡献；只有当前用户授权发布时才推送/公开。

