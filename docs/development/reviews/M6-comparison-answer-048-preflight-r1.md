# M6-048单次验证前置核验记录 r1

日期：2026-11-02

## 结论

用户授权按单题预算执行一次 `support-v1-048` 比较验证，接受费用上界未知并要求失败即停止。本轮完成正式身份与旧账只读核验，并发现、修复一处阻止正式控制库绑定的风险档案缺陷；但正式执行前的 `runtime_versions()` 必需门因本机embedding与reranker权重目录均不存在而失败。为避免消耗唯一执行槽，本轮在创建正式Git授权、manifest、experiment、slot、Run之前停止，未发送模型请求。

状态：**未派发、没有答案质量结果；单题授权的模型请求额度未消耗。** 本记录不构成M6阶段验收或独立关闭。

## 定向核验

- 官方catalog、配置哈希与已登记题集匹配，题集为150题（85 dev、65 heldout），本配置只选dev题 `support-v1-048`。
- 正式maintainer仍持有该知识库权限；正式控制库中用户与题集各1条，experiment/result/slot/Run/execution-link/outcome/输出预算账本均为0。
- 已消费source-relation 048账户与保存快照一致，保持blocked、无pending、无unknown窗口且仅有原消费槽结算；没有读取或改动其凭据及终态。
- 当前端点规范化指纹与已审profile相符。执行入口 `app/evaluation/query_adapter.py` 在检索前要求当前 `runtime_versions()` 与冻结配置完全一致；本机配置的 `BGE_M3_PATH` 和 `BGE_RERANKER_LARGE` 对应目录均不存在。对本机现存的候选模型目录只读重算后，代码与模型fingerprint均不匹配冻结配置，prompt fingerprint匹配；因此改用候选路径仍会在正式job执行前拒绝。没有修改路径或配置。
- 比较输入不能使用保存输入回放里的合成答案或不完整输出。没有创建替代正式输入、实验或Run来绕开runtime前置。

## 已修复的准入缺陷

风险档案此前把本次EvaluationService控制库强制要求为来源执行母清单的数据库。正式M6控制库与历史来源实验库不同，这是受控分库，不代表题集或知识主体漂移。现由专用048授权显式绑定本次 `evaluation_control_database`；共享成员构建继续校验冻结owner、KB、题集、题目、配置与源码身份。其他风险档案未定义该授权字段，保留旧数据库比较行为。

测试先复现正式控制库被拒绝，再验证跨库授权可冻结并通过配置核验、错误数据库仍拒绝。定向单元与关联隔离回归结果见[摘要](M6-comparison-answer-048-preflight-validation-r1.json)。这是实现方自验，尚无独立技术复核结论。

## 执行与质量边界

本轮新增模型/产品stream 0，本地embedding/reranker推理0，正式Mongo写入0，新增usage 0；累计usage仍为输入53089、输出30412。候选目录fingerprint只做文件hash，没有载入模型或执行推理。reasoning、精确HTTP、费用及付费输出上界继续unknown/null。没有真实048回答，不能评判其是否完整回答比较题。

M6保持5/7：M6-04继续验收；M6-05缺真实反馈复评proof；M6-08缺有效候选质量和阶段验收证据。原43题继续暂停，heldout 65题未运行，M7未启动。下一步先恢复与冻结版本完全匹配的代码与本地embedding/reranker权重，或为新身份重新冻结并复核完整运行配置；在完整runtime指纹、风险档案修复独立技术复核和来源输入全部匹配前，不建立正式执行身份、不重试本单题。
