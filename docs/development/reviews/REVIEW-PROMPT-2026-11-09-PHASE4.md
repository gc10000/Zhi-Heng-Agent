# 评审任务：知衡（Zhi-Heng）前端 Phase 4 布局级补课的独立评审

## 你的角色

你是一位资深前端架构与代码评审专家，独立、挑剔、以证据为准。你的评审结论将直接决定这批改动是否合入主干。不要客气，发现问题就直说；同时不要为了显得严格而编造问题——每条意见必须落到具体代码行或具体行为。

**背景**：你上一轮评审（2026-11-08）对 v6 改版给出「有条件通过」，并指出 D1 重要缺陷「T3.3 四页铺开只做了 token 换肤，布局级重构未发生」。本批改动（Phase 4）即针对你那次评审的 D1/D2/D4/D5/D6/D7 六项处置。**请以同一标准验收你上次提出的问题是否真正修复。**

## 评审对象

仓库：https://github.com/gc10000/Zhi-Heng-Agent
改动范围：`e4829fd..470fe16`（10 个提交，`feat/ui-phase4-layout` 分支，未合入 main）
改动性质：纯前端布局级重构（侧栏六要素/证据栏按路由/两页卡片化/评测页整理）+ 上轮评审快修四项。**SSE 三文件与后端 Python 声称零改动（需你验证）；e2e 声称零语义删除（需你验证）**

## 第一步：必读材料（按序）

1. `docs/development/reviews/CHANGESET-REVIEW-BRIEF-2026-11-09-PHASE4.md` —— 改动说明书（清单/验收/争议点索引）
2. `docs/plans/PHASE4-LAYOUT-PLAN-2026-11-09.md` —— 任务书（验收标准出处，23 checkbox 声称全勾）
3. `frontend/docs/design/PHASE4-EXECUTION-REPORT.md` —— 执行报告（含自审修复记录 a8454dd）
4. `docs/design/ui-final-v6.html` —— 视觉基准（侧栏六要素/catalog 卡片语言的对照标准）

## 第二步：验证红线（先做，任何一条不成立即高优先级缺陷）

```
git clone https://github.com/gc10000/Zhi-Heng-Agent && cd Zhi-Heng-Agent
git checkout 470fe16

# 红线1：零新增 npm 依赖
git diff e4829fd..470fe16 -- frontend/package.json   # 期望空

# 红线2：SSE 状态机零改动
git diff e4829fd..470fe16 --name-only | grep -E "useRunStream|run-events|stores/run"   # 期望空

# 红线3：后端零改动
git diff e4829fd..470fe16 --name-only | grep "^app/"   # 期望空

# 红线4：颜色纪律（唯一允许例外 PDF citation-overlay）
grep -rn '#[0-9a-fA-F]\{3,8\}' frontend/src --include="*.vue" --include="*.css" | grep -v tokens.css | grep -v citation-overlay   # 期望空

# 红线5（本期新增）：e2e 语义不得删除
git diff e4829fd..470fe16 -- frontend/tests/e2e/ | grep "^-" | grep -E "getBy|expect|locator"   # 期望空（改动只允许增量）
```

## 第三步：复跑验收（全绿才算通过，失败即缺陷）

```
cd frontend && pnpm install --frozen-lockfile
pnpm typecheck        # 期望 0 错误
pnpm test:unit        # 期望 62/62
pnpm build            # 期望成功
npx playwright install chromium && pnpm test:e2e   # 期望 58/58
```

## 第四步：逐项验收上轮缺陷处置（你的上次意见，请复核）

| 上轮编号 | 处置声明 | 你的复核点 |
|----------|----------|-----------|
| D1 布局级重构未发生 | P4-1/P4-2/P4-3 三任务落地 | 侧栏六要素是否真实存在（对照 v6 设计稿）；lucide 消费是否从 2 个扩到 11 个；Card 组件消费页面是否 ≥2；非聊天页证据栏是否真的收起 |
| D2 场景截图无断言 | 5 用例各补 1 条可见性断言 | 断言是否真实有效（非空转）；顺带修的 mock products 映射是否正确 |
| D4 任务书未入库 | 0637ce7 首个 commit 入库 | 核实 |
| D5 登录主钮 | 删覆盖回 primary 语义 | 视觉是否归位（--ink 底） |
| D6 死代码 | 三元删除 | 核实 |
| D7 空文档名回退 | document_id mono 小字 + t0-5 用例 | 回退逻辑与用例质量 |

## 第五步：重点评审 8 个争议点（说明书第四节，逐项给出独立判断）

1. **新建钮样式冲突**（任务书写 `--ink` 底 vs 实现按 v6 设计稿 `--bg` 底）：视觉基准优先规则是否适用？你的取舍？
2. **route.meta.evidence 白名单语义**：未来新页面默认无证据栏，遗漏需显式声明。白/黑名单哪个更符合演化方向？
3. **会话搜索只过滤已加载页**（ConversationList keyword 作用于 vue-query 已取回页）：语义边界是否可接受？是否需要「加载更多」提示？
4. **上传区双形态**（拖放卡+表单并存）：体验一致性？
5. **ChatPage 双份逻辑自审修复**（a8454dd）：修复是否完整？两消费方（SidebarNav/ChatPage）错误展示是否都接入？
6. **isActive('/chat') 前缀特判**（SidebarNav.vue:29）：路由匹配健壮性？
7. **移动端六要素密度**：窄屏纵向滚动是否可接受？
8. **P4-4 hover 仅 RunsPage 生效**：是否符合「最小整理」边界？

## 第六步：抽查代码质量（自主选择）

建议至少看：SidebarNav.vue（六要素实现与 token 纪律）、useCreateConversation.ts（composable 设计与错误处理）、WorkbenchLayout.vue 的 showEvidence computed（路由驱动布局的接线）、ProductsPage.vue（Card 消费与 e2e 兼容类保留）、__scenario-shots.spec.ts（断言补强质量）。

## 输出格式（必须遵循）

```
## 评审结论：通过 / 有条件通过 / 需返工
（一句话理由）

## 红线验证
（5 条逐项：成立/不成立 + 证据）

## 验收复跑
（命令 + 实际结果 + 与声称的差异）

## 上轮缺陷处置复核（D1/D2/D4/D5/D6/D7 逐项）
（已修复 / 部分修复 / 未修复 + 证据）

## 争议点判断
（8 项逐项：同意执行者的处理 / 不同意 + 理由 + 建议改法）

## 发现的缺陷
（分级：阻断 / 重要 / 次要；每条给 文件:行号 + 复现方式 + 建议修复）

## 值得肯定的设计
（如有，简列）

## 给后续开发的建议
（优先级排序，最多 5 条）
```

## 评审纪律

- 所有断言必须基于你实际运行的命令或阅读的代码，注明文件与行号
- 你上轮提出的 D1 是本批改动的核心命题——侧栏/证据栏/卡片化三件事是否让布局级重构「真实发生」，请给出明确判断而非敷衍
- 说明书第四节的 8 个争议点是执行者自曝的风险，你的价值在于独立判断而非复述
- 如果某项你无法验证，明确标注「未验证」而不是猜测
- 不要建议大规模重写——改动已过全部自动化验收，评审目标是发现自动化覆盖不到的问题
