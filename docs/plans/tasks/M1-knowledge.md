# M1：知识注册、解析与版本发布开发 ToDo

> 执行方式：按任务逐项开发；使用 superpowers:executing-plans 技能。任务中的步骤采用勾选框跟踪；不自行派发子代理。

**目标：**交付“知识注册、解析与版本发布”阶段可独立验收的能力。
**架构：**沿现有 Python/FastAPI/LangGraph 链路做小步适配；Vue 3 前端只消费统一 API 与事件契约。保留旧入口与数据直至本阶段验收通过。
**技术栈：**Vue 3 / TypeScript / FastAPI / MongoDB / Milvus / MinIO；具体测试工具与依赖在对应任务中建立。
**设计依据：**[优化方案](../2026-10-22-technical-support-optimization.md)、[接口与数据契约](../DEVELOPMENT_CONTRACTS.md)、[开发总清单](../DEVELOPMENT_TODO.md)。

## 进入条件与执行约束

进入实现前 M0 验收通过；M2 最小协议可以先讨论。

- 以下文件均为**计划创建/修改**，不表示已经存在；执行前用 `rg` 核对真实接口与源码。
- 本阶段遵守总清单中的 Vue 3、中文注释、数据隔离、配置脱敏和完成证据规则。
- 每个代码任务先增加能揭示错误的用例，再做最小实现；文档、样式等低影响变更按实际结果检查，不写镜像测试。
- 每完成一个任务，记录验证命令、输出摘要、涉及文件和遗留问题；验证通过后才勾选[总清单](../DEVELOPMENT_TODO.md)，并更新[进度](../../development/PROGRESS.md)与[变更记录](../../development/CHANGELOG.md)。
- 命令均从项目根目录运行；`pnpm -C frontend` 命令需 M3-01 建立对应 scripts 后才存在。依赖安装和测试数据准备不表示任务验收通过。
- 每个任务验证其直接影响的行为，阶段验收时再执行阶段回归；不要重复运行无关全量测试。

<a id="m1-01"></a>
### M1-01：知识数据与稳定标识

**依赖：**M0-09。
**文件：**`app/knowledge/models.py`; `app/products/models.py`; `tests/unit/test_knowledge_ids.py`; `docs/architecture/knowledge-schema.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M1-01.1** 定义 product/kb/document/revision/section/chunk/asset。
- [x] **M1-01.2** 原件 hash 与业务 ID 分开。
- [x] **M1-01.3** source_refs 使用页码/章节/单元格可空联合类型。
- [x] **M1-01.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_knowledge_ids.py -q。
- [x] **M1-01.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**同名不同文件不覆盖；同 hash 不擅自合并业务归属；所有对外 ID 为字符串；定位精度可显式缺失。

<a id="m1-02"></a>
### M1-02：注册表与幂等仓储

**依赖：**M1-01。
**文件：**`app/knowledge/repository.py`; `app/products/repository.py`; `tests/integration/test_knowledge_repository.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M1-02.1** 创建 Mongo 唯一索引和条件更新。
- [x] **M1-02.2** 注册原件/修订及处理 attempt。
- [x] **M1-02.3** 无跨集合事务假设，失败可核对补偿。
- [x] **M1-02.V** 验证：.venv/Scripts/python.exe -m pytest tests/integration/test_knowledge_repository.py -m integration -q。
- [x] **M1-02.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**重复请求不产生重复修订；同名不同资料互不覆盖；单机 Mongo 可运行；对旧消息/资料无回写。

<a id="m1-03"></a>
### M1-03：解析契约与格式路由

**依赖：**M1-01。
**文件：**`app/ingestion/models.py`; `app/ingestion/parsers/base.py`; `app/ingestion/parsers/router.py`; `tests/unit/test_parser_routing.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M1-03.1** 定义 ParsedDocument/Block/SourceRef。
- [x] **M1-03.2** 从旧 node_entry 提取格式路由。
- [x] **M1-03.3** 扩展名大小写归一，按实际类型验证 PDF/MD/XLSX。
- [x] **M1-03.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_parser_routing.py -q。
- [x] **M1-03.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**不支持格式在入口返回错误；解析降级带质量标记；原文/模型图像描述字段分离。

<a id="m1-04"></a>
### M1-04：长 PDF 分段与恢复

**依赖：**M1-03。
**文件：**`app/ingestion/parsers/mineru.py`; `app/ingestion/stages/pdf_segments.py`; `tests/unit/test_pdf_segments.py`; `tests/integration/test_mineru_parser.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M1-04.1** 阅读 output/course-import/run_import.py 等已验证脚本再抽取。
- [ ] **M1-04.2** 供应商限制可配置，保留 segment_offset/batch_id/hash。
- [ ] **M1-04.3** 复用成功段并合并原始页码。
- [ ] **M1-04.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_pdf_segments.py -q；真实 MinerU 小样单独标记 integration。
- [ ] **M1-04.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**150 页拆分测试跨段页码无偏移；重试不重交成功段；超时/结构修复/原生降级可区分。

<a id="m1-05"></a>
### M1-05：Excel 与 Markdown 解析

