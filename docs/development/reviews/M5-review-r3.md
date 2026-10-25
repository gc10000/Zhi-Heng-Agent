# M5 总控独立复审 · 第3轮

日期：2026-10-25。审查实现`b273f6a66446f9d173cfa6be973a5a18b4e7ead0`、交接`d283aac1332860ae216b83272b43a42aa6cee6b6`和统计更正`65cf4b5e7d7b3a22d1b5eb74dbb4e11cff4ec0f2`；基线为[第二轮总控](M5-review-r2.md)的`8b0ad6140dc36c64de53bbe934db5512d2f351e6`。

结论：**需修复。R1保持关闭；R2原递归与R3新格式撤回的原反例已通过，但归档终态事件、旧格式撤回及显式新选择仍有遗漏。重开M5-05/08，M5核心5/7、总核心58/76；M5-06延期，M6未授权。** 本轮只审查、隔离验证与维护文档，不修改业务实现，新增付费调用0。

## 已接受的修复

首轮R1/R2和第二轮两个原探针合计4通过；未包装的原归档递归探针另1通过（仅改输出路径以保留旧失败证据）。归档恢复可进入`interrupted`并释放自身，未再抛`RecursionError`；未归档版本门禁及fencing保留。当前新创建的撤回聚合会冻结`subject_withdrawn=true`，不带新型号时正式QueryRunner返回澄清；正式新增测试中的问题文本明确写AX-48可正常执行。本轮不重复否定这些已验证路径。

## R2 · P2，未关闭：归档领取直接写终态，绕过事件outbox

位置：[app/runs/repository.py](../../../app/runs/repository.py)第133—145行`_interrupt_archived()`；调用入口是[app/runs/commands.py](../../../app/runs/commands.py)的`start()`。

`_interrupt_archived()`直接CAS修改`state/claim_state/error/version`后释放占用，没有将`run.interrupted`、seq和待投递outbox与终态一同持久化。另一条`RunCommands.recover()`归档分支使用EventLedger，只有这条路径满足现有[事件契约](../../plans/DEVELOPMENT_CONTRACTS.md)第4节的终态outbox要求。

独立真实Mongo反例：正常创建已claimed/pending的run，经公开HTTP PATCH归档，再由实际`QueryRunner.execute()`启动，或直接调用实际`RunCommands.start()`。运行变为`interrupted`、自身占用已释放，但`seq=0`、事件列表为空。重建仓储/事件实例并执行两次恢复仍补不出终态事件。公开GET快照返回200/interrupted，公开GET events也返回200，但正文为空，未回放任何`run.interrupted`。另外混合并发`reconcile/recover`探针同样观测到终态无事件。对照只调用归档扫描的用例通过，证明两条终止路径不一致。

影响是持久状态与事件协议不一致，按执行与扫描先后顺序丢失终态通知/重放。现有Vue断流后可GET快照恢复，不能据此声称页面永久卡死；快照兜底也不能修复缺失的持久事件。本例为刚创建的独立run，不涉及24小时TTL到期。

修复要求：归档的领取、worker启动、扫描及归档竞态出口统一遵循状态/seq/outbox的同文档原子终态协议，再幂等投递并释放自身占用。不能终态后另行裸写一条事件，或吞掉冲突并假定已有事件。正式测试覆盖worker先于扫描、公开SSE、状态保存后投递前中断、并发领取/扫描恰好一个终态及旧worker不能写入/释放新占用。保留本轮有界恢复和未归档门禁。

## R3 · P2，未关闭：旧撤回格式失效，新产品选择仍消费旧主体

位置：[app/support/commands.py](../../../app/support/commands.py)第11行及第40—42行缺省值；[app/runs/query_runner.py](../../../app/runs/query_runner.py)第136—141行主体边界只在没有requested_product_ids时生效。

