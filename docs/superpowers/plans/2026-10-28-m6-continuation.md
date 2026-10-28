# M6-08 正式 continuation 来源与题级账本实施计划

用户已授权实施协议和定向测试；供应商模型、heldout、真实评分和校准不在本轮范围。起点为已推送的 `33b120d1331bf25b8688337a7ebb8685704e4bd4`。本会话顺序执行，不派发子代理。

**目标：**新实验显式保存来源实验/attempt/version；020 的新请求在模型调用之前有持久来源，重复执行不会静默再派生 Run，成功检查点继续复用。

**方案：**创建请求新增可选 continuation 对象，由服务端按所有者、知识范围、冻结题集/config、父实验终态及版本校验。采用独立 evaluation_continuations 题级不可变身份账本：先以新实验和原 checkpoint 身份创建固定来源/请求键，再经 RunService 创建 Run。重新领取仅复用这个请求；后续 Run 再次中断时不自动创建第三条 Run。已有 retryable 失败重试门禁保持。普通实验不能因为存在中断 checkpoint 就获得新请求资格。

**边界：**本版只支持完全相同冻结 config 的 continuation；源码身份变更仍须新版本及独立继承审计，不提供自动迁移。r3 旧实验/结果/来源材料不回填、不改写。本轮修改不执行任何真实 dev 入口。

## 1. 正式实验来源

- [x] 在 ExperimentInput 加入严格 continuation 来源字段，repository 创建时鉴权读取源实验，验证终态、attempt/version、题集/config 完整身份；保存来源快照。
- [x] 先在独立 Mongo 建立红测，覆盖重复创建、非可重试旧失败不变、未知来源/越权/活动或过期源/冻结身份变化拒绝。
- [x] job 仅将显式 continuation 来源传给适配器；普通任务仍仅在 attempt>1 时设置原 retryable 重试键。

## 2. 题级幂等与账目

- [x] 先写测试复现：无显式来源时禁止 interrupted 重生成，completed 复用；同一 continuation 重建 executor 或后续 Run 再中断不创建第三条 Run。
- [x] 调用前以 setOnInsert 保存新实验、父实验/attempt/version、父 Run、checkpoint/input/config hash、固定 request_key；RunService 返回后绑定新 Run，执行后记录状态和可观测遥测。
- [x] HTTP 次数、费用默认 null，逻辑调用/token 仅从实际持久遥测记录；保留旧未知窗口，不把复用算新生成。

## 3. 验证与交接

- [x] 运行 adapter/jobs/repository/API schema 的定向回归，全部只用随机 m1_test_m4_* 子库与合成模型；原始日志/JUnit 存 output 本机新目录。
- [x] 同步契约、workbench、OpenAPI/前端类型与 M6 接续文档，保持 M6 4/7、04/05/08 未验收、M7 未授权。
- [x] 审查差异；提交推送及远程核头在最终交接记录；tmp、output、evals、原始 evidence 不上传。
