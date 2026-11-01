## 2026-11-01 · 总控独立关闭原句选择具体子项；三项缺陷及比较形态未通过

独立审查0f31c78，并接续核17d91ed执行端复核，业务源码未变。严格编号、调用前冻结映射、完整原段呈现及正常缓冲／证明的受审子项独立关闭；R1首次outcome前恢复未重绑冻结载荷、R2断流片段未持久保存、R3空证据Run完成而评测失败仍open。最终独立故障矩阵4通过／5失败，归三根因；原62／新28／新提交及OpenAPI35单元、38及60相关隔离集成、两库正常身份2项、空证据开关对照2项与1313回放断言有独立证据，组间不累计为质量分。

当前模式只能作为证据摘录，不能替代048完整比较；三处技术修复不会自动解除产品边界。下一包唯一目标为可完成比较且受来源约束的生成端方案，一次处置R1／R2／R3；真实推理预算0，不签新048执行方案、不恢复43、不跑heldout或M7。原条件性提案不自动生效，旧blocked／已消费槽／评分及既有关闭保持。

新增真实推理／业务库写入0，累计53089／30412按封存材料保留，reasoning／HTTP／费用null、硬限及付费上界unknown；无真实质量proof或现场全库重扫。M6保持5/7，04保持验收，05缺真实反馈复评proof，08缺有效新候选质量及阶段证据。配置键、API与默认未改，无新增环境变量。

[独立报告](development/reviews/M6-assertion-binding-independent-review-r1.md) · [脱敏摘要](development/reviews/M6-assertion-binding-independent-review-validation-r1.json) · [集中接续要求](development/handoffs/M6-assertion-binding-independent-followup-r1.md)。以下历史保留。

## 2026-11-01 · 原句选择执行端定向复核：两类缺口，未放行048

本轮未改业务实现；61单元通过，随机隔离集成11通过／4失败，失败集中为R1恢复证明未重绑冻结载荷、R2断流部分选择未持久化。1313保存输入断言及1项OpenAPI通过，仅证明程序和保存输入边界，不冒充总控独立关闭或整体技术通过。原完整摘录不等于完整比较；当前仅证据摘录视图有证据。

assertion_binding仍默认关闭，配置键／function_version无变化，无新增环境变量或API。完整策略沿配置／Run／checkpoint／link绑定；R1／R2的最终来源与失败材料保证尚不完整。新模式提案未实现／登记／授权，回放旧unknown合同和max_tokens不可派发；不改输出硬限与原结算／首停止协议。

新增真实推理／stream／真实库写入0，累计53089／30412，历史HTTP／费用null及付费上界unknown保持；43题暂停，不创建质量链记录。M6 5/7，04保持验收，05缺真实反馈复评proof，08缺有效新候选质量及阶段证据，M7未启动。唯一下一动作先补齐R1／R2并有限复核，不得用新调用替代修复或将相关摘录改判为完整回答。

[本包报告与集中矩阵](development/reviews/M6-assertion-binding-execution-review-r1.md) · [脱敏摘要](development/reviews/M6-assertion-binding-execution-review-validation-r1.json)。以下历史保留。

## 2026-11-01 · 生成端原句约束补修（实现自验，默认关闭）

总控按用户授权承担实现，新增内部assertion_binding_v1：严格编号选择、完整原段程序呈现、流式缓冲、证明入Run/outcome及恢复拒绝。旧默认/旧策略不升级；不按关键词启发式判语义。最终1427离线/契约、65隔离集成及54成员+25题/35单元回放通过；不证明新048质量。新增真实推理0，旧43暂停、blocked/已消费槽保持；M6仍5/7，04保持、05/08未验收，M7未启动。

新模式限制自由断言，代价是原文摘录未必完成比较。下一步仅独立定向核验与一个新身份048真实验证提案，本条不授权模型调用。完整策略沿既有归属身份与冻结来源核验；无新增环境变量，.env.example无需新键，公开OpenAPI不变。详见[报告及完整执行Prompt](development/reviews/M6-assertion-binding-fix-r1.md)。以下历史保留。

## M6已审来源关系048单次内部配置（2026-11-01）

默认关闭的output_contract.function_version=`diagnostic_source_relation_048_v1`只接受封存Git授权的单成员新批次。须enabled=true且显式布尔thinking=false、n1、unknown状态及精确manifest／输入／旧账前值；普通v2 unknown拒绝不变。仅锚配置的experiment_id、versions.code、output_contract、output_token_field四处可变。完整题集与固定max_completion_tokens4096／非思考profile不改，无新环境变量、公开API或全局默认，.env.example无需新增键。

本固定槽已经一次真实消费，来源拒绝后账户blocked，不能拿配置再派发；不是通用供应商能力声明或43题恢复授权。精确hash与实际6116／859结算见[执行报告](development/reviews/M6-source-relation-048-canary-execution-r1.md)。以下历史保留。

## M6角色边界补修与离线配置身份（2026-11-01）

现有source_relation_spans_v1只在内部显式启用；本次无新配置键、环境变量、API或默认变化。完整候选语法歧义回退unknown，原句／scope／引用保留，明确关系仍解析。582载荷policy与答题prompt版本不改，但源码canonical及两版完整离线配置必须独立冻结，旧输入、Run、检查点和已消费槽不能静默升级。

本轮草案在output/m6-source-relation-role-boundary-fix-20261101/replay-r1，仅为54／25保存输入零推理投影；普通输出合同unknown仍阻断，不是可派发048配置。安装SDK Mock保持已封存非思考profile，不能据此获得真实调用授权。未写真实配置／实验／Run，43题仍暂停；总控只需复核新角色差异与原失败矩阵。精确新旧hash与限制见[执行报告](development/reviews/M6-source-relation-role-boundary-fix-execution-r1.md)。以下历史保留。

## M6来源关系跨度索引：仅内部显式配置（2026-11-01）

默认关闭，旧配置不增加字段。新键`parameters.evidence_attribution.source_relations`结构为`{enabled: true, function_version: "source_relation_spans_v1", frozen_payloads: {chunk_uid: payload_sha256, ...}}`；这里是结构示意，成员必须从同一正式完整corpus.snapshot精确生成，不能手填示意hash。必须与外层归属scope／documents／corpus hash一致，不接受`reviewed=true`或自定义关系事实。省略enabled不会开启；启用但缺完整成员、同修订正文或元数据漂移即拒绝。

启用仅选择新模板并附原句跨度，不改旧模板、检索、输出预算、model或thinking设置；不会取得额外推理授权。无新环境变量、全局默认或API；`.env.example`仅追加说明。元信息若挤出旧策略证据或历史则422拒绝，不扩大字符／token预算。配置变更须新请求及检查点，不用旧Run或已消费槽恢复；新策略及全量来源hash通过原归属canonical贯穿正式恢复。

本包`output/m6-source-relation-evidence-fix-20261101/replay-r1/`仅是本机离线输入投影草案；原54成员历史输出合同仍unknown／阻断，不是可派发的新048配置。SDK Mock另外复用已封存最新非思考wire固定profile，只替换messages，不能当新授权、实际网关遵从或新答案效果。未写真实配置／实验／Run，43题继续暂停。

本配置实际诊断已在版1 048来源错误处封存：新增2 stream，17-b限定来源诊断通过、048拒绝，余43未执行。新账户blocked，两个槽已消费；不可用配置说明重新派发。两次未上报reasoning计数，保持null；网关能力unknown。见[本包报告](development/reviews/M6-nonthinking-diagnostic-execution-r1.md)，M6仍5/7。

## M6显式非思考有界诊断配置（2026-11-01）

内部`diagnostic_nonthinking_manifest_r1`默认关闭；启用必须消费0e61ada封存Git授权及45成员新manifest，`thinking`必填且只能为严格布尔false。专用客户端实际wire仅比旧成员增加`enable_thinking=false`，保留`max_completion_tokens=4096`、n1、stream及usage、SDK重试0和120秒超时；无新环境变量或全局默认变化，`.env.example`不新增变量。普通v2 unknown拒绝、旧单题槽和旧remaining合同保持。

新批次`m6-nonthinking-diagnostic-r1`以原版1控制库`diagnostic_nonthinking_accounts`共用唯一CAS账户；旧remaining账户和根halt只读全等核验，保持blocked。前值37541／28633由旧结算来源逐级hash绑定，只计一次；最多45新stream，先新版17-b，逐题合法结算及来源决定后再接44题。固定槽、唯一在途、预算及崩溃窗口复用已审账本核心，不返还失败额度。

