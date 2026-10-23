# v1隔离小样备份、恢复与v2迁移

当前只允许1–3份`m1_test_`隔离源/目标和`m1-test/`对象前缀，原课程库不全量迁移。旧Milvus真实schema使用INT64 chunk_id、content/title/parent_title、dense_vector/sparse_vector；不能拿文件名或item_name推断唯一资料。旧链路没有统一原件注册表，先人工核对源身份、原件与切片对应，生成明确清单，再使用工具。无对应原件/资产映射的资料暂不迁移，不伪造来源坐标。

清单是JSON数组，每项包含source_id（稳定旧身份）、name、original_key、original_sha256、chunk_ids（旧主键字符串数组），可附purpose/product_ids及images数组。images项包含url（旧绝对图URL）、object_key、sha256。原件/向量/URL留本地，不提交GitHub。相同name不是碰撞；相同source_id或重复切片归属是碰撞。源没有版本注册表时，活动清单明确保存`[]`，不能把它说成旧版本功能已存在。

PowerShell从项目根运行，先使用独立命名并保存本轮实际参数：

```powershell
.venv/Scripts/python.exe scripts/migrations/register_v1_documents.py --dry-run --manifest output/selection.json --owner-id test --kb-id migration-sample --output output/dry-run.json
.venv/Scripts/python.exe scripts/migrations/backup_v1_sample.py backup --manifest output/selection.json --source-db m1_test_SOURCE --mongo-collection legacy_SAMPLE --milvus-collection m1_test_SOURCE_legacy --active-snapshot output/active.json --directory output/backup-SAMPLE
.venv/Scripts/python.exe scripts/migrations/backup_v1_sample.py restore --snapshot output/backup-SAMPLE/snapshot.json --target-db m1_test_RESTORE --milvus-collection m1_test_RESTORE_legacy --prefix m1-test/RESTORE/
.venv/Scripts/python.exe scripts/migrations/build_v2_index.py --snapshot output/backup-SAMPLE/snapshot.json --recovery-report output/backup-SAMPLE/recovery-report.json --target-db m1_test_TARGET --collection m1_test_TARGET_v2 --owner-id test --kb-id migration-sample --apply
```

参数中的SOURCE/RESTORE/TARGET/SAMPLE需替换为本次独立名称。仅`--dry-run`无清单会返回退出2、报告缺`--manifest`且writes=0，不接服务。dry-run读取清单本身零服务写；backup只读服务，写本地完整快照。restore要求独立空Mongo目标、新Milvus集合，原向量和业务字段完整读回比对，MinIO恢复原件/图片hash校验；失败不生成成功恢复报告。重新演练使用新目标，不清空旧现场。真实源schema、对象key、Mongo记录、活动列表和向量都保存在snapshot.json及blobs，快照hash保护清单/对象一致性。恢复到原环境之外需要另行环境与schema兼容检查，本阶段没有灾备服务器演练。

migrate_batch在任何注册前要求匹配的成功恢复报告并重新校验备份；按批注册/新建修订/迁移图资产与绝对链接/生成双路向量/校验/发布。批次ID为快照hash，完成资料持久checkpoint，未完成资料依靠注册/修订/索引幂等恢复。完成批次重跑不重编码。旧绝对URL改为asset://资产ID，原URL到资产映射留迁移结果；未知bbox保持null。保留旧源不按文件名删向量，任何失败不触碰其他资料活动指针。

回切：新资料替换旧活动版本前保留其指针，使用RevisionPublisher.publish(旧revision_id,expected_active=当前revision_id)回滚。迁移是新增业务资料时，旧入口仍读旧集合，停止使用新入口即可恢复原服务；不删除迁移记录。放大范围必须由后续总控授权，并先核对缺失、碰撞、统计、来源与恢复报告。

验证：`$env:M1_TEST_DB='m1_test_20261023_migration'; .venv/Scripts/python.exe -m pytest tests/unit/test_migration_manifest.py tests/integration/test_migration_dry_run.py -q`。真实测试自动创建小PDF、150页PDF、跨sheet表格和一张PNG，原库不访问；产物在output/m1-migration/<本轮ID>/。付费模型调用为0，本地现有BGE不自动下载。
## 第2轮恢复契约与失败处理

新备份格式version=2，将milvus_schema及milvus_indexes纳入快照哈希，保存动态字段、字段参数和索引metric/类型。恢复不再调用在线源describe/get；仅需已验证的本地快照/blobs与目标服务。显式恢复旧主键，避免auto_id重新生成引用。旧v1缺schema应明确拒绝；保留旧目录，从可读源另建全新v2备份，不能手填schema后冒充原备份。超出当前恢复器的函数/结构数组schema明确拒绝写入。

任何写入前同时要求：独立空Mongo目标、新Milvus集合、规范m1-test对象路径、与同桶源对象目录不重叠、对象目标前缀为空。拒绝同源key、父子前缀、点路径/重复斜杠和已有其他对象；失败不覆盖、不清现场，重新演练使用全新目标。默认不支持复用恢复前缀续跑。预检不是跨存储分布式事务，独立演练前缀须只由本次恢复器写入；管理员并发写入与生产灾备不在本次验收范围。

实际命令与红绿、真实目标位置见records/M1-10.md（项目路径docs/development/records）。原始snapshot/recovery-report只留本机，不上传对象key或配置。
