# M6比较答复执行归属修复与单题预调度复核 r1

日期：2026-11-02

## 结论

**执行身份接线修复完成，定向测试通过；唯一048授权在正式实验创建前被配置登记冲突阻断，按fail-stop封存。没有真实答案，未关闭产品质量或M6阶段。**

修复解决评测账号与知识库owner分离时的错误拒绝。新任务记录其冻结知识owner；执行关联使用评测发起者作为job owner，并校验冻结owner、KB、有效维护角色和租约。失败父Run恢复按评测发起者查找，不接受改owner、失效权限、过期租约或旧记录缺失冻结归属。比较风险合同、批次、槽位及Git授权路径统一到本次r2身份。

## 验证

- 离线单元与契约：1512 passed，6条既有依赖/序列化警告。
- 隔离Mongo正式job、同库/分库来源恢复和完成Run观察复用：48 passed。
- 补充owner/权限/租约及撤权后续接矩阵：10 passed。
- `git diff --check`通过；测试库使用随机`m1_test_m4_`命名空间。
- BGE-M3与bge-reranker-large使用已有本地权重。冻结model、prompt指纹及当前最终代码指纹匹配新的离线execution manifest；无模型推理。

## 单题预调度停止

用户授权对象为完整反馈派生题集`fb-07c584730833908571fe9dd7c7c890afa3cf9e66`中的`support-v1-048`，最多一个provider stream，接受费用上限未知，并要求首失败停止。正式只读预检确认维护者具有该KB维护权限、题集数据和manifest身份匹配、旧source-relation 048仍blocked且无未知窗口、新输出预算账户及experiment/result/slot/Run/outcome均不存在。

实际预调度脚本在调用`EvaluationService.create_experiment`前重复调用`register_set`。同一冻结题集版本已登记且dataset/manifest hash正确，但历史descriptor的config白名单与新r2配置不同，重复登记触发`eval_set_version_conflict`。这是本地调度编排错误，不是embedding缺失，也不是供应商失败。该调用未创建experiment、slot、结果或Run；provider请求/stream、本地推理、正式输出预算写入和新增usage均为0。Mongo只读计数仍为experiment/result/slot/account均0。

按授权fail-stop，在全新风险批次/成员槽写入唯一halt证据；该槽不可重领，未修改旧blocked账户。私有预调度脚本、完整trace、输入和测试日志留本机`output/m6-comparison-answer-048-execution-r3/`及`output/m6-execution-owner-fix-20261102-764061/`，不提交。

## 状态边界

本轮没有048模型答案、评分、候选、反馈复评proof或阶段proof。累计历史usage仍53089/30412；本轮增量0，reasoning、精确HTTP、费用及付费输出上界仍unknown。M6保持5/7：M6-04已验收并保留，M6-05缺真实反馈复评proof，M6-08缺有效候选质量和阶段验收证据；43题继续暂停，heldout65未运行，M7未授权。原句摘录不等同完整比较回答。

该批次r2授权已在本地封存停止；任何新执行需新的单题授权、身份与槽位，不得以删除halt、重用request id或直接跳过题集descriptor检查恢复。
