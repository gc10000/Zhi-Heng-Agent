# M6 固定诊断缓存补齐与继续执行完整Prompt r1

你是本包执行Agent。日期2026-10-31，Asia/Shanghai；仓库`D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag`，Windows／PowerShell。

## 已裁定授权，直接执行

先读适用AGENTS.md、PROGRESS、REVIEW_STATUS、TODO、M6任务、contracts、GIT_WORKFLOW，以及：

- `docs/development/reviews/M6-diagnostic-cache-review-r1.md`及对应`M6-diagnostic-cache-review-validation-r1.json`；
- `docs/development/handoffs/M6-attributed-evidence-diagnostic-execution-r1.md`；
- 上包`M6-attributed-evidence-diagnostic-execution-r1.md`／摘要与本机prepared-r2、stop、缓存材料。

核对HEAD、工作区、origin/main及远程是否新增。审查接续10a07cecde2a1e9d4f3844f65ce45592b76b0c02；后续总控文档提交不改变已核app／prompt树。

**本Prompt是原有界诊断的受控准备增补，优先替换其中“缺缓存即停且禁止任何新增编码／重排”的准备阶段限制。** 总控已经裁定本包预算，无需再逐键索取用户授权。原52答案stream上限、54单题job粒度、非验收身份、范围／策略／首失败停及所有历史保护不变；047不生成答案，但明确允许其必要的目录编码。先补齐、全范围预检，再继续原诊断，不仅交付又一份准备报告。

保留M6 5/7、04已验收、旧v2两gate blocked及原评分。047呈现、最终逐维source_checked、attributed_assertions_v1接线及P2／p30／001／组合／continuation已经独立关闭，不重做账号、标签、基线、预校准或技术整轮复审。不新增业务规则、不开展其他召回策略实验、不启动M7／heldout／默认切换或新子Agent。

## 固定范围、身份及证据位置

原主manifest仍为`output/m6-attributed-evidence-diagnostic-20261031/prepared-r2/master-source-manifest.json`，semantic SHA256=`3e4931e8ac206f243851a206ab3f888a51a59cee068ad96c18ba9138971f5467`，文件SHA256=`e479481dec4be520d673d561975ab7a068d8298bbc85ea4ce72bcb5ed3d4e0e0`。复用该目录既存54份子配置及execution-manifest，不重跑startup创建脚本，不重写主manifest、配置或client_request_id；附加本包授权／缓存账本manifest并互相绑定hash。

两派生题集版本分别是`fb-07c584730833908571fe9dd7c7c890afa3cf9e66`、`fb-a3fa87c1adb2a6dc4e9638214164eb5f343ad008`；完整85 dev／65 heldout不改。每版仅以下27题，按原次序：

```text
m6-g540-02-a
m6-g540-02-b
m6-g540-03-a
m6-g540-04-a
m6-g540-04-b
m6-g540-05-a
m6-g540-05-b
m6-g540-09-a
m6-g540-09-b
m6-g540-10-a
m6-g540-10-b
m6-g540-11-a
m6-g540-17-a
m6-g540-17-b
m6-g540-18-a
m6-g540-19-b
m6-g540-20-a
m6-g540-unknown-01-b
m6-g540-unknown-03-b
m6-g540-unknown-04-a
m6-g540-unknown-04-b
m6-g540-unknown-05-a
m6-g540-unknown-05-b
support-v1-008
support-v1-030
support-v1-047
support-v1-048
```

新工作使用全新`output/m6-diagnostic-cache-completion-20261031/`，如已存在则另选不覆盖的r2目录。总控可复用证据为`output/m6-diagnostic-cache-review-20261031/query-requirements.json`、`summary.json`、`saved-score-source-inspection-r2.json`及`input-protection.json`。先读脚本再复制／适配；不在旧目录运行会写文件的脚本。

runtime预期：code=`bcbc147ce1183fb5cf774099c8080838bc11284919bc2939d346f6e3de9932da`；prompt=`5c0cb39e58800fc437c1f32b48b05540363ea8dbb8a147f5e030aa84a59aa9dc`；model=`565fbfe4c795fb52f84183f7b2708491fd7824fa07f2de9fd546e9d6d6e5bb90`。实际模型名／端点身份／参数从正式runtime核，不凭hash猜测；进程内本地模型环境overlay沿旧冻结，不修改.env、永久代理或正式默认配置，不自动下载模型。

策略仍是已核source_branch_compare_v1＋attributed_assertions_v1，weighted .5/.5，20／20／20／20／10；窗口32768、输出4096、预留256、max_chars12000。源码／prompt／范围／预算漂移不自行修复掩盖，留证停止。

## 总预算，未使用部分不是必须消耗

| 类别 | 本包允许的新增上限 | 去重及限定 |
| --- | --- | --- |
| 查询及目录编码 | 17个固定精确缓存键／17本地小批／20文本输入 | 15单文本检索键＋047的4／1两批；两版共享 |
| 本地重排 | 520来源绑定pair、26补分逻辑请求、78内部小批 | 26个不同问题各≤20输入；内部batch≤8；先精确复用，仅补缺 |
| 答案 | 原授权剩余最多52逻辑stream | 每版26题，全部原先未生成；两版047为0答案 |
| 其他推理 | 0 | 不做预热、HyDE、扩词、图摘要、文档重编码或额外审核推理 |

