# M2 总控审查 · 第2轮

日期：2026-10-24。审查提交：`3b17ec905e71900dd3a1efa1217456fcbfac121a`。结论：**通过；关闭首轮 R1–R3，授权 M3-01 至 M3-11 按依赖连续开发。** M2 12/12、核心32/76；M3 0/11，尚未启动实现，M4及后续阶段未授权。

已独立读取[第二轮提交](M2-submission-r2.md)、[实际摘要](M2-validation-summary-r2.json)、[原提交快照](M2-artifact-manifest-r2.json)、首轮审查、实际源码、阶段计划与公共契约。没有仅凭开发自验通过阶段；本轮重新运行完整回归，并补充真实Mongo并发/中断窗口探针。原审查、提交、快照及失败证据保留，不回写历史。

## 独立验证

| 检查 | 实际结果 |
| --- | --- |
| 完整阶段pytest | **345 passed、2 deselected、0 skipped、7 warnings，275.26秒，退出0**；180单元、83契约、82集成目录用例；JUnit为275.246秒 |
| 既有重导入 | **3 tests OK，0.003秒，退出0** |
| 原提交快照 | 修改审查文档前独立核对**112文件hash、74份Python语法、205本地链接和本机敏感值扫描**，原始证据hash、实际JUnit数量和OpenAPI导出一致，退出0 |
| 真实API原产物只读复核 | **11检查通过，18事件一致，退出0**；没有重新执行供应商HTTP问答，新增付费调用0 |
| 总控补充探针 | **9检查通过，退出0**；独立新Mongo库，八方竞争、旧worker保护、旧run快照恢复、跨轮占用与事件核对 |
| Linux镜像源码 | 隔离、无网络容器内4个关键源码hash与工作区一致：ingestion/runner、runs/repository、commands、query_runner |
| Git | 审查开始时本地HEAD与远程main均为上述3b17ec9完整SHA |

完整阶段命令：`M1_TEST_DB=m1_test_20261024_m2_review_r2`，`.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -m 'not live_provider' -q --junitxml=docs/development/evidence/M2-review-r2-stage.xml`。Windows PowerShell、既有.venv，PYTHONIOENCODING=utf-8，关闭业务文件/控制台日志，未启用付费测试。7条既有警告为PyMuPDF SWIG弃用提示。集成目录包含真实存储、Linux worker/宿主BGE、模型端口注入和逻辑探针，不把82项统称供应商端到端，也不按本次耗时宣称性能提升。

快照命令：`.venv/Scripts/python.exe -m scripts.verification.build_m2_artifacts --summary docs/development/reviews/M2-validation-summary-r2.json --manifest docs/development/reviews/M2-artifact-manifest-r2.json --live-report docs/development/evidence/M2-r2-live-recheck.json --legacy-report docs/development/evidence/M2-r2-reimport.txt --check`。本轮文档更新后原manifest仍代表开发提交时点；不覆盖它来匹配总控文档。

既有回归命令：`.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q`。只读复核命令：`.venv/Scripts/python.exe -m scripts.verification.recheck_m2_live --report docs/development/evidence/M2-live-api-first.json --output docs/development/evidence/M2-review-r2-live-recheck.json`。答案hash、任务/修订、原件hash、消息与引用、唯一终态、增量一致和事件顺序均通过。首轮51.593秒/回答1次仍是历史真实HTTP证据，本轮没有将其冒充新执行结果。

## R1–R3 复核结论

**R1接受。** `app/ingestion/runner.py`先识别APITimeoutError，再识别其父类APIConnectionError，同时覆盖httpx/requests网络异常；超时与连接失败分别公开upstream_timeout/upstream_connection_failed。实际SDK的429/5xx可重试、401/403及格式错误不可盲重试。正式红测4失败/7通过的原始业务断言已核对，新增入口用例在本轮完整回归通过：run_import持久retryable、viewer拒绝、维护者版本门禁、重试后复用解析检查点。补充直接检查httpx ReadTimeout、ConnectError与本地OSError边界通过，无供应商请求。

