# regression 反馈受控接续

仅维护者在授权知识库使用既有 API；与 revision 的 bind-revision、affected/full 发布证明分开。本页描述能力和顺序，不表示真实反馈已经绑定或质量通过。不在终端打印凭据，不把私有答案或原件放进 Git。

1. `GET /api/v1/feedback?kb_id=...` 核对已确认 regression 草稿、完整题目及预期；`GET /api/v1/feedback/{id}/regression-status` 只读返回绑定状态。`unbound` 不是已审；`invalid` 表示来源或冻结记录不再可核验；`recorded_not_revalidated` 仅表示有旧证明，`quality_passed=null`，不能用来发布。
2. 已有已审且内容未变的 dev 题，完整题目、反馈预期与精确原件范围匹配时，使用 `POST /feedback/{id}/regression-binding`，传 dataset_id/version、config_id/version、question_id。不能直接绑定草稿001或猜测两种预期语义相同。
3. 需要审核的题用 `POST /feedback/{id}/regression-candidates` 提交完整 draft Question；无原引用的合法澄清可另传 `evidence_revisions=[{document_id,revision_id}]`。库由已登记反馈来源确定，不能提交任意 source_database。候选保存规范映射及 `evidence_mapping_sha256`，不回填旧 Run 引用。
4. 另一具名助手核对完整标签、反馈预期映射和授权原件，提交已在 Git 固定的审核文档及 SHA 到 `POST /regression-candidates/{candidate_id}/annotation`；补充原件时须同时显式确认返回的 mapping hash。自审、缺证据、错误 hash、撤权或来源变化拒绝。审核 artifact 应明确列出题级内容及映射依据；签审不是答案 human 双轮。
5. 原维护者传 annotation_id 绑定反馈。只有 Question（含 annotation）实际变化才派生新 dataset/manifest/config entry，保留父版本。派生配置会复制父 runtime，**不能因此直接执行**；技术收敛后须新建当前可执行配置并做无生成预检。
6. 正式实验请求传 `regression_source={id,sha256}`。服务端校验来源、题级指纹、文件身份与选择范围；基线先完成有效双轮并预校准，之后候选传 baseline_experiment_id 和 regression_calibration_id。当前正式 gate 仍为 human，助手政策提案未启用，不能提交假 human 绕过。
7. 完成实验后 `POST /feedback/{id}/regression-proof` 只传 source、experiment_id、calibration_id；服务端核验当前结果、有效质量、题级关联、范围及顺序，拒绝客户端 passed。不要求虚构资料修订。

所有不可变对象相同请求返回原对象；冲突保留现场。正式 job 发布中断后由派发/claim 恢复，复用原 Run，核验完整输入/输出冻结记录；缺历史 outcome/link 时拒绝自动追认。新增调用与持久累计调用分账，缺测 null。操作方不得手改 lease/state/slot/retryable，不能重跑首次创建脚本或清库。

回切：关闭新的显式查询策略，停止新增引用；保留旧索引、修订、配置、结果、映射及证明。源码回切用正常反向提交，不重写历史。当前不切工作台默认，不运行 heldout。
