# 导入worker恢复（M2）

更新：2026-10-24。统一问答与API说明见[API v1](../architecture/api-v1.md)。API断开订阅不会取消执行；重连先按run_id读快照与最后seq，410读快照而非重发创建。API进程重启后恢复扫描将失联执行标interrupted，不能自动重跑已计费回答；用户用新client_request_id新建运行。型号候选/确认点在Mongo，重新领取使用新token。

completed已存但assistant消息缺失时，每10秒扫描按completion_snapshot和稳定message_id补写，不再调模型。出现recovery_issue.conversation_scope_mismatch时需人工核对会话归属；系统保留异常条目并继续其他恢复，不自动转移owner或删除历史。先保存只含任务ID/状态/阶段的脱敏诊断，不导出完整prompt或签名URL。

配置见[说明](../CONFIGURATION.md)。保留存储卷，不执行down -v或清队列。Linux镜像仅处理/队列依赖，宿主CUDA模型不复制；MODEL_HOST_TOKEN由环境读取，桥接禁止公网暴露。

Mongo是事实账本，Dispatcher发后确认，broker仅job_id；重复投递由条件claim拒绝。停止worker后等待租约失效，再运行`.venv/Scripts/python.exe scripts/admin/dispatch_jobs.py --once`并启动原worker，过期任务重领新attempt。旧attempt/token不能save或改活动修订。重试需维护者、expected_version及可重试错误；429/超时/5xx可重试，格式/鉴权/配置先处理。

解析/原图存MinIO，图摘要按hash/上下文/模型/prompt复用，嵌入按批次hash持久。MinerU分段batch挂worker-cache，恢复原卷，不删除成功段付费重跑。最终指针CAS附资料attempt/token/期限，验证原件/来源/索引后才发布。completed重复投递不再发布；已发布但任务终态保存中断会核对修订后结束。

真实隔离结果与限制见[09](../development/records/M2-09.md)/[10](../development/records/M2-10.md)。只强停新测试worker，未故障注入源数据库；供应商响应至缓存落盘有计费窗口，不承诺exactly-once。生产灾备与全库迁移未验收。

### 过期资料许可接管

旧job已completed但finally前退出时，资料import_permit仍可能存在。等待import_lease_until过期后，新修订job通过原子CAS自动接管，无需手动清字段；有效其他job和同job更高attempt仍拒绝。同attempt异token不能覆盖。迟到heartbeat仅匹配完整job/attempt/token且许可未过期；finally只清自己的完整许可，最终指针仍核对permit和期限。多worker竞争只一方领取；不要直接修改许可来恢复。无期限的异常遗留需保留现场并人工核对，不自动猜测过期。
