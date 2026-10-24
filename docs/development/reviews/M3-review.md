# M3 总控审查 · 第1轮

日期：2026-10-24。审查源码交付：`d1fa5e106aa76b4cdf0d6c6c6484344a69c2478f`；接续文档HEAD：`a259703`；基线：`ed18aebc0334accb4438a5e9f657920d83ff8274`。结论：**需修复，M4未授权。**

已读取[执行提交](M3-submission.md)、[原摘要](M3-validation-summary.json)、[原快照](M3-artifact-manifest.json)、实际源码、任务计划及真实证据。常规回归通过；实际Vue页面的补充协议探针确认两个交互正确性问题。重开M3-04、M3-06、M3-09、M3-11，M3当前7/11、核心39/76；其余验收结果保留。本轮只做独立审查与文档维护，未修改业务源码。

## 独立验证

| 检查 | 实际结果 |
| --- | --- |
| 后端完整阶段回归 | **346 passed、2 deselected、0 skipped、7 warnings，300.56秒，退出0**；180单元、83契约、83集成目录用例 |
| 前端安装、类型、构建 | frozen-lockfile安装、typecheck、build均退出0；构建727模块，9.43秒 |
| 前端单元 | **34项、8文件通过，5.45秒，退出0** |
| 离线浏览器 | **14项通过，24.0秒，退出0**；API协议模拟与合成PDF，不称为真实供应商端到端 |
| 既有重导入 | **3 tests OK，0.007秒，退出0** |
| 原提交快照 | **110文件hash、5份Python语法、221个本地链接、19份构建文本敏感值扫描通过**；文档修改前核对 |
| OpenAPI输入类型 | 重新生成到本机evidence，与提交schema.d.ts的文件hash一致 |
| 原真实产物只读复核 | **8项通过、4条消息有序**；本轮新增付费调用0，不冒充重新执行真实浏览器或供应商问答 |
| 目视核对 | M3-11桌面、390px手机证据抽屉、真实导入截图可读；来源、修订与导入发布状态明确 |
| 补充交互反例 | **2项预期失败，进程退出1，无浏览器pageerror**：缓存会话当前运行恢复、目录跨页选中设备可见性 |

后端使用`M1_TEST_DB=m1_test_20261024_m3_controller`，命令`.venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -m 'not live_provider' -q --junitxml=docs/development/evidence/M3-review-stage.xml`，UTF-8、关闭业务文件/控制台日志；7项警告为既有PyMuPDF SWIG弃用提示。真实存储/Linux worker/模型端口注入的集成目录不统称供应商端到端；运行时间不作为性能收益。

前端使用`pnpm -C frontend install --frozen-lockfile`、`typecheck`、`build`、`test:unit`。离线浏览器清除M3_LIVE_CONFIG，执行`pnpm -C frontend test:e2e --reporter=list,json --output=../docs/development/evidence/M3-review-offline-artifacts`，JSON输出另存M3-review-offline-results.json，不覆盖原报告；Vite上未模拟身份接口的独立布局/PDF用例产生后端未运行的代理连接日志，套件14项实际通过，不据此声称真实API验收。

原产物命令为`.venv/Scripts/python.exe -m scripts.verification.recheck_m3_live --config docs/development/evidence/M3-live-config-stage-ready.json --flow docs/development/evidence/M3-live-config-stage-ready.flow.json --output docs/development/evidence/M3-review-live-recheck.json`。核对两轮完成、真实参数与追问、精确初始修订引用、唯一终态/事件顺序、上传发布与产品范围、原件hash；source flow SHA256为`52cd0cbc3820e78c2b725d2b5df42b32c0ac6f834223b151626e742aa087d96e`。原真实浏览器1条正式链路和1条登录记录保留接受，阶段累计付费回答仍为4，本轮没有新增。

## R1 · P2 · 切回缓存会话后，一次性恢复标志阻止接收新的活动运行

位置：[ChatPage.vue](../../../frontend/src/features/chat/ChatPage.vue)，第33–40行；相关查询在`frontend/src/features/chat/queries/conversations.ts`。关联M3-04及M3-11。

复现：先打开A，缓存其已完成旧轮及`active_run_id=null`，切到B；另一标签页在A发起新轮。再切回A，Vue Query立即提供旧缓存并后台刷新。让旧run快照先返回，历史新页250ms后返回，目录500ms后返回。这些均为同一用户、同一知识范围、正常授权响应；新历史包含新轮用户消息，目录明确返回`active_run_id=new-active`。

实际：恢复watch先请求`old-done`，随后将`restored=true`。新目录和新历史到达时第34行直接return；最终只读过`old-done`，从未请求`new-active`，新问题虽已显示，页面仍显示“回答完成”，停止按钮0个、填写问题后发送可用。新的流、候选确认和取消无法从该页面恢复；后端同会话占用保护仍在，不能据此声称后端接受了并发运行。硬刷新可绕过此缓存时序，不构成修复。

