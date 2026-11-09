# 知衡前端 Phase 4 · 布局级补课任务书（v6 保真度修复）

> **文档性质**：交给执行 Agent 的独立施工计划，自包含全部上下文。**本文件须随首个 commit 提交入库**（修复评审 D4：任务书未随库）。
> **来源**：独立评审报告 `docs/development/reviews/CODE-REVIEW-V6-2026-11-08.md` 第五节 + 用户产品所有者反馈（"系统粗糙、前端页面没法看、布局设计之初就有问题"）。
> **创建**：2026-11-09 · 基线：main @ `db8481a`（v6 双主题改版已合入）。

---

## 一、背景：为什么有 Phase 4

v6 改版（34 commits）已完成：双主题 token 体系、Chat 页气泡/步骤卡/引用角标/SCOPE 胶囊、五项 P0 体验修复、基础组件库（Button/Badge/Card×5/Input）、首条 CI。评审结论**有条件通过**。

但评审发现 **D1（重要缺陷）：T3.3 "四页铺开"实际只做了 token 换肤，布局级重构未发生**——这就是用户"粗糙、没法看"观感的直接根源：

| 用户感受 | 代码证据（评审实测） |
|----------|---------------------|
| "根本没法看" | 侧栏仍是 5 个裸文本 RouterLink（无图标/无分组/无新建钮/无搜索/无用户卡）；lucide 全套仅用 2 个图标（ThemeToggle 的 Sun/Moon）；Card 组件 7 个文件创建后 **0 个页面消费**；Products/Documents 仍整页沿用旧 `catalog-page` 结构 |
| "毫无用户体验" | 导航无可读性层次；页面间信息密度跳跃 |
| "布局先天有问题" | 证据面板常驻**所有**页面——/products /documents /evaluations 右半屏永远空置或塞不相关内容 |

Phase 4 目标：把这四件事补上，让 v6 设计稿（`docs/design/ui-final-v6.html`）的布局在全部页面真实落地。

## 二、环境与红线（与 v6 任务书一致，重申）

- **仓库**：GitHub `gc10000/Zhi-Heng-Agent`，从最新 `origin/main` 切分支 `feat/ui-phase4-layout`
- **零新增 npm 依赖**（lucide-vue-next / reka-ui / Tailwind 4 全部已在）
- **不动 SSE 状态机**（useRunStream.ts / run-events.ts / stores/run.ts 只读）
- **组件样式禁止颜色字面量**，只引用 `src/styles/tokens.css` 语义变量（唯一例外 PDF 纸面 citation-overlay）
- **后端零改动**（本 Phase 纯前端；评审建议 D3 的 behavior 字段属后续后端任务，不在本期）
- 每任务：勾选 checkbox → commit（`feat(ui): P4-x 描述`）→ 跑验收
- **注意（评审遗留#1）**：若 `frontend/node_modules` 是指向其他目录的 junction，先删除再 `pnpm install --frozen-lockfile` 重装

## 三、任务清单

### P4-0 · 环境准备 + 快修四小项（半天）

- [x] **T0.1 环境与分支**：`git fetch origin && git switch main && git pull`（应到 db8481a+）→ `git switch -c feat/ui-phase4-layout` → 检查 node_modules junction 问题 → 本任务书随首 commit 入库（`docs/plans/PHASE4-LAYOUT-PLAN-2026-11-09.md`）。
- [x] **T0.2 [评审 D2] 场景截图测试补真断言**：`tests/e2e/__scenario-shots.spec.ts` 的 5 个测试在 screenshot 前各加 1 条可见性断言：
  - t1-1 错误卡：`await expect(page.getByText('型号候选过多')).toBeVisible()`
  - t1-2 澄清：`await expect(page.getByRole('button', { name: /以上都不是/ })).toBeVisible()`
  - t1-3-t1-5：`await expect(page.getByText('适用型号：NX308-S')).toBeVisible()` + `await expect(page.getByRole('button', { name: /反馈/ }).first()).toBeVisible()`
  - t1-4 证据卡：`await expect(page.getByText('NX300 安装手册.pdf')).toBeVisible()`
  - t2-4 依据不足：`await expect(page.getByText('依据不足')).toBeVisible()`
  验收：`pnpm test:e2e` 57/57 全绿（断言加入后不再空转）。
- [x] **T0.3 [评审 D5] 登录主钮归位**：`LoginPage.vue` 删除 `.login-submit` 对 `--accent` 底的覆盖，改用 Button 组件 primary 语义（--ink 底），保持全宽。
- [x] **T0.4 [评审 D6] 清死代码**：`ChatThread.vue:38` 删除无意义三元 `m.run_id&&messages.length?undefined:undefined`，query 只留 `{ run: m.run_id }`。
- [x] **T0.5 [评审 D7] 空文档名回退**：`EvidenceCard.vue` 当 `nameOf(id)` 返回空串时显示 `document_id`（mono 小字），并补一条单测或场景断言覆盖该回退。

### P4-1 · 侧栏六要素重建（最高优先，1 天）

文件：`app/WorkbenchLayout.vue`（+ 可能新建 `components/ui/SidebarNav.vue` 承载导航块）。对照 `docs/design/ui-final-v6.html` 侧栏区块逐项落地：

- [x] ① 品牌区：保留 BrandMark + 知衡 + 副标（已有，微调间距对齐 v6）
- [x] ② **「新建会话」主按钮**：全宽，lucide `Plus` 图标 + 文字；样式：`--ink` 底 `--bg` 字（v6 发送钮同语义）；点击复用 ChatPage 的 createConversation 逻辑（提取到 composable 或经 stores/ui 暴露，避免复制粘贴）；非 /chat 路由点击后跳 `/chat/{新id}`
- [x] ③ **分组导航**（v6 六要素核心）：
  ```
  工作台 WORKSPACE
    技术问答   MessageSquare
    支持流程   ClipboardCheck
  知识库 KNOWLEDGE
    设备目录   Server
    资料管理   FolderOpen
  质量 QUALITY
    评测工作台 FlaskConical
  ```
  每项 = lucide 图标（15px，`--ink3`，激活态 `--accent`）+ 文字标签；激活项左侧 2.5px `--accent` 指示条 + `accent 10%` 底（用 color-mix）；分组标题 mono 8.5px 字距 0.15em
