# M6-048执行前置补修与剩余单流接续

日期：2026-11-03。分支：`codex/m6-source-bound-comparison`。用户要求发现前置问题直接修复；本次验证总计最多一个provider stream，不复用失败身份。

已修复Windows干净Git检出的行尾差异误拒，以及InternalRunInput遗漏ComparisonAnswer048Contract导致Run创建前校验拒绝。真实内容变化仍拒绝，公开RunInput仍拒绝内部合同。

r4实验be93be34-2b73-4a10-9366-f7e1e91b5443失败/result0；r5实验dbf52772-43c8-4c5b-9c51-31401bc822c0失败/失败result1，已有conversation/checkpoint而无Run/link/outcome/risk账户/provider。原summary调用和usage为null，另存只读审计证实首次模型入口前失败。均封存，不修改state、lease、retryable或旧blocked账户。

验证：104相关单元/契约通过（1条既有Pydantic警告）；13隔离Mongo通过，包括正式RunService合同持久化、幂等及比较正常/断流/非法/空证据路径；OpenAPI2通过。误用m1_test_m6r5fix前缀造成7项目标门拒绝，使用m1_test_m4_前缀后通过；不是Docker阻塞。

新r6仅续接此前尚未消费的一次stream，授权提交ced704033b6be6704c16485dc4637b71046f5179，SHA d2871685f00753c9429ca0c8b1ec0bf85857d9e9bf30a48a7c2d0d8311437a51。下一步冻结最终代码并通过资源及精确身份预检后执行。目前新增provider stream、本地推理和usage为0；正式业务写入不为0。

后续r6进入正式Run，10份正文、映射、分组和预算相同，但产品名称排列与冻结prompt相反，被生成前严格校验拒绝。持久Run telemetry为invoke0/stream0，无风险账户/started/settled；本地BGE编码已运行，不能将整个本轮写为本地推理0。已补比较模式按冻结input_product_snapshot顺序呈现名称，回归先复现AX/BX反序，再验证修后通过。当前106相关单元/契约（含OpenAPI2）、14隔离Mongo通过。r6实验f41b7a56-d10b-400c-b23a-ed9df3bd1a1a及failed Run保留，新r7只续接未消费的那一次stream。原summary调用/usage为null保留，另存审计不得覆盖原件。

本记录是实现/执行自验，不签独立关闭或答案质量通过。M6保持5/7，04保持验收，05缺反馈复评proof，08缺有效候选质量和阶段证据；43题暂停，heldout未运行，M7未启动。
