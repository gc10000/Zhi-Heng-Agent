# M6-08：修复后001真实隔离接续（部分交付）

状态：M6阶段未提交，04/05/08未验收，核心4/7；M7未授权。R001-1已由总控关闭，本轮未修改业务源码或测试。起点main：`f3b0d4389a2e6384e4515d134d93714378005e1a`，远程核头一致。历史933项后端、3重导入及前端回归未在本轮重跑，不计作本轮结果。

## 行为与实际结果

旧001明确LA2608-GM/GU却进入澄清，没有答案/引用；原失败不变。修复后仅选择已曝光dev `support-v1-001`，使用新隔离Mongo、实际代码/模型/prompt指纹，经正式API→独立Linux Celery→认证Windows模型宿主完成。新实验`878abb8c-6d55-483e-b1a1-b7458c19d0e0`，新run `6187c269-0cef-48a2-9a47-3b1f4c3351ec`，保存425字答案和10条引用。实际代码指纹`c587205af5b679e6941ebac12214dcf6c81c0daa6c691be0fb8df4f284080a4e`（完整模型/prompt指纹绑定本机manifest）。

答案首段说明不能与任意品牌控制器互通，引用[1]对应chunk `576af7ff-e4c6-56c5-be84-57538905e977`、原PDF物理第4页“目前，LA2608只支持与H3C公司的无线控制器互通。”PDF SHA256为`72983cc9b60f7f165bf89d3f6cbe39d56c4db148fd4b894c70c37378f8be5c8e`。逐一核对10个引用切片正文/来源，2图片hash及完整解码；技术关联通过不等于全部答案人工正确。

真实只读初次/恢复UI后各15项，真实浏览器初次/恢复后各8项，退出均0；两次不是30/16条独立测试。新执行器检查点复用1题，完成1/失败0、run数1→1、核心结果一致、0新增调用，不是第二次独立生成。逻辑stream1/invoke0，精确SDK HTTP次数/费用未知，不能写付费0。未运行heldout、全dev，不调整默认策略。

## 反馈与人工边界

执行助手将用户旧001实际观察转录，经正式反馈接口和维护者审核形成confirmed regression draft（feedback_id `ff45ecf4-4b82-5f3b-a31d-808ec5ae485e`，annotation_status=draft）。创建/审核及其幂等重放、草稿状态、旧run/results/messages/reviews未变，6项退出0；0新模型调用、0human评分写入。新真实查询发生在本次正式草稿保存之前，`closed_loop_complete=false`，后续反馈后复评仍未完成，不改变时间顺序或声称闭环验收。

旧045本人双轮及unknown保留，不移植到新实验、不要求重审。新001当前human评分0、校准0；必须用户本人独立分两轮核对，不代填。审阅页`http://127.0.0.1:5176/evaluations/reviews/878abb8c-6d55-483e-b1a1-b7458c19d0e0`；原件与引用从会话`http://127.0.0.1:5176/chat/869470c8-9582-4e39-95a8-307ba88574b5`查看。本机说明和账号位于`output/m6-08/001-repaired-r1-20261026/新001人工核对说明.md`、`本机审阅账号.txt`；不能上传凭据。无需Milvus地址，独立对照位于`output/m6-08/001-repaired-r1-20261026/001-source-review-20261026-230755/001回答与切片对照.html`。

## 精确命令、证据和退出码

项目根PowerShell、`PYTHONUTF8=1`；下表命令均已实际执行，退出码0。tmp脚本是本机验证编排，不作为业务源码提交。

