# M0 第3轮提交 · 2026-10-23

**R3真实图片与正常配置新进程冷启动已自验，M0任务9/9；提交总控复核，M1未授权。** 本轮只处理[第2轮总控审查](M0-review-r2.md)留下的R3，R1/R2已获接受，不重做设计或扩大阶段。保留[第2轮提交](M0-submission-r2.md)、[原提交](M0-submission.md)和全部原失败证据。

## 1. 任务与审查项

| 项目 | 本轮结果 |
| --- | --- |
| R1 / M0-06 | 第2轮总控已通过；无新业务切片变更，原23项随完整回归通过 |
| R2 / M0-09离线部分 | 第2轮总控已通过；本轮真实对象暴露历史JPEG MIME别名，先红测后限定兼容，增2项测试 |
| R3 / M0-09 | 原Docker健康；原会话只续验图片，准确拓扑真实HTTP/hash/解码/正文final全部通过；另起正常配置进程冷启动通过 |
| N1 | 无分隔符长串/超长标题仍交M1-07，不声称已解决，M1未授权 |
| N2 | 继续显式--spec及本轮独立快照，读取105/3真实输出，不沿用73或固定状态 |

已完成M0-01至M0-09，未完成M0任务无；核心9/76、可选0/2。任务勾选仅代表开发自验，总控状态为“待审查”，执行会话未标记“通过”。

## 2. R3真实图片：生成成功、验收器失败、同响应只读复核

用户启动Docker后四个原milvus/mongo/etcd/minio容器healthy，未重建/重置/清理。复用原隔离小样及会话，仅运行失败图片题，已知题76.795秒与追问48.524秒的原成功记录保留。

图片图调用**83.858秒完成**：唯一final、无error、预期3G/4G事实、正文/final相等且均含准确拓扑、助手新增一次。该命令实际退出**1**，因为两张真实JPEG对象的Content-Type是历史`image/jpg`，Pillow识别标准`image/jpeg`，验收器严格比较拒绝。原图调用结果与退出码保留于[M0-r3-live-image.json](../evidence/M0-r3-live-image.json)，不能称该命令退出0。

先新增能揭示误拒绝的回归，**1 failed/19 passed**；共享校验仅将image/jpg归一成image/jpeg，再补PNG冒充该别名的反例，**21 passed**。仍须准确origin/bucket/key/hash、禁重定向、200及完整解码；不放宽其他MIME错误，也不更改对象元数据或桶策略。证据[红测](../evidence/M0-r3-jpeg-mime-red.txt)、[绿测](../evidence/M0-r3-jpeg-mime-green.txt)。

新只读脚本用原响应正文SHA256唯一匹配真实持久化助手消息，原报告已证明唯一final、正文相等和图集合合法，再核对保存图集合等于原final集合并真实HTTP下载。没有新造final、重答、模型调用或历史写入。第一次复核已退出0，之后仅澄清报告源退出码字段，再次只读复核退出**0**，最终选用[M0-r3-live-image-verified-final.json](../evidence/M0-r3-live-image-verified-final.json)：`source_process_result`明确保留原退出1；本次复核退出0，不继承源error_type冒充新错误。首次复核报告也保留。

准确图为手册“图1 配置LA2608与无线控制器互通”，Host A/B/C→WiFi→LA2608→3G/4G→Internet→AC；第2轮人工身份确认见[预期图清单](../../../evals/datasets/m0-image-expectation.json)。本次实际结果：

| 对象 | 真实HTTP与内容 | 正文/final |
| --- | --- | --- |
| `m0-test/20261022_213750_933c22/eae9659759d836da4ae8897f0509f88545e464b7c550179a0eae1310bd479ebd.jpg` | 200，SHA256等于文件名，1090×446、31863字节，image/jpg→完整JPEG解码image/jpeg | 两处均含准确拓扑，关联检查全真 |
| 同前缀`1c6c5f2e20783d7dc14631772cc04ae178410203b37ca9807fad82873c4b2f07.jpg` | 200，精确hash、71×59，完整JPEG解码 | 合法额外提示图标，不能替代拓扑 |

报告沿用image_expectation.object_http_status“本轮未请求”是第2轮静态来源身份记录；真实HTTP结论来自本次image_verification.objects/checks，保留其时点避免篡改原记录。

**原43.085秒图片业务失败本次未复现，原因仍未知。** 本次没有新业务异常链可定位，不能把验收器MIME问题、Docker故障或成功重试倒推为原根因。原失败及两次原生0xc0000005加载崩溃全部保留。

