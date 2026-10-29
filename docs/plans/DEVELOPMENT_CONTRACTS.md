# 开发公共契约与任务交接边界

## M6-08流式答案过滤边界（2026-10-29）

当前定向复核7c41d33：原4反例通过，AF-R2技术范围通过；AF-R1表格原缺陷已覆盖，但列表续行制表符部分展开使实际token与原文无法逐字匹配，出现AF-R1-R／P2代码改写回归，整体未关闭。后续答案侧坐标必须覆盖解析器的缩进消费与制表符展开，不能全局修改原文或模糊放行；不重开SQ共享实现。274回归及25题已存流通过不能覆盖新增2项红测，也不代表答案质量通过。见[限定结论与整改](../development/reviews/M6-08-answer-filter-review-r2.md)。下文补修自验按历史状态阅读。

AnswerFilter在答案专用映射中以实际inline token.content识别代码，再精确映射至原文；表格各单元格不能借整行map跨格配对反引号，无法精确定位不授予代码豁免。共享SQ坐标工具不变。代码内文本和看似图片的例子逐字保留。解析以html=false执行，代码外`<`以Markdown转义保留可见字符，不将供应商原始HTML作为节点渲染。跨chunk的行内代码歧义段落在空行或final后判定，防止反引号尚未到达时误判代码；围栏起始行收到CR/LF后才能走块代码即时放行，final用完整来源判定，普通感叹号不被延迟。

真实图片语法与代码文本分离：仅允许当前引用已授权资产，外部/未登记图片与残缺引用仍拒绝。题级缓存回放不改Run、历史答案或数据库。AF-R1/AF-R2补修仅自验，待独立复审；该层修复不表示语义或答案质量通过，最终答案仍须正式质量流程独立核验。[本轮补修证据](../development/reviews/M6-08-answer-filter-fix-r2.md)。

## 2026-10-28 · 同25题隔离新答案验证完成，10题仍需补正或召回

接续0c06548，独立运行账本新建25个正式Run并真实生成；复用既存四文档、查询向量与500对重排缓存，不重导入、不切默认，不继承旧19个完成Run。单轮assistant原件分析为15题核心支持、6题部分正确、4题仍未完整答出，未写正式评分/观察/候选/校准/human声明。四题019/021/022/048正文缺口保留；008/034最终过滤丢参数/按钮，04-a跨对象套用能力，05-a/b及17-b未点名MateDock3，均保留实际证据。

实际25次逻辑stream，输入47093/输出37464/总84557 token，HTTP及费用null；供应商usage含reasoning且008输出超过请求max_tokens4096，该参数不作计费硬上限。74共享、25无供应商预检、2046持久/引用/缓存/冻结审计及本机25题报告检查通过，组间不累计；同请求恢复新增调用0。过滤缺陷12种合成损失复现，不冒称修复通过；初次合成预检中断已正式recover，审计/浏览器失败日志保留。

下一条由执行方补修最终AnswerFilter，以合成红测和本轮25份供应商缓存离线前后回放，不追加模型或覆盖答案。四题召回与其他语义补正继续挂账，不交回用户找PDF/填判断。原SQ/continuation/图片/正式接线独立结论保留，582新片/67资产/867冻结片、21非TTL集合及旧证据未变，TTL差异单列。正式双轮及后续质量前置仍保留，默认发布和答案质量未验收。M6仍4/7、04/05/08未验收，M7未授权。见[实际结果、25题结论及下一动作](../development/reviews/M6-08-isolated-answer-quality-r1.md)。以下为历史时点。

## M6来源前提正式接线独立状态（2026-10-28）

本轮c121cbc的身份、授权装载、分组引用与关闭回切独立核验通过，范围限默认关闭的隔离配置；保留weighted，未授权默认发布或M7。下一步转已有25题的隔离新答案验证，首次真实调用前登记配置/源码/语料身份、来源关联、题级幂等和调用账本；不得复用配置不同的旧19条Run，不写human评分或绕过正式质量前置。见[独立结论](../development/reviews/M6-08-prerequisites-wiring-review-r1.md)。以下为历史契约时点。

## M6来源前提正式消费者内部接线契约（2026-10-28）

SourcePrerequisitePolicy通过QueryRunner构造器或受信parameters.source_prerequisites显式传入，默认关闭；不从环境加载，不向HTTP RunInput开放。InternalRunInput规范化配置在prepare前进入请求身份，非缺省配置及SHA保存在新Run；默认旧身份不变。执行期对比配置/SHA，旧缺省Run不能在启用消费者执行，不回填历史。EvaluationStrategy和adapter把配置传至正式消费者/内部Run，完整config检查点身份包含开关、函数版本1、预算及scope。

scope绑定owner/kb、精确m1_test_数据库/集合、冻结doc→revision映射和产品；本次只支持原weighted默认预算，来源前提与旧可选邻接扩展互斥。装载只查本题种子doc/revision/product，并逐资料/产品授权；max_rows≤1000，读取端limit剩余+1超限拒绝，消费端重核行归属/source_refs，不能靠函数同资料关系代替租户授权。groups接正式最终预算/引用；trace保留关系，引用仍经资产/修订和图片关系校验。

关闭回切须新配置/请求，不修改启用旧Run或历史状态；保留旧索引与catalog，不默认发布。当前正式接线131离线/2契约/25无模型回放/66及15隔离集成通过，各组重叠，仍待原总控独立核验；此前来源前提函数与SQ关闭保留，不冒称答案质量通过。[实际边界与证据](../development/reviews/M6-08-prerequisites-wiring-r1.md)。以下为历史契约时点。

## M6固定RRF及显式来源前提对照边界（2026-10-28）

当前独立状态：58296be新增来源前提函数及weighted接线/回切方案通过定向核验，89离线/25实际prompt重放通过；原“仅自验”按历史时点阅读。正式QueryRunner接线仍未实现，下一步须将显式默认关闭配置纳入不可变请求/检查点身份，并兑现授权行读取、groups及引用边界；不追加模型或默认发布。见[独立核验与接线约束](../development/reviews/M6-08-rrf-prerequisites-review-r1.md)。

本次RRF真实候选/重排24/25、context21/25（新增019、退化02-b），不支持默认切换；weighted+前提保留原21。来源前提函数仅显式隔离调用，未接入QueryRunner/API/全局配置。最多1000授权行、20种子、新增4块/总6000字符，封面日期不当适用版本，同修订/产品/路径的近表格对象前提不得由图摘要替代；source_refs不一致或载荷冲突拒绝。groups必须传最终prompt，使依赖与前提原子保留或排除；不改原文/metadata/分数。

既有正式请求/配置指纹尚无本函数开关，若后续接线必须先显式固定开关/函数版本与授权行来源，不暗改默认、不继承不同语料/源码身份的旧19检查点。源处理/索引未变，四修订保持，无需重复导入。18本地调用74新pair、426历史分数复用，未结算窗口停止，HTTP/token/费用null。新函数及接线方案仅自验，既有SQ/图片/continuation关闭保留；正式质量依赖与M6阶段未验收。[实际证据和回切方案](../development/reviews/M6-08-rrf-prerequisites-r1.md)。以下为历史契约时点。

## M6新隔离真实检索证据边界（2026-10-28）

独立核验状态：f923870隔离语料与25题真实检索取证已核验，21/25原文到达口径保留。固定RRF离线复算24/25仅候选池诊断，不冒称真实重排/context改善；下一步在独立配置作真实对照并保留来源前提，不改全局默认。既有SQ关闭不重开、正式质量与M6阶段未验收。见[范围与下一步](../development/reviews/M6-08-isolated-real-retrieval-review-r1.md)。

正式同步导入指纹已实测包含chunker5。新命名空间/新document和revision使用现有校验/CAS发布，仅隔离内部激活，不切默认catalog；不得复用旧revision伪装新处理。67历史图摘要仅按字节+合并Markdown alt+摘要文件来源复用，历史视觉model/prompt未知保持null。三处助手图标转写保留前后hash/页/截图、human=false及pending_review身份。

逐题真实链路要保留双路原始排名及融合响应、重排标题对象输入/输出、context排除和实际prompt。必要PDF原文与image_description分开计；原文21/25到达不等于答案正确率或对象前提完整。2019日期、MateDock精确名称及历史图摘要对象污染单列，不因字节匹配自动授予语义质量。模型调用先记started与稳定输入/模型键，缓存读回恢复稀疏整数键再验hash；未结算窗口停止，不盲重算。未知token/HTTP/费用保持null。

本轮未改公共API/数据模型/默认策略；原参数保持，未生成答案/写正式质量记录，既定正式质量依赖保留。实际结果与唯一后续动作见[交接报告](../development/reviews/M6-08-isolated-real-retrieval-r1.md)。

## SQ续审原始源码坐标与行标题契约（2026-10-28）

当前独立验收状态：5812df4的SQ原三项及续审三项已通过并关闭，原反例16、直接相关离线269及隔离Mongo39通过。此前“待独立复审”为历史状态。下一步可推进新命名空间真实检索验证，真实检索/答案质量与M6业务验收尚未完成。见[独立关闭范围](../development/reviews/M6-08-semantic-quality-review-r3.md)。

生成与chunker5共用app/core/markdown_source：块token.map仅按CRLF/CR/LF映射原文行偏移，不把分页符/U+2028/U+2029等当Markdown换行，不归一化或删除原文。inline代码坐标在图片alt递归时按固定image规则子串起点逐层累计，finally恢复父base，最终保护区相对同一原文。固定markdown-it-py 4.0.0升级须重验递归约定。邻接真空导航仍显式标注，预算计投影实际长度，原证据/引用不变。

HTML th的scope=row/rowgroup是数据行标题，不增加列头；thead与scope=col列头及多行条件仍随数据重复，行标题和值不得分离，非连续列头仍拒绝。不改API/配置/依赖或冻结r3；chunker5区分正式导入新身份，旧解析产物不迁移。SQ-R1-R/R2-R/R3-R仅补修自验、待独立复审，通过前不发布语料，既定正式质量依赖保留。见[本轮报告](../development/reviews/M6-08-semantic-quality-fix-r3.md)。

## SQ补修后证据完整性契约（2026-10-28）

独立复审8f16cdf状态：原7反例通过，但源码绝对坐标/换行映射及行标题识别尚有SQ-R1-R/R2-R/R3-R（P2）待补修，当前实现未完整满足以下目标，通过前不发布语料。见[续审要求](../development/reviews/M6-08-semantic-quality-review-r2.md)。

