# 项目开发约定

适用范围：本目录及其子目录。用户在当前会话中的明确要求优先。

## 开始工作

1. 阅读 `docs/development/PROGRESS.md`，确认当前任务与交接点。
2. 阅读 `docs/plans/DEVELOPMENT_TODO.md`、对应 `docs/plans/tasks/M*.md`、`docs/plans/DEVELOPMENT_CONTRACTS.md` 和涉及的实际源码。
3. 默认按任务依赖逐项执行，优先完成并验收当前任务，再领取下一项。发现计划与现状不一致，先同步计划与受影响契约。
4. 阅读 `docs/development/REVIEW_STATUS.md`，按当前阶段授权连续开发。阶段末提交审查材料，由原规划会话独立复核后授权下一阶段；执行会话不得自行标记总控审查通过。

## 已确定方向

- 设备技术支持与知识工作台；前端 Vue 3 + TypeScript + Vite，不使用 React。
- 当前 Windows 本机调试；保留 FastAPI/LangGraph/Milvus/MinIO/MongoDB 底座。Redis/Celery 在对应阶段接入，worker 使用 Linux Docker。
- 新增业务注释、配置说明、用户文案和维护文档使用中文；版权/许可证原文保留。
- 优先可维护的 GitHub 组件复用，登记上游固定版本、文件映射、许可证与改动。不要将借鉴描述为原创。
- 用户已授权更新提交并推送至 `https://github.com/gc10000/Zhi-Heng-Agent.git`，无需逐次确认。先读 `docs/development/GIT_WORKFLOW.md`；首次允许在本项目目录初始化及绑定远程，按任务小提交、验证后正常推送，保留用户和远程历史。旧审查“不初始化/不推送”是历史限制，已由本次授权更新。

## 实施与验证

- 对行为修复先写能揭示问题的回归，按任务定向验证；文档/样式等低影响改动按实际结果检查。
- 不输出 `.env` 的值。新增配置必须同步 `.env.example` 和 `docs/CONFIGURATION.md`，缺配置仅报告变量名与用途。
- 迁移、写入与故障验证使用独立测试库/集合/对象前缀；保留当前课程知识数据，遵守新集合、小样、验证后发布和回切方案。
- 单元测试不访问真实数据库/云服务或自动下载模型。只有实际运行且结果符合预期才能声称验证通过。
- 不自行生成性能提升数据，不把未实现页面或 mock 指标当已完成能力。
- 默认在当前工作任务中顺序开发；只有用户明确要求时才使用子代理。Git同步遵守上述授权与文件排除要求；阶段审查、服务器部署和公开Release按各自授权执行。

## 每次开发必须维护文档

- 开始任务：在 `docs/development/PROGRESS.md` 写当前 ID、范围和下一步。
- 任务验收通过：在 `docs/plans/DEVELOPMENT_TODO.md` 勾选任务，完成阶段文件的步骤，保存 `docs/development/records/<任务ID>.md`，同步进度和 `CHANGELOG.md`。
- 变更 API、事件、数据、配置、依赖、复用或部署时，同步对应契约、说明与 runbook；取舍记录到 `DECISIONS.md`。
- 结束会话或中断：留下实际改动、检查结果、未完成步骤、阻塞与下一条动作。未验证的任务保持未勾选，不把部分实现计为完成。
