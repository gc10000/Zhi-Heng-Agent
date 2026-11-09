# 知衡（Zhi-Heng）Phase 4 · 布局级补课改动评审说明书

> 评审范围：`e4829fd..470fe16`（基点 = main HEAD 评审 Prompt 入库；当前 = feat/ui-phase4-layout 分支头，**未合入 main**）
> 改动构成：**10 个提交**（1 任务书入库 + 6 任务执行 + 1 场景截图刷新 + 1 自审修复 + 1 报告补记），源码改动全部在 `frontend/`，另任务书勾选与报告若干
> 源码规模：`frontend/src` 12 文件 +`SidebarNav.vue`/`useCreateConversation.ts` 两个新文件；零新增 npm 依赖；**SSE 三文件与后端 Python 零改动**
> 上一轮评审：`CODE-REVIEW-V6-2026-11-08.md`（外部产物，不在库内）结论「有条件通过」，本批改动处置其 D1/D2/D4/D5/D6/D7 六项

---

## 一、改动背景（为什么改）

上一轮评审确认 v6 改版「有条件通过」，但发现 **D1（重要缺陷）：T3.3 四页铺开只做了 token 换肤，布局级重构未发生**——侧栏 5 个裸文本 RouterLink、lucide 全套仅用 2 图标、Card 组件族 0 页面消费、证据面板常驻所有页面致目录页半屏空置。这是用户「粗糙、没法看」观感的直接根源。

Phase 4 目标：把布局级重构补上，让 v6 设计稿（`docs/design/ui-final-v6.html`）在全部页面真实落地。任务书 `docs/plans/PHASE4-LAYOUT-PLAN-2026-11-09.md` 随首个 commit 入库（处置 D4）。

## 二、改动清单（按提交粒度）

| Commit | 任务 | 内容 |
|--------|------|------|
| 0637ce7 | 任务书入库 | 处置 D4：施工计划自包含入库 |
| ccdb74e | **P4-0 快修四小项** | D2：`__scenario-shots.spec.ts` 5 用例各补 1 条可见性断言（screenshot 前不再空转）+ 新增 t0-5 空文档名回退用例 + 修复暴露的 mock 缺陷（products 映射缺失致徽标显示 product_id）；D5：登录钮删 `--accent` 覆盖回 Button primary 语义；D6：ChatThread 无意义三元删除；D7：EvidenceCard 空名回退显示 document_id |
| b981922 | **P4-1 侧栏六要素**（D1 核心） | 新建 `SidebarNav.vue`：①品牌区 ②新建会话主钮（lucide Plus）③三分组导航（工作台/知识库/质量，5 项 lucide 图标+激活指示条）④kb 选择卡 ⑤会话搜索框（前端标题过滤）+列表 ⑥用户卡（首两字母头像+角色 mono 标+LogOut）。新建会话逻辑提取 `useCreateConversation.ts` composable |
| c9ea7c1 | **P4-2 证据栏按路由收起**（D1 核心） | `router.ts` chat 路由加 `meta:{evidence:true}`；WorkbenchLayout `showEvidence = route.meta.evidence===true && !mobile`。目录/资料/支持/评测页主区全宽，chat 证据栏不变，移动端抽屉不变 |
| f6c7291 | **P4-3 两页真卡片化**（D1 核心） | ProductsPage：Card/CardHeader 消费+Server 图标+登记主钮+Badge 型号歧义；**保留 `h2.pc-model` 与 `.product-card` 类名**兼容 5 条既有 e2e（零用例修改）。DocumentsPage：类型图标（FileText/FileSpreadsheet/FileCode）+发布 Badge+虚线拖放上传卡；重构为**单一 file input**（`getByLabel('原件文件')` 语义保留） |
| 239ef78 | P4-4 评测页最小整理 | 五页头统一 1.1rem/700 + 表格 padding 12px + 行 hover；不重排（评审明确边界） |
| 1958a6f | P4-F 收尾 | grep 双验证清零 / 全套验收 / 双主题 12 截图更新 / 执行报告 / 任务书 23 checkbox 全勾 |
| 55b5c13 | 场景截图刷新 | 5 张 after 截图随新侧栏布局重跑（e2e 产物） |
| a8454dd | **自审修复** | 生成评审材料时自审发现：ChatPage 空态按钮（T2.1 遗留）未迁移 composable 形成双份逻辑；侧栏新建失败静默；空态错误在 `v-else` 分支不可见。三处一并修复 |
| 470fe16 | 报告补记 | 执行报告补 a8454dd 记录 |

## 三、验收证据（评审可复核）

