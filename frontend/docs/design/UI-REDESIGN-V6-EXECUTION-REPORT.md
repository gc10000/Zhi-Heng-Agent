# 知衡前端改版 v6 · 执行报告（feat/ui-redesign-v6）

> 执行日期：2026-11-07/08 · 分支基点：codex/m6-source-bound-comparison
> 任务书：主仓库 `docs/plans/FRONTEND-REDESIGN-PLAN-2026-11-07.md`（主仓库 docs 只读，故 checkbox 勾选记录在本文件）

## 一、Commit 序列（20 个，全在 feat/ui-redesign-v6）

| Commit | 任务 | 实际改动文件 |
|--------|------|--------------|
| b6fec57 | T0.1 token 体系 | `styles/tokens.css`(新)、`main.ts` |
| f697034 | T0.2 主题 composable | `lib/theme.ts`(新)、`App.vue` |
| ac4d27c | T0.3 ThemeToggle | `ui/ThemeToggle.vue`(新)、`app/WorkbenchLayout.vue`、`style.css` |
| 32b5d4f | T0.4 BrandMark | `ui/BrandMark.vue`(新)、`auth/LoginPage.vue` |
| b0e67f8 | T1.1 错误人话化 | `lib/error-codes.ts`(新)、`chat/components/RunProgress.vue`、`ChatThread.vue`、`ChatPage.vue` |
| 41f91bc | T1.2 澄清出口 | `chat/queries/product-selection.ts`、`chat/components/ProductClarification.vue` |
| 1cce813 | T1.3 设备同步 | `style.css`（watch 逻辑随 T1.1 提交） |
| 893fae8 | T1.4 文档名 | `evidence/queries/document-names.ts`(新)、`evidence/components/EvidenceCard.vue`、`EvidenceDrawer.vue` |
| d395bd9 | T1.5 直达反馈 | （随 T1.1 文件批提交，空标记 commit） |
| e86e8e9 | T2.1 空态行动化 | `ChatPage.vue` |
| eeedf53 | T2.2 kb 显示名 | `stores/auth.ts`、`WorkbenchLayout.vue` |
| 5329524 | T2.3 命名统一 | `cases/CasesPage.vue`、`tests/e2e/support-case.spec.ts` |
| dca687d | T2.4 依据不足徽标 | `RunProgress.vue` |
| c2215a6 | T2.5 任务折叠区 | `documents/components/ImportJobsFold.vue`(新)、`DocumentsPage.vue`、`stores/ui.ts` |
| b0fc609 | T2.6 记录列表增强 | （随 T2.3 提交，空标记 commit） |
| 26e342d | T3.1 基础组件库 | `ui/Button/Badge/Card/CardHeader/CardContent/CardFooter/Input.vue`(新×7)、`ui/dialog/Modal.vue`、`ui/__stories.md` |
| 928a5f6 | T3.2 ChatPage 对齐 v6 | `style.css`、`ChatPage.vue`、`EvidenceCard.vue` |
| 70581f6 | T3.3 四页铺开 | `ProductsPage.vue`、`LoginPage.vue`、`CasesPage.vue`、`OperationChecklist.vue` |
| 521ff07 | T3.4 清理收尾 | `App.vue`、`evaluation/`×5、`tests/e2e/support-case.spec.ts` |
| a02ddcc | 双主题截图 | `docs/design/screenshots/final/`×12 |
| ed13d7a | 执行报告 | `docs/design/UI-REDESIGN-V6-EXECUTION-REPORT.md` |
| 9424420 | 改版前基线截图 | `docs/design/screenshots/before/`×6 |
| 768ce72 | 场景级前后对比截图 | `docs/design/screenshots/scenario/`×10（T1.1/T1.2/T1.4/T1.3+T1.5/T2.4 × before/after） |
| 27173f0 | 场景截图 e2e | `tests/e2e/__scenario-shots.spec.ts`（五场景 mock，常规套件可跑，SHOT_TAG 区分前后） |

## 二、Checkbox 勾选（对应任务书）

