# M6-08：SQ续审源码坐标与行标题补修自验

日期：2026-10-28。接续 `a91432a36e9f712af4bfdcf1874f73e94233c52e`，开始时HEAD/origin/main/GitHub main一致，仅tmp未跟踪；相对8f16cdf的后续提交只有复审文档，未覆盖业务改动。本轮顺序执行，无子代理。

依据[第二轮独立复审](M6-08-semantic-quality-review-r2.md)补修SQ-R1-R、SQ-R2-R、SQ-R3-R三个P2项。原7反例已通过的事实保留；本轮仅补修自验，SQ各项**待独立复审，不自行关闭**。原continuation R1/R2/R2-R及图片协议关闭不变，M6仍4/7，04/05/08未验收，M7未授权。通过前不发布语料、不做真实检索或模型质量验证。

## 定位及实现

| 项目 | 已复现根因 | 补修及边界 |
| --- | --- | --- |
| SQ-R1-R/P2 | Python splitlines识别分页符/Unicode分隔符，而CommonMark token.map只按CRLF/CR/LF；图片alt递归的state.pos是子串坐标 | 新增共享app/core/markdown_source.py。块代码跨度仅以CRLF/CR/LF计算原始偏移；生成和切片共用。图片规则进入alt子串时按固定规则labelStart=pos+2累积绝对base，退出用finally恢复，任意层代码跨度都回到原始全文坐标；不靠查找相同字符串猜偏移 |
| SQ-R2-R/P2 | 同一块行号错位把代码后半段交给普通切割 | 正式split_text消费共享原文跨度，围栏仍由固定markdown-it-py决定符号、长度、缩进、未闭合规则；整体超限明确拒绝。chunker4→5，使正式导入指纹区分行为变化 |
| SQ-R3-R/P2 | 任何th被累计为列头，scope=row数据行把表头撑大 | th明确scope=row/rowgroup不新增列头；thead及scope=col列头、多行列头原样保留，数据行标题继续与其值一同行切片，版本/单位条件随数据重复。非连续列头仍明确拒绝，未把结构不明数据升级为列头 |

不删除分页符、不把Unicode分隔符归一化为换行；只在解析器自己的语义里识别换行，原CRLF/CR/LF、分页符和Unicode字符保持原样。合法代码的保护范围精确到对应源码跨度，邻接的真实空导航仍标注，预算继续计投影实际长度，prompt_used_docs和引用原文不变。无题号/命令白名单，无答案回填。

图片alt跨度接线依赖固定markdown-it-py 4.0.0 image/backticks规则的子串约定，升级该依赖需重验递归和坐标回归；不拷贝或重实现上游规则。本轮没有新增依赖、环境配置、API或前端结构。无scope且无thead的任意表头语义、复杂合并单元格仍不保证通用推断，发布前依旧核差异。

## 红绿及回归证据

在新本机目录 `output/m6-semantic-fix-r3-20261028/` 原样复制本轮9项探针执行，旧output与失败原件未修改；另按字节一致副本纳入tests/unit/test_semantic_review_adjacent_probes.py长期回归。

| 证据 | 本轮实际结果 |
| --- | --- |
| red-adjacent.xml | 独立续审探针6失败/3通过，与报告一致 |
| red-coordinates.xml | 新增原文坐标及行标题18项：16失败/2通过 |
| green-boundaries.xml | 初验46通过/2失败；两失败来自新增测试预算40允许两行数据同片，却误断言三片。将夹具预算改为35以要求一行一片，未改业务凑片数，原失败保留 |
| offline-regression.xml | 原251项＋18项相邻边界，269通过 |
| green-independent.xml | 原7项＋本轮独立9项，16通过 |
| integration-regression.xml | 同范围5个隔离Mongo文件，39通过 |

各组不累计唯一总数。新增18项覆盖LF/CRLF/CR与分页符/U+2028/U+2029/U+0085组合，实际prompt及切片原文拼接、代码原子超限；长短前文、嵌套图片alt及其邻接空导航；scope=row/rowgroup与scope=col多行版本/单位列头。原9项通过正式prompt/chunk_document，不加载图片。原251和新增unit由禁联网夹具约束；隔离Mongo使用m1_test_m4_sqfix3随机后缀库与stub索引/供应商，不是实际模型质量证明。SWIG弃用告警离线/探针5条、集成2条，不是失败。

无API/前端变化，未重复typecheck/OpenAPI/浏览器或全量阶段检查；未重跑旧21边界、49/520项。正式双轮、预校准、候选、反馈复评仍未完成。

## 语料、来源与现场

复用既有四份ParsedDocument，起点a91432a旧chunker与本轮chunker5对同输入逐表比较：43张表文本和source_refs相同，四文档分别18/151/64/282片，1360项原文本/表格单元保留，图片来源4/14/20/29保持。实际缓存无显式thead/th：scope修复由合成反例验证，43表用于检查既有路径不退化，不能据此声称真实召回改善。本轮新切片只落新output目录，未embedding、未发布或切换工作台修订。

开始保存297个既有output文件hash（排除自动pycache），结束核对一致，含本轮复审、前轮补修与原件判断。直接只读审计核145历史文件、16份早期补修证据及3处图标来源转写hash，867冻结切片payload和r3持久85结果、旧失败身份保留。21非TTL集合与历史交接相同；run_events历史2315/当前1675，旧导出2308中的634条消失事件均已到期，TTL索引存在。只称符合TTL特征，不归因导出外缺失，不声称跨历史22集合均相同；审计窗口内22集合前后相同。审计计数和摘要见脱敏JSON，原始数据仅本机。

本轮供应商/embedding/真实重排调用0，真实dev/heldout0，正式评分/assistant observation/校准/候选/人工声明0；历史state/lease/slot/retryable或题级关联未写。r3仍19继承＋66执行、历史stream19/新增61，HTTP/费用未知；旧失败failed/attempt2/provider_invalid_response/retryable=false、results0，调用/费用未知。保留tmp/evals/output/evidence，不上传原文、私有日志、完整答案或配置。

## 执行方后续

将源码、合成回归与脱敏材料送总控独立复审，优先核共享坐标消费者、图片alt逐层偏移及行标题/列头区分。通过前不发布语料或切默认修订；通过后由执行方沿新命名空间/新修订验证真实检索与上下文，再走正式发布/回切。源码回切为正常反向提交，保留旧修订/catalog及全部证据，不删记录或改租约。

实际召回及新答案质量尚未验证；正式双轮→预校准→同范围独立候选→反馈后复评依赖继续保留。模型调用前仍须明确范围、幂等来源、检查点身份及计费方案；不要求用户查PDF或重填既有判断，不绕过正式前置。