| 验收项 | 结果 | 复核命令 |
|--------|------|----------|
| 类型检查 | 0 错误 | `cd frontend && pnpm typecheck` |
| 单元测试 | 62/62 | `pnpm test:unit` |
| 端到端 | **58/58**（57 + 新增 t0-5） | `pnpm test:e2e` |
| 生产构建 | 通过（8.6s） | `pnpm build` |
| 零新增依赖 | package.json diff 为空 | `git diff e4829fd..470fe16 -- frontend/package.json` |
| SSE 零改动 | 三文件不在 diff | `git diff e4829fd..470fe16 --name-only \| grep -E "useRunStream\|run-events\|stores/run"` |
| 后端零改动 | app/ 不在 diff | `git diff e4829fd..470fe16 --name-only \| grep "^app/"` |
| 颜色纪律 | 字面量 0（例外 PDF citation-overlay） | `grep -rn '#[0-9a-fA-F]\{3,8\}' frontend/src --include="*.vue" --include="*.css" \| grep -v tokens.css \| grep -v citation-overlay` |
| **e2e 零语义删除** | diff 中无删除断言行（选择器适配仅增量） | `git diff e4829fd..470fe16 -- frontend/tests/e2e/ \| grep "^-" \| grep -E "getBy\|expect\|locator"` → 空 |
| 任务书勾选 | 23/23 | `grep -c "\[x\]" docs/plans/PHASE4-LAYOUT-PLAN-2026-11-09.md` |

## 四、建议重点评审的争议点/风险（执行者自曝）

1. **新建钮样式与任务书原文冲突**：任务书 P4-1② 写「`--ink` 底 `--bg` 字（发送钮语义）」，实现按 v6 设计稿 `newbtn` 样式（`--bg` 底+`--line2` 边+hover accent）。任务书冲突处理规则「视觉基准优先」，已在 commit 注明。请独立判断取舍。

2. **route.meta.evidence 白名单语义**：evidence 栏采用 chat 路由白名单（`meta.evidence === true` 才显示）而非黑名单。语义影响：未来新增需要证据栏的页面必须显式加 meta，遗漏即不显示。评审可判断白/黑名单哪个更符合该应用演化方向。

3. **会话搜索只过滤已加载页**：`ConversationList` 的 keyword 过滤作用于 `query.data.pages.flatMap`（vue-query 无限查询已取回的页）。会话多于首页时，未加载页的会话搜不到。前端过滤零成本但语义是「在已加载中搜索」而非全库搜索。

4. **上传区双形态**：拖放卡与表单内 file input 并存（单一 input 方案，拖放卡为入口+状态显示）。视觉上表单仍整体展示，未做分步向导——任务书允许（保留 input 兜底）。

5. **ChatPage 双份逻辑（已修，a8454dd）**：P4-1 提取 composable 时 ChatPage 空态按钮未迁移，生成评审材料自审时发现并修复。此为执行疏漏的如实记录，评审应复核修复完整性（SidebarNav 与 ChatPage 两消费方错误展示均已接入）。

6. **isActive('/chat') 前缀特判**：`SidebarNav.vue:29` 对 /chat 用「精确或前缀」、其他路由用「前缀」匹配。若未来出现 /chat-xxx 类路由会误判（当前路由表无此形态）。

7. **移动端六要素密度**：抽屉行为经 layout.spec 验证不回归；六要素在窄屏的纵向密度未单独优化（原任务书未要求，侧栏内容增多后小屏需滚动属预期）。

8. **P4-4 hover 仅 RunsPage 生效**：ReviewPage 等无表格结构，hover 规则无处生效（符合预期，但执行报告已列）。

## 五、评审材料索引

| 材料 | 位置 |
|------|------|
| 任务书（验收标准出处） | `docs/plans/PHASE4-LAYOUT-PLAN-2026-11-09.md` |
| Phase 4 执行报告 | `frontend/docs/design/PHASE4-EXECUTION-REPORT.md` |
| v6 设计稿（视觉基准） | `docs/design/ui-final-v6.html` |
| 上一轮评审说明书/Prompt | `docs/development/reviews/CHANGESET-REVIEW-BRIEF-2026-11-08.md`、`REVIEW-PROMPT-2026-11-08.md` |
| 双主题截图（Phase 4 后） | `frontend/docs/design/screenshots/final/` ×12 |
| 场景截图（含 before/after） | `frontend/docs/design/screenshots/scenario/` |
| 全部源码改动 | `git diff e4829fd..470fe16 -- frontend/src/`（12 文件） |

## 六、环境事实（评审者可能需要知道的）

- **分支未合入 main**：`feat/ui-phase4-layout` 领先 main 127 commits（历史 M6/M7/v6/CI 已在 main 的部分除外），本次评审结论将决定合并方式。
- 上一轮评审报告 `CODE-REVIEW-V6-2026-11-08.md` 为外部产物未入库；其缺陷编号（D1-D7）在任务书中有完整转述，可据任务书第一节表格对照。
- e2e 58 条在本地 msedge 与 CI chromium（GitHub Actions ubuntu-24.04）双环境均绿。
