# M4 总控独立审查 · 首轮

日期：2026-10-25。审查对象：`e7571e32a86f309348b6c305d1a51bd76b3b75fd`。结论：**需修复，存在一项P1阻塞R1；不进入M5。**

独立读取[阶段提交](M4-submission.md)、任务计划、正式实现、评测适配器、冻结配置、原始实验及[实验报告](../../evaluation/retrieval-report.md)。接受已披露的执行范围、语义缺漏和计量限制；发现“候选合并后按拼接顺序截断”的确定性缺陷，既损害跨型号取证，又使成功增强的新增证据无法参与重排，不能仅作为模型回答质量波动接受。

重开M4-03、M4-04、M4-05、M4-10；当前M4 **6/10**、核心 **49/76**，可选0/2。其余六项保留完成，旧10/10为执行提交时点。仅继续M4修复和复审，M5及后续未授权。本轮只改审查与状态文档，不实现业务修复、不改默认策略、不启动新付费实验。

## R1 · P1：合并候选按顺序截断，后续产品与增强分支被排除

主位置：[rerank.py](../../../app/retrieval/rerank.py)第8行；相关实现：[search.py](../../../app/retrieval/search.py)的逐范围拼接、[graph.py](../../../app/retrieval/graph.py)第75–76行的local→hyde→decomposition拼接，以及[adapters.py](../../../app/retrieval/adapters.py)的保序去重。正式[QueryRunner](../../../app/runs/query_runner.py)第197行与[QualityExecutor](../../../app/evaluation/quality_grid.py)第101行共用此逻辑。

每个产品/查询可返回fusion_limit条；去重保留首次出现顺序，随后直接取`candidates[:rerank_limit]`。默认两项均为20：第一范围有20条时，第二范围即使有关键证据也不会送入重排；本地有20条时，成功HyDE/分解新召回的唯一证据同样没有机会。现有比较测试每型只给一条，HyDE入口测试让本地为空，没有覆盖正常满池情况。

独立使用正式`RunService.create→QueryRunner.execute`、真实隔离Mongo及注入索引/模型复现；不调用供应商。三个测试均在预期业务断言失败，运行31.22秒、退出1，无收集/夹具错误：

| 场景 | 实际结果 |
| --- | --- |
| 两个已确认型号各召回20条 | candidates=40，rerank输入=20，仅1个型号，最终仅1份资料引用 |
| 本地20条，HyDE成功新增关键证据 | 分支completed，candidates=21，rerank=20，新增证据未进入重排/引用 |
| 本地20条，有限分解成功新增关键证据 | 分支completed，candidates=21，rerank=20，新增证据未进入重排/引用 |

真实证据也对应此缺陷：dev `support-v1-048`规划compare/两个scope，两份资料各20条候选，但重排只含一份资料20条、引用一份，来源组覆盖0.5。dev网格`support-v1-036`的HyDE在7.421秒内completed，候选从20增到28，重排仍20条；其重排缓存key与control完全相同，说明实际输入相同。四份根因源码与冻结执行字节完全一致；不以当前工作区推测历史实验行为。

**修复与验收要求：**在全局数量上限内明确跨范围/查询/分支的候选选择或融合规则，使后续范围与新增证据能够竞争重排机会；比较场景需保留每个有有效证据的已确认型号的取证机会。不能只反转拼接顺序、放大默认数量，或依靠最后的“资料不足”文案掩盖已召回证据丢失。保留稳定身份、权限/活动修订、原始正文与分阶段分数边界，不把不同分支原始分数直接当同一量纲比较。

先将三个独立反例转成正式红测，再修复；覆盖两型满池、交换范围顺序、重复/唯一候选、HyDE和分解单独/组合、超时降级、全局上限，以及正式入口和QualityExecutor一致性。新唯一证据进入重排即可证明接线，最终引用仍由实际相关性与预算决定，不要求每条增强证据都被引用。

