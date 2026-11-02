# M6-048授权正向来源绑定合成复核 r1

日期：2026-11-02

## 裁定

**授权正向代码路径的合成验证通过；真实Git授权、供应商执行和答案质量仍开放。**

本轮只增加测试与审查材料，没有修改生产实现。测试在pytest临时目录构造冻结题集、split manifest、原始执行输入、master、历史usage来源和唯一成员，并使用合成Git引用。Git读取器本身保持真实，只将底层`git show`进程输出替换为合成授权字节；GitEvidence字段校验、固定commit/path参数、SHA-256内容核验、冻结来源文件hash及risk档案逻辑均实际运行。

## 核验路径

使用真实`comparison_answer_048_risk`函数完成：

- `sources`校验授权类型、function/batch/member身份、完整题集及原执行manifest文件hash、题级输入hash、配置/result/prompt hash、模型runtime和预算。
- `authorized_inputs`从临时完整题集重建版1第27项`support-v1-048`输入，核验dev分割和题级执行manifest关联。
- `build_manifest`将唯一成员、原始请求、题目输入指纹、配置身份和历史usage receipt组装为冻结计划。
- `prepare_manifest`在临时目录完成计划和题级计划的独占写入；同一计划可读取，改变计划后拒绝覆盖。
- `require`和`validate_config`通过冻结manifest hash验证请求；改题或改target collection均被拒绝。
- `validate_prompt`接受完全一致的prompt/context/reference map/evidence groups/budget，并拒绝prompt漂移。
- 篡改冻结source input后，`sources`因文件hash不匹配而拒绝。

## 验证结果

- 新增授权正向/漂移测试：`2 passed`。
- 9个相关单元模块：`166 passed`，1条既有Pydantic序列化警告。
- OpenAPI契约：`2 passed`；`compileall app`与`git diff --check`通过。
- 红测与夹具修正：首轮测试发现夹具缺少冻结题集计数；后续验证先发现测试错误地耦合中文错误文本及Windows `Path`/字符串类型。已修正测试夹具/断言；没有发现生产路径缺陷。过程摘要保留在本机`output/m6-comparison-answer-048-forward-review-20261102/`。

## 限制与下一步

合成测试没有证明授权SHA对应的真实Git对象存在，也没有读取新的正式授权文件或正式catalog；没有运行Mongo正式job、客户端真实构造/供应商HTTP、模型stream、Run/outcome或答案评分。本轮真实模型调用、本地推理、正式评测库写入均为0。因此它只关闭“授权材料正向数据形状在风险档案中可被处理、冻结和后续复核”的代码路径子项，不等于授权、运行许可或答案质量通过。

M6保持5/7：M6-04保持已验收，M6-05缺真实反馈复评proof，M6-08缺有效候选质量及阶段证据；43题继续暂停，heldout 65题未运行，M7未启动。下一步仍须另有正式新授权与模型身份核验，之后才可裁定是否进行单次048真实验证；真实比较结论须按完整回答目标评价，原文摘录不能替代答案。