## 3. 正常配置新进程冷启动

[冷启动报告](../evidence/M0-r3-cold-first.json)由全新Python进程PID3580实际生成，退出0，查询计时**56.599秒**（不含整个进程启动）。无预热、thread_overrides为空，OMP_NUM_THREADS/MKL_NUM_THREADS/OPENBLAS_NUM_THREADS均未设置，torch默认intraop/interop均10。两模型单例初始None，首次查询后embedding/reranker均已加载。

按原.env模型/设备配置，仅覆盖原隔离库/集合名、关闭日志、HF/transformers离线下载保护；未设置线程、未修改.env。嵌入**配置**cuda:0，未独立记录实际参数设备；重排配置cpu、实际target_devices为cpu，不用配置值冒充实际GPU观测。

真实API runner/图/模型/仓储完成已知题，正确display wlan ap与R/M事实，used_chunk_ids非空、唯一final、无error、final.answer与答案相等、助手保存一次、历史两条，9项检查全部真。一次成功满足本次冷启动验收，不构成长时间/并发稳定性或性能收益保证。历史原生异常不声称根治。

## 4. 实际验证命令、退出码与数量

全部在项目根目录执行，完整环境/行为前后/命令/数据/回滚见[M0-09任务记录](../records/M0-09.md)。pytest/unittest使用作用域fake，真实图调用与真实MinIO HTTP独立列出，不混算数量。

| 命令 | 退出码 | 结果与证据 |
| --- | ---: | --- |
| `docker ps -a --format '{{.Names}} {{.Status}}'` | 0 | 原四容器healthy；[健康证据](../evidence/M0-r3-docker-restored.json) |
| `.venv/Scripts/python.exe scripts/verification/resume_m0_live.py --source docs/development/evidence/M0-09-live-prewarm.json --output docs/development/evidence/M0-r3-live-image.json --cpu-threads 1 --prewarm-reranker --only image` | 1 | 图成功、验收器MIME失败；[原控制台](../evidence/M0-r3-live-image-console.txt) |
| `.venv/Scripts/python.exe -m pytest tests/unit/test_image_acceptance.py -q`（修复前） | 1 | 1 failed/19 passed，9.49秒 |
| 同上（修复及反例后） | 0 | 21 passed，9.48秒 |
| `.venv/Scripts/python.exe scripts/verification/recheck_m0_images.py --source docs/development/evidence/M0-r3-live-image.json --output docs/development/evidence/M0-r3-live-image-verified.json` | 0 | 原响应真实HTTP只读复核，无新问答写入 |
| `.venv/Scripts/python.exe scripts/verification/verify_m0_cold_start.py --source docs/development/evidence/M0-r3-live-image.json --output docs/development/evidence/M0-r3-cold-first.json` | 0 | 无预热正常冷启动；[控制台](../evidence/M0-r3-cold-first-console.txt) |
| `.venv/Scripts/python.exe scripts/verification/run_m0_checks.py --prefix M0-r3` | 0 | pytest105 passed/14.21秒及重导入3 tests OK，各自退出0；[实际验证摘要](../evidence/M0-r3-validation.json) |
| 内部 `.venv/Scripts/python.exe -m pytest tests/unit tests/contract -q` | 0 | [105项完整输出](../evidence/M0-r3-pytest.txt) |
| 内部 `.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q` | 0 | [3项输出](../evidence/M0-r3-reimport.txt) |
| `.venv/Scripts/python.exe scripts/verification/recheck_m0_images.py --source docs/development/evidence/M0-r3-live-image.json --output docs/development/evidence/M0-r3-live-image-verified-final.json` | 0 | 仅报告来源字段澄清后再只读验证，[控制台](../evidence/M0-r3-image-recheck-final-console.txt) |

相较已接受103项新增**2项**，阶段105项与既有3项分别报告；不把脚本、文件语法或HTTP对象数算作业务测试。无跳过M0必需验收项；MCP缺配置/KG占位不计已验证。真实问答通过实际API runner调用，未启动真实问答HTTP服务端口或浏览器E2E；真实HTTP在本次指MinIO图片GET。

## 5. 六项原缺陷对照及修改范围

本轮未再改A01–A06业务实现；原红绿和控制器审查结论保留，完整105回归覆盖。

