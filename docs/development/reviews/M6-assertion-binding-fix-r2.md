# M6原句约束生命周期缺陷补修 r2

日期：2026-11-01，Asia/Shanghai。总控根据用户明确要求承担本包实现。**这是实现及自验记录，不是独立技术关闭。** 受审分支HEAD基线为`225e78cec843c2569c24885e31a09c3af9148eb7`。

## 卡点与修复

| 卡点 | 根因 | 修复与退出条件 |
| --- | --- | --- |
| R1 恢复未重绑冻结来源 | proof仅在当前保存的引用映射与文档间自洽核验；没有完整原始输入，也未用冻结payload重新派生映射 | Run额外保存完整`prompt_used_docs`；首结果投影／恢复时，用当前冻结归属策略重新运行`evidence_labels`，含source_relations的冻结payload hash校验，要求派生映射与持久映射全等，再核citation正文及proof。该原始输入进入`run_output`身份；协调改写原文、局部hash／frames／proof在创建outcome前拒绝，不追加调用 |
| R2 断流部分选择不落库 | 生成异常只在`AnswerGenerationError.partial_answer`中保留；QueryRunner失败分支未收到state证明 | assertion-binding生成异常时将最多4096字符原始片段、总接收长度、失败类别和prompt／映射／完整策略hash存入受控失败字段。QueryRunner沿原stage事件CAS持久化；运行仍失败，使用量缺失仍为null，不补0、不重发、不创建outcome |
| R3 空证据Run与评测投影不一致 | 零证据固定答案不经过模型绑定步骤，Run完成却没有answer_binding；新策略投影把缺proof视为损坏 | 加入`insufficient_evidence`状态proof，只接受精确既有不足证据固定答案、空映射、空引用；无需编号、不调用模型。Run、结果与outcome持久化同一proof。旧策略行为不变 |

R1在完整Run/outcome前投影时校验冻结配置；运行身份现包含被选择的完整原始文档，防止只改持久文档而保留旧proof。缓存结果读取仍对比当前配置与Run策略/hash。新Run负载仅在显式assertion_binding策略下保存完整prompt-used docs。

## 产品边界

这些修复解决的是生成结果生命周期、故障留证和零证据合同。`assertion_binding_v1`仍只能选择并展示完整原文；**不能组织048所需的双方上联比较**。技术修好不等于答案质量通过，新048仍未授权、旧消费槽与blocked账户不可复用。完整比较的受来源约束生成能力仍open，M6-05反馈复评proof及M6-08有效候选质量／阶段证据也未补齐。

## 验证

- 红测先行：冻结来源协调改写、零证据固定proof、断流部分片段，以及正式同／分库断流和零证据运行均按预期失败。
- 最终定向离线单元及OpenAPI：108 passed，包含严格选择、原映射／分页、恢复、旧身份和来源关系消费者。
- assertion-binding wiring及直接故障矩阵：16项随机短前缀隔离Mongo通过；包含正常成功／复用、协调改写在首次outcome前拒绝、同／分库断流留证与usage未知、同／分库零证据Run和结果均完成且0模型调用。
- 旧诊断输出合同、已消费048作业及来源关系消费者组合回归由最终日志记录，未改合同硬限／停止与旧默认。
- 旧错误日志保留：初轮单元在没有冻结source hash输入的最小用例未得到期望拒绝；后续补用完整prompt-used源载荷后定向通过。首次执行测试时使用了不存在的`test_execution_identity.py`路径，该命令未运行测试，改为实际存在的adapter及契约测试。
- 本轮最终复跑使用项目`.venv`：定向单元／契约／OpenAPI 108 passed；合规`m1_test_m4_`短前缀下隔离集成16 passed。两次前置探测错误也保存在本机：系统pytest缺少FastAPI而未收集测试，随后一个不符合M4目标命名的短前缀在Run创建前被目标校验拒绝；均不是业务回归，纠正后重跑通过。

本包未运行模型、embedding、rerank、真实数据全扫、真实业务库写入、43题或heldout。私有日志、随机库前缀和故障材料在`output/m6-coordinator-assertion-binding-fix-20261101/`，不提交。历史输入／输出累计保持53089／30412；reasoning、HTTP、费用null，网关限制与付费上界unknown。M6保持5/7；04保持，05／08未验收，M7未启动。

**下一动作：**由独立复核方仅定向检查R1／R2／R3最终路径及本报告源码差异，并分别确认技术修复与完整比较产品边界；不得把总控实现自验记作独立通过。当前无新048调用授权。
