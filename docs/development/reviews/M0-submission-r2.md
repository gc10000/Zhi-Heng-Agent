# M0 第2轮提交 · 2026-10-23

**待总控复审：R1 已修复，R2 离线修复与准确拓扑身份已完成，R3 真实验收仍被本机 Docker 阻塞。M0-09 未完成，M1 未授权。**

依据 [首轮审查](M0-review.md) 逐项处理，保留 [原提交](M0-submission.md)、原始失败和旧快照。本轮没有新增真实查询或存储写入，不将 Docker 故障解释为原图片题的异常根因。

## 1. 逐项回应

| 审查项 | 本轮结果 | 完成边界 |
| --- | --- | --- |
| R1 / M0-06 | **已修复并定向通过** | 正常 step_2→step_4 同名章节红绿、真实生成身份及传播、合法同章合并、缺身份与原边界全部覆盖；恢复任务勾选，待总控复审 |
| R2 / M0-09 | **离线修复及来源图确认完成** | 共享检查精确origin/bucket/key/hash、MIME/解码、正文/final关联；正确拓扑已目视确认；真实对象HTTP验证归R3，尚未通过 |
| R3 / M0-09 | **仍阻塞，未验收** | 一次只读Docker检查退出1，Linux引擎管道不存在；不重复调用失败预检；原图片题脱敏根因和正常冷启动均待真实运行 |
| N1 | 保留后续边界 | 无分隔符长串/超长标题仍交已登记M1-07，不在M0扩展切片算法；M1未授权 |
| N2 | 已补正 | 工具改为--spec选择实际报告/新输出，从真实退出码/输出读取数量，状态依当前清单/证据计算，不固定73或旧失败状态 |

当前完成任务：M0-01、02、03、04、05、06、07、08；未完成：M0-09。任务自验统计8/9、核心8/76，可选0/2；总控审查尚未通过。

## 2. R1 实现与前后行为

`node_document_split.py` 现为每次标题拆分生成运行 UUID 前缀，每个实际章节实例分配不同 `section_instance_id`；同名“## 配置”也不同，长块通过副本保留。合并在原来源/产品/结构/父标题/表格/大小条件之外，要求相同非空实例身份，或调用方显式可靠 section_id。缺身份、仅 heading_path/标题/part 相等时不合并。无标题兜底也分配本轮身份；不是持久知识ID，不改Milvus schema或旧数据。

回归先以总控合成内容走**正常 step_2→step_4**，在断言“不存在同时含A/B的块”处失败，复现真实串合。另覆盖缺身份、同章合法合并、输入不变和跨拆分轮次；原16项表格/来源/产品/大小等用例保留，合法合并fixture补充可靠身份，未删除或放宽原断言。前5 failed/17 passed，修复后23 passed；新增7项。详见 [M0-06记录](../records/M0-06.md)。

## 3. R2 准确预期图与校验

已目视原完整手册**物理第4页、印刷第1页**及节选物理第1页的“图1 配置 LA2608 与无线控制器互通”：Host A/B/C→WiFi→LA2608→3G/4G→Internet→AC。四张旧对象中准确拓扑是下列对象，其余三张是小提示图标：

- SHA256：`eae9659759d836da4ae8897f0509f88545e464b7c550179a0eae1310bd479ebd`。
- 准确key：`m0-test/20261022_213750_933c22/eae9659759d836da4ae8897f0509f88545e464b7c550179a0eae1310bd479ebd.jpg`。
- 缓存 JPEG 完整可解码，**1090×446，31863字节**，与首轮复制清单hash/大小一致。
- [准确图像与来源哈希清单](../../../evals/datasets/m0-image-expectation.json)、[原手册来源页](../evidence/M0-r2-topology-original-page.png)、[准确拓扑副本](../evidence/M0-r2-expected-topology.jpg)、[本地核对结果](../evidence/M0-r2-topology-check.txt)。原件和缓存只读；该结果不代表本次真实对象下载通过。

两条真实脚本接入 `scripts/verification/image_acceptance.py` 的同一函数，纯离线fake HTTP回归先复现旧表达式假阳性，再收紧：

