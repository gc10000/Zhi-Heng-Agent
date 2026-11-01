# M6原句选择约束：执行端定向复核 r1

日期：2026-11-01，Asia/Shanghai。复核锚点：`0f31c7872e7f40245f943f7ace54ba5ea36b244b`。本报告是执行端定向复核，**不是总控独立关闭、实现整体通过或M6验收**。本轮未修改业务实现，没有模型调用授权。

## 结论

严格编号选择、完整原段围栏、调用前漂移拒绝、常规身份与正常恢复有实际通过证据；但**冻结来源恢复核验和断流拒绝材料持久化仍有两类缺口**。4个反例失败集中归入这两个根因，不扩展为新的检索、角色或供应商框架任务。本轮不放行新048，不恢复43题。

完整原文保留不等于完整回答。当前renderer固定呈现所选原段，并明确声明摘录不代替完整比较结论。即便脚本全选全部证据，也只证明原段没有丢失，不能证明回答了“上联方式是否相同”。当前可证明的产品范围是**证据摘录视图**，尚不适合作为048完整比较答案通过的依据；不得为适配该形态降低原任务退出条件。

原`0f8922f`裁定保持：048必要证据已入prompt，旧失败在自由断言把客户端访问、排障条件与设备上联拼接。没有漏召回新结论，不补关键词、角色标签或提示词，不重审p30或重签001；EoC及GM/GU字样不新增为独立硬门槛。

## 核验锚与范围

- 启动及收尾准备时均实核HEAD、origin/main、实际远程main为上述锚点；未回退或在旧提交运行。报告列出的11个源码／模板／原测试SHA全部匹配。
- app canonical SHA256：`0563dd43a855b309013093b00efbb6d8740591faf91198fdb5b1a25172ed46c9`。本轮新增合成测试和脱敏文档，业务源码／prompt没有改变。
- 已阅读项目约定、进度、审查状态、Git流程、公共契约、TODO、M6任务以及[实现自验报告](M6-assertion-binding-fix-r1.md)和其validation；逐段核读assertion_binding、evidence_attribution、node_answer_output、正式query_runner／query_adapter／repository／execution_identity及telemetry差异。
- 真实状态默认只读。仅使用新随机短`m1_test_m4_abr_b30311`合成库前缀写入测试；未启停服务、未创建真实experiment／Run、未访问private-identity。没有进行真实业务库全扫，不能据此宣称全部旧状态／TTL／默认指针重新现场核明。
- 检测到并行复核的PROGRESS新增段；保留其原文，不纳入本包提交。历史报告和全部红测／中间失败保持原样。

## 集中缺口矩阵

| 根因／状态 | 最小及正式反例 | 实际结果与影响边界 | 有限退出条件 |
| --- | --- | --- | --- |
| R1，高优先级，open：恢复只核材料自洽，未重新绑定冻结载荷 | 保留冻结policy和payload hash，改写合成doc.text，重算content hash／frames／渲染answer及proof；另在正式Run完成后、首次outcome冻结前协调改写同组字段 | `validate_saved_binding`未拒绝；首次投影的合成job变为completed并创建outcome。对照调用完整`evidence_labels(docs, policy)`则拒绝同一漂移。已有outcome后的单字段篡改仍会被既有身份核验拒绝；没有真实资料被篡改的证据，也不意味着所有恢复失效 | 缓存复用、首次投影和恢复在核proof前，用完整冻结归属／source_relations重新派生载荷与映射并全等核验；上述协调改写均拒绝，且不新增模型调用。不修改历史proof或outcome来凑通过 |
| R2，中优先级，open：生成异常路径未持久保存缓冲部分选择 | 合成stream先返回`{"references":[`再断流，同库／分库各一例 | 内存`AnswerGenerationError.partial_answer`有原始片段，但state未设answer_binding_failure，正式failed Run没有raw_selection。Run确实失败、无用户JSON泄漏、无成功outcome、仅一次合成调用；缺口是中断材料的持久追溯，不是自动重试或错误答案泄漏 | 对断流等生成异常，将已收选择、失败原因及输入身份以受控字段持久保存；保留failed／未知窗口及原usage结算，不将部分输出标完成、不补0、不重发。两种库路径反例通过 |

R1代码路径：`assertion_binding.py::validate_saved_binding → bind_response → checked_sources`只核当前doc／映射互相一致，未重新执行带冻结policy的`evidence_labels`；正式`query_adapter.project_result`消费此证明。调用前`node_answer_output`已有完整冻结校验，因此本缺口不重开此前调用前保护。

R2代码路径：`node_answer_output.step_3_generate_response`的生成try/except只抛partial；完成流后的绑定拒绝分支才写answer_binding_failure。`QueryRunner`仅在state有该字段时持久化，故断流部分选择丢失。上述结论有最小单元对照和正式同／分库反例，不再开启无界试词。

私有反例文件：`output/m6-assertion-binding-review-20261101/test_failure_probes.py`，保留4个失败。红探针未作为“已修复”绿色回归提交；其hash进入[脱敏摘要](M6-assertion-binding-execution-review-validation-r1.json)。本包未实施R1／R2修复。

## passed与证据限制

