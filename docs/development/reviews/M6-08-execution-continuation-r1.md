# M6-08 AF-R1-R执行侧复核、25题助手判断补记与阶段阻塞矩阵

日期：2026-10-29。执行基线：`edc5944f736f006ba5eba9e7de92e65141b41276`；开始时HEAD与origin/main相同。实际工作区另有已修改的`docs/development/PROGRESS.md`、`prompts/answer_out.prompt`和未跟踪`tests/unit/test_answer_prompt_scope.py`、`tmp/`；均保留。本轮只读数据库、未调用供应商、未运行heldout、未写正式质量记录。M6仍4/7，M6-04/05/08未验收，M7未授权。

## AnswerFilter AF-R1-R

我直接复核了`app/runs/answer_markdown.py`与`app/runs/answer_filter.py`。答案专用CommonMark实例在paragraph/setext规则执行时使用解析器实际`state.getLines`/容器缩进状态；CRLF/CR规范化时另以原流offset表映射。容器tab展开生成的虚拟空格标记为`None`，只有行尾坐标和原文后缀逐字符一致、重建内容与inline token一致才授予代码范围。未映射文本不获代码豁免。表格仍按实际cell token和单元格单调坐标查找，不把跨格反引号重新配对；稳定围栏开头的既有AF-R2逻辑未改。

覆盖列表续行、列表标记后tab、嵌套列表、引用与列表组合、LF/CRLF/CR、跨行代码、表格格边界、占位符、真实HTML及图片授权；逐字符分片和各单点边界均核。合法代码中的`<ADDRESS>`、代码图片示例在整串/分片结果中保持原文；代码外真实未授权图片仍被替换，授权图片按原规则归一化，真实HTML保持转义。无法精确映射的坐标fail closed。

本轮实际命令与结果：

| 命令范围 | 结果 |
|---|---:|
| `pytest tests/unit/test_answer_filter_tab_review_regressions.py tests/unit/test_answer_filter_tab_boundaries.py tests/unit/test_answer_filter_container_boundaries.py tests/unit/test_answer_filter_review_regressions.py tests/unit/test_answer_filter_content.py tests/contract/test_answer_filter.py tests/unit/test_answer_prompt_scope.py -q` | 130 passed，退出0 |
| `pytest output/m6-execution-continuation-20261029/test_independent_tab_review.py -q` | 13 passed，退出0 |
| 已存共享检索/Markdown/答案回归集（完整16文件命令见`tmp/m6-af-r1-r-independent-20261029/shared-review.xml`） | 297 passed，5条既有SWIG弃用警告，退出0 |
| 25题缓存供应商流离线回放，输入原分片及1/2/7字符/整串变体 | 25 passed，退出0；新输出与缓存供应商正文一致 |

缓存测试第一次在新的`tmp/`副本收集时报退出1，原因为未复制被测的本地旧过滤器夹具；未执行任何测试。复制同一已存夹具后重新运行25题通过。该失败属于测试夹具布置错误，不是产品回归。130/297范围重叠，不累计为唯一总数。此为本执行会话的定向源码核验，AF-R1-R仍待原规划/总控独立审查；AF-R2既有通过结论保留。

## 25题助手侧答案判断更新

复用本机已存25题供应商流、正式Run、原件判断和PDF物理页映射，未生成答案。新Run与题级父Run/`subject_sha256`的实时只读关联25/25一致，持久答案SHA与既有助手判断绑定一致。另存的私有逐题报告含运行ID、来源文档/修订/原件SHA、物理页、原件摘录定位、新旧过滤答案SHA及差异：`output/m6-execution-continuation-20261029/assistant-answer-quality-review-r2.html`和JSON。85题既有助手原件核查未重做、未更改。

