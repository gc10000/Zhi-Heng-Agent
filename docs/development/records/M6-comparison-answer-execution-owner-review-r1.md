# M6比较答复执行归属补修记录 r1

日期：2026-11-02。性质：实现与执行方自验，等待另一审查方独立复核；不构成阶段验收。

## 修改

- `evaluation_experiments.owner_id`继续表示提交任务的maintainer；创建时另存config冻结的`target.owner_id`为`knowledge_owner_id`。
- 执行链接依据job身份/租约检索experiment，以冻结知识owner匹配目标；跨主体时再次检查发起人当前enabled角色和KB授权。
- continuation父实验按评测发起人查找，同时验证父实验冻结知识归属，避免恢复路径将发起人误当知识owner。
- 比较合同的authorization path、risk profile batch/slot/ledger统一到用户本次批准的r2单题身份。历史r1材料保持不变。

## 验证与失败

1512单元/契约、48正式隔离job/恢复及10项权限/撤权集成通过。初期风险合同path测试1项失败，原因是解析器常量仍引用r1；修正后全量离线通过。初期恢复矩阵2项失败，暴露恢复按KB owner查找父job及续租筛选与既有交接上下文不一致；修正后分库/同库恢复、Run复用通过。失败原件留在本机私有验证目录。

执行授权的正式只读预检确认已登记完整题集与dataset/manifest身份一致，受限maintainer仍对目标KB有权限，旧source-relation 048仍blocked且无pending/unknown，新账户和experiment/result/slot/Run/outcome均不存在。唯一预调度尝试脚本随后对已登记题集版本重复调用`register_set`，因历史descriptor配置清单与r2执行配置不同返回409 `eval_set_version_conflict`。问题发生在创建experiment之前；没有provider HTTP/stream、本地embedding/reranker推理、正式质量写入或usage增量。

遵循“失败即停止”后写入本机r2批次halt证据，校验哈希`59e04d769ca3fcd7137fb6f37577de7b1d4c15834f0c74b3189136b868c2dc0c`，不得重试此授权槽。调度脚本尝试、完整异常日志及私有输入均保存在ignored `output/`，不上传。

M6保持5/7：04已验收并保留；05缺真实反馈复评proof；08缺有效新候选质量和阶段证据。无新048答案，不改变43题暂停状态，不运行heldout65，不启动M7。
