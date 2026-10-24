# M2 总控审查 · 第1轮

日期：2026-10-24。审查提交：`337297fb7a921cdec6fdcaad563d19fe5905d496`，基线：`ea798d1f08326a7798c3ea12169f7276bf4aa4ad`。结论：**需修复，M3不授权。**

已读取[阶段提交](M2-submission.md)、实际实现、[M2计划](../../plans/tasks/M2-api-runs.md)、公共契约、原始证据并独立验证。常规回归通过，但补充正常调用与中断窗口反例发现下列三个问题。重开M2-09、M2-10、M2-11、M2-12，当前M2 8/12、核心28/76；其余已验收能力保留。本轮仅审查与文档维护，没有修改业务代码。

## 独立验证结果

| 检查 | 实际结果 |
| --- | --- |
| 完整阶段pytest | **326 passed、2 deselected、0 skipped、7 warnings，289.46秒，退出0**；178单元、74契约、74集成目录用例 |
| 既有重导入unittest | **3 tests OK，0.003秒，退出0** |
| 原提交快照与证据 | **102文件hash、68份Python语法、188个本地链接、敏感配置值扫描通过**；原始报告hash、JUnit数量及OpenAPI导出一致 |
| 真实API既有产物只读复核 | **11项通过**：完成状态、答案hash、任务完成、活动/已发布修订、原件hash、消息引用、来源、唯一终态、增量一致、事件顺序；本轮付费调用0 |
| Git | 审查开始时本地HEAD及远程main均为337297fb7a921cdec6fdcaad563d19fe5905d496 |

阶段命令：`M1_TEST_DB=m1_test_20261024_m2_controller`，`.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -m 'not live_provider' -q --junitxml=docs/development/evidence/M2-review-stage.xml`。PYTHONIOENCODING=utf-8，关闭文件/控制台业务日志，未设M1_LIVE_PROVIDER。289.46秒为pytest控制台结果，JUnit为289.451秒，外层进程297.406秒，不据此宣称性能变化。7条警告为PyMuPDF SWIG弃用提示。集成目录含纯逻辑探针及真实存储配合模型端口注入，不将74项全部称为供应商端到端。

既有命令：`.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q`。快照实际通过命令：`.venv/Scripts/python.exe -m scripts.verification.build_m2_artifacts --check`。直接文件入口在当前环境因scripts导入路径失败，模块入口通过；这是检查命令问题，不当成业务红测。

真实API复核只读原M2-live-api-first.json对应Mongo记录和MinIO原件，核对18条持久事件与答案/消息/引用，不重新登录、不重新派发或调用供应商。本轮不是再次完成新API真实HTTP验收；接受原51.593秒/一次回答的有效证据。独立输出见本机evidence/M2-review-stage.txt/xml、M2-review-reimport.txt、M2-review-runs.json、M2-review-live-recheck.json。

## R1 · P2 · 真实OpenAI SDK超时与连接异常被标为不可重试

位置：`app/ingestion/runner.py:26`–`39`。关联M2-10。

configured_runner实际使用OpenAI SDK进行图片摘要。classify_error只识别内置及requests网络异常，遗漏SDK的APITimeoutError/APIConnectionError。独立直接构造当前已安装SDK真实异常类型，不发网络请求：两者均返回`invalid_document_or_configuration, False`，预期为可重试上游错误。run_import会把该结果保存为failed/retryable=False，维护者retry接口随后拒绝；短暂供应商网络故障因此被当成永久文档问题。现有测试用内置TimeoutError、requests异常或合成status_code，未覆盖实际SDK类型。

要求：按当前真实客户端的异常类型进行分类，保留429/5xx可重试、401/403及格式/配置不可盲重试的区分，不以所有异常都重试绕过。明确连接错误与超时的公开code；检查SDK/httpx包装关系后补准确映射。

验证：先用实际SDK异常类补正式红测；覆盖超时、连接失败、429、鉴权、5xx与格式错误。另验证图片摘要异常经run_import落库后retryable为真、通过现有维护者/版本门禁可重试，并复用已完成检查点；不为错误分类重复付费。

## R2 · P1 · 已完成旧job遗留的过期发布许可永久阻止新修订

位置：`app/ingestion/runner.py:67`–`72`，关联`run_import`末尾许可清理、JobRepository.requeue_expired。关联M2-09/M2-10。

领取资料许可只接受“没有import_permit”或“同job且旧attempt”，未考虑其他job留下的过期许可。正常窗口为：旧job成功保存completed后、finally清理许可前进程退出；completed任务不会被过期任务扫描重新领取，许可留在资料上。后续同资料新修订的新job，即使自己租约有效且旧import_lease_until已过期，仍在此处ConflictError，随后被归为version_conflict不可重试。单纯等待租约过期不能恢复，新的修订持续失败。

