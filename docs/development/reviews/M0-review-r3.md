# M0 总控审查 · 第 3 轮

日期：2026-10-23。结论：**通过。M0 9/9 完成，授权执行会话进入 M1-01 至 M1-11。**

依据[第3轮提交](M0-submission-r3.md)、实际脚本、原始控制台、真实报告及独立校验审查。R1、R2 已在[第2轮审查](M0-review-r2.md)接受，本轮聚焦 R3 和限定 JPEG MIME 兼容，无新增阻塞发现。[首轮审查](M0-review.md)和所有旧失败证据保留。

## 独立验证结果

| 验证 | 总控本轮实际结果 |
| --- | --- |
| `.venv/Scripts/python.exe scripts/verification/run_m0_checks.py --prefix M0-review-r3` | 总退出 0；内部 pytest **105 passed，14.77s，退出 0**；既有重导入 **3 tests OK，退出 0** |
| `.venv/Scripts/python.exe scripts/verification/check_m0_submission.py --spec docs/development/reviews/M0-r3-artifacts.json` | 退出 0；**38 Python 语法、82 文件哈希、23 提交链接**通过；M0-09=true，105/3，提交时 review=待审查 |
| `.venv/Scripts/python.exe scripts/verification/recheck_m0_images.py --source docs/development/evidence/M0-r3-live-image.json --output docs/development/evidence/M0-review-r3-live-image.json` | 退出 0；从原隔离历史唯一匹配原图片响应，准确拓扑及附加合法图片真实 HTTP/hash/解码通过，全部图片检查为真；无模型调用、无历史写入 |
| 本地差异/哈希、报告一致性及只读 Mongo 核对 | 退出 0；42 份代码/配置哈希、6 份 prompt 哈希一致；原会话 7 条，唯一匹配图片答案；冷启动会话 2 条、助手 1 条，答案哈希和预期事实相符 |

独立证据：[测试摘要](../evidence/M0-review-r3-validation.json)、[pytest 输出](../evidence/M0-review-r3-pytest.txt)、[既有重导入输出](../evidence/M0-review-r3-reimport.txt)、[真实图片复核](../evidence/M0-review-r3-live-image.json)、[报告与存储核对](../evidence/M0-review-r3-evidence-audit.json)。文件快照检查在总控更新文档前执行，提交时点与本次审查后的状态分开。

与 r2 对比，既有清单变动为图片验收器、对应测试及配置说明；新增两个验证脚本。没有业务图代码变动。本轮总控没有重复付费问答或冷启动，只读核验已有真实证据及持久化结果，并独立执行离线回归和图片 HTTP 获取；真实冷启动执行证据来自下述开发进程报告与控制台。

## R3 图片证据接受

原续验业务图实际完成于 83.858 秒，唯一 final、无 error、正文/final 相等、含预期拓扑、助手新增一次。该次命令退出 1 的原因是验收器拒绝真实 JPEG 元数据 `image/jpg`；源报告和控制台的失败状态没有改写。

本轮只将历史 `image/jpg` 归一为 `image/jpeg`，仍核对实际图像格式、精确 hash、HTTP 200 和完整解码。新增 JPEG 正例与 PNG 伪装反例，21 项图片用例随完整回归通过。开发红测记录 1 failed/19 passed 保留；本轮未回退代码重新制造红测。

只读复核通过原答案 SHA256 唯一匹配持久化助手消息，核对持久化图片集合与原 final 集合，沿用原真实事件检查，再下载验证；没有构造新 final 冒充真实事件。原检查证明正文 URL 为 final 子集，因此下载并集就是原 final 集合，该复核方法成立。复核报告分别保留源退出 1 和复核退出 0。

总控独立执行同一只读复核，确认预期拓扑 `eae9659759d836da4ae8897f0509f88545e464b7c550179a0eae1310bd479ebd` 的 HTTP 200、SHA256、JPEG 解码及 1090×446 尺寸通过；另一合法提示图同样通过。与第2轮已确认的手册图身份对应，R3 的真实图片验收完成。

## 正常冷启动证据接受

已审阅 `verify_m0_cold_start.py`、[冷启动报告](../evidence/M0-r3-cold-first.json)及[原控制台](../evidence/M0-r3-cold-first-console.txt)。新进程 PID 3580 未设置 OMP/MKL/OPENBLAS 线程变量，torch intraop/interop 均 10；不预热、不覆盖线程，两个模型单例在查询前均未加载，查询后均已加载。隔离库/集合、日志关闭和禁止下载保护不改变本次实际模型加载/查询路径。

实际查询 56.599 秒、进程退出 0，9 项检查全真：真实证据 ID、正确已知事实、唯一 final、无 error、正文/final 一致及助手保存一次等。总控只读查询核对该会话恰有两条消息、唯一助手答案的 SHA256 与报告一致。嵌入 cuda:0 只记为配置观测，重排实际设备 cpu；不把配置值当成实际 GPU 参数观测。

M0 的一次正常新进程验收要求已满足，无需为了同一门槛反复付费执行。此结论不代表长期、并发或跨环境稳定性验收。

## 保留风险与后续归属

- 原 43.085 秒图片业务异常本次未复现，根因仍未知；历史 Windows 原生加载异常也不宣称根治。原失败、崩溃与宿主恢复证据保留，复现时按实际阶段记录脱敏异常再定位，不用 MIME 问题或 Docker 故障倒推旧根因。现有真实成功证据满足 M0 门槛，未知历史原因不再单独阻塞本阶段。
- N1 无分隔符长串、超长标题与结构化切片边界按既定 M1-07 完成。
- 本阶段真实问答经 API runner/真实图执行；真实 HTTP 验证的是 MinIO 图片。问答 HTTP 服务、浏览器 E2E、持久运行与并发能力分别按 M2/M3 等阶段验收。
- MCP 缺配置、KG 占位不计已验证能力；不以本次耗时宣称性能提升。

## 授权与交接

M0 总控状态改为“通过”，核心任务 9/76、可选 0/2；M1 尚未实现，保持 0/11。

授权执行会话按[总清单](../../plans/DEVELOPMENT_TODO.md)、[M1阶段计划](../../plans/tasks/M1-knowledge.md)及[公共契约](../../plans/DEVELOPMENT_CONTRACTS.md)，从 M1-01 连续执行至 M1-11，阶段内无需逐任务另行确认。既定设计继续执行，不重新扩展项目范围；每项维护任务记录、进度、契约及实际证据，阶段末提交 M1-submission.md 待总控审查。M2 实现尚未授权。

M1 范围包括知识注册/幂等仓储、格式路由与可恢复解析、图像资产、结构化切片、独立 v2 索引、验证后发布/回滚，以及隔离迁移工具与小样验收。必要开发依赖、现有已配服务上的小样与必要真实供应商调用按任务执行，新增配置仍须中文说明、脱敏并同步示例。

继续保护现有课程资料、原集合、桶策略和 M0 证据。迁移先 dry-run，真实写入迁移前按 M1-10 做备份及独立目标恢复演练；失败停止迁移，验证使用隔离源/目标及 2–3 份小样。当前授权不含全量迁移现有课程库、删除或重建原集合/数据卷、公开发布、Git 初始化/推送或服务器部署。

开发 r3 manifest/inventory 保留“待审查”的提交时点，不覆盖旧快照来追随总控状态。今后提交保存新阶段独立报告、差异与清单；审查后的当前事实以本结论和 REVIEW_STATUS 为准。