生成context不再全局替换大于号/emptyset；只标记点击指令中明确连续空导航，未知符号不猜填。使用已固定markdown-it-py块语法和backticks实际源跨度保护fenced/缩进/跨行/变长行内代码；先识别后strip，原引用与prompt_used_docs保持原值，预算计投影实际长度。固定解析器升级须重验源跨度回归。

chunker4用固定Markdown fence/code_block行跨度保持代码原子，开闭符号/长度、缩进、未闭合规则由解析器决定，超限明确拒绝。HTML显式thead/th表头优先于无表头推断；内部Block.table_header_rows缺省1，多行连续表头的完整单位/版本/对象条件随每片数据重复，不连续表头拒绝。无thead常见列名可识别括号限定但输出原完整文本，任意无标记表头语义仍需发布前核查。新字段仅内部解析契约，旧缓存不迁移，正式导入版本指纹变化；原图/continuation协议及API不变。SQ三项自验不替代独立复审，通过前不发布语料；[补修范围](../development/reviews/M6-08-semantic-quality-fix-r2.md)。

## M6语义证据完整性补修契约（2026-10-28）

独立复审状态：d1286e0尚未完整满足以下代码原子性、表头语义及代码保护目标；SQ-R1/P1、SQ-R2/P2、SQ-R3/P2需补修，通过前不发布新语料。具体反例与验收补充见[独立复审](../development/reviews/M6-08-semantic-quality-review-r1.md)。下文为应满足的契约，不能据此宣称当前实现全部通过。

MineruParser structure-3读取code_body，非法空代码显式拒绝；chunker3保持fenced CLI原子，单块超限不截断。同非空章节、同产品/修订、PDF连续页短正文可有界合并，可越过同范围独立版面图，保留所有source_refs与独立图资产；不跨表格/warning/章节/产品/页码缺口。无th两列键值/编号表按行索引，th、多列或常见td列标题继续带表头；表头语义推断有限，新语料发布前做差异核查。正式导入指纹通过parser/chunker版本区分，不覆盖旧修订。

配件登记仅表达有源SHA/页码支持的检索归属，须目录品牌与完整型号匹配，不表示产品等价或兼容承诺。USB标准版本非设备型号，显式未知型号仍澄清。重排passage增加title/heading，不改原证据、分数类型或增加调用。生成context可读投影标识丢失图标，保护代码；引用与prompt_used_docs仍存原文，context图片不因此成为answer图。不新增API、配置或依赖，不回填历史结果/关联。

冻结r3不重导入；本轮四份缓存及图标转写仅新本机修订待审，未embedding/发布/真实生成。不同源码/语料配置不自动继承旧检查点；未知HTTP/费用不补零，正式双轮/预校准/候选依赖不变。详见[边界与回切](../development/reviews/M6-08-semantic-quality-fix-r1.md)。

## M6-08 R2控制/Run分库接线契约（2026-10-28）

正式job显式传递现有控制库能力，API/宿主实验和租约在M2_DB_NAME核验；Run/知识/checkpoint/来源关联仍在冻结target.database。先校验当前控制身份再写conversation/checkpoint/Run，绑定前重验；link固定control_database/target_database映射，父实验读控制库、父题级link读目标库。缺能力/来源/映射明确拒绝，无target fallback、实验复制、旧关联回填或配置迁移。跨库窗口不保证原子性，校验后失效可留下pending，由正式恢复收敛；合法进程重建复用固定请求及Run。R1累计计量契约不变，R1已有独立通过不替代R2复审；M6仍4/7、04/05/08未验收、M7未授权。

## M6-08 continuation R1/R2补修契约（2026-10-28）

正式job在模型前保存experiment/attempt/question/input/config/checkpoint→Run的不可变execution link，校验当代worker与租约，不存worker token。execution与observed_reuse分列，后者只证明当次观察复用。continuation须在新Run前核对指定父experiment/attempt/version及同题输入/配置/Run关联，后续账本绑定父link ID/hash；另一父实验、上一attempt、历史缺失来源明确拒绝，不回填旧记录。新M6题结果logical_provider_calls_scope=run_total、logical_provider_calls来自持久Run累计，execution_logical_provider_calls为当前adapter调用新增量，不参与累计汇总；缺测null。新澄清明确零值随等待事件持久化；结果尚未落盘时崩溃恢复保留累计，不重调或重复计数。旧r3与19继承+66执行不变，精确HTTP/费用未知，未变更API请求结构。

## M6-08显式continuation来源账本（2026-10-28）

创建实验可选continuation严格绑定source_experiment_id/source_attempt/source_version/reason；由服务端校验同owner/kb、failed/cancelled/incomplete终态、当前代际和相同dataset/manifest/config字节hash。保存父state/retryable/error与配置/请求hash快照，父记录不改；省略/null兼容原幂等身份。普通首attempt不提供interrupted重生成键；只有正式continuation允许为中断题派生固定请求。evaluation_continuations用新experiment+checkpoint唯一身份，在调用前持久化父Run/输入hash/request_key，新Run先绑定再执行。重复领取/重建复用同一请求，后续Run再中断不自动新建第三条；completed复用、非retryable失败拒绝。精确HTTP/费用及未测遥测null，不承诺失败窗口exactly-once。只支持相同冻结config；源码身份变化不自动迁移旧检查点，r3历史组合结果不回填。详见[工作台](../evaluation/workbench.md)。

## M6图片协议R1/R2补修：渲染语义与免审门禁（2026-10-27）

答案图判定采用固定markdown-it-py 4.0.0，与前端markdown-it 14.1.0同源；default规则、html=false/linkify=false/breaks=true。只读取实际inline子image token，不递归图片alt，目标协议、ID白名单及授权资产集合与前端一致。列表缩进、转义反引号及引用式图不因手写正则丢失；真正代码块/跨度、转义图、外链、HTML和未授权资产不成为答案图。25项共享字面期望矩阵在Python选择器和实际Vue渲染器分别验证；将来升级任一解析器须一起核对，不能宣称不同实现任意输入永远等价。

审阅写入与质量投影都重新核对正文中的受控图片；即使旧metadata误记context，实际图不能N/A。投影对任何受控图片URL保守要求审核，不因评测结构缺asset_id放行；旧误收N/A记录保留但使新校准拒绝、门槛pending，不回写已有校准。旧引用没有v1标记时全部图像保留为使用关系未知，默认不创建img或发图片请求，展开后才读取。不新增API字段或配置，不迁移真实001，不把显示修正当成相关性得分提高。

日期：2026-10-26。状态：M0至M5总控通过；M6-01执行自验完成，M6-02按授权执行，M7未授权。关联：[开发总清单](DEVELOPMENT_TODO.md)、[原始优化方案](2026-10-22-technical-support-optimization.md)。

## 1. 稳定接口和文件归属

以下约定让阶段间能对齐，而不是提前生成所有业务代码。实现发现不适配时，先更新此文档、影响任务与决策记录，再改消费者；不能只改函数名让后续计划失效。

| 接口/对象 | 建立任务与文件 | 最小输入输出与不变量 | 主要消费者 |
| --- | --- | --- | --- |
| 历史窗口 | M0-03，`app/clients/mongo_history_utils.py` | 保留 `get_recent_messages(session_id: str, limit: int=10) -> list[dict]`；取最近 N 条后正序返回 | 旧图、M2/M4 会话适配 |
| 字符预算 | M0-04，`app/answering/context_budget.py` | `pack_prompt_inputs(docs, history, max_chars=12000)` 返回 context/history/used_chars/used_chunk_ids；不访问 IO | 输出节点；M4 扩展 token 预算 |
| 生成失败 | M0-07，`app/answering/errors.py` | `AnswerGenerationError` 包含 `partial_answer: str`；异常必须传播到外层任务终态 | 旧 API、M2 query_runner |
| 型号匹配 | M0-05，原 `step_5_align_item_names` | 保留 confirmed_item_names/options 字典；非精确的多个高分返回候选 | 原图；M4 规范产品解析器 |
| `SourceRef` | M1-01，`app/knowledge/models.py` | document_id/revision_id、kind、page/section_path/sheet/cell/bbox 可空；明确原件与描述来源 | 解析、切片、引用、PDF、评测标签 |
| `ParsedDocument` | M1-03，`app/ingestion/models.py` | pages/blocks/tables/images、原件 hash、parser/version、质量标记、source_refs | 切片/图像/索引 |
| 知识仓储 | M1-02，`app/knowledge/repository.py` | `register_document`、`create_revision`、`get_active_revisions`；显式接收 kb/owner 范围 | 上传、索引、发布、检索 |
| 发布服务 | M1-09，`app/knowledge/publishing.py` | `RevisionPublisher.validate(revision_id, attempt=...)`、`publish(revision_id, expected_active=...)`、`reconcile(document_id)`；范围由注入repo固定 | 后续维护者API、迁移 |
| 同步领域导入 | M1-11，`app/ingestion/service.py` | `IngestionService.import_file(path, request_id=..., expected_active=...)`；原件/切片/资产按修订回看 | 本机领域调用、M2后续适配 |
| 任务导入阶段 | M2-10，`app/ingestion/runner.py` | `run_import(job_id)`从Mongo领取attempt/token，按对象键和检查点执行；过期attempt不可发布 | Linux Celery worker |
| 问答运行 | M2-04/11，`app/runs/service.py`、`query_runner.py` | 创建、领取、恢复/中断、终态与幂等；旧图经适配器接入 | API、Vue SSE、观测 |
| SSE 消费 | M3-05，`useRunStream.ts` | 输入 run_id 与最后 seq，消费事件/快照，关闭订阅；取消单独调用后端 | ChatPage、Pinia run store |
| 检索候选 | M4-02，`app/retrieval/models.py` | `RetrievalHit`、`QueryPlan`、`EvidencePack`；保留范围、修订、分数来源与实际入选证据 | 检索各节点、引用、评测 |
| 评测最小入口 | M4-01，`app/evaluation/validate_dataset.py`、`runner.py` | 校验 JSONL，按固定配置运行基线；输出可复核逐题结果 | M4 消融；M6 扩展指标/工作台 |

函数参数与 Pydantic 类型在该任务实施时于单独规格中冻结；任务文件里未出现的内部方法不能被后续任务假定存在。对外 API/事件字段使用下述名称，变更需记录兼容方式。

