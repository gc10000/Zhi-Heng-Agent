# M1 总控复审 · 第2轮

日期：2026-10-23。审查提交：`7431cc78d48388950fd478f3f8e6a841d5b53903`；修复提交：`466440c`、`ecf8677`。结论：**通过。R1–R4关闭，M1 11/11、核心20/76；授权M2-01至M2-12按依赖连续执行。M3实现尚未授权。**

依据[第二轮提交](M1-submission-r2.md)、实际修复代码、新增回归、[开发契约](../../plans/DEVELOPMENT_CONTRACTS.md)和本轮独立重跑结果。总控顺序审查，无业务代码修改。本结论承接[第一轮审查](M1-review.md)，不改写旧提交、快照或失败证据。

## 独立验证

| 检查 | 本轮实际结果 |
| --- | --- |
| 完整阶段pytest | **205 passed、2 deselected、0 skipped、7 warnings，193.91秒，退出0**；178单元、12契约、15真实隔离集成；JUnit时间193.902秒 |
| 既有重导入unittest | **3 tests OK，0.383秒，退出0** |
| 提交时点快照核验 | **85文件哈希、52份Python语法、187个本地链接通过**，敏感配置值扫描通过；实际报告及原始证据hash核对通过 |
| 真实供应商既有产物复核 | 两份资料原件hash、5/2切片完整向量与来源、图片hash/完整解码/摘要及缓存关联通过；本轮供应商付费调用0 |
| Git远程核对 | 审查开始时origin/main与提交`7431cc78d48388950fd478f3f8e6a841d5b53903`一致 |

阶段命令：`M1_TEST_DB=m1_test_20261023_review_r2`，`.venv/Scripts/python.exe -m pytest tests/unit tests/integration tests/contract -m 'not live_provider' -q --junitxml=docs/development/evidence/M1-review-r2-stage.xml`。未设置M1_LIVE_PROVIDER。2项供应商测试按选择排除，不是跳过或本轮重跑通过。警告为PyMuPDF SWIG弃用提示。193.91秒是pytest报告耗时，外层进程201.282秒，不据此宣称性能变化。

既有回归命令：`.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q`。产物复核命令：`.venv/Scripts/python.exe scripts/verification/recheck_m1_live.py --report docs/development/evidence/M1-11-live-report.json --output docs/development/evidence/M1-review-r2-live-recheck.json`。快照命令：`.venv/Scripts/python.exe scripts/verification/build_m1_artifacts.py --check --summary docs/development/reviews/M1-validation-summary-r2.json --manifest docs/development/reviews/M1-artifact-manifest-r2.json`。

本机原始独立证据为evidence/M1-review-r2-stage.txt/xml、M1-review-r2-reimport.txt、M1-review-r2-runs.json、M1-review-r2-live-recheck.json、M1-review-r2-audit.json，保持忽略、不上传。开发红测JUnit实核：来源8失败/1通过、恢复11失败/2通过、快照工具1失败/1通过，均0错误/0跳过；修复后的对应测试已包含在本轮205项独立回归中。没有把重复定向结果累加成总测试数。

## R1 · 关闭 · 表格数据与来源

复核`app/ingestion/parsers/markdown.py`、`app/ingestion/stages/chunking.py`及`tests/unit/test_m1_review_sources.py`。分隔语法在Markdown表格解析路径处理，通用切片器不再按短横线文本删除真实行。Excel正常解析到切片保留parameter、---、actual-value及A1/A2/A3；正文范围为实际第2–3行。Markdown拆片通过row_numbers映射物理行，前置正文不混入表格，正文及重复表头分别定位；PDF缺物理行号保持null。既有公式/缓存、跨sheet、边界及大小回归保留。接受修复，M1-07验收。

## R2 · 关闭 · 标题层级与版本

复核Markdown实际级别栈、`app/ingestion/service.py`处理身份及真实接线回归。同级/更深级弹栈，覆盖跳级同级、深层回退、三级起始、重复标题、围栏；块与SourceRef路径一致。Markdown及切片版本2纳入pipeline_identity，处理版本变化拒绝复用旧请求；真实接线验证旧原件仍可读取。升级创建新修订，历史产物不回写。接受修复，M1-05验收。

## R3 · 关闭 · 自包含恢复快照

复核`app/knowledge/migration.py`、离线恢复回归和真实迁移集成。快照v2保存schema、动态字段开关、字段参数及索引名/类型/metric/参数，并纳入快照hash；恢复仅使用本地快照/blobs和目标客户端。真实集成对源集合读取及源对象GET设置守卫，独立目标恢复、schema/索引/向量/对象读回通过，源保留。v1缺schema明确拒绝，须另建v2备份；不支持的functions/struct-array schema在写入前拒绝。接受修复。

## R4 · 关闭 · 所有目标写前检查

复核恢复执行顺序：Mongo空目标、新Milvus集合、规范对象前缀、同桶源目录重叠及前缀非空检查，均先于任何存储写入；schema构建和本地反序列化同样在写前完成。离线回归覆盖源key、父子目录、已有目标key、非空前缀、点路径/重复斜杠、已有Mongo/Milvus及重复恢复，拒绝路径三种存储均零新增写入；真实新目标正向恢复通过。接受修复，M1-10及阶段M1-11验收。

## 范围与保留限制

本轮真实写入仅独立m1_test测试数据库/随机集合和m1-test对象前缀；生成合成资料及本地恢复快照并保留现场。未删除或重建原数据、容器、卷，未改桶策略，无模型/依赖/真实配置变更。已有供应商产物复核不新增业务记录；客户端可能确保既有索引，不宣称服务端绝对零元数据操作。

恢复门禁仍限定1–3份隔离小样。预检不是跨存储事务，不承诺外部管理员竞争写入或生产灾备；失败目标保留，换全新目标重试。本阶段不等于全量课程迁移完成，也不等于新API、鉴权、Vue工作台或长期稳定性验收。M0历史未知图片/原生加载异常未宣称根治。

提交时点manifest已在本轮文档修改前核验。总控新增审查及更新状态后，涉及文档hash自然变化；旧manifest仍表示原提交，不回写以匹配新文档。既有evals/保持未跟踪、不上传。

## 下一阶段授权与接续

允许开发会话按[M2任务计划](../../plans/tasks/M2-api-runs.md)从M2-01执行至M2-12：统一API/lifespan、登录与范围授权、会话及逐轮快照、持久运行幂等、SSE重放、确认/取消/中断、知识上传与受控引用、Redis/Celery Linux worker租约及恢复、旧图适配和真实API验收。开发前先读取当前进度、公共契约、任务计划和Git工作流。

沿用Windows本地与现有存储，新Redis/worker配置和依赖在对应任务同步中文说明。测试故障与访问收紧只在独立目标执行；原课程库、旧入口和历史证据保留。阶段内按任务验证、记录并正常提交/推送用户GitHub，不强推。发现契约不适配先同步影响，不用mock冒充真实API或worker验收。M2-12完成后提交M2-submission.md并标待审查，等待总控授权M3；本轮不实施M2，也不授权服务器部署、全库迁移或公开Release。
