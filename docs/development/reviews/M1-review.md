# M1 总控审查 · 第1轮

日期：2026-10-23。审查提交：`2945ebcff0686612ec4018173ceb0d17da4e9205`，基线：`0a409294c173601898c847ee962938b155f98d45`。结论：**需修复，M2 暂不授权。**

依据[阶段提交](M1-submission.md)、实际源码、任务契约、原始证据及独立验证。本轮顺序审查，未修改业务代码，未重复付费供应商调用。已将补充正常函数探针保存在本机忽略的 evidence 目录；以下包含可公开的合成复现说明。

## 独立验证结果

| 验证 | 实际结果 |
| --- | --- |
| `M1_TEST_DB=m1_test_20261023_controller`，`.venv/Scripts/python.exe -m pytest tests/unit tests/integration tests/contract -m 'not live_provider' -q --junitxml=docs/development/evidence/M1-review-stage.xml` | 退出0，**181 passed，2 deselected，7 warnings，169.84秒**；154单元、12契约、15真实隔离集成 |
| `.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q` | 退出0，**3 tests OK，0.007秒** |
| `.venv/Scripts/python.exe scripts/verification/build_m1_artifacts.py --check` | 退出0，78文件哈希、49份Python语法、176链接及原始报告hash核对通过；敏感值检查通过 |
| `.venv/Scripts/python.exe scripts/verification/recheck_m1_live.py --report docs/development/evidence/M1-11-live-report.json --output docs/development/evidence/M1-review-live-recheck.json` | 退出0，两资料5/2切片的原件、载荷、向量、来源、图片及摘要缓存关联复核通过，供应商0调用 |
| `git ls-remote origin refs/heads/main` | 审查开始时远程头等于上述2945ebc提交；工作区只有既存未跟踪evals/ |

完整测试命令另关闭控制台/文件日志并设置PYTHONIOENCODING=utf-8；未设置M1_LIVE_PROVIDER。本轮没有重新执行两项付费测试，开发已有实际供应商报告、控制台和当前产物的只读复核有效，不将其算进181项。警告为已有PyMuPDF SWIG弃用提示。

本机原始证据为 `docs/development/evidence/M1-review-stage.txt/xml`、`M1-review-reimport.txt`、`M1-review-runs.json`、`M1-review-live-recheck.json`。补充探针见同目录 `M1-review-probes.json`、`M1-review-excel-source-probe.json`、`M1-review-restore-target-probe.json`；均不上传原始现场。不把探针结果计入pytest通过数。

## R1 · P1 · 表格分隔行处理会删除Excel真实数据并错配来源

位置：`app/ingestion/stages/chunking.py:88`–`115`，关联`MarkdownParser`的rows/来源构造。

`rows[1]`只要各单元格匹配短横线模式便被删除，没有判断来源格式；删除后又没有同步真实行号映射。正常 `ExcelParser→chunk_document` 合成工作簿：A1=`parameter`、A2=`---`、A3=`actual-value`。解析器正确读到三格，最终切片却是 `parameter\nactual-value`，`---`消失；切片summary来源为第2行，保留A2引用而丢掉实际正文A3引用。Excel真实单元格不能当成Markdown语法。

Markdown路径也有同源问题：四物理行`|Name|Value|`、`|--|--|`、`|alpha|1|`、`|beta|2|`，以max_chars=25拆成两片后，alpha/beta来源row_start分别为2/3，实际物理行是3/4；line_start/end仍都指整个表1–4，未表达拆片定位。对未知物理表格行位置的PDF，也不能用推算序号伪装准确来源。

要求：仅在明确Markdown表格语法路径识别分隔行，并保留行与原始坐标的映射；Excel不能删除真实短横线单元格。拆片正文、重复表头和来源必须对应，缺定位保持显式未知，必要时另定义表内序号，不能冒充物理来源。

验证：先加入上述正常Excel解析到切片的红测，断言全部值、A3和实际行范围；加入Markdown前置非表格文本、多片表、分隔行、真实短横线数据和PDF缺物理行定位的边界。保留既有公式/缓存、跨sheet、表头重复及大小限制回归。**M1-07重开。**

## R2 · P2 · Markdown跳级标题后的同级章节路径错误

位置：`app/ingestion/parsers/markdown.py:38`。

`headings[:level-1]`把当前路径元素数当成实际标题级别。当输入`# Root → ### First → ### Second`时，Second路径实测为`Root/First/Second`，期望`Root/Second`；正文与SourceRef.section_path同样错误。手册中合法的跳级标题会制造不存在的父子关系。

