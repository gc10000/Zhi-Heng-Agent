# 跨存储隔离备份与恢复

当前`scripts/operations/snapshot.py`只放行随机`m1_test_m4_`库/集合、zh-preview/zh-restore私有桶及规范前缀。这是已实现的小样恢复路径，**尚非生产热备或通用生产迁移工具**。生产数据保持只读；正式生产演练须扩展并独立审阅命名空间准入，不能改名绕过护栏。

清单`zhi_heng_backup_v1`包括Mongo文档/索引/校验器、用户角色/kb权限/密码摘要、活动修订、MinIO精确对象/hash/版本及私有策略、Milvus完整scalar/dense/sparse/schema、源码版本及文件hash。会话、登录限流窗口和恢复控制记录排除；目标必须重新登录。备份包含敏感账户摘要，目录和介质须按私有数据管理，禁止提交Git。

停写后备份：

```powershell
& $py scripts/operations/backup.py --env-file output/local-preview/host.env --output output/backup-r1 --source-commit (git rev-parse HEAD)
```

host.env由本轮runtime转换为公开回环端口，仅静默消费。文件x-open、manifest最后生成，源前后双读检查变化；任一阶段失败保留目录，不复写“完成”。跨存储没有分布式事务，不能靠双读替代停写。

恢复必须显式提供本次打印的manifest SHA256及三个**均不存在**的新目标：

```powershell
& $py scripts/operations/restore.py --env-file output/local-preview/host.env --input output/backup-r1 --manifest-sha256 $manifestHash --target-database m1_test_m4_res_new123 --target-bucket zh-restore-new123 --target-collection m1_test_m4_res_new123_v2 --prefix knowledge/
```

命令中的new123仅语法例子，实际目标由本轮receipt生成，不能复用已恢复目标。写前检查清单/路径/符号链接/原件/hash/源和目标；Mongo原子预留，失败保存failed及部分产物，不删除锁、桶或集合后续写。完成后读回对象、索引、注册关系；活动修订/owner/kb保持，仅重绑目标向量身份和资产桶，源不改。第二次同目标恢复应拒绝。

切换和回切必须整体更换三元绑定并重建API/worker/dispatcher；先只读验证原件Range、引用授权、RevisionPublisher.inspect、合成索引检索和重新登录权限，再开放写入。未获新模型调用授权时只读检索不等于恢复后真实问答通过，保持生成关闭。实际演练与限制见[M7报告](../development/reviews/M7-delivery-first-r1.md)。