答案保守预算仍为输入1477632／输出212992 token；不是实际用量。本地编码／重排token、精确HTTP和费用无可观测值则null，不把上限写成已用量。供应商调用仅限原52答案授权，无额外供应商调用。历史已核336逻辑stream、input644642／output355857单列，不当作全项目总数。

重排520是可证明的最坏上限，不是当前缺分数。两版本target／corpus／parameters／runtime相同，固定一次实际检索产物后共享相同计算；各正式实验、请求、Run、输出及质量来源仍独立，不能跨版继承答案／检查点／校准。若实际身份不能共享，不按另一版再追加预算。

## 阶段A：无推理全范围预检，先解决全部需求再生成

1. 验证主manifest及54子配置文件hash、稳定请求键、旧subject／Run来源，检查实际正式请求是否已存在。已有成功结果按正式幂等恢复读回；未结算或失败状态不另建新request绕过。不要先创建任何新job。
2. 通过现有受控服务只读核当前授权、两真实题集登记、四原件／582切片及向量／67资产、隔离修订／产品／策略／p30证明和必要配置。只报告适用差异，不重签或修旧记录，不读取private-identity或输出.env值。
3. 复核本轮29个精确编码缓存键需求：27检索＋2目录；已有12、缺17。逐项核模型文件指纹、设备／fp16、runtime、input_type=query、输入文本顺序／批次和value hash。原44条缓存是可识别集合；如在别处找到同一精确键且来源／值验证合格，优先复用并相应减少新增，不重算已有值。
4. **047直接边界**：正式`QueryRunner._product_candidates`在clarify前对`[问题,*产品标签]`编码。检查四个授权产品及实际迭代顺序，5文本精确hash须匹配已封存输入`8abb9dfd6139c588512fcc72d821660cdc28b6f71ba8f9830624d66f6c855e37`，按4／1两批取向量再恢复原顺序。不能调用不带candidate_search的plan_query并把四目录兜底当作旧top3全等；也不能注入旧top3伪称新正式结果。
5. 所有允许缺项先记录完整矩阵，不在第一个允许缺项处结束只读枚举。身份、来源、未知额外键或未结算窗口才触发停止。无推理预检失败时不执行阶段B。

## 阶段B：精确编码补齐，先结算再取真实候选

授权清单以脱敏JSON的`authorization.embedding.allowed_missing`及私有query-requirements双hash为准。每个key采用正式既存fingerprint合同：

```text
fingerprint({kind:'embedding_query', model: model_files_sha256,
 device: frozen.device, runtime: frozen.parameters.runtime,
 payload:{texts: exact_batch}})
```

本地文件模型指纹=`3995645af911d30aa3ec13c90c61919bfe52830a0611f3f3820b6097062520fc`；embedding为cuda:0／fp16=true，reranker为cpu／fp16=false；须与实际配置和冻结文件相同。按正式本地encode／generate_embeddings(query)计算，最大批4，不更换模型或请求文本。

调用前封存key／完整输入hash、原主manifest、授权报告Git来源、模型／runtime、用途和两版使用者、预算占用及planned／started；成功后独占写入新缓存、输出hash和completed。先核历史及本包completed，命中即复用；存在started但无法证明完成时停止，不删除pending、不盲目重算。所有中间失败保留。若调用被重试、崩溃或内部发生未知窗口，实际及未知消耗分别记账，不重新获得一份上限。

仅在17个允许键内计算，禁止补文档向量、重导入582片或重建原件。编码全结算后，以新旧缓存读取器验证29键全部命中且无fallback，再进入C。

## 阶段C：一次冻结真实候选、全范围缺分、按需补齐

先用完全相同的计划、过滤、向量、修订、产品范围、组合和预算核已封存真实索引响应；可精确复用则复用，否则允许对该隔离索引做只读真实检索。26个问题共27个范围查询，各一次正式search及其weighted／dense／sparse真实响应，最多81个新发往真实索引的客户端检索方法调用；缓存回放另计，这不是HTTP次数。旧索引响应必须校验完整请求与返回身份，不能拿旧最终context冒充后端输出。

两版相同计算只冻结一份；封存每个问题的原始双路／融合响应、candidate去重顺序及正式`select_candidates(...,20)`的输入。完整26题一次汇总后再封存缺分清单，不能每发现一pair就临时授权／换策略。81次预算不含只读权限／向量核验；这些其他IO另列实际观测，不猜成0。新目录只保存副本，不改数据库或索引。

优先复用已审缓存及旧正式Run重排trace＋精确来源切片。本轮已核52个Run1034条观察可追溯到517个来源绑定pair。实际pair须逐项匹配问题、chunk／document／revision、标题＋正文、模型／设备／fp16、runtime与normalize=True；记录源Run／文件hash、原分和原rank。不能只匹配题号／页码，不能把fusion分当rerank分。