要求：保留实际标题level的栈或映射，遇新标题弹出同级及更深级；不要为缺失级别编造标题。同步块和SourceRef，并保留代码围栏内标题不解析的行为。

验证：正常解析路径覆盖跳级同级、深层回退、以三级标题起始、重复同名标题及围栏。旧缓存/解析版本如需更新，按不可变修订策略说明，不回写已发布证据。**M1-05重开。**

## R3 · P1 · 恢复仍依赖在线源集合schema，备份不自包含

位置：`app/knowledge/migration.py:59`–`81`与`104`–`108`。

`backup_selection`没有保存Milvus schema，`restore_sample`却直接向源集合调用`describe_collection`再构造恢复schema。源集合不可用时，即使本地snapshot和blobs完整、hash正确、独立目标可用，恢复仍失败。本轮合成客户端在该调用明确抛出源不可用异常，未执行真实故障或删除集合。现有集成始终保留源在线，未覆盖该缺口；runbook称schema已在snapshot中也与实现不符。

要求：备份保存并纳入hash校验的必要schema及索引/动态字段等恢复信息，恢复依据已验证快照创建目标，不再读取源数据或源schema。旧快照缺信息应明确拒绝或提供显式兼容流程，不能悄悄声称恢复完整。不要求扩展为新服务器灾备系统。

验证：先补能阻断所有源读取而允许目标操作的回归；备份后仅从本地快照和目标恢复。保留原向量、全部业务字段、动态字段、对象与引用的读回校验，随后在新的隔离目标完成真实小样复验。不得为制造反例删除真实源集合。**M1-10重开。**

## R4 · P1 · 恢复对象目标未检查独立与非空，可重写源对象

位置：`app/knowledge/migration.py:97`–`120`。

Mongo/Milvus有源目标比较，但MinIO只检查prefix以`m1-test/`开头，随后无冲突检查地put。用同桶同prefix、源key为`prefix+sha256`的合成对象客户端，函数实测向源key执行put，并返回verified=true。全部为离线fake，无真实对象写入；同字节重写仍可能改变元数据/版本，且违反“不覆盖已有对象”的恢复约定。已有恢复目录即便不与源重叠也可能被覆盖。

要求：在任何恢复写入前预检所有存储目标。明确拒绝与选定源对象重叠的目标及已有目标对象/非空恢复前缀；防止前缀嵌套等别名绕过。若支持继续已有恢复，须显式校验内容及身份，不能默认覆盖。保留失败现场、不清空目标来凑通过。

验证：离线覆盖同桶同源key、已有不同对象、重用恢复前缀、前缀嵌套及合法新目标，拒绝路径断言Mongo/Milvus/MinIO写入均为0；真实小样使用新的隔离恢复目标，不触碰原数据。与R3可同轮修复，但分别记录。**归M1-10。**

## 已接受部分与范围

注册幂等、attempt CAS、完整索引载荷冻结、双路向量及范围过滤、图资产hash/解码与缓存、验证后CAS指针和outbox故障核对、已发布修订回看，在已阅读实现和独立回归范围内有有效证据。N1连续长串/超长标题正式回归通过，不因本轮表格问题否认这部分修复。

供应商真实小样通过是有效证据，但不能覆盖上述源位置和恢复保护缺口。本轮无新增配置缺项，不要求升级模型、重做全部付费题、全量重导入或扩展M2。旧M0历史未知异常继续保留，不作为本轮新增阻塞。

代码中较多分号压缩多条控制流影响可读性，可在改动相关函数时适度展开；这不是另一个阶段门槛，不要求为此全库格式化。

## 状态与下一步

- M1-05、M1-07、M1-10重开，M1-11整体验收保持未完成；其他7项保留完成。当前M1 **7/11**，核心合计 **16/76**，可选0/2。任务原自验及提交时点快照不覆写。
- M1状态“需修复”，允许执行会话在M1内连续完成R1–R4、先红后绿及必要隔离真实复验；**M2未授权**。
- 修复按任务小提交并正常推送，保留旧证据和本次失败探针。生成新的`M1-submission-r2.md`、实际测试摘要与独立文件快照，不能覆盖原manifest或把旧181固定当新数量。
- 阶段测试完成后再交总控复审。优先只读复核原供应商产物，只有修复影响供应商协议或当前产物无法证明时才做必要的新小样调用。
- 总控本轮真实写入仅独立集成测试产生的`m1_test_*`与`m1-test/`小样、备份恢复目标，原库未改；补充反例全离线，无供应商调用。
