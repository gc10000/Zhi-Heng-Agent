# M6连接048定向补修与完整输入冻结

2026-11-03；任务`M6-connection-048-input-freeze-r1`；分支`codex/m6-source-bound-comparison`，基点`07e92c2c5b8884183134342abdcd25791aa72764`。当前总控直接审阅并实现，以下均为**实现身份自验，不是不同实现身份的独立技术通过**。

本轮完成清单顶层身份和旧拒绝review两处实证补修，并实际读取四资料582成员标量，以正式装配/prompt消费者冻结完整输入。当前新包独立技术审查和真实答案质量仍open。`AUTHORIZED_GIT=None`，合同关闭，未创建正式实验、Run、checkpoint、派发清单或预留槽；无新供应商调用或本地推理。

## 启动核验与定向范围

启动只读核验：开发工作树干净，本地HEAD、origin及实际远程分支均07e92c2；本地main、origin/main、实际远程main均f49d06b；主区仅未跟踪tmp。未切换/合并main，未清理tmp，未启动或唤醒Agent。

实际读取07e92c2源码、最新报告/摘要、计划、方案及导航。复核限新profile的来源、登记前准入、清单/账本寻址、客户端、正式结算和恢复影响面，不重开既有关闭协议。三算法文件实际hash仍与17103bf独立结论匹配：`comparison_context.py`、`connection_semantics.py`、`comparison_answers.py`未修改。此前独立233离线/69隔离Mongo/56前端检查保留为历史独立证据，不算本轮验证。

## 实证问题与修复

1. **清单顶层未重算。** 原`require`核对清单hash和单成员文件，成员验证又只重算entry；修改`shared_control_database`并同步两个文件及请求hash仍可接受，可能将账本寻址转至另库。版本、批次、派发顺序、历史前值、重复entry也未在完整清单边界拒绝。12项写入前/恢复反例全部复现；补`validate_manifest`，在prepare写目录前及require读取后按专属授权重建完整清单。旧profile和CAS核心不变。
2. **旧账户拒绝review未检查。** 原检查已有blocked、结算和halt，却未检查账户reviews；缺review、改accepted=true或证据不匹配的3项反例仍被接受。现指定旧槽review必须为`accepted=false`且evidence与封存halt的source_review全等。测试只用只读合成端口，本轮没有读写真实旧账户；未来正式运行仍必须实际核验。
3. **完整输入有实际消费。** 新增`connection_048_production_input_v1`，逐成员校验完整标量、种子归属和正文，复用正式QueryRunner装配与prompt消费者；保存完整pool、问题输入、产品/计划、种子、分组、上下文、连续引用、装配身份、预算和精确prompt。新profile来源验证实际重装配整个anchor并核原题集输入，不接受仅重签prompt/result摘要或虚报已冻结。

清单反例使用deepcopy隔离夹具后的red-r2仍12失败；第一份red也保留。新输入模块未实现时15失败；输入消费者补测4失败。首次consumer-green为65通过/1失败，原因是缺production_inputs时直接抛KeyError；补显式版本/字段检查后66通过，原日志不覆盖。旧review红测为3失败/5通过。上述不隐去，也不将中间green文件名当通过证据。

## 实际完整输入冻结

首次在全新`output/m6-connection-comparison-048-input-r1/`执行4次Milvus Strong只读查询，逐个固定document/revision显式投影9个标量字段；不读向量、不读取private-identity、不消费MONGO_URL、不构建模型/Mongo客户端。全部582成员与原四资料快照及source_relations映射全等，不采用333成员投影。

旧review补修改变代码身份后，从上述完整保存标量在新`input-r2/`重放，新增实时查询0；原r1不覆盖。r2为**当前源码对应的最终冻结候选**：

| 项目 | 实际结果 |
| --- | --- |
| 原题集 | 完整150题，85 dev/65 heldout；仅dev support-v1-048 |
| 完整来源 | 4资料582成员，逐归属/正文/hash全等 |
| prompt上下文/引用 | 10文档，连续1–10，未省文档或历史 |
| 输入保守预算计数 | UTF-8字节上界10340，输入约束28416；不是供应商usage |
| prompt UTF-8 SHA256 | `9c1f2941f40f274aeba9d03453f5724c5ccea3135b7ab728f5c44af24319c2fe` |
| 完整标量/精确prompt状态 | full_scope_scalar_payloads_replayed=true；exact_production_prompt_frozen=true |
| 模型 | 保存指纹沿用，未重新hash权重或推理 |

