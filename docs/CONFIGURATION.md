# M7交付配置（2026-11-04）

`compose.delivery.yaml`为独立预览拓扑，不叠加旧compose，不复用旧容器名、卷、队列、数据库或模型账户。`scripts/operations/prepare_preview.py`自动生成私有随机配置，禁止将runtime.env提交或打印。所有宿主发布端口仅绑定127.0.0.1；不提供公网TLS/认证隔离的生产部署承诺。

| 配置 | 用途与默认 |
| --- | --- |
| M7_GENERATION_ENABLED | 普通旧部署默认true；本轮预览false，在创建Run前503拒绝新生成且关闭问答扫描。live不检查模型，ready把模型标为disabled。导入仍需要MODEL_HOST，不把缺项当成功。 |
| M7_PROJECT_NAME / M7_RUNTIME_ENV | 生成的独立Compose项目及服务端私有环境文件路径。 |
| M7_IMAGE_TAG | 候选镜像标签；最终以交付清单记录的image ID和源码SHA为准。 |
| M7_HTTP_PORT / M7_MONGO_PORT / M7_REDIS_PORT / M7_MINIO_PORT / M7_MILVUS_PORT | 回环发布端口，由脚本探测空闲端口；竞争时保留失败并以新目录重做，不杀占用者。 |
| MODEL_HOST_URL / MODEL_HOST_TOKEN | 轻量API与worker通过受控宿主复用已有BGE-M3/reranker；Windows使用host.docker.internal，Linux使用已防火墙限制的host-gateway。预览均为空，不加载或下载权重。 |
| M7_PREVIEW_USERNAME / M7_PREVIEW_PASSWORD | 仅随机合成预览账户；bootstrap登记，密码只在本机私有文件中。不会读private-identity。 |

新健康API `/health/live` 为进程存活；`/health/ready`分类Mongo、MinIO桶、Milvus集合、Redis、模型及可选工具。必要依赖不可用503，异常正文/URL不返回。模型探针只看已加载单例或宿主受token保护的ready；供应商仅配置核验，**不发推理，也不证明供应商可用或硬限**。`/api/v1/health`旧契约保留。OpenAPI及前端schema同步。

API镜像显式PROJECT_ROOT=/workspace，不依赖.env文件寻找提示模板。API镜像仅安装CPU轻量服务端锁文件，不装torch/FlagEmbedding/MinerU本地模型。PDF解析走已有受控MinerU接口；空配置拒绝。图片/文本/检索模型路径与凭据只由服务端消费。预览M6 catalog为空、评测队列无消费者，不派发旧168/旧43任务。宿主 `/rerank`复用原normalize=True实现，不引入新检索模型或排序方案。

模型宿主依赖另走独立短路径环境：共同依赖从uv.lock导出hash，Windows/Python3.12的官方CPU/cu128三件套分别固定在deploy/model-host/windows-cpu.lock与windows-cu128.lock。本轮两环境安装/导入及GPU设备可见性已验证，未加载权重或推理，不改变主CUDA；详见[安装路径](runbooks/dependencies.md)。

以下历史说明按原时点保留。

## 2026-11-04 · 完整候选补修完成自验，独立技术与新真实质量仍open

已针对本批实际错误补修对象/配件/示例及限定/时序提示、内部规则与产品证据隔离、输出发布前整体验证和澄清呈现快照。最终389离线/契约、101随机短隔离Mongo、62前端单元、6浏览器、typecheck/build通过；早一轮67相关Mongo与最终轮重叠，不累计。170保存输入/582保存标量回放保留完整上下文、连续引用和分组，166提示改变、两份048保持；最大输入估算14327/28416，不是新实际usage或临发现场核验。

此补修由总控实现自验；既有三连接算法未改，原独立技术结论只保持原范围，新差异尚无不同身份独立通过。原168真实stream、170结果、340判断、两blocked gate及proof存量0不变；原批已halt且调用/委派范围已执行，不重领槽、不改旧分。补修新增真实provider/本地推理/真实业务库访问/委派均0。提示修订不证明真实对象/完整性错误已解决；澄清快照不回填旧结果或评分。

