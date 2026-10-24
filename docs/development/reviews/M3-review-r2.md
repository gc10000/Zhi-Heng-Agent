# M3 总控审查 · 第2轮

日期：2026-10-24。审查提交：`522b16863295309e52e780e7bb25aa863a0e9860`；修复基线：`6ccd3c78fe750ddd5ef6d7a108dfde12b9a64280`。结论：**通过，关闭R1/R2。授权M4-01至M4-10按依赖连续执行；M5及后续阶段未授权。**

独立读取[第二轮提交](M3-submission-r2.md)、实际修复/正式回归、任务记录、公共契约和ADR-037，并核对[本轮提交快照](M3-artifact-manifest-r2.json)。本轮未发现新的阻塞项。M3恢复11/11、核心43/76；M4为0/10，授权不计为实现完成。本会话仅审查和维护文档，没有启动M4代码或实验。

## 独立验证结果

| 检查 | 实际结果 |
| --- | --- |
| 完整后端阶段回归 | **346 passed、2 deselected、0 skipped、7 warnings，261.84秒，退出0**；180单元、83契约、83集成目录用例 |
| 前端单元 | **37项、9文件通过，4.37秒，退出0** |
| 完整离线浏览器 | **24项通过、0跳过、0失败、0 flaky，34.1秒，退出0**；含R1五项、R2五项正式浏览器回归 |
| 安装/类型/构建 | frozen-lockfile安装、typecheck、build均退出0，728模块、5.20秒 |
| 既有重导入 | **3 tests OK，0.207秒，退出0** |
| 提交时点快照 | **24文件hash、216本地链接、19构建文本敏感值扫描通过**；本轮无Python源码变更，0份语法检查 |
| 原真实产物只读复核 | **8项通过、4条持久消息有序，退出0**；本轮新增付费调用0 |
| 首轮独立反例复用 | **2项业务预期均通过，退出0、无pageerror**；缓存A→B→A恢复活动run、目录外设备显示/提交一致 |
| 新补充交错 | **通过、退出0、无pageerror**；旧run快照已在途，新轮恢复后才释放旧响应，当前候选/停止/禁重复发送保持正确，仅订阅新run |

后端命令：`M1_TEST_DB=m1_test_20261024_m3_r2_controller`，`.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -m 'not live_provider' -q --junitxml=docs/development/evidence/M3-review-r2-stage.xml`；PYTHONIOENCODING=utf-8，关闭业务文件/控制台日志。JUnit计时261.825秒，7项警告为既有PyMuPDF SWIG弃用提示。集成目录含真实隔离存储、Linux worker、本机模型及模型端口注入，不能统称供应商端到端；不以本次耗时差异宣称性能收益。

前端依次执行`pnpm -C frontend install --frozen-lockfile`、`typecheck`、`build`、`test:unit`；浏览器在构建结束后执行，清除M3_LIVE_CONFIG，使用`test:e2e --reporter=list,json --output=../docs/development/evidence/M3-review-r2-offline-artifacts`，独立JSON为M3-review-r2-offline-results.json，精确耗时34.135427秒。使用本机Edge，实际Vue/Query配合API协议模拟和合成PDF，未重跑真实API浏览器。独立布局/PDF用例未模拟的身份接口仍有8000代理连接拒绝日志，不影响24项实际通过，不能算真实后端验证。既有命令为`.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q`。

快照在总控文档修改前使用显式`build_m3_artifacts --summary docs/development/reviews/M3-validation-summary-r2.json --manifest docs/development/reviews/M3-artifact-manifest-r2.json --base 6ccd3c78fe750ddd5ef6d7a108dfde12b9a64280 --check`核对通过。实际源码diff确认后端/API/schema/配置/依赖未改。开发正式红测原件为4项业务失败（R1三项、R2一项），其控制台/JSON已核对，不把脚本错误计作业务红测，也不声称缺失的红测trace已独立保存。

## R1 · 接受缓存会话恢复修复

`frontend/src/features/chat/ChatPage.vue`以目录/历史本轮刷新结束为恢复前提，按当前活动指针或已读末页选目标；目标身份变化可以继续恢复，同一目标保留流状态。请求代次与会话epoch共同拒绝旧读取，创建后同步使目录/历史失效；没有活动指针且历史还有后续页时保持禁发。

