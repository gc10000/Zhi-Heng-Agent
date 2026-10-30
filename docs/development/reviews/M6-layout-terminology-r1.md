# M6 原P2版面补修与来源术语检索对照 r1

日期2026-10-30。接续`cf173410ea041437a1a322c9353da2c1bac90143`，HEAD/origin/GitHub一致，仅未跟踪tmp/，六容器运行且适用健康检查正常。顺序执行，无子代理。001消费关闭结论保持，没有重登记、重签审、重绑定或访问其写入口。

## 交付结论与剩余位置

1. **C06-PAGE-R1-R四种版面边界已补修，执行自验通过，未自行关闭原P2**。原矩阵修前4失败/3通过，原样副本修后7通过；含原短型号、页内关联和新相邻边界的定位组28通过。合法同列换行和同列正常续页保留。
2. **048通用来源术语投影改善稀疏入口，但未到最终上下文，不采用**。必要正文由原dense198/sparse42变为dense57/**sparse1**，实际Milvus分路响应确认稀疏第一；weighted融合limit20中已无此正文。因此未进入候选池公平选择、重排或context，不归咎重排/上下文。25题仍24/25，原24题两种context/prompt/分组/预算完全一致。后续只处理已有候选融合保留，不重复旧两失败策略或本次相同编码。
3. 真实最终范围/可生成配置未冻结，不启动答案、质量记录、预校准、候选或proof。本包是技术与真实检索证据，不是M6质量通过。

## 版面补修证据与最小实现

旧实现只看整体包围框相交，单cell直接放行，未检查片段连续性。现在NativePage保留原件文本行ID、基线、字符bbox、文本方向、物理页宽高和水平分隔线（含矩形上下边）；按原件行构造Fragment。

- 单cell内部逐行验证：同一原件行禁止远距离横跳；换行必须沿同列或同一原件行已明确的前缀起点，行距有界，禁止跨分隔线。单cell也受检查。
- 单元格间要求首文本行基线对齐、列左右分离；少量字体bbox重叠不能替代真实行带，明确分隔线阻断合并。
- 跨页须同一完整cell跨越边界、页宽一致、续文与该cell/已证实段落列位一致，并进入有界页首区域；两页各自仍检查内部片段连续性。未知或扫描件无坐标不能授予精确定位。

阈值按字符高度与物理页比例固定，未按具体文档或题号调参。保守规则不是通用PDF语义认证；不可靠即page=null。MineruParser结构5→6，chunker仍6，正式pipeline_identity包含新adapter版本与chunker。原Provider缓存键和原始内容不改。

全43表249行复算：134精确/115未知→**89精确/160未知**，45行保守降未知，不能称45条已证实原件错误。原24题必要摘录仍各有精确命中，microSD受控补证与RJ45保留物理p5。范围外未知不设全部补完门槛；最终使用的新依据需按实际依赖核清。本次048目标表格行也降未知，后续若融合后实际消费它，须同时核验原页关联；原件p30已渲染目视查看，不能把该截图自动冒充独立row审核或直接回填旧修订。

新命名空间：`m1_test_m4_m6_layout6_da6474d5f3c94940`（Mongo/Milvus），对象前缀`m4-test/m6-layout6-da6474d5f3c94940/`。四文档新修订由正式IngestionService/Publisher创建、CAS激活仅限新隔离空间。582切片（22/165/84/311）原文与向量按文档/ordinal逐项复用，三处图标转写继续assistant来源，67派生摘要保持原资产映射并继续隔离。未云解析、未调用视觉模型、未改默认catalog或冻结r3。

## 术语候选：来源先于题目、固定范围与失败停止

抽取器先扫描四文档全部授权正文，只允许“概述/产品简介”中ASCII词紧邻“网络”的原件字面名称，精确页码和原件引用完整；不读旧答案、25题判断或目标故障排查行来挑词。每修订最多2词、每scope最多4词，超限整体不用；不从故障排查、未知页码或派生图摘要提词。

预检发现“CC721E网络集中器”是设备名而非网络介质，新增合成红测复现后收紧字面后继词法边界，原始预检与失败保留。最终冻结D1 `3G/4G`（原件p4）、D5 `Cable`（原件p8），D3/D4空；没有新增同轴/EoC或题号规则。逐原PDF核对字面文字并渲染p8/p30目视核实。网络介质名仅帮助检索，不证明它就是上联能力，不改变原题/生成输入、对象路由、版本、否定或来源。

适用条件：明确已授权产品与修订、answer/compare路线、无未知型号、原检索输入含上联/上行/广域网/WAN/uplink；代码或多行坐标不确定时不改。默认enabled=false，只保留隔离候选函数，**未接入QueryRunner/RetrievalPolicy/工作台配置**。先固定词表及完整SHA，再扫描25题；恰有048两scope改变。术语Manifest/执行配置在新output，非最终可生成配置。

一次真实25题对照仍保留weighted和20/20/20/20/10预算：新本地查询编码2、缺缓存重排1批/8pair，其余精确缓存复用。必要D5正文实际sparse1、dense57，实际hybrid输出20无此UID；它未进入后续阶段。首份本机audit将排除层笼统记为双路top20之前；追加实际后端分路UID核验后，audit-v2明确更正为weighted融合输出排除，两份原件均保留，以v2为最终结论。虽然本题稀疏初召回改善，最终同轴/EoC两必要单元仍缺，因此**本策略不采用**，无正式接线，不把测试或稀疏命中写成答案正确率。

源码中保留抽取/投影函数只为默认关闭的隔离复现，并无产品配置开关或正式默认变动。停止进一步同类扩词和调用；下一执行动作是复用本次已保存的真实双路结果/分数，在原融合池总量及比较分组预算内验证通用分路证据保留候选，先证明原24题不退化再考虑新的推理范围。不得题号/答案词特判、增加top-k、放宽阈值或切RRF。

## 配置与调用账本

语料处理身份在导入前冻结；导入期间只收紧了尚未调用的独立source_terms后继词法保护。未修改parser/chunker及实际语料，处理指纹保持；随后另外冻结检索执行代码身份，保存其父语料配置hash与唯一差异source_terms.py，拒绝将两者冒称同一源码快照。两份实际指纹见摘要。

沿用模型文件hash `3995645af911d30aa3ec13c90c61919bfe52830a0611f3f3820b6097062520fc`，BGE-M3 CUDA:0/fp16、bge-reranker-large CPU/fp32，embedding batch4/rerank batch8，禁联网/下载。稳定请求键绑定模型、设备、runtime、完整输入；association绑定题目、历史Run、原结果subject、父r3、术语目录及配置。started先持久化，completed后保存完整结果hash，未结算窗口停止自动重试。3个逻辑调用均有started/completed，两个编码键与一个重排键见摘要；本轮无未知窗口。**token、精确HTTP、费用仍null**；新增供应商/答案调用0。新索引和25题基准检索不新增推理。

## 实际验证与保护

- 共享24份文件 **270 passed**（含OpenAPI），5条既有SWIG警告；随机隔离Mongo四文件 **34 passed**。定位组28通过；原矩阵副本+最终术语13项合计20通过。组间重叠不累计唯一总数。
- 红测：独立原矩阵4失败/3通过；增加相邻矩阵7失败/5通过；术语设备误归介质单项1失败，修后通过。新模块未创建时的collection error也保留，单独记录不冒充行为红测。无删失败日志。
- 5875正式审计断言、1661额外保护断言分别通过；实际新582原文/向量、父SQ5的582载荷/向量、冻结867及上一structure5的582载荷/向量和非TTL数据库摘要核验。TTL继续单列，不声称历史所有集合不变。
- 历史821/404/294、297/45/20、最近125/26与331/14份保护hash匹配。旧PDF/cache/evidence/output/evals/tmp均保留。001关闭结论不重开，本轮不读取其写入口，不写真实质量、签审、绑定或proof。前端/API契约无改，不扩大无关构建测试。
- 25题两模式逐项复算；未投影的24题与本轮新语料基准context/prompt/groups/budget全等。该全等证据不是新答案质量结论。

## 阶段与下一步

出处补修等待总控定向核验本P2，旧SQ/AF/continuation/图片/比较/001消费及政策接线关闭结论不变。048待处理点已缩至已召回必要正文的weighted融合保留，以及该实际表行出处核清；不重新要求用户找PDF或判断。

M6-04仍缺最终有效结果的助手独立双轮与固定报告；M6-05虽已绑定真实反馈，仍缺有效预校准后同范围独立候选与服务端proof；M6-08仍缺最终题集/语料/配置无生成预检、有序真实质量比较及四题对象/配件新答案效果。正式链保持“基线有效助手双轮→预校准→校准后同范围独立候选双轮→真实反馈proof”。本轮不运行真实dev/heldout、不生成答案、不写正式评分/政策/校准。human发布独立保留。

M6仍4/7，04/05/08未验收，M7未启动。r3仍19继承+66执行、历史stream19/新增61；旧failed/attempt2/provider_invalid_response/retryable=false/results0和调用/费用未知保留。

私有逐题实际证据：`output/m6-layout-terminology-20261030/25题版面出处与术语真实对照.html`。Git仅上传源码、合成回归及脱敏文档/摘要。新空间失败停止引用，旧修订/索引/默认指针保留；源码回切用正常反向提交，不删库或改旧账本。

## 25题统一口径

| 题目 | 必要文本/精确出处 | 术语影响 | 新答案 |
| --- | --- | --- | --- |
| m6-g540-02-a | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| m6-g540-02-b | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| m6-g540-04-a | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| m6-g540-04-b | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| m6-g540-05-a | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| m6-g540-05-b | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| m6-g540-17-a | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| m6-g540-17-b | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| m6-g540-18-b | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| m6-g540-20-a | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-003 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-004 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-006 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-007 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-008 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-009 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-010 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-019 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-020 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-021 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-022 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-034 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-037 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-038 | 已覆盖 | context/prompt/groups/budget均不变 | 未生成 |
| support-v1-048 | 未全部到达 | 稀疏入口改善、融合丢失 | 未生成 |
