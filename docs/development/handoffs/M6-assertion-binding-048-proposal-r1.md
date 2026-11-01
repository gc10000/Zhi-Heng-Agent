# M6原句选择048单次验证：受阻条件性规格 r1

日期：2026-11-01。**仅为方案，不是执行Prompt、调用授权或已登记配置。** 当前真实推理预算0，R1／R2尚open，43题暂停。本规格只有一种策略变量，不提供候选供应商、预算或提示词试错分支。

## 适用性与阻断

当前`assertion_binding_v1`要求模型只选编号，程序呈现完整原段。它能限制自由断言，但固定renderer没有生成完整比较结论。保存输入的合成全选回放已证明“完整摘录”与“完整回答”不同；不能拿所选原文替代对048关系问题的明确、正确且完整回答。

技术前提：先完成[复核矩阵](../reviews/M6-assertion-binding-execution-review-r1.md)R1冻结来源恢复核验及R2断流材料持久化，保留红测并定向复核最终hash。产品前提：维持原完整比较退出条件，证明本输出形态适用。**若仅能作为证据摘录视图，则本048比较验证方案不生效，不调用模型，也不修改门槛或再补提示词。** 后续任何真实调用须有独立明确的新授权，本文件不沿用旧048授权。

## 一个拟定模式与身份规则

模式拟名`diagnostic_assertion_binding_048_v1`，提案版本`r1`；归属策略版本仍是`assertion_binding_v1`。前者未实现／未登记，后者是本轮已审实现。不得将拟名写成能力verified或已有账户／槽身份。

唯一变化是启用严格原句选择协议及对应程序呈现。模型、非思考设置、原检索候选／分数／排序、weighted 0.5／0.5与20／20／20／20／10预算、源上下文、分组、引用、完整题集和原问题保持。冻结归属、source_relations及已有受审对象证明继续精确消费；不重签001，不做实体词分类或把connection猜成上联。

运行对象仅为**版1 support-v1-048**。owner、control、target、kb从受控master manifest及上一正式048身份材料只读提取并核hash，不按库名推断，不换owner领取额度。使用原完整dataset及split manifest，不缩成1行伪造题集；选择单成员在正式配置question_ids层完成。subject／reviewed_subjects仍按完整Git证明和成员消费，不新建registry。

未来获准后，所有实体必须由正式接口产生并封存：

- 先冻结最终源码／模板／完整归属策略、完整dataset／manifest、目标身份、精确请求及授权Git blob。manifest必须包含父请求与失败结果的只读来源hash，不能把旧Run标成新模式。
- 新请求键由`新模式版本＋完整配置canonical SHA256＋题级输入SHA256＋question_id＋授权blob身份`生成。只可增加一次封存的命名空间；同义nonce、目录、控制库或ledger更换不能重获额度。
- experiment_id、Run ID和题级checkpoint ID由EvaluationService／正式执行链分配，执行前从实际返回封存；本规格**没有已登记ID**。配置／Run／checkpoint／execution link必须绑定完整策略及hash、最终源码、run_input_sha256和该题来源。
- 新固定slot／新账户／新检查点与旧已消费槽、blocked账本／账户、旧output_contract及旧answer proof完全隔离；沿既有正式CAS、租约、Run关联及操作系统独占started实现，不私改state／lease／retryable／pending。需有新模式正式门禁与定向自验，不能用方案名绕过现有unknown拒绝。

## 精确输入证据锚

本轮回放文件：`output/m6-assertion-binding-review-20261101/replay-r1/inputs/v1-support-v1-048.json`。

- 文件SHA256：`d7a9419132afd2a63a9f9beed855a78a1ba5a6d3b92cce1148a3d4035803f348`。
- prompt原始UTF8 SHA256：`50aae51ac20ceeef6b7368eeed7bb77b30b83b0071c18035516bebc7e1987175`。
- prompt canonical fingerprint：`d14ee996739c36732866ec561dfe99328918487b517e5ccb2e9bf3e5fede8f77`。两种prompt hash算法不能混用。
- 10个context、10组，原引用编号及完整原段保留；保守输入14169，limit28416，输出预留4096，reserve256，未省略证据或历史。
- 父输入来源：`output/m6-source-relation-role-boundary-review-20261101/replay-r1/requests/v1-support-v1-048.json`；继续追溯受控master及原完整dataset／manifest。精确hash必须从这些原件及新冻结manifest读取，不凭本规格补造。

