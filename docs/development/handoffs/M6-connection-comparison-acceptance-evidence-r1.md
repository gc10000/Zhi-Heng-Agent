# M6连接比较补修的独立技术验收交接

本文件是准备就绪的审查范围，不是独立通过结论或新模型调用许可。当前实现总控不签独立通过；用户禁止自行委派子Agent。分支`codex/m6-source-bound-comparison`，以`e3178ca80540b9845d10ad79b2a8b7d86d38ae13`为本轮差异基点。先读[报告](../reviews/M6-connection-comparison-acceptance-evidence-r1.md)及[摘要](../reviews/M6-connection-comparison-acceptance-evidence-r1-validation.json)，保留上一包及既有关闭结论。

## 唯一审查矩阵

最新接续：先读[结束与生命周期补核报告](../reviews/M6-connection-comparison-terminal-review-r1.md)及[摘要](../reviews/M6-connection-comparison-terminal-review-r1-validation.json)。其基点为657e87f；上文e3178ca是第一次补修的差异基点，**e3178ca初始新模式实施包也尚未获独立通过**。独立验收应覆盖[初始实施包](../reviews/M6-connection-comparison-implementation-r1.md)、第一次补修与本次终止边界累计范围，不能只审最后几行。只核新模式及受影响旧出口，不重开已独立关闭协议。

| 检查 | 源码／证据入口 | 退出条件 |
| --- | --- | --- |
| 正确装配先于调用前记录 | `QueryRunner.assemble_connection_context`、`evidence_prompt`、`comparison_inputs.freeze_input` | 原完整池逐payload核验、介绍和完整子条件、必要预算通过后才首次冻结；不能从篡改恢复Run补签 |
| 第一次outcome之前的协调删来源 | `test_first_outcome_recovery_rebinds_sources_without_new_call`的coordinated_deletion／delete_condition，同库和分库 | 介绍或子条件删除且所有Run自证字段重算，冻结配置和原调用前记录保持时拒绝；不产生outcome，不追加调用 |
| 持久锚完整性和故障 | missing／changed_input_checkpoint、write_failure用例 | 无记录／记录漂移拒绝；写入失败在模型0调用时失败；重复相同冻结不覆盖原记录 |
| 缓存及生成静默降级 | `test_coordinated_source_deletion_cannot_push_cached_answer`、`test_comparison_mode_cannot_be_disabled_after_input_freeze`、缺guard／来源生成中漂移用例 | 先验证输入和模式，再推送或调用；无自由答案绕过；进程闭包不当作持久恢复证据 |
| 渲染无无关术语 | `test_renderer_does_not_add_media_or_web_absent_from_sources`与现有语义反例 | 仅输出资料支持的介质、端点、用途、限定及可归因的比较；不补写Cable／Web，不把客户端访问当上联 |
| 正常与旧路径兼容 | 55项隔离Mongo（35新、20旧），252项离线／契约 | 同／分库成功复用、首次恢复、断流raw、故障结算、默认关闭、旧比较／原句选择／OpenAPI保持 |
| 本次调用正常结束 | 最新新模式stream／invoke、异常／缺失／陈旧／冲突结束、终止后正文和空用量帧用例 | 必须本次观察stop且无异常；展示前拒绝不合格终止，raw保留，无额外调用；正常空尾帧保持 |
| 结束持久化与恢复身份 | 最新65项隔离Mongo、275项离线／契约 | 成功Run保存结束原因，缓存及首次outcome前恢复核验；仅显式新模式outcome身份新增结束原因，旧投影不升级 |
| 调用前记录重复／冲突 | 同／分库repeated_freeze_and_conflict用例 | 相同输入幂等且仅1记录；不同输入不能覆写原记录，正常Run仍只1次合成调用 |
| 原048逐分句核源 | 本机新目录`four-cell-r2/D-private.json`、`clause-audit-r2-private.json` | 同一冻结双资料333成员投影，10条prompt文档；LA管理3G/4G到AC、CB融合和Cable接入侧限定比较、分型号引用均有依据；不发明同用途同角色门槛，不把程序输出算正式模型质量proof |

私有材料在本机`output/m6-connection-acceptance-evidence-20261103-r1/`。`checks.py`已审阅，使用随机短测试库名；所有脚本有写入，若再运行先复制适配到全新目录，不覆盖任何红／绿日志。不得读取private-identity或输出.env值，不扫描真实库、修改真实Run／lease／slot／blocked账户。

## 独立通过之后的真实验证准备范围

只准备`support-v1-048`单题新身份方案，不恢复43题、heldout或M7。对象仍为反馈版本`fb-07c584730833908571fe9dd7c7c890afa3cf9e66`的原问题；采用新connection模式，范围和完整输入必须冻结成新的正式catalog，不能把当前333成员双资料离线投影冒充原四资料582成员全scope。与r8相比来源装配及语义都已改变，不能声称仅改一个提示词；若比较新旧消费者，须以相同装配输入为对照，唯一差异为消费者版本。

计划中必须一次交齐：精确源码／来源／模型／策略版本和输入hash；新的请求、实验、题级检查点及Run绑定；幂等和缓存身份；独立调用前记录及首次outcome前恢复；新槽预留／started／settled与本批次及累计分账；最多一个stream、不重试、首失败停止；usage缺失使用null、reasoning／HTTP／费用未知保留unknown。当前保存输入预算为32768窗口、4096输出预留、256保留、12000字符、10条文档，字节上界计数输入10340，输入硬约束28416。它是离线提案依据，不是已授权预算或真实token用量。

质量退出按原rubric判断是否**完整回答比较**：必须有双方限定结论、LA到控制器的管理连接和互通限制、CB融合及Cable侧路径、分型号引用，不能仅列摘录或用“不足”当通过；同时不能把不同角色拼成同用途或断言现场连通。原正式评分、r7/r8质量拒绝及blocked/halt保持。

本轮没有新048授权，不创建正式新请求、实验、Run、槽、候选、分数或proof。独立技术验收与新真实质量验证仍是两个不同步骤。