正式五项浏览器覆盖历史先到、目录先到、旧快照迟到、恢复中切会话与分页；实际确认/取消POST使用对应version。首轮独立探针保持原数据/250ms历史与500ms目录时序，只把输出位置改为本轮新文件，结果从两个失败转为通过：请求包含new-active、停止按钮存在、重复发送禁用；原反例源码/报告/截图未覆盖。

另加独立探针，先正常触发旧run GET并用门闩保持在途，再通过实际QueryClient失效刷新目录/历史到新run；确认新候选已显示后才释放旧响应。实际读取顺序old/new/new，仅有`/runs/new/events`订阅，旧完成快照未覆盖候选，停止可见且重复发送禁用。该探针补足“旧响应确实已在途”的交错证据，不把等待时长本身作为覆盖证明。R1关闭。

## R2 · 接受可见设备与实际提交一致性修复

目录保存带用户/kb身份的设备描述，选择查询先核对授权首100项；未包含选中ID时按真实型号进行一次有界授权搜索，并精确匹配ID后补充可读option。旧描述不能独立证明授权。等待、断线、未找到或无当前范围描述时有可读状态，按钮与发送函数同时禁发；允许主动清空。退出、401及切范围同时清除ID和描述。

正式五项浏览器与新增三项单元覆盖搜索/分页、新建及切换会话、型号/payload一致、清空、失效/慢/断线、按钮/Enter、范围/身份清理和迟到查询。首轮独立设备探针实际结果为`value=p-101`、`selectedIndex=101`、可见型号BEYOND-100，发送`product_ids=[p-101]`，无pageerror。R2关闭。

接受已披露的有界取舍：同名搜索最多100项，极端重复型号可能找不到该ID，此时明确禁发并要求重新选择；不静默提交、不猜授权或无限遍历目录。这是显式失败边界，不宣称任意规模设备目录都可成功解析。

## 真实证据与保留边界

本轮只读命令复核原M3-live-config-stage-ready.flow.json对应真实持久产物，另存M3-review-r2-live-recheck.json：两轮完成、消息顺序、参数/追问、精确初始修订引用、唯一终态/事件、UI导入发布/设备范围和原件hash共8项通过。source flow SHA256仍为`52cd0cbc3820e78c2b725d2b5df42b32c0ac6f834223b151626e742aa087d96e`，4条消息有序。使用`recheck_m3_live`显式选择原config/flow及新output，未重新生成答案。

原真实工作台和真实登录各1项作为已接受历史证据保留，本轮真实API浏览器运行0、付费调用0，阶段累计付费回答仍为4。大PDF浏览器实际Range/性能、真实解析bbox全链路、生产/长期压力仍未验收；合成PDF和后端206不能替代这些结果。历史原生冷启动未知根因和课程来源/旧入口保留边界不因M3通过而扩大承诺。

原首轮/第二轮提交、manifest、失败和成功证据不回写。独立脱敏汇总见[M3-review-validation-r2.json](M3-review-validation-r2.json)；本机原始文件为evidence/M3-review-r2-*，含原反例副本及late-snapshot脚本/报告，均不上传。写入仅隔离回归小样，原课程知识数据、桶策略、真实配置和依赖未改；自启Vite已停止，原未跟踪evals/保留。

## M4授权与接续

授权开发会话从[M4-01](../../plans/tasks/M4-rag-quality.md#m4-01)开始，依计划完成M4-01至M4-10，阶段内不逐项申请。先建立至少50题的标注规则、允许证据和冻结划分，跑原链路基线，再做可回滚的单因素/组合实验。heldout在策略选定后才用于最终评价，不用于调参；没有可重复稳定收益保留旧默认，报告真实失败例、成本和p50/p95，不预设性能提升。

本次不修改既有未跟踪evals/；M4实施前核对并保留已有文件，不覆盖/清理或自动把它们加入Git。原始问题/回答及运行产物不默认上传，题集/报告仅按既有数据脱敏与Git约定处理。知识写入、迁移/故障实验继续使用独立范围，原课程数据及旧入口保留。M4-10结束提交新审查材料，开发会话仅能标“待审查”；M5及后续实现、服务器部署和公开Release未授权。

Git核对：本轮直连ls-remote与fetch恢复，远程main为`0e75640a6bb5cfe6cd413670d70083b050df4227`，本地仅领先522b168一笔、无分歧。依用户既有授权补推该交付和本轮审查文档；实际最终提交/同步结果见[Git交接](M3-git-handoff-r2.md)及最终回复，不强推或更改永久代理。Git同步与阶段验收分别记录。
