# 知衡（Zhi-Heng / Product-Knowledge-Rag）改动评审说明书

> 评审范围：`df8ce7e..2970483`（基点 = 原 `codex/m6-source-bound-comparison` 分支头；当前 = main HEAD）
> 改动构成：**34 个提交**（30 个 v6 改版 + 2 个实测/勘误 + 1 个 merge + 1 个截图补齐），其中**源码改动全部在前端**，另有 CI 工作流 1 个、配置勘误 2 个、文档与截图若干
> 源码规模：`frontend/src` 39 文件 +824/−60；零新增 npm 依赖；**SSE 状态机与全部后端 Python 代码零改动**
> 评审基点说明：`df8ce7e` 之前该分支还包含 81 个历史提交（M1-M7 后端演进），不在本次评审范围

---

## 一、改动背景（为什么改）

2026-11-07 三方评审结论：前端「从未开始打磨」——tailwind/lucide/cva 装而不用，style.css 13 行塞全站样式；存在三处卡死体验的 P0 问题（错误码裸露、澄清无出路、设备跨会话残留）。用户经 6 轮设计迭代定稿 **v6 方案**：一布局双皮肤（亮=冷中性+深青 #0E7490；暗=深空青 #22D3EE；同一青色相两档明度品牌同源），任务书见 `docs/plans/FRONTEND-REDESIGN-PLAN-2026-11-07.md`。

## 二、改动清单（按提交粒度）

### Phase 0：双主题基建（4 commits）

| Commit | 内容 | 关键文件 |
|--------|------|----------|
| b6fec57 | token 体系：`tokens.css` 定义全部语义变量（--bg/--ink/--accent/--line 等），`:root` 亮色 + `[data-theme=dark]` 暗色两组，main.ts 在 style.css 前 import | `src/styles/tokens.css`（新） |
| f697034 | 主题 composable：localStorage('zhiheng-theme') 优先 → prefers-color-scheme 兜底 → 写 `data-theme` 属性 | `src/lib/theme.ts`（新） |
| ac4d27c | ThemeToggle 分段开关（☀/☾）接入顶栏；侧栏命名统一「支持流程」 | `src/components/ui/ThemeToggle.vue`（新） |
| 32b5d4f | BrandMark 水平仪 Logo（气泡 fill=var(--accent) 随主题），侧栏+登录页两处 | `src/components/ui/BrandMark.vue`（新） |

### Phase 1：P0 体验修复（5 commits）

| Commit | 内容 | 关键文件 |
|--------|------|----------|
| b0e67f8 | **T1.1 错误人话化**：error-codes.ts 五类映射（product_selection_required→"型号候选过多…"），RunProgress 危险色错误卡 + 复制错误码 + 主/次按钮 | `src/lib/error-codes.ts`（新）、RunProgress.vue |
| 41f91bc | **T1.2 澄清出口**：ProductClarification 候选从按钮改卡片网格，新增「以上都不是」虚线出口 → 全目录搜索指定型号（manualSearch 查询） | ProductClarification.vue、product-selection.ts |
| 1cce813 | **T1.3 设备随会话同步**：会话加载后绑定恢复（watch conversation.product_ids）；消息级适用型号徽标；SCOPE 胶囊 | ChatPage.vue、ChatThread.vue |
| 893fae8 | **T1.4 引用显示文档名**：document-names.ts 分页拉 /documents 建 document_id→name 映射（带 staleTime 缓存），EvidenceCard 头部显示文档名+页码 | document-names.ts（新）、EvidenceCard.vue |
| d395bd9 | **T1.5 聊天页直达反馈**：assistant 消息操作行（✓有帮助/✎反馈/处理草稿→）+ 内联 FeedbackForm（经 window CustomEvent 汇聚到 ChatPage 统一 POST /feedback） | ChatThread.vue、ChatPage.vue |

### Phase 2：P1 优化（6 commits）