M4-10须更正此版本的实验解释：来源覆盖数值和调用记录原样保留，但不能以本次HyDE与control结果相同证明增强经过有效比较后没有收益。修复后冻结新代码/配置/新输出，先在dev和合成反例验证候选合并及单因素比较，再重交；无需承诺提升、开启增强或增加默认候选量。

15道heldout已曝光，原输出保留为旧版本最终评价；不得据其答案调参，再把相同15题称作新版本未见最终评价。必要的旧题复跑应标回归；若要主张修复后新的盲测结果，须另冻结未用于修复/选择的新测试集。没有新增付费结果时如实保留未验证边界，不复制旧结果充当新版本运行。

## 独立验证与证据边界

| 检查 | 独立结果 |
| --- | --- |
| 提交快照，修改总控文档之前 | 134文件hash、80份Python语法、306个本地链接及登记原始证据通过，退出0 |
| 完整后端阶段回归 | **698 passed、2 deselected、0 skipped、7 warnings，682.01秒，退出0**；456单元/115契约/127集成目录用例；包含后补接线，不重复累加4项 |
| 前端 | 37单元、24离线浏览器通过；typecheck/build退出0 |
| 既有重导入 | 3 tests OK，1.539秒，退出0 |
| 当前35dev产物只读 | 33完成/2澄清、68消息、23引用图片完整解码，引用/事件/修订/语料通过 |
| 当前15heldout产物只读 | 14完成/1澄清、31消息、19引用图片完整解码，引用/事件/修订/语料通过 |
| 总控交付文档 | 7文件、236本地链接、敏感值扫描通过；49个核心/6个M4完成勾选核对一致 |
| 独立满池反例 | 3项业务断言失败，退出1；作为R1证据保留 |
| 实验关联分析 | 真实048/036、策略指纹/开发报告hash、运行创建时序、4invoke+47stream及四份冻结源码核对通过 |

后端使用独立`M1_TEST_DB=m1_test_m4_control_review`，命令`.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -m 'not live_provider' -q --junitxml=docs/development/evidence/M4-review-stage.xml`。集成目录含真实存储、Linux worker及模型端口注入，不能统称供应商端到端。前端依次执行`test:unit`、`typecheck`、`build`，构建结束后执行`pnpm -C frontend test:e2e`；24项使用实际浏览器配协议模拟/合成PDF，非新增真实API浏览器。未模拟身份接口产生既有8000代理拒绝日志，不计为真实后端验证。

只读核验分别显式选择`evals/configs/m4-10-dev-control.yaml`与`m4-10-heldout-control.yaml`，配对应`output/evals/support-v1-r2-m4-10-*-control`，使用`scripts/verification/recheck_m4_evaluation.py`写新报告。前后语料均为`dd01944db688807c158923c0d21d272f1f45aa4304aa9012efada71c2c18b810`，不加载模型、不生成答案。原M3只读8项是提交证据的历史部分，本轮不冒称重新执行。

独立分析确认选择记录为北京时间2026-10-25 02:42:45，35dev最后创建02:41:30，15heldout首次创建02:43:18；选择绑定的开发报告hash和heldout策略指纹一致。本轮未发现使用heldout选择策略的证据。原实验实际逻辑调用为4次invoke与47次stream，不含历史基线34次；HTTP重试次数/金额未知。本轮新增模型/付费调用 **0**。消息/来源命中和执行成功不能代替答案语义正确率，人工正确率保持null；已披露004/006/009/019等缺漏不因常规测试通过而被抹去。

脱敏汇总见[M4-review-validation.json](M4-review-validation.json)。独立反例本机入口为`output/evals/test_m4_control_starvation.py`，以`M1_TEST_DB=m1_test_m4_control_probe`运行pytest；实验关联脚本为`output/evals/m4_control_analysis.py`。原始JUnit、控制台、探针、只读报告及hash仅本机`docs/development/evidence/M4-review-*`，不上传。原提交/快照/失败证据、evals及课程数据保留。下一动作是开发会话在M4内完成R1红绿与受影响实验说明，提交`M4-submission-r2.md`供复审。