## 2. ID、归属与版本

M1-01已冻结Pydantic实体契约，具体字段及UUID/SourceRef规则见[知识schema](../architecture/knowledge-schema.md)。空活动指针/未知定位允许null；非空ID严格字符串，禁止以整数暗中转换。业务ID独立随机UUID；修订内结构ID由stable_id(kind, revision_id, parts)的规范JSON UUID5确定。

- 所有对外 ID 使用字符串；Mongo ObjectId/Milvus 64 位 ID 不直接作为 JavaScript number。
- document_id 表示业务资料，revision_id 表示不可变修订，chunk_uid 表示稳定切片，asset_id 表示原件/图像。文件名与 hash 不替代业务 ID。
- 每个 run 保存用户、kb、产品与知识修订快照；授权既检查 owner，也检查当前知识访问范围。历史引用的精确修订不能被新版悄悄替换。
- Mongo standalone 不依赖多文档事务。跨集合一致性采用单文档条件更新、幂等键、派发账本和核对补偿；并发/崩溃窗口必须有测试。
- active_revision_id 条件发布与检索过滤使用同一份活动修订清单；指针切换不保证已经开始的查询立刻换版本，已开始 run 按自己的修订快照回答。

## 3. API 约定

统一前缀 `/api/v1`。以下为最小契约；M2-12 输出真实 OpenAPI 后前端生成类型。列表统一返回 `items`、`next_cursor`；错误返回 `error.code`、`error.message`、`error.details`、`request_id`。details 不含密钥或私有完整文档。

| 接口 | 请求要点 | 响应/约束 | 建立任务 |
| --- | --- | --- | --- |
| `POST /auth/login` | username/password；Origin 校验与限流 | 登录 cookie，用户/角色/CSRF 令牌；不返回密码散列 | M2-02 |
| `POST /auth/logout`、`GET /me` | cookie，写请求 CSRF | 撤销登录；当前身份与允许范围 | M2-02 |
| `GET/POST /conversations` | title/kb_id/product_ids | 目录/新会话，owner 由服务端设置 | M2-03 |
| `PATCH /conversations/{id}` | title/archived，乐观版本 | 更新自身会话，禁止改 owner | M2-03 |
| `GET /conversations/{id}/messages` | cursor/limit | 正序历史分页；逐轮产品/引用快照 | M2-03 |
| `POST /conversations/{id}/runs` | client_request_id、question、product_ids、kb_id | 202持久快照；同幂等请求返回同 run；同键不同内容 409 | M2-04 |
| `GET /runs/{id}` | 已登录身份 | state、seq、answer（运行中为部分文本）、citations、candidates、resume_point | M2-05 |
| `GET /runs/{id}/events` | `Last-Event-ID` 或 `after_seq` | text/event-stream；游标失效 410，再读快照 | M2-05 |
| `POST /runs/{id}/confirm-product` | product_ids、expected_version | 只允许从持久候选中选，owner 与版本必须匹配 | M2-06 |
| `POST /runs/{id}/cancel` | expected_version，可重复请求 | 记录取消意图；终态不复活 | M2-06 |
| `GET /products`、`GET /products/{id}/documents` | 搜索/分页 | 返回授权目录和活动修订信息 | M2-07 |
| `POST /documents` | multipart 原件、kb_id、product_ids、client_request_id | 202 + document_id/revision_id/job_id；名称仅展示 | M2-07 |
| `GET /documents`、`GET /documents/{id}/revisions` | 过滤/分页 | 状态与解析质量，不将已上传视为已发布 | M2-07 |
| `GET /documents/{id}/revisions/{rid}/chunks` | cursor/limit | 维护者切片、来源和图片预览 | M2-07 |
| `POST /documents/{id}/revisions/{rid}/publish` | expected_active_revision_id | validated 修订才可发布；维护者权限与 CAS | M2-07/M1-09 |
| `POST /documents/{id}/rollback` | target_revision_id、expected_active_revision_id | 目标需是可用已验证版本；不删除当前修订 | M2-07/M1-09 |
| `POST /documents/{id}/withdraw` | expected_active_revision_id | 撤回活动指针；历史引用按授权仍可回看 | M2-07 |
| `GET /import-jobs/{id}`、`POST /import-jobs/{id}/retry` | job 与权限 | 阶段、attempt、错误码、是否可重试 | M2-07/09/10 |
| `GET /runs/{id}/citations/{cid}` | owner/kb 校验 | 原文、来源、定位、asset_ids、修订与解析质量 | M2-08 |
| `GET /assets/{id}` | 授权、Range | 图像/原件；PDF 支持 200/206/416 | M2-08 |
| `GET/POST /cases`、`PATCH /cases/{id}` | run_id、用户编辑、expected_version | draft→用户确认后 confirmed；只修改授权记录 | M5-03 |
| `POST /cases/{id}/confirm`、`GET /cases/{id}/export` | 用户确认/导出格式 Markdown | 不将 AI 步骤当已执行事实；导出受控引用 | M5-03/07 |
| `POST /feedback` | run_id、citation_ids、category、note | pending_review，不自动入库 | M5-07 |
| `GET/POST /eval-sets`、`POST /experiments` | 数据/配置版本 | 有权限的评测任务，独立队列预算 | M6-01/03 |
| `GET /experiments`、`GET /experiments/{id}`、`GET /experiments/{id}/results` | 当前所有者/kb、实验ID和题级游标 | 真实状态/统计/题级结果与同题集基线差异 | M6-03 |
| `GET /experiments/{id}/results/{question_id}/images/{document_sha256}/{page}/{asset_sha256}` | 当前维护者、当前结果attempt中的完整引用三元组 | 仅当前实验所属授权知识库内、原件SHA/物理页/图像SHA完全匹配的图片字节；私有不缓存、不返回对象键或签名URL | M6-04 |
| `GET /eval-catalog`、`POST /experiments/{id}/cancel`、`POST /experiments/{id}/retry` | 目录ID或expected_version | 受控登记选项；取消意图/可重试失败门禁 | M6-03 |
| `GET/POST /experiments/{id}/reviews`、`POST /experiments/{id}/reviews/{review_id}/followups`、`POST /experiments/{id}/calibrations`、`GET /experiments/{id}/release-gate` | 原题级结果指纹、原审核者/审阅ID/轮次、未知维度及逐项证据、校准ID | 原审阅不可变；原审核者仅对该轮全部unknown追加一次不可变结论；幂等及原审阅唯一键拒绝覆盖/并发竞争；仅当前结果匹配且无其他未解unknown时校准 | M6-04 |
| `POST /feedback/{id}/review` | 审核结论/回归题或修订链接 | 只有维护者审核，记录理由 | M6-05 |
| `GET /feedback`、`POST /feedback/{id}/bind-revision`、`POST /feedback/{id}/quality-proof` | 知识库、版本、新修订/受影响题、实际实验/校准 | 重新授权的审核队列、修订门禁绑定及有序回归证明；不接受客户端质量分 | M6-05 |
| `GET /runs/{id}/telemetry`、`GET /run-telemetry` | 当前owner/kb、run或分页游标 | 安全耗时/阶段/失败/降级/修订/逻辑调用统计；私有正文和未采集计量不外泄 | M6-07 |

M6审阅追加复核契约：`POST /experiments/{eid}/reviews/{review_id}/followups`仅接受原reviewer_id对应的已登录维护者、当前完整结果指纹和原human记录。请求须包含本人重新核对原件声明、`resolutions`（恰好覆盖该轮全部且仅全部`unknown`维度，每项含0/1/2或`not_applicable`与非空依据）、不可变幂等键及可追加的关键错误。服务端以`(experiment_id, review_id)`唯一键仲裁竞争，原审阅不更新；重复相同幂等请求回原追加记录，异内容或第二追加方409。结果变化409、他人/他题404、无维护权限403、结构/依据错误422。审阅查询附带追加记录。质量门槛只将同一原审核者、原结果指纹、原审阅内容hash均匹配的追加结论应用于该条unknown；确定分数和关键错误不可撤回。其他审阅的unknown仍pending；双轮对not_applicable适用性不一致仍pending；新增追加记录会改变冻结校准指纹并要求重新校准。没有业务步骤的兼容性题可由本人说明“不适用”，含图像来源必须核对其用途及相关性，不能自动免审。此能力不重新执行模型、不自动发布知识。

M6审阅图片契约：`GET /experiments/{eid}/results/{question_id}/images/{document_sha256}/{page}/{asset_sha256}`只接受维护者/管理员，重新读取实验当前`result_attempt`并要求该题结果中存在完全相同的原件SHA、物理页和图片SHA引用；随后仅在该实验绑定知识库内查找匹配修订与`knowledge_assets`，由`KnowledgeGateway.revision`再次确认当前账号仍有权访问，最后用既有`read_asset`验证图像字节SHA。实验、题目、引用、修订、页码或hash任一不匹配均404，不向浏览器返回`asset_id`、对象键或签名URL；响应为私有`no-store`图像字节。UI图片失败/来源页缺失时明确提示并保留unknown。提交控件须说明依据、本人核对声明或不可覆盖记录的实际缺项；不可变原记录引导到本人的未知项追加复核，不能由前端排序/改写历史绕过。

鉴权约定：未登录 401；已登录但无功能权限 403；访问不属于自己或无知识范围权限的具体资源返回不泄露存在性的 404；版本/占用/幂等内容冲突 409；游标过期 410；超限大小 413；不支持媒体 415；格式校验 422。前端显式处理，不将所有失败包装为“网络错误”。

## 4. 运行状态机与事件

状态：`pending`、`running`、`awaiting_input`、`cancel_requested`、`completed`、`failed`、`cancelled`、`interrupted`。前四者为非终态，同一会话只占用一个非终态 run。

- 创建后 pending→running。需要型号/补充信息进入 awaiting_input，确认后pending重新领取，再恢复running。
- 取消先进入 cancel_requested；阶段或生成器检查取消，最终 cancelled。浏览器断开不自动取消。
- 只有所有必要阶段成功且无取消意图才 completed。供应商在部分答案后失败为 failed，部分文本保留但不能当最终成功答案。
- 执行进程异常退出且运行租约过期时 interrupted；awaiting_input 没有活动 worker 时不能仅因执行租约过期误判中断。等待超时策略在 M2-06 明确配置。
- 终态互斥、不可复活；新请求创建新 run。释放会话占用采用条件匹配 run_id，旧 run 不能清除新占用。