**依赖：**M1-03。
**文件：**`app/ingestion/parsers/excel.py`; `app/ingestion/parsers/markdown.py`; `tests/unit/test_tabular_sources.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M1-05.1** 提取全部非空单元格、sheet/cell 和公式/缓存值。
- [ ] **M1-05.2** 按文档用途分类。
- [ ] **M1-05.3** Markdown 标题层级与图片引用保留。
- [ ] **M1-05.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_tabular_sources.py -q。
- [ ] **M1-05.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**跨 sheet 不丢内容；公式与缓存值不混淆；项目计划类 Excel 不被默认为设备技术手册。

<a id="m1-06"></a>
### M1-06：图片资产、摘要缓存与限流

**依赖：**M1-02,M1-03。
**文件：**`app/ingestion/stages/images.py`; `app/knowledge/assets.py`; `app/infrastructure/rate_limits.py`; `tests/unit/test_image_cache.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M1-06.1** 缓存 key 组合原图/上下文 hash、模型、prompt 版本。
- [ ] **M1-06.2** 保存原图与摘要关系。
- [ ] **M1-06.3** 多个导入任务共享供应商限流，失败可恢复。
- [ ] **M1-06.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_image_cache.py -q。
- [ ] **M1-06.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**相同图不同上下文不串摘要；摘要去除嵌套图片标签；缺摘要有状态；重复任务不重复付费摘要。

<a id="m1-07"></a>
### M1-07：结构化切片与适用范围

总控已知边界：M0 审查发现原有 splitter 缺少无分隔符文本兜底，2500 字连续文本在 2000 上限下输出 2506 字。此项纳入本任务，加入连续文本/超长标题的回归，并保留图像和表格结构边界；不是 M0 新增回归。见 [M0 审查 N1](../../development/reviews/M0-review.md)。

**依赖：**M1-03,M1-04,M1-05,M1-06。
**文件：**`app/ingestion/stages/chunking.py`; `tests/unit/test_structured_chunks.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M1-07.1** 保留 heading_path/source_refs/asset_ids。
- [ ] **M1-07.2** 表格拆分重复表头并保留行范围。
- [ ] **M1-07.3** 支持块级型号范围与同修订父子关系。
- [ ] **M1-07.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_structured_chunks.py -q。
- [ ] **M1-07.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**长表、步骤列表、警示框和配图可溯源；chunk_uid 重试稳定；不跨型号合并。

<a id="m1-08"></a>
### M1-08：v2 Milvus 索引适配

**依赖：**M1-02,M1-07。
**文件：**`app/knowledge/index.py`; `app/retrieval/filters.py`; `tests/integration/test_v2_index.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M1-08.1** 新集合加入 kb/document/revision/chunk_uid 和来源。
- [ ] **M1-08.2** 序号 INT32。
- [ ] **M1-08.3** 复用现模型生成 dense/learned sparse，统一构造转义与授权过滤。
- [ ] **M1-08.V** 验证：.venv/Scripts/python.exe -m pytest tests/integration/test_v2_index.py -m integration -q。
- [ ] **M1-08.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**独立 v2 集合小样检索通过；引号/特殊字符安全过滤；旧集合不删不重建。

<a id="m1-09"></a>
### M1-09：验证后发布与回滚

**依赖：**M1-08。
**文件：**`app/knowledge/publishing.py`; `tests/integration/test_revision_publish.py`; `docs/architecture/revision-lifecycle.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M1-09.1** staged→validated→published。
- [ ] **M1-09.2** 验证数量/hash/向量与图片。
- [ ] **M1-09.3** 条件更新 active_revision_id，检索只用活动修订清单，发布失败可核对。
- [ ] **M1-09.V** 验证：.venv/Scripts/python.exe -m pytest tests/integration/test_revision_publish.py -m integration -q。
- [ ] **M1-09.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**插入失败旧版仍可用；新旧引用各可回看；回切不重解析；并发发布仅一个合法指针生效。

<a id="m1-10"></a>
### M1-10：旧知识迁移工具

**依赖：**M1-09。
**文件：**`scripts/migrations/register_v1_documents.py`; `scripts/migrations/build_v2_index.py`; `tests/integration/test_migration_dry_run.py`; `docs/runbooks/index-migration.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M1-10.1** 先 dry-run 输出映射/缺失/碰撞报告；任何真实迁移前保存 Mongo/MinIO/Milvus 与活动修订清单，在独立目标恢复一个样例并核对原件、向量和引用；失败则停止写入迁移。
- [ ] **M1-10.2** 2–3 份小/长/表格样例迁移。
- [ ] **M1-10.3** 支持批次、断点与回切，扩大范围前核验统计。
- [ ] **M1-10.V** 验证：.venv/Scripts/python.exe scripts/migrations/register_v1_documents.py --dry-run；仅使用隔离测试源执行迁移测试。
- [ ] **M1-10.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**dry-run 零写入；不按文件名删旧向量；旧绝对图链接有 asset 映射；无坐标资料不伪造 bbox。

<a id="m1-11"></a>
### M1-11：M1 阶段验收

**依赖：**M1-10。
**文件：**`docs/development/records/M1-11.md`; `docs/runbooks/index-migration.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [ ] **M1-11.1** 实测同名/重试/失败发布/回滚。
- [ ] **M1-11.2** 对 PDF/Excel/图片逐来源抽检。
- [ ] **M1-11.3** 保存迁移清单和活动修订快照。
- [ ] **M1-11.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit tests/integration -m 'not live_provider' -q。
- [ ] **M1-11.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**一份新资料贯通注册→解析→检索→回看；小样恢复演练通过后才考虑全量迁移。

