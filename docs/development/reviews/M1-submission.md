# M1阶段提交：知识注册、解析与验证发布

提交日期2026-10-23。开发自验完成，**等待总控审查M1**，不得据Git推送自行判总控通过，M2未授权。M0第三轮通过是历史基线，未重复其付费问答。M1-01至M1-11均完成，11/11；无未勾选的M1任务，核心合计20/76。

## 交付范围与行为

| 任务 | 实际文件/行为 | 关键证据 |
| --- | --- | --- |
| 01 | knowledge/products模型、schema；业务ID/hash分开、稳定结构ID、可空SourceRef | 9项实体定向；同名/同hash不合并 |
| 02 | 范围仓储、唯一索引、幂等注册/修订、attempt CAS | 5项真实Mongo，含并发与越权 |
| 03 | ParsedDocument/格式路由，旧入口仅适配检测 | 大写/伪格式/未知格式回归，原文与派生描述分开 |
| 04 | MinerU分段、页offset/hash/batch检查点及显式降级 | 150页边界；任务内真实两页小样1项；成功段不重交 |
| 05 | Excel全sheet/cell/公式/缓存/用途、Markdown章节/行/图片 | 实际合成文件解析，未知不默认为设备资料 |
| 06 | AssetStore、联合摘要缓存、Mongo共享预算 | 并发领取/跨实例限流、原图读回；阶段另验真实视觉 |
| 07 | 结构化切片，旧splitter复用字符兜底 | N1长串/超长标题修复，表头/行范围/型号/来源不丢 |
| 08 | 独立v2双路索引、INT32、完整来源/归属/修订过滤 | 真实本地BGE与Milvus；引号过滤、序号300、重试不编码 |
| 09 | 原件/载荷/向量/图片校验、CAS指针/outbox、回滚 | 未验证/坏hash拒绝、指针后故障核对、并发一胜、历史保留 |
| 10 | 三个迁移CLI及migration.py、迁移runbook | 零写dry-run，3资料/3向量/4对象独立恢复后才迁移，两个中断窗口恢复 |
| 11 | 同步IngestionService/OriginalStore、逐来源回看/自查/阶段回归 | 真实新资料贯通，最终181常规＋3既有＋1新供应商小样 |

完整修改文件和SHA256由[M1文件快照](M1-artifact-manifest.json)提供，逐任务环境、命令、退出码、失败/成功证据和回滚见records/M1-01.md至[M1-11](../records/M1-11.md)。代码层面新增app/knowledge、products、ingestion、infrastructure/rate_limits、retrieval/filters及隔离迁移；旧入口只改格式检测/切片兜底，旧问答图不整体替换。

## 自查发现与修复

同正文但章节元数据变化曾被误当幂等，现比较完整载荷；编码中断换载荷现被不可变身份阻止。PDF跨段标题路径曾为空，现传播到块和SourceRef（structure-2）。已有v2字段名相同但类型不兼容、跨修订chunk主键覆盖、资产冲突上传前缺检查均有真实或离线业务红测。发布补来源/原件/图片hash、正learned sparse、父关系闭包。原图被同路径替换造成重试冲突，现保留原始字节快照；Excel用途补未知资料注册字段。首轮全量发现无序读回，按ordinal/uid排序后原断言和完整阶段通过。没有删除有效测试、降低断言或用ImportError作为红测；测试缓存隔离/错误接线失败单独说明，不伪称业务复现。

## 本次实际验证

| 命令（从项目根运行） | 实际结果 | 本地原始证据 |
| --- | --- | --- |
| `$env:M1_TEST_DB='m1_test_20261023_stage'; .venv/Scripts/python.exe -m pytest tests/unit tests/integration tests/contract -m 'not live_provider' -q --junitxml=docs/development/evidence/M1-stage-final.xml` | 退出0；181 passed、2 deselected、7 SWIG弃用警告；176.74秒 | M1-stage-final.txt/xml |
| `.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q` | 退出0；3 tests OK；0.636秒 | M1-stage-reimport.txt |
| `$env:M1_TEST_DB='m1_test_20261023_live'; $env:M1_LIVE_PROVIDER='1'; .venv/Scripts/python.exe -m pytest tests/integration/test_ingestion_live.py -m live_provider -q` | 退出0；1 passed；77.20秒；一次真实视觉＋新一页MinerU | M1-11-live-first.txt/report.json |
| `.venv/Scripts/python.exe scripts/verification/recheck_m1_live.py --report docs/development/evidence/M1-11-live-report.json --output docs/development/evidence/M1-11-live-recheck.json` | 退出0；当前代码两资料原件/载荷/向量/来源/图像/缓存关联复核通过，供应商0调用 | M1-11-live-recheck.txt/json |
| `scripts/migrations/register_v1_documents.py --dry-run --manifest <实际隔离selection.json> --owner-id test --kb-id migration-review --output docs/development/evidence/M1-10-dry-run.json`（同venv Python） | 退出0；3份映射、同名独立、writes=0 | M1-10-dry-run.json/txt；精确路径见record10 |
| 25份领域/迁移/复核Python文件ast.parse | 退出0；25通过 | M1-syntax.json |

