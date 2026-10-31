# M6候选审核呈现、选源核验与证据消费补修 r1

2026-10-31，Asia/Shanghai；执行方自验交付，待总控独立定向复核。接续 `e0184899254a1ae0078a3394cc49e80c44ca135b`，开始HEAD／origin/main一致、仅tmp/；初次远程核验因本机Git代理不可达失败，使用单次禁用Git代理核实远程仍为该提交。没有覆盖后续提交。本包不新增子Agent、推理、真实评分／case／校准／proof；两候选v2的blocked和原分保留。

## 实际修复

1. **047正式呈现**：`EvaluationRepository.save_results`保留state／公开候选；adapter按授权product_id过滤，repository仅白名单product_id／model；新审核组件区别awaiting_input、失败／取消／中断、拒绝／依据不足，兼容无新字段旧记录。不预填评分或本人声明。
2. **有效选源核验**：`ReviewRepairs.effective`逐维追踪最终选中来源，再all求有效source_checked。四维全部来自已核新来源可为true；仍留任何旧未核维或新来源false仍阻断；规则N/A不自动证明原件已核，critical合并／subject／scope／封存hash／独立性校验保持。只生成内存有效投影，不改原记录。
3. **一套固定通用候选**：默认关闭`parameters.evidence_attribution`，版本`attributed_assertions_v1`及新独立prompt。用冻结产品／document／revision／原件SHA标注对象、物理页和真实编号，约束具名配件／机身／上联边界、逐断言消费依据、完整比较、摘录限制、图标残片、实时未知及风险版本条件。没有题号／答案特判，没有改weighted、分数、top-k或20/20/20/20/10预算。
4. **引用呈现**：连续编号来自最终实际prompt的选中文档次序，生成`prompt_reference_map`保存到Run、正式结果及审核UI；页级citations一片可有多页，未知页还可能省略，所以它的位置不能用作正文[n]。本包不事后改模型答案或补造引用。

证据归属启用须与已审内部组合scope／语料快照一致；正式config先核目标／语料／产品／修订，再进入InternalRunInput、Run幂等身份、执行关联、题级检查点及恢复核验。公开RunInput不接受此字段；新策略没有环境变量。默认关闭原prompt／state／请求身份保持；显式非缺省关闭仍有独立身份。启用Run不可交给关闭消费者恢复，回切用新配置／请求，不删旧记录。实际新配置目前只有本机草案，**未登记为正式新生成配置，未跨源码／prompt复用旧校准**。

## 已存答案和原件诊断

[完整30／9／5矩阵](M6-candidate-evidence-quality-matrix-r1.md)及[逐项hash与来源](M6-candidate-evidence-quality-matrix-r1.json)为assistant-side诊断，不是第三轮或新评分。30下降中27个prompt未变；6维对应4个题级输出问题、21维有已证提取／呈现限制、3维语义待核。这不证明各维应改成什么分数，不消除blocked。

可直接证明的输出问题包括：版2 02-a把物理遮挡扩大成摄像头不能被使用并附加无正文支持的隐私关联；11-a与008打印的chunk标识不符实际prompt编号；18-a把残缺“+ P”写成操作。18-a的[6]/[7]与实际prompt对应，旧页级列表错位理由不足以证明改号；完整断言支持问题另列，不能沿用错误编号推断。

重要限制：02-b输入隐私段确仅标题；04-b原页有图但输入无图；17-a输入只有标题／部分表行而非整表；09-a及030被引用的真实prompt证据因未知页未进页级展示。图标原页可见、prompt缺图标也必须区分。本机渲染39页，直接目视D3 p3/4/8/13/14/15/16/17/24及D5 p4/23/30共12页；其余以文本核对，不声称全部目视。

047两版Run均awaiting_input／model_required，有真实型号候选。已追加关联原Run／subject／实验／结果hash的**只读补充视图**，明确旧审核者未见补充。旧result／subject／第一轮source_checked=false不回填，也不据此自动判2。048两版真实prompt[4]均含Cable／同轴／EoC及已审p30，输出仍未完成比较；归属提示缺少是输入弱点，尚不能认定唯一生成根因或声称新prompt有效。

10个步骤适用性维、4个固件引用范围已完整列入矩阵，保留question-purpose-v1与真实assistant身份；不为过门禁新增第三票、不替换旧适用性或原分。

## 验证与失败保留

