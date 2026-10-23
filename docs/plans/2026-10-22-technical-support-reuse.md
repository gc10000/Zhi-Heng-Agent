# 技术支持工作台：GitHub 源码复用清单

M1实际实施说明（2026-10-23）：保留课程底座来源，Git真实基线0a409294c173601898c847ee962938b155f98d45可追踪；未将课程/批脚本经验描述为全部原创。新领域适配器借鉴已验证分段offset/批次、OpenXML和缓存经验，不导入批脚本全局客户端或其monkeypatch。未增加第三方源码副本/依赖；沿用本机PyMuPDF 1.24.14、Pillow 12.1.1、pymilvus 2.6.10、pymongo 4.16.0、OpenAI SDK 2.28.0、requests 2.32.5，dev pytest 8.4.2。各库原授权保留，课程来源见NOTICE.md；前端复用项仍是后续计划，未声称已集成。实际文件映射及改造行为见records/M1-01至11和阶段manifest，原始模型/课程文件不上传。

日期：2026-10-22。前端已按项目决策统一为 Vue 3 + TypeScript + Vite。关联：[主计划](2026-10-22-technical-support-optimization.md)。

目标是尽可能复用合适的已有实现。区分三种方式：将可定制 UI 源码复制到本项目；通过包安装使用成熟库；借鉴架构并按本项目数据结构实现。复制大型产品的数据库、路由和状态管理通常比使用组件更昂贵。

本轮已读取下列仓库许可证，并实际获取文中标出的源文件或官方适配示例。新增 [Vue 仓库记录](../brainstorming/2026-10-22/support-research/vue3/repositories.json) 与 [Vue 源码记录](../brainstorming/2026-10-22/support-research/vue3/source-files.json)；原研究记录中的 React 方案已被本清单取代。记录包含观察到的 commit、文件 HTTP 状态和 SHA256，见 [reuse-source-files.json](../brainstorming/2026-10-22/support-research/reuse-source-files.json) 与 [reuse-repositories.json](../brainstorming/2026-10-22/support-research/reuse-repositories.json)。404 的猜测路径保留在研究记录中，不算作已核实可复制文件。尚未安装这些依赖、移植代码或做构建兼容性测试。

## 1. 优先级与复用方式

