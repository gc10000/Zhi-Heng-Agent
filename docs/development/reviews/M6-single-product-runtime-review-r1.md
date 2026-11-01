# M6唯一05-a环境与临发身份总控核验 r1

日期：2026-11-01，Asia/Shanghai。角色：总控独立只读核验，不代执行产品调用，不是答案评分或阶段验收。

## 当前裁定

启动HEAD与缓存origin/main均为`ab2e1d5f4f3e7a5c767d8c6768e5477c9fe8f379`，工作区仅tmp。已读r3实际失败、摘要、r2驱动失败与修正版，保留d41b3a4对准入、最终集成及精确消费者的关闭，不重跑75项集成或54／25题准备。

**r3的服务不可用阻塞在当前时点已解除。** 本轮首次检查Docker已启动，4项基础服务健康，Mongo仍启动中；不是本总控启动或重启Docker。首次只读Mongo审计遇连接关闭，原失败日志保留。后续日志显示WiredTiger恢复完成，进程无OOM／重启，观察到启动期CPU／读盘活跃；等待后Mongo转healthy。现5项基础服务全部running／healthy，实际日志配置仍20m×3，D盘首次检查可用约126.06 GiB。本轮未清库、改参数、启动worker或恢复旧job；不宣称证明了此前Docker为何退出，亦不宣称所有7个历史容器均运行。

## 真实只读结果

| 范围 | 本次结果 |
| --- | --- |
| Mongo实际连接及正式主体 | ping成功；沿现有公开主体字段核maintainer／admin及原kb权限，无提权、不读private-identity |
| 同一正式请求／配置 | request与config各自查询实验记录均0 |
| 固定账户 | 在目标库同时按固定账户key和合同hash查，均0；分库控制侧同key亦0，未仅按新合同hash漏查冲突账户 |
| 关联／检查点 | 目标执行关联按配置和合同分别为0；精确题级checkpoint为0 |
| 磁盘固定槽 | 审计前后started／settled均不存在；planned／code-plans不改 |
| 完整题集 | 正式descriptor存在，dataset／manifest匹配，总数150、dev85；不把题集缩为单题 |
| 输入与运行身份 | app源码b50b1f5b…、runtime、prepared配置／请求、封存Git授权、prompt、context、reference_map、groups及受审关系全等，保存预检收据hash匹配 |
| 修正版私有驱动 | 与r3封存hash一致；只离线提取其完整题集断言，150／85正例及两反例共3项通过；没有运行执行驱动 |
| 历史保护 | 138／336／597／1314组逐文件hash匹配，组间重叠；2415项身份、来源、保护与状态检查通过，不计为质量分 |

账户状态现为`absent_by_current_read`，不同于r3当时的`unknown_unreadable`；r3的历史记录保持原样，不回填旧摘要。该结论只针对本次读取时点，不能代替临发正式job的原子claim、CAS预留和固定槽独占创建。

私有证据：`output/m6-single-product-runtime-review-20261101/`，含首次失败readonly-audit.log、Mongo启动尾部样本、成功readonly-audit-r2.log、current-counts、audit／checks、service-after及只读脚本。新目录保存，不覆盖旧失败，不上传日志或原始数据。脚本仅使用Mongo读取；没有创建EvaluationRepository等可能建立索引的真实写入对象。

## 身份、分账与限制

- app源码：`b50b1f5b0eab66d7a4eb2a32314bcd415dba2624354cfb0ece59d2efce17ab8b`。
- 配置canonical：`22d0e525ba1074336a6d7af973cc50427eb96e4c3f5ad28d9a3c60e37ff65efc`；manifest：`0e94544429f865b2f2e35193f9f915e06282de9c1faf85fafe27d4891bb85533`。
- 修正版驱动SHA256：`f45e94989079eab370d971ff0a4004f3d87747890c262ff5480582b23069e19d`。
- 本轮新增产品stream、本地推理、token及真实数据库写入均0；诊断前值23582／20602保持，非全项目累计。精确HTTP／费用null，付费输出上界unknown、网关能力unknown保持，不登记verified。
- 未全量扫描向量、业务库内容、默认指针、run_events或TTL。未新增正式评分、候选、attest、校准、gate、proof，原48 job暂停，M6 5/7，04保持、05／08未验收，M7未授权。
- 本轮GitHub直连连接被重置，本机原配置代理7890不可达；不能以缓存origin/main宣称本轮已核远程，最终提交推送另记。未改永久Git代理。

## 直接接续，不再等待同一批准

执行方现在可沿[原完整授权](../handoffs/M6-single-product-canary-r1.md)及[维护后接续](../handoffs/M6-single-product-canary-resume-r1.md)使用现有`execute_canary_r2.py`。只做紧邻发起时的服务／同槽／账户／输入只读核验；身份一致、无消费或未知窗口后，通过既有正式接口创建并执行唯一版1`m6-g540-05-a` job。不得直接插库或重置state／lease／slot。

仍是最多一个产品stream，n1、max_completion_tokens4096、原profile与预算不变；一次结果无论成功、空答／纯reasoning／截断、usage异常或语义失败均封存即停，不重抽、不自动接续原48题。没有新增授权审批节点，不要求重新查PDF、账号或评分。

本轮总控完成环境与当前消费状态的核验；下一实际交付应是唯一05-a正式job的真实结果或新的明确运行失败。当前没有新答案，不能据此声称质量改善或扩大范围。