| Commit | 内容 |
|--------|------|
| e86e8e9 | T2.1 空态行动化：聊天空态直接「新建会话」主按钮 |
| eeedf53 | T2.2 kb 显示名：auth.labelOf（首段大写兜底），下拉不再显示裸 ID |
| 5329524 | T2.3 命名统一「支持流程」（标题/侧栏/e2e 断言，grep 残留清零） |
| dca687d | T2.4 依据不足徽标：按后端 INSUFFICIENT_ANSWER 固定文案精确匹配 → warn 横幅 + 上传资料链接 |
| c2215a6 | T2.5 导入任务折叠区：ImportJobsFold（最近任务 1.5s 轮询 + 失败重试 + 状态徽标；任务 ID 从上传返回与 URL ?job= 收集） |
| b0fc609 | T2.6 处理记录列表增强：设备名/相对时间/草稿-已确认徽标/回会话链接 |

### Phase 3：设计系统铺开（4 commits）

| Commit | 内容 |
|--------|------|
| 26e342d | **T3.1 基础组件库**：Button/Badge/Card 三段/Input（cva + 语义变量零依赖手写，参照 shadcn-vue 模式）+ stories.md props 表；Modal 样式变量化 |
| 928a5f6 | **T3.2 ChatPage 对齐 v6**：用户气泡（右对齐 14/14/4/14 圆角）/AI 纯文本；ol 步骤块卡片化；行内引用角标 mono 化 hover 反白；composer 聚焦光环；**含 T1.3 watch 时序修复**（见第四节争议点①） |
| 70581f6 | T3.3 四页铺开：Products 卡片网格+型号歧义徽标；Cases 操作清单三态 Badge（系统建议 info/用户记录 warning/无效 danger）；Login v6；评测 5 页 token 化 |
| 521ff07 | T3.4 清理收尾：**组件层颜色字面量清零**（全库 grep 验证，唯一例外 PDF citation-overlay 坐标高亮） |

### CI 与交付（8 commits）

| Commit | 内容 |
|--------|------|
| a02ddcc…2970483 | 双主题截图×12、执行报告、基线截图×6、场景对比截图×10 + 场景截图 e2e（`__scenario-shots.spec.ts`，mock 数据 before/after 可复现） |
| ce10cda | 自审记录：T1.3 一次性同步与后端 product_snapshot 继承语义交叉验证（详见第四节争议点②） |
| 2987ce0 | Merge PR #1（merge commit 保留任务粒度） |
| d313d64/1ccba2d/d7bfec5 | **首条 CI**：typecheck/unit/build/e2e；修复 setup-node 相对路径坑、钉 ubuntu-24.04（Playwright 1.56 不支持 26.04）、CI 用 chromium 替代 msedge（`channel: process.env.CI ? undefined : 'msedge'`） |
| 942fedf | **9 题实测产物**：报告+两轮 JSONL 版本化进 docs/evaluation/；**模型下线勘误**（.env.example：qwen3.8-flash→qwen3.7-plus、qwen-vl-plus→qwen3-vl-plus，182 在列模型实测） |
| 2970483 | 真实环境截图×4（内容断言非空态）+ 报告遗留#7 闭环 |

## 三、验收证据（评审可复核）

| 验收项 | 结果 | 复核命令 |
|--------|------|----------|
| 类型检查 | 0 错误 | `cd frontend && pnpm typecheck` |
| 单元测试 | 62/62 | `pnpm test:unit` |
| 端到端 | 57/57（52 原有 + 5 场景截图） | `pnpm test:e2e` |
| 生产构建 | 通过（9.6s，产物含 [data-theme=dark]） | `pnpm build` |
| 双主题运行时 | dark → --bg=#0A0E14 | devtools 验证 |
| 颜色纪律 | 组件层字面量 0（例外：PDF 高亮） | `grep -rn '#[0-9a-fA-F]{3,8}' src/ --include='*.vue'` |
| CI | ubuntu-24.04 四关全绿（PR 与 main 均验证） | GitHub Actions |
| 真实环境 | 预览全链路真实问答 + 9 题对照实测 | `docs/evaluation/evidence-expansion-9q-20261108/` |

