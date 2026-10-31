# 执行Prompt：M6对象关系与输出能力有界修复 r1

你是本包执行修复Agent；总控独立验收由另一会话承担。仓库`D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag`，Windows／PowerShell，接续日期2026-10-31（Asia/Shanghai）。先读适用AGENTS、PROGRESS、REVIEW_STATUS、TODO、M6任务、contracts和GIT_WORKFLOW。

## 权威接续与目标

执行包`6541506734670c4b94cffe3cef364b146c4d26d9`已真实完成六题并停止；先只读核当前是否有更新，不回退提交。先读：

- `docs/development/reviews/M6-diagnostic-subject-usage-review-r1.md`及对应validation JSON。
- `docs/development/reviews/M6-diagnostic-subject-source-proof-r1.json`：两张表的总控来源证明，本轮独立审阅已经完成。
- `docs/development/reviews/M6-diagnostic-cache-completion-execution-r1.md`及validation JSON。
- 本机新总控证据`output/m6-diagnostic-subject-usage-review-20261031/`；执行证据`output/m6-diagnostic-cache-completion-20261031/`。

本包仅修复**对象／表格关系消费**与**输出能力及预算合同**两个边界。不再扩词、改融合、调重排或用新prompt碰运气；保留P2、p30、001、组合、047／source_checked和恢复的既有关闭结论。M6为5/7，04已验收，05／08未验收；M7不启动。

## 本包权限与停止边界

允许修改上述两边界必要的业务源码、合成测试、配置示例与契约／文档；不得把自己自验写成总控独立通过。默认关闭且旧路径等值，新增能力采用版本化内部配置，沿既存授权和身份机制，不新增公开端点来绕开正式入口。

**本包新增编码、重排、供应商请求、答案生成、模型能力探测、真实诊断job、正式质量写入均不允许。** 余48 job（46答案＋2澄清）继续暂停；不得将原52答案上限视为自动接续许可。不要重跑首次创建脚本。真实旧状态默认只读；无必要不访问真实库。故障写库用随机短`m1_test_m4_`前缀隔离夹具。

不开子Agent，不要求用户找原件／账号或评分。tmp保留，output／evals／原件／缓存／日志不上Git，不读private-identity或输出.env值。历史Run／评分／blocked／state／lease／slot／retryable和旧证据不改。使用全新output目录，旧脚本先审阅再复制适配，禁止原地覆盖。

## A．实现受审表格对象关系，避免重新解析／推理

总控已独立确认：G540原件p5的机身15号RJ45用于网线；p13的MateDock2五行表不含LAN；p13末标题MateDock3所续p14七行表含LAN及microSD。只在精确原件版本范围内成立，不扩展型号兼容性。

解析缓存block92为MateDock2普通text，94为其表；95是被上游标成footer的MateDock3标题，98为其表。当前parser仅按text_level建heading，行切片丢失具名对象。当前05-a prompt内[2]LAN、[3]MateDock2、[5]MateDock3分别出现，尚无关系。不能把05-a机身主结论写成错误；不能凭空宣布输入正确、只改生成提示词。

选择最小的**受审旁挂关系消费**路径：不改原PDF／缓存／切片正文，不重导入或重算向量；在既有证据归属模块与正式消费者中传递“这条具体表行属于该具名配件”。总控证明已给出两表来源与12行成员hash；无需重做语义审阅，但必须验证内容hash及正式绑定身份。

必须绑定：原件SHA、缓存SHA、冻结document／revision、表体hash与表block、行成员hash及实际chunk身份、审核报告／证明的Git来源和hash、适用语料快照／范围。`payload_sha256`按证明除该字段后的项目canonical fingerprint计算；文件hash是另一层，不能混淆。该JSON本身尚不是服务已登记的binding，不能伪造已消费状态或审核身份。

先从既存冻结载荷／持久快照派生精确chunk→表行映射，验证table成员和来源，不凭正文或标题字符串匹配跨表绑定。同样的USB行可能属于两配件，必须保留各自来源；若缺精确成员关系则unknown／拒绝消费，列明缺项，不能“最近标题即归属”。已知LAN冻结UID为`62b18a99-8a1c-5d46-9ff2-a6661bc82256`，孤立标题UID为`6116cc5a-9772-5cdb-b53c-b1811856ed53`；不能使用总控缓存子集复放产生的新UID冒充冻结切片。

具名配件是证据对象，不冒充已授权产品目录项；文档产品G540与配件主体分开。最终prompt／reference_map只附最小对象关系与其来源，保留原连续编号／budget；不注入目标答案或完整期望回答、不按05-a等题号特判。关闭时原路径全等。

**表级页码与行级页码分开**：关系证明允许说明标题p13、表p14；原LAN行source_refs仍unknown，不悄悄提升精确页码或重开P2。既有p30关系保持。任何新来源展示必须准确标明表级审核证据，不能伪装成旧行精确定位。

策略及证明hash进入现有配置、Run幂等身份、执行关联、题级检查点、continuation及恢复核验；旧Run不得追加策略，配置漂移拒绝，默认关闭／回切等值。新prompt或配置使用新派生诊断身份，旧manifest／请求键／六Run不覆盖、不把旧答案当新策略结果。

## B．把输出计量口径变成可核验合同