| 题目 | 助手侧结论 | 原件依据（物理页） | 本轮判断 |
|---|---|---|---|
| support-v1-003 | 核心支持 | D1 p.4 | 补回CLI提示符；命令和顺序不变。 |
| support-v1-004 | 核心支持 | D1 p.4 | 补回CLI提示符；地址获取约束仍在。 |
| support-v1-006 | 核心支持 | D1 p.5 | 补回CLI提示符；DNS命令未变。 |
| support-v1-007 | 核心支持 | D1 p.5 | 补回CLI提示符；默认路由与接口未变。 |
| support-v1-008 | 核心支持（由部分正确调整） | D1 p.5–6 | `<AC-IP>`占位符恢复；答案保留示例地址不是现场通用值的限制。 |
| support-v1-009 | 核心支持 | D1 p.5 | 输出差异不影响结论。 |
| support-v1-010 | 核心支持 | D1 p.5–6 | 输出差异不影响结论。 |
| support-v1-019 | 原件可答但未答出 | D5 p.9–10 | ping正文未进入weighted融合候选；回答仍未完成。 |
| support-v1-020 | 核心支持 | D5 p.11 | 缺省SSID构成依据保留，不推断实时SSID。 |
| support-v1-021 | 原件可答但未答出 | D5 p.12 | 登录账号依据未进入weighted融合候选。 |
| support-v1-022 | 原件可答但未答出 | D5 p.14、26 | 首次改密码依据未进入weighted融合候选；WEP页面不等于首次建议。 |
| support-v1-034 | 核心支持（由部分正确调整） | D5 p.27 | `<更新配置>`、`<备份配置>`名称恢复，两个动作可区分。 |
| support-v1-037 | 核心支持 | D4 p.3、6 | 2019现场局域网、设备/电脑接入及禁用无关网卡范围保留。 |
| support-v1-038 | 核心支持 | D4 p.3–4 | 旧版隐藏入口步骤保留；不泛化为现行所有产品。 |
| support-v1-048 | 原件可答但未答出 | D1 p.4；D5 p.8、30 | LA2608移动网/AC端已答，CB Cable/EoC同轴上联依据未召回，比较未完成。 |
| m6-g540-02-a | 核心支持 | D3 p.3–4 | 摄像头盖板依据与不推断实时状态的边界保留。 |
| m6-g540-02-b | 核心支持 | D3 p.3–4 | 物理遮挡说明保留。 |
| m6-g540-04-a | 部分正确／对象范围错误 | D3 p.5 | 把配件TF卡能力套到机身microSD范围；对象证据需分开。 |
| m6-g540-04-b | 核心支持 | D3 p.5 | 不把部分型号差异推成所有型号结论。 |
| m6-g540-05-a | 部分正确／具名配件缺失 | D3 p.3、5 | 机身RJ45和扩展坞LAN均有依据，回答未点名MateDock3。 |
| m6-g540-05-b | 部分正确／具名配件缺失 | D3 p.3、5 | 机身接口有答；附加配件描述未绑定MateDock3。 |
| m6-g540-17-a | 核心支持 | D3 p.14 | MateDock3充电USB-C限制与机身多功能USB-C区分。 |
| m6-g540-17-b | 部分正确／具名配件缺失 | D3 p.14 | USB-C限制基本正确，未保留MateDock3精确名称。 |
| m6-g540-18-b | 核心支持 | D3 p.15 | HDMI/VGA并行限制限于MateDock2，不泛化其他扩展坞。 |
| m6-g540-20-a | 核心支持 | D3 p.17 | 蓝牙符号、3秒和灯闪操作依据是既存assistant转写；不冒称PDF原生文字或人工审核。 |

25题助手分析从15核心支持/6部分正确/4原件可答未答调整为17/4/4。六题过滤输出变化为003、004、006、007、008、034；除008、034的助手分类更新外，其余结果作为不变对照。此为assistant-side单轮原件分析，不是human评分、正式观察、正式双轮或答案质量门槛通过。

## 保留问题与技术边界

G540 04-a、05-a/b、17-b的原25题prompt引用含机身和具名配件内容，回答仍出现跨对象能力归属或未保留MateDock3名称；判断为答案表达/对象约束问题。`prompts/answer_out.prompt`中当前未提交改动增加了通用的具名配件归属和仅在证据不能消歧时才澄清规则，真实prompt构造测试通过；本轮没有用新模型输出验证行为，不能宣称修复已见效。