下一整包须对具体补修定向独立复核，并准备新批独立身份/准入与现场完整输入，再依对应新授权完成真实候选→结算→两轮独立质量→正式gate/proof→05/08判定。M6仍5/7，04保持，05/08open；heldout/M7/旧43/基线不启动。没有新增环境变量或API，OpenAPI一致；来源关系回答现在检查后整体发布。详见[补修交付及限制](development/reviews/M6-candidate-quality-repair-r1.md)，以下历史按原时点保留。

## 2026-11-04 · 完整候选与340独立判断已完成，两gate阻断，M6保持5/7

两版各85真实结果/170 Run，168stream+2零调用澄清全部完成，实际输入809676/输出30791。新范围独立技术通过；两个全新Agent依次独立170判断，共340条正式记录/4seal/2attest。正式gate均blocked：22/21下降维度、各8题不完整，第二版2题wrong_object；两proof正式409拒绝且存量0。001/048两版双轮事实/引用均2，已成立边界保持。

两版completed恢复仅观察，新增stream0、账本hash不变；正式halt后cursor170/settled170/168stream、pending=null、unknown=[]，旧两个停止账户全等。05缺有效反馈proof，08缺有效完整候选质量和阶段退出；04保持，M6仍5/7。原低分/unknown/适用性分歧与critical不改；047候选与前端固定澄清文案的审核呈现限制单列，不据此放行。heldout/M7/旧43/基线不运行，human发布pending独立。下一项为证据驱动的完整质量修复；本批168授权已消费并封存，不能重试或重领。

详见[本批最终报告](development/reviews/M6-feedback-candidate-execution-r1.md)。以下历史按原时点保留，不作为当前未运行状态。

## 2026-11-03 · 已批准开发政策文件的Windows检出

assistant-development-v1仍按已批准原字节/hash验证。两份docs/evaluation/assistant-development-policy-{proposal,decision}-v1.md由.gitattributes固定text eol=lf；Windows core.autocrlf=true新检出保持批准LF，正文篡改仍拒绝。没有新环境变量或API。下一170成员候选为关闭准备包，不能将单题048合同/授权扩成85题准入；未授权派发的目录和限制见[完整执行指令](development/handoffs/M6-feedback-stage-execution-r1.md)。

以下历史按原时点保留。

本批独立170成功链已在补修前源码完整通过；随后整题后处理/发布出口4+6红测已补绿，最终源码309离线/152隔离Mongo通过，既定页面5项通过。最终r5已完整重冻，独立最终故障差异和输入重算已通过，95离线/77隔离Mongo/4正式故障绿；真实新调用/质量/proof仍0。

## 2026-11-03 · M6连接048新准入与完整输入包独立技术复核通过

用户本轮明确授权后，未参与实现的独立Agent完成17103bf之后07e92c2、53ecbaa及本次补修定向审查。发现validate_candidate整块忽略输出合同，协调重算后错误端点/历史来源hash仍准入；独立2反例失败，总控只正规化enabled/admission、要求anchor完整关闭模板后，由原审查者复测关闭。总控实现侧76定向通过单列，不作独立证据。

独立最终324离线/契约、96隔离Mongo、额外4磁盘故障检查及r3强化输入审计2项通过，各组有重叠不累计。审查者未改业务源码，结论为passed_with_specific_boundaries，无未关闭的实证技术问题；既有三算法独立关闭及hash保持。见[独立报告](development/reviews/M6-connection-048-independent-review-r1.md)和同名JSON（SHA256 `64a90dc5e26b5b4d0e72499bfe9f3c9a930a36d460620431b8ad623bd317fea5`）。

当前候选更新到`output/m6-connection-comparison-048-input-r3/`，catalog为`prepared/catalog/catalog.json`，独立执行目录`prepared/execution/`；完整582保存标量重冻、4资料/10文档/连续1–10、保守10340/28416及prompt字节保持。code=`c6fc212e2ea3659114a42614af22f5efae83e792f193abbffc6d533cc4d0ca38`；prompt SHA256=`9c1f2941f40f274aeba9d03453f5724c5ccea3135b7ab728f5c44af24319c2fe`。r1/r2保留，不能把旧配置代码身份冒充当前候选；种子仍为封存r8复放，未重新检索或核权重。