每个事件字段：`run_id: str`、`seq: int`、`type: str`、`at: ISO8601 UTC`、`payload: object`。SSE `id` 为 seq；comment 心跳不分配 seq。seq 严格递增，可有间隙，禁止依赖相邻整数连续性。

| type | payload 关键字段 |
| --- | --- |
| `run.started` | conversation_id、message_id、策略/修订快照标识 |
| `stage.changed` | stage、state、进度可空、降级说明 |
| `product.candidates` | candidates、expected_version、澄清原因 |
| `product.confirmed` | product_ids、上下文版本 |
| `input.required` | 缺少的槽位、expected_version |
| `answer.delta` | text；重连后按 run_id/seq 去重 |
| `citation.selected` | 本次实际入选证据的 citation 列表 |
| `artifact.ready` | 处理清单/草稿的 ID 与类型 |
| `run.completed` | 最终答案/引用快照版本 |
| `run.failed` | 可公开错误码、阶段、partial_answer 标识 |
| `run.cancelled`、`run.interrupted` | 原因、是否有部分文本、可重试标识 |

终态持久化成功后再发事件；同一 run 只允许一个终态事件类型。考虑“状态写入后进程退出、事件尚未写入”窗口：在同一个 run 文档持久化待发终态 outbox，再幂等写入事件日志；客户端始终可以读快照，不能只靠进程内队列。

delta 约 50–100ms 合并，最终按压测调节；默认事件保留 24h，最终答案与引用按业务保留。服务端过期游标返回 410；Vue 关闭旧流，加载快照，再根据是否仍在运行决定订阅，不重放虚构增量。

## 5. 前端状态与复用

M3-08兼容补充：授权引用响应可空`original: {asset_id,media_type,name,url}`，从精确document/revision登记读取并重新授权；url仅`/api/v1/assets/{asset_id}`，无object_key/bucket/签名URL。历史未登记原件返回null，禁止前端推导原件ID或补造页码/bbox。PDF坐标采用SourceRef.normalized_top_left，叠加原页面旋转与用户旋转，未给bbox不绘制高亮。

M3实际消费说明：原生EventSource不暴露HTTP错误状态，onerror（含410）关闭旧流后GET持久快照，按新seq/非终态再订阅；401/403/404停止，暂态网络/5xx退避。终态事件、快照和命令响应按同run/seq折叠，旧回调epoch失效；取消是独立命令，断流不取消。输入schema由OpenAPI生成，当前动态响应未声明schema，响应TS类型按实际公开字段维护，不能声称完整响应全自动生成。

- Vue Query 管会话/资料/任务/实验等服务快照；query key 包含用户和知识范围。
- Pinia 管当前设备/抽屉等界面状态及按 run_id 隔离的流式状态。不得把相同完整会话数据长期再维护一份。
- run 结束后使对应 query 失效；退出登录清空查询缓存并关闭所有订阅。跨会话切换不复用 delta 缓冲。
- 默认自有 Vue 聊天组件；shadcn-vue 复用基础 UI；PDF.js 自封装。第三方库没有实际构建验证前不能写成“已集成”。
- M3-01 建立固定脚本：`typecheck`（vue-tsc）、`build`（Vite）、`test:unit`（Vitest）、`test:e2e`（Playwright）；测试名过滤语法随锁定版本实测并更新计划。

## 6. 验证、配置与可选范围

M1-11新增同步IngestionService接线已批准M1能力，无M2任务/API。import_file要求request_id/expected_active，支持同资料新修订；原件/解析JSON/原始配图快照写指定对象前缀，失败类型向外传播且仅当前staged attempt可置failed。恢复复用快照及摘要缓存；配置/图片输入变化须新修订。来源回看方法逐项复核仓储范围，完成旧请求不会自动激活已回滚版本。缺图/未解析远程图或摘要未就绪不能发布；PDF显式降级质量保留、标题跨段传播，结构版本为structure-2。V2Index验证完整字段类型，Mongo knowledge_chunk_claims唯一身份预留防止跨修订主键覆盖，要求同一v2集合对应同一注册表数据库；发布验证父关系同修订且无环，learned sparse必须正权重。公开任务接线与生产权限仍由M2承担。

M1-10迁移工具接受显式source_id/name/original_key/original_sha256/chunk_ids及images(url/object_key/sha256)清单。dry-run零服务写；无清单退出2、报告缺项。backup_selection只读选定源并保存完整本地快照；restore_sample要求独立空Mongo和新Milvus/对象前缀，读回一致才生成recovery-report。migrate_batch在任何注册前检查恢复报告/快照hash，只允许1–3份m1_test隔离小样，按快照hash＋源身份checkpoint恢复；同名不合并，旧绝对图URL映射asset://ID，源坐标缺失仍null。全库发现/全量迁移不在当前授权。

M1-09的RevisionPublisher(repo,index,read_original,asset_store)以validate(revision_id,attempt)校验原件、完整索引及图资产并转validated；publish(revision_id,expected_active)重验并CAS单资料活动指针，首次expected_active=None。指针文档内outbox可由reconcile(document_id)修复发布状态；历史validated/published目标可通过同入口回滚，不删新版。索引前冻结index_identity，载荷变化必须新建修订。无跨集合事务，旧公开查询图保持兼容，M2再接任务协议。

M1-08的V2Index使用显式新集合、INT32 ordinal、来源JSON和BGE dense/learned sparse；所有范围值严格字符串JSON转义。write_revision要求staged/attempt一致，同UID正文或元数据变化拒绝；索引清单含正文hash与完整业务载荷hash。search默认读取活动修订快照，空快照不编码；内部显式快照也须复核调用归属。旧集合不删不重建。

M1-07的chunk_document(parsed,max_chars=2000,default_product_ids=())返回Chunk；完整标题留元数据不重复占长标题正文预算，chunk_uid由修订/块/分片/内容hash及上限稳定生成，子片父指向同块首片。原子图片/表格单行超限显式失败，表头重复、行范围真实，Excel单元格refs原样保留；来源document/revision不匹配拒绝。按块不跨型号合并；字符预算不是token预算。旧splitter复用split_text完成N1兜底，原M0章节身份/表格边界不变。

M1-06的process_images返回新ParsedDocument及Asset列表，原文不写模型描述；派生块kind=image、description单独存，SourceRef.kind=image_description。稳定asset_id连接原图片及摘要，重试替换派生块。ImageSummaryService联合键包含原图/上下文hash、模型、prompt版本；MongoSummaryCache以owner/lease CAS，忙碌抛SummaryBusy，失败可再次领取。SharedRateLimiter通过同MongoRateStore/key预约全部导入的供应商slot，不是每线程限额。AssetStore要求注入已存在bucket客户端，只写指定前缀，不调用建桶或策略修改。租约是有界排重，不承诺外部计费跨硬崩溃exactly-once。

M1-05的ExcelParser(purpose=None)不计算公式，Cell分别记录value/formula/cached_value，来源保留sheet/cell/row，未知坐标不补；工作簿用途默认unknown，项目计划标记project_plan，只有显式用途才能当technical。MarkdownParser(purpose='unknown')保留原文图片语法和行/章节路径，本地安全相对图片登记ParsedImage，远程/缺图标记质量并不联网下载。两解析器由ParserRouter注入，不改旧Excel导入图。

M1-04提供MineruParser(provider,work_dir,max_pages,max_bytes,allow_native_fallback=False)。原件hash/修订/解析版本/限制/降级策略共同隔离检查点；保留segment_offset/hash/batch_id/result hash，成功段直接复用，超时恢复原batch。原始page_idx为0起，仅合法段内页码加offset+1；无页码时保持null和质量标记。缺content_list可用Markdown修复但显式structure_repaired/missing_page_refs；原生降级需显式选择并记录provider_timeout/provider_error。批次领取到上传之间进程中断不承诺供应商exactly-once，保留批次供核对，不伪造成功。

M1-03解析契约已实现：ParsedDocument含pages/blocks/images与tables视图、original_sha256/parser/parser_version/quality_flags/purpose；Block的text为原文、description为模型派生描述，source_refs/product_ids/asset_ids单独传播。ParserRouter注入按pdf/md/xlsx注册的Parser，先detect_format验证实际结构；缺适配器或格式不匹配明确失败。旧导入node_entry共用检测但不接Excel，不能宣称旧图完成XLSX；新流水线使用注入解析器。M2持久runner接线见下方M2-09/10契约。

- M0 单元与契约测试不连接真实服务。集成/供应商验证必须显式标记，缺条件不能悄悄跳过后宣称全链路通过。
- M0-02 定义 `unit`、`contract`、`integration`、`e2e`、`live_provider` 标记。integration 必须有独立库/集合/对象前缀；live_provider 明确会产生调用成本。
- M4-01 同步建立最小题集校验器/基线运行器；M6 扩展并提供 UI，不能让 M4 的实验依赖尚未实现的 M6。
- 最小运行器入口固定为 `python -m app.evaluation.runner --dataset <JSONL> --config <YAML> --output <结果目录>`；输出逐题 JSONL 和包含数据/模型/prompt/策略版本的 manifest。M4 的所有消融复用该入口，各次实际参数写入验收记录。
- Redis/Celery、登录会话、测试隔离、任务超时等新配置在相关实施任务中命名并附中文解释；不在规划阶段猜测实际密钥是否可用。
- 可选任务：M5-06 MCP 网页工具、M6-06 Ragas 评分。选择延期时记录原因、影响、重新评估条件，不虚构集成通过。
- 文档是执行依据；任务路径、接口、依赖随真实实现变化时在同一项工作里同步。兼容性或范围取舍追加到[决策记录](../development/DECISIONS.md)。


### M0-02 实施边界

离线测试使用正常模块导入，网络与真实客户端默认拒绝；测试标记不隐式开放网络。旧 API 的 `query_app` 默认 None，经 `get_query_app()` 首次调用建立，允许测试注入 invoke 对象。Mongo 与模型 SDK 延迟初始化；保持原业务接口。CUDA 环境不执行通用锁全量 sync，证据见 M0-02。


### M0-04 字符预算实施

