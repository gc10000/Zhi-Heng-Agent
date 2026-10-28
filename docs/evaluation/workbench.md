# 评测工作台与任务恢复

## 有来源的后续实验与中断Run（2026-10-27）

不可自动重试的实验保持失败及原`retryable=false`，不以恢复服务为由改写终态。维护者可显式创建具有源实验ID的后续请求；正式M6 job以`client_request_id:experiment_id:attempt`作为本次执行键。适配器仍复用completed Run；只有带明确执行键且旧Run已为`interrupted`时才用包含旧Run ID的独立请求键创建新Run，旧Run与事件不覆盖。普通调用不自动重新生成，非retryable失败不因提供执行键而放行；活动Run仍受原占用/租约协议约束。该路径不承诺失败窗口exactly-once或已知费用。

代码指纹变化时不得修改原冻结配置或继续冒充原版本；另存派生配置及目录，记录代码差异和源/目标hash。继承成功题须逐题核对源结果、持久Run及输入hash，另存来源清单和新配置键，不能复制失败题冒充成功或新生成。继承结果与本轮新结果须在固定报告中明确分列，原失败文件及实验保留。

## 2026-10-27 · 完整dev运行与故障恢复边界

新隔离四文档已覆盖85题dev；真实首次运行19成功、1连接失败、65未完成，Mongo/Docker故障及恢复失败证据保留。成功记录观测逻辑答案stream19，精确SDK HTTP/费用及失败窗口未知；未写人工、校准或聊天来源，未运行heldout。新规则双轮/预校准/候选比较仍未完成，原聊天判断不重复。M6-04/05/08保持未验收、核心4/7、总核心64/76，M7不启动。恢复服务后先核原任务和租约，正式收敛后复用成功检查点；不重导入、不手工清字段，不直接重跑首次创建脚本。详见[完整接续及实际验证](../development/reviews/M6-08-full-dev-baseline-r1.md)。

M6-03采用服务端受控题集/配置目录、Mongo所有者账本和独立Celery队列。浏览器只能提交已登记ID/版本，不接受路径、标准答案或客户端指标。普通用户无维护权限；维护者只能读取自己的题集、实验和题级结果，并再次核对当前知识范围。登记不将草稿升级为已审，heldout不能从工作台派发。

## 配置和启动

根目录`.env`新增`M6_EVALUATION_CATALOG`、`M6_EVALUATION_WORK_DIR`、`M6_QUEUE_NAME`，说明见[配置手册](../CONFIGURATION.md)。API/模型宿主共享同一`M2_DB_NAME`账本和冻结catalog；评测配置的target仍限`m1_test_m4_`库/集合与`m4-test/`前缀。请勿把业务课程库配置为评测目标。

catalog形状如下。所有文件路径相对catalog所在目录，拒绝绝对路径、父目录、编码路径、反斜杠和越界符号链接；不得把该本机目录提交Git。

```json
{
  "datasets": [{"id": "support-dev", "version": "r1", "dataset": "datasets/support.jsonl", "manifest": "datasets/support-manifest.json", "kb_ids": ["评测授权知识范围"]}],
  "configs": [{"id": "control", "version": "v1", "path": "configs/control.yaml"}]
}
```

配置必须绑定题集文件hash、划分manifest文件hash、真实代码/模型/prompt版本、seed，且`phase=development`、`split=dev`、`execution_mode=real_query_runner`、`metric_schema_version=1`。保持M4完整语料快照和题集接受结论门禁；版本变化须另建配置、输出与登记版本，不修改旧产物。目录/登记不暴露原始文件路径或标准答案。

从项目根目录启动模型宿主（沿用既有`.venv`，不安装/下载新模型）：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.infrastructure.model_host:app --env-file .env --host 0.0.0.0 --port 8011
docker compose --profile tasks up -d --no-deps redis
docker compose --profile evaluation build evaluation-worker
docker compose --profile evaluation up -d --no-deps evaluation-worker
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

模型宿主只允许本机/Docker访问，已有`MODEL_HOST_TOKEN`认证；不公开端口至外网。Linux worker仅携带实验UUID调用固定`POST /evaluation-jobs/{id}`，不传配置/路径/原件/私有prompt；宿主按本机受控目录重新解析、核对指纹并执行。选择此分工是因为现有Linux导入镜像没有PyTorch/FlagEmbedding/模型权重，评测不能在容器重新下载模型或冒称版本一致。

问答执行不进入评测队列。导入worker显式只消费`M2_QUEUE_NAME`，评测worker显式只消费`M6_QUEUE_NAME`，并发1、prefetch1；宿主每进程只有1个评测槽，每所有者只允许1个活动实验。该预算防止评测占用问答线程池/导入消费槽，**不代表共享GPU或供应商没有资源竞争，也不是生产延时保证**；模型调用仍经过既有共享小批与推理锁。只能以独立容量实验评价生产影响。

## 状态、取消和恢复

### 显式continuation来源（2026-10-28）

R1/R2补修追加：正式job在模型执行之前写入私有`evaluation_execution_links`，唯一身份为experiment/attempt/question，内容绑定owner/kb、输入hash、完整config/checkpoint指纹、Run与conversation。写入校验当前任务worker/attempt/租约，worker token不存入来源记录；身份字段不可覆盖。`mode=execution`表示当次任务准备执行该Run，`mode=observed_reuse`表示当次任务实际观察并复用已有Run，不证明原始生成归属或新增计费。普通executor缺少正式执行身份时不创建已认证题级关联。