| 项目 | 采用方式 | 复用目标 | 接入成本与约束 |
| --- | --- | --- | --- |
| [shadcn-vue](https://github.com/unovue/shadcn-vue) · MIT | **优先复制 Vue 单文件组件源码**，锁定版本与来源 | 侧栏、对话框、表格、可调整分栏、按钮、表单 | 低到中。同步 Reka UI、VueUse、工具函数、Tailwind 变量、别名和移动端行为 |
| [assistant-ui Vue](https://github.com/assistant-ui/assistant-ui/tree/main/packages/vue) · MIT | **备选**；首版采用自有 Vue 聊天组件 | 消息列表、输入、自动滚动、停止/重试、附件 | 中。观察版本 0.0.5；默认 AI SDK 示例仍需 React，免 React runtime 接法另做构建验证 |
| [VueUse](https://github.com/vueuse/vueuse) · MIT | 包依赖，按需使用 | 响应式断点、滚动、监听与生命周期清理 | 低。运行事件去重仍由业务 composable 明确实现 |
| [PDF.js](https://github.com/mozilla/pdf.js) · Apache-2.0 | 安装 `pdfjs-dist`，封装 Vue 组件 | 分页、文本层、缩放、原件渲染 | 中。worker/CMap/字体按固定版本本地提供；页码/坐标由后端提供 |
| [TanStack Vue Query](https://github.com/TanStack/query) · MIT | 安装 `@tanstack/vue-query` | 文档、任务、会话、反馈的服务状态缓存 | 低。SSE delta 进入 Pinia run store，queryKey 包含用户与知识范围，退出清理缓存 |
| [Naive UI](https://github.com/tusen-ai/naive-ui) · MIT | 备选组件系统，本期不混用 | 后台表格、表单和通知 | 中。若改用需统一整体视觉，当前首选 shadcn-vue |
| [vue-pure-admin](https://github.com/pure-admin/vue-pure-admin) · MIT | 参考工程组织，不复制整站 | 权限菜单、路由、后台布局 | 中到高。完整模板会带入额外依赖与业务，按需参考 |
| [kotaemon](https://github.com/Cinnamon/kotaemon) · Apache-2.0 | 优先读源理解；选择可拆小函数时再提取 | 证据格式化、内联引用、引用预览的规则 | 中到高。实际实现依赖 kotaemon/theflow/Gradio，整文件复制会带入另一套框架；本期默认借鉴并实现轻适配 |
| [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm) · MIT | 参考字段与交互；不复制 Node/Prisma 模型 | 工作空间检索配置、资料选择与会话组织 | 中到高。`workspace.js` 与原后端强耦合，迁入 FastAPI 没有直接运行价值 |
| [Ragas](https://github.com/explodinggradients/ragas) · Apache-2.0 | 独立评测依赖组，不放入线上问答必经路径 | 辅助评价 faithful answer、context precision 等 | 中。版本化评审模型/提示词，费用与人工抽检；检索指标另用标准证据标签计算 |
| [Langfuse](https://github.com/langfuse/langfuse) · 社区部分 MIT、ee 部分另许可 | 可选外部观测服务，使用 SDK；不复制整个平台 | 调用追踪、提示词实验与耗时 | 中到高。全量自部署会引入额外基础设施，16GB 本机先使用内部 run 记录；不作为首版运行依赖 |

## 2. 已核实的具体文件

### shadcn-vue

观察 commit：`de1f76cbb4b319ea26b0dea175dc00c18fce3bd0`，开发分支 `dev`。

- [Sidebar.vue](https://github.com/unovue/shadcn-vue/blob/de1f76cbb4b319ea26b0dea175dc00c18fce3bd0/apps/v4/registry/new-york-v4/ui/sidebar/Sidebar.vue)：Vue 单文件组件、slot、移动端 Sheet 和折叠状态。目标 `frontend/src/components/ui/sidebar/Sidebar.vue`。
- [ResizablePanelGroup.vue](https://github.com/unovue/shadcn-vue/blob/de1f76cbb4b319ea26b0dea175dc00c18fce3bd0/apps/v4/registry/new-york-v4/ui/resizable/ResizablePanelGroup.vue)：使用 `reka-ui` Splitter 和 VueUse `reactiveOmit`，用于问答/证据分栏。
- [Dialog.vue](https://github.com/unovue/shadcn-vue/blob/de1f76cbb4b319ea26b0dea175dc00c18fce3bd0/apps/v4/registry/new-york-v4/ui/dialog/Dialog.vue)：转发 `reka-ui` props/emits，用于型号确认、处理单预览与反馈。

同步完整组件依赖树及工具函数，保留版权说明，修改中文文案；不复制整个演示站点。

### assistant-ui Vue（备选）

观察 commit：`e55314209965381f6f9621418340425ff55a643f`。

- [package.json](https://github.com/assistant-ui/assistant-ui/blob/e55314209965381f6f9621418340425ff55a643f/packages/vue/package.json)：确认 `@assistant-ui/vue` 0.0.5、Vue `^3.5.0` peer 约束及共享 runtime 依赖。
- [README](https://github.com/assistant-ui/assistant-ui/blob/e55314209965381f6f9621418340425ff55a643f/packages/vue/README.md)：`AuiProvider`、`useAuiState` 与 thread/composer primitives；默认 `AISDKChat` 示例依赖 React。免 React 接法要求 `RuntimeAdapter` 与 `@assistant-ui/tap/standalone-shim` 的 Vite alias。
- [index.ts](https://github.com/assistant-ui/assistant-ui/blob/e55314209965381f6f9621418340425ff55a643f/packages/vue/src/index.ts)：确认消息、线程、输入、取消和附件 primitives 的导出。

首版自写 `ChatThread.vue`、`ChatComposer.vue`、`ProductClarification.vue` 与 `useRunStream.ts`，基于 shadcn-vue 复用基础交互。assistant-ui Vue 只在独立小样证明免 React 接法、SSE、重连、取消与历史恢复可行后采用，不改变后端协议迎合模板。

### PDF.js

观察 commit：`d774262d9e01dc83e2c7a52b0cca0d05b250a3cb`。

- [helloworld.html](https://github.com/mozilla/pdf.js/blob/d774262d9e01dc83e2c7a52b0cca0d05b250a3cb/examples/learning/helloworld.html)：确认 workerSrc、getDocument、getPage、viewport 与 HiDPI canvas 的使用流程。

安装 `pdfjs-dist`，封装 `frontend/src/features/evidence/components/PdfViewer.vue`，自写 `CitationOverlay.vue`。将后端归一化 bbox 转为 viewport 坐标，验证旋转、缩放、裁切与跨页；另加文本层。Markdown/Excel 无 bbox 时按章节或单元格溯源。

### kotaemon

观察 commit：`9ad3e4e49aa35b8acddd235918a5d9753c1cfdf9`。

- [simple.py](https://github.com/Cinnamon/kotaemon/blob/9ad3e4e49aa35b8acddd235918a5d9753c1cfdf9/libs/ktem/ktem/reasoning/simple.py)：问答、证据准备、引用与相关性展示。
- [format_context.py](https://github.com/Cinnamon/kotaemon/blob/9ad3e4e49aa35b8acddd235918a5d9753c1cfdf9/libs/kotaemon/kotaemon/indices/qa/format_context.py)：证据格式化和 token 裁切，但其中固定 tokenizer 不能原封不动用于当前模型。
- [citation_qa_inline.py](https://github.com/Cinnamon/kotaemon/blob/9ad3e4e49aa35b8acddd235918a5d9753c1cfdf9/libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py)：内联引用与编号解析。可借鉴引用映射，但我们的 citation 白名单、授权和版本快照必须由后端验证。

### 评测与服务状态

- [Ragas faithfulness](https://github.com/explodinggradients/ragas/blob/298b68274234c060deacab3cf5fb52aa3a20e885/src/ragas/metrics/_faithfulness.py)
- [Ragas context precision](https://github.com/explodinggradients/ragas/blob/298b68274234c060deacab3cf5fb52aa3a20e885/src/ragas/metrics/_context_precision.py)
- [TanStack Vue useQuery](https://github.com/TanStack/query/blob/84332ded752c6796fb3499a47c66f20c22bfbc43/packages/vue-query/src/useQuery.ts)
- [AnythingLLM workspace.js](https://github.com/Mintplex-Labs/anything-llm/blob/0acf0e896721d214df6a8c50282a6d118666a735/server/models/workspace.js)

## 3. 复用策略比较

**推荐：保留当前 Python 核心，按组件复用。** UI 可定制，运行数据仍归本项目；学习与维护范围可控，能够清楚说明独立贡献。

备选一：大规模 fork AnythingLLM 后接 FastAPI。上线界面快，但需适配 Node 服务、工作空间数据库、认证与消息协议，易出现双后端/双知识库。本项目已有可运行链路，收益不明显。

备选二：将 RAG 迁入 RAGFlow/Dify 平台再做薄客户端。适合只需快速交付应用，但会替换当前底座并引入较多平台结构，也不利于围绕现有 LangGraph 工作讲清楚改进。

首个兼容性小样采用 Vue 3.5、Vite、shadcn-vue、Pinia、Vue Query、PDF.js 和自有 SSE：展示一个真实流式问题、一条引用、历史恢复、停止/取消和 PDF 定位。通过后冻结 Vue、Tailwind、Reka UI、组件和库版本；assistant-ui Vue 另做可选验证。

Vue Query 缓存服务数据，Pinia 保存按 run ID 隔离的运行状态；不重复存储同一字段。浏览器 abort 只中断读取，取消还需请求后端。Vue Router 负责页面导航，路由守卫不替代服务端授权。

## 4. 来源追踪与维护

执行阶段维护 `THIRD_PARTY_NOTICES.md` 和 `docs/reuse/manifest.json`：仓库、固定 commit/tag、原路径、目标路径、许可证、修改摘要、上游链接、依赖版本和本地校验值。复制文件保留所需版权说明；Apache 组件若带 NOTICE，同时核对并保留相应通知。

业务代码采用中文说明；原项目版权与许可证原文保留原语言。上游更新通过人工差异审查和组件回归，不自动覆盖修改后的 UI。研究快照不是最终 vendored 代码，公开仓库只纳入实际使用内容及必要通知，不把整个研究下载目录当作产品源码提交。

## M0 实施补记（2026-10-23）

本阶段未复制上游产品源码、未创建 Vue/React 组件，未将研究快照纳入应用。仅新增 pytest 8.4.2 开发测试依赖及 iniconfig/pluggy/pygments，固定版本见 pyproject/uv.lock；pytest 上游 https://github.com/pytest-dev/pytest，许可证 MIT，经包管理使用而非 vendoring。原环境 torch/CUDA/模型版本不变；安装差异见 M0-02 证据。本阶段不会把规划中的第三方 notices/源码复用清单当作已交付能力。后续实际复制时仍按上文追踪固定来源和许可证。


## M2-09/10实际队列复用

Celery固定5.5.3（BSD-3-Clause，上游https://github.com/celery/celery），redis-py固定6.4.0（MIT，上游https://github.com/redis/redis-py）；通过依赖引用，无源码vendoring。文件映射app/infrastructure/queue/celery_app.py、app/infrastructure/rate_limits.py、pyproject.toml/uv.lock，独立Linux镜像deploy/worker。Redis服务镜像7.4.6-alpine，Redis 7.4为RSALv2/SSPLv1双许可（https://github.com/redis/redis），不是历史BSD；仅本机开发部署定义，后续公开分发/商用部署需复核适用条款。独立requirements不升级宿主PyTorch/CUDA。


## M2-11实际旧能力复用

复用现有课程node_answer_output.step_2_construct_prompt/step_3_generate_response及BGE模型工具，新增client注入保持默认旧调用兼容；ContextVar出口映射持久事件，旧整图保留。没有复制新上游源码或新增依赖，不将课程提示词/模型包装描述为原创。实际新授权检索与持久适配见ADR-031、records/M2-11.md。