以下是实际命令与退出结果，各组重叠，不累计唯一总数或质量分：

| 范围 | 命令／日志 | 实际结果 |
| --- | --- | --- |
| 最终聚焦 | 摘要commands.focused列明8个文件的pytest命令，final-focused.log | 97 passed，exit 0 |
| 相关共享 | shared-final.log | 250 passed，exit 0；与聚焦重叠 |
| 正式隔离合成 | pytest三个文件：test_candidate_evidence_quality_fix.py、test_review_repairs.py、test_combination_adapter.py，final-isolation.log | 58 passed，exit 0；同／分库、创建与完成窗口、保存后恢复、映射漂移拒绝、幂等、选源真假／部分／规则／critical及既有拒绝原子性 |
| 真实浏览器合成API | frontend：pnpm exec playwright test tests/e2e/reviews.spec.ts tests/e2e/review-presentation.spec.ts --output=../output/m6-candidate-evidence-quality-fix-20261031/browser-related | 13 passed，exit 0 |
| 类型／构建 | frontend：pnpm typecheck；pnpm build | 均exit 0 |
| OpenAPI | .venv/Scripts/python.exe -m pytest -q tests/unit/test_prerequisite_contract.py | 2 passed，exit 0；公开API契约全等 |
| 保存产物 | replay_saved.py，replay-r2.log | exit 0；25题／35单元全部保留，双方、p30、分组与预算不变；两版170旧结果／340判断不变，168保存流两种分片输出全等 |

回放有禁止socket及subprocess外部IO的审计钩子，新增推理／真实数据库访问／质量写入均0。它重建新prompt和映射、过滤原供应商流，**没有让原模型按新prompt生成，不能证明新答案改善**。完整prompt长度／元信息开销计入原预算；本组保存输入未挤出旧context，不据此保证任意未来输入都相同。

初始后端公开投影／选源红测5失败4通过，归属红测7失败1通过，map红测1失败9通过；浏览器最初4失败、map新增1失败均保留。后续夹具label、原子组映射次序、诊断字段名等中间失败及修后结果分别留存。首次Mongo不可达（37 setup错误，随后1 setup错误停止）不是业务通过；本包用已缓存mongo:7.0镜像创建无真实卷的新容器，只写随机短m1_test_m4_合成库，不修历史库／容器或清库重来。新容器现场保留，具体端口／库名只在本机test-mongo.json和final-isolation.json。

## 身份、现场与退出

1205份本包开工保护、240及609两份既有保护清单逐文件hash全匹配（组间重叠）。两版170持久答案／340判断仅按封存文件核验；**没有本轮访问真实质量库、重扫live582／867向量、默认指针或历史22集合**。不将封存哈希等同即时数据库审计。原r3的19继承＋66执行、历史stream19／新增61和失败实验调用未知身份不改。历史HTTP／费用未知保持null；本包没有新增模型路径，usage null不被解释成历史0。

私有证据目录：`output/m6-candidate-evidence-quality-fix-20261031/`；可读对照为`候选证据与下降诊断.html`，另有`047-048只读补充-r2.html`及`historical-047-supplements-r3.json`，由保存实验补齐精确题集／配置版本；不是即时数据库视图。本包日志／原页／完整答案／PDF／缓存不上传。脱敏[验证摘要](M6-candidate-evidence-quality-fix-validation-r1.json)含具体命令、来源hash、红绿结果及配置草案hash。

| 子项 | 本包交付／剩余 |
| --- | --- |
| 审核呈现、选源核验、固定证据候选 | 执行方自验完成，交总控独立复核；不自行关闭技术审查 |
| 旧v2 | 两版blocked、30下降、9混合、5变化及047未核来源保持；不追加旧v2补审追求过关 |
| M6-04 | 已验收保持，不重生成基线或改旧校准 |
| M6-05 | 未验收；须后续有效同范围真实复评及服务端proof，本包不创建 |
| M6-08 | 未验收；新prompt真实效果／新执行身份及可比性尚未验证 |

**唯一下一动作：总控定向独立复核本包技术与完整诊断；通过后再按[有界真实诊断草案](../handoffs/M6-attributed-evidence-diagnostic-draft-r1.md)裁定固定生成身份及正式可比性。** 草案本轮不执行，不自动重开170题，不跨新配置复用旧检查点或校准，不增加heldout／Ragas／默认发布门槛。M6保持5/7，M7未启动。
