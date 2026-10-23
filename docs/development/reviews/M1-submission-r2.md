# M1第2轮提交：R1–R4修复与隔离复验

2026-10-23。依据[第1轮总控审查](M1-review.md)，完成M1-05、M1-07、M1-10及M1-11的修复自验，M1为11/11自验，核心20/76；本轮无未完成M1任务。**等待总控审查 M1，M2未授权。**原首轮提交、验证摘要、文件快照与失败证据均保留，不覆盖。

## 逐项回应与修改范围

| 审查项 | 修复前 | 本轮实现与验证 |
| --- | --- | --- |
| R1 · 表格丢值/来源错位 | 通用切片删除Excel第二行真实短横线，正文A3引用错为A2；Markdown删除分隔行后行号偏移，PDF无行定位也推算行号 | MarkdownParser识别表格入口及分隔语法，并保存rows对应的物理row_numbers；通用切片不按文本删除数据，正文范围与重复表头各有来源。Excel保留A1/A2/A3与真实行范围；PDF缺定位保持null。正常ExcelParser→chunk_document与前置正文/多片Markdown/PDF边界正式红绿，原公式缓存/跨sheet/大小/旧N1回归保留 |
| R2 · 跳级标题 | Root→三级First→三级Second误成Root/First/Second | 按实际level栈弹出同级/更深级，Second为Root/Second，Block及SourceRef同步；三级起始、深层回退、重复同名、围栏回归。Markdown版本2与切片版本2纳入处理身份，升级创建新修订，不静默改写已发布历史 |
| R3 · 恢复依赖在线源schema | snapshot无schema，restore在线describe源，不可用便失败 | 快照version=2保存milvus_schema/milvus_indexes并纳入hash；保留字段参数、动态字段、索引名/类型/metric/参数。restore只读本地快照和目标服务。旧v1缺元信息明确拒绝、另建新备份。离线阻断源读取仍恢复成功，真实集成以守卫阻断源集合调用和源对象get，完整读回通过 |
| R4 · 对象恢复覆盖源/已有对象 | 仅检查m1-test前缀，允许向源key执行put并报告成功 | 任何写入前同时检查Mongo/Milvus/MinIO目标，拒绝源目录父子重叠、非规范点路径/重复斜杠、已有对象/非空目标前缀、复用恢复前缀。离线拒绝路径断言三种存储写次数均0；合法新目标恢复成功，原源对象hash不变 |

源码：app/ingestion/parsers/markdown.py、stages/chunking.py、service.py，app/knowledge/migration.py。新增tests/unit/test_m1_review_sources.py（9项）、test_m1_review_recovery.py（13项）、test_m1_artifact_reports.py（2项）；加强既有integration的恢复守卫、schema/索引读回及处理版本冲突断言。

快照工具build_m1_artifacts.py补显式--summary/--manifest/--base，读取本轮摘要指定JUnit；另有1失败/1通过红测与2通过绿测，避免新轮次暗用首轮181。完整修改文件、哈希、Python语法及链接以[第二轮独立快照](M1-artifact-manifest-r2.json)为准。

## 实际命令与证据

所有命令从项目根运行，使用已有.venv/Scripts/python.exe；真实命令设置PYTHONIOENCODING=utf-8、LOG_CONSOLE_ENABLE=False、LOG_FILE_ENABLE=False，未设置M1_LIVE_PROVIDER。以下证据都在本地docs/development/evidence，原件未上传。

