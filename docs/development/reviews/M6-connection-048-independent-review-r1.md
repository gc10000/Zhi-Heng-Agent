# M6连接048新准入与完整输入包独立技术复核

2026-11-03。审查者为用户明确授权、未参与实现的独立Agent；未再委派。范围是`17103bf`之后的`07e92c2`、`53ecbaa`及本次总控补修。最终Git HEAD仍`53ecbaa12eb5f06a2cc7524f4cf0643ec3914b57`；结论绑定同名JSON的`final_candidate`文件hash及下列当前代码指纹，包含尚未提交的合同校验补修和6项实现回归。未改业务源码、已有测试、Git index/HEAD或导航，未提交/推送。

**独立技术结论：通过，限本报告实核边界。** 初始版本存在一项有两个表现的准入缺陷，现由实现总控补修，原审查者反例复测关闭；没有尚未关闭的实证技术问题。该结论不授权新048调用，不代表真实答案质量或M6阶段验收。

## 独立发现与补修复测

R1／P1：`connection_comparison_048_risk.validate_candidate`用期望合同整块覆盖实际合同，跳过合同冻结字段的差异检查。`sources`随后只将实际policy与anchor合同比较；协调修改端点hash或历史计量来源hash、重新装配anchor并同步模拟Git授权中的anchor/result/prompt摘要，两项均仍能准入。未来可能接受超出原r8允许差异的端点或历史来源。当前`AUTHORIZED_GIT=None`仍阻止真实派发；并非已经发生未授权调用。

独立探针在`output/m6-connection-048-independent-review-20261103-r1/test_independent_admission.py`。最初未重装配的两个变异被拒绝；完善为协调重算后`probe-coordinated`实得2失败，不能用初版2通过掩盖缺陷。已立即将复现和根因交总控。补修只正规化`enabled=False/admission=None`，其余合同字段按固定候选全等比较；`sources`另要求anchor完整配置本身严格等于关闭模板。独立原2项修后通过；实现侧新增6项也纳入本次最终独立回归。未由审查者自行修复。

## 实核范围和证据

阅读AGENTS、Git流程、最新进度/授权/合同、方案、两份实施计划和报告，并实际审阅新profile、合同路由、登记前准入、完整输入模块、准备/冻结脚本、AnswerBudget/InternalRunInput、生成节点及QueryRunner结算。定向追踪继承的Remaining/Nonthinking账本、客户端wire、正式job、execution link、检查点和比较输入持久锚。旧三算法hash仍与17103bf独立报告完全相同，保留其既有关闭；未整体重开旧AnswerFilter、图片、continuation或001消费协议。

| 独立实际执行 | 结果与证明范围 |
| --- | --- |
| 最终离线/契约 | **324 passed**，0失败/错误/跳过；含原/新风险合同、登记前拒绝、清单顶层变异、旧review只读变异、输入重算、安装SDK及OpenAPI一致性 |
| Mongo正式/恢复回归 | **96 passed**；随机短`m1_test_m4_`合成库，同/分库，CAS并发、未知usage、思考、断流、单Run与检查点恢复；来源/模型/授权端口明确为合成 |
| 独立磁盘故障探针 | **4 passed**；同/分库调用前started写盘失败仍保留唯一pending，禁止重领；DB结算后写盘失败只能以相同receipt恢复，变更receipt拒绝，磁盘未补齐不能review放行 |
| 独立新profile wire探针 | 原2项补修复测＋7项wire共**9 passed**，已包含在324内；实际安装SDK＋内存MockTransport核`n=1`、4096、thinking=false、stream usage和字段落wire，拒绝重试/重定向/额外参数/温度/Responses漂移 |
| 当前r3完整输入强化审计 | **2 passed**，也包含在324内；最终又单独运行加强版2项，通过当前code/prompt/catalog、原题输入及实际EvaluationService在repo.create前拒绝 |

各组有重叠，不累加为唯一总数。此前独立305离线已通过，最终扩为324。首次离线命令误用`tests/contracts`目录导致未收集测试，随后修正；原日志保留。`saved-r2-audit`首次包含1个实质完整输入检查及1个尚待r3的占位返回，不把它写成两个实质审计；最终2项r3强化检查均实际执行。仅有一条既有Pydantic浮点usage序列化警告。全部XML、日志、探针及hash保存在全新上述output目录，同名JSON记录准确结果；没有借实现自验数量充作独立证据。

## 当前生产输入与默认关闭核验

当前候选是`output/m6-connection-comparison-048-input-r3/`，r1/r2原样保留。独立读取并重装配完整pool/anchor，逐项核原r8保存Run的seeds、query_plan、groups及产品快照；题目仅4个正式输入字段，与原完整题集同一dev048完全相同。完整四资料582成员、修订集合和快照映射一致；未用333双资料投影补签。

- 当前完整代码指纹：`c6fc212e2ea3659114a42614af22f5efae83e792f193abbffc6d533cc4d0ca38`。
- r3 anchor文件SHA256：`a7b4a0870c9acf26b9e232058e2f4d82434187ddde29a52461df6f27435555be`。
- r3 config subject：`9076d71348eb97b4072e963cab7822a00d7366af5c01bd6026bb3bb78556c180`。
- prompt字节SHA256：`9c1f2941f40f274aeba9d03453f5724c5ccea3135b7ab728f5c44af24319c2fe`；与r2相同。result摘要亦保持。
- 10份上下文、连续引用1–10；保守输入10340／28416，无省略文档或历史。该计数不是供应商usage。

实际`preflight_catalog`通过，150题85/65及唯一dev048、原配置来源和全scope得到消费；实际服务缺授权时在创建实验前拒绝。`AUTHORIZED_GIT`确为None，本地本批正式planned清单不存在；审查者未生成授权、清单、正式Run或预留槽。正式Mongo不作全库扫描，因此不将本地文件缺失扩大为全业务库对象计数证明。

## 有界结论及仍未验证项

新合同/旧合同按生成模式配对，默认关闭、不借用r8消费槽；完整清单顶层身份、独立collection/key和控制库寻址、唯一预留/幂等结算/失败不退款以及精确prompt/context/引用/groups/装配身份均有源码与反例证据。旧账户blocked、唯一settled及拒绝review一致性的校验代码已审，合成只读端口实际通过；新授权的正向来源消费使用合成证据，不存在本轮新真实授权Git。

本轮未重新读取真实资料、运行编码/重排/模型或调用provider；仅静默取得Mongo连接配置以连接随机隔离合成库，无删库/删集合。保存pool和来源hash可独立重算，但历史4次实时Strong查询不是本审查者现场见证，不冒称本轮重检索。未核新权重、真实Milvus/vector当前状态、真实旧blocked账户或付费网关；MockTransport的一次合成HTTP不等于真实未来恰好一次HTTP。

未来有新明确单题授权后，调用前仍须实际核来源/旧账户/runtime/wire，并成功写入独立`comparison_generation_inputs`持久锚。断流、异常结束、非法选择、漂移或质量拒绝仍应停止，不解锁/重试/换槽。真实完整自然语言比较质量仍open，技术审查不替代真实答案证明；不增加同用途/同角色或EoC/GM/GU字样门槛。

归档累计usage仍56239／30516，逻辑预算上界84655／34612；费用、reasoning明细和精确HTTP为null，硬限unknown。M6仍5/7，04既有验收保持，05反馈复评proof与08候选质量/阶段证据open；43题暂停、heldout65和M7未运行。