下一项是新048有界真实验证的明确调用授权；本轮授权仅独立复核，AUTHORIZED_GIT=None、默认合同关闭，未创建授权/正式实验/Run/清单或预留槽。未来临发仍核实际来源、旧blocked账户、runtime/wire并写独立持久输入锚。本轮provider/本地推理/真实资料新查询/真实业务读写/评分均0，累计56239/30516、预算上界84655/34612不变，HTTP/费用/reasoning明细null、硬限unknown。独立技术通过不等于真实质量或阶段验收；M6保持5/7、04已验收、05反馈复评proof及08候选质量/阶段证据open，43暂停、heldout65/M7不启动。以下历史按原时点保留。

## 2026-11-03 · M6连接048完整输入已冻结，清单与旧拒绝review补修完成自验

当前总控补修完整清单顶层重算（12反例）及旧账户拒绝review一致性（3反例），新授权消费者从完整标量重算精确输入。257离线/契约、72随机隔离Mongo和实际关闭catalog/完整输入审计通过，均为实现身份自验；新包不同身份独立技术审查仍open，旧三算法独立关闭保持且hash匹配。

实际4次指定修订标量只读取得四资料582成员；最终源码在全新input-r2目录完整重放，10文档连续引用1–10，保守输入10340/28416，无省略。full_scope_scalar_payloads_replayed与exact_production_prompt_frozen均true，prompt SHA256=`9c1f2941f40f274aeba9d03453f5724c5ccea3135b7ab728f5c44af24319c2fe`。种子为封存r8复放，不冒称重新检索/重排或新核权重；独立Run持久输入锚须未来调用前实际写入。

当前冻结候选在`output/m6-connection-comparison-048-input-r2/`，完整anchor、prompt字节及`prepared/catalog/catalog.json`已配置；旧catalog/证据不覆盖。AUTHORIZED_GIT=None、合同关闭；正式实验/Run/清单/槽/评分均0。新调用/推理/真实写入0、真实业务Mongo读取0；隔离合成Mongo另列，本轮真实资料读取仅上述4次标量查询。累计实际56239/30516，HTTP/费用null、硬限unknown保持。

下一项是未参与实现身份定向复核新profile及补修/输入消费者；未授权委派，不启动Agent。取得明确新单题调用授权后才可有界验证，临发仍核实际来源、旧blocked账户、runtime/wire和持久输入锚。没有新真实答案质量proof，M6保持5/7、04验收、05缺反馈复评proof、08缺候选质量/阶段证据；43暂停、heldout65/M7不启动。详见[本轮报告](development/reviews/M6-connection-048-input-freeze-r1.md)与同名机器摘要。以下历史按原时点保留。

## 2026-11-03 · 新连接048配置已由程序准备，无需用户填写路径

新模式专属合同、登记前验证、独立CAS账本及正式Run结算已实现；补修新合同思考输出观测遗漏。222离线/契约、72新及连接模式隔离Mongo、66旧风险隔离Mongo通过。方案指定目录的关闭catalog实际预检通过：完整150题85/65，仅选048，4资料582成员冻结映射保持；正式派发blocked_no_new_authorization。

这是当前实现总控自验，新风险/准入包未自签独立通过；上一包连接算法独立关闭保持。尚未实际全scope读取标量并冻结精确生产prompt，保存模型指纹不等于重核权重。无新调用授权、正式实验/Run/槽/评分；真实调用、本地推理、真实业务库读写0，累计56239/30516。M6仍5/7，04验收，05反馈复评proof与08有效候选质量/阶段证据open；43暂停、heldout/M7不启动。

下一项：对本包定向独立复核并落实生产输入冻结准备；未获新单题授权不执行048。详见[实现报告](development/reviews/M6-connection-048-admission-r1.md)，不勾选仍缺正式证据的阶段任务。历史保留。

已实际生成的catalog文件为`D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.worktrees/m6-source-bound-comparison/output/m6-connection-comparison-048-r1/catalog/catalog.json`，持久输出为同级`execution/`。config_id/version=`m6-connection-comparison-048-r1`/`connection-r1`。`scripts/verification/prepare_m6_connection_048.py`默认准备上述目录，已存在即拒绝，不重复运行覆盖。无新增环境变量，不自动替换服务目录；当前合同enabled=false/admission=null/AUTHORIZED_GIT=None。

## 2026-11-03 · 新连接模式技术通过但仍不可正式派发