| 命令 | 结果/本机证据（相对output/m6-08/001-repaired-r1-20261026） |
| --- | --- |
| `.venv/Scripts/python.exe tmp/m6_001_repaired_environment.py prepare --output output/m6-08/001-repaired-r1-20261026` | 1题、3来源准备，源不变；preparation.json |
| `.venv/Scripts/python.exe tmp/m6_001_repaired_environment.py serve --output output/m6-08/001-repaired-r1-20261026` | 真实查询完成；results/；后续stop-requested正常退出0 |
| `.venv/Scripts/python.exe -m scripts.verification.recheck_m6_review --session output/m6-08/001-repaired-r1-20261026/private-session.json --identity output/m6-08/001-repaired-r1-20261026/baseline-identity.json --report output/m6-08/001-repaired-r1-20261026/readonly-r1.json` | 15检查，原件HTTP hash1、图片HTTP hash/解码2 |
| `.venv/Scripts/python.exe -m tmp.export_m6_001_repaired_sources` | 10切片/2图片；001-source-review-20261026-230755/verification.json |
| `.venv/Scripts/python.exe -m tmp.m6_replay_001_repaired` | 1完成/0失败，无新调用；checkpoint-replay-report.json |
| `node tmp/m6_001_repaired_browser.cjs` | 8项、未提交评分；browser-ready.json |
| `.venv/Scripts/python.exe -m tmp.m6_001_feedback_record` | 正式反馈/审核6检查；feedback-transcription.json |
| `.venv/Scripts/python.exe -m tmp.restore_m6_001_repaired_ui` | 仅恢复新账本API/Vite，未启模型宿主/worker；restore-20261026-231359.json |
| `.venv/Scripts/python.exe -m scripts.verification.recheck_m6_review --session output/m6-08/001-repaired-r1-20261026/private-session.json --identity output/m6-08/001-repaired-r1-20261026/baseline-identity.json --report output/m6-08/001-repaired-r1-20261026/readonly-r2-restored.json` | 恢复后15检查、0新调用 |
| `node tmp/m6_001_restored_browser.cjs` | 恢复后8检查；browser-restored.json |

output/m6-08/001-repaired-r1-20261026在上述表中精确展开为`output/m6-08/001-repaired-r1-20261026`。这轮没有逻辑实现修改，无需新业务红测。曾读取不存在文档、误定位results/manifest路径及内联Python换行SyntaxError，均为定位/编排错误，不当作业务失败或验收测试；原始现场保留。

摘要与独立快照显式选择本轮文件：

```powershell
.venv/Scripts/python.exe -m scripts.verification.build_m6_artifacts --summary docs/development/reviews/M6-08-001-live-validation.json --manifest docs/development/reviews/M6-08-001-live-manifest-final.json --base f3b0d4389a2e6384e4515d134d93714378005e1a
.venv/Scripts/python.exe -m scripts.verification.build_m6_artifacts --summary docs/development/reviews/M6-08-001-live-validation.json --manifest docs/development/reviews/M6-08-001-live-manifest-final.json --base f3b0d4389a2e6384e4515d134d93714378005e1a --check
git diff --check
```

最终重新运行旧浏览器脚本时，8条页面检查均为true，但保存报告使用wx且原报告已存在，退出1；这是证据防覆盖错误，不是业务失败。改用新脚本`node tmp/m6_001_final_browser.cjs`输出到全新browser-final.json/review-final.png，8项通过、退出0，原报告未覆盖。首次12文件/303链接快照保留，最终快照另名保存。

## 数据范围、恢复与接续

随机独立Mongo只保存本次评测/会话；原M4隔离Milvus/MinIO只读复用，原源Mongo/语料快照未变。旧账本只新增上述反馈及draft，原运行/结果/消息/评分hash不变。未修改课程知识、冻结标签、活动指针、配置、依赖、接口或发布知识。

原报告、失败证据和总控探针全部保留。Git仅提交本轮文档/脱敏摘要和hash，排除tmp/output/evals/原始evidence、账号、原PDF与图片；自身SHA在最终交接补记，不循环amend。当前只保留新账本审阅API/Vite，专用模型宿主与worker已停止；人工打开页面不重新调用模型。回滚可停止这组UI进程并反向本轮文档提交，保留全部账本/证据，不删集合或对象。

下一动作：用户本人核对新001并分两轮如实保存；助手只读核对身份/内容指纹及未知项，再推进校准/候选及按顺序反馈后复评和全dev回归。未知/错误不改分，未满足门槛不勾选M6，不进入M7。