continuation在新Run创建之前重新核对声明父experiment/attempt/version及上述同题/同输入/同配置/同checkpoint/同Run关联，并将父link ID和hash写入后续账本；父实验存在且同配置不足以放行。另一父实验、上一attempt、输入变化、历史缺link或旧continuation缺认证链均拒绝新增生成，明确报父题级来源未核实，走单独留证和审核流程；没有自动认证、回填或导入旧关联的入口。新实验对completed checkpoint的当次观察复用可以建立自己的observed_reuse记录，不向旧父实验回填。

M6新结果`logical_provider_calls_scope=run_total`，`logical_provider_calls`读取持久Run累计遥测，供题级/实验汇总；`execution_logical_provider_calls`仅为当前adapter调用的进程counter差值，未观测null。Run完成但结果尚未落盘时退出，恢复可同时报告累计stream1和本次新增0；结果重复落盘/读取不能把累计改0或加为2。新澄清路径将当次明确测得的零值随等待事件持久化，历史缺测仍null；精确HTTP/费用继续未知。本次新增字段不改变旧结果内容或追认其计数范围，混合历史报告仍按原分列身份解释，不能把Run累计当本轮新费用。

`POST /experiments`可带`continuation={source_experiment_id,source_attempt,source_version,reason}`。父实验由服务端按当前owner/kb读取，必须是failed/cancelled/incomplete终态且attempt/version、dataset/manifest/config字节指纹匹配；失败可重试标记不修改。已完成实验的质量比较继续用baseline，不使用continuation。省略与显式null等价，同client_request_id变更来源409；父来源缺失或越权404，活动/过期/冻结身份不匹配409。该协议只支持相同冻结配置；修改源码导致runtime code身份变化时，不能将新配置当旧版本续跑，也不自动迁移任何检查点。

普通job首attempt不赋予中断重生成资格。只有显式continuation才能为已收敛interrupted Run派生新请求；已完成题仍按原config/question checkpoint复用，非retryable failed Run仍拒绝。调用之前在私有`evaluation_continuations`集合用新experiment/checkpoint稳定键`setOnInsert`保存父experiment/attempt/version快照、父Run/输入身份/固定request_key；RunService创建后先绑定新Run，再执行。创建Run后、checkpoint绑定前崩溃，原请求重发仍复用同一Run。重复/重新领取同一个continuation固定请求，后续Run再次interrupted时停止，不自动派生第三条付费Run。

账本单列逻辑invoke/stream与token usage（只从实际Run遥测观察，缺失null），精确HTTP次数和费用保持null，不能把prepared或调用边界故障记为付费0。原失败/中断Run及旧结果不改，账本不是供应商计费明细，不承诺失败窗口exactly-once。r3已存的19继承+66执行材料保留历史身份，不为通过新门禁回填或重跑。本轮只运行隔离合成测试，未执行模型、heldout或人工评分。

Mongo是任务状态事实来源。创建先持久化`pending/dispatch_pending`，API后台每15秒扫描；broker成功后确认，未领取的任务60秒后允许重投，重复消息由条件claim拒绝。运行保存attempt/token/租约，后台每10秒续120秒租约；过期`running/cancel_requested`可重新领取，旧代结果不能发布可见指针或释放新实验占用。

取消带`expected_version`。排队直接取消并释放自身；运行中保留取消意图，在当前题结束边界停止，保留完成结果。浏览器退出不取消任务，同步模型请求无法硬中止，不能把已发送请求记成未计费。失败只保存安全错误码；超时/连接/429/5xx等已分类失败可以由维护者带版本重试，鉴权/格式/未知失败不自动重试。重试沿原输出和成功题尝试日志恢复；显式重试失败题用新的持久run请求身份，成功题不重复调用模型。供应商响应到检查点提交之间仍存在计费窗口，不承诺exactly-once。

结果按attempt独立保存，CAS成功后才发布该attempt的结果指针。题级API分页按question_id；基线必须是同用户、同知识范围、同题集版本与hash的已完成实验，按题身份比较答案/状态。文本变化只报告差异，不能声称质量提升；未采集的token/费用与未审答案语义正确性保持未知。

异常进程留下`.runner.lock`时，先保留现场，核对任务attempt/租约和宿主进程确已退出。不得在线删除仍有执行者的锁；人工核验后将旧锁另存本机证据再恢复，不覆盖attempts/results/manifest。不能用清空数据库、删除缓存或重建集合恢复。终态与预算回收中断时，新请求仅回收账本确认已终结的旧占用；排队时间本身不会让有效占用失效。

## 验证边界

用户本人操作的M6固定报告只在本机5176提供；账号/完整配置位于被忽略的output。当前使用已有dev两题和原三资料小样，只读复用源向量/对象，新建隔离登记和运行账本；一题澄清、一题图文答案。两题可审不等于完整开发集/真实反馈验收，不能以检查点复用替代独立生成。人工双轮后仍须校准、候选和真实反馈复评门禁，详见[M6-08记录](../development/records/M6-08.md)。

离线浏览器使用明确的协议模拟，只验证Vue交互，不称真实模型评测。Mongo集成仅使用显式`M1_TEST_DB=m1_test_...`随机子库及合成输入；真实模型/Redis/Linux端到端证据需独立记录。原始题集、答案、对象链接、输出和课程原件保留本机，不上传Git。复现的精确命令与数量见[M6-03记录](../development/records/M6-03.md)。
