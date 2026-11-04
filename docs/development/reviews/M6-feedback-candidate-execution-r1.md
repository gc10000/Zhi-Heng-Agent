# M6两版完整候选执行与质量闭环 r1

2026-11-04，Asia/Shanghai。**本批授权执行流程已完成，答案质量未通过：两版gate均blocked、反馈proof均正式409拒绝且未保存。M6保持5/7，05/08不验收。** 实现自验、不同身份独立技术、真实质量和阶段验收分开记录。本报告替换准备期追加叙述为最终状态；此前各时点材料在Git及本机原件保留。

用户明确授权两版各85道dev、最多168个provider stream及2条零调用澄清、1名独立技术复核者和2名全新Agent依次盲审170结果（340判断）。固定qwen3.8-flash、n=1、不思考、输出4096/输入28416、SDK自动重试0、首失败停止；未知网关/付费输出/费用硬上界已接受。未重跑基线、旧43、heldout或M7，未切默认资料或发布。

## 真实正式执行与来源

两版experiment分别为`4633c638-2fb8-405b-8154-2e72c5f8b147`、`7fe25d10-5a7c-49ce-82ab-46b123f840ad`，均attempt1/completed、各85正式结果。共170 Run、168 completed生成Run/独立调用前输入锚、2 awaiting_input澄清Run；168真实stream、invoke0、0失败。实际新增usage输入809676、输出30791；授权预算4773888/688128不是usage或费用保证。精确HTTP、reasoning细目、费用null，硬上界unknown；不同历史批次不合并伪造总费用。

r5实际4资料582标量、170规划/168精确prompt/2澄清冻结，来源读取4次Milvus Strong标量查询、不读向量。manifest fingerprint `b0ad2650d3fe7675cb5bacd0d4e8cff9725f669d948b4b93092720fef7c1d867`、文件SHA256 `efe350e63f3f6f18c02a52d3cbfee6ca8f8400c9918124a81c357a13a756454b`。授权正文9f392b2、Git引用6c4f16e按顺序提交；临发重核现场582、实际模型权重/runtime/wire、旧账户、请求与空槽。独立重算和生成后正式消费者核168输入字节/引用映射、170 Run/link及两版来源/校准均通过。独立报告覆盖206文件生成后hash全等，固定源码指纹`e6ad2c5a534331760c5a3fd86f6c577340153e49240f589bb9b8f4dbae30e6d1`。

## 技术实现、自验和独立技术边界

新合同`diagnostic_feedback_candidate_manifest_r1`、独立170成员共享CAS和168流上限，服务在repo.create前核两版请求/来源/校准/规划；运行消费者核完整来源、prompt、预算、客户端与wire，独立输入锚先持久后派发。Git授权引用与生产清单分离，固定LF避免循环和Windows行尾漂移；不借旧048授权或旧槽。并发派发/halt争用同一版本，在途409拒绝假停；未知pending保留，恢复只观察原Run不重生成。

独立首轮发现授权循环、停止竞态、完整生产消费者/正式链缺口、未知恢复，后续发现恢复绕过、独立输入未核、原题规划与路由差异、产品目录brand/series/aliases丢失等问题，总控补修并由原未参与实现者复测。最终另补整题后处理首失败停止及发布异常/complete空返回/取消终态的封存，4项runner及6项job实红后补绿；在途unknown不假签halt、不覆盖首错误。旧已审三比较算法不改、不重开其独立结论。

实现最终309离线/契约、152随机短m1_test_m4_隔离Mongo通过；1条既有Pydantic浮点usage反例警告。既定experiments/feedback-loop共5浏览器契约通过，响应合成，不能冒作真实页面proof。不同实现身份`/root/independent_048_admission_review`最终结论passed_with_specific_boundaries、open_findings=[]：95离线、77隔离Mongo、4条安装SDK内存wire后处理故障、1纯runner和r5完整重算通过。完整170合成成功链绑定补修前a396c6源码；最终按206文件身份及runner/jobs差异实核，**没有伪称最终源码重跑170合成链**。各组重叠不累计；合成wire不等于真实供应商或答案质量。详见[独立技术报告](M6-feedback-candidate-independent-review-r1.md)。

## 双轮真实质量、正式gate与proof

