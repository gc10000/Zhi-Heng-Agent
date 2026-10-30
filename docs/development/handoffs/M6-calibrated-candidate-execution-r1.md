# 交给执行Agent的完整指令：两版已校准dev候选与反馈复评

请按本指令执行M6剩余质量链。总控已正式接受固定六结果的双轮来源，完成两份attestation及两份预校准，并按原合同验收M6-04。当前M6核心5/7（01／02／03／04／07），05／08待验收，M7未授权。下一包从独立候选开始，不再开发审核纠错接口、重做六题补证、重生成基线、重attest、重校准或重登记题集。

## 1. 接续与已关闭范围

仓库：`D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag`。先读AGENTS、PROGRESS、REVIEW_STATUS、M6任务及Git约定，只读核对HEAD、origin/main和远程。当前总控两次同包文档提交均须保留，不回退到38ab41e；如有后续新改动，先判断是否影响本包。不要整轮重跑旧测试／审计。

先读本轮[总控报告](../reviews/M6-review-repair-attestation-r1.md)、[验证摘要](../reviews/M6-review-repair-attestation-validation-r1.json)、[固定基线报告](../../evaluation/M6-baseline-development-quality-r1.md)。本机精确输入：

- `output/m6-review-repair-attestation-20261030/candidate-v2-requests.json`：两份完整请求，已经填入真实quality／regression calibration ID。
- `output/m6-review-correction-fix-20261030/prepared-r4/catalog/catalog.json`：两份candidate/v2冻结catalog。
- 同prepared-r4的`coordinator.json`：既有owner、控制库、case和正式来源身份；只读所需公开投影，不读private-identity。
- 本轮`attestations.json`、`calibrations.json`、`post/result.json`和`private-evidence-manifest.json`：核对精确请求与校准来源，不重新执行这些写入脚本。

| 版本 | dev版本 | 原基线实验 | 正式预校准 | 候选配置／固定请求键 |
| --- | --- | --- | --- | --- |
| 1 | fb-07c584730833908571fe9dd7c7c890afa3cf9e66 | 2b4307e3-2f03-46d7-850c-7d1054b1f8d2 | 69a95e6b-c3b1-4ee1-8523-bab605451a2b | m6-final-1-candidate/v2；m6-final-1-candidate-review-fix-v2 |
| 2 | fb-a3fa87c1adb2a6dc4e9638214164eb5f343ad008 | 29d405dc-81c9-4b63-a35f-5abdcbea081c | 379c925f-3bd9-4f2a-9607-e5a9679f0a2f | m6-final-2-candidate/v2；m6-final-2-candidate-review-fix-v2 |

第一版配置SHA256：`20fbcf3e47e7275b1dd01b24a2309ceaba287a5cbf77b76587866c0fc3e5aa26`；第二版：`b49c1bd7bf0689935bc13f0cb975f28029525e990ae09899d4c783733c981424`。控制库、政策及regression_source各自以请求为准，两版政策ID相同也不能互换hash／来源／校准。每版范围85 dev，65 heldout仍不运行。

旧P2、p30出处消费、001正式签审／派生／绑定、组合接线与冻结预检的关闭结论保持。无需用户找PDF、查账号或手工评分。两版047合理澄清作为完整评测结果保留，不能为凑85个答案强行回答。低分不是unknown，不删题或改分。

## 2. 一次调用前核对，然后正式执行候选

在全新本机output目录保存本包脚本、计划、调用账本和回执。先核对上述私有hash、两校准正式读取结果、来源／配置／权限及当前runtime identity；这是调用前必要核对，不再准备一包重复“待登记”材料。若一致，按既有真实dev候选授权继续执行，无需重复索取用户授权。身份确实漂移则报告精确字段和正式拒绝，不静默重冻配置或重生成基线。

开始真实推理前向用户说明：两版85 dev范围、模型／prompt／语料／组合来源；固定请求键与config hash；实验ID由正式创建回执产生，Run及题级关联由正式路径生成，不预填不存在的ID；每题有效config／subject／检查点身份；调用上限计划与本次已发生、历史累计分账；故障恢复方式和usage未知项。

本包是新候选，不能把基线检查点或旧r3的19条检查点算作候选独立执行。可复用合法解析／向量／模型缓存，是否复用以及实际新增编码／重排均据账本记录。基线历史168次逻辑stream、input321926／output168290 token及未知HTTP／费用保持，不将计划170题写成实际170次调用。合理澄清、缓存命中和失败窗口分别核账。

通过`EvaluationService.create_experiment(owner, request)`使用原样完整请求，在对应控制库创建，立即保存真实回执；再通过正式`execute_job`执行。两版顺序推进。可先审阅历史`output/m6-formal-quality-chain-20261030/execute_baseline.py`，在**新目录**适配为候选驱动：替换输入为本轮两份请求／prepared-r4 catalog、正确候选范围声明，保留透明调用旁录、权限校验、检查点与故障观察；不要原地运行或改写旧驱动和证据，不复制旧答案／评分。适配仅是执行驱动，不修改业务策略。

