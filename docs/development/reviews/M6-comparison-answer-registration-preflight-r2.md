# M6-048已登记题集复用预检 r2

日期：2026-11-02

## 结果

修正预调度流程：不再对已正式登记的同一题集版本再次调用`register_set`，只读复核现有descriptor，再走`EvaluationService.create_experiment`的冻结dataset/manifest比较和服务端catalog配置解析。

新的只读预检通过。维护者对目标KB的权限仍有效；完整题集版本`fb-07c584730833908571fe9dd7c7c890afa3cf9e66`已登记，dataset及manifest hash与本次配置一致，登记的config列表不含本次r2 config。当前创建服务比较descriptor中的dataset/manifest身份，配置由受控catalog独立resolve；重复register是多余动作并造成原409。正式experiment、result、新预算账户、活动slot仍为0；旧source-relation 048仍blocked。此次预检不写正式库、不推理、不调用provider。

该读路径验证不能解封r2批次：r2 `halt.json`仍有效，授权明确要求失败即停止。后续实际尝试必须另有明确的新单题授权、全新Git授权身份、风险批次和slot；不能删除halt或重用r2槽。

## 验证边界

机器摘要在[validation-r2.json](M6-comparison-answer-registration-preflight-validation-r2.json)，原始只读输出和首轮脚本异常仅保存在本机`output/m6-comparison-answer-048-execution-r4-preflight/`。首轮错误为摘要代码在MongoClient关闭后读取计数；已修正查询时序后只读复跑通过。原预调度409、r2 halt和相关私有材料保留。

下一步唯一范围为在新的授权身份下复用现有题集descriptor、不重复登记，并只对`support-v1-048`创建一次新实验；同一份题目、prompt、模型、参数和输出预算保持冻结。任何真实模型调用仍待新授权，M6仍5/7；本报告不提供答案质量结论。