connection_comparison_v1经用户授权的独立Agent完成具体技术审查及6组补修复测；新增完整来源语境结果和PDF text/table类型约束，无新环境变量或外部配置键，仍需显式模式和冻结来源。比较器/renderer新版本证明漂移拒绝，不自动升级旧Run。默认关闭、EvaluationService正式登记拒绝保持，不能用旧048风险合同绕过。

下一项为新模式专用风险/准入合同和catalog预检。执行端负责[方案](development/handoffs/M6-connection-comparison-048-proposal-r1.md)中已经给明的catalog/独立持久输出绝对路径，用户无需再填占位路径；本轮目录未创建、未登记或预留。真实调用授权仍缺，费用/HTTP未知保持。见[独立技术结论](development/reviews/M6-connection-comparison-independent-review-r1.md)，不等于正式质量/阶段验收。

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

`comparison_answer_v1`可作为冻结开发配置登记，但不能仅凭配置开关派发。内部专用`diagnostic_comparison_answer_048_v1`合同与CAS风险档案已实现自验；它固定support-v1-048、历史usage 53089/30412、单次输入/输出预留28416/4096和累计算术上限81505/34508。当前缺少新专属Git授权，因此catalog必须保持`output_contract=null`；即使手工加合同，正式service也会在预留slot前返回`422 comparison_admission_required`，而客户端/计划冻结入口同样拒绝。不要把旧source-relation合同改名复用，不得把合同注册误作调用授权；完整自然语言比较答案和真实质量仍未验证。

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
2026-11-01 assertion_binding r2仅改Run内部源载荷留存／proof恢复校验和评测投影，不新增环境变量、配置键、公开API或OpenAPI合同。实施自验108/16/89，独立复核待办；不改变默认关闭，不授权新048调用。见[补修报告](development/reviews/M6-assertion-binding-fix-r2.md)。


2026-11-03：内部evidence_attribution.comparison_answer.function_version新增comparison_answer_v2，可显式用于离线候选；enabled仍默认false、版本仍默认comparison_answer_v1。缺省和旧Run不升级。v2改进精确简称、客户端接入、完整scope条件与原文呈现；生成和恢复严格绑定策略版本。无新环境变量，公开OpenAPI未变。现048专用风险授权仅v1且已消费封存，本包不修改正式catalog或模型调用授权。

2026-11-03同包续修：v2以known_frozen_relations_v1从同一冻结目录补齐所有已识别关系；proof保留原selected_frames，并单独绑定supplemental_frames、rendered_frames和catalog_sha256。缺省v1不补入。恢复重算覆盖、答案和证明；不把程序补入伪称模型选择，不把离线候选当正式质量proof。

### 2026-11-03 · 比较答复v3（内部离线候选，未切默认）

既有内部键`parameters.evidence_attribution.comparison_answer.function_version`可显式设`comparison_answer_v3`。开启仍须enabled=true及冻结归属/source_relations；缺省enabled=false、版本v1不变，无新增环境变量，`.env.example`无需新增项。v3分离文档端口/介质/对端与现场状态，使用独立classifier/renderer proof版本，旧Run和v1/v2配置不升级。当前仅离线/合成验证，无v3专用真实风险合同；不得将它写入已消费r8配置、复用槽或新发048。完整比较质量仍未通过。

2026-11-03 v3接续：仅核明确本机端口主体后呈现documented_path；未识别/其他设备端口只保留原文。删除把程序未分类说成资料未说明的摘要。无配置键/环境变量变更、缺省v1/关闭保持；已保存本地v3候选漂移拒绝，不升级真实Run。穷举固定048目录全部2048选择都不足，当前v3不可作为完整回答候选，不在现已消费r8风险合同下启用。

2026-11-03 连接语义方案已审但未实现：connection_comparison_v1仅为预定行为名，当前配置不接受它；不新增环境变量，不修改.env.example。概述补齐形成的11项输入只是离线来源对照，不能绕过原context_limit=10注册正式运行。后续以新装配及输入身份在既有预算内保留必要来源，不升级旧Run或旧风险合同。详见[设计](superpowers/specs/2026-11-03-m6-connection-semantics-design.md)。