模式观测在SDK归一化前扫描raw reasoning_content；非空内容或任一usage片正reasoning计数均阻断后续。省略reasoning明细保留null；未观测到thinking不证明网关硬关闭。请求4096、客户端超时和账户观测预算均非供应商费用硬上界，HTTP／费用及可见token不可观测为null；网关能力仍unknown。本包不产生正式质量候选、评分、校准、gate或反馈proof。

## M6剩余清单已触发持久停止（2026-11-01）

本批m6-remaining-diagnostic-r1在版1 17-b出现length／空答，4个成员槽已消费，唯一共享账户blocked。即使pending为null、usage合法且有settled，也不代表可继续或补额度；根halt不可删改，余44成员不派发。没有新环境变量／公开API／默认profile。后续输出策略仅交总控裁定，本包不改thinking、模型或4096请求。详见[实际执行报告](development/reviews/M6-remaining-diagnostic-execution-r1.md)。

## M6剩余清单限定准入（2026-11-01）

内部`parameters.answer_budget.output_contract`新增默认关闭的`diagnostic_remaining_manifest_r1`，仅消费e54043f封存的本包Git授权；`admission`含Git commit／path／SHA256、固定批次manifest SHA和`member_slot`。它不升级普通v2能力，也不改变已消费单题合同。无新环境变量、公开API或默认配置，`.env.example`无需新增必填项；普通v2的unknown拒绝不变。

固定批次`m6-remaining-diagnostic-r1`在授权原版1控制库的`diagnostic_remaining_accounts`共用一个CAS文档，两个原控制库、所有成员及进程均寻址同一账户。前值28747／22304只初始化一次；每成员固定磁盘planned／started／settled，调用前原子预留该成员、唯一在途及输入／输出预算，CAS后磁盘失败仍保留pending。不能换ledger、库、nonce、目录或清理槽来重领。

合法结算进入`awaiting_review`，执行方逐题保存来源诊断后才允许下一固定成员；坏usage、未知窗口、空答、length／截断或来源失败保持blocked。成功恢复走既有完整outcome和题级关联，不重发。047以正式澄清消费者记0生成，不借旧top3绕过目录。所有固定成员完整题集仍150题／dev85／heldout65，输入来自已审完整题集，初次冻结也不允许只保留同题号而换问题。

能力及实际付费输出上界仍unknown；4096是请求与观测约束，HTTP／费用不可观测为null，reasoning包含在output内。私有驱动每次只接一个成员，经EvaluationService／execute_job／默认RealQueryExecutor，精确缓存仅替代embedding／rank及封存检索响应读取口；未启动worker，不恢复旧批量job。实现自验不等于总控独立技术或M6质量验收，M6保持5/7。

## M6唯一单题诊断已消费（2026-11-01）

固定slot m6-05a-product-canary-r1现已started／settled，唯一版1新版05-a完成且限定诊断成功。账户open仅表示合法结算，不能作为新调用额度；同一固定槽只可依正式协议只读复用，不删除或手改slot／账户／lease。原封存profile、prompt、配置及源码身份未改，能力及付费上界unknown仍保持，无新公开API或环境变量。

实际新增input5165／含reasoning output1702，前值23582／20602，累计28747／22304；本地推理0。精确HTTP／费用null，不能用本机1个request／200 response hook充当端到端付费计量。完整dataset150／dev85保留，原48 job暂停。见[实际执行与退出边界](development/reviews/M6-single-product-canary-execution-r4.md)。下方各历史状态按原时点保留。

## M6当前运行环境边界（2026-11-01）

总控d41b3a4技术关闭保持。当前Mongo连接拒绝、Docker引擎管道不存在，唯一05-a修正版驱动未启动，磁盘槽无started／settled，数据库现场unknown不可读；不能将既有预检通过冒充当前现场可用。没有更改配置、来源身份、模型profile或新增环境变量。恢复服务后须先核同槽／账户／输入，再沿原授权执行唯一job；详见[实际环境失败记录](development/reviews/M6-single-product-canary-execution-r3.md)。

## M6维护后接续状态（2026-10-31）

单题风险准入、最终集成及精确消费者已由总控d41b3a4独立关闭；prepared-r2身份保持，实际配置仅供这一题诊断，不扩大授权。完整冻结dataset为150行，其中dev85；私有执行驱动须分别按完整文件核总数和dev数，不将dev数当question_count，不缩水题集或改历史登记。

本轮新驱动在创建实验前因该计数错误停止，修正版仅离线核验、未再次执行；无新实验／Run／账户预留，固定slot无started／settled。无新增环境变量或公开API，unknown能力／付费上界及原固定profile保持。见[执行报告r2](development/reviews/M6-single-product-canary-execution-r2.md)。下方原执行时点记录保留。

## M6显式单题风险准入（2026-10-31）

内部output_contract新增默认关闭的`diagnostic_single_product_risk_v1`，仅消费bcee539封存的版1新版05-a授权；普通`diagnostic_total_output_v2`仍拒绝unknown。风险允许与网关能力分别保存：status／semantics仍unknown、evidence为空，不认定硬限。仅本机固定槽m6-05a-product-canary-r1，控制／目标／完整题集／prompt／源码／预算／请求均绑定；无新公开API、环境变量或.env必填项，不改变默认配置。

请求必须n1、qwen3.8-flash、temperature0.1、extra_body.max_completion_tokens4096、默认thinking、stream＋usage、retry0／timeout120／无redirect。started未知不重发，已settled只读复用；开启或回切须新配置身份，enabled=false沿关闭路径。前置失败后的源码冻结只追加、不改首份计划；全部仍共享唯一started，不因换manifest、nonce、目录、账户或库重获额度。总预算与prior分别记录，实际付费输出上界unknown。

本轮只完成离线检查与保存输入Mock，用户要求Docker维护期间不启动；最终版集成和实时消费者预检仍缺，真实配置／实验未创建，产品调用0。见[执行报告](development/reviews/M6-single-product-canary-execution-r1.md)。

## M6行级出处与比较上下文隔离配置（2026-10-30）

`parameters.retrieval.comparison_context`／`RETRIEVAL_POLICY_JSON.comparison_context` 仅接受 `global`（默认）与 `scope_first_v1`。显式模式仅对 compare 的已重排证据，在原 `context_limit=10` 内先保留各非空授权产品范围的首条，再按实际重排顺序补满；不改变候选、分数、weighted、top-k、阈值或原题。缺少召回不补造证据；低分入选不等于相关性通过。QueryRunner 与 RetrievalExecutor 使用同一函数，完整策略进入现有配置身份，关闭应创建新配置 `global`，不改旧Run。来源前提允许此显式组合，其他weighted及预算约束保持。默认.env未改。

MinerU本地结构版本由3升4，chunker由5升6；正式导入的 pipeline_identity 已包含 parser.version 与 chunker VERSION。复用供应商原始缓存不代表复用旧处理修订。PDF HTML表格增加 `Block.row_source_refs`，独立匹配同表连续页的完整单元格，短版本/型号限定也必须存在。短文本、重复、OCR/图标差异不推定精确页码，以 `page=null` 和 `table_row_page_unresolved` 保留未知。切片重复表头时汇总表头和数据行的实际出处，不沿用整表起始页。未知不是引用已通过，隔离发布也不是工作台默认切换。

四文档最终隔离目标及未定位行请以本轮[执行报告](development/reviews/M6-page-recall-binding-r1.md)和脱敏摘要为准；无答案生成、正式评测候选、评分或默认切换。

# 配置核对与填写说明

## M6图片解析补修依赖（2026-10-27）

新增固定运行依赖markdown-it-py 4.0.0及其mdurl 0.1.2，用于与前端Markdown规则对齐，不新增环境变量，无需修改.env或.env.example。pyproject.toml/uv.lock与Linux worker requirements同步；现有环境安装前dry-run确认仅新增这两个纯Python包，原193个非根锁记录不变，不升级PyTorch/CUDA或模型。uv lock --check --offline已通过。现有常驻API需在维护窗口重启才加载新解析和门禁；本轮真实001仅只读复核，未重启其服务，不将只读检查说成新版API真实部署验证。

请编辑项目根目录的 `.env`。`.env.example` 仅提供无密钥模板，不能代替实际配置。系统中同名环境变量优先于 `.env`，这是原代码 `load_dotenv()` 的行为。

当前本机 `.env` 已由用户填写两个个人凭据，并通过真实 PDF 导入、带图引用问答、多轮追问及浏览器验证；核心链路无需继续补必填配置，见 [完整链路验收记录](E2E_VALIDATION.md)。下文“需填写”也适用于在新机器从模板重新配置的情况。MCP 联网服务仍未配置。

## 你当前选择的部署方式

当前先在 Windows 本机调试：Python/FastAPI 和两个 BGE 模型直接在本机运行，Milvus、MinIO、MongoDB 使用本机 Docker Compose；百炼及 MinerU 使用你本人的云端 API。后期再迁移到服务器。