| 原缺陷 | 修复前 | 当前行为/证据 |
| --- | --- | --- |
| A01最近历史 | 20取10读最早 | ts/_id倒序截窗后反转；同时间/空/跨会话/非法limit覆盖 |
| A02证据预算 | 首块过长遮蔽后续 | 整块跳过过长证据继续短块，记录实际入选ID/索引 |
| A03历史预算 | 单条超长消息越界 | 最近可容纳完整消息优先，头部/分隔符纳入字符计数 |
| A04型号歧义 | 多个近分自动第一 | 多个非精确高分澄清；精确型号优先，任一歧义向外传播 |
| A05短章节 | 缺身份或同名跨章合并 | 可靠章节实例ID并传播；缺身份不合并，原大小/表格/源/产品边界保留，23项 |
| A06生成异常 | 被吞并成功终态 | 异常携partial_answer传外层；失败无成功保存/final；成功唯一final，旧非流式失败502 |

本轮修改 `scripts/verification/image_acceptance.py`、`tests/unit/test_image_acceptance.py`，新增 `scripts/verification/recheck_m0_images.py` 与 `scripts/verification/verify_m0_cold_start.py`；无生产业务图代码改动。同步清单/阶段/进度/审查状态/CHANGELOG/任务记录/契约/配置运行/基线/README/源码审计/ADR-016及本提交。完整M0差异与哈希见下节。

## 6. 独立快照、数据边界与兼容

规格[M0-r3-artifacts.json](M0-r3-artifacts.json)明确选择本轮最终真实图片复核、正常冷启动和105/3输出；生成[baseline-manifest-r3](../../../evals/datasets/baseline-manifest-r3.json)、[M0-r3-diff.patch](../evidence/M0-r3-diff.patch)、[M0-r3-file-inventory.json](../evidence/M0-r3-file-inventory.json)。旧baseline/原与r2快照/提交/总控审查不覆盖；manifest任务“已验收”是开发自验，review仍“待审查”。

精确文件检查命令为 `.venv/Scripts/python.exe scripts/verification/build_m0_review_artifacts.py --spec docs/development/reviews/M0-r3-artifacts.json`，随后 `.venv/Scripts/python.exe scripts/verification/check_m0_submission.py --spec docs/development/reviews/M0-r3-artifacts.json`；实际退出码/文件数见[生成输出](../evidence/M0-r3-artifact-build.txt)与[检查输出](../evidence/M0-r3-artifact-check.txt)，不沿用前轮36/78/22数量。

实际生成退出0，42份代码/配置、82条清单；检查退出0，**38份Python语法、82文件哈希、23提交链接通过**，读取105/3及review=待审查。文档最终冻结后重建并复核哈希，文件检查不计业务测试数。

继续使用Mongo `m0_test_20261022_213750_933c22`、Milvus同前缀_chunks（4切片）/_items（1主体）、MinIO `m0-test/20261022_213750_933c22/`（4对象），未重导入或上传新对象。原会话 `m0-live-resume-1792676964083601400` 历史5→7；新冷启动会话 `m0-cold-1792729748518559800` 历史0→2，总增**4条隔离Mongo消息**。两次只读图片复核各写0/模型调用0。原件、缓存、原集合、隔离对象元数据及桶策略不变，原失败消息保留。

无新增配置/安装依赖/模型升级，无.env改写或凭据/签名URL输出；.env.example无需新增。兼容只影响验收器接受真实JPEG历史别名，不改变业务API/存储schema。未初始化Git、提交/推送、部署或公开发布。

## 7. 风险、回滚与下一动作

原业务图片失败原因未知；一次冷启动不排除历史Windows原生加载异常复发，后续真实运行如复现应继续脱敏采集，不执行破坏性故障测试。进程内单worker状态、MCP/KG未验证、N1长串/超长标题及其他未授权阶段问题仍保留，不宣称全面日志治理/完整token预算/前端产品能力已完成。

回滚先保护后续用户改动，对照evidence/r3-before/scripts/verification/image_acceptance.py逐片撤回MIME别名，停用两个新脚本；测试备份在首个红测之后，不当未修改原件，按新增两项逐片撤回。报告字段澄清前副本在r3-before/recheck_m0_images.py。无需数据迁移、删除会话或清理小样。原始originals/r2-before及所有失败证据继续保留。

**等待总控审查 M0。请独立复核本轮R3真实证据与105/3回归；M1未授权，执行会话在M0交接处停止。**
