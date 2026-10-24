# M3：Vue 3 技术支持工作台开发 ToDo

> 执行方式：按任务逐项开发；使用 superpowers:executing-plans 技能。任务中的步骤采用勾选框跟踪；不自行派发子代理。

**目标：**交付“Vue 3 技术支持工作台”阶段可独立验收的能力。
**架构：**沿现有 Python/FastAPI/LangGraph 链路做小步适配；Vue 3 前端只消费统一 API 与事件契约。保留旧入口与数据直至本阶段验收通过。
**技术栈：**Vue 3 / TypeScript / FastAPI / MongoDB / Milvus / MinIO；具体测试工具与依赖在对应任务中建立。
**设计依据：**[优化方案](../2026-10-22-technical-support-optimization.md)、[接口与数据契约](../DEVELOPMENT_CONTRACTS.md)、[开发总清单](../DEVELOPMENT_TODO.md)。

## 进入条件与执行约束

当前结论：M3第2轮总控通过，R1/R2关闭，11/11、核心43/76。独立346后端/37单元/24离线浏览器/既有3/只读8及原反例/新交错通过，本轮付费0。授权M4-01至10按依赖执行，本会话不启动实现；M5及后续未授权。详见[第二轮总控结论](../../development/reviews/M3-review-r2.md)。以下保留原执行/修复时点和证据。

当前状态：首轮R1/R2已修复，第二轮执行自验11/11、核心43/76，待总控复审。仅授权在M3内处理R1缓存会话新活动run恢复、R2目录首100项外设备可见选择，先正式红测再实现，已重提[第二轮材料](../../development/reviews/M3-submission-r2.md)与独立摘要/manifest；M4未授权。完整触发与验证见[M3首轮审查](../../development/reviews/M3-review.md)。下文原执行勾选中，未受影响的已验收步骤保留。

M2已通过第2轮总控审查，授权从M3-01连续执行至M3-11，按依赖逐项验收；阶段末提交总控，M4未授权。真实API与SSE契约来自M2-12，范围见[M2授权结论](../../development/reviews/M2-review-r2.md)。M3-01可先做最小登录/API/SSE纵向小样验证兼容性，后续任务完善对应模块；预备接线不等于后续任务已验收。

- 以下文件均为**计划创建/修改**，不表示已经存在；执行前用 `rg` 核对真实接口与源码。
- 本阶段遵守总清单中的 Vue 3、中文注释、数据隔离、配置脱敏和完成证据规则。
- 每个代码任务先增加能揭示错误的用例，再做最小实现；文档、样式等低影响变更按实际结果检查，不写镜像测试。
- 每完成一个任务，记录验证命令、输出摘要、涉及文件和遗留问题；验证通过后才勾选[总清单](../DEVELOPMENT_TODO.md)，并更新[进度](../../development/PROGRESS.md)与[变更记录](../../development/CHANGELOG.md)。
- 命令均从项目根目录运行；`pnpm -C frontend` 命令需 M3-01 建立对应 scripts 后才存在。依赖安装和测试数据准备不表示任务验收通过。
- 每个任务验证其直接影响的行为，阶段验收时再执行阶段回归；不要重复运行无关全量测试。

<a id="m3-01"></a>
### M3-01：Vue 工程与复用兼容性小样

