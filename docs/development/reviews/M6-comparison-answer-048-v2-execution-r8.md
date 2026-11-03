# M6-048 comparison_answer_v2 单题执行与质量复评

日期：2026-11-03。授权：提交`fc656db374d13a55f6904bebd5936055f5861b1c`；执行源码：`e15adf3a7ee04d012c157597f885c0670667f666`。本报告记录一项真实provider执行和协调端质量复评，不构成不同执行身份的独立技术验收或M6阶段验收。

## 结果

新批次`m6-comparison-answer-048-risk-r8`、槽`m6-comparison-answer-048-r8-support-v1-048`仅执行冻结题集`fb-07c584730833908571fe9dd7c7c890afa3cf9e66`中的`support-v1-048`。模型为`qwen3.8-flash`，实际单一provider stream。r7已消费槽、blocked账户、结算与质量拒绝停止证据均保持不变。heldout 65题及原43题未运行。

真实Run与experiment技术执行完成，唯一结果和outcome落库，v2 proof从正式Run恢复并重算成功；模型原始选择、程序补入帧和最终呈现帧身份一致。答案区分了客户端接入、管理连接和Cable排障检查，避免把三者作为设备上联关系。但回答仍判断比较证据不足，没有提供题集冻结rubric要求的“CB304n融合Cable和无线路由，Cable上联”这一关键点。因此产品答案质量复评拒绝；没有把evidence insufficiency降格算作正确比较。

## 计账与停止

- r8新增usage：input 1575、output 67；此前累计54664/30449；累计56239/30516。
- 本机BGE-M3已加载并实际生成查询向量；本地推理发生。精确reranker推理次数没有可靠计量，保持unknown。
- reasoning明细、精确HTTP请求数、费用、网关硬限制及付费输出上界保持unknown/null。
- 正式风险账本经settle、review(accepted=False)及halt收敛为blocked；预留1、结算1、review 1、pending为空、unknown窗口为0。没有重试。
- `execution-summary.json`初次投影未包含run_id；随后通过正式checkpoint execution link只读定位Run并完成proof复算，原摘要未被覆写；最终Run ID保存在私有复核材料中。
- 正式实验/Run/outcome及账本写入为执行和结算所需；真实调用后审计为只读。没有改写r7或其他历史Run/lease/slot。

## 验证与限制

调用前离线冻结通过：单题、10个冻结上下文/引用项、题集及prompt哈希一致，唯一策略变化为`comparison_answer_v2`；provider requests、正式Mongo写入和本地推理均为0。调用前正式只读预检确认已登记题集、维护权限、r7停止状态正确，r8 experiment/result/account/checkpoint/link/outcome不存在。

代码回归：1397单元/契约通过，保留6条既有警告；相关隔离Mongo集成36通过。第一次隔离测试因命令错误使用`m1_test_m6_`而有22项目标库拒绝、14项通过；按项目要求改用`m1_test_m4_`随机短库名后36项全部通过。该初轮失败属于测试前置命令错误，不是业务阻塞，也不从结果中删除。

产品边界仍开放：当前冻结帧分类将Cable材料识别为诊断检查，不能从其当前结构化含义推出已建立的设备上联；题集rubric却要求比较答案报告CB304n的Cable上联。r8真实输出证明当前v2方案仍无法完成该产品问题。下一包唯一目标应是复核并补齐“文档明确说明的端口/接入介质与诊断状态之间的关系表达”，在独立保存输入上证明能给出有来源的逐产品完整比较，同时保留条件、避免把诊断现象写成现场已验证状态。不得改评分门槛，不得重试本槽或再次调用048替代该边界工作。

M6仍为5/7：04保持验收；05缺真实反馈复评proof；08缺有效候选质量和阶段证据。heldout未运行，43题保持暂停，M7未启动。真实v2质量验证未通过，不能作为候选质量或阶段验收证明。

脱敏机器摘要见[M6-comparison-answer-048-v2-execution-r8-validation.json](M6-comparison-answer-048-v2-execution-r8-validation.json)。原始答案、Run、账本、日志仅保存在本机`output/m6-comparison-answer-048-execution-r10/`，不进入Git。
