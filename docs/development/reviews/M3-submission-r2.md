# M3 第二轮执行提交 · R1/R2

日期：2026-10-24。依据[首轮总控审查](M3-review.md)修复，基线`6ccd3c78fe750ddd5ef6d7a108dfde12b9a64280`。**M3执行自验11/11、核心43/76，仅待总控复审；M4未授权。**原审查、首轮提交/快照、总控探针、原始evidence及未跟踪evals均保留，不覆盖、不上传原件。

机器证据：[本轮实际摘要](M3-validation-summary-r2.json)、[独立快照](M3-artifact-manifest-r2.json)。精确命令、环境、失败与回滚详见[M3-11第二轮记录](../records/M3-11.md)。R1提交`e751ff80b0fc39dcecd0ea0b36e65a10c6f58b23`，R2提交`0e75640a6bb5cfe6cd413670d70083b050df4227`，均已正常推送main并核对远程完整SHA一致。交付文档提交自身SHA由最终交接补记。

## R1 · 缓存会话恢复

修复前：A旧完成轮缓存→B→A，旧快照先恢复后一次性`restored`门闩屏蔽新活动指针；反向时序也可能被迟到旧快照覆盖，无法查看当前候选、确认或停止。

修复后：[ChatPage.vue](../../../frontend/src/features/chat/ChatPage.vue)协调本轮会话目录和历史刷新，以活动指针或已读末页运行选择恢复目标；目标身份变化继续恢复，同一目标刷新保留流状态。请求代次与会话epoch共同拒绝迟到响应；创建后同时刷新会话目录/历史，防止旧活动指针回盖。无活动指针且历史未读到末页时禁发，不把第一页末条当最终运行。

正式业务红测R1三项失败，修复后扩展为[5项浏览器回归](../../../frontend/tests/e2e/cached-run-recovery.spec.ts)：历史先到、目录先到、旧快照迟到、快照期间切会话、历史后续页。实际断言新run订阅、当前候选、禁重复发送、确认expected_version=2、运行version=3及取消POST；跨会话不订阅旧流。原历史/流/引用回归保留通过。[任务记录](../records/M3-04.md)。

## R2 · 跨页设备范围

修复前：实际目录搜索/分页选第101个设备，问答首100项不含其option，选择框空白但请求仍携带该ID。

修复后：[ui store](../../../frontend/src/stores/ui.ts)保留当前用户/kb内的设备描述，[目录](../../../frontend/src/features/products/ProductsPage.vue)传递实际设备；[选择查询](../../../frontend/src/features/chat/queries/product-selection.ts)对首100项以外设备按真实型号做一次现有授权搜索、精确匹配ID，再给[选择框](../../../frontend/src/features/chat/components/ProductSelector.vue)补可读型号。描述本身不作为授权事实。没有描述、失效、断线或等待时有可读状态，按钮与发送入口同时禁发；允许主动清空。范围/退出/401同时清ID与描述。

正式业务红测R2一项失败，修复后[5项浏览器回归](../../../frontend/tests/e2e/selected-product.spec.ts)覆盖101项目录搜索、分页选择、新建/切会话、可见型号与payload一致、主动清空、失效/断线/慢核对禁按钮及Enter、切范围/退出再登录清理。新增[3项单元](../../../frontend/tests/unit/product-selection.test.ts)覆盖无描述、旧身份/范围描述与迟到搜索；既有身份单元扩展401清描述。[M3-06记录](../records/M3-06.md)、[M3-09记录](../records/M3-09.md)。

同名搜索返回上限100项，极端重复型号可能无法精确核对；此时明确拒绝并要求重选，不静默提交、不猜型号、不无限遍历目录。未新增后端接口或变更授权边界。取舍及契约已同步[ADR-037](../DECISIONS.md)和[公共契约](../../plans/DEVELOPMENT_CONTRACTS.md)。

## 本轮实际验证

所有下表成功命令退出0，数量按原始报告读取；不同测试类型分别列示，定向10项包含在完整24项内，不重复计数。

