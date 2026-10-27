# M6-04/05/08：完整dev隔离语料与首次真实运行中断接续

日期：2026-10-27。起点 `main/bde79d14b82aeaa6d1cfe59be0417b80e1688c91`，开始与fetch后均核对origin/main一致。原未跟踪tmp、evals、全部原始证据保留，不上传。图片协议R1/R2总控已关闭，本轮没有修改业务源码、prompt、依赖、模型或默认策略，没有重复上轮全量回归。

**本轮完整dev尚未完成，M6仍4/7，M6-04/05/08未验收、阶段未提交，M7不启动。** 已完成完整语料准备，但85题真实执行在19题成功后遇到Mongo/Docker不可用；020失败、65题未完成。没有代填human、复制聊天双轮、创建新校准或声称质量提升。

## 完成的独立准备

冻结题集support-v2-r2共150题，dev85、heldout65；本轮不运行heldout。dev中31题具有审核标签资格，54题为辅助草稿，不能计入标准质量分。原三文档评测小样缺G540，影响50道fresh-dev；因此不能直接把旧两题结果当成完整开发集。

- 新随机Mongo数据库与Milvus集合均限定`m1_test_m4_m6_dev_`前缀，MinIO使用既有桶内全新`m4-test/m6-dev-`对象前缀。写前确认数据库、集合和对象目标为空且与源不重叠；没有改桶策略、建新桶或重建源集合。
- 原三份真实供应商资料只读复制595个完整向量切片及56个引用对象，保留稳定身份、来源与向量；目标登记的对象键/集合名替换为新隔离目标，原课程及旧评测无写入。
- G540原件SHA256为`977b5522d45fb1d3dfe8ac330c37841ad2751ffdfcbdaa64847ca753e78eff83`，24物理页。复用原MinerU content_list真实产物276块；14图逐张完整解码，用准确字节hash→历史Markdown图片→alt→旧摘要账本严格关联。最初按图片hash猜摘要文件名的方法未匹配，原报告保留；后续精确关联14/14通过，不将检查方法错误当业务缺陷。
- G540通过正式IngestionService/ParserRouter/MineruParser、切片器、图片资产/摘要缓存、真实本机BGE编码和Publisher完成新隔离修订：272切片、14图，published、quality_flags为空。PDF供应商适配器只读真实缓存，摘要回调只读已核对历史摘要，模型身份明确为`legacy-artifact-description`，不是新MinerU或视觉调用，也不是用合成解析结果冒充供应商结果。
- 独立续验确认四文档published、dev所有source_scope有覆盖、原三文档完整语料SHA未变。源SHA `dd01944db688807c158923c0d21d272f1f45aa4304aa9012efada71c2c18b810`；新目标SHA `81cd5d7583f6671a3ed66f85f4fa81e37cada0a79ae4d6d612533b4f81bb1481`。故障后服务不可用，不能声称已再次完成前后全量服务复核。

准备脚本实际退出1：在源只读上下文仍打开时改写共享config，退出核验因误用目标G540身份报“修订不在已发布授权范围”。这是工具使用错误；已完成的隔离导入不重做，不删除现场。原日志保留，用新进程分别加载独立源/目标配置只读续验，退出0。没有把这次工具异常当业务红测。

## 真实运行、故障与恢复尝试

新实验 `a5607e05-de22-4b24-9570-e85b7e09b521`，85题dev，固定seed20261026、metric_schema_version1、m4-configured；dense/sparse/fusion/rerank各20、context10、weighted 0.5/0.5、expansion/HyDE/decomposition/cache禁用，输出预算4096。代码/prompt/模型指纹及完整参数绑定在本机config和实验manifest；本轮不调参或选策略。沿此前Windows诊断方式在主线程串行预加载真实重排/embedding，未改设备/线程/权重；预加载成功不证明正常冷启动，也不声称Windows原生异常根治。

执行使用正式EvaluationService→持久实验任务execute_job→RealQueryExecutor→RunService→QueryRunner，真实Milvus/重排/LLM。所有者维护权限由数据库再次核对；每题独立run，成功结果持久检查点。**本轮未重新验证HTTP/Linux队列运输入口**，不将Python应用服务入口表述为全HTTP链路通过。

当前真实结果：19成功、020失败、65未完成。成功记录观测到stream_started19、invoke_started0；精确SDK HTTP次数/费用和失败窗口未完整采集，保持未知，不写本轮付费0。失败题记录ServerSelectionTimeoutError/provider_unknown_error/retryable=false，failure_stage=unknown，保留原分类，不为重试而手工改retryable。未知Mongo错误不能当作供应商可重试故障。

心跳因数据库失联丢失租约，runner在边界停止，本地manifest为cancelled并保存20条attempts/results；随后向Mongo发布终态、异常收敛也因连接超时失败，宿主进程退出1。磁盘cancelled不证明Mongo终态或占用已释放，当前无法读取数据库最终状态。成功题19条是已保存结果，不是完整报告通过。

故障时Mongo TCP可连但ping超时，配置MinIO/Milvus端口可连；Docker引擎查询超时。WSL仍响应，Docker后端日志持续报告引擎_ping/init control API未就绪；没有证实根因为OOM、模型或数据，未臆测。恢复尝试：官方Docker Desktop restart超时退出1；仅终止docker-desktop WSL发行版退出0，再次官方restart因旧进程仍在退出1，最后引擎查询超时。没有强杀整组进程、终止Ubuntu、清卷、重建容器或重新导入。

