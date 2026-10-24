# M4题集标注与冻结规则

M4-10配置策略通过`m4-configured`与严格parameters接入正式QueryRunner；原`m3-baseline`不接受参数覆盖。`python -m app.evaluation.quality_grid --dataset <JSONL> --manifest <划分> --config <YAML> --output <新目录>`仅用于dev真实检索单因素/组合，输出不是生成答案。阶段缓存绑定完整执行版本与语料；原始耗时继续约束可选分支，命中不能把超时变为质量收益。所有复用、原耗时与逻辑供应商invoke/stream计数单列；不缓存答案、不将复用后的wall当生产时延，精确SDK重试数/金额未知。宽窗口字符兜底是当前模板对照，不能冒称历史原链路。先dev报告/默认选择冻结，再最终heldout；来源指标、人类正确率和助手答案抽检分别报告。

M4-01已完成执行自验，M4阶段仍在执行。用户委托的独立原件审核及r2七题定向复核均已完成，三项必改/四项补充关闭，见[第二轮结论](../development/reviews/M4-01-dataset-review-r2.md)。可以继续独立语料、资产映射、配置及dev原链路基线；不再等待用户逐题核读。35dev原链路基线及完整只读复核已通过，34逻辑生成/1澄清；heldout和调参未运行。原始题目、手册、问答和evals只留本机。

## 当前审阅材料

本机`output/evals/support-v1-review.md`包含50题、期望关键点与原件物理页；`evals/datasets/support-v1.jsonl`保存包含禁止结论等字段的完整结构化标注，`split-manifest.json`保存来源、逐题及划分指纹。题集SHA256：`041c2a4c27929bf82879e8682acd7b4d0074e2476396acd5bf97507c9f33d975`。dev35、heldout15；50题均为执行助手对照原件的辅助草稿，人工复核0题，不伪填reviewer。

独立逐题意见保存在本机`output/evals/support-v1-assistant-audit.md`与`output/evals/assistant-review-r1/audit.json`，三项必改的字段建议在同目录`proposed-changes.json`。原可读稿实际上省略了forbidden_claims、history、source_scope和证据组层级；新审阅报告已补齐，后续生成审阅稿须完整展示。助手独立审核与真实人工是不同身份，审阅时schema尚无前者的正式已审状态；r2已按下文扩展协议并验证，不把助手写成human_reviewed，也不改原50条annotation。

## 逐题复核

### support-v1-r2 定向复核接受（2026-10-24，当前）

总控接受001/023/037/038/042/043/047七题新内容与审阅溯源，连同不变的43题累计50题来源审核完成。冻结r2仍保持回交时43 reviewed/7 draft、人工0，不回写manifest；[本轮结论](../development/reviews/M4-01-dataset-review-r2.md)与[独立摘要](../development/reviews/M4-01-dataset-review-validation-r2.json)绑定r2完整SHA及七题当前subject指纹，可以按既有授权继续独立语料、资产映射、真实配置及dev基线，无需等待用户逐题核读。实验记录应引用本次接受结论及其hash。若未来需要内嵌更新annotation，另建版本并绑定本次结论，不修改原冻结文件、不要求重复审核不变内容。下节待复核计数是执行回交时历史状态，M4-01整体仍未验收。

### support-v1-r2 修订与审阅身份（2026-10-24）

新增本机`evals/datasets/support-v1-r2.jsonl`、`support-v1-r2-manifest.json`和`output/evals/support-v1-r2-review.md`；原版及原manifest不覆盖。新版本保留50题的ID/问题族/35与15划分，修改001/023/037/038/042/043/047七题。完整可读稿逐条保留所有JSON字段，包含历史角色/顺序、禁止结论、来源检查范围、全部必需证据组和组内替代项。044历史内容未改。

`annotation.method=independent_assistant_review`明确表示用户委托总控助手的独立原件审阅，不是人类；`status=reviewed`只表示该身份已审。必须填写真实`reviewer`与`review`：仓库内审阅文档相对路径`artifact`、文档SHA256、40位提交`commit`、`method=independent_source_audit`及`subject_sha256`。subject是**不含annotation的原始题目对象**，沿用校验器的规范JSON fingerprint；任何问题、历史、产品、证据或期望答案修改均使旧已审状态失效。路径限制在`docs/development/reviews/`内的Markdown文件。schema验证引用形状和内容绑定，不自行认证审阅人的身份或访问GitHub；本轮另对照本地Git提交字节与审阅文件hash验证溯源。

43题内容未变，记录原审阅的`control_assistant`身份和内容指纹；七题修订后保留`source_checked_assistant_draft/draft`，`review`仅关联修改前的独立意见，**不把该意见当成新内容已审**。这些题没有填写执行者冒充独立reviewer。后续只需定向复核七题修订与证据，不要求用户重读全部50题。`human_reviewed/reviewed`仍只用于真实人工，计数须同时检查method与status，不能把reviewed总数当成人工数。本轮43独立助手已审/7修订草稿/真实人工0。

