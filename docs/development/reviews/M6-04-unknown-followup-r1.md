# M6-04 未知项追加复核机制交付 r1

日期：2026-10-27。环境：Windows PowerShell、仓库原 `.venv` Python 3.12.7、Node 22.17.1、pnpm 11.25.0、现有 Docker 测试服务及锁定前端依赖；未安装或升级依赖。状态：追加复核机制完成实现和执行自验；真实 001 的两个未知项仍待原审核者本人逐轮判断。**这不是 M6 阶段验收，不代表未知项已解决、校准已建立或 M6-04/05/08 已完成；M7 未授权。**

## 修复范围与行为

针对“同一审核者已经保存两轮审阅，但其中的 `unknown` 不可更正，校准永久停在未完成”的接续问题，增加独立的 `evaluation_review_followups` 追加账本、HTTP 接口及审阅页。原审阅行仍只读、不覆盖。只有原审核者本人可以针对自己的原 `review_id` 和当前题目结果指纹追加结论；请求必须恰好覆盖原轮次全部未知维度，逐项填写结论和非空依据并重新声明本人原件核对。已确定的分数不可改，原关键错误不能被追加结论删除，其他审核者的未知仍阻止校准。

同一原审阅使用 Mongo 唯一键仲裁并发；相同幂等请求重放返回原记录，内容不同或再次追加返回冲突。结果指纹变化、越权、身份不匹配、缺少原件声明、漏项/多项、非法分数或空依据均拒绝。结果含图片资产时，图片相关性不能标为不适用。页面解释步骤可执行性应先按题意判断是否适用，配图须核对实际用途和与问答的关系；不能确定时保留原 `unknown`。

接口为 `POST /api/v1/experiments/{eid}/reviews/{review_id}/followups`。同步更新 OpenAPI、前端类型、公共契约和发布门槛说明。无新依赖、配置、迁移、知识写入或索引发布。

## 修复前后与红绿证据

- **正式 HTTP 红测：**`$env:M1_TEST_DB='m1_test_m6_followup_red_r1'; .venv/Scripts/python.exe -m pytest tests/integration/test_evaluation_reviews.py -q --tb=short -k followup --junitxml=output/m6-04/followup-red-r1.xml`，退出码 1；16 项中 14 项失败、2 项通过、16 项因选择表达式排除。失败是新追加复核正式路由尚不存在、返回 HTTP 404；不是导入或构造失败。
- **追加复核正式入口最终回归：**`$env:M1_TEST_DB='m1_test_m6_followup_final_20261027_r4'; .venv/Scripts/python.exe -m pytest tests/integration/test_evaluation_reviews.py -q --tb=short --junitxml=output/m6-04/followup-regression-final-r5.xml`，34 passed，29.45 秒，退出码 0。使用显式隔离 Mongo 测试库、合成结果/审阅，不写真实 001 账本，不调用供应商。覆盖原审阅不变、两轮追加后校准传播、只追加一轮仍拒绝、当前结果变化、身份/资源/维护权限、图片不可跳过、幂等重启、冲突、并发唯一胜出、审计字段完整和关键错误保留。
- **前端定向回归：**`pnpm -C frontend exec playwright test reviews.spec.ts --output=../output/m6-04/followup-ui-final-r2-artifacts --reporter=list`，4 passed，退出码 0。覆盖逐轮提交与刷新显示、重复提交防护、澄清状态保留未知以及辅助身份隔离。
- **阶段后端与既有重导入：**`.venv/Scripts/python.exe -m scripts.verification.run_m5_checks --output output/m6-04/followup-stage-r2 --group backend`，命令账本退出码 0；951 passed、2 deselected、0 skipped，其中 574 unit、135 contract、242 integration；7 条 SWIG 弃用警告。既有重导入 3 项通过，退出码 0。回归使用脚本生成的独立 `m1_test_...` 数据库名前缀。
- **阶段前端：**`.venv/Scripts/python.exe -m scripts.verification.run_m5_checks --output output/m6-04/followup-stage-r2-frontend --group frontend`，typecheck、37 项 Vitest、build、37 项离线 Playwright 均退出码 0，未跳过或不稳定。OpenAPI 文件解析通过，共 49 paths、59 operations。

阶段回归比历史 950 增加一项审计完整性测试后实际为 951；本报告只引用本轮新目录中的结果。

## 测试工具与中间错误记录

- `output/m6-04/followup-regression-final-r4.xml` 对应一次定向命令遗漏 `M1_TEST_DB` 的夹具前置错误：34 项 setup error，未进入业务断言；它不是红测或通过证据。补上随机隔离库名后，r5 正式定向回归 34 项通过。
- 前端阶段检查初次指定已由后端检查创建的输出目录，验证脚本按设计拒绝覆盖，退出码 1；随后改用全新 `followup-stage-r2-frontend` 目录完整通过。
- 首次追加 UI 浏览器红测在追加说明尚未实现时因定位“步骤是否适用”内容失败，退出码 1；实现说明及控件后，四项定向浏览器测试通过。错误/截图原件仍保留在本机 `output/m6-04/`，不修改旧输出冒充通过。

## 真实数据、人工审阅及范围

用户报告新隔离 001 的两轮人工审阅已保存，步骤可执行性和配图相关性仍为未知。本次只为隔离合成数据运行测试；没有读取或写入真实审阅账本，没有提交追加复核、修改评分、创建校准、生成答案或重跑供应商模型。既有真实 API 样品报告 `output/m6-08/review-r2/readonly-r2.json` 与检查点复用报告仅保留作历史背景，不作为本轮重新执行结果。既有 UI 只读就绪报告 `output/m6-08/001-repaired-r1-20261026/browser-followup-ready.json`记录当时未发送追加请求、未改人工记录、模型调用为 0；该报告不代表用户现在已提交追加结论。

fresh heldout 未运行；没有接触课程原始资料、生产知识库、Milvus、MinIO 或真实用户反馈。M6 核心仍 4/7；M6-04 因真实人工未知项尚未追加及固定报告抽检未完成而未验收，M6-05/08 未验收，M6-06 可选延期，M7 未授权。不存在本轮新增供应商调用。

## 文件、复核与回滚

源码涉及 `app/evaluation/review_followups.py`、`app/evaluation/reviews.py`、`app/evaluation/api.py` 和审阅页 Vue 组件；测试涉及正式集成入口与离线浏览器。契约、OpenAPI、类型、门槛手册、决策、变更、进度、M6-04/08 任务记录及 M6 计划均同步。精确脱敏验证见[验证摘要](M6-04-unknown-followup-validation-r1.json)，源码和链接快照见[独立 manifest](M6-04-unknown-followup-manifest-r1.json)。原始测试输出仅保留在本机 `output/m6-04/`，未加入 Git。

回滚只反向追加复核代码/API/UI提交，保留原审阅、追加账本、用户评分和本机证据；不删除集合、不改写原记录，也不触碰知识库和对象存储。下一步由原审核者在同账号下逐轮查看当前审阅页提供的依据并决定是否提交；不能确定时保持未知。随后再由既有 M6 流程决定是否校准、进行反馈后复评和完整开发集验证。
