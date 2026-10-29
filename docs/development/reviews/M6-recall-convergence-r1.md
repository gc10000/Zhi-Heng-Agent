# M6 C05/C06/C07：真实召回收敛执行 r1

接续 `8060abb40af33abd7f13fcd2221630f82ad303fe`，开始时 HEAD、origin/main、GitHub main 一致，仅未跟踪 tmp/。保留 C03/C09/C04 及 AF/SQ 等既有独立通过结论。本轮新增投影接线为执行自验，未自行关闭新审查或验收 M6。

## 实际结果与边界

同25题真实索引、既存向量、本地真实重排及最终 prompt 对照，沿原必要摘录口径由 **22/25 到24/25**，原21题及019均保留；新增改善021、022。正式源码再用同批缓存回放25题，新增模型调用0，结果相同。不是答案正确率，没有生成新答案。

021/022 必要正文不含显式型号，旧稀疏排名8/7的正文在 weighted 融合池被排除，含型号的管理计算机内容靠前。隔离将已由产品过滤确定的型号词转换为“该设备”，功能、版本及原问题不改，实际使两题必要正文通过候选、真实重排和上下文预算。这证明对检索文本的敏感性，不推断模型内部注意力因果。

源码新增 `query_projection=scoped_subject_v1`，默认 `original`。仅对已确认 answer/compare 路径投影；产品授权过滤、原题、生成问题、重排问题不变。配件名、登记完整版本变体、代码/尖括号/多行、无法可靠映射的 Unicode 坐标保留原查询。没有题号分支、固定答案、额外查询、RRF、扩大 top-k 或放宽阈值。QueryRunner 与无答案 RetrievalExecutor 消费同一版本函数，完整策略和查询计划参与原配置/缓存身份；不同源码配置不继承旧19检查点。来源前提允许该显式组合，其他 weighted/预算约束保持；关闭须使用新配置 original，不改旧 Run 或默认修订。

**048未改善。** 必要正文 ordinal268、物理30页的同轴/EoC仍未进入候选；新查询全量既存向量IP排名 dense198/sparse42，旧诊断129/36。新候选包含CB304n，但重排前10最终只剩LA2608。“必要正文未召回”和“比较上下文失去一方”分别记录，后者不能解释前者。语义低排细因未知，不用加大邻接窗口或复制原文掩盖。下一次只围绕该固定候选/分数验证双方上下文保留及必要正文召回，保留原24题。

## 逐题结果

下表均指既定必要摘录是否完整到达；不是操作充分性或答案质量评分。

| 题目 | 相对22/25 | 候选必要摘录 | 最终上下文必要摘录 |
| --- | --- | --- | --- |
| support-v1-003 | 保留 | 全部 | 全部 |
| support-v1-004 | 保留 | 全部 | 全部 |
| support-v1-006 | 保留 | 全部 | 全部 |
| support-v1-007 | 保留 | 全部 | 全部 |
| support-v1-008 | 保留 | 全部 | 全部 |
| support-v1-009 | 保留 | 全部 | 全部 |
| support-v1-010 | 保留 | 全部 | 全部 |
| support-v1-019 | 保留 | 全部 | 全部 |
| support-v1-020 | 保留 | 全部 | 全部 |
| support-v1-021 | 改善 | 全部 | 全部 |
| support-v1-022 | 改善 | 全部 | 全部 |
| support-v1-034 | 保留 | 全部 | 全部 |
| support-v1-037 | 保留 | 全部 | 全部 |
| support-v1-038 | 保留 | 全部 | 全部 |
| support-v1-048 | 未改善 | 缺必要摘录 | 缺同轴/EoC |
| m6-g540-02-a | 保留 | 全部 | 全部 |
| m6-g540-02-b | 保留 | 全部 | 全部 |
| m6-g540-04-a | 保留 | 全部 | 全部 |
| m6-g540-04-b | 保留 | 全部 | 全部 |
| m6-g540-05-a | 保留 | 全部 | 全部 |
| m6-g540-05-b | 保留 | 全部 | 全部 |
| m6-g540-17-a | 保留 | 全部 | 全部 |
| m6-g540-17-b | 保留 | 全部 | 全部 |
| m6-g540-18-b | 保留 | 全部 | 全部 |
| m6-g540-20-a | 保留 | 全部 | 全部 |

完整原件依据、旧判断、候选、重排输入/输出、上下文、物理页码及预算可直接阅读本机 `output/m6-recall-convergence-20261029/25题真实检索与来源对照.html`。原85题及25题判断保持 assistant-side 身份，不转为本次 human 或独立双轮。四题04-a/05-a/05-b/17-b只有上下文证据，新答案效果仍未证。

## 身份、模型与调用

实际 Mongo/Milvus 隔离目标均为 `m1_test_m6_sq5_aad3135569bb44baaaf8f786cea680fd`，四修订及582条既存索引不重建，67图摘要在检索前排除。BGE-M3 CUDA fp16、bge-reranker-large CPU fp32；全部本地文件重算匹配组合 SHA `3995645af911d30aa3ec13c90c61919bfe52830a0611f3f3820b6097062520fc`。完整修订、源码/prompt、模型、参数、题目、缓存身份保存于 `comparison-config-identity-v2.json`，没有将对照配置称为最终正式实验配置。

新增本地查询编码16次、逻辑重排9次、69个新pair，其余pair复用既存缓存。缓存键绑定模型文件/设备/runtime/完整输入，started先落盘、结果保存hash；全部started均有completed，未结算窗口0。token、精确HTTP、费用保留null。供应商调用0、新答案0；正式源码25题回放新增模型调用0。

