## 2026-11-02接续：风险合同与单槽账本独立复核

总控独立关闭有限技术子项：默认关闭合同解析/专用路由、无新授权时实验/客户端/manifest失败关闭、旧048账户collection与冻结hash核对，以及隔离CAS账本结算/失败不重领。授权后的正向manifest/runtime路径仍未验证；不放行调用。真实比较答案和质量未产生，M6保持5/7，05/08证据仍缺。验证为164相关单元、52隔离Mongo、2 OpenAPI契约通过；首次集成启动前置失败及修复留本机。详见[独立复核](../reviews/M6-comparison-answer-risk-review-r1.md)及[验证摘要](../reviews/M6-comparison-answer-risk-review-validation-r1.json)。

## 2026-11-02接续：风险合同与单槽账本实现自验

上述“合同解析类型／处理器未实现”是该记录创建时点的现状。接续`857a4dd`后，已实现独立默认关闭的`diagnostic_comparison_answer_048_v1`合同、专用risk档案和CAS账本路由。新risk使用不同batch、成员slot、collection和ledger_id；唯一题为`support-v1-048`。预算沿历史input/output `53089/30412`，单次预留`28416/4096`，累计算术上限`81505/34508`。启用合同仍无新的受审Git授权，正式catalog `output_contract`保持`null`；service、client和manifest入口失败关闭。

164项相关单元、5项随机隔离Mongo新账本和47项旧比较／source-relation隔离Mongo自验通过。首轮红测、cwd、MONGO_URL环境装载和slot目录夹具失败均留本机`output/m6-comparison-answer-risk-20261102/`；修复情况和禁止真实调用边界见[风险合同实现报告](../reviews/M6-comparison-answer-risk-r1.md)。

本接续仍为实现自验，等待独立定向复核。正式账本未写experiment/Run/slot/outcome，模型调用/本地推理/质量记录均0；模型权重不可用、model fingerprint未重算。M6保持5/7，04已验收，05反馈复评proof与08有效候选/阶段proof仍缺；43题暂停、heldout未运行、M7未启动。旧“下一目标”文本按原提交时点保留。

# M6 比较答复正式控制账本记录 r1

日期：2026-11-02

分支：`codex/m6-source-bound-comparison`
基线提交：`f3ba326`

## 本轮目的与边界

本轮只完成正式评测控制账本登记、冻结题集目录读回和 `comparison_answer_v1` 配置准备，并补上服务端在实验／槽位预留前的准入拒绝。没有启动真实模型、没有创建正式 experiment／slot／Run／outcome，也没有写入评分、候选、校准或阶段 proof。此记录不是独立技术关闭、真实答案质量结论或 M6 阶段验收。

## 冻结题集与配置

- 题集：`m6-full-dev-r1` / `fb-07c584730833908571fe9dd7c7c890afa3cf9e66`
- 规模：150 题，其中 dev 85、heldout 65
- 唯一选择：`support-v1-048`
- 配置：`m6-comparison-answer-048-r1` / `r1`
- `comparison_answer_v1`：开启
- `assertion_binding_v1`：关闭
- 题集 SHA256：`c72a78955afe86503fbb37cc7293fa54287b0427877af4616bb762dfb57656c9`
- manifest SHA256：`3f2b3c3413da98773b600623200deb399f91da3e9c8b1b6dd0be3fc2d83109f9`
- 配置 SHA256：`60f5e896a3b1ca0cf44114959f8a04b96f60f51ab25be8c8d44aa857b1aacf0d`
- catalog SHA256：`f44721cedc0d6bf08067781923ab92e00953b3f151b8061b16797f7de42bb20d`
- 本机 catalog：`output/m6-comparison-answer-048-r1/catalog/catalog.json`
- 本机持久输出根目录：`output/m6-comparison-answer-048-r1/work`
- 配置文件：`output/m6-comparison-answer-048-r1/catalog/configs/m6-comparison-answer-048-r1.json`
- 代码指纹：`0d0dd5e47fd0de685e60541804441b1fbf4145819f1139f41e1fc2eb5efea6c6`
- prompt 指纹：`cd3c40ef0e6af5de7edc7d4257aa09edeb92ac895aaeff16683d00110b395dc6`
- model 指纹：沿用冻结 profile；本机模型权重目录不可用，未重新计算。

配置的 `output_contract` 当前为 `null`。这使它可被登记和复现，但不可派发；不能把比较模式开关当成调用授权。代码预留的 `diagnostic_comparison_answer_048_v1` 目前尚未在输出合同解析器或风险处理器中注册，因此当前没有可接受的比较风险合同。后续须先实现并审查该合同，再以新实验身份和单次预算形成可派发配置；不能复用旧已消费槽、blocked 账户或旧质量证明。

## 控制库登记读回

独立控制库为 `product_knowledge_rag_m6_eval_control`。本轮读回确认：

- maintainer 账号 1 个，密码验证通过；凭据只保存在本机 Windows DPAPI 加密目录，不进入 Git 或本报告。
- `evaluation_sets` 题集登记 1 个，题集／manifest hash 与冻结目录一致。
- `evaluation_experiments`、`evaluation_results`、`evaluation_slots`、`runs`、`evaluation_execution_links`、`evaluation_outcomes`、`diagnostic_output_accounts` 均为 0。
- 模型调用为 0。

一次正式服务准入预检在写 experiment／slot 前返回 `422 comparison_admission_required`；预检前后实验和槽位计数均未增加。这证明当前配置被安全阻断，不证明真实答案可用。

## 实现与验证

`EvaluationService` 现在对开启比较模式但缺少专用风险合同、旧合同或未知合同的请求稳定返回 422，避免先占用槽位再由 worker 失败。合成比较接线测试通过仓储直接创建隔离实验，生产准入仍由单元测试覆盖。由于该风险合同解析类型和处理器尚未实现，当前所有比较模式实验均保持不可派发。

定向验证使用随机 `m1_test_m4_` 隔离库：45 passed，包括比较准入单元、正常／分库 Run 接线、断流失败材料、空选择、恢复和既有比较边界。第一次命令使用了不符合执行目标allowlist的`m1_test_m6cmpctl_`前缀，7项合成集成在`validate_target`抛出`ValueError`，38项单元／离线测试通过；按要求换成`m1_test_m4_`新随机前缀后重跑通过。该命令失配记录留在本机，不计业务缺陷或通过证据。

本轮再次运行专用账本验证脚本，catalog官方解析和数据库读回断言通过；未重算模型指纹。代码与prompt哈希仍匹配冻结配置。配置准备摘要见[验证摘要](../reviews/M6-comparison-control-ledger-validation-r1.json)；私有读回和首次测试失败摘要保留在本机 `output/m6-comparison-control-ledger-r1-20261102-155443/`。根 `.env` 已指向上述 catalog 和 work 路径，相关值不进入仓库。

## 当前阶段与未决项

M6 保持 5/7：M6-04 已验收；M6-05 仍缺真实反馈复评 proof；M6-08 仍缺有效候选质量和阶段验收证据。原 43 题继续暂停，heldout 65 题未运行，M7 未启动。历史累计 input/output 仍为 53089/30412，reasoning、HTTP 和费用保持未知或空值。

本轮唯一下一目标是：在不复用旧消费身份的前提下，为 `support-v1-048` 建立受审的新风险合同和单次实验身份，再由总控决定是否进行最多一次真实 stream。真实执行必须判断完整的自然语言比较结论，而不是把原文摘录数量当作质量通过条件。