2026-11-03较早交接时：comparison_source_assembly_v1为内部纯函数版本，尚未注册connection_comparison_v1。此为历史时点说明；当前模式保持默认关闭，正式评测入口因缺独立风险授权而拒绝，不变更.env.example或增加环境变量。装配与四格回放是本机输入验证，不是正式Run或新调用授权。
## M6连接比较模式（内部默认关闭）

`connection_comparison_v1`是显式冻结`evidence_attribution.comparison_answer.function_version`，不是环境变量或用户可选开关。必须同时绑定冻结来源关系、完整payload映射及既有prompt预算；离线/开发自验之外没有新的正式评测风险合同。将其用于正式评测会在实验登记前以`comparison_admission_required`拒绝；不得通过复用旧048风险合同绕过。当前配置catalog不新增或启用该模式，没有新增环境变量。任何未来真实调用需独立审查新配置、请求身份和预算授权。


## 2026-11-03 · 连接比较调用前记录与验收证据

本次不新增环境变量，不变更.env.example，不切默认。connection_comparison_v1仍需内部显式冻结配置且正式新评测准入未登记。仅此模式在Run目标Mongo库新增comparison_generation_inputs内部集合，_id为run_id，保存connection_generation_input_v1身份及摘要，不复制来源正文；首次插入后只校验，不在恢复时补建。备份显式新模式Run时应一并保存此集合；记录缺失／漂移则拒绝复用，写入失败comparison_input_checkpoint_invalid且不调用模型。进程内_connection_input_guard不写库、不序列化。旧模式／旧Run不迁移或新增配置。

当前离线完整输入为双资料333成员明确投影，非原四资料582成员全scope；不能把回放输出直接作为正式catalog或真实质量proof。实际预算、验证、原rubric门槛纠正和后续范围见development/reviews/M6-connection-comparison-acceptance-evidence-r1.md及development/handoffs/M6-connection-comparison-acceptance-evidence-r1.md。无需用户找模型目录、查PDF或手工配置。


2026-11-03新连接模式终止补修：没有新环境变量，不改.env.example或默认开关。仅connection_comparison_v1要求本次调用有正常stop终止；缺失／异常／冲突或终止后正文在展示前拒绝，空用量帧允许。成功Run保存answer_finish_reason，缓存及首次恢复不接受缺失或漂移；新模式的完整输出身份包含该字段，旧版本不迁移。错误码comparison_termination_invalid；本模式没有已执行的真实Run，不手工补写历史状态。详见development/reviews/M6-connection-comparison-terminal-review-r1.md。

## 2026-11-03 · 连接048授权Git引用

固定docs/development/reviews/M6-connection-comparison-048-authorization-reference-r1.json保存GitEvidence(commit/path/sha256)。缺文件仍为None；文件须与HEAD内原字节相同且只指本批authorization-r1.json，再由evidence_bytes核不可变Git正文。该文件不在app指纹中，允许先冻结最终代码输入，再提交授权及引用，避免循环。没有新增环境变量或API；默认catalog继续关闭。引用接线由本轮总控实施自验，原独立审查范围不追改。

2026-11-03最终执行结果：本批已在供应商前失败并halt；引用仍保留历史授权，不能重用。修后准备目录output/m6-connection-comparison-048-input-r5/prepared/catalog/catalog.json默认关闭；完整anchor及精确prompt见同级上两层。新代码与旧授权输入不符将继续拒绝，不填写假授权或复用旧槽。引用文件由.gitattributes固定LF。

## 2026-11-03 · 048授权引用加载时点补充

授权引用在可选048 profile模块导入时读取并冻结到AUTHORIZED_GIT；load_authorization_reference会核HEAD原字节，但文件热改不会自动更新已加载常量，不能当作热撤销机制。部署/切换引用须重启相应执行进程；真正停止仍由固定批次halt与不可重领账本约束。默认服务启动不提前加载该可选profile。独立真实临时Git与新模块导入探针已覆盖该边界；旧r1已halt，本轮不借新引用重用。

## 2026-11-03 · 用户再次授权后的048 r2固定身份