新版本检查命令：`.venv/Scripts/python.exe -m app.evaluation.validate_dataset evals/datasets/support-v1-r2.jsonl --manifest evals/datasets/support-v1-r2-manifest.json`。题目ID沿用原版，由dataset版本/字节sha区分，不沿用旧实验输出目录或策略选择。047空证据组且行为为clarify，正确无引用澄清的组召回为null；human_answer_correctness仍null。038新增物理第3页起始步骤必需组，并保留第4页后续步骤，物理页3/4均须覆盖。

覆盖仍是dev有歧义/跨型号、heldout有无答案；不声称heldout覆盖全部能力，不调整划分填补缺口，不观察heldout模型表现。本轮仅离线修订，真实基线/heldout/模型调用均未执行；M4-01未验收。修改回应与指纹见[本轮回交](../development/reviews/M4-01-dataset-revision-r2.md)。上节描述的50条draft为原版本历史状态。

1. 对照原PDF物理页，核对可答性、型号、单位、范围和前提；不得从模型答案反推标准。
2. `allowed_evidence`外层是全部必需组，内层是每组的多个正确替代证据。保留真实原文与原始图示，不只依赖模型摘要。
3. 图示须目视准确对象、指纹和连接关系。本轮原PDF裁图与既有MinerU裁图未必同字节，未建立准确映射前不能将hash不等解释为图示错误或检索失败。
4. 期望行为区分回答/澄清/不足/部分/比较；列关键点、禁止结论和无答案检查范围。多轮历史不能混入判分标签。
5. 同问题族不跨dev/heldout；策略选定后heldout才最终评价，不用于调参或挑默认。
6. 真正人工核对后才标`human_reviewed/reviewed`及真实reviewer。需修订标签则新增版本和manifest，不覆盖本轮草稿、冻结划分或旧失败证据。

## 校验、真实入口与恢复

从项目根运行`.venv/Scripts/python.exe -m app.evaluation.validate_dataset evals/datasets/support-v1.jsonl`。通过仅说明字段/来源边界/冻结/划分自洽，不证明人工正确。已建立本机`evals/configs/baseline-r2.yaml`和独立三资料语料，绑定实际源码（含评测实现）、prompt、本机权重、接受结论，以及原件/活动修订/完整切片载荷与向量/图片/产品。配置文件字节SHA与manifest中的规范JSON配置SHA不同，分别记录，不混用。

正式链路为RunService→QueryRunner→V2Index→模型重排→现有回答节点，旧四分支LangGraph仅兼容。现状：dense/sparse各20、WeightedRanker(0.5,0.5)、最终20、重排前10、12000字符上下文，未调整默认。

运行器按选定split执行；heldout须final阶段及绑定题集/策略列表/开发报告hash的selection。CLI拒绝单元注入。`results.jsonl`可从已提交的`attempts.jsonl`重建，未换行尾部先另存残片再恢复，中部损坏拒绝执行。实际适配器在独立Mongo的evaluation_items中保存会话/run，同请求恢复不重复调用已完成问题；失败/中断run不静默新建付费请求。

`.runner.lock`独占防并发。崩溃后先核对PID及配置，确认进程结束再将锁移到新的证据路径保留，使用完全相同配置续跑。不删除attempts，不手改成功检查点。语料、参数或源码指纹变化时建立新实验版本，不冒充原基线续验。

来源组命中只是原件页/资产的辅助命中，不是人工答案或精确引用正确率；p50/p95只来自实际完成耗时。单元注入、真实Mongo加端口注入、真实服务和付费调用分列，不混称全链路。


## 独立语料冻结与图像对应

真实入口每题执行前只读复核完整语料快照；仅原件hash和活动指针相同不足以证明切片正文、metadata、向量或图片没有变化。切片业务载荷和dense/learned sparse向量分别规范化取hash；图片复核对象字节/完整解码、资料与修订、独立对象前缀、摘要状态/文本hash、缓存identity、物理来源，并绑定产品集合。先拒绝变化的切片载荷，再读取其图片引用；不让变化引用引导访问其他对象。默认真实入口缺完整snapshot或接受结论hash不符时拒绝资源初始化；测试resource_factory显式注入不代表真实语料验收。

原PDF标准裁图与MinerU输出可能覆盖同一准确对象但字节不同。仅允许目视核对并冻结的document_sha256/page/asset_sha256/expected_asset_sha256对应，绑定reviewer、原图裁图与比对图hash。同页其他图不能替代，结果保留实际引用asset_sha256，不把对应写成同hash。当前三处对应仅用于辅助来源组召回，不证明模型读懂原图或答案正确。

历史摘要准确命中字节及原上下文缓存，但其原模型/prompt元数据未知，保留unknown。原解析部分code块缺正文、来源只有物理页等限制纳入基线，不从gold修补。基线首题包含冷加载，运行期间同机离线测试可能影响耗时，本轮p50/p95只作执行观测，不称隔离性能基准。SDK内部网络重试尚无HTTP计量，不将持久run生成次数等同精确HTTP调用次数或金额。

基线结果、精确命令与限制见[交付说明](../development/reviews/M4-01-baseline-delivery.md)；后续策略实验使用新配置/版本，不重写本次原始结果。