**R2接受。** 资料许可通过单文档CAS接管过期其他job，拒绝有效其他job、同job更高attempt及同代异token；正常入口在领取前重读job fencing。续约不复活过期许可，旧清理匹配完整permit，最终活动指针仍校验permit和期限。自然过期后新修订实际发布及四方竞争的正式回归通过。另以新隔离Mongo补查：completed旧job保留许可、自然过期、八个有效新job竞争仅一个胜者；旧heartbeat/cleanup及迟到指针写入均为零匹配，接管者许可保留。无期限异常许可仍需人工核对，不把未知期限视作已过期。

**R3接受。** `RunRepository.release`重读持久事实，先幂等物化完成消息再按本run条件释放；新轮reconcile先补偿active旧终态。QueryRunner、事件flush和恢复复用此入口，消除旧的提前释放路径。正式两轮历史、第二轮实际生成prompt、写失败、实例重建、16方补偿/创建、分页与旧run释放保护在本轮回归通过。总控另停在completed/outbox已存且assistant写失败窗口，确认占用及outbox保留；传入pending旧快照仍能正确恢复完成消息，再让八个不同新请求竞争，只有一轮领取成功。重复恢复后历史仍为user1/assistant1/user2、新占用不被释放，原run唯一completed事件可读。

补充源码与输出仅留本机 `docs/development/evidence/M2-review-r2-probes.py/json`，9项检查不重复累计进345项。完整阶段原始输出为M2-review-r2-stage.txt/xml，镜像核对为M2-review-r2-worker-source.json。测试仅使用新m1_test_后缀库、新v2集合、m2-test/对象及隔离worker/队列，保留现场。本轮没有业务源码、真实配置、依赖或模型改动，不修改课程知识、原件/缓存、桶策略或原服务数据卷。evals/及原始evidence不上传。

## 授权与下一步

授权开发会话从 **M3-01连续至M3-11**，按[Vue工作台计划](../../plans/tasks/M3-vue-workbench.md)和依赖逐项验收，无需逐项申请。优先完成Vue工程与复用兼容性小样，再接登录/生成API类型、三栏布局、会话历史、SSE、型号确认、引用/PDF和资料导入界面。仅授权M3实现，本轮总控没有代为启动前端开发。

- 使用Vue 3 + TypeScript + Vite，依既定方向接Router、Pinia、Vue Query、shadcn-vue、PDF.js；固定可构建版本，登记复用commit、许可证与实际文件映射，不引入React。
- 消费现有API v1、Cookie/CSRF和SSE契约；断流恢复、410快照、401清理、409忙碌与版本冲突、取消及引用均按真实语义实现。前端不得因终态事件到达就假定会话占用已释放，持久化失败应允许原请求恢复。
- M3-01真实纵向小样可用最小登录/API/SSE接线验证兼容性，再在后续任务完善；不将预备接线记为M3-02/05等完整验收。不展示假进度、假引用或未实现管理动作。
- 真实验证沿用明确隔离数据，小样按需要调用模型并记录次数，历史有效产物优先只读复核；浏览器密钥检查、XSS、刷新恢复、桌面/手机实际交互和截图证据纳入M3-11。
- 每项维护任务记录、总清单、进度、CHANGELOG及受影响契约；依现有Git授权正常小提交/推送，不强推，不上传密钥、课程原件、模型、运行数据、evals/或原始本地证据。

M3阶段末交付M3-submission.md、实际验证摘要和新的独立快照，标为待审查，等待总控。**M4及后续阶段、服务器部署和公开Release未授权。** 合作取消、供应商响应至缓存窗口、生产灾备/全库迁移、高负载性能和历史未知原生异常的既有限制保留，本次通过不扩大其验收范围。