这是缓存/网络交错：未延迟的新历史先返回时可以恢复新轮；250/500ms时序下稳定失败。不能用一次冷启动刷新或只测试迟到旧会话响应代替回归。

要求：恢复必须协调当前会话的目录/历史新鲜度与所选运行身份。不能让旧缓存完成快照永久屏蔽随后到达的当前活动run；同一次恢复中的多个异步run读取也应有明确的胜出条件，防止旧响应覆盖新轮。保留跨会话/身份隔离、历史分页与终态幂等；不要求每条增量重新请求快照。

验证：先加正式浏览器红测，真实挂载Vue Query缓存，执行A→B→A，并以受控延迟返回新活动目录和已持久的新用户消息。断言最终恢复新run、订阅正确run、展示其真实状态/候选、禁重复发送且可确认/取消；另覆盖历史先到、目录先到及旧run快照迟到，确认无旧轮覆盖或跨会话串流。不需付费模型调用。

## R2 · P2 · 目录所选设备不在选择框首100项时，实际提交范围不可见

位置：[ProductSelector.vue](../../../frontend/src/features/chat/components/ProductSelector.vue)，第10–12行；目录入口为[ProductsPage.vue](../../../frontend/src/features/products/ProductsPage.vue)第13行，提交为ChatPage.vue第53行。关联M3-06、M3-09及M3-11。

复现：设备目录搜索/分页查到首100项以外的`p-101 / BEYOND-100`，点击“选择设备”，再打开或新建会话。目录把ID存进ui.productIds，但问答选择框仅请求`/products?...&limit=100`，没有该ID对应option。

实际：选择框`value=""`、`selectedIndex=-1`、无可见选中型号；填写问题发送时实际payload仍是`product_ids:["p-101"]`。因此界面无法让用户核对本轮设备范围。“更多设备请从设备目录选择”的提示正好引导到此失效路径。该反例没有发现后端越权，而是已授权范围的显示与实际提交不一致。

要求：从目录、搜索或后续页选中的授权设备，必须在问答中有可读型号并与实际提交ID一致。可以保留选中设备描述、按授权目录解析ID或提供分页/搜索选择；不能仅清空显示、伪造型号、默默丢掉选中ID或加载无限目录来规避。无法解析/已失效的设备应有明确状态，阻止不可核对的静默提交；切知识范围/登录失效仍要清理旧选择。

验证：先加正式浏览器红测，构造至少101项并通过实际目录搜索或分页选择首100以外的项；回到问答后断言选中型号可见，发送payload与该型号匹配。覆盖新建会话、切换会话、手动清空选择和知识范围/身份清理。该问题可完全离线回归。

## 接续与边界

授权开发会话仅在M3内连续修复R1/R2：先正式红测，再最小实现，维护任务记录和必要契约，完成定向及阶段回归；重开M3-04/06/09/11，阶段7/11、核心39/76。M3-05流协议、既有鉴权/授权、安全Markdown、精确修订来源、PDF与真实导入的有效证据保留，不要求无关重做。M4及后续实现仍未授权。

生成新的`M3-submission-r2.md`、实际验证摘要及独立manifest，保留本轮提交、首轮快照、失败与成功原证据。不要回写旧manifest匹配审查文档；如需核对旧快照，使用原提交的独立检出。先只读复核现有真实产物，仅在改动使原证据失效时做必要的真实验收，不机械重复付费。大PDF真实Range/性能、真实解析bbox全链路仍按原提交未验收边界表述，合成PDF/后端206不能冒充这两项。

本机最终有效探针：`docs/development/evidence/M3-review-ui-probes.mjs`，对应`M3-review-ui-probes-confirmed.json/txt`；执行`node docs/development/evidence/M3-review-ui-probes.mjs`，两个业务预期为false且退出1。初次探针的依赖路径/协议字段/定位器调整不计业务失败；最终版本包含真实协议必需字段和新轮用户消息。独立脱敏汇总见[M3-review-validation.json](M3-review-validation.json)。原始evidence与evals/均保留不上传；原课程数据、桶策略、依赖和真实配置未改，独立回归的小样数据保留。本轮自启Vite已停止。

Git：默认代理此前未监听，直连曾超时；本轮稍后直连只读与fetch恢复，实时远程main为`7691b5d7c0f2914d09b4cedb6419098541953fd8`，与本地无分歧、仅落后两笔原交付提交。依用户现有授权正常提交/推送本审查文档并补齐原交付；实际结果在最终交接记录，不用强推、不修改永久代理。Git同步不代表M3审查通过。