- [x] ④ 知识范围选择器：保留现有 select，容器改卡片式（1px `--line` 边 + 圆角 + label 小字），样式对齐 v6 kb 卡
- [x] ⑤ 会话列表：头部加搜索框（lucide `Search` 12px 图标 + 输入，按标题前端过滤 ConversationList）；列表行保留现有 hover/active 样式
- [x] ⑥ 用户卡片：`--line` 顶边分隔；头像圈（26px，`accent-soft` 底 accent 字，取用户名首两字母大写）+ 用户名 + 角色 mono 小标（MAINTAINER/VIEWER，从 auth.user 取）+ `LogOut` 图标退出钮
- 验收：亮暗双主题截图对照 v6 侧栏六区块；`pnpm test:e2e` 不回归（既有侧栏断言若因结构变化失败，允许同步修正选择器但不得删除用例语义）；移动端抽屉行为不回归。

### P4-2 · 非聊天页收起常驻证据栏（半天，消先天布局缺陷）

文件：`app/router.ts` + `app/WorkbenchLayout.vue`

- [x] router.ts 给 chat 路由加 `meta: { evidence: true }`
- [x] WorkbenchLayout：`const showEvidence = computed(() => route.meta.evidence === true && !mobile)`；桌面右栏模板条件从 `v-if="!mobile"` 改 `v-if="showEvidence"`；主 SplitterPanel 在无右栏时占满（reka-ui Splitter 单面板自动 100%，验证即可）
- [x] 移动端证据抽屉行为不变（按 ui.evidence 开关）
- 验收：/products /documents /cases /evaluations 主区全宽无空右栏（截图×4）；/chat 证据栏宽度/拖拽/引用点击不回归（e2e citation 相关用例全绿）。

### P4-3 · Products / Documents 真·卡片化（1 天）

- [x] **ProductsPage**：弃用整页 `catalog-page` 旧结构中的产品区块，设备卡改用 Card 组件族（Header/Content）：
  - 卡头：lucide `Server` 图标 + 型号名（粗体）+ 系列（`--ink3` 小字）
  - 卡体：适用资料数、当前修订（mono 小字）、资料目的标签
  - 型号歧义 → `Badge` variant="warning"「型号歧义」
  - 页头：标题 + eyebrow + **「登记设备」主钮**（Button primary + `Plus`）
  - 保留既有登记表单/搜索逻辑，仅改呈现
- [x] **DocumentsPage**：资料行卡片化：
  - 类型图标：PDF=`FileText` / Excel=`FileSpreadsheet` / Markdown=`FileCode`（按 active_revision 或 metadata 判型，未知用 `File`）
  - 名称 + 修订徽标（`Badge`：已发布=success）+ 状态 mono 小字
  - 上传区改虚线边框拖放卡（`--line2` 虚线 + `Upload` 图标 + 文案），保留既有 input 兜底
  - 与既有 ImportJobsFold（任务折叠区）整合排布，不破坏其逻辑
- 验收：Card 组件消费页面数 ≥ 2（grep `ui/Card`）；两页亮暗截图对照 v6 catalog 语言；e2e documents/products 相关用例全绿（选择器同步修正允许）。

### P4-4 · 评测页最小整理（半天，内部工具不重排）

- [ ] 五页统一页头：标题（1.1rem 粗体）+ eyebrow（mono 小字大写）+ 右侧操作区留白
- [ ] 表格密度统一：单元格 padding 9px→12px，行 hover `--panel` 底
- [ ] 不做其他投入（角色隐藏后普通用户不可见；此为评审明确边界）
- 验收：五页页头一致截图；e2e 评测用例全绿。

### P4-F · 收尾（半天）

- [ ] 全库 grep 验证：颜色字面量仅 tokens.css + citation-overlay；`catalog-page` 旧类在已重构页清零
- [ ] 全套验收：`pnpm typecheck && pnpm test:unit && pnpm build && pnpm test:e2e`（57/57，含 T0.2 补强的断言）
- [ ] 双主题全站截图更新至 `docs/design/screenshots/final/`（6 页 × 2 主题，覆盖新侧栏与全宽页面）
- [ ] 执行报告：`frontend/docs/design/PHASE4-EXECUTION-REPORT.md`（checkbox 对照 + 实际改动文件 + 遗留清单，格式沿用 v6 报告）

## 四、工期与顺序

P4-0（0.5d）→ P4-1（1d）→ P4-2（0.5d）→ P4-3（1d）→ P4-4（0.5d）→ P4-F（0.5d），合计约 4 个工作日。P4-1 与 P4-2 完成即可显著改善"没法看"观感（侧栏+全宽），P4-3/4 为完整度收尾。

## 五、参考文件（只读）

| 文件 | 用途 |
|------|------|
| `docs/design/ui-final-v6.html` | 侧栏六要素/证据栏/catalog 卡片语言的视觉基准 |
| `docs/development/reviews/CODE-REVIEW-V6-2026-11-08.md` | 本任务书的缺陷出处与判断依据 |
| `frontend/docs/design/UI-REDESIGN-V6-EXECUTION-REPORT.md` | v6 执行情况与遗留（node_modules junction 等） |
| `frontend/src/components/ui/__stories.md` | 已有基础组件 props 表 |