注意3组相同正文来自不同chunk时原分略有差异，保留来源绑定值，禁止取最大、平均、改分或按正文键覆盖。相同来源仍有真实冲突则不静默选值：标记为不可复用；若属于冻结候选，允许在本包总上限内重新计算一次，结果独立保存，不改旧分。新实际缺pair的确切数在此阶段产生，不能预写0或520。

缺分清单必须先hash冻结，且只含26个问题的实际输入各≤20。缺多少补多少，≤520来源pair、≤26逻辑补分请求、内部≤78批，每批≤8；使用正式normalize=True入口。相同来源pair两版只计算一次。已存在合格分数不再次推理；同一问题只发一个汇总缺分请求，不拆成反复试跑。不得选择性跳过低分、改变重排输入或顺序，也不得因为预算尚余就重新取候选或继续搜词。

planned／started／completed、输入／输出hash、幂等与未知窗口规则同B。完成后核所有实际重排输入可精确命中；缓存缺失／混淆／预算越界即停。

## 阶段D：缓存全检后直接继续原单题诊断

使用正式消费者复放全部54请求的查询、实际候选／rank、context seeds／来源前提、最终prompt／reference_map、编号和预算。047走真实目录相似度的缓存向量及澄清呈现核验，不生成答案。048核同轴／EoC／Cable必要正文、双方和已审物理p30在实际输入中；原24题／35单元属于历史检索回放证据，不自动把本次27题当作同一质量分母。

为正式执行提供只读、精确、fail-closed缓存适配。可使用既有resource_factory／QueryRunner实例embedder、ranker及索引消费者接口进行旁路缓存读取，业务决策仍调用正式实现；不改app／prompt树、配置、分数／rank或权限校验。对纯读取器做最小合成检查：旧格式与稀疏键恢复、目录4／1组回、错key／错模型／错scope、缺项及started窗口均不会触发真实推理。不要重跑无关整轮技术测试。

阶段D回放及正式job期间**关闭新增编码／重排入口**：任何新miss或隐式fallback均留证停止，不能自动调用模型“修一下”。目录候选函数会捕获异常兜底，须在预检中证明缓存命中，并旁录miss／异常；即便业务兜底未抛到顶层，也不能把它作为前置通过或继续派下一job。

全检通过后，不再停在“交总控再批准运行”。直接按原52答案授权，使用原54份单题配置，经EvaluationCatalog→EvaluationService→execute_job→QueryRunner按版1到版2的原次序执行。请求稳定键仍为`fingerprint([master_source_sha, version, question_id, 'attributed-diagnostic-v1'])`；实际experiment／attempt／Run／checkpoint由正式服务创建，原master与本缓存授权双向绑定旁录。

新请求继续无quality_policy、quality_calibration_id、regression_source、regression_calibration_id、baseline_experiment_id；只允许诊断所必需的新实验／Run／题级记录，不写新质量评分／attest／校准／gate／proof。不能用旧答案充新输出，不把子集当正式85题候选，不跨版继承答案或检查点。

每个正式单题job完成后保存原流、输入、输出、出处、编号、运行状态及实际调用账，再按原Prompt的对象／配件／版本／未知边界和完整断言核对；首个明确技术或诊断失败即停，保留剩余清单。不临时改prompt、补词、改分、扩预算、重抽或自动扩170题。02-a、18-a等限定语义按既有独立结论，不重新发明错误描述。

## 恢复与退出，不把准备成功当质量成功

不要重跑首次创建脚本。正式恢复先查既存Run和服务检查点，按正式状态协议；不手改state／lease／slot／retryable。预算跨进程／崩溃累计，不能重开目录重置计数。存在无法结算的窗口则保留未知，停止而不是再试一次。

成功退出：编码17键以内全部结算、实际缺分在上限内补齐、54请求全预检通过，并完成原范围逐题诊断或在首个明确失败处按约停止；必须分别报告准备、实际执行、语义结果和未执行部分。若答案失败，本包不自修或追加调用；若所有诊断通过，交总控评估是否值得进入同范围正式85题新候选及原质量链，也不自行创建候选／proof或重跑基线／校准。

交付新增/累计/历史三本账：本地小批、文本输入、逻辑补分请求／内部批／pair、正式job／答案stream、usage及未知HTTP／费用；禁止预热或其他未列调用。输出具体每题结果、剩余列表、准备完整矩阵、所有中间失败、保护hash及本机可读对照。生成脱敏报告／JSON，更新导航保留历史，显式暂存后普通提交push并核本地／origin／远程。

真实旧状态只读；本包正式写入仅原诊断所需记录。故障夹具如确需写库用随机短`m1_test_m4_`前缀。tmp保留；output／evals／PDF／原答案／日志／缓存／凭据不上传；不读private-identity。阶段M6 5/7、04保持，05／08未验收，M7不启动。不要把执行方自验、检索覆盖或检查数量写成独立质量验收。
