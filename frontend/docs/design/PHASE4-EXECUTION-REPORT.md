# 知衡前端 Phase 4 · 布局级补课执行报告

> 执行日期：2026-11-09 · 分支：`feat/ui-phase4-layout`（基线 main @ e4829fd，含 db8481a）
> 任务书：`docs/plans/PHASE4-LAYOUT-PLAN-2026-11-09.md`（已随首个 commit 入库，评审 D4 闭环）
> 目标：修复评审 D1「四页铺开只做了 token 换肤、布局级重构未发生」

## 一、Commit 序列（7 个）

| Commit | 任务 | 实际改动文件 |
|--------|------|--------------|
| 0637ce7 | 任务书入库 | `docs/plans/PHASE4-LAYOUT-PLAN-2026-11-09.md` |
| ccdb74e | P4-0 快修四小项 | `__scenario-shots.spec.ts`（5 用例补真断言+新增 t0-5 回退用例+mock products 映射）、`LoginPage.vue`（D5 钮归位）、`ChatThread.vue`（D6 死代码）、`EvidenceCard.vue`（D7 回退样式） |
| b981922 | P4-1 侧栏六要素 | `SidebarNav.vue`（新，六要素组件化）、`WorkbenchLayout.vue`（接入）、`ConversationList.vue`（keyword 过滤+移除旧 create）、`useCreateConversation.ts`（新 composable） |
| c9ea7c1 | P4-2 证据栏按路由 | `router.ts`（chat meta.evidence）、`WorkbenchLayout.vue`（showEvidence computed） |
| f6c7291 | P4-3 两页卡片化 | `ProductsPage.vue`（Card 族+Server 图标+登记弹层）、`DocumentsPage.vue`（类型图标+发布 Badge+虚线拖放上传卡） |
| 239ef78 | P4-4 评测页整理 | `evaluation/` 5 文件（页头 1.1rem 粗体+表格 12px+行 hover） |
| (本提交) | P4-F 收尾 | `screenshots/final/` ×12 更新、本报告 |

## 二、Checkbox 勾选（对应任务书）

- [x] T0.1 环境与分支（node_modules 非 junction，直接可用）
- [x] T0.2 场景截图补真断言（5 用例各 1 条可见性断言；顺带修复暴露的 mock 缺陷：products 映射缺失导致徽标显示 product_id）
- [x] T0.3 登录主钮归位（删 --accent 覆盖，回 Button primary 语义）
- [x] T0.4 清死代码（无意义三元删除）
- [x] T0.5 空文档名回退（evc-fallback mono 小字 + t0-5 e2e 断言覆盖）
- [x] P4-1 侧栏六要素（品牌区/新建会话主钮/三分组 lucide 导航/知识范围卡/会话搜索+列表/用户卡片含首字母头像与角色 mono 标）
- [x] P4-2 非聊天页收起证据栏（route.meta.evidence；/products 等 4 类页面全宽，chat 不变，移动端抽屉不变）
- [x] P4-3 两页真卡片化（Card 组件消费页面 2 个 ≥ 验收线；CardHeader/CardContent/Badge 全用上；上传改虚线拖放卡）
- [x] P4-4 评测五页最小整理（仅页头与表格密度，不重排）
- [x] P4-F 收尾（grep 双验证/全套验收/12 截图/本报告）

## 三、验收记录

- 每任务后 `pnpm typecheck`（0 错）+ `pnpm test:unit`（62/62）
- 全套：typecheck 0 错 · 单测 62/62 · `pnpm build` 9.06s 通过 · **e2e 58/58**（57 原有 + 1 新增 t0-5）
- 结构化视觉断言（临时用例跑过即删）：侧栏六要素全部可见 + /products 无证据分隔条（全宽）✅
- 双主题截图：`docs/design/screenshots/final/` 6 页 × 2 主题全量更新（新侧栏+全宽页面），带内容断言
- 红线自查：零新增 npm 依赖 ✅ · SSE 三文件零改动 ✅ · 后端零改动 ✅ · 颜色字面量仅 citation-overlay 例外 ✅

## 四、e2e 选择器适配记录（铁律：不删语义）

- `selected-product.spec`：设备卡改 Card 后保留 `h2` 承载型号（语义即卡片标题）+ Card 上保留 `product-card` 类 → 5 用例零修改通过
- `documents.spec`：上传 input 保留 `getByLabel('原件文件')` 关联 → 用例零修改通过

## 五、遗留问题（如实）

1. **上传区双形态**：拖放卡与表单内 file input 并存（单一 input 方案，拖放卡为入口+状态显示）。视觉上表单仍整体展示（含用途/关联设备），未做成分步向导——任务书允许（"保留既有 input 兜底"）。
2. **新建会话钮样式**：按 v6 设计稿 newbtn 实现（--bg 底+accent hover），任务书原文写"--ink 底 --bg 字（发送钮语义）"——以设计稿为准实现（任务书冲突处理规则：视觉基准优先），已在 commit 中注明。
3. **评测页 hover 仅 RunsPage 表格生效**：ReviewPage 等无表格结构，hover 规则无处生效（符合预期）。
4. **P4-1 移动端**：抽屉行为经 layout.spec 验证不回归；六要素在窄屏的密度未单独优化（原任务书未要求）。
