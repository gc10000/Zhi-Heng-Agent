# M6 attributed_assertions_v1 有界真实诊断草案 r1

2026-10-31；**仅草案，本包不调用、不创建实验／评分／proof。** 先总控独立复核本技术包，再确定新源码／prompt身份和实际生成可比性。固定一套通用策略，不试第二条规则、不重跑旧v2追求过关。

## 固定范围及预算

由完整30／9／5矩阵去重23题，加4个对象／配件对照，共每版27题。047仅正式路由／呈现无生成对照；其余26题，两版本合计**最多52个新增逻辑stream**。不生成新基线、不运行heldout，不将子集当完整85题质量证明。

- m6-g540-02-a
- m6-g540-02-b
- m6-g540-03-a
- m6-g540-04-a
- m6-g540-04-b
- m6-g540-05-a
- m6-g540-05-b
- m6-g540-09-a
- m6-g540-09-b
- m6-g540-10-a
- m6-g540-10-b
- m6-g540-11-a
- m6-g540-17-a
- m6-g540-17-b
- m6-g540-18-a
- m6-g540-19-b
- m6-g540-20-a
- m6-g540-unknown-01-b
- m6-g540-unknown-03-b
- m6-g540-unknown-04-a
- m6-g540-unknown-04-b
- m6-g540-unknown-05-a
- m6-g540-unknown-05-b
- support-v1-008
- support-v1-030
- support-v1-047
- support-v1-048

保持现有模型hash `565fbfe4c795fb52f84183f7b2708491fd7824fa07f2de9fd546e9d6d6e5bb90`；实际模型名、参数及版本须在启动前从正式runtime核验并固定，不从hash猜测。保留weighted及20／20／20／20／10、原答案窗口32768／输出4096／预留256／字符12000。上限52×4096=212992输出token；输入预算上限52×28416=1477632（预算计数为字节保守上界，不是实际usage）。价格／精确HTTP不可观测为null，不承诺0费用。若当前可用模型身份、付费授权范围或使用上限变化，停在调用前；已有授权不重复询问。

只复用严格匹配的向量／重排缓存与封存候选；缺任何pair／prompt/context匹配立即停止，不补编码／重排、不导入。答案缓存只在新prompt、模型、输入、源码及来源全等时可复用；旧答案仅作对照，不计为新策略输出。

## 正式身份与来源

先新目录冻结两份diagnostic配置，固化最终提交、app源码树SHA、全部prompt树SHA、模型SHA、dataset／manifest、两个题集精确版本、原始四文档／隔离修订／chunk／reviewed p30 proof、source terms／组合scope及新evidence_attribution。parameters草案已保存但不是正式生成冻结；不得沿用旧v2的versions值。

`runner.select_questions`允许冻结dev非空子集；正式`DevelopmentPolicy.validate_candidate`要求与已校准基线subjects全等，故**27题子集不能挂85题旧校准冒充正式候选**。先将本草案作为独立诊断方案审阅，正式执行如采用EvaluationService／execute_job，应登记新的受控诊断config/catalog，使用无quality_policy／无旧calibration／无regression_source的非验收实验；旧记录为provenance对照，不作为“已验证父候选”。不得为绕门禁删除正式候选必需字段；该模式只能产出诊断证据，不能获得development gate或feedback proof。

两版原候选experiment／Run／subject／prompt／答案hash与题号的来源映射，从本包矩阵及170保存结果冻结到不可变诊断manifest；该manifest连同新config／模型／prompt身份计算诊断source SHA，纳入稳定client_request_id，并在运行输出逐题对照。正式请求只使用现有schema，不发明parent字段；旧实验关系明确是封存对照，不能冒称continuation继承。若总控要求直接形成正式质量证据，则必须另行裁定完整85题同范围的配置可比性与校准引用，**不在本草案自动扩展170生成或重生成基线**。

请求键固定为 fingerprint([diagnostic-source-sha, version, 'attributed-diagnostic-v1'])；实验实际UUID、attempt／version和每题稳定checkpoint由现有服务生成保存，不手写state／lease／retryable。相同键只消费同身份完成Run；中断用正式恢复／continuation协议，核原执行关联、输入输出与prompt_reference_map，不因新源码继承旧19或旧v2检查点。新实验、Run及题级输入与旧来源manifest逐项关联，模型调用前先核本题请求身份及预算。

## 记账与停止线

调用前逐题持久写planned键／来源／配置／预算；正式Run执行记录累计逻辑stream与本次adapter新增stream，复用完成Run应累计保留、本次新增0；合并先前失败/未知窗口，不根据结果行数推断调用0。供应商usage有则记录input/output，缺失为null；HTTP／费用不可见始终unknown/null。调用后保存前崩溃保留unknown窗口，先正式恢复查既存Run，不自动再次请求。

零生成预检必须证明047仍澄清、未见越权引用、25题35单元既有回放保持且诊断范围所有缓存命中；任何缺缓存／来源漂移／预算变化／错误引用映射／非重试终态／生成后资料仍不完整，保存首个失败并停止，不试词、不变阈值、不换规则或用补审改旧分。完成后先逐题原件诊断新输出，不自动追加真实审核子Agent；后续真实独立双轮及总控来源核验另按既定流程，不能把本执行分析当新独立来源。

本草案不创建proof。有效同范围候选质量门禁成立后，才走原服务端反馈proof；04已验收保持，05／08未验收，M6 5/7、M7不启动。
