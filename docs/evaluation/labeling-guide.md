# M4题集标注与冻结规则

M4-01目前是未验收接续点。用户后来已委托总控助手审核50题，独立原件核查已完成，43题可保留、4题建议补充、3题需修改，见[审阅结论](../development/reviews/M4-01-dataset-review.md)。不再要求用户自行逐题核读。本次未运行dev原链路查询、heldout或调参；先新增修订冻结版本、回应审阅问题，再续基线准备。原始题目、手册、问答和evals只留本机。

## 当前审阅材料

本机`output/evals/support-v1-review.md`包含50题、期望关键点与原件物理页；`evals/datasets/support-v1.jsonl`保存包含禁止结论等字段的完整结构化标注，`split-manifest.json`保存来源、逐题及划分指纹。题集SHA256：`041c2a4c27929bf82879e8682acd7b4d0074e2476396acd5bf97507c9f33d975`。dev35、heldout15；50题均为执行助手对照原件的辅助草稿，人工复核0题，不伪填reviewer。

独立逐题意见保存在本机`output/evals/support-v1-assistant-audit.md`与`output/evals/assistant-review-r1/audit.json`，三项必改的字段建议在同目录`proposed-changes.json`。原可读稿实际上省略了forbidden_claims、history、source_scope和证据组层级；新审阅报告已补齐，后续生成审阅稿须完整展示。助手独立审核与真实人工是不同身份，当前schema没有前者的正式已审状态；需扩展协议时另作实现及验证，不得把助手写成human_reviewed。本次报告不改原50条annotation。

## 逐题复核

1. 对照原PDF物理页，核对可答性、型号、单位、范围和前提；不得从模型答案反推标准。
2. `allowed_evidence`外层是全部必需组，内层是每组的多个正确替代证据。保留真实原文与原始图示，不只依赖模型摘要。
3. 图示须目视准确对象、指纹和连接关系。本轮原PDF裁图与既有MinerU裁图未必同字节，未建立准确映射前不能将hash不等解释为图示错误或检索失败。
4. 期望行为区分回答/澄清/不足/部分/比较；列关键点、禁止结论和无答案检查范围。多轮历史不能混入判分标签。
5. 同问题族不跨dev/heldout；策略选定后heldout才最终评价，不用于调参或挑默认。
6. 真正人工核对后才标`human_reviewed/reviewed`及真实reviewer。需修订标签则新增版本和manifest，不覆盖本轮草稿、冻结划分或旧失败证据。

## 校验、真实入口与恢复

从项目根运行`.venv/Scripts/python.exe -m app.evaluation.validate_dataset evals/datasets/support-v1.jsonl`。通过仅说明字段/来源边界/冻结/划分自洽，不证明人工正确。复核后仍须建立独立语料和`evals/configs/baseline.yaml`，绑定实际源码、prompt、本机权重及原件/活动修订；目前尚无可执行真实基线配置。

正式链路为RunService→QueryRunner→V2Index→模型重排→现有回答节点，旧四分支LangGraph仅兼容。现状：dense/sparse各20、WeightedRanker(0.5,0.5)、最终20、重排前10、12000字符上下文，未调整默认。

运行器按选定split执行；heldout须final阶段及绑定题集/策略列表/开发报告hash的selection。CLI拒绝单元注入。`results.jsonl`可从已提交的`attempts.jsonl`重建，未换行尾部先另存残片再恢复，中部损坏拒绝执行。实际适配器在独立Mongo的evaluation_items中保存会话/run，同请求恢复不重复调用已完成问题；失败/中断run不静默新建付费请求。

`.runner.lock`独占防并发。崩溃后先核对PID及配置，确认进程结束再将锁移到新的证据路径保留，使用完全相同配置续跑。不删除attempts，不手改成功检查点。语料、参数或源码指纹变化时建立新实验版本，不冒充原基线续验。

来源组命中只是原件页/资产的辅助命中，不是人工答案或精确引用正确率；p50/p95只来自实际完成耗时。单元注入、真实Mongo加端口注入、真实服务和付费调用分列，不混称全链路。
