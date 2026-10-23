# M2阶段提交 · 2026-10-24

状态：开发自验完成，提交总控独立审查；执行会话不标记审查通过。M2-01至M2-12全部完成，12/12；核心累计32/76，可选0/2。M3未授权。

## 修改范围与行为

| 任务 | 实际交付 | 记录 |
| --- | --- | --- |
| M2-01 | 新app.main工厂、版本API/错误信封、lifespan延迟资源；旧入口独立保留 | [01](../records/M2-01.md) |
| M2-02 | scrypt账号、散列会话、当前角色/kb、Origin/CSRF与共享登录限流 | [02](../records/M2-02.md) |
| M2-03 | owner会话、稳定消息ID、逐轮产品/引用快照与ordinal分页 | [03](../records/M2-03.md) |
| M2-04 | 幂等请求、条件占用、崩溃窗口补偿和条件释放 | [04](../records/M2-04.md) |
| M2-05 | 单文档事件outbox、幂等投递、seq重放/24h窗口/410、注释心跳 | [05](../records/M2-05.md) |
| M2-06 | 持久型号候选、版本确认、新token恢复、合作取消与失联中断 | [06](../records/M2-06.md) |
| M2-07 | 显式组织/kb目录、原件随机key、幂等修订/任务、验证后发布和回滚 | [07](../records/M2-07.md) |
| M2-08 | 授权原件/图片/引用、PDF Range、旧图准确hash映射、懒MinIO | [08](../records/M2-08.md) |
| M2-09 | Mongo事实账本、Redis/Celery Linux worker、attempt租约/共享限流 | [09](../records/M2-09.md) |
| M2-10 | 解析/原图/摘要/嵌入检查点、错误分类、最终发布许可fencing | [10](../records/M2-10.md) |
| M2-11 | 旧答案节点接每run持久事件、授权v2检索、答案引用快照及消息补偿 | [11](../records/M2-11.md) |
| M2-12 | OpenAPI、事件示例、代理说明、阶段回归与独立交付快照 | [12](../records/M2-12.md) |

源码主要位于app/main.py、app/settings.py、app/identity、app/conversations、app/runs、app/knowledge的API与资源适配、app/ingestion任务执行、app/infrastructure队列/模型桥接，以及compose.yaml、deploy/worker和scripts/admin。精确改动路径/hash见[M2独立快照](M2-artifact-manifest.json)，基线为M1总控通过提交ea798d1f08326a7798c3ea12169f7276bf4aa4ad。

旧入口依赖全局session队列、内存状态及课程集合；新入口在Mongo持久保存运行/事件/输入快照，断流不取消，终态互斥，旧执行不能覆盖新token。旧main_graph直接使用课程检索范围，因此新入口复用其答案提示词与生成节点，通过ContextVar注入出口；v2授权检索/产品确认/重排由新适配器实现，旧整图保持兼容。该最小调整已同步计划和ADR-031，不把旧未鉴权入口称为受新权限保护。

## 本轮实际验证

所有命令从项目根目录运行，Python均为已有.venv/Scripts/python.exe。原始证据留本机docs/development/evidence，未上传；[脱敏摘要](M2-validation-summary.json)记录原始hash、真实结果及边界，不覆盖M0/M1材料。

| 检查 | 精确命令与范围 | 实际结果/证据 |
| --- | --- | --- |
| 完整阶段回归 | `$env:M1_TEST_DB='m1_test_20261023_m2_stage_v2'; .venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -m 'not live_provider' -q --junitxml=docs/development/evidence/M2-stage-v2.xml` | 退出0，326 passed、2 deselected、0 skipped，205.655秒；M2-stage-v2.txt/xml；7条SWIG弃用警告 |
| 既有重导入 | `.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -v` | 退出0，3 tests OK，0.128秒；M2-legacy-reimport-v2.txt |
| 真实新API | `.venv/Scripts/python.exe scripts/verification/m2_live_api.py --database m1_test_20261023_m2_live_api_first --report docs/development/evidence/M2-live-api-first.json` | 退出0，51.593秒、11项检查真，真实回答调用1次 |
| 09/10联合复验 | `$env:M1_TEST_DB='m1_test_20261023_m2_queue_resume_checkpoint'; .venv/Scripts/python.exe -m pytest tests/integration/test_job_leases.py tests/integration/test_import_resume.py -q --junitxml=docs/development/evidence/M2-0910-checkpoint.xml` | 退出0，15 passed/43.35秒，Linux强停/续跑/重复投递 |
| 恢复边界修复后定向 | `$env:M1_TEST_DB='m1_test_20261023_m2_recovery_green'; .venv/Scripts/python.exe -m pytest tests/integration/test_query_runs.py tests/integration/test_job_leases.py tests/integration/test_run_commands.py -q --junitxml=docs/development/evidence/M2-11-recovery-green.xml` | 退出0，30 passed/20.62秒；已包含在完整阶段回归，不另累计 |

