# M5执行提交 · 技术支持流程与有限Agent

状态：**待审查**。执行自验完成M5-01/02/03/04/05/07/08，7/7核心，总核心60/76；可选M5-06延期0/1，未注册网页MCP工具。M6未授权，本材料不代表总控通过。

## 范围与行为变化

| 任务 | 实际交付与关键文件 | 可观察边界 |
| --- | --- | --- |
| M5-01 | `app/support/models.py`、`workflow.py`、`repository.py`、`api.py` | 会话单文档CAS持久状态/槽位/来源，一次询问必要槽位，最多3轮，无进展/缺证据转交；候选不作事实 |
| M5-02 | `checklist.py`、Vue OperationChecklist | 引用原文整段保留前提和风险；自报未试/已试/无效追加时间，稳定身份去重，全部无效转交 |
| M5-03 | `cases.py`、CasesPage | 同run幂等草稿、用户编辑留痕、确认冻结；未知保留未知，不自动发送转交 |
| M5-04 | `tools.py`、`budget.py` | 仅查目录/读引用/搜内部手册，后端授予范围，预留预算与晚到CAS；不执行设备操作 |
| M5-05 | `commands.py`、`app/runs/repository.py`、`query_runner.py`、`app/conversations/context.py`、SupportContext | 新run冻结确认槽位和最新自报；领取核对上下文版本；纠正只影响未来，旧消息/记录快照不变 |
| M5-07 | `feedback.py`、`export.py`、FeedbackForm | 5类幂等pending_review反馈，只绑定本run引用；已确认且授权资料方可转义导出 |
| M5-08 | 安全边界回归、真实环境/复核/阶段检查脚本、OpenAPI及Vue生成类型、恢复手册 | 撤权拒绝嵌套历史/工具原文；刷新恢复、无效步骤出口、真实下载与待审反馈通过 |

全部修改文件及字节hash见[独立manifest](M5-artifact-manifest.json)；公开契约见[开发契约](../../plans/DEVELOPMENT_CONTRACTS.md)与[API说明](../../architecture/api-v1.md)。OpenAPI实际33路径/39操作；动态响应仍有手写前端类型，不宣称全部响应自动生成。

## 本轮验证

所有命令从项目根目录执行，使用已有`.venv/Scripts/python.exe`及pnpm。原始日志、JUnit、浏览器JSON/媒体仅存本机，路径/hash见[验证摘要](M5-validation-summary.json)，不将其内容上传。

| 验证 | 实际命令或入口 | 结果 |
| --- | --- | --- |
| 最终后端+既有重导入 | `.venv/Scripts/python.exe scripts/verification/run_m5_checks.py --group backend --output output/m5-stage-backend-final` | 脚本及两子命令退出0；774 passed、2 deselected、0 skipped、7 warnings；既有3项通过 |
| 测试目录组成 | `output/m5-stage-backend-final/backend.xml`逐用例统计 | 497单元、128契约、149集成目录；集成包含真实隔离服务及注入模型/检索端口，不代表149项付费测试 |
| 最终前端 | `.venv/Scripts/python.exe scripts/verification/run_m5_checks.py --group frontend --output output/m5-stage-frontend-final` | 类型/37单元/构建/27离线浏览器全部退出0；浏览器0跳过/0不稳定/0意外 |
| 原真实产物只读 | `.venv/Scripts/python.exe -m scripts.verification.recheck_m3_live --config docs/development/evidence/M3-live-config-stage-ready.json --flow docs/development/evidence/M3-live-config-stage-ready.flow.json --output output/m5-08-prior-live-readonly.json` | 退出0，8检查通过，新增调用0 |
| 真实新进程浏览器 | 设置本机M5_LIVE_CONFIG及M5_UI_BASE后，`pnpm -C frontend exec playwright test support-live.spec.ts --output=../output/m5-live-r5-browser-artifacts` | 1通过、58.2秒、退出0；r6独立目录从检查点继续，1通过、29.1秒，无新run/反馈 |
| 新真实产物只读 | `.venv/Scripts/python.exe scripts/verification/recheck_m5_live.py --config output/m5-live-config-r2.json --flow output/m5-live-config-r2.flow.json --report output/m5-08-live-recheck-final.json` | 16检查通过、退出0，复核新增供应商调用0 |
| 提交快照 | `.venv/Scripts/python.exe -m scripts.verification.build_m5_artifacts --summary docs/development/reviews/M5-validation-summary.json --manifest docs/development/reviews/M5-artifact-manifest.json --base a842ce8`，然后同参数`--check` | 核对实际JUnit/前端报告/逐命令退出码、本机原件hash、文件hash、Python语法、Markdown链接及本机敏感配置；实际快照计数以manifest和交接回复为准 |