本次已将 BGE-M3 与 reranker 下载到 `.env` 默认模型目录，并通过真实推理验证。当前 `.env` 已包含本机服务地址及自动生成的本地 MinIO 密码；本机调试先填写 `OPENAI_API_KEY` 和 `MINERU_API_TOKEN` 即可，联网检索另需配置 MCP 地址。修改 `.env` 后重启两个服务。

本机数据库地址保持 `MILVUS_URL=http://127.0.0.1:19530`、`MINIO_ENDPOINT=127.0.0.1:19000`、`MONGO_URL=mongodb://127.0.0.1:27017`。MinIO 账号、密码由 `.env` 同时提供给应用和 Compose，当前保持一致即可。

## 一次问答中，各配置分别做什么

导入文档时：**PDF → MinerU 解析 Markdown 和图片 → 视觉模型解释图示 → MinIO 保存文件与图片 → 文本模型识别产品主体 → BGE-M3 生成双路向量 → Milvus 保存索引**。

提问时：**MongoDB 读取历史 → 文本模型改写问题并识别产品 → BGE-M3 编码问题 → Milvus 检索，结合 HyDE 和可选 MCP 联网检索 → 本地 reranker 重排 → 文本模型基于证据流式回答 → MongoDB 保存会话**。

因此，文本/视觉大模型、PDF 解析器、嵌入模型、重排模型承担不同工作，不能使用同一个“最新版模型名称”替换所有配置。

## 模型与接口更新核对（2026-10-21）

| 项目 | 官方当前信息 | 本项目处理 |
| --- | --- | --- |
| 文本模型 | 官方选型页列出 `qwen3.8-flash`、`qwen3.7-plus`、`qwen3.8-max`；分别面向低成本、均衡和较强推理需求 | 模板将 `LLM_DEFAULT_MODEL` 更新为 `qwen3.8-flash`；本地 `.env` 仅替换仍为课程默认值的字段 |
| 视觉模型 | 官方视觉选型页同样列出上述多模态型号，支持图像理解 | 模板将 `VL_MODEL` 更新为 `qwen3.8-flash`；复杂图表可选 Plus/Max，不要求名称带 `vl` |
| 百炼基础地址 | 共享 DashScope 域名仍可用，官方建议生产使用业务空间专属域名 | 本地保留北京共享地址；有专属地址时按控制台实际值替换，同时匹配 API Key 地域与业务空间 |
| MinerU 精准解析 | 官方仍提供 `/api/v4/file-urls/batch` 和结果轮询接口，推荐 `model_version=vlm` | 保持当前基础地址及代码中的 `vlm`；`v4` 是接口版本，不表示解析模型已经过时 |
| MinerU 轻量 Agent API | 新增 `/api/v1/agent/parse/*`，文件限制、输出与调用流程不同 | 不是仅改基础地址就能切换的替代品，当前保留精准解析流程 |
| BGE-M3 与 BGE reranker | 本项目是已验证的本地模型链路，未宣称为最新模型 | 保留。切换其他嵌入模型需匹配稠密维度、稀疏表示和 Milvus Schema；更换后需重新生成索引 |

新型号已按官方页面确认，但尚未使用你的 Key 验证账号权限、可用地域及真实效果。模板建议不是“已完成 API 联调”。客户端按 provider 能力配置思考开关，部分结构化调用要求 JSON Object；后续应分别验证文本 JSON 输出、答案流式增量和图片输入。

`LLM_DEFAULT_MODEL` 同时影响多个文本节点。若要只提高最终回答模型、而让改写等节点保持低成本，需要后续拆分配置，当前不能单靠一个变量分别控制。

## 必须填写或确认

| 变量 | 填写方式 | 用途 / 说明 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 本人的阿里云百炼 API Key | 主体识别、查询改写、HyDE、最终回答及图片理解共用。不要使用原课程文件中的密钥。 |
| `OPENAI_BASE_URL` | 默认中国内地百炼兼容接口；账号区域不同需同步修改 | M0 按 LLM_PROVIDER 能力传参；百炼默认 `enable_thinking=false`，通用接口不带专属字段。 |
| `LLM_DEFAULT_MODEL` | 默认 `qwen3.8-flash`，需账号可调用 | 产品主体识别、查询改写、指代解析、HyDE 和最终回答共用的文本模型。 |
| `VL_MODEL` | 默认 `qwen3.8-flash`，需账号可调用 | 给文档中的图示生成文字摘要；应支持 `image_url` 输入，与 MinerU 整份 PDF 解析职责不同。 |
| `MINERU_API_TOKEN` | 本人的 MinerU API Token | PDF 通过云端解析；纯文本 Markdown 可跳过 MinerU。 |
| `MINERU_BASE_URL` | 默认 `https://mineru.net/api/v4` | 代码调用 `/file-urls/batch` 和 `/extract-results/batch/{batch_id}`。 |
| `MILVUS_URL` | 本地 `http://127.0.0.1:19530` | 向量数据库连接地址，保存主体与切片索引。原实现未接入 Milvus 鉴权 token 配置。 |
| `MINIO_ENDPOINT` | 本地 `127.0.0.1:19000` | 保存原文件和图片；**不带** `http://`，本机 19000 转发到容器 S3 API 9000，9001 为控制台。 |
| `MINIO_ACCESS_KEY` | 本地默认 `raglocal` | Compose 与 Python 应用读取同一份 `.env`，保持一致即可。 |
| `MINIO_SECRET_KEY` | 本地 `.env` 已生成随机密码 | 当前本机方案可保留；不要改成 `.env.example` 中的占位密码，也不需要创建 `.env.infra`。 |
| `MINIO_BUCKET_NAME` | 建议使用专用测试桶 `product-knowledge` | 原代码启动时会检查/建桶并设置匿名读取策略。账号需要相应权限，请勿指向已有敏感业务桶。 |
| `MONGO_URL` | 本地 `mongodb://127.0.0.1:27017` | 保存会话消息。后续有鉴权时可用 `mongodb://用户名:密码@服务器:27017/?authSource=admin`，凭据特殊字符需 URL 编码。 |
| `MONGO_DB_NAME` | 建议 `product_knowledge_rag` | 会自动使用 `chat_message` 集合并创建会话索引。 |
| `BGE_M3_PATH` | 本机 BGE-M3 模型目录 | 默认 `./models/bge-m3`；需要下载权重、配置、分词器等完整文件。原作者的 D 盘模型路径不存在。 |
| `BGE_RERANKER_LARGE` | 本机 BGE reranker 模型目录 | 默认 `./models/bge-reranker-large`；原作者对应目录也不存在。 |

