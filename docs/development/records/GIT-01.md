# GIT-01 · 2026-10-23 · 首次接入

用户明确授权初始化/正常推送，覆盖M0历史限制。仅本项目建立.git，main承接远程初始提交679fe9b，远程只含README，原内容保留为docs/GITHUB_INITIAL_README.md；没有重写远程历史。

首次提交是当前已验收M0的整体验收基线，保留NOTICE课程底座说明，不伪造过去逐任务历史。未加入M1实现。显式暂存源码/测试/依赖/示例配置/必要文档，未使用git add .。排除原件、模型、缓存、运行数据和整个docs/development/evidence（包括所有原始报告、originals/r2-before/r3-before）。本地证据未改写；远程文档中原证据链接可能仅在本机可用，不把脱敏摘要当原始输出。

接入前新跑`.venv/Scripts/python.exe scripts/verification/run_m0_checks.py --prefix M0-git-baseline`退出0：pytest105通过、既有unittest3通过。它们是本次离线验证，M0真实图片/冷启动仅引用既有总控已接受证据，没有重跑付费查询。本地输出evidence/M0-git-baseline-validation.json等保留。

暂存264文件逐文件检查大小和凭据/签名URL模式：唯一命中test_llm_options.py为既有合成泄漏回归字符串，不是真实签名。无.env、课程PDF/Excel、模型、备份或真实证据文件。git diff --cached --check存在原课程/第三方研究文件既有行尾空白，不批量修改来源代码。没有新增许可证，课程来源及第三方版权保持原样。

本提交完成后续记实际SHA和推送核对结果，不循环amend。回滚不删原数据，不重写推送历史；后续更正用新提交。
