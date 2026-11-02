# M6比较答复048风险合同与预算账本实现报告 r1

日期：2026-11-02

分支：`codex/m6-source-bound-comparison`

接续基线：`857a4dd`。本文件记录当前执行自验，不构成独立技术关闭、真实调用许可或答案质量通过。

## 本包范围

为冻结目录中的`support-v1-048`完整比较答复准备独立风险合同与单次预算账本。默认关闭；不修改catalog私有文件，因此其`output_contract`仍为`null`。没有新的专属Git授权时，风险档案拒绝正式实验准入、客户端构造和清单冻结，不会因为合同类型已注册而开放执行。

合同固定`diagnostic_comparison_answer_048_v1`、`n=1`、`qwen3.8-flash`、`openai 2.28.0`／`langchain-openai 1.1.11`、`max_completion_tokens=4096`、显式`thinking=false`。唯一成员为`support-v1-048`；账本collection、batch、ledger_id和成员slot均为此模式的新身份，不复用旧source-relation profile的风险合同、blocked账户或已消费槽。

预算以历史前值input/output `53089/30412`及有来源hash的receipt为起点，单次保守预留`28416/4096`，全量算术上限`81505/34508`。未知usage不估算为零，reasoning/精确HTTP/费用均可保留null；未知窗口、断流或账本pending永久阻止重领。账本复用现有CAS和started/settled封存方式，并使用专用collection身份。

## 修改范围

- 新增`app/infrastructure/providers/comparison_answer_048_risk.py`：固定身份、runtime/预算/历史receipt验证、输入与配置绑定、单一成员manifest、旧blocked账本只读核对和CAS账本profile。当前`AUTHORIZED_GIT=None`为显式硬门。
- 修改`app/infrastructure/providers/output_contract.py`：新增严格Pydantic合同/准入、注册解析器和专属risk_handler/OutputLedger路由。
- 修改`app/answering/service.py`：`AnswerBudget`接受显式关闭的专用合同类型，避免策略反序列化丢合同。
- 修改`app/evaluation/service.py`：risk档案验证错误转换为既有稳定`422 comparison_admission_required`，写experiment/slot之前拒绝。
- 修改`app/runs/query_runner.py`及`app/query_process/agent/nodes/node_answer_output.py`：保留这类Run的正文、截断/finish reason及非思考reasoning观测供账本结算。
- 新增`tests/unit/test_comparison_answer_048_risk.py`、`tests/integration/test_comparison_answer_048_risk_jobs.py`；扩展`tests/unit/test_comparison_experiment_admission.py`。

公开API、OpenAPI schema、默认模型配置、环境变量、catalog配置和答案策略默认值均未更改。

## 验证结果

- 相关合同/比较渲染/旧风险单元集合：提交前在当前工作树重新运行9个相关单元模块，`164 passed`，1条既有Pydantic序列化警告；含新增旧048账户collection与快照hash反例及Git授权核验超时失败关闭反例。
- 比较账本随机隔离Mongo：`5 passed`，覆盖同库与分库、精确reserved input/output、CAS并发单赢家、settle后不重领、unknown usage/中断后blocked、不虚构HTTP/费用。
- 旧比较Run接线与source-relation 048联合随机隔离Mongo：`47 passed`，含成功、恢复、空选择、断流与无效选择路径。
- 提交前重新运行上述三组隔离Mongo模块：合计`52 passed`（新账本5项＋旧接线47项），使用随机`m1_test_m4_`库前缀。首次启动因工作树测试夹具未找到仓库根`.env`而在测试体前报`MONGO_URL`缺失、未写库；随后在测试进程内静默加载仓库根配置后通过。前置失败摘要保留在本机私有输出目录。
- 初始合同RED：`2 failed, 1 passed`；已按预期暴露尚未注册的新合同类型和解析路由。
- 旧账现场核验RED：新增反例发现风险档案误查非思考账户collection；修复为绑定source-relation 048专用collection、planned SHA、snapshot SHA、settlement内容及固定slot，目标单测通过。
- 授权核验超时RED：新增反例发现service未将Git读取超时转换为稳定准入错误；修复为`422 comparison_admission_required`且不创建slot，目标单测通过。
- OpenAPI契约检查：`2 passed`；`compileall app`与`git diff --check`均通过。
- 失败/恢复台账及命令环境说明留本机`output/m6-comparison-answer-risk-20261102/`，不入Git。早期隔离测试和旧比较联合测试的前置启动错误与复跑修复均保留，不作为业务通过或仍未修复缺陷。

## 状态判定

**实现项可交独立复核：**新合同严格默认关闭、固定profile/预算与新身份路由、单槽CAS结算、分库寻址、未知usage/失败永久阻断重领、service在创建前失败关闭。

**未关闭：**实现自验尚无独立总控复核；没有新的已审Git授权或冻结运行manifest；正式比较配置仍是`output_contract=null`，无法派发。授权未来生效时必须由Risk档案单独增加完整受审Git授权并重算manifest/预算/模型/代码hash，不能把当前静态固定值视为准入。

**质量仍缺：**未产生真实比较回答，未判断答案是否先给比较结论并正确区分设备上联与客户端访问、管理连接及排障检查。完整原句摘录不是完整比较答案。本包没有质量校准、candidate、M6-05/08 proof或阶段验收证据。

真实模型、stream、供应商HTTP、正式experiment/slot/Run/评分/proof及真实评测库新增写入均为0。本地模型权重目录不可用、model fingerprint未重算。历史累计usage `53089/30412`不变；reasoning、HTTP、费用及供应商付费输出上界继续unknown/null。

M6保持5/7：M6-04保持已验收；M6-05缺真实反馈复评proof；M6-08缺有效新候选质量与阶段验收证据。43题继续暂停，heldout 65题未运行，M7未启动。