独立Mongo探针通过真实KnowledgeRepository/JobRepository创建同资料两修订、两job；先将旧job正常保存completed，保留其许可并将期限设为过去，模拟上述崩溃窗口；新job正常claim后调用ImportRunner.execute，实际ConflictError，且新job租约仍有效。不涉及模型、Milvus或原课程数据。首次探针因缺originals属性报AttributeError，不计业务复现；补齐端口后v2/v3/v4均复现，其中v4明确旧job为completed。

要求：为遗留过期许可建立可重复、并发安全的回收/接管协议，同时保护仍有效的其他job和更高attempt；不能简单去掉最终发布fencing。考虑旧finally清理、旧心跳、新claim与指针CAS交错，确保旧执行者不能删新许可或迟到发布。更新恢复手册，不能仅靠人工清字段。

验证：先覆盖“completed后清理前退出→期限过期→新修订job”的正式红测；验证新修订能够继续并仅发布一次。覆盖有效其他job拒绝、更高attempt保护、过期接管竞争、旧心跳/清理/最终发布均不能影响新许可。采用新隔离目标，保留旧现场，不删除原服务或手工清数据来制造通过。

## R3 · P1 · 先释放会话再补助手消息，导致跨轮历史永久错序

位置：`app/runs/query_runner.py:182`–`185`、`app/runs/events.py:58`–`60`及`70`、`app/conversations/repository.py:60`–`78`；关联RunCommands.recover完成消息补偿。关联M2-11及M2-12。

完成CAS先释放active_run_id，随后才append_message；补偿写助手消息时再分配当前message_seq。上一轮completed已保存而助手消息尚未写入期间，下一轮用户问题可以正常创建并入库。恢复再补上一轮助手消息，实际顺序为`user(run1), user(run2), assistant(run1)`，ordinal为1/2/3。独立探针仅调用现有start→finish(completion_snapshot)→第二轮create→recover，确定性复现，没有强杀进程或伪造跨用户归属。

影响：历史API把上一轮答案展示在下一轮问题之后；若第二轮执行先于补偿，_history看不到上一轮答案；若在补偿之后，则按ordinal读取错误顺序。现有补偿测试只有单轮，证明不丢消息，但没有证明跨轮顺序与上下文正确。

要求：为完成消息投递与下一轮领取建立可恢复的顺序保证；可以在允许新轮前幂等补齐上一轮消息，或采用可靠持久序位预留并处理消息尚未物化的执行窗口。不能只在前端排序、修改时间戳、改写已有消息ordinal或取消失败后的恢复。保存终态/事件/outbox、消息快照及条件释放仍需幂等，多实例可核对。

验证：先补两轮正常函数红测，精确停在完成CAS后/助手写入前，创建下一轮并恢复，断言最终历史为user1/assistant1/user2/assistant2；另验证第二轮实际生成上下文包含正确的上一轮答案且顺序正确。覆盖消息写失败、实例重建、重复恢复/创建、分页、并发补偿和旧run不能释放新run；无真实供应商调用也能验证该窗口。

## 接受范围与接续要求

鉴权/会话范围、Origin与CSRF、请求幂等、持久状态与outbox、合作取消、正常Linux导入、新API真实问答及受控引用的已有有效结果保留。SSE并发投递补充探针见到seq1/2完整有序，未据猜测报告丢事件问题。取消仍是执行边界合作停止，生产灾备/全库迁移/大规模性能未验收，原有明确限制保留。

本轮真实写入仅独立回归小样及新m1_test总控探针库，保留现场。无原课程知识、桶策略、旧容器/卷清理，无真实配置/依赖/模型改动；原始evidence和既有evals/不上传。探针源码/输出M2-review-probes.py及v2/v3/v4均留本机，v4为最终有效复现；不把探针依赖错误当业务红测。提交快照在文档更新前已核对，旧manifest保持原时点，不回写以匹配总控文档。

允许开发会话只在M2内连续修复R1–R3，先正式红测再最小实现，分别维护任务记录与契约。重开M2-09/10/11/12，阶段8/12、核心28/76；其余任务不因本轮重做。修复后完整回归及既有重导入，定向验证上述失败窗口，先只读复核原真实API产物；仅当实际改动影响原证据有效性时再做必要的小样，不机械重复付费。

复审生成新的M2-submission-r2.md、实际摘要和独立manifest，保留本轮337297f、首轮快照、原始失败和总控探针。不硬编码326，检查器必须显式选定本轮新报告/快照并核对实际数量；旧检查工具如需支持参数同步改进。按用户授权正常提交/推送GitHub，阶段仅标待审查，等待总控审查M2；**不得进入M3，不含服务器部署或公开Release授权。**