- 严格JSON：自由答案、JSON外解释、额外／重复字段、空／重复／越界／bool／string／float编号均拒绝，不补造引用。enabled缺省关闭，须开启冻结归属及source_relations；原默认兼容检查保持。
- 原段呈现：条件、否定、版本、unknown保留；connection没有被新逻辑猜成上联，没有新实体关键词分类器。动态围栏中的指令、代码、HTML、图片及内部编号在逐字符CitationGuard／AnswerFilter检查中完整保留为资料文字；这是程序过滤链检查，不是浏览器执行安全的完整渲染审计。
- 调用前的原文、原件hash、页码、跨度、引用编号／映射漂移拒绝。普通旧答案缓存没有可重放证明时不能跳过；raw／proof单字段篡改拒绝。但协调改变材料仍受R1限制，不能写“所有篡改均拒绝”。
- 流式原始JSON缓冲、不向用户逐delta泄漏；length截断及非法最终选择拒绝。断流的内存partial可得，但其正式持久化为R2，不能将整体失败材料链写成通过。
- 完整策略及其canonical hash进入Run、题级checkpoint和execution link；raw selection、reference_map hash及answer hash进入Run、结果和冻结outcome。正常成功复用仅一次合成模型调用；首次outcome可信来源仍受R1限制。
- 合成usage为101输入／7输出，程序渲染字符明显多于7；结果仍保存101／7，不把渲染长度当模型token。没有修改输出硬限、原首停止或费用结算协议；上述合成测试不证明真实网关遵从或付费上界。

## 实际命令与结果

私有证据新目录：`output/m6-assertion-binding-review-20261101/`。以下为本轮实际运行，互有重叠，不相加成质量分：

1. `.venv/Scripts/python.exe -m pytest tests/unit/test_assertion_binding.py tests/unit/test_assertion_binding_review.py -q --tb=short --junitxml=output/m6-assertion-binding-review-20261101/target-unit-r1.xml`：**61 passed，exit0**，原27＋新34，无失败／errors／skip。
2. 设置PYTHONUTF8和随机M1_TEST_DB后，`.venv/Scripts/python.exe -m pytest tests/integration/test_assertion_binding_wiring.py tests/integration/test_assertion_binding_review.py output/m6-assertion-binding-review-20261101/test_failure_probes.py -q --tb=short --junitxml=output/m6-assertion-binding-review-20261101/target-integration-r1.xml`：**11 passed／4 failed，exit1**，原9＋新2通过，R1两例／R2两例失败；无Mongo setup error或skip。
3. 审阅原`replay_final.py`后仅复制适配OUT至新目录，运行`replay_review.py`：**1313断言通过，exit0**。54成员＝52生成输入＋2原澄清，另原25题／35必要单元；context、编号、引用映射、分组、顺序及必要原段保留。全部选择是脚本合成，不是新产品答案，没有正式job。
4. `tests/unit/test_prerequisite_contract.py::test_openapi_still_matches_checked_contract -q --tb=short`：**1 passed，exit0**，公开OpenAPI全等。未机械重跑1427／65或历史整轮。
5. 审阅并复制适配旧文件保护脚本、运行`finish_audit.py`：本轮465文件、11源码hash，以及89交付／4686指定文件、历史138／336／597／1314组hash匹配。组间重叠；检查只覆盖指定本地文件，不是全量真实数据库审计。完整冻结policy拒绝R1漂移的对照也通过。

实现报告的1427离线／65隔离／27定向（重叠）／1313原回放均保留为**实现自验历史**，不是本轮通过数，更不是质量分。失败日志和全部原件保留，不覆盖或删库。

## 唯一048方案的状态

“核验通过后提出可执行方案”的前提尚未成立。本轮只交付一份[受阻的条件性规格](../handoffs/M6-assertion-binding-048-proposal-r1.md)：唯一变量是严格原句选择；列明新身份、输入、幂等、预留／结算和首失败停止，但没有登记ID、冻结授权或可派发配置。**R1／R2未消除、完整比较适用性未成立前不应安排真实stream；本Prompt也未授权新调用。**

回放048的prompt是方案证据锚，不是可派发包。其budget继承旧unknown草案合同和max_tokens，不能搬入新job。未来即使技术修复，仍须新模式／新版本／新身份、最终源码及新正式配置冻结；旧blocked账户、槽、证明不能搬用。

## 计量与交付

新增产品／非产品stream、供应商调用、embedding／rerank及真实库写入均**0**；新真实模型token为0，测试中的101／7是合成数据。历史累计依封存来源仍为**53089输入／30412输出**。历史reasoning明细、HTTP及费用为null／unknown，实际付费输出上界unknown；没有从“本轮没调用”反推历史HTTP或费用为0。

没有正式评分／校准／候选／gate／feedback proof；未运行heldout、未切默认。M6 **5/7**：04保持验收，05缺真实反馈复评proof，08缺有效新候选质量及阶段证据，M7未启动。既有技术关闭与05-a等限定结果不重开。

本包交付合成绿色测试、脱敏报告／摘要／受阻方案及导航；output、日志、缓存、PDF、真实输入／答案及tmp不上传。最终提交／普通push与本地、origin、实际远程核验结果见会话收尾，不用自身SHA反复amend。

**唯一下一动作：执行方先按矩阵补齐R1／R2并作有限复核；技术满足后才审定原句摘录能否用于原048完整比较目标，不能把相关原文展示改判为质量成功，也不以新调用试运气。**
