# M2 第2轮修复提交 · 2026-10-24

状态：开发自验完成，提交总控复审。R1–R3逐项修复，M2-01至M2-12自验12/12、核心32/76；M2仅标待审查，M3未授权。首轮[审查](M2-review.md)、[提交](M2-submission.md)、快照、失败输出与总控探针均保留。

## 对审查意见的回应

| 项目 | 修复前 | 本轮实现与验证 |
| --- | --- | --- |
| R1 · 供应商异常 | OpenAI SDK超时/连接失败落库不可重试 | 实际SDK 2.28.0异常分类，先超时后连接；公开upstream_timeout / upstream_connection_failed。429/5xx可重试，401/403、400及格式错误不可自动重试。真实run_import注入SDK异常后保存retryable，viewer403、维护者版本409、重试及解析检查点复用通过 |
| R2 · 过期许可 | completed旧job在finally前退出，过期许可永久挡住新修订 | 单资料原子CAS允许接管过期其他job许可，保护有效其他job、同job更高attempt及同代异token。旧heartbeat/finally完整permit匹配，最终发布仍核对permit/期限；真实独立存储小样自然过期后新修订发布一次，4方竞争仅一胜者，迟到旧worker不能续约/清理/切回指针 |
| R3 · 跨轮顺序 | 完成CAS释放占用后才补assistant，下一轮缺上一轮上下文 | RunRepository.release重读持久快照，先幂等物化assistant再条件释放；下一轮reconcile先补偿旧终态。写失败保留旧占用/准备请求，可原请求恢复。两轮历史为user1/assistant1/user2/assistant2，第二轮实际生成prompt按顺序包含上一轮正确答案；实例重建、16方恢复/创建、重复恢复、分页、旧run释放保护通过 |

关键文件：app/ingestion/runner.py（分类、许可协议、heartbeat/finally）；app/runs/repository.py（顺序屏障与条件释放）、commands.py及query_runner.py（统一复用）；新增test_provider_errors.py、test_review_provider_retry.py、test_review_import_permits.py、test_review_completion_order.py。交付工具build_m2_artifacts.py新增显式summary/manifest/base/live-report/legacy-report选择，test_m2_artifact_reports.py以相反的新旧报告结论验证不会误用历史结果；recheck_m2_live.py只读复核已有产物。精确文件/hash见[新独立快照](M2-artifact-manifest-r2.json)。

## 实际验证

命令均在项目根目录、Windows PowerShell、既有.venv执行，PYTHONIOENCODING=utf-8，业务控制台/文件日志关闭。原始输出保留本机docs/development/evidence，不上传；[新摘要](M2-validation-summary-r2.json)保存实际JUnit数量、原始文件hash与范围。

| 验证 | 命令与证据 | 实际结果 |
| --- | --- | --- |
| R1正式红测 | pytest tests/contract/test_provider_errors.py tests/integration/test_review_provider_retry.py -q；M2-r2-R1-red.txt/xml | 退出1，4 failed/7 passed，24.99秒；SDK分类及入口落库业务断言失败 |
| R1定向 | pytest tests/contract/test_provider_errors.py tests/integration/test_review_provider_retry.py tests/integration/test_import_resume.py -k 'not real_linux' -q；M2-r2-R1-green.txt/xml | 退出0，16 passed/1 deselected，34.74秒 |
| R2准确红测 | pytest tests/integration/test_review_import_permits.py -q；M2-r2-R2-red-v3.txt/xml | 退出1，2 failed/2 passed，22.20秒；completed旧job自然过期后新job领取ConflictError，并发0胜者 |
| R2定向 | pytest tests/integration/test_review_import_permits.py tests/integration/test_import_resume.py tests/integration/test_review_provider_retry.py -k 'not real_linux' -q；M2-r2-R2-green-v2.txt/xml | 退出0，11 passed/1 deselected，56.48秒 |
| R3正式红测 | pytest tests/integration/test_review_completion_order.py -q；M2-r2-R3-red.txt/xml | 退出1，2 failed；控制台8.93秒、JUnit8.187秒 |
| R3定向 | pytest tests/integration/test_review_completion_order.py tests/integration/test_query_runs.py tests/integration/test_run_commands.py tests/integration/test_run_claim.py tests/integration/test_event_outbox.py -q；M2-r2-R3-green.txt/xml | 退出0，36 passed，42.21秒 |
| 检查器红/绿 | pytest tests/unit/test_m2_artifact_reports.py -q；M2-r2-artifacts-red/green.txt/xml | 先退出1/2 failed，再退出0/2 passed，14.88秒 |
| 完整阶段 | `$env:M1_TEST_DB='m1_test_20261024_m2_r2_stage'; .venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -m 'not live_provider' -q --junitxml=docs/development/evidence/M2-r2-stage.xml` | 退出0，345 passed、2 deselected、0 skipped，7条既有SWIG警告；控制台295.92秒，JUnit295.889秒 |
| 既有重导入 | `.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -v`；M2-r2-reimport.txt | 退出0，3 tests OK，0.013秒 |
| 当前worker镜像 | `docker compose --profile tasks build worker`；M2-r2-worker-build.txt | 退出0，仅重建worker镜像；阶段回归使用当前源码镜像，不重建旧服务/卷 |
| 原真实API产物只读复核 | `.venv/Scripts/python.exe -m scripts.verification.recheck_m2_live --report docs/development/evidence/M2-live-api-first.json --output docs/development/evidence/M2-r2-live-recheck.json` | 退出0，11检查真、18事件一致，供应商调用0 |