常规181项由实际JUnit分为154单元、12契约、15真实隔离集成。当前总收集183，常规命令排除两项付费测试（不是skip）：M1-04供应商小样已在该任务真实验过，不为阶段再次付费；本项新live小样另行执行。不要把各轮重复测试叠加成数量，也不要沿用M0历史105/3或旧73项。首轮全量179 passed/1 failed的输出与XML保留。各定向红/绿完整列表见record11。

[明确脱敏验证摘要](M1-validation-summary.json)从实际JUnit/控制台动态提取数字并保存原输出hash，不是手改原件。原始evidence/output含本机路径/对象映射，全部留本机、未上传；提交的文件快照仅相对源码路径/hash和脱敏检查状态。

## 真实、fake和未验证边界

单元/契约默认禁网络；其中端口fake只证明领域逻辑。15集成使用真实独立Mongo、Milvus、MinIO和现有本地BGE，无付费LLM；非付费pipeline的PDF为明确native降级、图摘要测试端口fake，均不冒充供应商验收。新增live独立验证真实视觉、真实MinerU、真实存储/索引/发布/检索/回看；图片hash `3735b6ffe0d2e45c734199ff0ca775d17607ac8a46d49285c02bcfc9d0259a26`、960×300完整解码，已目视核对Gateway→Controller→Support PC及实际摘要。两新资料共7切片/两活动指针，精确原件读回一致。Excel在真实存储pipeline抽查两sheet/cell、公式缓存、用途和无伪页码。

未验证/未实施：生产全库迁移、公开任务/文件HTTP API、浏览器前端、服务器部署、大规模性能、长期并发稳定性、跨硬崩溃外部计费exactly-once。M0历史图片异常与Windows原生加载异常仍不宣称根治。供应商未确认上传窗口保留人工核对恢复步骤，未做破坏性真实故障；测试故障仅注入控制流。

## 配置、依赖、数据与兼容

沿用FastAPI/LangGraph/Milvus/MinIO/MongoDB及现有模型，无新运行依赖/模型升级，pytest使用已有8.4.2；真实依赖版本见复用文档。配置说明/示例新增M1_TEST_DB、M1_LIVE_PROVIDER、MinerU分段页数/字节/轮询限制的中文解释；.env真实值未改/未上传。M1-11仅扩展现有付费开关说明。资料新身份/集合不自动覆盖旧知识。

所有新写入仅m1_test_*库/集合及m1-test/对象前缀。三资料迁移源也独立新建，包含小PDF、150页PDF、跨sheet表格和PNG；先备份源Mongo/向量/原件和活动列表，再独立目标读回恢复，未通过不能迁移注册。旧库没有统一原件/修订注册表，因此使用显式人工核对清单，不能猜文件名；ADR-020记录调整。无删除/重建旧集合、全库重导入、清桶或桶访问策略变更。

M1同步领域服务由后续M2封装，旧公开图保持兼容。发布函数按实际接口冻结到公共契约，不保留已过时的计划函数名。回滚通过expected_active CAS发布旧可用修订，不重解析、不删新版；停用新入口仍能读旧课程库。单个v2集合需绑定同一Mongo注册表数据库；部署权限/管理员篡改隔离属于后续阶段。代码撤回按正常revert，禁止破坏性reset或清现场。

## Git与总控交接

origin为用户授权仓库，main，承接原README/历史无强推。课程真实整体基线`0a409294c173601898c847ee962938b155f98d45`明确非伪造逐任务历史。M1-01至10各源码/测试/记录已提交且正常推送，远程头逐次核对：

| 任务 | 提交SHA |
| --- | --- |
| 01 | 9e4ff90e0e24de000a5511d199b982565a7c1807 |
| 02 | 165746065ad17716a1eca7031c15cc4b24f737d0 |
| 03 | 0d54cab60e728255918b725664f30445b251858b |
| 04 | 7f4fcbd9923cd9e30ce20bb3f1f71314aaa52fb8 |
| 05 | 63a0676c9bc355e8978c041870ac8173caf1babc |
| 06 | 2685bff6e420aff377342a32cb492e2b38fdde36 |
| 07 | 3d0d54e36c0f52cfc29bcefe43dc726ddd01588b |
| 08 | 0bc4b82741c78f0aaa84637d65da88ba26e3ecd4 |
| 09 | 145677f2c32273e6cb7e037187df5dd1bd47fcf4 |
| 10 | 857bca217702a090efab85691646540c3415f63f |

M1-11本提交SHA与实际推送核对由最终交接补记，不循环amend。在提交前审阅明确文件列表及脱敏摘要，不使用git add .；原始evidence/备份、模型、虚拟环境、.env、PDF/Excel、对象数据和临时输出忽略。既有未跟踪evals/保留本地，不纳入公开提交。NOTICE及课程/开源来源保留。

总控建议独立重跑常规/既有检查，按manifest核对源码和原始报告hash，重点审查图片快照恢复、幂等载荷、发布故障窗口及迁移恢复门禁；必要时优先只读复核已存真实产物，不重复付费。通过审查后再授权M2，当前停在M1。