## 可以保留模板默认值

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_DEFAULT_TEMPERATURE` | `0.1` | 原代码直接转为浮点数，不要留空。 |
| `CHUNKS_COLLECTION` | `product_knowledge_chunks` | 切片集合，首次导入自动创建。避免填写已有业务集合，重新导入会删除同主体的旧数据。 |
| `ITEM_NAME_COLLECTION` | `product_knowledge_items` | 主体集合，首次导入自动创建。 |
| `BGE_DEVICE` / `BGE_RERANKER_DEVICE` | `cpu` | 先用 CPU 验证；CUDA PyTorch 就绪后再切换 `cuda:0`。 |
| `BGE_FP16` / `BGE_RERANKER_FP16` | `0` | CPU 阶段关闭半精度。 |
| `MINIO_IMG_DIR` | `images` | 图片对象前缀。 |
| `MINIO_PDF_DIR` | `pdf_files` | 原文件对象前缀；原 `.env` 未填，但代码有默认值。 |
| `MINIO_SECURE` | `False` | 原客户端建立连接时硬编码 HTTP，当前阶段先使用 HTTP 端点；HTTPS 端点需要修正客户端后再联调。 |
| `LOG_*` | 见 `.env.example` | 日志输出和保留时间。 |

## MCP 联网搜索

`MCP_DASHSCOPE_BASE_URL` 是百炼 WebSearch MCP 的 **SSE 服务地址**，不是大模型 `OPENAI_BASE_URL`。需要在自己的百炼账号中开通对应服务，代码调用工具名为 `bailian_web_search`，共用 `OPENAI_API_KEY`。

它属于问答中的补充检索。未配置时不能验证联网搜索能力；原节点会捕获搜索异常继续后续流程，并未提供显式的启用开关。先验证本地知识链路后，再用真实服务地址验证 MCP。

当前实现是 Python 直接通过 `MCPServerSse` 连接工具服务，与官方文档中通过 Responses API 让模型调用 MCP 的方案不同。不要将 Responses API 地址或 Streamable HTTP 端点直接填入 SSE 配置。

原节点发送 `Authorization: <Key>`，没有 Bearer 前缀；官方 MCP 示例使用 `Authorization: Bearer <Key>`。这是后续鉴权联调需核实的兼容性问题，不能通过把 `.env` 中的 Key 加上 Bearer 来处理，因为同一个 Key 还用于大模型客户端。本轮仅记录问题，未修改业务调用代码或宣称 WebSearch 已验证。

## 原文件中出现但不需要照搬的配置

- `NEO4J_*`：Neo4j 工具文件存在，但主流程的 `node_query_kg` 只有进度占位，没有真实图谱查询，不需要部署 Neo4j。
- `ENTITY_NAME_COLLECTION`：配置类读取但当前主流程未实际使用，原 `.env` 本身缺此项，对运行主链路没有影响。
- `EMBEDDING_DIM`：当前建集合代码根据实际向量长度计算维度；BGE-M3 为 1024，不依赖该环境变量。
- `MINERU_MODEL_SOURCE`、`MODELSCOPE_OFFLINE`、`MODELSCOPE_CACHE`、`HF_HOME`：旧机器的下载/缓存配置，不是云端 MinerU API 的必需项。特别是不要照搬 `MODELSCOPE_OFFLINE=1` 阻止首次下载。
- `MD_ROOT_DIR`、`ITEM_NAME_DIAG`：主链路未读取。
- `BGE_M3`：配置类读取，但当前嵌入实现选择 `BGE_M3_PATH`，为空才回退 `BAAI/bge-m3`，并未使用这个变量选择模型。
- `PROJECT_ROOT`：可选的项目根目录覆盖项；正常从当前项目根目录启动时无需设置。

## 本地基础设施及后续服务器部署要求

当前使用 [Windows 本机 Docker 调试说明](WINDOWS_DOCKER.md)，服务器部署暂不处理。

1. 当前选择 Windows 本机 Python + Docker Desktop，连接地址用回环地址，无需 SSH 隧道。
2. Milvus 支持 `SPARSE_FLOAT_VECTOR` / `SPARSE_INVERTED_INDEX`；Compose 选用 2.6.10，与原 SDK 主次版本对齐。MinIO 改为固定官方源码构建，首次启动前需执行构建命令。
3. MinIO 使用独立测试桶；原代码会设置该桶匿名只读，浏览器配图也必须能访问其地址。
4. MongoDB 账号有读写目标数据库、创建索引的权限。
5. 如服务器 Milvus 必须鉴权，或 MinIO 仅提供 HTTPS，告知实际要求后再做对应的最小客户端适配。

## 官方参考

以下内容于 2026-10-21 直接读取官方页面核对，模型清单随服务更新；不据此推断账号权限或具体计费金额。

- [百炼模型总览](https://help.aliyun.com/zh/model-studio/models)
- [文本生成模型选择](https://help.aliyun.com/zh/model-studio/text-generation-model)
- [视觉模型选择](https://help.aliyun.com/zh/model-studio/vision-model)
- [百炼基础地址与地域](https://help.aliyun.com/zh/model-studio/base-url)
- [结构化 JSON 输出](https://help.aliyun.com/zh/model-studio/json-mode)
- [视觉理解与思考模式](https://help.aliyun.com/zh/model-studio/vision)
- [百炼接入 MCP](https://help.aliyun.com/zh/model-studio/mcp)
- [MinerU 官方 API 文档](https://mineru.net/apiManage/docs)


## M0 离线测试与环境保护（2026-10-22）

默认 `.venv/Scripts/python.exe -m pytest` 只收集 tests/unit、tests/contract；真实测试另用显式脚本。单元测试不读取真实 .env，禁止网络与真实客户端构造。`uv` 实际位于 `C:/Users/10426/.local/bin/uv.exe`。现有 CUDA torch 为 2.10.0+cu128，不直接全量 uv sync；仅安装锁定 pytest==8.4.2 及必要依赖。已验证原依赖锁版本不变。独立测试命名空间见 development/baseline.md。API 导入不会预加载查询图，首次请求编译；Mongo 首次调用才连接。


## M0 型号分数阈值

可选 `PRODUCT_MATCH_HIGH_SCORE` 默认 0.85（严格大于），`PRODUCT_MATCH_MIN_SCORE` 默认 0.6（大于等于）；根目录 .env 填写，重启生效。须满足 0 <= min <= high <= 1，不是概率。精确标准名在候选阈值以上优先；否则单一高分自动确认、多个高分返回候选、中分澄清、低分无匹配。默认只是延续已有分数基线，不代表经评测校准。


## M0 大模型参数与日志基线

`LLM_PROVIDER` 可选 auto（默认）、dashscope、openai_compatible。auto 仅匹配 dashscope.aliyuncs.com 或其子域的主机名，代理域名需显式指定 dashscope。`LLM_ENABLE_THINKING` 可选 true/false，默认 false；只有 dashscope 才传 enable_thinking，通用供应商不带此字段。根目录 .env 填写，修改后重启；未修改现有模型。LLM_DEFAULT_TEMPERATURE=0 保留，缺省/空值为 0.1。

答案日志记录 session、阶段、字符数和图片数量，不写完整 prompt、知识正文、图片链接；MinerU 结果签名 URL 不记日志。文件日志关闭 Loguru diagnose，避免异常展开局部变量。历史日志未清理；其他旧节点仍需后续按阶段治理，M0 的合成标记检查覆盖本次变更路径。


M0-09 实测 SDK 核对：FlagEmbedding 1.3.5 的重排设备参数是 devices，现已正确映射 BGE_RERANKER_DEVICE，配置 cpu 不会自动改选 GPU；没有变更模型或真实 .env。整图原生加载异常与续验方式见 M0-09 记录。

## M0 第2轮验收运行说明

本轮不新增配置或安装依赖；使用环境已有 Pillow/PyMuPDF 做图像解码和来源页渲染。图片验收运行时以 MINIO_SECURE、MINIO_ENDPOINT、MINIO_BUCKET_NAME 绑定准确origin/bucket，key/hash来自原复制清单；不会把前缀相同的任意站点当成允许对象。预期拓扑身份见 `evals/datasets/m0-image-expectation.json`。下载禁自动重定向；正文/final/MIME/hash/可解码全部满足才通过，真实HTTP尚待R3。

阶段回归可运行 `.venv/Scripts/python.exe scripts/verification/run_m0_checks.py --prefix <本轮新M0前缀>`，保存实际退出码、数量及输出哈希；已有前缀拒绝覆盖。复审工具必须显式传 `--spec docs/development/reviews/M0-r2-artifacts.json`，分别运行 build_m0_review_artifacts.py 与 check_m0_submission.py；不再接受隐式旧报告/73项默认。新提交使用 baseline-manifest-r2.json、M0-r2-diff.patch和M0-r2-file-inventory.json，首轮文件保留为历史。

resume_m0_live 的 --cpu-threads/--prewarm-reranker 仅为既有图片失败诊断路径，不等于正常冷启动配置。Docker恢复后仅复用原隔离小样和会话；正常冷启动必须另起默认配置进程，无脚本专有线程覆盖/预热。精确续验命令与当前阻塞见 development/records/M0-09.md。

## M0 第3轮真实验收与审查运行说明

M1-04新增MINERU_SEGMENT_MAX_PAGES（默认50）、MINERU_SEGMENT_MAX_BYTES（默认100000000）、MINERU_POLL_TIMEOUT（默认600秒），填写根目录.env可调整供应商限制。按字节继续二分，单页超限报错；超时沿原batch恢复，供应商明确失败的下次调用可新批次，旧批次ID保留。allow_native_fallback默认false，仅由调用方显式开启，质量标记随结果传播，其缓存与严格模式隔离。M1_LIVE_PROVIDER=1仅在显式live_provider测试时启用付费调用，默认留空；只上传测试新建小样，不自动选择课程资料。输出/cache保持本地，不打印签名URL。

M1真实集成测试显式设置M1_TEST_DB为m1_test_开头独立库，测试读取根目录.env的MONGO_URL，缺独立库报错不跳过。默认单元/契约测试仍隔离网络；integration标记本身不开放网络，测试不删除库/集合。示例：`$env:M1_TEST_DB='m1_test_20261023_repository'` 后执行指定integration文件。测试变量不应填原业务库；M1_TEST_DB默认留空不影响应用。

M1-11真实新资料贯通测试`tests/integration/test_ingestion_live.py -m live_provider`另需M1_LIVE_PROVIDER=1、OPENAI_API_KEY/OPENAI_BASE_URL/VL_MODEL及MINERU_*。沿用现有配置不升级模型，仅合成图/新一页PDF；视觉原图使用data URL在内存传输，默认30rpm共享Mongo预算，摘要缓存重读不重复付费。测试明确匹配百炼provider时传enable_thinking=false，通用兼容接口不传。非付费阶段回归用`-m 'not live_provider'`；全量集成BGE_M3_PATH必须是已有本地目录，禁止自动下载。单个v2集合应绑定同一Mongo注册表数据库，以便唯一chunk身份预留覆盖所有写入。

2026-10-23用户恢复已有Docker后，原图片题续验及正常配置新进程冷启动已自验完成，105项单元/契约和3项既有回归通过。上节“真实HTTP尚待R3”是第2轮时点，当前见 `development/reviews/M0-submission-r3.md`。本轮没有新增环境变量、改写.env或安装/升级依赖，因此.env.example无新增项。

共享图片验收仅兼容历史image/jpg→image/jpeg别名，继续以准确hash和实际JPEG格式解码验证，PNG伪装不能通过；既有对象元数据、桶访问策略不变。`recheck_m0_images.py --source <原真实报告> --output <新路径>`只读原隔离Mongo响应，以正文hash唯一匹配和原final证据核对，再真实HTTP获取准确对象；不调用模型，不写历史，旧图调用退出1与复核退出0分别保留。`verify_m0_cold_start.py --source <原真实报告> --output <新路径>`必须以新Python进程运行，读取根目录.env中的正常模型/设备配置，仅覆盖隔离集合/库、关闭日志和禁止模型下载；不设置线程或预热。该脚本会进行真实模型/云服务调用，并在原隔离Mongo库新会话新增两条消息，不作为离线测试运行。

精确实测命令、退出码及设备见 `development/records/M0-09.md`。r3审查文件生成/检查分别运行 `.venv/Scripts/python.exe scripts/verification/build_m0_review_artifacts.py --spec docs/development/reviews/M0-r3-artifacts.json` 与同参数的 `check_m0_submission.py`。选用本轮105/3实测摘要、真实图片复核和正常冷启动报告，生成独立baseline-manifest-r3.json/M0-r3-diff.patch/M0-r3-file-inventory.json，不覆盖原或r2文件。脚本输出存在时不要重跑真实问答覆盖；需要重验应选新输出名并保留历史。

## M2统一API入口

使用`.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。启动阶段读取根目录.env，必填MONGO_URL与M2_DB_NAME（独立新账本库，不默认沿用旧课程库）；缺配置只报告变量名。API_ALLOWED_ORIGINS默认http://localhost:8000，逗号分隔明确来源、不允许通配符；API_COOKIE_SECURE默认true，只有本机HTTP调试显式false。当前健康检查/api/v1/health，资源在lifespan创建/关闭，import不连接服务或加载模型。旧query_service/file_import_service独立入口保留，不挂载到新API，不承诺旧无鉴权接口有新鉴权保护。