模型桥接环境维持正式冻结设置（原准备明确禁用MODEL_HOST_URL／MODEL_HOST_TOKEN），不打印环境或凭据；核对模型实际身份，不改.env来迎合hash。正文、原分数、weighted .5/.5与20／20／20／20／10，以及已审source_branch_compare_v1都按候选冻结配置消费，不再试词或换融合规则。

创建响应不明时，先只读查固定请求键；只能全等重放，不能换键重复创建。已有运行或终态实验先读正式状态，不盲跑job。中断按正式lease／retryable／continuation协议处理，复用本候选成功检查点；不手改state、lease、slot、retryable或token，不把provider_invalid_response当可自动重试。保留started未completed窗口并如实记未知调用／费用。需要额外付费重试且不在既有授权内时才提出具体恢复动作。

## 3. 同范围真实独立候选双轮

候选完成后先按题核对结果、Run、来源、调用账本及85题完整范围，再按assistant-development-v1和question-purpose-v1组织真实双轮。不得从基线分数或六结果补证复制候选判断，不因需要过门禁重复抽审到同分。

本指令由用户转交执行会话后，仅为本包候选质量审阅授权两个全新`fork_turns=none`审核子Agent，顺序执行，不授权开发并行。两个审核任务各自对两版85题的实际候选结果审阅；同轮跨两个版本的实际使用范围如实记录，不虚称为四个完全独立任务。先按正式begin冻结第一轮纯输入并完成真实审核／seal；两版第一轮封存后，再建立第二轮。第二轮不读取第一轮判断、回执或封存文件。总控与运输主体不填审核者分数或代签。

纯输入应包含当前完整答案、实际展示来源、必要原件及明确题意，不暴露expected／annotation／基线或其他轮评分。原始输出、允许读取清单与hash、时间、任务ID、可见模型身份、工具访问及所有失败留存到各自独立目录；未知精确模型、token／HTTP／费用保持null。不得把协调端的全量配置／校准／评分摘要放进盲审包。封存记录与原始输出逐项全等核验，begin→实际审核→seal时间顺序可查。

如出现unknown、来源未核、critical、同一维度N/A混合，或正式gate发现任一退化，保留具体题目／维度／来源并停止相应版本后续证明；不要私改case、适用性、评分、预算或删除反例，也不以第三票表决消解分歧。基线纠错case不能直接套给新候选。若为真实协议缺陷，交最小反例和正式错误，由总控明确范围后处理，不扩大成全量重审。

双轮完成即交总控核验实际provenance。执行方可运输并封存已有判断，不能自签新的总控独立性裁定；原基线attestation不覆盖候选。通过后直接正式development gate，不另开重复接口开发包。

## 4. 服务端反馈proof与任务验收

只有对应候选有效双轮及来源核验通过、正式development gate通过后，才为对应既有001反馈调用服务端复评proof路径。第一版反馈`c34496c4-c065-5765-93a5-4ba9a9167e55`，第二版`ff45ecf4-4b82-5f3b-a31d-808ec5ae485e`；仍使用各自valid绑定及请求内regression_source、派生版本、基线和校准。不能重签／重绑001，也不能把两版proof合并或用客户端passed代替。

M6-05退出：两条既有反馈各有真实同版本候选及有效服务端复评proof，来源、校准、题级结果与审核完整匹配；相关原反馈闭环合同满足。不能用“001标签消费通过”代替整条闭环。

M6-08退出：独立候选和同范围双轮／正式gate的真实证据、05闭环、固定阶段报告及剩余合同项逐项齐备，经总控验收。原24题、048及对象／配件04-a／05-a／05-b／17-b以实际候选答案与正式审核判断核验，覆盖25/25不预定答案质量改善。保留低分和置换代价，不把非劣化写成绝对高质量。M6-04保持已验收，不因05／08待完成而回退。

## 5. 交付与范围

保存脱敏报告／JSON：两版实际候选ID、Run／题级来源、模型及本地调用分账、缓存／恢复、双轮封存与独立性边界、gate／proof实际状态、通过及失败矩阵、历史保护和证据限制。总控核验节点前如尚无gate／proof应明确写pending，不预填通过。更新当前导航且保留历史，显式暂存应提交文档及必要驱动说明、普通push并核对本地／origin／远程。

output／evals／原始答案／PDF／日志／缓存／private-identity不上传，tmp保留。合成写库测试如确需执行使用随机短`m1_test_m4_`库，不把真实状态当故障夹具。M7、heldout、默认切换和human发布未授权；不新增Ragas、heldout或用户手工评分前置。
