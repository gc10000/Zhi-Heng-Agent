# M7 operational r2任务记录

用户明确批准r2新批8stream及1位新独立审查者，新增本地范围14文本/8rank/48pair。已实现默认关闭v2新身份与独立本地限额、实构建并通过独立导入准备检查。正式导入时Mongo读取取消触发STOP，provider0；本地仅可证6文本预留，完成unknown，历史job因自动租约恢复进入attempt2。

已用真实合成库红测复现、最小修复持久IMPORT_MAX_ATTEMPTS、领取/重排/手动重试/展示边界，12项定向及原恢复兼容通过。补修不改历史、不部署恢复本批。独立审查和最终构建/验证收据见[执行报告](../reviews/M7-operational-r2-execution-r1.md)、[validation](../reviews/M7-operational-r2-validation-r1.json)、[独立报告](../reviews/M7-operational-r2-independent-review-r1.md)。

运行消费者及宿主已停，generation=false；真实问答/恢复08/容量/完整演示未运行，无新阶段勾选。下一项为Linux目标上的全新身份导入前限额方案；旧r2永不恢复。保留output、全部失败、模型、数据库、原Run与tmp，不合并main或公开发布。
