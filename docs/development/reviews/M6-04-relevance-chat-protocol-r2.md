# M6-04/05/08：图片协议R1/R2第二轮修复交付

日期：2026-10-27。起点main `6cea5f332d503b2185cf23cbf49807fbf915e56d`，开工fetch后origin/main与本地一致；用户既有授权内实现/验证/正常提交推送，未进入M7。本轮为局部修复自验，**待总控定向复审**；M6-04/05/08仍未验收，核心4/7、总核心64/76。

## R1：按实际Markdown语义记录答案图，阻断免审

原问题：正则把所有四空格行和转义反引号间正文删除，导致列表/转义反引号图片实际显示却写context，正式审阅接受N/A并校准null。正式红测14失败/30通过，另加历史已误收N/A校准反例1失败；输出保留red.xml/calibration-red.xml，非ImportError或夹具失败。

修复app/answering/image_selection.py，以markdown-it-py 4.0.0/default规则读取inline直接image token；与前端markdown-it 14.1.0一致禁HTML/linkify、启breaks，URL/ID及允许资产集合对齐。识别列表、段落续行、转义反引号、引用式/带标题/尖括号图；排除真正代码、转义图片、禁用HTML、外链及未授权资产，不递归图片alt。

共享tests/fixtures/answer-image-markdown.json的25个字面期望分别由Python和实际Vue渲染器运行。正式QueryRunner→历史/终态事件→RealQueryExecutor→评测→审阅/校准隔离测试证明两个边界记录answer_asset_ids/image_usage=answer，N/A返回422、校准409且零审阅/校准写入；正常图片0分可双轮校准为0。质量投影重新解析正文，即使旧metadata误标context、旧N/A已存在，也拒绝新建null校准。旧记录/旧校准不改写，发布核对保持pending；正文防御对任何受控图URL保守要求审核，不依赖旧资产ID完整性，不把无法展示的映射猜成不适用。

修复后定向45通过（39单元/6隔离HTTP集成），包含新增历史误收N/A窗口。总控原正式运行/审阅探针复制到新目录复跑5通过，原探针、pycache及失败XML未触碰。原双轮校准探针要求先收下N/A（201），现正确在前置入口422拒绝；不改其原断言凑绿，以新增正式测试验证拒绝后无校准及合法0分正路。

## R2：聊天旧引用明确未知关系，默认不读图

EvidenceCard无image_selection_version=1时不再把asset_ids全部当答案图；保留全部资产、展示“答案使用关系未记录”，展开历史图像入口后才创建img和读取。新版答案图仍默认显示，context仍折叠。正式ChatThread/SafeMarkdown浏览器测试还确认R1两类正文实际显示；旧原文/XSS/坏图测试仅补展开动作，原断言保留。

旧引用浏览器红测1失败（默认img=1），修复后审阅/引用12通过，完整离线浏览器44通过。折叠不意味着图片相关性提高，也不把旧配图0改成N/A。

## 实际验证

| 验证 | 本轮结果 | 原始证据 |
| --- | --- | --- |
| 后端完整阶段 | 1015 passed、2 deselected、0 skipped，退出0 | output/m6-protocol-r2/stage/backend.xml |
| 组成 | 613单元 / 135契约 / 267真实隔离存储集成 | 同上XML classname；模型注入，不冒称供应商调用 |
| 既有重导入 | 3通过，退出0 | stage/reimport.txt |
| 前端单元/浏览器 | 62 / 44通过，退出0 | frontend-final/unit.json、browser.json |
| 类型/构建 | 均退出0 | frontend-final/typecheck.txt、build.txt |
| 后端定向/原探针副本 | 45 / 5通过，退出0 | green.xml、original-probes.xml |
| 定向浏览器 | 12通过，退出0 | browser-green/，不另加到全量计数 |
| 前端共享矩阵 | 25通过，退出0 | frontend-contract.json，已纳入全量 |
| 真实001只读 | 12检查通过，退出0 | live-readonly.json |
| 原失败/提交证据保护 | 72份旧证据哈希一致 | prior-evidence.json及摘要raw_evidence |
| 依赖锁 | uv0.9.5 lock --check --offline退出0 | lock-check.txt、lock-scope.json |

所有路径均位于项目output/m6-protocol-r2下，原始日志/截图/trace本机保留不上传。正式红测14失败/30通过和独立历史校准1失败对应增加最后一项前后不同收集，不将它们合并成同一轮统计。完整阶段包含全部本轮测试；排除2项live_provider，未运行heldout。既有真实产物只读，不产生供应商付费或新的答案质量结论。

