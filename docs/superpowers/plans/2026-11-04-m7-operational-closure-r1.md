# M7 Linux与真实演示收尾执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用superpowers:executing-plans连续执行。本轮建议授权仅1位独立审查Agent，不使用按任务多Agent实施。各步骤使用复选框跟踪。

**Goal:** 在原r3限定独立通过基础上，完成现有Linux路径、8槽真实演示、恢复/容量及发布材料的完整工作包。
**Architecture:** 继续现有正式API/Run/QueryRunner及受控模型桥接，原18080保持关闭，新隔离项目仅白名单生成。Linux环境身份、答案质量与公开发布分列。
**Tech Stack:** WSL2 Ubuntu、Docker Compose、Vue/FastAPI、Mongo/MinIO/Milvus/Redis/Celery、既有embedding/reranker、qwen3.8-flash。
**Spec:** [完整执行Prompt](../../development/handoffs/M7-operational-closure-execution-r1.md)。所有调用/资源/故障/委派边界以该文件为准。

## 全局约束与授权状态

用户已明确采用并执行本包；以下建议范围按用户实际授权生效，本计划自身不充当授权。实际出口：来源临发首失败，provider0、本地embedding5，r1已STOP/halt；其余独立工程完成或实证封存，见[执行报告](../../development/reviews/M7-operational-closure-r1.md)。建议新增最多8个stream，输入227328/输出32768预算，unknown硬限明示；本地推理限2资料/32chunk、64embedding文本、8rerank/512pairs，1名独立审查者。首失败停止新真实派发，其他工程继续。
原r3应用实现b4d3ec77、归档817f913；新提交以实际为准。M6债务、旧槽、blocked/0proof/halt保持。主环境、main、原18080和旧证据不改。

### 任务1：Linux身份及部署适配

**Files:** 读/必要修改scripts/operations/prepare_preview.py、preview.py、compose.delivery.yaml；更新docs/runbooks/ubuntu-deploy.md、dependencies.md。只在有真实移植缺陷时增加定向测试，不为文档写镜像测试。

- [x] Windows只读检查：`git status --short`、`git rev-parse HEAD`、`git ls-remote origin refs/heads/codex/m6-source-bound-comparison refs/heads/main`、`wsl --list --verbose`、`docker context show`。
- [x] 采用授权后运行`wsl -d Ubuntu -- bash -lc 'cat /etc/os-release; uname -r; command -v docker; command -v python3'`，静默核Docker daemon归属及存储/端口。
- [ ] 选Linux本地新目录和独立项目，从固定源码/锁运行实际Compose解析/部署，保存精确命令/OS/daemon/image身份。Desktop daemon只签WSL兼容，不冒充原生Ubuntu服务器。
- [ ] 发现路径/权限/依赖问题先保存失败，修复相应文件并定向回归；系统级安装不自动执行。Linux缺项不阻断后续Windows新隔离项目。

### 任务2：真实演示输入和额度接线

**Files:** 复用app/runs/{service,query_runner}.py、app/infrastructure/providers/output_contract.py及现有ledger实现；必要新增scripts/verification/m7_real_demo.py、tests/contract/test_m7_real_demo_admission.py、tests/integration/test_m7_real_demo_budget.py。新增名称是本计划拟实现入口，不宣称已存在或指定不存在的签名。

- [ ] 按Prompt冻结8请求、版本化CC0来源、真实索引、模型/SDK、输入上限/引用和新槽，盘清所有模型角色及本地调用量。
- [x] 只在用户真实采用授权后写新授权记录；实现最小正式服务适配，不能复制旧授权或绕过API。
- [x] 对“未授权创建拒绝、并发额度唯一消费、未知usage/断流停止、恢复不重发、旧槽不消费”保存能揭示缺陷的合成测试与红绿日志，仅随机隔离Mongo。
- [ ] 冻结当前源码与可审阅输入，由本轮唯一独立审查者定向复核新调用边界，通过后派发。

### 任务3：8槽执行、实际恢复及浏览器

**Files:** 新演示入口、scripts/verification/restore_preview.py、frontend/tests/e2e/delivery-live.spec.ts（或新real-demo专用用例）；docs/demo/scenarios.md、docs/evaluation/capacity-report.md、docs/runbooks/backup-restore.md。

- [ ] 按1/2/4波依次执行7次，每波结算/核停止条件，记录真实模型输出、引用、usage、时延及资源采样。
- [x] 停写新资料，实际备份/恢复到全新三目标，共用恢复控制库，核预算/输入身份归属不能回退；只切新项目绑定。
- [ ] 恢复目标执行预定第8请求，核真实引用属恢复目标；完整浏览器草稿确认/反馈/刷新，录屏留私有output。
- [x] 所有失败和在途保留，不自动重试；finally回切本轮服务或明确封存失败，并关闭演示生成入口。

### 任务4：发布候选和限定独立结论

**Files:** THIRD_PARTY_NOTICES.md、docs/runbooks/ubuntu-deploy.md、docs/development/reviews/M7-operational-closure-r1.md/json；新候选精确Compose覆盖与公开文件补充清单（实际身份确定后命名）。

- [x] 从锁及产物提取许可/SBOM候选和具体生产准入差距，不代签许可、不改生产恢复护栏。
- [x] 如源码/镜像变化，保存新SHA/image/源码映射/回滚/私有归档；旧r3不覆盖。
- [x] 同一本轮审查者复核差异、真实答案/引用及最终部署身份，逐项写passed/open；8题演示不变成M6质量proof。

### 任务5：归档与Git

**Files:** PROGRESS、REVIEW_STATUS、TODO、M7相关记录、CHANGELOG、DECISIONS和受影响配置/契约。

- [x] 逐项按实际证据更新，Ubuntu原生目标/生产许可/阶段批准未满足者不勾绿。
- [ ] 脱敏、JSON/链接/语法/`git diff --check`检查；显式文件暂存，普通提交push，核本地/origin/实际远程/main及工作树。
- [ ] 最终交付实际入口/启动/开关/8槽结算/独立结论/剩余具体条件，不停在只完成某一个子任务。

## 最终子项与开放项（按本次实证）

- [x] Ubuntu工具/私有目录700，Windows Desktop新隔离项目、API实构建，源码与镜像离线独立映射。
- [x] 新准入38项独立定向通过；8题清单冻结，但来源必要事实临发拒绝，未签manifest gate。
- [x] 首失败STOP/账户halt，provider0/Run0，宿主/消费者现场安全停态；后续Docker/WSL持续状态另列unknown。
- [x] 资料句级补修独立4项，稀疏键12项；真实新工程目标恢复/三元绑定回切、只读浏览器路径1项。
- [x] API/OS/锁/前端许可库存及6份原文候选、生产差距、新批14/8/48及8stream提案。
- [ ] Linux完整部署/原生Ubuntu；最后启动及停止操作超时，最终Ubuntu停态unknown。
- [ ] 1/2/4真实问答、恢复08、完整真实浏览器草稿反馈；本批禁止新派发。
- [ ] 许可法律批准/外部部署/公开Release及M7整阶段验收。

未勾选的完整任务不能由已通过子项代替；最终归档/Git以提交收据为准。
