# M6 已校准候选双轮总控独立复核 r1

2026-10-31（Asia/Shanghai）。审查ff8331e873c432261d30016ffcd784491e93a408；本轮实际确认HEAD／origin/main／远程一致、工作区仅tmp/。总控未参与这两个实际候选审核任务，不复制执行方自验结论；本轮无业务源码修改、模型调用、子Agent或评分改写。M6-04已验收保持，M6核心5/7，05／08未验收，M7未授权。

## 独立性裁定：接受真实双轮来源，不等同质量通过

接受/root/candidate_blind_round1_fresh及/root/candidate_blind_round2_fresh作为两次真实独立审核任务。每轮跨两个版本170条，合计340条，不称四个独立任务。纯输入无expected／annotation／旧评分，实际材料与正式完整subject一致；两轮输入在不同目录内容相同，各自原件／渲染／留存脚本和声明访问hash匹配。跨两个版本均先封存第一轮，再begin第二轮；原始判断、4seal及340条正式assistant记录全等。登记主体与总控不同，无human代填。

第一轮完整初稿／逐批／终稿一致；第二轮保留036引用1→2的封存前本人修正及原因，原初稿和修正版均留存，未见由协调方或第一轮反馈诱导的证据。截断、引号和GBK失败均保留，不把声明访问清单等同完整OS访问审计。当前无可调用旧thread全量读取工具，fork_turns=none依据用户实际交付和执行记录，与封存provenance、目录hash及正式时序交叉核验；精确模型、平台调用／token／HTTP／费用未知保留null。此证据限制接受用于既定开发政策，不新增全量重审、换模型或OS沙箱门槛。

本报告受控提交后可由原kb实际总控admin正式调用DevelopmentPolicy.attest。attest证明来源独立性，不修复047未核来源、不消除N/A混合、不改变任何分数。随后只读调用正式release gate保存完整blocked／pending原因；即使证据完整性未全闭合，正式门禁也能报告已成立的数值下降，不能因此写为passed。实际回执在受控提交后追加。

## 本轮已关闭与仍开放的完整矩阵

| 边界 | 本轮裁定 | 退出／下一条动作 |
| --- | --- | --- |
| 两版85题独立执行、调用与封存运输 | passed，继承0，真实结果／Run／subject匹配 | 本包关闭，不重跑候选创建和旧job |
| 两任务真实双轮来源 | passed，允许正式独立性登记 | 只登记来源，不追认所有语义正确 |
| 047低分能否证明澄清路由错误 | 不能；该推论关闭。真实awaiting_input／model_required／候选列表存在，产品UI有选择型号提示 | 审核呈现缺口仍open；补充可验证的只读Run／UI视图，不能伪造新答案 |
| 9处轮内N/A混合 | open；6步骤、3引用 | 固定题意／完整展示来源规则；不投第三票或择高分 |
| 5处跨基线适用性变化 | open；4步骤、1引用，原执行摘要未列出 | 与9处同包处理；不改已冻结基线／校准 |
| 30处已封存数值下降 | 原始比较为版1八维、版2二十二维，完整下表；待正式gate读回 | 不等价30个独立产品缺陷；按实际prompt／输出／展示引用分根因，不抹分 |
| 048完整比较 | open；必要Cable／同轴／EoC正文确在两次实际供应商输入[4]，输出仍遗漏 | 生成／证据归属消费问题；不重开检索、扩top-k或重排 |
| 既有019／021／022及四对象配件关注题 | 当前双轮事实／引用均2的原记录保留 | 不是全题集质量或proof通过 |
| M6-04及旧P2／p30／001／冻结接线 | 既有关闭保持 | 不重新登记、评分或回退阶段 |

## 047材料边界及接口反例

RealQueryExecutor.project_result（app/evaluation/query_adapter.py）已产生awaiting_input state及candidates；EvaluationRepository.save_results（app/evaluation/repository.py）public_keys未保留两字段，正式结果只留下空answer与clarify。ReviewPage有澄清说明，实际聊天ProductClarification组件显示“请选择适用型号”和候选按钮。原两轮主要针对空白投影评分，不能把该分数升级为已证明的澄清路由业务错误；也不能据路由合法就替他们填2分。两个047第一轮source_checked=false保持，第二轮true不代替第一轮。