中间失败保留：首次私有执行器误读空products集合，25题实际未投影；其结果无效，保留日志后在新目录改读knowledge_products。有效对照048第二scope复用缓存时，JSON稀疏键int转str导致hash校验退出1；未改缓存，恢复脚本按既存规范还原int键再校验，复用completed结果，未重复编码。首次比较口径漏去Markdown反斜杠使020假阴性；最终采用既存analyze.py去空白/反斜杠/表分隔符口径，22→24以最终同口径结果为准。补充Unicode扩展/组合抵消反例1失败；中间直接跳过所有NFKC变化输入使普通中文标点过度保守，194通过/2失败并保留日志，最终逐字符一一映射及整体拼接等价检查196通过；25题投影计划与已存真实结果一致。文档生成脚本首次引号嵌套语法失败，未写历史材料，改为独立文件后完成。

## 真实反馈实际写入

两条反馈各经正式 `RegressionService.candidate()` 创建一个完整001题目标注候选，并重复调用核验幂等；原 completed/awaiting_input 来源及授权补充修订分别固定。只在两个原控制库的regression_candidates各新增1，没有修改原feedback/Run，没有写annotation/binding/proof，没有创建答案评测候选、评分、观察或校准。详见[真实候选及部分映射记录](M6-05-real-regression-candidates-r1.md)。

001只对应版本内兼容性与简称；未知型号路由、旧human/图片用途要求仍单列。正式独立标签审核须另一实际执行者按固定candidate及evidence_mapping hash核验，并提交受控产物。本轮只读确认两个控制库只有原维护者账号，不改角色、不制造独立身份、不由作者自签。由执行/总控安排实际独立标签审核后继续annotation→必要派生→binding，不新增用户重查PDF或逐题填写任务。

## 实际验证

完整原始命令、退出结果、JUnit与失败日志在新output目录；各组重叠不累计唯一总数。

| 命令（均使用 `.venv/Scripts/python.exe`） | 结果／退出码 |
| --- | --- |
| `-m pytest tests/unit/test_scoped_subject_query.py -q --junitxml=output/m6-recall-convergence-20261029/projection-red.xml` | 实现缺失红测15失败，退出1 |
| `-m pytest tests/unit/test_scoped_subject_query.py::test_retrieval_executor_consumes_projection_instead_of_silently_ignoring_it -q` | 未接线红测1失败，退出1 |
| 投影、计划、策略、前提首组 | 97通过，退出0 |
| `-m pytest tests/unit/test_scoped_subject_query.py tests/unit/test_query_plans.py tests/unit/test_manual_evidence_integrity.py tests/unit/test_retrieval_policy.py tests/unit/test_retrieval_provenance.py tests/unit/test_retrieval_grid.py tests/unit/test_retrieval_graph.py tests/unit/test_source_prerequisites.py tests/unit/test_source_prerequisite_wiring.py tests/unit/test_prerequisite_contract.py -q` | 最终196通过，退出0，5条既有SWIG弃用警告 |
| `-m pytest tests/integration/test_scoped_subject_run.py tests/integration/test_source_prerequisite_run.py tests/integration/test_query_planning.py -q`，环境 `M1_TEST_DB=m1_test_m4_rc` | 随机隔离Mongo32通过，退出0；合成索引/供应商，不是质量证明 |
| 新目录 `compare_v2_resume.py`、`formal_replay.py`、`diagnose_048.py`、`no_generation_preflight.py` | 均退出0；真实检索/缓存重放/只读诊断，无答案生成 |

最终Unicode收紧后另重跑正式开关/恢复2项通过，退出0（与32项重叠）；新反例、所有中间失败均保留。前端未改，不无理由重跑浏览器/类型；OpenAPI只读比较与冻结JSON一致；四修订582条完整载荷/向量逐条匹配原snapshot，25题原始分路补取与回放候选完全一致，均零新增推理。原821/404/294保护清单全部匹配；独立与冻结非TTL集合前后hash一致，run_events TTL单列，不声称历史22集合全部未变。r3仍19继承+66执行、历史stream19/新61及HTTP/费用未知；旧失败仍failed/attempt2/provider_invalid_response/retryable=false/results0，调用费用未知。

## 正式验收依赖与下一条动作

| 子项 | 本轮已满足 | 未满足及执行责任 |
| --- | --- | --- |
| M6-04 | 已批准政策实现、既存原件分析、本轮上下文取证 | 最终题集/配置未冻结；执行方完成实际独立assistant双轮、总控确认独立性后预校准；human发布另计。 |
| M6-05 | 两条真实完整题目候选、授权补证映射、正式服务幂等 | 不同执行者独立annotation、必要版本派生/绑定及有序真实复评proof尚缺，由执行/总控安排。 |
| M6-08 | 021/022真实改善至24/25且原21/019保留 | 048召回、比较双方上下文仍缺；四题对象/配件新答案效果、同范围独立候选质量仍待正式链。 |

无生成预检明确 `ready_for_generation=false`；只固定对照身份，没有登记真实政策、实验或最终配置。**下一条动作由执行方承担：基于本轮048固定候选/分数完成双方上下文与必要正文召回对照；独立标签执行者并行消费两条已持久化候选。两前置满足后一次冻结最终题集/config，再走有效基线双轮→预校准→独立候选→反馈proof。** 不跳过前置调用答案供应商，不要求用户重新判断。

M6保持4/7，04/05/08未验收，M7未启动。代码自验、真实检索到达、助手原件分析和正式质量证据分别记录。