326项按目录为178单元、74契约、74集成目录用例。集成目录含错误分类/非法key纯探针、真实存储加模型端口注入与真实Linux worker；不能把74项全部称为供应商全链路。默认回归排除2项付费供应商测试，0跳过；本轮新API另以真实BGE dense/learned sparse、真实重排和真实LLM完成合成Markdown手册问答。未重复M1 MinerU/视觉付费调用。

真实API为独立正常新进程，登录→注册两型号→原件上传→Linux导入验证发布→无型号提问→候选澄清/确认→真实24V/2A回答→引用物理来源回看→消息快照→SSE重放→同请求幂等均通过；仅一次真实回答。原件hash、唯一终态、增量与快照一致、seq严格递增也通过。API实际运行未使用诊断预热或线程覆盖；嵌入复用受控宿主桥接，重排使用已有宿主模型。该小样不代表质量题集、性能提升或长期稳定性结论。

## 故障矩阵与原失败保留

| 行为 | 验证位置与结果 |
| --- | --- |
| 并发幂等/会话占用/三个领取崩溃窗口 | test_run_claim.py通过 |
| outbox保存/投递确认丢失/seq间隙/过期410 | test_event_outbox.py通过 |
| 错误版本/伪造候选/合作取消/过期旧token/失联中断 | test_run_commands.py通过 |
| 越权原件/引用、PDF200/206/416、旧图hash/解码 | test_asset_api.py和test_asset_access.py通过；仅独立测试桶策略变化 |
| broker失败/旧attempt拒绝/跨worker限流/Linux宿主连通 | test_job_leases.py通过 |
| 强停新测试worker后恢复/成功段缓存/仅一次发布 | test_import_resume.py通过；真实存储和Linux，付费端口计数用例明确注入 |
| 部分生成失败/消息补偿/并发不串流/撤权/无证据/外部图片 | test_query_runs.py、test_query_run_adapter.py、test_answer_filter.py通过 |

阶段首轮M2-stage-final为323 passed、2 failed、2 deselected，退出1/204.04秒。根因是扫描类测试共用账本，派发扫描到前例任务，以及异常会话归属阻断恢复。正式M2-11-orphan-red为1 failed/10 deselected；修复逐条范围检查、记录recovery_issue后继续，并将每个集成用例换独立后缀库，保留原断言/原现场；最终326通过。其他红测详见各任务记录；ImportError/NameError/镜像缺依赖及标准库test包遮蔽只记环境或命令失败，不当业务红测。

## 配置、依赖、数据和兼容

配置见[配置说明](../../CONFIGURATION.md)与.env.example，包含独立M2账本/知识owner/对象/索引、Cookie/Origin、运行与任务租约、Redis队列、宿主模型令牌/地址、全worker视觉预算。真实.env未改，不打印密钥/私有prompt/签名URL。缺配置只阻塞相关能力。

新增Celery5.5.3、redis-py6.4.0及Linux独立镜像，安装前dry-run/锁文件差异已核对；既有torch/vision/audio CUDA版本不变，未全量uv sync。Redis服务7.4.6为RSALv2/SSPLv1双许可；库来源与许可证见[复用登记](../../plans/2026-10-22-technical-support-reuse.md)。

真实写入仅显式m1_test_库及每例随机后缀、新测试v2集合、m1-test/m2-test隔离对象前缀、新测试队列/worker；测试数据与容器现场保留。旧课程原件、缓存、原知识集合/原桶策略及旧存储卷保持。没有重建旧服务/清桶/全量重导入，也没有部署服务器或发布Release。原始evidence和未跟踪evals/未上传。

## 风险、回滚与下一阶段

取消为边界合作停止，阻塞供应商请求不保证即时终止计费；供应商响应至持久缓存落盘有窗口，不承诺exactly-once。事件/账本当前使用单文档outbox，长回答和高负载容量、生产备份与灾备、多组织及公网部署未验收。PDF Range当前先读完整对象验hash，不代表大文件流性能。HTML/图片出口限制后，前端仍须采用安全Markdown渲染。历史Windows原生加载异常和原图片业务异常不宣称根治。

回滚停止新API、派发器、worker/模型桥接，按任务提交撤接线，保留Mongo/Redis/worker-cache卷、原件/索引/历史证据；不清库或修改旧桶。已发布资料回切用验证后发布CAS，不删新修订。异常归属条目由维护者人工核对，禁止自动接管owner。

main已推送M2-01至11：最近09/10为43d56027cc3a7b9eb5a00111ad7797b07cc52b6e，11为5323a1af662eba9a85742b219c32560057af18a0，均核对远程一致。M2-12文档/快照提交自身SHA在最终交接补记，不循环amend。Git同步不代表总控通过。等待总控审查M2；通过并获授权后再进入M3 Vue 3工作台。