后台最终pytest控制台508.85秒，JUnit508.778秒；完整进程522.516秒。重导入测试0.298秒，完整进程19.156秒。前端浏览器报告60.171秒、完整进程62.484秒。计时口径不同，不相互替换，不作为生产性能结论。

## 正式失败与更正保留

- `m5-08-boundaries-red.txt`：撤权后support回显200、全部无效仍ready，共2失败；修复递归精确修订授权及handoff出口。
- `m5-08-action-red.txt`：原文“接线前必须断电”无清单，1失败/5排除；补断电动作识别，保留完整前提。相关最终6通过，完整774再次覆盖。
- 首轮阶段770通过/4失败/2排除：评测夹具目标要求`m1_test_m4_*`，脚本最初前缀不合约束。未削弱目标守卫；改用`m1_test_m4_m5_stage_*`，定向4通过后完整774通过。此为验证配置错误，不计业务红测。
- M5-05模板Promise类型失败曾被组合命令末尾退出码掩盖；M5-07浏览器首轮1失败/2通过曾提前误写3通过。原日志保留，任务记录已明确更正；独立命令/稳定可访问名称修复后，最终阶段类型和27浏览器通过。
- 真实首轮Vite端口被既有服务占用、空输入按钮检查错误、复制目录集合名错误分开记录，不当业务反例。未停用户原进程；改独立5175与代理登录预检。两次问答在product阶段失败，保留原run，无prompt预算、无模型调用。临时测试凭据曾在本机失败截图显示，已轮换；原媒体保持私有不上传。

详见[M5-08记录](../records/M5-08.md)及[M5-01](../records/M5-01.md)、[02](../records/M5-02.md)、[03](../records/M5-03.md)、[04](../records/M5-04.md)、[05](../records/M5-05.md)、[06延期](../records/M5-06.md)、[07](../records/M5-07.md)。不覆盖既有提交/失败证据，不把ImportError或setup失败当业务红。

## 真实范围与未验证项

新随机`m1_test_m5_live_*`账本仅复制已接受M3测试资料登记/历史及其来源快照。源Milvus/MinIO只读复用，原账本hash不变，不重导入/发布/清理。真实API新进程实际完成：确认槽位→引用清单→刷新恢复→用户自报断电核对接线仍无效→转交→新未解决追问→编辑确认→下载Markdown→待审反馈。新请求3次：2次setup失败未到模型，**1次真实答案生成**；精确SDK HTTP重试及金额未知。r6是检查点续验，不冒称从零无中断。

16只读检查含源Mongo不变、实际索引/来源/正文关联、原件真实HTTP hash、流式答案/唯一终态/消息一致、未来支持快照、用户报告、确认编辑、下载字节与pending反馈。助手单样例复核新答案承认无效步骤、未重复该建议并说明缺资料转交；**人类质量评分null，不主张整体质量提升**。没有新dev/heldout调参或重跑。

单元/契约中的fake仅验证边界，离线浏览器mock不等于真实服务；既有知识只读与新真实流程分列。可选MCP延期，无外部凭据/官方页面真实联调，不写成集成通过。未实施M6、生产负载、设备控制、服务器部署或公开Release。

## 配置、兼容、风险与回滚

无新增开发依赖、模型升级或应用必填环境变量。测试专用M5_LIVE_CONFIG/M5_UI_BASE仅传本机私有路径/服务地址，不能当应用生产配置。工具上限6次/2扩展检索/30秒累计/12000 UTF8字节保守token、2在途执行槽；超时拒绝晚到结果，不保证中断GPU/数据库底层操作。崩溃后running预留不重派发，应人工转交，禁止清字段续跑。槽位/工具/草稿历史仍有Mongo单文档大小上限，未验证长年会话容量。

新增数据仅conversations.support、run.support_snapshot/input_support_version、support_cases/support_feedback；旧消息ordinal、原知识修订/活动指针不改写。撤权后的整份快照拒绝是有意的权限边界。原Windows模型加载历史风险不宣称根治。

回滚撤回支持路由、问答支持快照消费者及Vue处理页入口，保留新增字段/记录、原课程数据和测试现场；不清库或删对象。只停止本脚本创建的进程（本轮已正常退出），恢复见[技术支持手册](../../runbooks/support-recovery.md)。

## Git交接

main基线`a842ce863d8b9e892da4760d2ec6975028121079`，已正常推送cbd15c9、d611740、69c6821、ddabe5c、c2fb0a4、f2c160c；当前阶段最终提交SHA及远程核头由最终交接补记，manifest记录提交前HEAD，不循环amend。仅提交明确审阅的源码/测试/文档/脱敏hash，不上传.env、原始evidence、output、evals、原件、模型或运行数据。Git同步不代表阶段审查通过。

下一动作：总控独立审查M5。**等待总控审查 M5；不进入M6。**
