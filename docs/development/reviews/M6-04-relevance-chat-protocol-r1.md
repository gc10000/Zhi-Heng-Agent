# M6-04/05/08：图片使用关系、聊天来源与步骤适用性补修

起点：main `806e4ca676614754939ba3fa10e9f659c763ed87`；本轮在用户已授权M6范围顺序实施，没有派子代理。Git fetch后本地与origin/main一致。M6核心仍4/7、总核心64/76，04/05/08未验收，M7不启动。本报告是局部补修提交，不是阶段验收通过。

## 对接续要求的处理

1. **无关图片的选择和展示**：新正式run引入`image_selection_version=1`，原`asset_ids`保留上下文证据，`answer_asset_ids`只包含最终答案以受控语法显式使用的图片。生成前选择事件答案图为空；完成事件、完成快照和历史保持一致。代码/转义/未授权图不算使用。评测适配器和仓储完整保存版本及图像`image_usage=answer/context`，进入结果指纹。Vue默认只展示新答案图，关联图展开后才读取；旧结果默认折叠并标“使用关系未记录”，不改旧结果或配图0分。显式使用只证明使用关系，仍需人工判断相关性，不宣称语义质量提升。
2. **聊天判断进入后续流程**：新增不可变`observations`正式接口及账本，保存当前结果指纹、稳定来源标识、原话、语义分和规则。服务端明确assistant转录者，不包含human声明或轮次；同来源幂等/冲突/并发和跨实验重用受控。后续独立审阅可显式引用`observation_id`，不自动复制分数或声明，不进入双轮计数。原话无需用户网页重填；服务端无法独立认证外部聊天作者，来源标识由转录者负责。
3. **适用性规则版本化**：`question-purpose-v1`按问题目的明确步骤是否适用及理由，false须N/A，true不可N/A；追加未知不能绕过适用性。混合版本无法校准，跨版本或数值/N/A变化门槛pending。旧请求省略版本仍走legacy-v1并保留精确旧请求指纹和质量投影结构，旧评分/校准不回写。采用新规则应有新的独立基线审阅、预校准及之后的新候选链，不能将旧步骤1改为N/A或将新N/A改1来通过。

## 真实001接续

现有候选`f0ac6186-b204-4987-bb14-0089f3b73996`、题级指纹`3d2ea7704c2e076979835c3ccae0cb72319d822fe5ca7e53a80a12a8a87ced39`未改变。正式运行`6f61feec-f301-4709-84fe-57321519994b`仍completed。新账本只追加原话来源1条：`8e3262fc-a4c6-44a0-b087-df1355533f3c`，语义2/2/N/A/0；来源标识由既有原话证据文件SHA派生，不冒称聊天平台原生消息ID。正式human 0、门槛pending，校准/助手审阅/人工审阅均未新增。

原答案只读重放新选择器得到0张答案图、2张上下文关联图；两图真实HTTP/hash/完整解码通过。只读派生输出不是新生成、不是新正式实验，也不覆盖原结果。13项API/Mongo/图片/账本检查及10项真实Edge只读检查通过，旧结果/运行/消息/知识登记/评分/追加/校准集合摘要保持一致。保留旧图像0分，不能将隐藏图像当质量达标。原聊天留证两份文件hash再次核对一致。

本轮仅重启原隔离审阅API加载新代码，未启动模型宿主/worker，没有付费模型调用、human写入、新校准、heldout运行或知识发布。重启前准备检查脚本因stdin下`load_dotenv()`自动定位抛AssertionError（工具错误，不是业务红测）；PowerShell未停止后续重启，因此无活动任务检查实际在重启后以显式.env路径重跑通过。此窗口和旧重启脚本`followup_route_loaded`历史标签保留；另以新OpenAPI只读检查确认observations路由与新版字段已加载。无现场字段清理/数据删除。

## 红测、定向验证和完整回归

原始材料在本机`output/m6-protocol-r1/`，不上传。退出码与实际数量以[本轮验证摘要](M6-04-relevance-chat-protocol-validation-r1.json)为准；独立[提交快照](M6-04-relevance-chat-protocol-manifest-r1-final.json)不覆盖任何旧快照。