定向行的完整解释器前缀为`.venv/Scripts/python.exe -m`，均带`--junitxml=docs/development/evidence/<对应名称>.xml`；精确独立库和命令见[09](../records/M2-09.md)、[10](../records/M2-10.md)、[11](../records/M2-11.md)、[12](../records/M2-12.md)。定向不与阶段重复累计。

阶段按目录为180单元、83契约、82集成目录，共345项；较首轮新增19项。集成目录包含纯逻辑探针、真实隔离存储配模型端口注入及真实Linux worker/宿主BGE，不称82项均为供应商全链路。排除2项live_provider付费测试，无跳过。首次真实HTTP/真实LLM的51.593秒、回答1次是保留的历史证据，本轮没有重跑付费查询。R1/R2改变导入故障处理，R3改变消息物化顺序；新增真实存储小样和实际生成端口上下文验证覆盖变化，正常HTTP供应商接口未变化。原HTTP产物的原件/活动修订/答案hash/消息/引用/事件只读复核有效。

## 失败记录与边界

R2最初完整发布用例4秒租约过短，在旧任务发布前被正确fencing拒绝；red-v2又因测试时间naive/aware相减失败，均不算该目标窗口业务红测。并发接管反例有效；red-v3使用15秒租约、完成后等待自然过期，准确复现新任务领取失败，随后green-v2通过。原red、red-v2、首次green不覆盖。文档批处理/一次回放脚本SyntaxError、patch上下文不匹配及只读复核脚本首次KeyError: bucket是脚本问题，非业务红测；后续修正，原记录保留。

无新增运行配置或依赖，无PyTorch/CUDA、模型升级。仅新m1_test_随机后缀库、新v2集合、m2-test/对象、隔离队列/测试worker；课程原件、解析缓存、旧知识、旧桶策略、原服务与数据卷不改，不手工清许可或删除现场。evals/与全部原始evidence未提交。新维护文档/契约说明中文。

恢复限制：无期限的异常许可保留人工核对，不猜测过期；正常QueryRunner完成必存快照，历史低层无completion_snapshot终态保留兼容、不推测消息。已存在错序历史不改写ordinal。消息存储不可用时暂时保留会话占用以保证顺序；恢复后同请求可补偿。取消仍为边界合作停止、付费响应至检查点有窗口，不承诺exactly-once。生产灾备、全库迁移、高负载性能、历史Windows模型加载/未知图片异常均不据此宣称根治。

## 交付检查、Git与回滚

快照生成及复核命令：`.venv/Scripts/python.exe -m scripts.verification.build_m2_artifacts --summary docs/development/reviews/M2-validation-summary-r2.json --manifest docs/development/reviews/M2-artifact-manifest-r2.json --live-report docs/development/evidence/M2-r2-live-recheck.json --legacy-report docs/development/evidence/M2-r2-reimport.txt`，复核加`--check`。基线沿M1通过提交，生成新文件且拒绝覆盖，原M2快照不改写；实际检查结果见任务12记录及最终交接。

已推送main：cd723c9（R1代码/测试）、f2d5631（R1记录补齐）、6d94ef6（R2）、e1a871f（R3）；最终交付提交自身SHA在最终回复补记，不循环amend。提交与推送不代表总控通过。

回滚先停止新API/派发/worker，按上述内聚提交正常撤回接线，保留Mongo/Redis/对象/索引/worker-cache及全部证据；不清库、清桶、删许可或强推。已发布版本按验证后CAS回切。

等待总控复审M2；开发会话不自行标通过，不进入M3，不部署服务器或创建公开Release。