- [x] T0.1 建立 token 体系（tokens.css 两组变量，main.ts 于 style.css 前 import）
- [x] T0.2 主题切换 composable（localStorage('zhiheng-theme') + prefers-color-scheme + data-theme）
- [x] T0.3 ThemeToggle 分段开关接入顶栏（保留「依据可查 · 适用范围明确」在其左侧）
- [x] T0.4 BrandMark 水平仪 Logo（气泡 fill=var(--accent) 随主题；侧栏+登录页两处）
- [x] T1.1 错误人话化（error-codes.ts 五类映射 + danger 错误卡 + 复制错误码 + 主/次钮）
- [x] T1.2 澄清「以上都不是」（候选卡片网格 + 虚线出口 + 全目录搜索 + 设备目录链接）
- [x] T1.3 设备选择随会话同步（会话绑定恢复 + 消息设备徽标 + SCOPE 胶囊）
- [x] T1.4 引用显示文档名（document-names.ts 分页拉全量映射 + v6 证据卡头 + 抽屉空态文案）
- [x] T1.5 聊天页直达反馈（有帮助/反馈/处理草稿操作行 + SOURCES 统计 + 内联 FeedbackForm → POST /feedback）
- [x] T2.1 聊天空态行动化（新建会话主钮，两步内发起第一问）
- [x] T2.2 kb 显示名（auth.labelOf：映射缺失取 ID 首段大写）
- [x] T2.3 命名统一「支持流程」（侧栏/标题/入口链/e2e；grep 残留清零）
- [x] T2.4 依据不足徽标（INSUFFICIENT_ANSWER 文本匹配 + warn 横幅 + /documents 链接）
- [x] T2.5 导入任务折叠区（最近任务轮询 1.5s + 失败重试 + 状态徽标；后端无列表端点，任务 ID 从上传结果+URL 收集）
- [x] T2.6 处理记录列表增强（设备名/相对时间/草稿-已确认徽标/回会话链接）
- [x] T3.1 基础组件库（cva+语义变量零依赖手写 + __stories.md props 表）
- [x] T3.2 ChatPage 对齐 v6（用户气泡 14/14/4/14 右对齐、AI 纯文本、ol 步骤块卡、mono 引用角标 hover 反白、composer 聚焦光环、会话行 accent 10% mix）
- [x] T3.3 其余页面铺开（Products 卡片网格+型号歧义徽标、Cases 三态 Badge、Login v6、评测 5 页仅 token）
- [x] T3.4 清理收尾（组件层颜色字面量清零——唯一残留 citation-overlay 属 PDF 纸面例外；e2e 全绿）

## 三、验收记录

- Phase 0/1/2/3 每阶段完成门：`pnpm typecheck`（vue-tsc 0 错）+ `pnpm test:unit`（62/62）全绿
- `pnpm test:e2e`：**57/57 全绿**（52 条原有 + 5 条场景截图测试；任务书写 23 条为旧数字）
- 场景对比图数据一致性：before/after 用同一份 mock 数据（`__scenario-shots.spec.ts`），仅代码版本不同——v6 分支跑 `SHOT_TAG=after`、基线 worktree 跑 `SHOT_TAG=before`
- 双主题运行时验证：`data-theme="dark"` → `--bg` 计算值 `#0A0E14` ✅
- 截图：`frontend/docs/design/screenshots/final/` 6 页 × 2 主题 × 1500×960（改版后）+ `screenshots/before/` 6 页（改版前基线，`codex/m6-source-bound-comparison` 原版，临时 worktree 生成后已清理）

## 四、遗留问题清单（如实）

1. **环境修复（非代码）**：worktree 的 `frontend/node_modules` 原为指向主仓库的 junction，导致 vite `/@fs/` 403、pdf-runtime/pdf-viewer 两条 e2e 在基线即失败。已删除 junction 并 `pnpm install --frozen-lockfile` 重装（依赖版本零变化）。主仓库若同名 junction 仍在，与本分支无关。
2. **T1.3 与既有 e2e 语义的折中**：任务书要求「切会话时 ui.productIds 重置为会话绑定」，但既有 e2e（selected-product.spec）要求「目录选中设备 → 新建会话 → 选择保留且发送一致」。最终实现：会话有绑定→跟随会话；无绑定→保留用户全局选择。两套验收都通过。
   - **自审补充（已验证非问题）**：`syncedConversation` 按会话 id 一次性同步是有意设计——后端中途确认型号只写 run 的 `product_snapshot`（app/runs/commands.py confirm），不回写 `conversation.product_ids`；且 query_planner 从消息历史 assistant `product_snapshot` 继承 `recent` 上下文（app/retrieval/query_planner.py recent_product_context），前端下一问即使传空 product_ids 也不会重新触发澄清。UI 层由消息级 scope-badge 显示中途确认的设备。
3. **T2.5 数据源限制**：后端 `/import-jobs` 只有单查端点（openapi 无列表）。任务折叠区的任务 ID 来自「上传返回 + URL ?job=」两处收集，非持久化——刷新页面后仅 ?job= 深链任务可见。若后端补列表端点可无缝接入。
4. **T2.4 判定方式**：run 响应无 behavior 字段，按后端固定文案 `INSUFFICIENT_ANSWER`（app/answering/assertion_binding.py:14）精确匹配。后端若改文案需同步前端常量。
5. **VERIFIED 徽标**：v6 设计稿的「VERIFIED m/n」需引用级比对数据，后端 citation 无该字段。T1.5 暂只显示 SOURCES 数；EvidenceCard 的 VERIFIED 徽标在有原件可开时显示。
6. **pdf-worker 资产**：`pnpm dev`/`build` 前置的 `scripts/pdf-assets.mjs` 在直接 `npx playwright test`（不走路由 dev script）时未执行，但依赖重装后 pdf e2e 已全绿，无需额外处理。
7. **截图覆盖**：~~聊天页为空态截图~~ **已补齐（2026-11-08）**——`screenshots/real/` ×4：真实预览环境（v6 前端 + qwen3.7-plus + 真实手册语料）的带引用回答流（亮/暗）与证据抽屉（亮/暗），内容断言保证非空态（ROUTE_ 文本 + citation 可见）。