**该回放文件不可派发**：budget中仍有旧`diagnostic_total_output_v2` unknown草案、max_tokens及旧账本前值。仅prompt／context是证据锚，不允许复制合同、实验ID、账本或synthetic_selection／synthetic_render／proof作为新结果。未来正式合同变化不能改变已审正文；若最终输入不全等，停止重新审定，不能临时编码／rerank或扩大预算。

## 固定runtime与计量提案

如未来明确授权，保持qwen3.8-flash、n=1、temperature=0.1、enable_thinking=false、stream＋usage、SDK retries=0、timeout120秒；langchain-openai1.1.11／openai2.28.0，extra_body.max_completion_tokens=4096且无max_tokens，无fallback／redirect／reasoning_effort／额外budget。endpoint仅核既有hash，不输出实际URL。context32768／output4096／reserve256／max_chars12000保持。installed SDK wire须用精确输入Mock核对；Mock不证明网关遵从。

新增最多**一个stream／attempt**，不得再加非产品探测。拟input预留上限28416，output观测限制4096；精确prompt保守输入14169需在正式消费者再核。当前前值53089／30412，若仅做该上限提案，拟观测累计为81505／34508；**这是预算算术，不是获准额度或实际付费硬上界**。原累计预算1477632／212992是否由新授权继续引用，必须在新封存授权中明确，不能把剩余额度直接当许可。

能力status／semantics及server hard limit保持unknown，4096仅请求和观测限制。新账户独立分账，同时关联历史累计，不把旧消费清零。reasoning已含在output内，不重复相加。新增实际usage、HTTP次数及费用在调用前为unknown／null；HTTP／费用不可观测时仍null，不能用结果行数、缓存命中或未见日志填0。

## 正式执行、幂等与恢复

未来只沿EvaluationService.create_experiment、execute_job、正式RealQueryExecutor；不得私有SDK直连、传executor_factory或monkeypatch风险／能力／账本。精确缓存只接已审embedding／rerank／检索响应读取口，实际只读索引授权核验保留；miss或来源漂移即停止，本地新增推理必须0。

临发前再次只读核新账户／固定槽／请求／配置／Run／输入／checkpoint及前值，无消费与未知窗口才进入正式链。先账户CAS预留、正式Run关联及run_input核验，再独占started，之后才联网。请求、wire、原始流、raw usage、finish、raw selection、完整映射／答案hash和来源证明均封存于新私有目录；日志不输出凭据或endpoint。

先按原观测结算，再检查选择／程序渲染与来源。结算严格全等幂等，冲突拒绝。成功outcome须对完整冻结来源、raw选择、映射及答案重新核验。恢复只复用正式冻结outcome，核完整身份并保持一次调用；started未结算表示未知窗口，**不自动重发**，不删槽／pending或手改state恢复额度。断流已收选择及失败材料必须按R2持久保留；程序渲染字符不是模型token。

## 首失败停止与效果退出

任一前置不符、空正文、length截断、非法／空／重复选择、来源或proof漂移、usage缺失／非法／矛盾／超过4096、中断或非思考模式出现不符观测，均封存并停止。usage未知或冲突沿原协议持久阻断，保留可证下界及未知窗口，不截数字、不补0、不重发。无论结果如何均不接43题。

即使技术完成，也必须正确完整地回答原问题：区分客户端访问设备、管理／排障条件和设备上联，双方关系及引用准确，条件／否定／版本与unknown不外推；不靠新增GM/GU或EoC关键词门槛评分。**只有相关摘录而未完成比较，真实效果仍失败／不适用，不能创建独立评分或有效候选来冒充通过。**

本轮不建立新授权、正式job／Run、账户／slot或质量链记录。M6 5/7、04保持验收、05／08未验收、M7未启动。下一步先按矩阵完成两处有限补修及复核；本规格在此之前不可执行。