| 验证 | 实际结果及证据 |
| --- | --- |
| 初始正式HTTP与运行红测 | 12 failed、5 deselected，退出1；`red.xml`，缺协议/缺图片使用字段/错误图片门禁，夹具已成立，无ImportError |
| 追加未知改变适用性红测 | 1 failed，退出1；`followup-red.xml`，原适用仍被改为N/A |
| 生成前选择事件边界红测 | 3 failed、5 deselected，退出1；`initial-selection-red.xml` |
| 审阅默认图墙、引用图墙、历史图默认展开反例 | 各1 failed、退出1，分别`browser-red/`、`evidence-red/`、`legacy-display-red/`，截图/trace保留 |
| 首批后端绿测 | 17 passed，退出0；`green-initial.xml` |
| 中间定向 | 9 failed/84 passed：测试目标库前缀不符合m1_test_m4_门禁，`target.xml`；不算业务红测，不放宽门禁；改用独立合规前缀后93 passed，退出0，`target-r2.xml` |
| 最终后端定向 | 95 passed，退出0；`target-final.xml`，包含完整阶段启动后新增的两项规则校准/旧指纹兼容检查 |
| 最终定向浏览器 | 9 passed，退出0；`browser-target-final/`；中间自阻塞2失败和刷新后测试未重新选择legacy规则1失败均保留在r2/r3目录，前者修逻辑，后者改测试选择、不削弱断言 |
| 完整后端 | 982 passed、2 deselected、0 skipped，退出0；588单元/135契约/259隔离Mongo集成，`stage-final/backend.xml`；测试模型/检索注入，不代表供应商调用；上述新增2项另在95项中通过，本轮去重覆盖984项，未声称一次全量984通过 |
| 既有重导入 | 3 passed，退出0；`stage-final/reimport.txt` |
| 前端单元/类型/构建/完整浏览器 | 37单元/41离线浏览器、0 skipped、typecheck/build全退出0；`stage-final/commands.json`，数量从JSON读取，不沿用历史 |
| 真实现有001 | 13服务/10浏览器检查，退出0；`live/report.json`、`live/browser.json`；聊天转录1，其余业务只读，模型0 |

精确执行命令（PowerShell，项目根目录）及隔离数据范围：

```powershell
$env:M1_TEST_DB='m1_test_m6_protocol_red_20261027'
.venv/Scripts/python.exe -m pytest tests/integration/test_review_protocol_v2.py tests/integration/test_answer_grounding_run.py -k 'protocol or answer_images' -q --tb=short --junitxml=output/m6-protocol-r1/red.xml
$env:M1_TEST_DB='m1_test_m4_m6_protocol_final_20261027'
.venv/Scripts/python.exe -m pytest tests/integration/test_review_protocol_v2.py tests/integration/test_answer_grounding_run.py tests/integration/test_evaluation_run_adapter.py tests/integration/test_evaluation_reviews.py tests/unit/test_answer_image_selection.py tests/unit/test_review_scores.py tests/contract/test_answer_filter.py -q --tb=short --junitxml=output/m6-protocol-r1/target-final.xml
.venv/Scripts/python.exe -m scripts.verification.run_m5_checks --output output/m6-protocol-r1/stage-final --group all
pnpm -C frontend exec playwright test reviews.spec.ts citations.spec.ts --reporter=list --output=../output/m6-protocol-r1/browser-target-final
.venv/Scripts/python.exe -m tmp.m6_protocol_live
node tmp/m6_protocol_browser.cjs
.venv/Scripts/python.exe -m scripts.verification.check_m6_protocol_artifacts --summary docs/development/reviews/M6-04-relevance-chat-protocol-validation-r1.json --manifest docs/development/reviews/M6-04-relevance-chat-protocol-manifest-r1-final.json
```

其余红测命令为上述pytest单独选择对应`test_new_rule_followup_cannot_change_applicability`或`-k answer_images`，浏览器分别选中文测试名；原始XML与trace不覆盖。完整阶段脚本逐命令记录真实参数、退出码和隔离前缀；每个Mongo测试再追加随机子库名，不访问课程库、不删集合。原始HTTP/启动/浏览器脚本保留tmp本机，不上传账号或私有session；正式可复查回归及检查器已纳入源码。

## 兼容、范围与回滚

未新增开发依赖、模型或环境变量；沿用已有Mongo与受控图片读取。新增集合仅`evaluation_observations`，唯一索引不改现有知识集合。OpenAPI、生成TS、前端手写类型、契约、审阅/标注手册、决策ADR-066、04/05/08任务记录与清单已同步。反向本轮代码提交可回滚；保留新增来源账本和原始证据，旧服务忽略新字段，无需删库、重导入或重新调用模型。

本轮仍未证明显式选图等于语义相关、原生模型加载问题根治、全dev答案质量提升或M6阶段通过。新规则所需独立基线复核/预校准/新候选及完整dev、固定质量报告仍待完成；不要求用户重填已有聊天判断。局部补修交总控定向审查，M6-04/05/08保持未验收，M7未授权。

Git采用显式文件清单审阅后正常提交/推送，不强推；tmp/evals/output/原始evidence/私有配置不纳入。自身提交SHA与远程核头在最终交接补记，不循环amend。

暂存检查发现新测试文件末尾空行，已仅整理空行、无行为变化；首份准备快照保留，最终快照另以r1-final命名，检查器显式选择最终文件。
