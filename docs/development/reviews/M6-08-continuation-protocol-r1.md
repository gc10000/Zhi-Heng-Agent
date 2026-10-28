# M6-08 continuation来源协议与题级账本定向验证

日期：2026-10-28。起点`33b120d1331bf25b8688337a7ebb8685704e4bd4`，与origin/main一致；仅tmp未跟踪。用户本轮授权协议实施与定向测试，不启动供应商模型调用。M6仍4/7、M6-04/05/08未验收，M7未授权。

## 当前仓库与实施边界

本轮开始时仓库已经包含[r3](M6-08-full-dev-baseline-r3.md)的interrupted分支及19继承+66执行组合材料，因此不重复创建实验、迁移检查点或执行真实dev。r3源码仅靠job字符串传递来源，普通首attempt也能为interrupted checkpoint派生请求；新Run再次中断后又能以不同父Run继续派生，缺少正式父实验校验和调用前来源账本。本轮收窄该边界，不回填r3，不把它认定为本轮生成或质量验收。本轮不重新认证r3对于旧attempt2触发来源的勘误；旧报告及未知HTTP/费用均保留。

## 最终协议

创建请求可选严格continuation字段：source_experiment_id、source_attempt、source_version、reason。服务端重新按owner/kb取父实验，核对failed/cancelled/incomplete终态、当前attempt/version及相同dataset/manifest/config字节hash；父state/retryable/error和配置/请求hash快照随新实验保存。不存在/越权404，活动/过期/冻结不符409，非法字段422。省略/null保留旧幂等身份，不改父实验retryable。

正式job只为显式continuation传入该来源；普通首attempt不再获得interrupted后续资格。对中断题，以新experiment+checkpoint生成唯一账本键，调用前setOnInsert保存父实验代际、父Run身份快照/指纹、输入hash和固定request_key。通过RunService创建后先绑定新Run，再执行QueryRunner；若Run已创建而checkpoint尚未绑定时退出，下次仍用同一请求取得同一Run。重复执行或重新领取同一个continuation不更换请求；该后续Run再次中断时停止，不自动产生第三条Run。

completed checkpoint仍复用，非retryable failed Run在retry_key或continuation下均不重生成。父Run文档原样保留；题级账本状态和遥测可随新Run观察更新，来源身份不改。逻辑invoke/stream与token仅取持久Run遥测，缺失null；精确SDK HTTP次数/费用保持null，prepared状态不能被当成付费0，不承诺失败窗口exactly-once。

本版只接受完全相同冻结config；修改源码会改变runtime code身份，旧config不能通过新代码真实运行。未增加自动检查点迁移或跨代码版本继承功能。原19成功项与r3继承材料均未写入；原本地manifest/attempts/results与r2备份SHA256逐项一致。

## 实际验证

所有Mongo测试使用显式`m1_test_m4_continuation_20261028`前缀及每例随机子库，保留现场、不删除库。模型/检索为合成端口注入；HTTP使用正式FastAPI路由和真实隔离Mongo，不是供应商全链路。

| 验证 | 实际结果 |
| --- | --- |
| 4项红测 | 4失败：缺少来源字段、活动来源错误门禁、无来源可重生成、普通首attempt获得retry_key；JUnit留存。PowerShell包装末尾Get-Content覆盖退出码为0，不以包装码冒称通过 |
| 首轮实现adapter/jobs | 23通过/1失败；父Run含datetime不能直接JSON fingerprint，已改为稳定身份字段 |
| adapter/jobs/RunCommands/题集/目录/适配器 | 85通过，退出0 |
| 最终定向（上述及宿主认证/并发） | 88通过/0失败/0错误/0跳过，退出0 |
| 最终加强非retryable+continuation边界 | 1通过，退出0；与88组重叠，不相加 |
| OpenAPI导出/前端API类型生成/vue-tsc | 生成成功，typecheck退出0；实际输出在本会话工具记录 |
| 本轮只读摘要 | 当前OpenAPI一致、5源码语法通过、原三文件与备份hash一致 |

测试包含父来源越权/缺失/活动/过期/配置变化拒绝、重复创建及null兼容、正式HTTP严格字段、job来源传递、completed复用、无显式来源不重生成、调用前账本存在、重建executor幂等、创建后崩溃恢复、后续再次中断停止、来源变化拒绝、旧Run全文不变和未知费用保留。

```powershell
$env:M1_TEST_DB='m1_test_m4_continuation_20261028'
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m pytest tests/integration/test_evaluation_run_adapter.py tests/integration/test_evaluation_jobs.py tests/integration/test_run_commands.py tests/unit/test_evaluation_query_adapter.py tests/unit/test_evaluation_dataset.py tests/unit/test_evaluation_catalog.py tests/unit/test_evaluation_host.py -q --junitxml=output/m6-continuation-protocol-20261028/final.xml
.venv/Scripts/python.exe -m pytest tests/integration/test_evaluation_run_adapter.py::test_explicit_m6_followup_does_not_retry_nonretryable_failed_run -q --junitxml=output/m6-continuation-protocol-20261028/nonretryable-final.xml
# frontend目录
npm run generate:api
npm run typecheck
```

原始红/中间/最终JUnit与日志只在本机`output/m6-continuation-protocol-20261028/`。脱敏[验证摘要](M6-08-continuation-protocol-validation-r1.json)保存每组实际数量、原文件hash和证据路径/hash；不同测试组重叠，不累计唯一总数。本轮未运行全量后端/前端单元/浏览器/build、真实模型、heldout、导入或Linux队列传输；没有真实human/observation/校准写入，没有重启服务。

已同步API契约、OpenAPI/前端声明、workbench、ADR-070、进度及M6接续记录。本会话按AGENTS约定顺序开发、自审差异，未派发子代理；自验不等于独立阶段验收。下一步只读审查本轮协议与r3组合结果的适用边界，再处理M6剩余固定报告/人工与校准门槛；不要求重复已保存聊天判断，不用继承结果冒充反馈后新生成，不进入M7。
