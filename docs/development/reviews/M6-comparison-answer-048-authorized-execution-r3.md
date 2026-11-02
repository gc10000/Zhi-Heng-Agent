# M6-048新授权r3执行前停止报告

日期：2026-11-02

## 结论

**新单题授权已在provider派发前按“失败即停止”封存；没有真实模型答案，048答案质量仍未知。** 本报告不关闭M6阶段。

用户授权仅对`support-v1-048`执行一次，最多一个模型调用，接受费用上限未知，失败即停止。新Git授权位于[授权文件](M6-comparison-answer-048-authorization-r3.json)，提交`4a49b6a`；批次`m6-comparison-answer-048-risk-r3`、槽`m6-comparison-answer-048-r3-support-v1-048`。旧r2 halt保持原样。新执行脚本只读取已登记题集descriptor，不再重复`register_set`。

## 停止原因

离线输入冻结及第一次正式只读预检通过：题集`fb-07c584730833908571fe9dd7c7c890afa3cf9e66`的dataset/manifest与已登记descriptor匹配，maintainer有KB维护权限，完整输入和prompt匹配；BGE-M3/reranker指纹匹配。experiment/result/slot/Run/link/outcome和新预算账户均为空。

随后在最后的调用前检查中，配置冻结源码指纹`26212526c3be318c51ce7a5725e103f78bbc57c456b1e47bd17500dc64b5ae65`与最终工作树源码指纹`7e3ba59d194934c41e593c161aefcd94279c4ab4e629fad597ffe462321fad25`不一致。原因是清单准备后又修改了参与指纹的Python文件注释。准入在Mongo读取和实验创建之前拒绝。按授权封存r3 halt，不以重算清单或重试消除失败。

## 验证与计量

- 定向单元/契约：53 passed。
- 比较风险账本隔离Mongo：5 passed。
- 评测归属/恢复隔离Mongo：24 passed。
- 代码/私有脚本compileall与`git diff --check`通过。
- 初次集成启动因工作树未加载根`.env`而在测试fixture取`MONGO_URL`前失败；未连接Mongo或写库。显式静默加载根`.env`后，同组测试通过。
- 本授权attempt：provider request/stream 0，本地推理0，正式experiment/Run及业务库写入0；新增usage 0。历史usage仍53089/30412；reasoning、精确HTTP、费用和付费输出上界仍unknown。

私有冻结输入、清单、预检和停止证据保存在本机`output/m6-comparison-answer-048-execution-r5/`及`output/m6-authorized-products/m6-comparison-answer-048-risk-r3/`；旧`execution-r3`重复登记失败原件未改。机器摘要见[脱敏验证](M6-comparison-answer-048-authorized-execution-validation-r3.json)。

## 阶段边界

M6保持5/7：04保持验收；05缺真实反馈复评proof；08缺有效候选质量与阶段证据。43题暂停，heldout65未运行，M7未授权。没有答案，不能评判比较结论或回答完整度。