补证接口另有确定缺口：ReviewRepairs.effective逐维替换后仍执行old.source_checked AND new.source_checked。5个内存合成边界证明，四维全部从新独立来源选择时，旧false仍永久阻塞；部分替换必须保留old false，new false也必须继续阻塞，原critical不得丢弃。探针首两次因合成夹具遗漏rationale／attestation id失败，原脚本和日志保留；r3成功，不冒称业务回归已修复。

本轮保持独立复核身份，不修改业务后自称独立技术通过。由于旧v2已有其他明确下降，不先花真实双轮调用补完047／9维再发现gate失败；不登记新repair case，也不让执行端在旧v2上反复换源追通过。所需最小接口修复、历史只读补充呈现及通用生成输出约束在下一包集中实现与隔离验证，再由总控独立复审。

## 9处轮内适用性分歧

| 版本 | 题目 | 维度 | 第1轮 | 第2轮 |
| --- | --- | --- | --- | --- |
| 1 | m6-g540-unknown-01-b | actionability | not_applicable | 2 |
| 1 | m6-g540-unknown-03-b | actionability | not_applicable | 1 |
| 1 | m6-g540-unknown-04-b | citation_support | not_applicable | 2 |
| 1 | m6-g540-unknown-05-b | actionability | not_applicable | 1 |
| 2 | m6-g540-unknown-01-b | actionability | not_applicable | 2 |
| 2 | m6-g540-unknown-03-b | actionability | not_applicable | 1 |
| 2 | m6-g540-unknown-04-a | citation_support | not_applicable | 1 |
| 2 | m6-g540-unknown-04-b | citation_support | not_applicable | 1 |
| 2 | m6-g540-unknown-05-b | actionability | not_applicable | 2 |

## 5处基线／候选适用性变化

| 版本 | 题目 | 维度 | 已冻结基线 | 候选双轮最低值 |
| --- | --- | --- | --- | --- |
| 1 | m6-g540-10-a | actionability | N/A | 2 |
| 1 | m6-g540-10-b | actionability | N/A | 2 |
| 1 | m6-g540-unknown-04-a | citation_support | N/A | 1 |
| 2 | m6-g540-10-a | actionability | N/A | 2 |
| 2 | m6-g540-10-b | actionability | N/A | 2 |

题意解释：unknown-01-b／03-b／05-b要求返回此刻电量／备份／蓝牙事实，并未询问“如何检查”；附带自查步骤不自动改变题目交付物。10-a／10-b要求识别适宜充电环境条件，不要求执行充电流程。依既定question-purpose-v1，前述5种题意的步骤维度应为N/A，在两版共10个题级维度，若未来需要合法纠错可由总控按固定题意登记，不预填数值。不能把所有带“读取／查询”词的问题都程序化判N/A；明确要求执行检查方法的题仍适用。

四个固件引用范围（两版04-a／04-b）必须同时看完整回答、实际展示来源与原件；无[n]不等于N/A，有来源列表也不自动2。“手册无本机实时版本”与“参考资料仅有标题”是两项不同断言，后者如不符实际正文要保留低分。第一版04-a是跨基线N/A→数值，另三项是轮内混合，不能遗漏前者或跨答案套用旧case。

## 30处数值下降的全表

以下比较只取已有合法数值对的min并与对应已冻结校准比较；047未核来源和9混合未当作数值0。不是第三轮评分，也不宣称30个客观错误或组合策略导致30个退化。