**依赖：**M2-12。
**文件：**`frontend/package.json`; `frontend/pnpm-lock.yaml`; `frontend/vite.config.ts`; `frontend/src/main.ts`; `docs/reuse/manifest.json`; `THIRD_PARTY_NOTICES.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-01.1** Vue 3.5+/TS/Vite/Router/Pinia/Vue Query。
- [x] **M3-01.2** 接 shadcn-vue 侧栏/分栏/对话框与 PDF.js。
- [x] **M3-01.3** 固定 Node/包管理器及通过构建的依赖。
- [x] **M3-01.V** 验证：pnpm -C frontend install --frozen-lockfile；pnpm -C frontend typecheck；pnpm -C frontend build。
- [x] **M3-01.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**一个真实流式问题、一条引用和取消可用；记录复用路径/commit/license；默认不安装 React 或 assistant-ui。

<a id="m3-02"></a>
### M3-02：API 客户端、生成类型与登录

**依赖：**M3-01。
**文件：**`frontend/src/lib/api/client.ts`; `frontend/src/lib/api/schema.d.ts`; `frontend/src/app/router.ts`; `frontend/src/stores/auth.ts`; `frontend/src/features/auth/LoginPage.vue`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-02.1** 从版本化 OpenAPI 生成类型并封装 cookie/CSRF/错误。
- [x] **M3-02.2** 登录过期清缓存、断开流。
- [x] **M3-02.3** 导航守卫提供体验，权限仍由后端校验。
- [x] **M3-02.V** 验证：pnpm -C frontend test:unit -- auth-client；pnpm -C frontend typecheck。
- [x] **M3-02.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**浏览器无供应商密钥；401/403/409/410 显示正确；退出后无上个用户缓存。

<a id="m3-03"></a>
### M3-03：三栏布局与响应式导航

**依赖：**M3-01。
**文件：**`frontend/src/app/WorkbenchLayout.vue`; `frontend/src/components/ui/sidebar/`; `frontend/src/components/ui/resizable/`; `frontend/src/app/router.ts`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-03.1** 会话/问答/证据三栏。
- [x] **M3-03.2** 390px 以抽屉切换，1500px 可拖拽。
- [x] **M3-03.3** 提供资料、记录、评测导航与空状态。
- [x] **M3-03.V** 验证：pnpm -C frontend test:e2e -- layout.spec.ts。
- [x] **M3-03.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**窄屏无横向溢出；键盘可切换与关闭抽屉；大图和长文件名不撑坏布局。

<a id="m3-04"></a>
### M3-04：会话目录与历史恢复

**依赖：**M3-02,M3-03。
**文件：**`frontend/src/features/chat/queries/conversations.ts`; `frontend/src/features/chat/components/ConversationList.vue`; `frontend/src/features/chat/ChatPage.vue`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-04.1** Vue Query 管列表/历史分页。
- [x] **M3-04.2** URL 关联 conversation_id。
- [x] **M3-04.3** 按用户与知识范围分 query key。
- [x] **M3-04.4** 切会话先恢复快照；R1需协调缓存与新目录/历史，拒绝旧轮覆盖新活动run。
- [x] **M3-04.V** 验证：pnpm -C frontend test:unit -- conversation-history。
- [x] **M3-04.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**刷新恢复已有答案与引用；跨会话不显示旧增量；新建/重命名/归档按 API 能力提供。

<a id="m3-05"></a>
### M3-05：SSE composable 与运行状态

**依赖：**M3-02,M3-04。
**文件：**`frontend/src/features/chat/composables/useRunStream.ts`; `frontend/src/features/chat/stores/run.ts`; `frontend/src/features/chat/components/ChatThread.vue`; `frontend/src/features/chat/components/ChatComposer.vue`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-05.1** 原生 EventSource 配合同源 cookie。
- [x] **M3-05.2** 按 run/seq 去重，410 改读快照。
- [x] **M3-05.3** Pinia 保存活动 run，支持停止/重试。
- [x] **M3-05.4** 组件卸载关闭订阅。
- [x] **M3-05.V** 验证：pnpm -C frontend test:unit -- run-stream；pnpm -C frontend test:e2e -- stream.spec.ts。
- [x] **M3-05.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**同会话 409 有提示；网络中断恢复无重复；停止另发取消而非仅 abort；失败保留部分文本但不显示成功。

<a id="m3-06"></a>
### M3-06：型号确认与阶段进度

**依赖：**M3-05。
**文件：**`frontend/src/features/chat/components/ProductClarification.vue`; `frontend/src/features/chat/components/RunProgress.vue`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-06.1** 候选型号卡片提交 run version。
- [x] **M3-06.2** 显示真实 stage.changed 与 awaiting_input。
- [x] **M3-06.3** 切设备可显式确认，模型输出不冒充真实执行记录；R2需显示并核对目录跨页所选设备。
- [x] **M3-06.V** 验证：pnpm -C frontend test:e2e -- clarification.spec.ts。
- [x] **M3-06.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**刷新后候选可恢复；已结束 run 禁止再次提交；进度来自事件，非计时假进度。

<a id="m3-07"></a>
### M3-07：结构化引用与图片联动

**依赖：**M3-05。
**文件：**`frontend/src/features/evidence/components/EvidenceDrawer.vue`; `frontend/src/features/evidence/components/EvidenceCard.vue`; `frontend/src/features/evidence/queries/citations.ts`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-07.1** 答案编号定位 citation_id。
- [x] **M3-07.2** 加载授权来源、章节、页码、原图。
- [x] **M3-07.3** 区分原文与 VL 描述。
- [x] **M3-07.4** Markdown 禁止未知 HTML 与危险链接。
- [x] **M3-07.V** 验证：pnpm -C frontend test:unit -- evidence-security；pnpm -C frontend test:e2e -- citations.spec.ts。
- [x] **M3-07.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**引用落到本次实际使用证据；坏图/无页码有清楚状态；越权资料不加载；XSS 输入不执行。

<a id="m3-08"></a>
### M3-08：PDF 原件定位与文本层

**依赖：**M3-07。
**文件：**`frontend/src/features/evidence/components/PdfViewer.vue`; `frontend/src/features/evidence/components/CitationOverlay.vue`; `frontend/src/features/evidence/composables/usePdfDocument.ts`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-08.1** PDF.js worker/字体本地固定版本。
- [x] **M3-08.2** 支持 Range、按需页渲染、缩放旋转及文本层。
- [x] **M3-08.3** bbox 坐标变换与取消旧渲染任务。
- [x] **M3-08.V** 验证：pnpm -C frontend test:unit -- pdf-coordinates；pnpm -C frontend test:e2e -- pdf-viewer.spec.ts。
- [x] **M3-08.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**不同缩放/旋转下高亮落点正确；无 bbox 仅跳页/章节；切换文档无旧渲染覆盖新文档。

实际接线调整：v1引用原响应不含原件描述，M3-08以兼容可空`original`字段返回精确修订登记的asset_id/media_type/name/url，经相同授权复核，不暴露对象键或签名URL。前端不自行推导ID；旧未登记原件保留null并仍可按原文溯源。

<a id="m3-09"></a>
### M3-09：产品资料与导入发布界面

**依赖：**M3-02,M3-03。
**文件：**`frontend/src/features/products/ProductsPage.vue`; `frontend/src/features/documents/DocumentsPage.vue`; `frontend/src/features/documents/ImportJobPanel.vue`; `frontend/src/features/documents/RevisionPanel.vue`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-09.1** 产品/资料筛选、上传、任务阶段与错误重试；R2需修复目录所选设备回问答显示一致性，其余证据保留。
- [x] **M3-09.2** 切片/图像预览、版本比较和维护者发布/撤回。
- [x] **M3-09.3** 显示解析降级质量。
- [x] **M3-09.V** 验证：pnpm -C frontend test:e2e -- documents.spec.ts。
- [x] **M3-09.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**上传成功不等于发布；查看者无发布按钮且后台仍鉴权；重复提交不创建多任务；失败可定位阶段。

<a id="m3-10"></a>
### M3-10：可访问性、异常与性能检查

**依赖：**M3-06,M3-08,M3-09。
**文件：**`frontend/src/components/`; `frontend/tests/e2e/edge-states.spec.ts`; `docs/development/records/M3-10.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-10.1** 核对空/慢/错误/超长回答/断图/过期登录。
- [x] **M3-10.2** 按需加载 PDF 和页面。
- [x] **M3-10.3** 键盘焦点、输入法回车与 reduced-motion。
- [x] **M3-10.V** 验证：pnpm -C frontend typecheck；pnpm -C frontend build；pnpm -C frontend test:e2e -- edge-states.spec.ts。
- [x] **M3-10.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**390/1500px 可使用；中文输入法选词不误发送；图示、等待与失败均有可读说明；无控制台异常。

<a id="m3-11"></a>
### M3-11：M3 阶段验收

**依赖：**M3-10。
**文件：**`frontend/tests/e2e/support-flow.spec.ts`; `docs/development/records/M3-11.md`; `docs/E2E_VALIDATION.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M3-11.1** 真实后端跑登录→选设备→提问→澄清→引用→追问→刷新恢复→小样导入。
- [x] **M3-11.2** 保存桌面/手机截图和录屏路径。
- [x] **M3-11.V** 验证：先补R1/R2正式回归，再前端/后端阶段验证和既有产物只读复核；原真实付费证据保留，按改动有效性决定是否需补真实验收。
- [x] **M3-11.D** 保存R1/R2修复记录与新的M3-submission-r2、实际摘要及manifest，同步总清单/进度/变更，交总控复审。

**验收：**不是 mock 数据演示；测试证据列明数据/模型/浏览器；后端密钥不进入前端产物或请求。