1. 允许对象由原复制清单和运行时真实配置绑定准确origin/bucket/key/hash，未知origin/bucket/key及URL编码别名/query在请求前拒绝，HTTP GET 禁止自动重定向。
2. 正文含预期拓扑图，final含同图，final.answer与答案一致，正文引用图均在final中；允许final额外包含其他已记录图。
3. 所有引用及final图均须HTTP200、image/* Content-Type、实际SHA256相符、Pillow verify+load完整解码、实际格式与MIME一致。结果仅记key/hash/尺寸/状态/异常类型，不回显URL或异常正文。

离线红测**10 failed/2 passed**；修复后12项通过，再补合法附图、重定向适配、URL别名及错误脱敏，最终**19 passed**。覆盖正确图、错误同前缀图、HTML200、跨origin、错误bucket、未知对象、正文/final不一致、缺预期图、内容hash错误、不可解码、MIME不一致、302等。详见 [M0-09第2轮记录](../records/M0-09.md)。

## 4. 实际命令、退出码与数量

均从项目根目录运行，无模型下载或真实服务调用。pytest/unittest外部依赖用作用域fake，不能冒充真实集成。

| 命令 | 退出码 | 实际数量 / 证据 |
| --- | --- | --- |
| `$env:PYTHONIOENCODING='utf-8'; .venv/Scripts/python.exe -m pytest tests/unit/test_chunk_structure.py -q`（修复前） | 1 | 5 failed/17 passed；[R1-red](../evidence/M0-r2-R1-red.txt) |
| 同上（修复后，增加跨调用轮次用例） | 0 | 23 passed；[R1-green](../evidence/M0-r2-R1-green.txt) |
| `$env:PYTHONIOENCODING='utf-8'; .venv/Scripts/python.exe -m pytest tests/unit/test_image_acceptance.py -q`（修复前） | 1 | 10 failed/2 passed；[R2-red](../evidence/M0-r2-R2-red.txt) |
| 同上（修复与补充边界后） | 0 | 19 passed；[R2-green](../evidence/M0-r2-R2-green.txt) |
| `.venv/Scripts/python.exe scripts/verification/run_m0_checks.py --prefix M0-r2` | 0 | 内部完整pytest **103 passed，14.68秒**；既有重导入 **3 tests OK**，二者退出均0；[实际验证摘要](../evidence/M0-r2-validation.json) |
| 内部 `.venv/Scripts/python.exe -m pytest tests/unit tests/contract -q` | 0 | [103项原始输出](../evidence/M0-r2-pytest.txt) |
| 内部 `.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q` | 0 | [3项原始输出](../evidence/M0-r2-reimport.txt) |
| `.venv/Scripts/python.exe scripts/verification/confirm_m0_topology.py` | 0 | 本地来源页渲染、缓存解码/hash与旧对象清单一致；不计业务测试数 |
| `docker ps -a --format '{{.Names}} {{.Status}}'`（Python子进程设置12秒超时，本次未超时） | 1 | Linux引擎管道不存在；[R3-infrastructure](../evidence/M0-r2-R3-infrastructure.json) |
| `.venv/Scripts/python.exe scripts/verification/build_m0_review_artifacts.py --spec docs/development/reviews/M0-r2-artifacts.json` | 0 | 40份代码/配置差异、78个清单条目，独立r2输出，旧文件不覆盖；[artifact-build](../evidence/M0-r2-artifact-build.txt) |
| `.venv/Scripts/python.exe scripts/verification/check_m0_submission.py --spec docs/development/reviews/M0-r2-artifacts.json` | 0 | 36份Python语法、78个哈希、22个提交链接；[artifact-check](../evidence/M0-r2-artifact-check.txt)，文件检查不计103项业务/工具测试 |

阶段新增**30项**：R1新增7项+R2新增19项+快照证据反固化4项。原73项全部保留；快照工具4项用临时JSON验证17/123动态数量、新成功报告、不合格冷启动和哈希变更，明确属于离线工具验证。

## 5. 修改文件、工具与历史保留

业务改动仅 `app/import_process/agent/nodes/node_document_split.py`；正式回归为 `tests/unit/test_chunk_structure.py`、新 `test_image_acceptance.py`、新 `test_review_snapshot.py`。R2共享检查与两脚本接线、只读来源核对、实际结果采集和快照生成/检查位于 `scripts/verification/`。契约、清单、阶段、进度、CHANGELOG、配置/运行说明、决策和任务记录同步。

N2生成器和检查器现在必须 `--spec`，本轮规格 [M0-r2-artifacts.json](M0-r2-artifacts.json) 明确选择：前轮预热真实报告（本轮无新真实结果）、本轮103+3实际测试摘要、cold_start_report=null、当前边界及独立输出名。新报告通过时能读取新结果，不再固定“失败”或73。实际测试输出同时记录退出码、数量、哈希；被改动的输出不能配旧摘要通过。

首轮 baseline-manifest.json/M0-diff.patch/M0-file-inventory.json、原提交与总控审查均保留。新文件为 [baseline-manifest-r2](../../../evals/datasets/baseline-manifest-r2.json)、[M0-r2-diff](../evidence/M0-r2-diff.patch)、[M0-r2-file-inventory](../evidence/M0-r2-file-inventory.json)。本轮前源码备份在 evidence/r2-before；首轮原始备份及其manifest未重写。

## 6. R3 阻塞与接续

本轮一次有超时限制的只读检查仍无法连接Docker Linux引擎；**没有重复Milvus预检、真实模型调用或空等**，未重置Docker/WSL、清卷、删除socket、重建集合或重复复制图片。前轮两题成功仍保留：已知题76.795秒、追问48.524秒；图片43.085秒失败，原异常根因仍未知。旧两次原生加载异常也保留，预热成功不能证明默认冷启动稳定。

恢复原Docker引擎并核对已有容器健康后，复用原库/集合/对象前缀和会话，仅执行失败图片题：

```powershell
.venv/Scripts/python.exe scripts/verification/resume_m0_live.py --source docs/development/evidence/M0-09-live-prewarm.json --output docs/development/evidence/M0-r3-live-image.json --cpu-threads 1 --prewarm-reranker --only image
```

此命令本轮**未运行**。采集脱敏业务原因链，必要时加回归后修复，验证R2真实正确对象/HTTP/正文/final及一次助手保存。如果修复影响原两题路径，再定向复验。完成后另起**全新正常配置Python/应用进程**，无续验脚本专有预热/线程覆盖，验证模型加载及一次真实查询，记录精确命令、退出码、实际设备、终态、保存次数；当前没有该合格证据，manifest明确cold_start_verified=false。

下一轮快照应显式选择新的真实报告/冷启动报告与重新运行的必要回归，不重用本轮结果作为未来已通过结论。M0-09及阶段审查保持未完成/待审查，不进入M1。

## 7. 配置、依赖、数据、兼容与回滚

本轮无新增配置或依赖，无模型/目录大改，无真实配置值输出。Pillow/PyMuPDF均沿用现有环境。真实数据读写0、供应商调用0；仅本地只读核对原PDF/缓存并新增审查图像证据。原课程原件、缓存、已入库知识、桶策略和隔离小样均保留。

兼容影响为切片过程新增section_instance_id，不改变旧业务API/数据库schema；验收脚本现在收紧图片条件、审查工具需显式--spec，旧无参数命令应按历史版本理解。旧进程内状态/存储写入异常策略、完整token预算、全局日志治理仍是后续范围；N1不作已解决声明。

回滚需先保护后续用户改动，对照r2-before逐片恢复本轮源码/脚本，并撤回本轮新文件接线；首轮原始备份可另供差异核查，不整目录覆盖。数据无需迁移或删除；停用测试脚本即可退出隔离命名空间。无Git初始化、提交/推送、公开发布或服务器部署。

**等待总控审查 M0。R1/R2申请复审，R3仍待环境恢复后的真实验收，M1未授权。**