## M2账号管理与会话

单组织角色viewer/maintainer/admin，账号创建不暴露HTTP注册口。配置M2_DB_NAME后运行`.venv/Scripts/python.exe scripts/admin/create_user.py --username <用户名> --role admin --kb <授权kb_id>`，密码通过getpass两次输入，至少12字符，不放命令行/环境日志。该操作只写显式M2数据库。不可把原课程库默认当账号库。

登录POST /api/v1/auth/login必须携带允许的Origin，成功设置support_session（HttpOnly/SameSite=Strict，Path=/api/v1，默认Secure）；返回CSRF令牌，后续写请求携带Origin及X-CSRF-Token。GET /me可恢复身份和CSRF；POST /auth/logout撤销服务端会话。会话8小时，Mongo只存令牌SHA256且显式检查过期/撤销，TTL仅清理；账号禁用或移除kb立即按当前账号拒绝。固定5分钟窗口每来源最多10次登录，Mongo原子计数跨实例共享；不信任X-Forwarded-For，反向代理需单独配置可信代理。未提供公开密码重置/跨组织管理；维护操作需maintainer/admin，具体资源同时检查owner与kb。

## M2运行超时与恢复

RUN_LEASE_SECONDS默认60秒，执行器需定期续约；RUN_PENDING_SECONDS默认300秒，未领取运行超时中断；RUN_INPUT_WAIT_SECONDS默认86400秒，为等待型号确认的独立期限，不按执行心跳误判。均为正整数秒，填写根目录.env。新API生命周期每10秒核对超时和终态outbox/占用，多个进程通过版本CAS避免相互覆盖；重启可恢复候选、恢复点及取消意图。改动默认配置不写回历史消息/课程数据。

## M2知识目录与上传

M2_KNOWLEDGE_OWNER_ID指定当前单组织知识owner，用户的kb_ids仍限定读取范围；不默认接管旧资料owner。M2_OBJECT_BUCKET指定已存在桶，M2_OBJECT_PREFIX指定独立相对前缀（例如knowledge-api-v2/），新API不建桶/改策略；原件随机key，名称仅展示。M2_MILVUS_COLLECTION须为独立v2集合且不同于CHUNKS_COLLECTION，复用MILVUS_URL；上传不要求Milvus或模型在线，索引/发布时才连接。MINIO_ENDPOINT/MINIO_ACCESS_KEY/MINIO_SECRET_KEY及可选MINIO_SECURE沿用连接变量，但绝不打印值。缺配置仅相关端点503列变量名/用途/根目录.env，身份/会话等仍可用。UPLOAD_MAX_BYTES默认100000000字节，正整数；multipart元数据最多另64KiB，文件不支持路径名。

POST /products为维护者注册产品及显式kb关联；GET目录限当前组织+kb。POST /documents接受file、kb_id、client_request_id、product_ids（JSON列表）、purpose及可选document_id（同资料新修订），成功202返回document_id/revision_id/job_id；job pending/uploaded不表示已索引或发布。GET import-jobs返回阶段/attempt/可重试标记，retry需维护者/版本及错误可重试。修订发布/回滚复用M1真实产物验证和CAS；withdraw只撤活动指针，历史不删。

## M2受控原件和旧图映射

GET /assets/{asset_id}先复核组织资料/当前kb/修订再取对象并验hash，PDF支持单段Range的200/206/416；无签名URL外传。POST documents返回original_asset_id，引用通过GET /runs/{run_id}/citations/{citation_id}读取该run实际持久入选快照，外部图片不自动抓取，登记asset://转换受控路径。旧图片用`.venv/Scripts/python.exe scripts/admin/map_legacy_asset.py --manifest <本地JSON> --kb <授权知识库>`显式核验并映射；清单为document_id/revision_id/bucket/object_key/expected_sha256五个字段，不上传内部清单。脚本只读源图/完整解码并写映射，不改对象或策略。旧get_minio_client首次使用才创建客户端，不再自动建桶/公开桶；需预先准备原有桶，现有策略保持原状。禁止提前收紧课程图片桶。


## M2导入队列与宿主模型桥接

REDIS_URL指定队列与全worker共享限流，宿主默认回环6379；REDIS_PORT为compose映射，M2_QUEUE_NAME默认knowledge-import。JOB_LEASE_SECONDS默认60，JOB_HEARTBEAT_SECONDS默认10且须小于租约。VISION_REQUESTS_PER_MINUTE默认30，按模型跨worker原子预约。均填写根目录.env，不打印连接值。

MODEL_HOST_PORT默认8011，MODEL_HOST_URL为worker可达宿主地址，MODEL_HOST_TOKEN需自行生成且不可为空。宿主启动`.venv/Scripts/python.exe -m uvicorn app.infrastructure.model_host:app --host 0.0.0.0 --port 8011`，仅允许本机Docker访问，禁止公网。桥接复用现有CUDA模型，不自动下载；Linux worker不装PyTorch，不接收Windows模型路径。

先运行`docker compose --profile tasks up -d --no-deps redis`，再按compose构建/启动worker，宿主运行`.venv/Scripts/python.exe scripts/admin/dispatch_jobs.py`扫描任务。容器覆盖Redis/模型地址，存储连接须容器可达。M2_WORK_DIR默认/var/lib/knowledge-worker，挂worker-cache保留MinerU分段batch。禁止down -v或清缓存重试，详见[恢复手册](runbooks/worker-recovery.md)。


## M2持久问答运行

`.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`启动统一API，生命周期后台领取持久pending，与SSE订阅分离。默认使用现有Windows BGE/重排配置，MODEL_HOST_URL和MODEL_HOST_TOKEN同时存在时嵌入走同一受控桥接；重排仍使用已有宿主配置。不新增模型、不自动下载。多型号未选择时等待确认；超过50候选需先从目录选型号。缺配置按相关run失败阶段显示变量用途，不影响其他已配置端点。旧独立query_service继续作为兼容基线，新API不调用其无鉴权路由。
# M3 前端本机配置

