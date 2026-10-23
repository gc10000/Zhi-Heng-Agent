# 导入worker恢复（M2）

配置见[说明](../CONFIGURATION.md)。保留存储卷，不执行down -v或清队列。Linux镜像仅处理/队列依赖，宿主CUDA模型不复制；MODEL_HOST_TOKEN由环境读取，桥接禁止公网暴露。

Mongo是事实账本，Dispatcher发后确认，broker仅job_id；重复投递由条件claim拒绝。停止worker后等待租约失效，再运行`.venv/Scripts/python.exe scripts/admin/dispatch_jobs.py --once`并启动原worker，过期任务重领新attempt。旧attempt/token不能save或改活动修订。重试需维护者、expected_version及可重试错误；429/超时/5xx可重试，格式/鉴权/配置先处理。

解析/原图存MinIO，图摘要按hash/上下文/模型/prompt复用，嵌入按批次hash持久。MinerU分段batch挂worker-cache，恢复原卷，不删除成功段付费重跑。最终指针CAS附资料attempt/token/期限，验证原件/来源/索引后才发布。completed重复投递不再发布；已发布但任务终态保存中断会核对修订后结束。

真实隔离结果与限制见[09](../development/records/M2-09.md)/[10](../development/records/M2-10.md)。只强停新测试worker，未故障注入源数据库；供应商响应至缓存落盘有计费窗口，不承诺exactly-once。生产灾备与全库迁移未验收。