已排除“4096未发出”和“reasoning重复计账”：六次实际kwargs为`extra_body.max_tokens=4096`，原流与telemetry一致。03-a为output6150／reasoning5556，05-a为4744／3848，均stop。真实网关为第三方兼容服务，其字段口径仍unknown。SDK Mock只证明wire／映射；不能证明供应商硬限。

先核已有本机供应商合同／可用能力材料和封存响应，不发真实探测。不要输出端点、key或private-identity。若读取公开技术文档，只依适用供应商的原始材料，记录固定出处、版本、hash和适用endpoint hash／model；不能套原厂Qwen语义到代理服务，也不能把模型名称相似当作能力证明。

在既有provider／answer budget机制中显式区分：limit字段、字段覆盖visible或含reasoning总量的语义、thinking开关与独立预算（仅在已证明支持时）、endpoint hash／model／客户端版本、证据来源及unknown状态。不要重复新建一套完整调度器。**本诊断的4096原保守总输出预算不能静默改口径或放大**；要改变须作为待裁定配置差异，不自行采用。

unknown／证据不适用／缺失时，在后续诊断调用前fail closed，提供安全具体错误，不能自动换字段／模型／提高上限或fallback调用。两种limit字段冲突、extra_body冲突、thinking标志不匹配或恢复时能力身份变化必须明确处理。关闭新策略保留旧非诊断路径；不把本诊断限制无差别施加成项目所有历史Run的新门槛。

保留真实总usage，不另加reasoning；可见量未知仍unknown，total-reasoning只是差值。未知HTTP／费用不写0。逐题结束后先结算新／累计／未知窗口，核单请求及累计预算，再允许下一题；缺usage／超限／未结算时停止，不把响应截断、finish_reason=stop或“累计未超”当服务端单请求cap通过。客户端取消也不能证明未付费token的硬上限。

能力合同及生效参数hash须纳入新诊断配置／请求／恢复身份，不修改旧Run。若本机证据仍不能证明真实网关语义，**照样完成可实现的代码、合成测试和来源修复**，将真实能力状态保留unknown；交付一项最小探测建议的精确输入、候选字段、token上限／最大请求数、幂等／不重试／未知费用方案，供总控另行裁定，本包不执行。不要笼统只写“请用户查账号”。

## 一次覆盖本包直接边界

先写暴露现状的红测，再实现，保留红／绿结果；只跑本包影响范围。

| 边界 | 必须证明的结果 |
| --- | --- |
| 两表正常关系 | MateDock3的LAN／microSD有精确成员关系；MateDock2无LAN，机身RJ45独立。 |
| 相同正文／不同对象 | 两表同名USB等接口不按正文串绑，不根据G540文档产品推断配件。 |
| 跨页与标题 | 允许已审p13→p14；footer未受审不自动当标题，错误／缺失／冲突证明拒绝。 |
| 文档／修订／内容漂移 | 正文、表hash、chunk、document／revision、原件或proof Git来源变更不能复用旧关系。 |
| 页码／缺项 | LAN旧unknown保留；表级证据独立，未绑定行仍unknown，不捏造兼容性。 |
| 实际消费者 | 缓存回放得到新版最终prompt／reference_map，可见对象关系且编号不丢；预算不扩，检索分数／rank／切片不改。 |
| 关闭及身份 | 默认关闭／回切等值；配置、授权、Run／题级恢复／成功检查点／崩溃关联窗口按现有合同拒绝漂移。 |
| cap发参／映射 | 安装SDK＋MockTransport，测两字段及冲突、thinking标志保留、原六流usage，明确Mock不是供应商证明。 |
| 未知／超限／异常 | 未知能力调用前拒绝；usage缺失／总量越界／中断／超时／重复结算均不派下一题、不重置预算。 |
| 两版与历史 | 不跨版继承答案；旧六Run、质量记录及blocked原样；新策略不会偷偷继承旧请求成功。 |

用54个已存实际检索消费者输入、原分数作**零新增推理正式回放**；检查27题两版及047澄清不受损、048双方及同轴／EoC、原25题35必要单元的已存保护边界。旧检索／分数缓存只在精确计算身份未变时复用；新prompt产生新的hash，不要求启用后旧prompt字节全等，但要列出全部差异，所有非关系相关内容不随意变化。任何额外缺缓存仅列完整缺项，不能自动补调用。

## 退出、交付与后续

一次交付两项完整矩阵：已实现并自验通过、外部能力unknown、实际答案效果未验证，三者分开。不因能力unknown停止独立可做的来源修复；不以合成通过冒充实际网关支持。不要再拆成逐个反例往返。

生成脱敏报告／JSON、可读新版输入对照及下一次接续所需精确配置差异；列新增调用0与此前六流input23480／output16506分别计账，HTTP／费用null，历史保护清单与源码变更范围精确列明。维护PROGRESS、REVIEW_STATUS、TODO、M6任务、contracts、CHANGELOG、DECISIONS，保留历史；显式暂存、提交、普通push并核本地／origin／远程。原始流、PDF、缓存、日志只留本机新output目录。

本包结束交总控独立核验两项技术边界及真实能力证据。没有真实供应商证据不能放行调用；有证据也不自动恢复48题。下一次真实接续应先确定新版05-a的有限重验范围、来源／身份／预算／恢复，不重用旧成功Run冒充新答案；通过后才按已有质量合同评估继续诊断或同范围正式候选，最后才是双轮、gate和反馈proof，不进入M7。