| 命令 | 实际结果 | 证据名称 |
| --- | --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_m1_review_sources.py -q --junitxml=docs/development/evidence/M1-r2-sources-red.xml` | 退出1，8 failed/1 passed，44.55秒；值、来源和标题路径断言失败 | M1-r2-sources-red.txt/xml |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_m1_review_sources.py tests/unit/test_tabular_sources.py tests/unit/test_structured_chunks.py tests/unit/test_chunk_structure.py -q --junitxml=docs/development/evidence/M1-r2-sources-green.xml` | 退出0，43 passed，40.45秒 | M1-r2-sources-green.txt/xml |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_m1_review_recovery.py -q --junitxml=docs/development/evidence/M1-r2-recovery-red.xml` | 退出1，11 failed/2 passed，12.41秒；源依赖/覆盖/旧快照反例 | M1-r2-recovery-red.txt/xml |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_m1_review_recovery.py tests/unit/test_migration_manifest.py -q --junitxml=docs/development/evidence/M1-r2-recovery-green.xml` | 退出0，16 passed，15.84秒 | M1-r2-recovery-green.txt/xml |
| `$env:M1_TEST_DB='m1_test_20261023_r2_retry'; .venv/Scripts/python.exe -m pytest tests/integration/test_migration_dry_run.py tests/integration/test_ingestion_pipeline.py -q --junitxml=docs/development/evidence/M1-r2-integration-retry.xml` | 退出0，4 passed，94.95秒，7 SWIG警告；含真实新目标恢复、导入接线和历史回看 | M1-r2-integration-retry.txt/xml |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_m1_artifact_reports.py -q --junitxml=docs/development/evidence/M1-r2-artifact-red.xml`；修复后使用-green.xml | 红退出1：1 failed/1 passed，14.20秒；绿退出0：2 passed，13.17秒 | M1-r2-artifact-red/green.txt/xml |
| `$env:M1_TEST_DB='m1_test_20261023_r2_final'; .venv/Scripts/python.exe -m pytest tests/unit tests/integration tests/contract -m 'not live_provider' -q --junitxml=docs/development/evidence/M1-r2-stage-final.xml` | **退出0，205 passed、2 deselected、0 skipped，139.12秒，7 SWIG警告** | M1-r2-stage-final.txt/xml |
| `.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q` | 退出0，3 tests OK，0.005秒 | M1-r2-reimport.txt |
| `.venv/Scripts/python.exe scripts/verification/recheck_m1_live.py --report docs/development/evidence/M1-11-live-report.json --output docs/development/evidence/M1-r2-live-recheck.json` | 退出0；两资料5/2切片原件、向量、来源、图像/摘要缓存关联只读复核通过，供应商调用0 | M1-r2-live-recheck.txt/json |

最终205项由实际JUnit分类为178单元、12契约、15真实隔离集成；首轮181保留，新增24项不把多次定向运行重复累加。前一阶段回归203 passed/2 deselected/154.65秒也保留在M1-r2-stage.txt/xml，追加快照工具2项后完整重跑为205。离线组合188 passed/77.40秒是中间结果，不代替最终205。摘要及所有本轮原始输出哈希见[第二轮脱敏摘要](M1-validation-summary-r2.json)。

首次真实集成在Docker未启动时出现4 errors、22.30秒、退出1（M1-r2-integration.txt/xml），Mongo拒绝连接，未进入业务；不计业务红测。正常启动已有Docker Desktop后，原四服务healthy，无重建/清理，使用新目标retry通过；两次现场分别保留。

## 真实、fake、排除及数据边界

单元/契约默认禁网络；R3/R4的冲突/源不可用反例全部合成输入及fake，无真实破坏性故障。15集成使用真实独立Mongo、Milvus、MinIO和现有本地BGE，视觉端口fake/PDF显式native降级不作为供应商验收。恢复真实测试三份合成小PDF、150页PDF、跨sheet XLSX及PNG，3资料/3向量/4对象，源读取守卫开启；源服务保持在线且没有删除。对象/向量/业务动态字段/索引读回及旧源hash检查均通过。

本轮未执行两项付费供应商测试（deselected，不是skip），原有效供应商报告只读复核通过；没有新增付费模型调用。真实新写入仅m1_test_20261023_r2_retry/r2_stage/r2_final及随机m1_test_restore_*，Milvus随机m1_test_*，MinIO独立m1-test前缀。最早targeted库连接失败未进入业务。完整新恢复目录与snapshot/recovery-report/migration-results哈希在本机M1-r2-recovery-locations.json，原始对象映射不上传。课程原件、缓存和已入库知识、原失败证据与旧快照均保留，无清桶、删集合、全量重导入或桶策略变更。

## 配置、兼容、风险与回滚

无新依赖、模型升级或环境配置，未修改.env；沿用MONGO_URL/MILVUS_URL/MINIO_*和本地BGE，不输出值。解析/切片版本升级需新请求修订，历史原件/切片/资产仍读已存载荷；旧请求配置不符明确ConflictError。快照v1不能由新恢复器悄悄补schema，保留旧件并从可读源另建v2。

默认不支持复用已写恢复目标续跑；失败现场保留，换新目标。写前预检不承诺对外部管理员并发写入的跨存储事务保护，演练使用唯一独立前缀。函数/结构数组等当前不支持的schema扩展拒绝写入；无生产灾备/全库迁移、长期稳定性或大规模性能结论。M0历史未知图片业务异常/Windows原生模型异常不宣称根治。

回滚按修复提交正常revert，不reset、不删除源或失败目标；保留新旧快照并使用匹配恢复器。停用新迁移/导入领域入口仍可读旧课程集合；已发布版本按expected_active CAS回切，不重解析或删除历史。下一阶段仍须总控明确授权。

## Git与交接

用户授权仓库main正常提交推送，原远程历史保留。R1/R2：466440c54938586e69df96f619ad38f63379ac45；R3/R4：ecf86777627956e5c9a5008ffa5251ae98370b2b，均已推送并核对远程头一致。最终材料提交SHA由本轮最终回复补记，不循环amend。原始evidence/output、.env、模型、课程原件与既有未跟踪evals/未上传。REVIEW_STATUS仅置待审查，未自行批准M1或进入M2。