`pack_prompt_inputs` 额外返回 `used_doc_indices: list[int]`，用于 chunk_id 为空的联网证据映射。`used_chars == len(context)+len(history)`，空输入为空串；不插入额外占位文本。预算只包含证据/历史，不含模板、问题与输出 token。图状态增加 used_chunk_ids/prompt_used_docs/prompt_input_chars；图片仅来自 prompt_used_docs，避免落选证据配图。


### M0-06 合并实施边界

`_merge_short_sections` 新增可选 max_length=2000，调用者传入真实 max_len。返回副本，缺来源/父标识不合并，来源/产品/结构/表格不同不合并；新增 merged_titles/merged_parts 保存完整标题和片段号。长块拆分保留输入元数据，尚不等同于 M1 SourceRef 实现。


### M0-07 旧接口兼容变化

生成异常 `AnswerGenerationError(RuntimeError)` 携带 partial_answer，通过实际节点/图调用传播。输出节点不发终态；旧 API 的 run_query_graph 在整图成功后设置 completed 并发送唯一 final，失败设置 failed、保留 partial_answer 和公开 error，不保存成功助手消息。非流式 POST /query 失败由原 200 改为 502（status=failed/answer 为空），成功保留原字段并增加 status=completed。每轮清空上一轮进程内结果；没有实现 M2 的持久运行协议。


### M0-09 外层补充

旧 GET /history 的 limit 必须 >=1，无效值返回 422（访问仓储前）。多主体匹配只要还有候选歧义，step_6 优先返回澄清，不基于另一已确认主体继续查询。SDK FlagEmbedding 1.3.5 的设备构造参数 devices 正确接收 BGE_RERANKER_DEVICE。

### M0 第 2 轮审查修复边界

标题拆分为每轮调用生成随机运行前缀、每个章节实例分配 `section_instance_id`，包括同名标题的独立实例；长块通过副本传播。合并须具备非空且相同的实例 ID，或调用方显式可靠 section_id，并满足原来源/产品/父标题/结构/大小约束。heading_path/标题文字/part 相等不能单独作身份；本字段只在当前切片处理内使用，不是 M1 持久知识 ID，也不迁移既有 Milvus 数据。原有无分隔符长串/超长标题超预算边界交 M1-07，M0 不宣称所有长块严格限长。

图片验收由 `scripts/verification/image_acceptance.py` 共享实现。准确对象清单以真实配置绑定 origin/bucket/key/复制时 SHA256，不从答案 URL 推断允许范围；未知 URL 在请求前拒绝，GET 禁止自动重定向。正文须包含人工确认的预期拓扑图、final 须含同图，final.answer 与实际答案一致，正文引用图均在 final 中；可额外携带其他已记录合法入选图。所有引用/final 图响应均须 HTTP 200、image/* Content-Type、SHA256 相符、可完整解码且实际格式与 MIME 一致。校验结果只记 key/hash/类型/尺寸/状态，不回显 URL 或异常正文。离线 fake 通过不代表真实图 HTTP 通过。

每轮审查生成器必须使用 --spec 选择实际报告、测试结果与新输出前缀；测试数和状态从实际证据/清单读取，检查器不固定 73 或特定失败状态，不覆盖旧提交快照。原已知题/追问证据可保留；R3 须另有正常配置且无脚本专有预热/线程覆盖的全新进程冷启动证据。

### M0 第3轮验收补充

允许既有HTTP元数据image/jpg作为image/jpeg的限定别名，仍须实际JPEG、复制时精确SHA256、verify/load完整解码；PNG/其他类型不能借此通过。不修改对象元数据或桶策略。只读复核必须用原响应正文SHA256唯一匹配真实持久化助手消息，且原报告已证明唯一final、正文/final一致及图集合合法；再比对持久化图集合与原final并真实下载。复核退出码与源命令退出码分别记录，不把重新构造参数当新final事件。正常冷启动报告须说明隔离/日志/下载保护覆盖及实际线程环境，不把图片诊断预热结果当冷启动。第三轮自验见M0-submission-r3.md，总控已通过，授权与验证边界见M0-review-r3.md及REVIEW_STATUS.md；提交快照的待审查字段按原时点保留。

## M1审查修复：表格物理来源与处理版本

Markdown解析器版本2按实际标题级别维护路径；表格rows不含分隔语法，row_numbers与每一数据行一一对应原文件物理行（含表头）。拆片SourceRef首项指正文范围，重复表头使用独立SourceRef。Excel短横线是数据，保留sheet/cell/实际row；PDF未知行/列不推算。切片版本2进入pipeline_identity，升级解析/切片需新请求修订，不回写已发布旧产物；历史回看使用已存载荷。
## M1审查修复：自包含恢复与目标保护

backup_selection输出version=2，milvus_schema/milvus_indexes纳入snapshot_sha256；restore_sample不得读取源服务，仅使用本地快照及目标客户端。旧v1缺元信息明确拒绝，保留旧快照并另建新版。恢复保留原主键、全部业务/动态字段、向量与对象引用。Mongo/Milvus/MinIO所有目标检查在任何写入前完成；拒绝源目录重叠、已有对象/非空前缀及非规范路径，默认不覆盖或续跑失败目标。测试使用新隔离目标，不删除真实源来模拟不可用。

## M2-01实际入口与生命周期

app.main:create_app(settings=None,resource_factory=open_resources)建立/api/v1；默认lifespan读取Settings并建立Mongo连接，退出关闭，import不建资源。健康/api/v1/health。错误含error.code/message/details和request_id；验证错误仅返回字段位置、不回显输入，未知异常统一500脱敏。旧查询/导入服务继续作为独立本机兼容入口，不挂载新路由、不新增弃用日期；不把旧服务误称受新鉴权保护。后续M2路由仅加入新application。

## M2-02实际身份契约

POST /api/v1/auth/login校验明确Origin与Mongo持久来源限流，返回user（user_id/username/role/kb_ids）和csrf_token及support_session HttpOnly/SameSite Strict Cookie；GET /me恢复公开身份与CSRF；POST /auth/logout需Origin和X-CSRF-Token并撤销会话。账号/会话/限流在users/login_sessions/login_attempts，密码scrypt含随机salt，原始会话令牌不入库。401登录失效、403同源/CSRF/功能权限、404具体资源越权；字段验证不回显输入。viewer无维护权限，所有角色的kb范围仍必须显式授权。账号仅本机create_user.py交互创建，无默认账号密码，不改真实.env。

## M2-03实际会话与消息契约

GET/POST /api/v1/conversations、PATCH /conversations/{id}（expected_version）、GET /conversations/{id}/messages。目录按字符串ID游标，消息按原子ordinal游标，limit为1–100，消息cursor非负整数；允许序号间隙，不以时间戳分页。每次查询按owner及当前kb授权，越权404。消息message_id由run_id和role稳定生成；同ID不同快照409，product_snapshot/citations持久后不可变。会话创建的product_ids为默认选择，实际逐轮快照在创建run时冻结，不改旧消息。

## M2-04实际运行领取契约

POST /conversations/{id}/runs接受question/client_request_id/kb_id/product_ids，返回202持久快照；GET /runs/{run_id}复核owner及当前kb。幂等键(owner,conversation,client_request_id)，同键不同输入409；消息ID由run/role稳定派生。先持久preparing运行再CAS会话active_run_id，之后标claimed并幂等写用户消息；请求重试或RunRepository.reconcile可核对补足任一步中断。竞争失败请求持久rejected且同键仍409；完成重试不会重新占用。终态释放仅匹配本run，不能清除新run。无Mongo多文档事务、无全局内存锁。执行/事件在后续任务接线。

## M2-05实际事件与恢复契约

GET /runs/{id}/events接受非负after_seq及Last-Event-ID（取较大值），返回text/event-stream，每条id为seq、event为type、data为完整信封；15秒注释心跳不分配seq，禁止代理缓冲。先验证身份/资源/游标再返回200，流中继续检查当前账号和kb；断流不取消后台运行。EventLedger.emit在run文档CAS增加版本/seq、状态/答案及outbox，再幂等投递run_events，保存失败向外传播、不伪成功；新实例read/flush补投。允许序号间隙，终态互斥。每条事件独立24h TTL，读取显式核对真实游标事件（初始0核对首事件），不依赖TTL即时清理；缺失/过期410，前端读GET快照。超出当前seq或格式错误422。DeltaBuffer约75ms/8Ki字符或显式终态前flush。

## M2-06实际命令与租约契约

POST /runs/{id}/confirm-product要求expected_version/product_ids，校验当前awaiting_input、owner/kb/候选/人工期限；保存新产品快照及恢复点后pending，重新领取执行token，旧token不能结束新执行。POST /runs/{id}/cancel按版本保存cancel_requested，同一expected_version重复取消幂等；运行边界收敛cancelled，取消后拒绝completed。终态不可复活。执行租约续约也增加version，扫描不能按旧版本中断已续约任务；人工等待独立超时。run.input_product_snapshot冻结创建时用户消息选择，run.product_snapshot可随确认变化，避免原请求重发篡改旧消息。默认执行60秒、排队300秒、人工86400秒，每10秒CAS扫描恢复；新run占用不会被旧run释放。

取消意图存在但原执行租约失效时标interrupted（未获得执行器停止确认）；未开始执行/人工等待无租约的取消可由扫描直接收敛cancelled。

M2-07知识数据使用显式M2_KNOWLEDGE_OWNER_ID的单组织归属，用户当前kb授权仍必须匹配；个人会话/运行不共享。产品需knowledge_product_kbs显式绑定kb。上传接收multipart file/kb_id/product_ids(JSON列表)/client_request_id，可指定document_id建立新修订；purpose默认unknown。请求绑定原件hash和元数据，先登记不可变修订/任务，再保存随机对象键，成功后202；实际导入/发布在后续执行任务或维护API完成。旧课程资料不自动接管。

## M2-08实际资产契约

上传响应新增original_asset_id。GET /assets/{id}先授权组织owner+当前kb+修订，原件/图片验SHA256；PDF返回Accept-Ranges及单段bytes 206，无效/多段416含Content-Range bytes */size，完整200。撤回不删历史原件。GET /runs/{rid}/citations/{cid}需个人run和该轮入选citation，复核资料/图片修订，返回原文与display_text/asset_urls（仅登记asset://）；不对任意外部图片发请求。旧图映射只接受维护者显式对象/hash清单，完整解码后登记稳定ID；旧桶策略不改。旧get_minio_client不再在import或首次调用建桶/设置公开策略，运维需事先准备桶。


## M2-09/10持久导入执行契约