|检查|本轮实际结果|本机evidence路径|
|---|---|---|
|正式业务红测|4 failed，退出1，43.062秒；R1三、R2一|M3-r2-red.txt、M3-r2-red-results.json|
|联合定向浏览器|10 passed、0 skipped，34.736秒|M3-r2-targeted-final.txt、M3-r2-targeted-final-results.json|
|完整后端阶段|346 passed、2 deselected、0 skipped；309.94秒；180单元/83契约/83集成目录|M3-r2-stage.txt/xml|
|前端单元|37 passed、9文件，10.15秒；较首轮新增3项|M3-r2-unit.txt|
|完整离线浏览器|24 passed、0 skipped、0 flaky，49.850秒；较首轮新增10项|M3-r2-offline.txt、M3-r2-offline-results.json|
|既有重导入|3 tests OK，0.517秒|M3-r2-reimport.txt|
|安装/类型/构建|frozen-lockfile一致，类型通过，728模块/6.75秒|M3-r2-install.txt、M3-r2-typecheck-final.txt、M3-r2-build.txt|
|原真实产物重新只读复核|8检查通过、4条持久消息有序|M3-r2-live-recheck.json/txt|
|摘要/源码快照|显式选择r2摘要、r2 manifest；证据hash、文件hash、本地链接、构建/历史trace后端敏感值扫描；计数见新manifest|M3-r2-artifact-build.txt、M3-r2-artifact-check.txt|
|检查器补充反例|3个内存副本：伪造后端数量、伪造前端数量、错选红测报告均拒绝；不计入测试总数|M3-r2-artifact-counterchecks.txt|

后端隔离目标`m1_test_20261024_m3_r2_stage`；集成目录含真实存储/Linux worker/本机模型及模型端口注入，不统称83项付费全链路。7项警告是既有SWIG弃用提示。浏览器使用真实Vue/Query与离线协议/合成PDF；未模拟身份的独立布局/PDF用例有到8000连接拒绝日志，套件24项实际通过，不据此声称真实API通过。安装和构建在浏览器结束后顺序运行，避免Vite资源复制重载。

## 历史证据、失败与未验证边界

本轮新增真实浏览器运行0、付费调用0。原真实工作台与真实登录各1项仅作为已接受的历史证据；本轮重新只读核对真实两轮答案/引用/事件、精确修订原件、导入发布和设备关联，8项通过。原flow SHA256为`52cd0cbc3820e78c2b725d2b5df42b32c0ac6f834223b151626e742aa087d96e`，历史阶段付费回答仍为4，不当成本轮调用。此次交互修复由实际Vue离线协议覆盖，原产物复核仍有效，未重复付费问答。

typecheck首次因查询key参数数不符退出2，修正后通过；联合扩展浏览器首跑9通过1超时为知识范围定位器错误，修正角色定位及目录缓存操作后10通过，原输出/JSON/失败trace保留。这些均不是业务红测。首次红测字面`--`使output未正确解析，trace写入默认test-results并被后续运行替换；红测控制台与JSON原件仍在，**不宣称红trace已独立归档**。新摘要登记35份本机原始证据hash；最终快照命令自身输出另存，不自循环登记。

未新增真实大PDF浏览器Range/性能、真实解析bbox全链路、生产部署或长期压力验收。保留原提交的这些边界，不将合成PDF和后端206代替浏览器大文件验收。未进入M4。

## 文件、数据与回滚

代码范围为ChatPage、ProductSelector、product-selection查询、ProductsPage、ui store和对应浏览器/单元测试；没有后端/API/事件/schema/配置/依赖变更。同步04/06/09/11记录、清单、阶段步骤、进度、变更、契约、决策和前端说明；快照列出本轮全部修改文件。

数据写入仅独立回归测试库/集合/前缀；原课程数据、解析缓存、桶策略和旧入口不改。所有原始evidence、账号、trace、evals、模型及运行数据未暂存或上传。回滚使用两笔修复的反向提交并运行相同定向验证；不删除数据，回退会重新引入R1/R2交互问题。首次直连推送超时、7890未监听，随后直连恢复并正常推送，无强推、无永久代理修改。详见[本轮Git交接](M3-git-handoff-r2.md)。

**等待总控复审M3，不自行标记通过，不进入M4。**