019/021/022的必要正文在weighted融合前被排除：019 ping正文稀疏第7，只有不同的图片摘要进入融合；021登录正文稀疏第9、022首次改密码正文稀疏第11。048的CB Cable/EoC正文不在双路top-20，已存dense第153、sparse第57。除上述保存排名外，精细排序原因未知。本轮保留weighted及现有top-k/阈值，不使用RRF、不调参数、不改默认修订，不以新答案掩盖未召回正文。

## 只读账本和正式验收阻塞矩阵

Docker/Mongo实况检查中Mongo ping通过。只读Mongo结果：r3实验79b3… completed、85题、85结果，仍是19个继承+66个执行；该实验没有human审阅行。原失败实验a560…仍failed/attempt 2/retryable=false/results 0；已保存身份将错误记录为`provider_invalid_response`，本次无新增调用，原调用和费用仍未知。25个隔离答案Run均completed，持久答案hash匹配25/25，父题级来源关联匹配25/25。数据库写入0。

| 子项 | 已完成证据 | 缺少的正式证据 | 责任方及先决条件 | 能否由执行端完成 |
|---|---|---|---|---|
| M6-04 | 不可变双轮/校准机制、未知项追加和受控图片审核技术验证已保留；001历史基线有2条human轮次及1个校准记录。 | r3固定85题当前human审阅行0；需要新规则下绑定85题当前结果的有效双轮，并处理unknown/适用性分歧；样例人工抽检与完整固定报告验收仍未完成。001候选有0条human审阅、gate为pending，不能代替85题。 | 有权的真实审核者依正式审阅协议；复用已有原件导航/依据，无需找PDF或复制聊天判断。之后才可预校准。 | 技术准备可由执行端完成；human声明/评分及独立双轮不能代写。未验收。 |
| M6-05 | 反馈审核/版本绑定/affected后full门禁实现与合成回归已完成；已存在confirmed regression反馈草稿。 | 该草稿尚未绑定目标修订或受影响题，`affected`与`full`证明均缺；001候选不绑定该草稿的目标修订，不能当作反馈后复评。 | 维护者确认/绑定新修订及affected题；须先有基线双轮/校准和通过的受影响题实验，再创建完整dev实验并验证证明顺序。 | 执行端可在前置有效后运行隔离回归；本轮无答案生成/评分写入，未验收。 |
| M6-08 | r3完整dev 85题结果及固定报告已保存，组成19继承+66执行；本轮补齐25题过滤回放和assistant侧语义判断。 | 85题正式双轮、基线预校准、相同题集独立候选、反馈后复评及受影响/full质量证明仍缺；65题heldout未运行。此前失败实验保持不可重试，不以0行推断无调用。 | 先满足M6-04有效human双轮与校准，再按顺序创建同范围候选及反馈后证明；heldout按其正式授权/门槛单独处理。 | 本轮助手侧与代码证据已完成；真实human记录不代写，heldout未执行。未验收。 |

M6-04/05/08具体依赖按[质量门槛](../../../docs/evaluation/release-gates.md)和M6任务文件执行。现有001基线的人工记录及校准只覆盖单题旧身份；其候选还没有human评分且门槛pending。不得将用户此前聊天判断复制为新规则双轮。

## 验证、数据与交接

- 答案过滤与提示范围测试130通过；原独立tab容器探针13通过；相邻共享离线回归297通过；25题缓存回放25通过。测试组有重叠，不累计。
- 初始回放收集失败的修复过程已记入本机`tmp/m6-af-r1-r-independent-20261029/`；最终录入25题结果到新的临时输出目录，不覆盖原cache或历史答案。
- 本次只读保护哈希复核：25题/历史输出清单821项、AF补修保护清单404项、真实检索保护清单294项均匹配，缺失/不匹配均0。
- 无新供应商调用、无答案生成、无Mongo写入、无heldout、无校准/候选/人工评分/正式观察；精确HTTP与费用未知值不改写为0。
- `M6-08-execution-continuation-validation-r1.json`记录本轮脱敏验证结果。独立技术及语义复审待总控；不重开SQ、continuation、来源前提接线、图片协议或AF-R2结论。工作台默认修订不切换。

**唯一下一步：将本报告和AF-R1-R探针结果交总控独立审查；通过后按既有顺序处理正式human双轮、预校准、同范围候选及反馈后复评。** M6仍4/7，M6-04/05/08未验收，M7未启动。