`API_PROXY_TARGET`仅Vite开发代理使用，默认`http://127.0.0.1:8000`；通过进程环境设置，不进入浏览器bundle。后端`API_ALLOWED_ORIGINS`须明确加入`http://127.0.0.1:5173`，本机HTTP用`API_COOKIE_SECURE=false`，HTTPS保持true。前端不读取根.env、不向VITE_变量复制任何供应商密钥。依赖、启动和隔离浏览器验证见[前端说明](../frontend/README.md)。

## M6评测目录与独立预算

`M6_EVALUATION_CATALOG`为API和模型宿主共同读取的本机catalog JSON路径，目录项只接受相对该文件目录的受控文件。未填写时仅关闭评测登记/创建入口，不影响问答。`M6_EVALUATION_WORK_DIR`为模型宿主的独立持久输出根目录，实验按UUID建立子目录，保留manifest/attempts/results和崩溃现场；不得指向课程原件或解析缓存，不提交Git。

`M6_QUEUE_NAME`默认knowledge-evaluation，必须非空且与`M2_QUEUE_NAME`不同。专用Linux worker并发1/prefetch1，只接收实验ID，调用已有`MODEL_HOST_URL`和`MODEL_HOST_TOKEN`保护的宿主接口；不向Linux安装PyTorch或复制权重。API/宿主共享`M2_DB_NAME`与catalog，模型宿主仍使用当前`.venv`核验真实运行版本和完整语料。根`.env`不自动修改，新增变量均不进入前端bundle。

每所有者最多1个活动实验，宿主每进程最多1个评测；运行租约120秒、心跳10秒、派发扫描15秒、未领取消息60秒后可重投为当前固定协议。排队久不回收有效占用；未形成任务的预算预留60秒后才可回收，迟到插入不可领取。此预算隔离消费槽，不保证共享GPU零竞争。完整catalog示例、启动、取消/重试与恢复见[评测工作台手册](evaluation/workbench.md)。

## M4按能力供应商策略

在根目录.env配置`PROVIDER_POLICIES_ENABLED`，默认false保留原SDK参数，不提前改变原链路基线。true后按下表独立加载，仅所用能力缺配置/配置错误时失败；不因缺VL_MODEL或MCP工具阻断本地文本问答。SDK内部重试只处理其可重试网络/HTTP状态；流已开始后不重新打开流。修改后重启API/worker；不自动改写.env，不升级模型或依赖。

|变量前缀|TIMEOUT_SECONDS默认|MAX_RETRIES默认|JSON_SUPPORTED默认|JSON_RETRIES默认|
|---|---|---|---|---|
|PROVIDER_TEXT_|60|2|true|1|
|PROVIDER_VISION_|120|2|false|1|
|PROVIDER_EMBEDDING_|300|0|false|0|
|PROVIDER_RERANK_|300|0|false|0|

完整变量名由前缀加列名组成，均同步.env.example。秒数为有限正数且不超过3600；额外重试/JSON格式额外调用均0..3；布尔只接受true/false。本机嵌入/重排不生成JSON，禁止启用JSON或设置非零JSON重试。temperature沿用LLM_DEFAULT_TEMPERATURE，合法零值保留。视觉摘要是纯文本，不启用JSON；视觉JSON声明供能力描述，当前未提供JSON视觉调用口，不能称该能力已验证。JSON模式仅同步invoke返回合法对象，拒绝数组/null/NaN/代码围栏，格式错误有限重试；JSON流式明确拒绝，避免将未验证片段交给调用方。

文本/视觉SDKtimeout限制网络请求；MODEL_HOST桥接使用embedding超时和受限重试。本机同步嵌入/重排仅在调用返回边界检测超时，**不能强制中断CPU/CUDA推理**，返回超时后不再自动发起第二次推理；仍需M4-08资源实验决定进程隔离。默认0重试，显式本机重试只针对已分类可重试异常，未知GPU故障不盲重试。嵌入数量/有限向量、重排数量/有限分数错误拒绝为provider_invalid_response，不能写成功结果。

`Settings.provider_capabilities()`仅本机配置检查，不访问模型列表、不发付费探针；configured不等于verified，verified始终false。返回变量名、策略和布尔状态，不返回密钥/端点/本地模型路径。默认不开新公开HTTP端点。真实调用的错误模型、鉴权、限流、5xx、连接和超时明确分类；问答外层保存安全code/stage/retryable，仍保持failed且保留部分答案，不自动复活run。

公共错误码：upstream_timeout、upstream_connection_failed、provider_rate_limited、provider_unavailable可重试；provider_authentication_failed、provider_model_not_found、provider_invalid_request、provider_invalid_response、provider_capability_unsupported、provider_json_stream_unsupported与未知错误不可盲重试。任务重试仍需原维护权限、版本与新运行请求协议，不代表SDK或本地推理可无限重试。该策略实验需在M4冻结开发集验证后才决定是否启用默认；当前.env不变、付费调用0。


## M4检索阶段独立配置

`RETRIEVAL_POLICY_JSON`填写根目录.env，空值保持已接受的默认。修改后重启API；正式持久run内部保存实际策略，公开API请求不允许浏览器任意覆盖服务端资源上限。非法JSON、未知字段、非整数数量、非有限权重及越界组合拒绝，不输出输入值。

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| dense_limit / sparse_limit | 20 / 20 | dense与learned sparse各自初召回数，后者不是BM25 |
| fusion_limit | 20 | 融合池上限 |
| rerank_limit | 20 | 实际送入本机重排的数量 |
| context_limit | 10 | 重排后允许参与字符预算的数量，最终可更少 |
| fusion | weighted | weighted / rrf / dense / learned_sparse |
| dense_weight / sparse_weight | 0.5 / 0.5 | Milvus加权融合参数，各0..1，不能同时为0 |
| rrf_k | 60 | Milvus RRF参数，1..16384 |
| exclude_image_descriptions | false | 显式隔离派生图片摘要，在ANN/融合前对两路及追踪使用相同来源类型过滤；不删除摘要、不代替图片授权、不改变原正文引用图片。当前仅有25题隔离证据，不启用工作台默认。 |

数量均1..1000，context_limit≤rerank_limit≤fusion_limit，融合池不超过所用初召回总量。所有分路共用组织/知识库/产品/冻结修订过滤，不从客户端接收过滤表达式。weighted保留Milvus原分数，rrf明确标为倒数排名分，不混成重排相关度。默认不提高候选量；清空配置可回切原加权策略。 M4-R1起，fusion_limit为每范围/查询召回池的上限，rerank_limit为汇合后全局输入上限。选择按范围轮转，再按分支/查询轮转；共享证据保留多路追踪但规范池只供给一次，不直接比较异量纲分数。比较时非空范围数超过rerank_limit会明确拒绝执行，不能静默丢范围；默认20不变。清空策略配置不会撤销R1工程修复。

固定dev检索网格入口为`.venv/Scripts/python.exe -m app.evaluation.retrieval_grid --dataset evals/datasets/support-v1-r2.jsonl --manifest evals/datasets/support-v1-r2-manifest.json --config evals/configs/retrieval-grid.yaml --output output/evals/support-v1-r2-retrieval-grid`。本机配置绑定实际源码/权重/prompt、题集接受结论和完整独立语料，源码变化必须另建新配置/输出，不改旧报告。网格只允许dev，答案供应商调用0，图/页来源命中不等同答案正确。查询嵌入按问题在同一进程共享，独立保存原编码时间；汇报检索/重排时间及含共享编码的估算时间，冷加载单列，非隔离性能结论。只读客户端不create_index或写run/消息；退出前再核完整语料。输出原始问题/检索正文留本机，不上传。


## M4证据扩展

`EVIDENCE_EXPANSION_JSON`在根目录.env可选，默认空/禁用，未确认dev收益前保持此值。可选enabled（严格布尔）、max_chars（1..12000，默认6000完整证据渲染字符）、max_added（0..20，默认4）、radius（0..2，默认1）、max_seeds（1..20，默认10）。修改后重启API；原基线评测显式禁用。非法值仅报变量名与用途，不打印JSON内容；不改实际.env。

启用后仅按同组织/kb/资料/修订/型号的明确父块与有限邻居读取，不递归整章。父块缺失/完整组越预算则省略后半块，避免丢前提；不同资料种子优先获得预算，随后才补可选邻居。元数据/原文/asset来源均保留；查询关系单独记expansion，不能称实际模型相关分。正式run内部保存expansion_policy/expansion_excluded/evidence_groups，公开API不新增任意范围参数。清空变量即可回切；字符预算沿用原兜底，最终token预算由M4-07接入，不把本项称完整token约束。

