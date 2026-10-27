# M6-04/05/08：单题校准、真实低分反馈与候选接续

日期：2026-10-27。起点main `7de85ceaaf9779cfa33b76b089d3c8caa82dc036`；用户接受双轮追加核验并要求按顺序继续。此次不是总控复审或M6阶段提交。M6核心仍4/7，04/05/08未验收，M7未授权。默认顺序执行，无子代理。没有业务源码、prompt、模型权重、依赖或默认策略改动。

当前：正式API冻结基线2/1/1/0，登记真实低分及原人工依据指纹为执行助手转录的反馈回归草稿，之后建立新的隔离候选并真实生成。第二候选已completed；其人工评分0条，发布门槛pending。**这是反馈后独立执行，尚未完成人工复评或证明质量提升。** 配图0是比较基线的一部分，候选0对0也可能满足非劣化，不能解读为配图达标。

| 对象 | 身份/状态 |
| --- | --- |
| 原基线 | `878abb8c-6d55-483e-b1a1-b7458c19d0e0`；原human2、追加2保留 |
| 校准 | `789deda3-ada9-4497-8263-799cd3da263b`；零容差，事实2/引用1/步骤1/配图0 |
| 低分反馈 | `c34496c4-c065-5765-93a5-4ba9a9167e55`；confirmed，regression/draft，执行助手转录/审核身份 |
| 首候选 | `41f44ee8-5bb8-4e6d-9ba4-3544781d8e0a`；原生异常后正式取消恢复为cancelled |
| 第二候选 | `f0ac6186-b204-4987-bb14-0089f3b73996`；completed，result_attempt=1，新增正式run1个 |
| 候选质量门槛 | pending / review_pending_or_changed；human_review_count=0 |

服务端顺序（UTC）：校准07:31:45.344004 → 低分审核草稿07:31:45.628742 → 首候选07:31:46.088163。第二候选07:37:44.753099创建，同样晚于校准及草稿。第二次准备正式重放校准、反馈、审核，复用原ID和全部内容，没有新建第二份校准/反馈或覆盖旧记录。

## 真实失败和恢复

首轮命令`python -m tmp.m6_001_calibrated_execute`退出1，候选在rerank阶段宿主消失；Windows事件1000精确匹配PID29276（0x725C）、2026-10-27 15:33:32.9518168+08:00、torch_cpu.dll/0xc0000005。Python日志无可用异常栈，根因没有证实，不归咎题目或云供应商。run后来由原API租约扫描收敛interrupted。未观察到答案生成事件，不以缺失日志冒称精确SDK调用或费用为0；本轮成功候选明确有1次逻辑答案生成。

先POST `/experiments/41f44ee8-5bb8-4e6d-9ba4-3544781d8e0a/cancel`，expected_version取当前正式账本；HTTP200/cancel_requested。确认原PID不存在，解析其`.runner.lock`并移至首轮目录`native-crash-runner-lock.json`保留。租约自然过期后调用正式`execute_job`，提供仅允许取消、不允许调用题目的上下文执行器；原cancel_intent使runner在调用任何题目前停止。结果cancelled、attempt2、slot释放。没有手工改state/lease或删数据来通过。该取消恢复使用禁止生成的执行器，明确不是模型或质量验证。

诊断第二候选仅把真实CPU重排模型放到宿主主线程串行预加载，再启动相同正式宿主；没有修改设备、torch线程数、权重、依赖或模型策略。预加载单对通用文本不调用供应商。Linux单并发专用worker随后执行同一正式RunService→QueryRunner→Milvus/真实重排→生成。不能将预加载成功当作正常冷启动验证或原生异常根治，也没有因结果选优改变默认配置。业务代码/冻结题集/标准标签完全未改，本轮不制造代码红测。

## 实际命令和范围

命令均在项目根PowerShell使用现有.venv Python3.12.7；逐命令退出码见[脱敏摘要](M6-08-calibrated-candidate-r1-validation.json)。临时脚本仅本机tmp，SHA已绑定到摘要。