Mongo import_jobs为事实账本，先发broker再确认dispatch_pending，消息仅job_id。至少一次投递由pending/过期running条件领取及attempt/token/期限fencing收敛；completed重复投递不执行。心跳续任务和资料发布许可，旧attempt/过期许可不能保存或切换活动指针。对象仅相对key，禁止Windows路径、URL、穿越。Redis Lua跨worker原子预约供应商预算。

原件验hash，parsed/原图对象、摘要缓存、分批嵌入检查点复用；MinerU分段batch挂持久卷。429/超时/5xx可重试，格式/鉴权/配置先处理，公开错误仅code/stage。验证来源/索引后才发布；已发布终态中断可核对修订收敛。供应商响应至检查点保存窗口不承诺付费exactly-once。Linux强停仅独立测试worker，生产灾备未验收。


## M2-11实际问答适配契约

API生命周期每200ms扫描claimed/pending，进程最多4个运行，Mongo start CAS防多进程重复领取；每租约三分之一续约。SSE断连不影响执行。型号仅显式组织/kb产品；无选择且多候选时awaiting_input，最多50，确认后新token继续。当前用户启用/kb在执行边界复核，撤权停止输出并记脱敏失败。

v2检索冻结活动修订，产品过滤，真实重排保留完整来源元数据，旧回答节点预算选出实际入选证据；无入选证据明确回答并不调LLM。ContextVar出口将旧delta转持久answer.delta，不创建session队列/旧history。引用为本run稳定citation_id及原文/来源/资产快照。输出仅允许本轮入选asset的受控图片路径，分段图片与HTML在写事件前过滤。

completed CAS同时保存completion_snapshot，assistant消息稳定ID幂等落库，恢复扫描补偿CAS后消息丢失；错误保留部分答案/阶段且无成功assistant。取消/失联按M2-06收敛，旧执行不能迟到completed。旧整图仍独立保留，不将旧课程检索挂到新权限体系。

### M2复审错误分类

导入供应商超时（含OpenAI APITimeoutError/httpx.TimeoutException）公开upstream_timeout；连接失败（含OpenAI APIConnectionError/httpx.NetworkError）公开upstream_connection_failed，均retryable=true。429/5xx可重试，401/403及400/格式错误不可自动重试。普通文件OSError不作为网络超时；维护者与expected_version门禁不变。

M2复审许可补充：跨job仅原子接管import_lease_until已过期的许可；同job更高attempt/同代异token保护，旧heartbeat/finally完整permit匹配，不影响接管者。最终发布fencing不变。

### M2复审完成消息与下一轮顺序

completed CAS持久保存completion_snapshot后，先幂等写assistant再释放会话。RunRepository.release从账本重读快照，各终态出口/事件flush/恢复复用；新轮reconcile先补偿active旧终态再CAS领取。写失败不释放旧占用，不插入下一轮user，可用相同client_request_id恢复。跨实例并发补偿只保留同一稳定消息，ordinal保持首次写入的值，不重排或改时间；释放仅匹配本run。正常QueryRunner每次completed均保存快照；历史低层无快照终态保留兼容，不推测生成答案。

## M3工作台消费与恢复契约

浏览器只请求同源/api/v1，Cookie身份与CSRF；不读供应商密钥，不把签名对象URL或内部对象键交给浏览器。输入类型来自版本化OpenAPI；无响应schema的动态字段按真实公开接口补充，不能声称完全自动响应生成。

Vue Query按用户/kb隔离目录与历史；401/退出清Query、设备/证据UI并关流。Pinia只保存活动run与UI；历史以持久message_id/ordinal为准。EventSource按run/seq去重，断连/410先回快照再订阅；终态不重连。确认带展示version，冲突后重选；取消独立POST，失败保留部分答案而不显示完成。

引用编号关联该run稳定citation_id，原图仅登记资产白名单；HTML和危险链接禁用。引用可空original由精确修订登记与授权产生；PDF.js本地固定版本、坐标换算、无bbox只定位页，取消旧渲染并拒绝迟到结果。

上传接收、导入完成与活动发布是不同状态；client_request_id处理网络重试，维护操作带版本或活动指针CAS。前端隐藏按钮只改善体验，后端鉴权仍是边界。旧课程入口保留；生产部署、压力/长期与全库迁移不属M3验收。

### M3首轮复审：恢复与设备范围

缓存历史允许先显示，当前run的恢复须协调本次目录与历史刷新。新的active_run_id或末页运行身份不能被旧完成快照锁住；异步读取以会话epoch和请求代次胜出，目标不变时不重开流。创建运行同时更新本会话目录/历史，避免旧指针盖住新轮。未读末页且无活动指针时不能据首历史页允许发送。

目录选择保存设备描述及其用户/kb身份。问答首100项未含所选ID时，以已有型号做一次授权搜索（最多100条）并精确匹配ID，成功才补充可见option/提交。无描述、搜索不含该ID、错误或等待均明确禁发，不无限加载目录、不静默清ID；用户可主动清空/重新从目录选择。描述不是授权事实，不能单靠旧描述跳过核对。退出/401/切范围清ID和描述；后端仍独立校验权限。


## M4评测接续约定（未验收）

2026-10-27 M6显式后续执行补充：正式M6 job以`client_request_id:experiment_id:attempt`传递来源执行键。已完成Run仍复用；明确后续执行面对已收敛`interrupted` Run时，以原检查点身份、旧Run ID及来源执行键派生新的幂等请求，不覆盖旧Run、不清token/lease、不将未知/不可重试失败改为retryable。未给执行键、旧Run仍活动或非retryable失败时不自动新建。代码变化必须另存配置版本并保留原冻结版本；若继承成功结果，必须另存逐题来源/内容hash/旧Run映射，明确不是同代码重新生成的完整实验，旧失败及费用未知保留。

JSONL逐题固定id/group/split、问题/产品/历史、期望行为、必需证据组及替代原文页/资产。辅助草稿、用户委托的独立助手原件审核、真实人工三种身份分开。新增annotation.method=independent_assistant_review；reviewed必须有reviewer及review的artifact/文档sha256/40位commit/independent_source_audit/subject_sha256。subject绑定不含annotation的原始对象规范JSON指纹，改内容后不能继承旧已审；修订草稿可关联旧review但不能宣称已审。schema校验引用形状/内容绑定，实际来源文件与Git提交字节由交付检查复核，不假称认证身份。human_reviewed只记真实人工。support-v1-r2保留原35/15及稳定ID，43题原内容助手已审、7题修订草稿，真实人工0；原版字节不变。澄清题允许空证据，来源组召回null，不强迫引用某型号。用户不必再逐题核50题，修订先定向回交；本轮不执行基线或heldout。运行器不依赖M6，输出尝试日志/结果/参数manifest，按相同配置恢复；heldout需最终阶段与精确策略列表、题集/开发报告hash。真实适配器只传输入字段，标准答案不进上下文；范围限定m1_test_m4数据库/集合和m4-test归属/对象前缀，以冻结原件与活动修订拒绝串库。正式工作台基线为QueryRunner/V2Index，旧图保留兼容。尚未建立实际baseline.yaml和三资料语料，不把单元注入当真实基线。见[evaluation手册](../evaluation/labeling-guide.md)。

## M4供应商能力与失败传播

`app/infrastructure/providers/policy.py`提供ProviderPolicy.load/capabilities/classify/invoke_json；clients.py接文本invoke/stream、视觉摘要、本机推理边界。`PROVIDER_POLICIES_ENABLED=false`默认保留旧SDK请求参数，显式启用才加载对应策略；不因可选工具或视觉缺配置阻断文本问答。能力描述与真实探针分离，配置存在不标verified。JSON同步对象有限格式重试，JSON流拒绝；部分文本流失败不重新打开流，完整外层失败/无助手成功消息。

问答error保留code/stage并可新增retryable布尔；上游超时/连接/429/5xx可重试，鉴权/模型/格式/未知不统一改可重试。只传播安全码，不回显供应商正文/地址。旧APIError原因链与撤权安全逻辑优先保留。导入既有错误码与许可/维护权限/版本门禁不弱化，ProviderFailure可沿现有分类入口传播。配置见[说明](../CONFIGURATION.md)，本机timeout只在同步推理返回边界检测，不承诺抢占CUDA。


### M4-01 独立真实基线冻结（2026-10-24）

题集七题总控定向复核已通过，外部接受结论绑定当前subject及冻结版hash，累计50题来源审核、真实人工0。冻结JSONL/manifest不回写review计数。真实baseline-r2配置已建立，仅dev35题运行；heldout15题不执行。新增corpus.snapshot冻结三资料完整切片payload与dense/learned sparse向量hash、原件字节、图片归属/对象字节/摘要及缓存identity/来源与kb产品。RealQueryExecutor默认入口必须完整快照与dataset_acceptance文件hash；每题在创建/恢复run前重新只读校验，变化即拒绝，不以原件/活动指针相同放行。runtime_versions.code包含app/evaluation实现，避免评分变更冒充同版本。

corpus.asset_equivalences仅接受原件目视核对、两端图片hash与物理页绑定的精确对应，并核对比对证据hash。指标可据此匹配标准裁图，不修改实际引用hash，也不将同页邻图视为命中。allowed_evidence_group_recall是辅助来源覆盖，human_answer_correctness仍null；行为为协议/证据保守判定，不是答案质量分。配置文件字节hash与规范JSON config_sha256分别记录。模型/依赖/课程数据不升级，历史摘要模型/prompt未知明确保留；新解析和视觉供应商调用0，文本调用待真实账本核对。基线执行期间不改app源码或冻结配置，版本变更另建实验。


### M4-02 候选与阶段溯源

RetrievalHit以document_id/revision_id/chunk_uid组成身份，保存原text/metadata与独立StageScore(stage/rank/score/score_kind/query_id)。dense和learned_sparse为真实IP分路，weighted_fusion为Milvus加权分；原策略不称RRF/BM25，未知分数null且backend_unspecified。QueryPlan保留原问题/实际检索输入/产品/修订；EvidencePack校验候选、重排和实际上下文子集及原文/来源不变。重排不得新增或重复候选，不同修订的旧同名ID不得融合。