## M4完整提示词与输出预算

`ANSWER_BUDGET_JSON`填写根目录.env；空值使用context_window=32768、output_tokens=4096、reserve_tokens=256、max_chars=12000、output_token_field="max_tokens"。窗口256..2000000、输出1..262144、安全余量0..8192、字符0..12000，均严格整数，输出加余量须小于窗口。字段只允许max_tokens或max_completion_tokens；未知字段/非法JSON拒绝且不打印值。部署者须按所用供应商的真实模型窗口配置，默认值不代表已探测能力。修改后重启API，实际.env未改。

完整模板、型号、问题、历史和证据渲染后计数，再预留输出与协议余量。没有准确生成tokenizer时按每UTF-8字节1 token保守估计并记录utf8_bytes_upper_bound；该值不是供应商usage，安全余量用于消息封装。可内部注入实际token计数器，不新增浏览器参数。字符预算继续兜底，完整父子组不可拆，固定输入超过窗口在调用模型前失败prompt_budget_exceeded；无可用证据沿原正式入口返回资料不足，不强留首条。

输出上限经当前LangChain/OpenAI SDK的extra_body显式传送选定字段，同时保留原enable_thinking等供应商参数，不修改client字典；已用合成HTTP核对流/非流两字段，尚无新供应商真实调用。finish_reason=length/max_tokens时保留部分回答并在流/历史/final一致提示达到长度上限。引用白名单及asset/revision检查接正式QueryRunner；旧兼容节点共享预算/输出限制，但未宣称完成同等引用编号校验。

## M4本机模型生命周期与查询向量缓存

`MODEL_RUNTIME_JSON`填写根目录.env，默认空值：embedding_batch_size=4、rerank_batch_size=8、cache_enabled=false、cache_max_entries=128、cache_ttl_seconds=60。批量严格整数1..64、缓存项1..2048、TTL秒1..3600、开关严格布尔，禁止未知字段；非法配置只报变量用途。实际.env不改，不升级PyTorch/CUDA或权重。

API/旧节点/模型宿主使用进程内首次加载锁和公共推理锁；大批拆小批，批间释放推理锁，异常不返回半批成功。默认导入document、正式查询query；当前安装版BGEM3两接口共同调用_encode，分流不宣称质量提升。`warmup_models()`显式预热现有模型，不在import加载/下载；API与独立模型宿主仍各属不同进程，锁不承诺跨进程单份权重，是否独立托管由真实1/2/4资源实验决定。

MODEL_HOST桥接新增可选input_type=query/document，省略仍document兼容现有导入worker；新query客户端要求同步重启新版宿主，否则旧服务会422拒绝，不能静默冒称query成功。清空MODEL_HOST_URL/TOKEN仅可在明确本机实验进程中选择直连模型，不修改真实.env。多进程部署的版本一致性需另验，尚未部署。

查询缓存只保存向量、默认关闭，范围键绑定用户/当前kb权限及角色/组织/kb/产品/活动修订/模型配置指纹/检索与查询计划/文本。TTL+LRU有界，重复miss共享计算且值深拷贝；退出清用户值并递增代际，迟到计算不能回填新代。权限/产品/修订/问题变更均重算，始终先鉴权；不缓存答案、检索正文或生成上下文。模型/权重不是热替换资源，变更后重启API/宿主，不能在原路径替换权重却沿用已加载单例。

## M6显式隔离来源前提

没有环境变量开关，不改实际.env；API/普通QueryRunner默认关闭。仅受信内部执行器可显式传`source_prerequisites`，公开HTTP的RunInput仍拒绝该字段。正式评测配置位置为`parameters.source_prerequisites`，进入现有完整config/request/checkpoint指纹；本次仅完成接线与合成验证，不授予运行新正式评测或模型的许可。

缺省为`enabled=false,function_version="1",max_added=4,max_chars=6000,max_rows=1000,scope=null`。enabled须严格布尔，版本仅接受1，新增块0..4、总证据字符0..6000、装载行1..1000为严格整数，未知字段拒绝。启用须冻结scope的owner_id、kb_id、确切database/collection（均m1_test_隔离前缀）、document→revision映射（≤20且唯一）、product_ids（≤50且唯一）。本次固定weighted .5/.5、dense/sparse/fusion/rerank20和context10；旧可选邻接扩展不得同时启用，防止双重预算/分组混接。

只有InternalRunInput可携带规范化配置；Run创建前配置参与幂等身份，非缺省配置及其SHA存入新Run，不回填旧Run。缺省关闭继续原RunInput身份；旧缺省Run不能在启用状态下消费，配置/预算/范围不同报execution_config_conflict，不能用相同请求键绕过。配置变更须新请求/新检查点，不能继承不同配置的旧19完成记录。执行期核对数据库/索引名、知识归属、实际冻结修订和本题产品范围，在任何前提读取前逐资料/产品鉴权。

装载经V2Index.prerequisite_rows，只查本题种子所在doc/revision与本题产品，强制owner/kb过滤。每次query限剩余max_rows+1，检测到超限则拒绝而不截断关系空间；装载返回值再次校验owner/kb、修订/产品及source_refs。前提函数只补声明范围的PDF封面日期及表格最近对象正文，不改变源文或重排分数。最终groups传现有prompt预算，引用沿原资产/修订校验和图片使用协议；关系trace和排除原因保存在Run，不冒称新增模型相关分。

关闭回切：新内部配置显式关闭（或移除本项）并使用新配置/请求身份，回到原weighted种子/旧扩展路径，不查询前提、不切换catalog或删除索引/历史记录。保留旧scope的显式关闭配置仍有独立身份；不能将旧启用Run直接交给关闭消费者冒称完成。源码回切使用正常反向提交。真实答案质量及默认发布仍须既定前置，本节不是启用默认或新增真实调用的授权。

## M4条件检索增强

`RETRIEVAL_ENHANCEMENT_JSON`可选填写根目录.env，默认hyde_enabled=false、decomposition_enabled=false、timeout_seconds=8、max_queries=3、hyde_max_chars=2000、hyde_output_tokens=512。开关严格布尔；时间0.01..60秒有限数，查询数1..3、假设字符1..2000、输出token1..1024严格整数。未知字段/非法值拒绝且不打印内容。实际.env未改，未获dev质量支持前保持关闭。

仅已确认单型号的模糊故障/症状才允许增强，参数/错误码不触发；分解只拆用户现象并最多追加2个查询，不补未确认型号。HyDE沿现有文本客户端和输出字段配置，用作检索查询，不入证据或回答prompt。每次最多两条可选分支、进程共享两个执行槽，忙时跳过、不无限排队；空/失败/超时均记录降级，本地必需分支失败继续向外传播。超时忽略迟到结果并仅汇合一次，SDK另有网络timeout，但无法硬中止正在执行的同步CPU/CUDA或撤回已发出的供应商请求，不能把被忽略调用称未计费。

旧兼容LangGraph移除占位KG执行，用真正多起点屏障等三分支；默认HyDE关闭，旧web节点只在内部状态明确allow_web时调用。正式工作台无外网工具入口，不代表M5工具授权。清空增强配置回默认本地路径，源码和旧节点文件保留。


## M6显式主体词投影对照

`parameters.retrieval.query_projection`／`RETRIEVAL_POLICY_JSON.query_projection`只接受`original`（默认）或`scoped_subject_v1`。后者只对已确认answer/compare产品范围的检索文本，用“该设备”替换目录精确型号/别名，产品授权过滤、原题、生成及重排问题不变；配件名称、登记完整版本变体、代码/尖括号/多行输入及无法精确映射的Unicode坐标保留原查询。没有新查询分支，不改weighted .5/.5和20/20/20/20/10预算、不放宽阈值。默认环境和工作台不变，本轮不修改实际.env。

正式QueryRunner与无答案RetrievalExecutor均消费该版本配置；完整参数/源码/查询计划进入现有缓存与实验身份。来源前提允许该显式组合，其他weighted/预算约束保持；关闭用新配置回到original，不修改旧Run、缓存或索引。实际对照24/25必要摘录到达不等于答案正确率，048仍缺，不据此发布默认或生成正式候选。


## M6默认关闭的内部组合 source_branch_compare_v1

仅受信评测配置 `parameters.retrieval_combination` 与 `InternalRunInput` 接受此项，公开 `RunInput` 拒绝；没有环境变量，实际.env不改。缺少字段或规范缺省 `enabled=false` 维持旧请求指纹和原检索/上下文路径。非缺省关闭配置仍保留自己的身份，不能把已启用Run交给关闭消费者恢复。