| 版本 | 题目 | 维度 | 基线 | 候选 |
| --- | --- | --- | ---: | ---: |
| 1 | m6-g540-19-b | factuality | 2 | 1 |
| 1 | m6-g540-19-b | citation_support | 2 | 1 |
| 1 | m6-g540-20-a | factuality | 2 | 1 |
| 1 | m6-g540-20-a | citation_support | 2 | 1 |
| 1 | m6-g540-unknown-04-a | factuality | 2 | 1 |
| 1 | m6-g540-unknown-05-a | factuality | 2 | 1 |
| 1 | m6-g540-unknown-05-a | citation_support | 2 | 1 |
| 1 | support-v1-030 | citation_support | 2 | 1 |
| 2 | m6-g540-02-a | factuality | 2 | 1 |
| 2 | m6-g540-02-a | citation_support | 2 | 1 |
| 2 | m6-g540-02-b | factuality | 2 | 1 |
| 2 | m6-g540-02-b | citation_support | 2 | 1 |
| 2 | m6-g540-03-a | factuality | 2 | 1 |
| 2 | m6-g540-04-b | factuality | 2 | 1 |
| 2 | m6-g540-04-b | citation_support | 2 | 1 |
| 2 | m6-g540-09-a | citation_support | 2 | 1 |
| 2 | m6-g540-09-b | factuality | 2 | 1 |
| 2 | m6-g540-09-b | citation_support | 2 | 1 |
| 2 | m6-g540-11-a | citation_support | 2 | 1 |
| 2 | m6-g540-17-a | factuality | 2 | 1 |
| 2 | m6-g540-17-a | citation_support | 2 | 1 |
| 2 | m6-g540-18-a | factuality | 2 | 1 |
| 2 | m6-g540-18-a | citation_support | 2 | 1 |
| 2 | m6-g540-20-a | factuality | 2 | 1 |
| 2 | m6-g540-20-a | citation_support | 2 | 1 |
| 2 | m6-g540-unknown-04-a | factuality | 2 | 1 |
| 2 | m6-g540-unknown-04-b | factuality | 2 | 1 |
| 2 | m6-g540-unknown-05-a | factuality | 2 | 1 |
| 2 | m6-g540-unknown-05-a | citation_support | 2 | 1 |
| 2 | support-v1-008 | citation_support | 2 | 1 |

逐题原因按本机完整答案／prompt／两轮依据封存：摄像头遮挡被扩大成禁用；答案称只有标题／无表／无图但完整原页有内容；图标路径提取不足被输出成残缺命令或“原件未提供”；正文[n]、模型自写chunk_id及实际展示源不一致。相同主结论仍可能因为附加错误被降到1，不能只查结论首句。原SQ关闭结论不整体重开，需检验这些实际新输出及其直接输入。

两版各84个真实stream输入与对应基线逐一比较：每版79个完全相同，5个变化（015、048、03-a、unknown-03-b、unknown-04-a）。30个下降维度中27个对应相同模型输入，3个对应变化输入；因此不能把所有下降归因为新增检索组合，也不能靠再次运行同prompt假设必定过关。实际输出及审核口径差异要分别留证，不变更容差0。

## 048限定生成失败

两版实际stream输入都含目标chunk b0132ca5-f5a0-5716-950e-0d99b0916f9b、Cable口同轴电缆、入户接口及远端机房EoC语句；CB304n侧目标位于[4]。实际输出未使用同轴／EoC／Cable比较，却称CB304n上联依据不足，两轮事实／引用均1保持。总控实际查看D5物理30页表格，确认这一链路依据；源文件字节及来源映射hash匹配。

当前实际prompt[4]仅标local／chunk／低分／“附录–故障排除”标题，没有在该段显式给出所属产品／文档；LA侧标题反复含LA2608。缺少逐证据归属标注是一个可验证的输入设计弱点，但尚未证明它就是模型遗漏的唯一原因或补上即可提高质量。后续只能用来源快照支持的通用归属标注及完整断言约束做一项有界候选；不得把048答案词写入问题、重扩词或宣称修复已成功。

## 验证、调用及证据限制

本轮独立只读审计6827项通过，执行产物572份hash、历史清单240／609份匹配（可重叠，不累加唯一数量），3555条既有非槽位记录hash保持，2条slot正式job生命周期变化与执行前后证据一致。170正式结果、4seal及340评分全等。两份基线与校准仍匹配。本轮没有live Milvus 582／867向量重扫，不把Mongo只读核验写成向量现场证明。

候选本次168stream、input322716／output187567 token保持；连同已核正式基线范围累计336stream、input644642／output355857，不是全项目总数。本轮总控新增推理0。精确HTTP／费用及平台审核usage未知保持null；旧r3、原失败窗口和19继承＋66执行不改。未知不填0，检查数不作答案质量分。

## 固定下一包与退出

先保存本轮正式独立性及gate实际回执，确认旧v2是否blocked；blocked则保留失败并停止该候选的proof与真实补审，不把本报告变成新开发验收门槛。下一包集中处理047审核呈现／选源核验接口，以及完整矩阵中通用的来源归属、断言与引用一致性边界；先用保存产物零推理验证，不重复候选或基线运行。任何后续真实生成只在技术包独立复审及固定配置／范围／调用预算说明后执行，不自动启动170次答案或平台补审。

M6-05仍缺两条反馈的真实有效复评proof；M6-08仍缺有效候选质量链和最终阶段验收。M6-04保持已验收，M6核心5/7；不新增human／heldout／Ragas／默认发布门槛，M7不启动。