首轮完整脚本后端和前端单元/类型/构建通过，但浏览器43通过/1失败：旧窄屏大图用例缺新版关系标记，仍假设打开引用就读取图。仅在edge-states.spec.ts补默认无img断言和展开操作，原尺寸/无横向溢出/Escape焦点断言保留，业务代码未因此变化。这是测试前提需同步，不当作新业务红测。失败截图/trace与stage/commands.json原样保留；随后frontend-final目录完整重跑前端，全部退出0。最终命令索引final-commands.json明确引用首轮已通过的后端/重导入和第二次完整前端，不将首轮all脚本退出1改写成0。

## 可复验精确命令

```powershell
$env:M1_TEST_DB='m1_test_m4_m6_protocol_r2_red'
.venv/Scripts/python.exe -m pytest tests/unit/test_answer_image_selection.py tests/integration/test_rendered_image_review.py -q --tb=short --junitxml=output/m6-protocol-r2/red.xml
.venv/Scripts/python.exe -m pytest tests/integration/test_rendered_image_review.py -k historical_na -q --tb=short --junitxml=output/m6-protocol-r2/calibration-red.xml
pnpm -C frontend exec playwright test citations.spec.ts -g '历史引用不推断' --reporter=list --output=../output/m6-protocol-r2/browser-red
pnpm -C frontend exec vitest run tests/unit/answer-image-contract.test.ts --reporter=json --outputFile=../output/m6-protocol-r2/frontend-contract.json
$env:M1_TEST_DB='m1_test_m4_m6_protocol_r2_green'
.venv/Scripts/python.exe -m pytest tests/unit/test_answer_image_selection.py tests/integration/test_rendered_image_review.py -q --tb=short --junitxml=output/m6-protocol-r2/green.xml
$env:M1_TEST_DB='m1_test_m4_m6_protocol_r2_original'
.venv/Scripts/python.exe -m pytest output/m6-protocol-r2/original-probes/test_image_usage_probe.py output/m6-protocol-r2/original-probes/test_image_gate_probe.py -q --tb=short --junitxml=output/m6-protocol-r2/original-probes.xml
pnpm -C frontend exec playwright test reviews.spec.ts citations.spec.ts --reporter=list --output=../output/m6-protocol-r2/browser-green
.venv/Scripts/python.exe -m scripts.verification.run_m5_checks --output output/m6-protocol-r2/stage --group all
.venv/Scripts/python.exe -m scripts.verification.run_m5_checks --output output/m6-protocol-r2/frontend-final --group frontend
.venv/Scripts/python.exe -c "import runpy;runpy.run_path('output/m6-protocol-r2/recheck_live_readonly.py')"
.\output\m6-protocol-r2\uv-tool\bin\uv.exe lock --check --offline
.venv/Scripts/python.exe -m scripts.verification.check_m6_protocol_artifacts --summary docs/development/reviews/M6-04-relevance-chat-protocol-validation-r2.json --manifest docs/development/reviews/M6-04-relevance-chat-protocol-manifest-r2.json
```

红测命令对应修复前时点，不能在修后重跑覆写原证据。上列输出文件已存在，复验请选择新目录。完整脚本commands.json保存每条真实参数、退出码和耗时；随机测试前缀`m1_test_m4_m5_stage_2fe8172e`，每例独立子库；定向使用单独red/green/original前缀，不删现场字段/集合。只读脚本从私有会话文件读取登录信息，不打印值；除登录外全部GET及Mongo读取，不重放observations POST。

## 真实001、依赖、兼容与回滚

真实001答案/题指纹、用户原话2/2/N/A/0、单条assistant转录及原受保护集合摘要不变，正式human仍0、gate pending；两张原图HTTP、hash、完整解码通过，新选择器派生0答案图，不回写旧结果。**新增模型/真实human/observation/校准写入均0**。未重启现有真实001服务，不能把历史API只读复核当作新门禁真实部署；新路径由独立测试库正式HTTP验证。

新增markdown-it-py 4.0.0及mdurl 0.1.2，安装前dry-run仅新增这两个纯Python包，以--no-deps最小安装。pyproject/uv.lock/worker requirements同步，原193个非根锁记录不变；uv离线锁检查通过，工具装在output而非项目环境。无新配置/模型、PyTorch/CUDA升级或API结构变化；复用清单/许可/ADR-067/契约/运行说明已同步。共享矩阵约束已覆盖行为，不声称两种实现对所有任意输入永远相同。

反向本轮代码提交并恢复锁即可回滚；保留所有旧账本、图像、分数、校准、原失败/原快照，不删库、不重导入。回滚会恢复已知配图免审问题，不能作为安全验收通过。M6独立新规则基线/预校准/新候选链、完整dev及固定报告仍待完成；不要求用户重复已有判断、不进入M7。

Git：显式文件清单审阅后正常提交/推送main，不强推。tmp、evals、output、原始evidence与私有配置不上传；新摘要只存结果和哈希，独立manifest不覆盖首轮或总控产物。自身提交SHA与远程头在最终交接补记，不循环amend。