种子、产品快照和query_plan明确来自hash绑定的封存r8 Run；本轮没有重新检索、编码或重排。原完整scope和582载荷均实际装配，不等于重放了完整检索运行。未来正式Run必须与冻结prompt/context/引用/groups/预算逐项相同；不相同则调用前拒绝，不能沿旧授权重抽。

当前可审阅的本机路径，无需用户填写：

- catalog：`D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.worktrees/m6-source-bound-comparison/output/m6-connection-comparison-048-input-r2/prepared/catalog/catalog.json`
- 独立持久输出：同级`prepared/execution/`；config_id/version仍`m6-connection-comparison-048-r1`/`connection-r1`，request仍`m6-connection-comparison-048-r1-request-01`。均未正式登记。
- 完整anchor：`output/m6-connection-comparison-048-input-r2/candidate-anchor-private.json`；精确字节：同级`prompt-private.txt`。
- r1旧catalog及其static-preflight保持历史原样；源码已变，其旧代码身份不冒充当前冻结候选。

入口`scripts/verification/freeze_m6_connection_048.py`默认首次实际只读，可用`--saved-rows`复放已保存完整标量；目录排他创建，既存即拒绝。工具失败保留中间文件和脱敏错误类型，不覆盖旧output。未新增环境变量或浏览器API。

## 最终自验及证据限制

| 检查 | 本轮实际结果 | 证明范围 |
| --- | --- | --- |
| 受影响离线/契约 | 257 passed；1条既有Pydantic浮点usage序列化警告 | 含新增35项、旧合同/客户端及OpenAPI一致性 |
| 新账本与既有连接正式Run | 72随机短m1_test_m4_隔离Mongo passed | 同/分库、并发、成功/失败/思考/断流/未知usage、恢复；模型及准入端口为合成 |
| 最终完整输入审计 | passed | 582全映射、4资料、10上下文、连续引用、精确字节与预算重算 |
| 当前catalog实际预检及服务拒绝 | passed；4组变异拒绝 | 缺授权仍在repo.create前422；题号/快照/合同/题集漂移拒绝 |
| 保存输入程序呈现 | 4事实/16span，qualified_medium_difference | 真实来源上的确定性renderer检查；使用空选择协议模拟输入，无模型答案/评分 |
| 三算法与固定r8配置 | hash匹配 | 保留已审结论，不扩为全库现场保护扫描 |

程序呈现保留两方完整连接条件、各自引用和客户端访问层次，限定比较可达；附加原文仍较冗长。它不是新产品答案、供应商能力证明或正式质量proof。本轮无前端行为变化，未重复前端整轮审计；未重跑此前独立233/69/56或旧风险66作为新证据。

私有证据：`output/m6-connection-048-input-freeze-20261103-r1/`，包含红绿XML/log、final-offline、final-integration、live-freeze-r1、final-freeze及audit-r1；脱敏机器摘要见同名validation JSON。原证据和原文不提交。

## 保持open的退出条件

- 新profile及本轮新增输入消费者、清单/旧review补修，需要未参与实现身份定向独立审查；本总控不能补签。此前算法独立通过继续有效，未唤醒原审查Agent。
- 本轮已完成完整生产输入冻结；正式运行前仍须重核实际来源、旧blocked账户、runtime/wire及独立comparison_generation_inputs持久输入锚。精确输入文件不等于该Run持久锚已写入。
- 本次新048调用尚未授权；专属Git授权、正式清单、实验/Run/槽仍不存在。技术通过也不产生调用许可；旧消费槽不能复用或解锁。
- 真实质量仍待新授权后的最多1个provider stream，有正常终止、完整自然语言限定比较、双方关系/条件/引用正确。仅列摘录或仅答无法判定不通过；不新增同用途/同角色、EoC或GM/GU字样门槛。

本轮真实资料标量查询4、真实业务写入0、新provider/本地推理/实际input/output增量均0。累计实际usage仍56239/30516；固定累计算术预算84655/34612不变，网关/付费硬限与费用上限unknown，reasoning明细/精确HTTP/费用继续null。未重扫867、默认指针、TTL、质量全库、原PDF或向量，不承诺发现所有问题。

M6保持5/7：04已验收；05缺真实反馈复评proof，08缺有效候选质量和阶段验收证据。原43题、heldout65、M7保持未启动；单题通过也不自动关闭05/08。提交和普通push在最终检查后进行，最终SHA见交付回复。