V2Index.search新增trace=True（默认）补同向量/同范围分路排名，多2次只读RPC；trace=False返回原融合响应，不改原融合/候选量。正式QueryRunner在持久run内部保存query_plan/retrieval_trace及selected标记；公开snapshot字段和citation.selected事件保持原接口，不暴露调试正文。实际citation只来自prompt_used_docs，未进上下文的图片不纳入引用。旧图适配无损保留原元数据/RRF/重排分；错误/取消/撤权继续通过原run协议收敛。


### M4-03 主体与查询计划

目录按NFKC/大小写/分隔符规范化的完整标准名/别名精确匹配，数字品牌不当单一设备，近/未知型号（含显式纯数字及全角）只给待确认候选。可选本机目录向量最多50项/前三候选，精确命中不编码，向量分不当确认概率；不可用仍澄清，超过50要求UI目录先选。错误码、协议编号和环境版本不当设备。用户确认后按同run/版本门禁恢复，不再解析原未知名强迫重复确认。

M6-08 R001-1补充：不能仅凭基础型号命中和字母后缀确认变体。完整目录别名或受控来源等价记录才可确认；当前仅登记 H3C LA2608 对 LA2608-GM/GU 的完整关系，原件SHA256/物理页/节号/引文随源码登记，不推导其他后缀。记录须匹配完整标准名及非空品牌；不适用于其他品牌。斜线参与完整身份检查，ZZ/FAKE及GM/FAKE、GM/GU/FAKE、GM/GU2仍为未知，正式运行须awaiting_input且无模型生成、答案、引用或助手消息。显式型号扫描遵守同一规则，已确认接口语境的编号规则保持原边界。

QueryPlan增加rewritten_query/slots/scope_groups/candidates/unconfirmed_tokens/reason，route区分answer/clarify/compare/insufficient/general/series。原问题不变，指代改写只加本目录已确认设备，槽位来自用户原文，不信助手猜测。比较每个产品独立过滤取证、共用权限与修订快照；后续证据缺失/预算仍须M4-06/07约束。内部requested_product_ids保留请求显式选择；旧run缺字段兼容旧输入快照。product_snapshot.context_route为可选新增字段，general表示继承清空边界；只从成功助手消息继承有效设备，取消/失败的用户快照不能覆盖，UI明确选择与指代冲突需澄清。不修改旧消息、ordinal或原始问题。


### M4-04 检索策略与dev网格

正式入口复用`app/retrieval/search.py`的RetrievalPolicy/retrieve、`rerank.py`的rank_hits及实际V2Index；融合复用已安装pymilvus的WeightedRanker/RRFRanker，不重复实现同名fusion.py以免与服务端分数失配。dense/sparse初召回、融合池、重排输入和上下文候选独立有界；默认20/20/20/20/10与原加权保持。独立参数在run内部retrieval_policy留存；公开API字段不变。各分路共用后端scoped_filter，重排只接受本次真正送入的候选身份，保留复合身份/阶段分数/原文来源。

`real_retrieval_grid`仅表示真实本机模型/索引检索实验，不表示答案生成或人工质量通过。固定grid只允许冻结dev；完整语料/接受结论/运行指纹在写报告前核验，使用独立输出和可恢复attempts，结束再核语料。原m3-baseline适配器显式使用RetrievalPolicy原默认，不受宿主实验环境覆盖；运行版本变化不能续写旧基线。保留课程数据和全部旧证据，不运行heldout调参。


### M4-06 有界证据扩展

V2Index.related_rows按后端owner/kb/document/revision/product范围与种子ordinal窗口/parent_uid定点读取，不递归或整章追加。ExpansionPolicy默认禁用；expanded在EvidencePack中显式区分，必须可溯源候选并保持正文/metadata；不能伪造rerank分。完整父块+种子组在字符预算内原子加入，缺父/超预算省略后半块；相邻证据同样不能绕前提。先按资料轮流给种子预算，再有界补邻居，按复合身份去重，不按相同文本删合法位置。run内部新增expansion_policy/expansion_excluded/evidence_groups用于复核，公开snapshot不增加底层调试正文。所有引用/图像仍来自实际prompt_used_docs，基线适配器显式禁扩展；默认策略须等真实dev实验后决定。

### M4-07 完整生成预算与引用门禁

AnswerBudget包含模型窗口/输出/安全余量/字符兜底/供应商输出字段；build_budgeted_prompt在完整模板渲染后计数，记录计数方式及舍弃数量，前提组原子选取。固定输入过大不调用模型。正式run内部prompt_budget、answer_support、missing_evidence_models、output_truncated用于复核，不扩展公开请求或快照调试字段。引用编号顺序严格按实际prompt_used_docs，不按原候选顺序；资产/来源须属于本次已授权资料修订。未知/残缺/非法编号在流式边界拒绝为answer_citation_invalid；原本已输出的有效部分可保留，不能写成功助手消息。代码反引号和图片alt数字不误当证据编号。

answer_support区分insufficient、partial_scope、partial_context、evidence_available、partial_output，evidence_available仅表示有入选证据而非答案正确。比较缺型号证据时提示资料不足；输出达到上限时中文部分回答说明与流/历史/final一致。来源不符citation_scope_invalid，固定输入超窗prompt_budget_exceeded均不可自动重试。引用门禁只保证本次编号/来源身份，不能替代语义事实正确性审查。

### M4-08 模型生命周期与缓存边界

复用实际app/infrastructure/model_host.py和原BGE/精排包装，不创建重复models/host.py。首次加载双重检查锁，失败不污染单例；公共推理锁及有界小批涵盖正式/兼容调用。generate_embeddings默认document，正式QueryRunner.encode显式query；HostEmbedder默认旧document协议，query发送input_type，需新版宿主。默认模型/设备/权重不变，安装SDK两接口实际同_encode。

ScopedEmbeddingCache仅存查询向量，cache_enabled默认false；范围必须完整绑定用户、权限、owner/kb、产品、活动资料/修订、模型和检索/查询策略，文本另入键。值深拷贝、异常不缓存、并发miss一次计算，TTL/LRU有界。退出递增用户代际且清现值，旧计算不能重新填新代；修订/权限变化换键，检索和run依旧授权。内部model_runtime记录实际小批/缓存配置，公开API不增加底层参数。单进程锁不宣称跨进程共享模型；真实1/2/4测量后再决定是否单独托管，不先增进程。

### M4-05 条件增强与受控降级

正式QueryRunner复用run_retrieval_graph/EnhancementPolicy，默认只跑必需本地检索；两个可选分支受已确认单型号/模糊症状和显式开关控制，参数/错误码跳过。HyDE只改派生search_queries，product_ids/revision_ids/scope_groups保持原授权事实，假设绝不转为证据。有限分解最多总3查询，仅拆用户症状。分支trace保留名称/原分数和实际资料身份，随后统一去重和重排一次。

分支内部只回结果，不写run；主路径错误由外层保存failed，可选empty/failed/timeout/busy保留本地结果。共享两个执行槽有界，晚到结果不能改已汇合包或终态；retrieval_branches/enhancement_policy/retrieval_merge_count为内部元数据，公开API不新增底层参数。timeout是结果接纳门禁，不是GPU硬抢占或供应商撤单保证。旧图不注册占位KG，真实LangGraph等待屏障汇合一次；兼容web须显式allow_web，未向正式产品暴露工具。

M4-04阶段召回汇总以冻结dev中所有要求证据的题为分母，错误澄清、失败或缺阶段结果计0；仅allowed_evidence为空题不适用。历史冻结输出不得回写修正，analyze_grid独立校验配置/完整题ID/attempts与results一致后生成新报告，拒绝未结束/污染/覆盖。来源组覆盖仍不等于答案正确率。

M4-03接口数字边界补充：仅有限已知接口前缀且紧随接口/端口语境时，Ethernet2/0等不当陌生型号；显式“型号”声明及未知AX近型号仍走确认，不能用端口规则补事实或绕产品授权。由dev失败发现、合成正式红/绿证明，原冻结结果不回写。

### M4-10 当前策略评价与真实阶段复用

`m4-configured`参数严格解析retrieval/expansion/enhancement/answer_budget/runtime并显式接入正式QueryRunner；m3-baseline拒绝策略覆盖。quality_grid只允许冻结dev；生产共享检索图/重排/扩展/完整预算，标准标签只在末端评分使用。阶段缓存按完整代码/模型/prompt版本、目标/完整语料及实际输入和策略绑定，key/value/原耗时共同校验，复用记录和原耗时不冒充新推理或生产时延。可选分支复用后，原生成及检索阶段耗时之和超期限仍拒绝该分支，保留本地同身份结果。计数包装仅数逻辑invoke/stream（含失败），各进程另存独立计数文件；精确SDK HTTP重试数和金额未知。源码变动后不续写旧实验；先dev选定策略及报告指纹，再最终heldout，不用heldout调参。


### M4-R1：跨范围与分支的有界候选选择

`retrieve`为每个范围/查询附加`candidate_pool`追踪：query_id保存规范JSON（scope、query序号），rank是后端该池的返回名次，score=null/score_kind=rank_only；图继续为可选分支加branch:hyde或branch:decomposition前缀。原dense/sparse/fusion分数与正文、修订、来源不改。

`rank_hits`统一调用`selection.select_candidates`：先按规范范围轮转，再按本地→HyDE→分解及查询序号轮转各池。相同复合身份保留所有池的追踪，但范围内仅由最先的规范池负责，避免重复前缀抢走新增证据名额；全局身份只选一次。单范围单查询保持后端原次序；不跨池比较原始分数、不增加默认20重排量。非空范围数超过重排上限时在调用重排前明确拒绝，不能默默丢范围或突破上限。范围空缺时名额可复用。入选机会不保证最终引用，模型相关性、上下文和完整prompt预算仍生效。

正式QueryRunner、RetrievalExecutor及QualityExecutor共用该选择函数。QualityExecutor新增内部`rerank_inputs`复合身份列表，包含缓存命中时本次实际提交的输入；不扩大公开API或暴露正文。阶段缓存随代码指纹隔离，本轮不可续写旧实验。参见ADR-049和[M4首轮总控要求](../development/reviews/M4-review.md)。


### M5-01 支持上下文聚合

GET/POST `/conversations/{cid}/support` 复用登录、CSRF和会话owner/kb授权。POST含expected_version、values（question/device/symptom/environment/error_code/tried）、confirmed、action(update/handoff/resolve/cancel)、可选本会话已完成run_id。单文档会话support.version CAS，独立context_version及历史快照，不改写消息ordinal、旧run或资料修订。状态awaiting_input/ready/handoff/resolved/cancelled；一次只问一个必要槽位，最多3轮补充，候选不当事实，缺证据/无进展转交。未输入环境/错误码保留未知；action=resolve仅用户自报解决，不代表系统验证设备。run引用快照不自动确认型号或实际操作，后续消费须重新授权精确修订。