两位新Agent均fork无父历史：`/root/feedback_full_blind_round1`、`/root/feedback_full_blind_round2`。第一轮完整两版seal后才begin第二轮，START在正式begin后；两轮分别独立读170完整实际结果和原件，共340判断。总控核完整原始初稿全等、两轮输入与正式答案/引用/状态/候选相同、hash/四维/唯一subject及先后；只运输不改语义，没有第三票或消去unknown。第一轮实看16物理页，第二轮38页；后台工具轨迹、OS沙箱及精确审核模型不可全核，第一轮精确START未捕获的限制明确。独立性报告2dd50fc已提交并push，随后两版正式attest各1份。详见[独立性核验](M6-feedback-candidate-blind-independence-r1.md)。

| 版本 | 题级结果 / 正式判断 | 下降维度 | 涉及下降题数 | 不完整题数 | 关键错误题数 | gate / proof |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 85 / 170 | 22 | 13 | 8 | 0 | blocked / 409拒绝 |
| 2 | 85 / 170 | 21 | 12 | 8 | 2 | blocked / 409拒绝 |

两版各7题步骤适用性分歧和047第一轮unknown保留；版本2的18-a/18-b两轮均wrong_object。实际问题还含规则合同进入产品答案、图标/连续步骤关系失真、无依据的数量/绝对限定、来源正文消费不完整。001/048在两版双轮均事实2/引用2、其余N/A，无critical，已成立子项保持。047前端确有固定澄清提示与候选，不能将审核包空answer等同网页空白；该限制单列，不改封存评分或凭此放行。完整统计与实证定位见[固定质量报告](../../evaluation/M6-feedback-candidate-development-quality-r1.md)。

两条proof实际调用返回409 regression_proof_invalid，真实存量0。正式gate重读当前基线校准/结果/评分/来源；两版85结果分页和completed恢复已核，恢复禁止构造生成器、新stream0且账本hash不变。正式halt后共享账户blocked，cursor170、settled170、168stream、pending=null、unknown=[]；旧两个停止账户全等。最终只读复核重算质量和gate、核340原始记录/4seal/2attest/0proof及账户终态通过。**blocked是当前质量结论，halt是调用生命周期封存，不能混写为成功或可重领。**

## 原始失败与证据限制

保留全部首轮实红、夹具/包装器错误和补修日志。来源夹具/真实冻结探针的源码漂移拒绝、系列目录丢失真失败、runner4红/job6红不隐藏；部分早期红绿只有终端原输出，没有补造日志。首个发布出口探针误读public字段先KeyError，修夹具后才形成真红；浏览器包装器GBK打印失败与实际5项JSON通过分别记。授权编排首次CRLF/LF字节比对失败、正式生成核验首次误取output_truncated、本次核验脚本编码名称拼写错误均属工具/脚本问题，保留可见失败，不冒作产品红测。最终工具按实际Git原字节和receipt字段核清。

完整582标量/权重临发实核不等于全业务库/向量/TTL扫描；本轮无前端行为改动，5页面项是合成契约。原始PDF、prompt、完整答案、340判断、日志、数据库及模型不提交。私有执行目录`output/m6-feedback-candidate-controller-20261104-r1/`，完整输入`output/m6-feedback-candidate-full-20261104-r5/`；脱敏hash/回执与统计见[机器摘要](M6-feedback-candidate-execution-r1-validation.json)。

## 阶段判定与下一完整修复包

M6-04保持；M6-05反馈审核/标签/绑定及原校准保持有效，但本批正式proof拒绝，故05不验收。M6-08真实完整候选、固定比较、恢复和既定页面契约已有实际证据，但有效候选质量与真实反馈复评proof未成立，阶段不验收。M6仍5/7，不进入M7，不增加human、heldout或Ragas门槛。授权168流已全部消费，旧批停止不可重试；不以同profile重抽或新授权包装旧槽。

下一整包按[证据驱动修复计划](../../superpowers/plans/2026-11-04-m6-complete-candidate-quality-repair-r1.md)处理对象限定/证据消费、内部规则外泄、图标与步骤时序及审核呈现边界，先覆盖完整失败矩阵的离线正反例和故障路径，不用扩词/改检索/补标签代替修复，不退回仅摘录答案。新答案必须另有合法新批身份和有界预算，不能消费本批余额（实际0）；未来生成与独立审阅范围变化仍按用户明确授权办理。此计划不预先声明修复或新的独立通过。