红线自查：**零新增 npm 依赖** ✅ · **SSE 三文件（useRunStream/run-events/stores/run）零改动** ✅ · **后端 Python 零改动** ✅ · **主仓库 .env/密钥不入库**（runtime.env 在 gitignore 的 output/ 下）✅

## 四、建议重点评审的争议点/风险

1. **T1.3 语义折中**（928a5f6 内）：任务书要求"切会话重置为会话绑定"，既有 e2e 要求"目录选设备→新会话→保留"。实现为：会话有绑定→跟随；无绑定→保留全局选择。且 `syncedConversation` 按会话 id 一次性同步（会话中途 confirm 型号不重同步）——已与后端 query_planner 的 recent_product_context 继承语义交叉验证对齐，但值得评审者独立复核。

2. **T1.5 的 CustomEvent 跨组件通信**：ChatThread 内联反馈表单经 `window.dispatchEvent('zhiheng-feedback')` 到 ChatPage 统一提交。简单但绕过了 props/emits 规范——评审者可判断是否应改为 provide/inject 或提升状态。

3. **T2.4 文本匹配判定**：依据不足徽标靠后端固定文案 `INSUFFICIENT_ANSWER`（app/answering/assertion_binding.py:14）精确匹配，后端改文案即失效。无 behavior 字段可用（openapi 已核对）。

4. **T2.5 任务 ID 非持久化**：后端无 /import-jobs 列表端点，折叠区任务 ID 来自上传返回+URL，刷新后仅 ?job= 深链可见。

5. **T1.4 全量文档映射**：document-names.ts 分页拉全量 documents（上限 20 页×100）建映射，文档量极大时有性能边界（当前演示规模无碍）。

6. **T1.2 手动搜索绕过会话绑定**：「以上都不是」出口搜索全目录（不限当前会话绑定的 kb 产品），是有意设计（用户明确指定优先）但需确认权限语义。

7. **CI 的 `channel: CI ? undefined : 'msedge'`**：本地仍走 msedge（保持原行为），CI 走 chromium——两环境浏览器差异理论上存在（Chromium 版本不同），57 条 e2e 在两环境均绿。

8. **实测有效性**：9 题对照每相位单次运行（LLM 随机性未做多轮均值），符合执行规格"最小证据集"定义，但作为产品化依据的统计强度有限——报告第五节已如实声明。

## 五、评审材料索引

| 材料 | 位置 |
|------|------|
| 任务书（验收标准出处） | `docs/plans/FRONTEND-REDESIGN-PLAN-2026-11-07.md` |
| 改版执行报告（checkbox+commit 对照+遗留） | `frontend/docs/design/UI-REDESIGN-V6-EXECUTION-REPORT.md` |
| v6 设计稿 | `docs/design/ui-final-v6.html` |
| 9 题实测报告+原始数据 | `docs/evaluation/evidence-expansion-9q-20261108/` |
| 截图 32 张（基线/双主题/场景对比/真实环境） | `frontend/docs/design/screenshots/{before,final,scenario,real}/` |
| 组件库 props 表 | `frontend/src/components/ui/__stories.md` |
| CI 工作流 | `.github/workflows/frontend-ci.yml` |
| 评审基点对照 | `git diff df8ce7e..2970483 -- frontend/src/`（全部源码改动 39 文件） |

## 六、环境事实（评审者可能需要知道的）

- 百炼 `qwen3.8-flash`/`qwen-vl-plus` 已于 2026-11-08 实测确认下线（model_not_found），替代 `qwen3.7-plus`/`qwen3-vl-plus` 已实测可用——.env.example 已勘误，但**用户本地 .env 未自动修改**（需手动改）。
- 配置键陷阱：`app/conf/lm_config.py` 读 `LLM_DEFAULT_MODEL`（非 TEXT_MODEL）；`prepare_preview` 生成的 runtime.env 不含该键。
- 预览环境（zh-m7-3e8697，127.0.0.1:58939）依赖宿主 8011 模型桥接进程（BGE-M3/reranker），该进程会话级，重启机器需手动拉起。