第一处是升级兼容：r2已支持设备撤回，其合法持久聚合有`device.value=null/confirmed=false/source=unknown`、`withdrawn_by`及`history.withdrawal`，但没有r3才加入的`subject_withdrawn`。新消费者将字段缺失一律视为false，没有按已有撤回记录恢复边界。独立兼容夹具保留撤回的全部业务字段，只去掉新增标记来复现r2格式；下一轮不传product_ids，仅问“它的电源呢”，正式QueryRunner实际`completed/answer/confirmed_context`，又以AX-24回答。当前槽位仍为null，旧撤回历史也仍存在。该探针仅写随机测试库，不改真实旧账本，也不冒称读取了某个真实用户的升级故障。

第二处是明确的新选择：当前r3格式撤回后，新增AX-48目录项，本轮请求明确传`product_ids=[AX-48的ID]`并问“它的电源呢”。分支因为requested_product_ids非空而跳过主体重置，旧AX-24助手历史仍进入计划器，实际得到`awaiting_input/clarify/selection_context_conflict`，没有按新选择回答。问题文本直接写AX-48的测试可通过，不能代替设备选择器这一正式输入路径。没有撤回时的真实历史/选择冲突门禁仍应保留；这里旧主体已被明确撤回，不应继续制造冲突。

修复要求：对旧格式已有撤回事实做确定性、幂等兼容识别或显式迁移，不把所有旧聚合都重置，也不删除旧消息/run/草稿；既有明确设备且从未撤回的聚合保持原语义。撤回边界应同时隔离旧历史和旧默认选择，在本轮新product_ids、产品确认恢复以及文本明确型号等入口接受新的用户确认。补充正式QueryRunner的旧格式升级、新格式选择器、确认恢复、未撤回冲突对照及无新输入保持澄清测试。保留本轮唯一目录项不能自动复活的修复。

## 独立验证与证据边界

实际阶段命令、结果、原件SHA256和探针脚本见[第三轮独立摘要](M5-review-validation-r3.json)。新增边界初组3失败/1通过，后续公开API与兼容格式2失败；共6个独立用例5失败/1通过，对应上述两个发现，不计为5个业务问题。旧原探针4通过和未包装递归1通过均保留。集成使用随机独立Mongo及注入模型，不是供应商端到端。

独立完整后端**795 passed、2 deselected、0 skipped、7 warnings，558.08秒，退出0**；既有重导入**3项，退出0**。前端**37单元、28离线浏览器**、类型检查和构建退出0，浏览器0跳过/0意外失败/0不稳定；阶段通过不抵消上述新增反例失败。

提交r3的manifest只登记8份证据hash，没有前两轮`files/baseline_commit`快照结构；原标准校验器因缺少base参数退出2，不计业务失败。随后逐项核对8份hash，并按Git差异独立审查23文件、10Python语法、260本地链接及敏感值，均通过。没有覆写提交manifest/摘要或前两轮快照。第三轮的500单元/128契约/169集成是包含2个live_provider排除项的797收集数；795实际执行组成为500/128/167，须清楚区分，不把169都写为通过。

本轮新执行原M5真实产物只读复核16项全部通过，未生成新答案；报告内逻辑生成1次属于原M5历史执行。M3旧事件TTL到期已在第二轮查明，本轮不重新生成事件或答案，沿用第二轮7/8的已说明边界，不宣称新8/8。未进行新真实浏览器全流程、dev/heldout或质量提升评价。原课程资料、原始产物、evals和全部失败证据保留本机。

## 后续授权与交接

仅授权M5内继续修复上述R2/R3遗漏、保留R1及本轮通过路径，先加入能揭示缺陷的正式回归，再最小修复及阶段复验，新增`M5-submission-r4.md`和对应新摘要/manifest。修订版manifest需覆盖源码/文档冻结信息及所有实际报告hash，不能只凭登记范围列表主张文件内容已冻结。M5-06延期，M6、部署、公开Release仍未授权。

本轮开始本地HEAD为65cf4b5；只读远程核头先连接超时300秒、后一次21秒连接失败，暂不能独立确认用户所述远程一致。只读失败不以origin/main缓存代替远程核头。最终审查文档提交与推送实际结果在交接回复记录，不循环amend；不强推、不改全局代理，原始output/evidence/evals不上传。