```powershell
.\.venv\Scripts\python.exe -m tmp.m6_001_calibrated_prepare
.\.venv\Scripts\python.exe -m tmp.m6_001_calibrated_execute
# 上一条实际失败退出1；先保存Windows事件、取消恢复，不把它计为通过。
.\.venv\Scripts\python.exe -m tmp.m6_001_calibrated_prepare_r2
.\.venv\Scripts\python.exe -m tmp.m6_001_calibrated_execute_r2
$env:M1_TEST_DB='m1_test_m6_calibration_followup_20261027'
.\.venv\Scripts\python.exe -m pytest tests/integration/test_evaluation_reviews.py tests/integration/test_feedback_triage_workflow.py -q --junitxml=output/m6-08/001-calibrated-r2-20261027/targeted.xml
.\.venv\Scripts\python.exe -m tmp.export_m6_001_calibrated_sources_r2
.\.venv\Scripts\python.exe -m tmp.m6_001_calibrated_verify
node tmp/m6_001_calibrated_browser.cjs
```

- 定向pytest **41 passed、0 skipped**，退出0，全部为真实隔离Mongo/HTTP协议集成；评分/答案为测试合成/注入，不是本人评分。
- 新候选真实API/持久账本 **15/15只读检查**，退出0；结果/引用/消息/唯一终态/占用释放、校准绑定、顺序、缺人工时pending均成立。
- 真实Edge **10/10只读检查**，退出0；题目、答案、物理第4页来源和两张图片完整解码显示；浏览器没有POST人工评分。
- Milvus真实入选10切片正文和来源精确相等；2图像hash/解码通过，另正式图片HTTP200/hash/解码均通过。这些不替代人工相关性。
- 真实完整语料在前后只读复核：SHA仍`dd01944db688807c158923c0d21d272f1f45aa4304aa9012efada71c2c18b810`。原件、索引向量、图片、产品和活动快照不变。
- 正式成功候选逻辑`stream_started=1 / invoke_started=0`；精确SDK HTTP次数/费用未知。与首个失败分开记，不写“本轮付费0”。成功题不是旧检查点复用；旧基线人工和知识摘要前后相等。
- 本轮未运行完整后端、重导入、前端单元/typecheck/build，也未运行全dev/heldout；历史951等不计本轮结果。无新增业务源码，无需将无关全量重复当完成条件。

原始产物分别在`output/m6-08/001-calibrated-r1-20261027/`与`output/m6-08/001-calibrated-r2-20261027/`；原失败、旧manifest、总控探针全保留。新实验逐题manifest/attempt/results在原work_dir下新UUID目录；当前代码、prompt及本机模型指纹已在新candidate.json/运行manifest记录，没有沿用原基线代码指纹冒充本轮版本。

## 接续与数据边界

新审阅入口：http://127.0.0.1:5176/evaluations/reviews/f0ac6186-b204-4987-bb14-0089f3b73996 ，沿用原本机账号。题目和引用已通过真实浏览器检查。新[回答与切片对照（含图）](../../../output/m6-08/001-calibrated-r2-20261027/001-source-review-20261027-153932/001回答与切片对照.html)便于无需Milvus账号核对。旧基线不需要再提交；新候选是不同结果，不能复制旧human或代填两轮。用户本人据本轮答案重新核对并保存两轮，不确定保持未知，配图继续0亦如实保存。

只有单题人工完整性满足的基线被冻结；没有全dev校准，不能拿此单题证明当全dev门槛。候选人工复评→读取与原校准的差异→完成全开发集基线/校准/回归和固定报告，后续才有完整M6材料。本轮回归草稿没有变成冻结真值，也未创建无依据的新资料修订或调用资料发布quality-proof；资料修订路线的affected/full证明不冒称通过。

本次只写既有`m1_test_m4_m6_review_`小样的校准、反馈、实验/运行/消息/检查点，以及全新的独立测试库。MinIO/Milvus仅只读，未改课程目标、存储桶权限或原件。没有新增.env配置、依赖或包安装。临时宿主和专用worker已停止，原审阅API/前端保留；tmp、output、原始evidence和evals不上传。

回滚：文档可正常revert；若停止候选流程，保留校准/反馈/候选和旧人工记录，用正式取消协议处理活动实验，不删账本或重建库/集合。临时预加载宿主不是业务默认改动，停止即可。仍保留Windows原生崩溃风险，不能声明根治。

见[本轮独立快照](M6-08-calibrated-candidate-r1-manifest.json)。提交及推送SHA在最终交接补记，不循环amend自身SHA。
