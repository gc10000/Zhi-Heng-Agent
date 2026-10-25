# M4 第二次执行提交 · R1候选截断修复

2026-10-25，Windows/PowerShell/已有.venv，main。状态：**执行自验10/10，待总控复审；M5未授权。** 基线881c98a（含总控522ec33）；修复2b06ee32e8c3ac167505dcafa575434cd4b1d58c已正常推送核头，验证接续a25b1f591cfb556e6297cd23e9ab5c49f3d0e584也已推送核头；本材料提交SHA在最终交接补记。原[首轮提交](M4-submission.md)、[总控审查](M4-review.md)及其快照/失败证据保留，不覆盖。

## R1回应及行为变化

恢复M4-03/04/05/10执行自验；无未完成的M4任务。先正式红测，再最小修复：`app/retrieval/search.py`增加池内rank/范围/查询追踪；`selection.py`按范围→分支/查询分层轮转；范围内共享身份由规范首池供给，所有追踪保留；`rerank.py`统一使用该规则。`quality_grid.py`保存实际rerank_inputs，正式QueryRunner与评测共用选择。不同分支原始分数不直接混比，默认20全局重排量不变；来源/原文/权限/活动修订及最终预算边界保持。非空范围多于上限时先拒绝，不能静默漏取或扩大上限。

| 场景 | 修复前正式反例 | 修复后证据 |
| --- | --- | --- |
| 两型号各20及交换顺序 | 第二范围从重排消失 | 正式入口/Quality一致；20内每侧10，原真实048重放及新dev048核对 |
| local20+HyDE新增 | 分支成功但唯一证据不进重排 | 单独/组合/重复前缀正式与离线覆盖；新真实dev035组合组6新增全入20，原真实036重放8新增全入20 |
| local20+分解新增 | 分支成功但唯一证据不进重排 | 正式入口新增证据入重排，独立/组合/多查询/重复及超时降级覆盖 |

先反转拼接或单纯扩大候选数均未采用。单范围单查询保持后端次序；全局复合身份只占一次，rank-only池标记不伪造模型分数。新唯一证据获得重排机会不等于保证最终引用。

## 实际验证与证据

| 检查 | 本轮实际结果 | 证据 |
| --- | --- | --- |
| 三个正式业务红测 | 3 failed，22.78秒，退出1；无收集/构造错误 | 本机evidence/M4-r2-entry-red.* |
| 边界正式红测 | 11 failed/4 passed，19.24秒，退出1 | M4-r2-selection-red.* |
| 首版修复反例 | 重复前缀+双增强仍1 failed/88 passed，36.09秒，退出1；补规范归属后通过 | M4-r2-targeted-green.* |
| 最终定向 | 89 passed，78单元/11集成目录，31.03秒，退出0 | M4-r2-targeted-green2.* |
| 完整阶段 | **717 passed、2 deselected、0 skipped、7 warnings**；控制台589.36秒/JUnit588.867秒，退出0 | M4-r2-stage.* |
| 既有重导入 | 3 tests OK，1.709秒，退出0 | M4-r2-reimport-corrected.* |
| 前端 | 37单元、24离线浏览器、typecheck/build退出0 | M4-r2-frontend-* / M4-r2-browser.* |
| 当前四组dev | 各35完成/0失败，共140真实检索题次；输入/冻结/缓存及原语料核对通过 | [dev核验](M4-r2-dev-validation.json) |
| 60秒单题诊断 | HyDE completed，新增9、进入重排9；默认仍8秒 | [诊断报告](M4-r2-hyde-diagnostic.json) |
| 原真实产物只读 | dev35/68消息/23图；旧heldout15/31消息/19图，hash/完整解码、事件/引用/修订/语料通过 | [旧dev](M4-r2-historical-dev-readonly.json)、[旧heldout](M4-r2-historical-heldout-readonly.json) |
| 旧真实候选仅选择重放 | 048两型10+10；036新增8全部进入20输入，无新模型调用 | [重放报告](M4-r2-real-candidate-replay.json) |

完整阶段组成471单元/115契约/131集成目录。定向均包含于完整阶段，唯一总数为717，不累加。首次重导入命令模块路径错误导致ImportError/退出1单独保存M4-r2-reimport，不当业务红测；更正后3项通过。离线浏览器的me代理拒绝日志保留，协议模拟/合成PDF不冒充真实API浏览器。集成目录为真实隔离存储、Linux worker与模型端口注入等混合，不统称供应商端到端。

完整命令：`$env:M1_TEST_DB='m1_test_m4_r2_stage'; .venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -m 'not live_provider' -q --junitxml=docs/development/evidence/M4-r2-stage.xml`。定向精确命令、首次失败、更正命令及所有退出码见[M4-03](../records/M4-03.md)、[M4-04](../records/M4-04.md)、[M4-05](../records/M4-05.md)、[M4-10](../records/M4-10.md)。[本轮摘要](M4-validation-summary-r2.json)绑定原始证据hash，[新快照](M4-artifact-manifest-r2.json)只包含审阅后的源码/测试/中文文档及脱敏报告。

## 实验解释与未验证范围

四组dev逻辑invoke 4次，固定dev036的60秒单题诊断另1次，合计5次；诊断新增9条均进入20输入，默认仍8秒，不将60秒结果当作默认策略收益。

旧HyDE与control覆盖相同受截断干扰，不能证明有效增强无收益；原数字和逻辑调用原件不改。新版本代码bb69858f1575b8d0928efe20962ad7c147200d839ed61bb1e0879348fb8e3ea9，prompt/模型未变，146份源码/prompt字节与新配置另存；新四组严格单因素及增强组合，不混扩展。真实语料hashdd01944db688807c158923c0d21d272f1f45aa4304aa9012efada71c2c18b810，仅复用原隔离三资料595切片/53图，不重导入、不修改已入库知识。

新逻辑invoke **5**、stream **0**；无新答案，精确HTTP重试/金额未知。缓存复用明确记录，部分实验与阶段回归同机重叠，wall不作生产性能结论；来源覆盖不作正确率。旧15heldout已曝光，本轮0，不作新版本盲测或调参；若需新盲测，应另冻结未用于修复/选择的新题。新真实dev035组合组HyDE完成，新增6条均进入20输入；单HyDE两题超时、组合另1题超时，不能以覆盖相同证明增强无收益。没有新人工答案正确率（null），旧语义缺漏保留，本轮真实dev分解未触发，不宣称真实收益。详情见[修正实验报告](../../evaluation/retrieval-report.md)。默认Weighted(.5,.5)、20/20/20/20/10及增强/扩展/查询缓存关闭均保留。

## 兼容、范围、回滚与交接

无依赖/模型升级、公开API或必填配置变更；内部追踪新增池身份和评测实际输入。更新[配置说明](../../CONFIGURATION.md)、[契约](../../plans/DEVELOPMENT_CONTRACTS.md)、ADR-049、任务清单/阶段/进度/CHANGELOG；原始evidence、evals/output均保留本机不上传。单元不联网/下载模型；新正式集成只写m1_test_m4_*随机后缀隔离账本，真实实验语料仅只读；不清集合/桶或课程数据。

回滚用正常反向提交本轮选择和池追踪改动，保留数据/所有实验；回滚会恢复原R1缺陷，不能宣称同时修复。代码已推送2b06ee3，最终文档提交正常推送并核远程完整SHA后在最终回复补记，不强推、不循环amend。本轮不部署、不建Release、不进入M5。**等待总控复审M4。**