启用必须显式绑定 `scope`（owner_id、kb_id、m1_test_数据库/集合、document→revision映射、唯一product_ids）、`corpus_snapshot_sha256`、`corpus_rows_sha256`、冻结 `terms` 和 `reviewed_sources`。版本固定 `function_version=source_branch_compare_v1`、`source_terms_version=source_network_terms_v1`、`fusion_version=branch_heads_v1`、`context_version=compare_branch_context_v1`，未知版本/字段拒绝。`reviewed_sources`绑定目标document/revision/chunk、单行载荷集合hash和封存消费proof文件hash；这表示消费既有独立审阅，不产生human声明。配置只由受信执行方授予，不能把任意hash当新审阅授权。

只允许同时启用相同scope的source_prerequisites、关闭扩展及增强；retrieval必须weighted .5/.5、20/20/20/20/10、exclude_image_descriptions=true、scoped_subject_v1、scope_first_v1。运行前比对实验target及corpus.snapshot，正式adapter沿现有全量语料快照复核原件/向量/资产。QueryRunner先核文档/产品授权、冻结revision snapshot、数据库/集合，再最多读取1000行并校验整批归属、正文/结构/出处hash，重新提取术语并匹配冻结目录；不新增或猜测术语。所有真实分路请求和分数沿正式V2Index，context只消费当次重排输出，组预算/图片授权不另造逻辑。

完整规范载荷/hash进入Run请求身份、evaluation_items、evaluation_execution_links和缓存策略身份；原题/历史/反馈来源保持。恢复同时核Run策略、原关联输入和检查点，不给旧Run/旧checkpoint回填。中断沿RunCommands.recover；显式continuation仍须原父实验来源和正式协议，不自行改state/lease/slot。缺缓存的本包回放直接失败，不调用后备模型。

关闭回切：使用新配置/请求身份移除或关闭retrieval_combination，恢复先前weighted及其原source_prerequisites配置；若全部回旧默认，再移除来源前提。新请求不读取组合术语，不执行分路保护；旧Run、catalog、修订、索引及证据保留。不通过删除数据或重用启用Run回切；源码回切正常反向提交。本次自验不授予默认切换、最终生成配置冻结或实际答案质量通过。

## M6默认关闭的证据归属 attributed_assertions_v1

受信评测参数 `parameters.evidence_attribution` 与 `InternalRunInput` 可显式配置；普通公开RunInput拒绝，QueryRunner默认关闭，没有新环境变量、不改.env。字段严格禁止未知项：enabled、function_version（仅attributed_assertions_v1）、scope、corpus_snapshot_sha256、documents（document_id／revision_id／original_sha256）、products（product_id→正式model）。启用须绑定完整scope／快照，与retrieval_combination一致；config核验语料及产品身份，执行再核原件修订和授权范围，缺失／漂移fail closed，不猜名称／页码。

启用消费 `prompts/answer_attributed_v1.prompt`，来源元信息开销计入原字符／token预算，不提高top-k或窗口。最终prompt连续编号与document／revision／chunk／原件hash／归属／物理页进入prompt_reference_map；页级citations列表不能据位置重编号。未知页或产品仍为unknown；context图片不变成答案已展示图片。

非缺省配置参与Run身份、execution link、题级检查点及恢复核验；已启用Run不能交关闭消费者，prompt映射变化也拒绝复用。关闭回切须新配置／新请求，移除或规范关闭本项回原prompt；旧记录、索引、默认修订不删不改。旧校准是否可比由正式合同核验，不从零推理回放得出质量通过。本包只完成自验，未冻结或执行新正式生成配置。见[补修报告](development/reviews/M6-candidate-evidence-quality-fix-r1.md)。
## M6受审对象与诊断输出能力（2026-10-31）

受审对象关系消费已独立关闭；输出合同v2为本轮执行方自验，待总控定向复核。两项都是受信内部配置，没有新增环境变量或公开API字段。缺省及回切均移除新字段／设为`null`，保留原配置、Run和语料；不因此放行产品调用或改变M6验收状态。

- `parameters.evidence_attribution.reviewed_subjects`：缺省`null`。显式启用`reviewed_table_subjects_v1`须使用`compile_binding()`准备的完整载荷；固定原件／缓存／冻结清单SHA、document／revision、表block／行坐标、真实chunk UID／完整载荷、corpus snapshot以及审阅／证明的Git commit、路径和Git blob SHA。Git blob SHA、工作树文件SHA（可能CRLF不同）和canonical proof payload SHA是三层身份，不互换。配置核验和运行授权逐一核验冻结成员，不能只填配件名或用最近标题／相同正文猜绑定。
- 表格具名主体附在`prompt_reference_map[].reviewed_subject`，同一标签在prompt中计入既有预算。文档产品与配件分开；`title_physical_page`／`table_physical_page`是受审表级证据，`page_scope=table_only_not_row_location`。旧行`page_status=unknown`仍未知，不更新切片、source_refs、向量或默认修订。
- `parameters.answer_budget.output_contract`：缺省`null`。诊断版本`diagnostic_total_output_v2`显式固定endpoint SHA、model、客户端包版本、limit字段、含reasoning总量语义、thinking／独立预算、单份生成`n=1`、适用Git证据、每请求总输出上限与累计输入／输出预算、历史usage来源及新ledger_id。原4096不得静默放大；`status=unknown`或证据不适用时在正式Run任何模型调用前拒绝。没有适用证据不得填`verified`；SDK Mock不能充作能力证明。
- 生效wire仅允许已绑定limit／thinking参数与`n=1`，拒绝typed非单份、所有诊断model_kwargs、default_query、两limit字段、未声明extra_body冲突或SDK自动重试；安装SDK最终payload也须符合单份ChatCompletions合同。有效参数SHA包含`n`与`usage_validation=raw_usage_v2`，随合同SHA进入Run、题级检查点、执行关联和恢复核验。能力证据需精确匹配`gateway_output_capability_evidence_v1`的适用身份（包括n）、来源类型及可证明的总输出范围；不自动换字段／模型／额度，不开放额外生成分支。旧显式v1不能原地补字段升级，须新身份；账本键保留旧命名空间以拒绝同ledger_id换合同重置额度。
- `diagnostic_output_accounts`只服务显式诊断合同。调用前CAS预留，调用后先结算再允许下一题；保留历史／新增usage、已知下界、实际逻辑调用和未知窗口。`logical_reservations`不是HTTP次数；在途、缺usage或中断的新增总量为`null`，已知下界另存`known_new_*`；超限、缺usage、未结算或剩余预算不足均阻断。重复结算只复用全等收据，不增加usage；身份变化拒绝。精确HTTP／费用始终未知则为`null`；`output_minus_reasoning`只是差值，不能标成已测可见token。
- 仅显式诊断创建保留usage的客户端，使用固定安装SDK解码口及非流JSON响应hook，在类型归一化前保存字段存在性、类型和值。非法／矛盾、累计计数倒退或遥测冲突不可被后续正常片擦除；缺失／null与非法分别记录。reasoning如存在须为非布尔非负整数且不超过含reasoning总output，不能重复相加。校验与reported总量沿生成节点→telemetry／Run→结算账本持久保存，非法总量不作为可信usage，后续派发阻断。普通客户端与缺省遥测不改变。

安全示例（合成身份，启用后仍因能力未知而阻断；不代表真实运行配置）：

```json
{
  "output_contract": {
    "enabled": true,
    "function_version": "diagnostic_total_output_v2",
    "n": 1,
    "status": "unknown",
    "endpoint_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "model": "synthetic",
    "client_versions": {"openai": "按实际安装版本固定", "langchain-openai": "按实际安装版本固定"},
    "limit_field": "max_tokens",
    "semantics": "unknown",
    "thinking": null,
    "reasoning_budget": null,
    "evidence": null,
    "per_request_total_output_tokens": 4096,
    "ledger_id": "synthetic-new-diagnostic",
    "max_total_output_tokens": 8192,
    "max_total_input_tokens": 32768
  }
}
```

实际准备差异、零推理结果及待裁定探测见[执行报告](development/reviews/M6-diagnostic-subject-usage-fix-r1.md)。不得把本节或草拟配置当成48个job恢复授权。

2026-10-31已执行唯一授权非产品探测：固定`qwen3.8-flash`／SDK1.1.11与2.28.0，`extra_body.max_completion_tokens=4096`、n=1、默认thinking、timeout120、重试0。观测input102／含reasoning总output4096／reasoning4096，finish=`length`，仅分类为`observed_limit_4096_at_fixed_profile`。这不是原产品`max_tokens`字段或网关全域硬限证明，不登记verified，不恢复48 job。固定授权槽、原子独占started、原流及未知费用本机封存；不得重复探测。见[本轮执行报告](development/reviews/M6-output-contract-boundaries-probe-r1.md)。
