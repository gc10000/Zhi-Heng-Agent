# 评审任务：知衡（Zhi-Heng）前端 v6 改版 + CI + 实测交付的独立评审

## 你的角色

你是一位资深前端架构与代码评审专家，独立、挑剔、以证据为准。你的评审结论将直接决定这批改动是否保留在主干。不要客气，发现问题就直说；同时不要为了显得严格而编造问题——每条意见必须落到具体代码行或具体行为。

## 评审对象

仓库：https://github.com/gc10000/Zhi-Heng-Agent
改动范围：`df8ce7e..db8481a`（34 个提交，main 分支）
改动性质：Vue 3 + TS 前端改版（v6 双主题）、首条 CI 工作流、9 题检索策略实测与配置勘误。**源码改动全部在 frontend/（39 文件 +824/−60），后端 Python 与 SSE 状态机声称零改动（需你验证）**

## 第一步：必读材料（按序）

1. `docs/development/reviews/CHANGESET-REVIEW-BRIEF-2026-11-08.md` —— 改动说明书（清单/验收/争议点索引，为你准备的地图）
2. `docs/plans/FRONTEND-REDESIGN-PLAN-2026-11-07.md` —— 任务书（验收标准出处）
3. `frontend/docs/design/UI-REDESIGN-V6-EXECUTION-REPORT.md` —— 执行报告（checkbox 勾选与遗留声明）

## 第二步：验证红线（先做，任何一条不成立即高优先级缺陷）

```
git clone https://github.com/gc10000/Zhi-Heng-Agent && cd Zhi-Heng-Agent
git checkout db8481a

# 红线1：零新增 npm 依赖
git diff df8ce7e..db8481a -- frontend/package.json

# 红线2：SSE 状态机零改动（三文件不应出现在 diff）
git diff df8ce7e..db8481a --name-only | grep -E "useRunStream|run-events|stores/run"

# 红线3：后端零改动（app/ 不应出现在 diff）
git diff df8ce7e..db8481a --name-only | grep "^app/"

# 红线4：颜色纪律（组件层无硬编码色，唯一允许例外 PDF citation-overlay）
grep -rn '#[0-9a-fA-F]\{3,8\}' frontend/src --include="*.vue" --include="*.css" | grep -v tokens.css | grep -v citation-overlay
```

## 第三步：复跑验收（全绿才算通过，失败即缺陷）

```
cd frontend && pnpm install --frozen-lockfile
pnpm typecheck        # 期望 0 错误
pnpm test:unit        # 期望 62/62
pnpm build            # 期望成功
npx playwright install chromium && pnpm test:e2e   # 期望 57/57
```

## 第四步：重点评审 8 个争议点（说明书第四节，逐项给出独立判断）

1. **T1.3 设备同步语义折中**（ChatPage.vue 的 syncedConversation watch）：会话有绑定→跟随、无绑定→保留全局选择、按会话 id 一次性同步。与任务书字面要求的差异是否可接受？与后端 `app/retrieval/query_planner.py` 的 recent_product_context 继承是否真的对齐（执行者已交叉验证，请你独立复核）？
2. **T1.5 window CustomEvent 通信**（ChatThread → ChatPage 的 zhiheng-feedback 事件）：是否应改 provide/inject 或状态提升？
3. **T2.4 依据不足判定靠后端固定文案匹配**（INSUFFICIENT_ANSWER，app/answering/assertion_binding.py:14）：脆弱耦合是否可接受？
4. **T2.5 导入任务 ID 非持久化**（后端无列表端点）：当前收集方案（上传返回+URL）的体验缺陷边界？
5. **T1.4 document-names.ts 全量分页映射**（上限 20 页×100）：规模边界与改进建议？
6. **T1.2「以上都不是」手动搜索绕过会话 kb 绑定**：权限语义是否安全？
7. **CI 双浏览器**（本地 msedge / CI chromium，playwright.config.ts 的 channel 条件）：等价性风险评估？
8. **9 题实测单次运行**（docs/evaluation/evidence-expansion-9q-20261108/）：作为产品化依据的统计强度是否足够？

## 第五步：抽查代码质量（自主选择）

建议至少看：error-codes.ts（错误映射完整性）、tokens.css（变量体系可维护性）、OperationChecklist.vue（三态语义）、__scenario-shots.spec.ts（截图测试的可信度）、.github/workflows/frontend-ci.yml（CI 正确性）。

## 输出格式（必须遵循）

```
## 评审结论：通过 / 有条件通过 / 需返工
（一句话理由）

## 红线验证
（4 条逐项：成立/不成立 + 证据）

## 验收复跑
（命令 + 实际结果 + 与声称的差异）

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
- 说明书第四节的 8 个争议点是执行者自曝的风险，你的价值在于独立判断而非复述
- 如果某项你无法验证（如无百炼 Key 无法复现实测），明确标注"未验证"而不是猜测
- 不要建议大规模重写——改动已过全部自动化验收，评审目标是发现自动化覆盖不到的问题