用户明确要求完整修复闭环并允许调用模型。当前专属合同固定batch/ledger为m6-connection-comparison-048-r2，slot为该batch加-support-v1-048；仅接受authorization-r2.json和authorization-reference-r2.json，引用仍限定已提交原字节及LF。默认静态准备目录随当前batch取output/m6-connection-comparison-048-r2，关闭合同无授权不能派发。旧r1正文、引用、Run及halt原件保持，当前准入拒绝旧r1合同。没有新增环境变量、浏览器API、供应商或模型；预算和CAS生命周期保持。固定身份切换属总控实施自验，原独立报告按其源码范围保留。


2026-11-03 r2实际出口：本批已真实执行1stream并正式结算、来源review(true)、halt；恢复只观察相同Run，无第二stream。合同56239/30516是本批派发前历史值，实际累计现为59589/30583；不得把当前关闭/已halt的r2身份当新额度或新授权。原输入r6、Git引用和receipt保留。

## 2026-11-04 · 两版完整反馈候选专属合同

diagnostic_feedback_candidate_manifest_r1固定两版各85道dev、170题级槽、168个provider stream上限和2条047零调用澄清。使用独立diagnostic_feedback_candidate_accounts共享CAS集合及目标库feedback_candidate_generation_inputs输入身份集合；备份此显式新合同Run须保留两者及本机排他证据目录，不为旧Run迁移/补建记录。授权正文和M6-feedback-stage-authorization-reference-r1.json分提交，引用固定LF，模块导入时冻结；缺失仍关闭，不能当作热撤销。来源消费者核已提交且覆盖当前源码的不同实现身份技术报告。

新增dev_question_order只允许恰好覆盖全部dev且不能与question_ids并用，支持048优先而不缩小质量范围。生产清单重算完整标量、原题路由/产品/修订及168精确prompt；运行前仍核现场完整语料与runtime，调用前输入先持久。在途halt返回409，不宣称网络已停止；恢复只观察、不重发，未知在途保留pending/unknown。全部成功仅awaiting_quality_review，真实质量与正式proof独立判断。本包不新增环境变量、浏览器API或默认启用项，.env.example无新增配置。
## 2026-11-04 · M7恢复共享目标预留

`M7_RESTORE_CONTROL_DATABASE`是同一隔离Mongo/MinIO/Milvus绑定的共享恢复控制库，由prepare_preview固定为随机`m1_test_m4_rc_`身份。旧预览可从合法随机`M7_PROJECT_NAME`稳定派生；两者均缺失则在写目标前拒绝，不能使用源/目标数据库替代控制库。所有恢复进程共用该配置，不允许按目标另选；部分/失败/未知预留不释放、不设TTL。最终补修候选固定覆盖见`docs/development/releases/M7-delivery-r3.compose.json`，r1/r2文件及镜像仅保留历史。

受控重排客户端保持既有检索策略，不缩小合法候选范围；按宿主每批最多64对/256000字符分批，原顺序合并并逐批验证分数数量、数值类型和有限性。单对超协议限在任何请求前拒绝，不截断。各批共用一次重排调用的超时预算，未增加自动重试；这不是模型推理容量或质量证明。

## 2026-11-04 · 显式M7八槽内部模式（r1已停止）

普通预览保持 `M7_GENERATION_ENABLED=false` 且以下五项未配：`M7_DEMO_MANIFEST`（完整来源/8题/目标白名单）、`M7_DEMO_AUTHORIZATION`（实际用户授权正文及hash）、`M7_DEMO_EVIDENCE_DIR`（排他持久wire/原流/输入证据）、`M7_DEMO_LOCAL_LEDGER`（宿主SQLite累计账本）、`M7_DEMO_LOCAL_AUTHORIZATION`（绑定既有模型配置/账本路径及限量）。均只为服务端私有文件，不能用VITE_或镜像构建ARG传入；缺失/漂移拒绝，不打印内容。

v1固定qwen3.8-flash/n1/nonthinking/单一4096/stream+usage/SDK retries0、8槽及227328/32768；输入28416、请求上下文窗口32768。宿主64texts/8rank/512pair是授权限量，不是吞吐或质量证明；网关/付费输出硬限、精确HTTP和费用unknown沿报告记录。本批资料首失败后已halt，不能重填配置/换目录/账本复用。新提案拟收紧14/8/48需先另作版本化适配，当前代码不自动支持。精确候选启动与限制见[本包报告](development/reviews/M7-operational-closure-r1.md)。