## 本轮实际验证与命令

命令从项目根PowerShell、原.venv执行。全部原始输出在`output/m6-dev-readiness-r1/`，原件不上传；[脱敏摘要](M6-08-full-dev-baseline-validation-r1.json)绑定本轮原始脚本、日志和报告hash，[独立快照](M6-08-full-dev-baseline-manifest-r1.json)绑定提交文件，不覆盖历史材料。

| 验证 | 实际结果 | 退出码 |
| --- | --- | --- |
| 新隔离语料准备 | 写入完成，末尾工具配置核验错误 | 1 |
| 新进程独立源/目标语料续验 | 四文档覆盖85 dev、G540272切片/14图、源SHA一致 | 0 |
| 完整dev首次真实执行 | 19成功/1连接失败/65未完成 | 1 |
| 原001故障前正式HTTP只读 | 12检查通过，旧答案/评分/校准/单次聊天不变、两图hash/完整解码 | 0 |
| 中断本地产物只读 | 20检查通过，冻结选择、划分、计数、日志/结果、独立重算汇总一致 | 0 |
| 中断报告Edge离线核对 | 5检查通过，20条可见/错误说明/无人工提交或云读取 | 0 |
| 官方Docker恢复 | 启动超时；定向WSL生命周期后再次停止超时 | 1、1 |

上述检查覆盖不同层，**不累计为唯一测试总数**。本轮未运行pytest/既有重导入/前端单元/全浏览器/typecheck/build；历史1015等结果不算本轮执行。完整85题产物只读核对、完整答案/切片/图像报告脚本已备但因运行未完成而未执行，不声称通过。

```powershell
.venv/Scripts/python.exe -X faulthandler -c "import runpy;runpy.run_path('output/m6-dev-readiness-r1/prepare_corpus.py',run_name='__main__')" *> output/m6-dev-readiness-r1/prepare-corpus.log
.venv/Scripts/python.exe -c "import runpy;runpy.run_path('output/m6-dev-readiness-r1/verify_prepared_corpus.py')" *> output/m6-dev-readiness-r1/verify-corpus.log
.venv/Scripts/python.exe -X faulthandler -c "import runpy;runpy.run_path('output/m6-dev-readiness-r1/run_full_dev.py',run_name='__main__')" *> output/m6-dev-readiness-r1/run-full-dev.log
.venv/Scripts/python.exe -c "import runpy;runpy.run_path('output/m6-dev-readiness-r1/recheck_old_001.py')" *> output/m6-dev-readiness-r1/old-001-readonly.log
.venv/Scripts/python.exe -c "import runpy;runpy.run_path('output/m6-dev-readiness-r1/verify_partial_artifacts.py')" *> output/m6-dev-readiness-r1/partial-readonly.log
node output/m6-dev-readiness-r1/verify_partial_browser.cjs *> output/m6-dev-readiness-r1/partial-browser.log
docker desktop restart --timeout 45
wsl --terminate docker-desktop
docker desktop restart --timeout 45
```

本地可阅读[首次运行中断记录](../../../output/m6-dev-readiness-r1/首次运行中断记录.html)，只显示已有答案/引用和失败，不声称有尚未导出的实际切片正文。不是让用户重新填写已有判断。

## 必须保留的接续点

1. 恢复现有Docker Desktop，引擎可响应后只读确认Mongo ping、Milvus/MinIO可用；不要重建源或目标。私有目标和新账号只在本机target-private/execution-session-private.json，不打印或提交。
2. 只读核原实验、020 run、attempt/token/lease、evaluation_slots及会话占用；旧执行进程已退出。数据库终态未知时禁止宣称已释放，更不能直接删state/lease/slot。依正式取消/自然到期重新领取/RunCommands.recover协议收敛原任务；原磁盘manifest/attempts/results先另存hash绑定备份。
3. 复用原冻结config/完整语料及19个成功检查点。不要直接重跑run_full_dev.py：它只用于首次建目录、账号和实验。020真实run可能已完成、running或interrupted，必须读事实；可恢复的继续、不可恢复的保留失败另建有明确来源的后续尝试，不把未知错误改成retryable。不承诺失败窗口exactly-once。
4. 只有完整85题均执行并完成独立持久/切片/图片核对后，才能更新完整dev技术结论。新规则独立人工双轮、预校准、新候选比较、反馈后人工复评和固定报告验收仍缺；现有聊天2/2/N/A/0只一次，不复制为两轮或冒填human。旧基线2/1/1/0及校准保持不可变，不凑分通过。
5. 本轮仅文档/脱敏摘要/快照提交，阶段未提交；M6-04/05/08不勾选，M7未授权。当前可独立完成的语料准备与本地留证均已保存，外部服务恢复后接续。

回滚只需停止引用新catalog/实验，依正式取消协议处理活动账本；文档可正常revert，保留所有隔离库、向量、对象和失败证据，不删除数据。无新增.env配置/依赖/运行参数，旧服务未换为新目标。提交自身SHA和推送核对在最终交接补记，不循环amend。