计划最小调整：补充repository.py和API接线以满足等待持久化及进程重建验收，仍复用既有Mongo单文档能力，不引入checkpointer或新服务。M5-05再连接跨轮上下文和迟到run版本校验。

首轮复审补充：POST允许显式`clear_slots`字段列表，六槽位范围内去重，拒绝与values重复或同时绑定新run；只撤回当前已确认值，写history及记录时间，置value=null/confirmed=false/source=unknown并递增version/context_version。有旧引用则要求新证据；未来run不继承撤回事实，旧run/草稿快照不变。单纯清空输入本身不会撤回，前端提供“设为未知”明确操作并提示。


### M5-02 引用清单

POST `/conversations/{cid}/support/checklist`含expected_version/run_id，必须为本会话完成run，精确资料修订重新授权；整段操作引用摘录保留前提，最多20步骤，无动作证据转交。POST `/conversations/{cid}/support/operations/{oid}`含expected_version/status(not_tried/tried/ineffective)/note，记录服务器UTC时间和user_report来源，修正追加不覆盖。稳定操作身份按会话/资料/修订/切片/原文去重，后续run同证据不重置无效步骤。Vue组件纯文本展示，不执行设备动作。

清单变更前递归重新授权当前聚合中的全部嵌套历史、旧操作引用和工具输出，再授权新run引用；任一修订撤权则拒绝整次请求，version与operations不变。新回答权限不代表旧资料仍可读。


### M5-03 草稿确认

POST /cases接受run_id/expected_support_version，本会话完成run生成幂等draft，字段未知显式未知，快照含run、支持上下文、资料修订与用户自报；同run重复生成返回现存草稿，不覆盖编辑。GET /cases支持cursor/limit；GET/PATCH /cases/{case_id}、POST confirm检查owner/kb与精确引用权限，expected_version CAS。用户编辑追加edits来源与时间，确认后冻结，不允许静默覆盖；相同确认版本重复返回同结果。草稿创建不发送任何消息或设备操作。新增Vue处理记录页，问答完成后可显式进入。


### M5-04 有限只读工具

POST /conversations/{cid}/support/tools：expected_version、tool(lookup_product/read_evidence/search_manual)、arguments按注册工具schema，拒绝额外scope/表达式/路径。lookup仅当前kb产品，read仅当前支持引用，search使用已完成run产品快照/当前授权修订及原默认检索。输出是待核对内部资料，不自动成为事实或执行指令。预算持久预留先于执行：最多6调用、2扩展检索、累计30秒、12000 UTF8字节保守token计数；失败/重复/超预算转交。共享2槽，超时仅拒绝晚到结果，不声称GPU/数据库硬中断。崩溃留下running预留时禁止再派发，可显式结束/转交；不手工清账本重试。新版本CAS失败的晚到结果不写入。外网MCP未启用。


### M5-05 跨轮支持快照

新run在prepare保存input_support_version及有界support_snapshot（确认槽位/最新报告/操作来源，不复制全部工作流历史），preparing→会话领取同时CAS支持版本，间隙纠正返回409、不得生成用户消息。已领取run保持旧快照；纠正只进入未来run的产品计划/生成history，已报无效不重复。目录外纠正必须澄清，不借目录唯一项自动确认。取消/解决后不继承支持快照。关联新完成回答检查snapshot.context_version，历史无support_snapshot回答仅首次绑定；清单只允许本次绑定时槽位或同版本新run。更改已确认槽位要求未来问答取新证据，旧run/消息/已保存草稿快照不改写。

恢复补偿区分占用CAS：准备run若上下文改变且active_run_id不等于自身，保留版本门禁、不得写消息；若该指针已指向本run，表示领取CAS已成功，恢复以不可变旧support_snapshot补齐claimed和幂等用户消息。精确匹配自身占用，不能覆盖其他run。未占用的过期prepare即使版本冲突也继续执行pending超时，终止后不释放其他run。重复/并发恢复不重跑模型。

M5-05第三轮补充：会话归档后，领取/恢复按运行版本CAS置为`interrupted`并记录`conversation_archived`，精确释放自身占用；扫描继续处理其他会话，迟到旧run不能清理新run。支持聚合的设备撤回保存`subject_withdrawn=true`，未来run无显式型号时将该标记传给QueryPlan作为主体重置边界，禁止旧助手快照、旧会话选择和唯一目录项自动恢复；显式新型号仍走目录精确确认。

M5-05第四轮补充：归档worker启动、领取和恢复扫描必须通过同一`EventLedger.emit`以版本CAS原子保存终态、`seq`和outbox，并幂等投递`run.interrupted`；并发冲突只能在确认事件已持久后收敛。r2撤回快照可能缺少`subject_withdrawn`，消费者须识别设备槽位清空及`history.withdrawal.slots=device`，但不得把普通未填写设备误判为撤回。撤回后旧助手历史不参与主体冲突；本轮显式`product_ids`保留并按`explicit_selection`继续，未显式选择仍澄清。旧消息、run、ordinal和草稿不可改写。

M5-05第五轮补充：撤回判定按当前有效事实优先。当前`slots.device.value`非空且`confirmed=true`时，视为用户重新确认的现行主体，即使完整`history`含更早设备撤回也不得重置本轮；当前未知且有撤回操作者、`subject_withdrawn=true`或旧格式明确撤回历史时仍必须澄清。未确认候选不能解除边界，再次`clear_slots=['device']`必须重新触发主体澄清。兼容处理不删除历史、旧run、消息、草稿或ordinal。


### M5-07 反馈与导出

POST /feedback：run_id/citation_ids/category(model/evidence/missing_material/operation/image)/note/client_request_id，owner由登录身份授予；仅同run已授权引用，幂等不同内容409，状态pending_review，不自动生成资料或执行审核。GET /cases/{case_id}/export仅confirmed且全部精确资料修订重新授权，返回{filename,markdown,case_version}供浏览器本地下载。动态文本转义Markdown/HTML，不把用户文本变成图片/链接/脚本；导出含修订、来源、用户编辑、原操作建议和自报时间。无对外发送。

### M5-08 阶段边界补强

支持上下文、处理记录的读取及变更前递归收集嵌套历史/工具输出的document_id+revision_id，重新核对精确修订访问；撤权时拒绝整份回显，不以最新引用列表代替历史授权。所有现有步骤均由用户自报无效时进入handoff/all_steps_ineffective，不声称已解决。接线前断电等原文保持整段前提；清单是待人工核对建议。前端反馈只选择对应run引用，跨记录/身份切换丢弃旧下载结果；确认必须先保存编辑。M5-06未启用，不存在外网工具注册。本阶段真实验收范围仅新隔离账本单样例，不能替代生产规模/答案质量评价。

### M6 题集、评测指标与运行报告（执行中）

M6-01允许证据使用稳定`source_span`：原件SHA256、物理页、引文SHA256及可选图像资产SHA256；映射结果带当前`document_id/revision_id/chunk_uid`，未映射来源标为invalid，不计检索失败。标签修订须有版本、理由、前后指纹，修订后回到draft；标准资格只接受有身份的`independent_assistant_review/reviewed`或`human_reviewed/reviewed`，两种身份分别统计，draft/feedback不是真值。历史曝光、fresh dev、fresh heldout必须互斥穷尽；heldout不能复用历史来源或fresh-dev来源，策略冻结前不得运行。

M6-02需定义多证据组规则：外层`allowed_evidence`每组是一个必需目标，组内证据为正确替代项，同一组在排名前缀中最多计一次命中；无必需证据题的检索指标为`null`而非0。来源召回/排序不等于答案质量或人工正确率。实验manifest绑定数据、代码、模型、prompt、策略和seed；成本/供应商逻辑调用与精确HTTP请求/费用分开，未采集字段记null而非0。各指标公式与执行范围在对应任务记录中补齐。

M6-02实现使用`metric_schema_version=1`启用新报告契约；M4既有配置不带该字段时维持旧输出。每个M6运行清单包含`manifest_schema_version=1`、数据/划分/配置/策略hash、策略参数、代码/模型/prompt版本及seed，并对复现对象另存SHA256。seed是固定配置的复核元数据，不保证控制供应商SDK或模型内部所有随机性。真实检索候选按`candidates/reranked/context`持久化稳定候选身份和授权来源指纹，不重复保存候选正文；单位测试使用合成候选不代表真实检索验收。

对符合资格的已审题，Recall@k=前k候选命中的必需证据组数/必需组数；组内任一正确替代来源即可命中，同组只计一次。MRR取首个命中任意必需组的倒数排名。组级nDCG的gain为该候选首次命中的新证据组数、折扣为`log2(rank+1)`，再除以必需组数；一个候选可用多个来源满足多个组。草稿/反馈题和空`allowed_evidence`题的标准检索指标均为null；`human_answer_correctness`始终不由来源指标生成。报告按类别汇总成功/失败、缺失结果、失败阶段、检索均值及供应商调用/token/精确费用；字段不完整时不把缺失值当0。

## M6-04/05/08补修：答案图、聊天来源、步骤规则（2026-10-27）

本轮保留所有旧评测结果及账本，新增image_selection_version=1，asset_ids与answer_asset_ids分离；答案图仅由受控显式图片语法选出，不代替语义相关性评价。评测citation.image_usage明确answer/context，版本和来源持久化并参与题指纹。Vue仅默认加载新答案图，其他及历史图像通过展开溯源；历史0分保留，折叠不是得分变更。

聊天observations不可变、当前题级指纹绑定、同转录者source_message_id唯一且幂等；只能是assistant转录，不得写human声明/轮次、不进入校准。后续独立ReviewInput可引用observation_id，不自动复制语义分或声明。question-purpose-v1显式记录步骤适用性和理由，false须N/A，true不可N/A；追加未知不能改变适用性。混合版本不完整，跨版本/适用性变化门槛pending；legacy请求指纹及已冻结校准不回写。重新采用规则必须先形成新基线独立审阅和校准，再创建候选。详见[审阅协议](../evaluation/release-gates.md)。M6三项与全dev仍未验收，M7未授权。
