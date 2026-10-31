# M6单题风险准入与05-a执行接续 r1

日期：2026-10-31，Asia/Shanghai。身份：execution-agent implementation/self-check；不是独立复审、答案评分或阶段验收。

## 本包实际结果

**新增真实产品答案0；唯一05-a调用尚未执行。** 实现显式单题风险准入并完成最终源码169项离线／契约和精确保存输入的SDK Mock。实时消费者预检在读取活动修订时因Mongo连接拒绝退出；随后用户明确回复“正在维护，暂不启动”。本包没有启动Docker、创建真实实验、登记真实配置或消费产品固定槽。维护后的最终版集成及实时预检仍是硬前置，不能把本次离线通过写成完整自验或质量改善。

开始实核HEAD＝origin/main＝GitHub main＝`bcee5395604bcd7169c907ddcf146f163ccc2d14`，起始仅未跟踪tmp。执行期间另一运维会话新增compose、WINDOWS_DOCKER、运维记录及PROGRESS段落；这些改动保留，不混入本包。远程与最终提交状态以最终交接为准。

## 实现范围

- 在既有OutputContract、正式配置、InternalRunInput、QueryRunner、执行关联和题级恢复检查点中加入默认关闭的`diagnostic_single_product_risk_v1`；不新增公开API，不修改正常v2的unknown拒绝分支。
- 授权采用封存Git `bcee5395604bcd7169c907ddcf146f163ccc2d14` 中的`docs/development/reviews/M6-single-product-risk-authorization-r1.json`；blob SHA256=`0270a6e7d8cdfc434a0dadf8fcbe7bae8b80e2417515f73117b83b3f1f81a591`。能力事实保持unknown，不登记verified或server_hard_limit。
- 固定`m6-05a-product-canary-r1`，绑定版1题目、完整题集／manifest、控制与目标范围、精确prompt／受审关系、当前源码、新配置、账户及生效发参。调用前先正式租约／Run关联核验，再CAS账户预留，再操作系统独占创建started，之后才允许联网。
- started未知窗口禁止重发；结算全等只读复用，冲突拒绝。换nonce、目录、ledger或库不产生额度。首次准备失败的计划不覆盖；未消费前仅允许同输入的代码版本追加冻结，所有冻结仍争用同一个started。started或settled后禁止追加。
- 专用客户端固定n1、qwen3.8-flash、temperature0.1、extra_body.max_completion_tokens4096、SDK重试0、120秒、stream＋usage、无redirect／fallback，网关默认thinking。raw_usage_v2仍在正式结算链。

本包红测另定位两个接线遗漏：生成节点的`output_limit_options`仍直接解析旧v2而拒绝新风险身份；显式enabled=false仍被风险分类识别。分别改为统一合同解析与enabled判定，先复现红测再修复。没有修改检索、重排、prompt构造、AnswerFilter或对象关系语义。

## 源码与输入身份

| 项 | 固定值 |
| --- | --- |
| 最终源码指纹 | `b50b1f5b0eab66d7a4eb2a32314bcd415dba2624354cfb0ece59d2efce17ab8b` |
| 诊断配置canonical SHA | `22d0e525ba1074336a6d7af973cc50427eb96e4c3f5ad28d9a3c60e37ff65efc` |
| 诊断配置文件SHA | `288f014ee987675a93151e54c40c54a83ea9996968f6a7c593157d17fb0e2b04`（本机冻结，尚未正式登记） |
| 最终执行manifest SHA | `0e94544429f865b2f2e35193f9f915e06282de9c1faf85fafe27d4891bb85533` |
| 正式请求稳定键 | `f3f16112c23330b0a5c142c3a64559d6cbd79f5e82ac00cd617529b5fc9526d9`（请求对象hash；client_request_id另在私有request.json中） |
| 题级检查点key | `9dc35acea3b1133b409e403caa2eea8bfea70cf4e91d8e0ba3c01da47f243301` |
| prompt canonical fingerprint | `c975587079e01a747990468487ac01c700137bc48578f130008e24ed676b5498` |

唯一源输入仍为受审`replay-final/requests/v1-m6-g540-05-a.json`，文件SHA `95a287a3a882aa6b7c3f16eed56a013db7b19b1031e6de035c11420b8ac1aeee`；prompt UTF8 SHA `05f47209a2bfe1aaa5b5d5d58344e6ac3112e55742790fc34034116383758e9f`。受审binding SHA `6b7b6e9062e1ca566008515a542cba0bb90daa1085f09ef81eb1ae015f00dabf`。新版完整dataset／split manifest沿原版1SHA，未缩为单题质量题集，仅配置选择唯一题目。

首份prepared／planned及失败日志原样保留；最终代码冻结另存prepared-r2和固定槽code-plans。旧代码计划现已不符合当前源码，不能拿它发请求。没有新experiment_id或Run id，不虚构这两个身份。

## 实际验证

| 检查 | 实测结果与限制 |
| --- | --- |
| 最终源码离线／契约 | 169通过，exit0；1个既有非法float故障夹具Pydantic告警保留 |
| 中途源码正式单题job | 8通过，exit0；同库／分库×正常、坏usage、断流、快照前中断；不是最终源码集成通过证明 |
| 最终所需隔离集成 | 未完成；槽前／后退出4例在Mongo前置报错，exit1，71项被-k筛除，未声称它们运行 |
| 保存输入SDK序列化 | 实际安装SDK＋MockTransport通过，exit0；精确prompt、n1、4096、usage开关等；不证明网关硬限或产品质量 |
| 实时消费者预检 | exit1；读取活动修订时Mongo连接拒绝，未到编码、重排或供应商阶段；preflight-complete不存在 |
| 只冻结本机身份 | freeze-only通过，exit0；不代表真实配置登记或消费者预检 |
| OpenAPI | 当前工厂与已存导出全等，无新增公开API |
| 离线保护审计 | 2438项文件／来源断言通过，不是数据库或质量分数 |

关键确切命令（全部原始日志与退出码均保留于本机新目录；组间有重叠，不累计唯一总数）：

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_single_product_risk.py tests/unit/test_output_contract.py tests/unit/test_output_contract_boundaries.py tests/unit/test_provider_clients.py tests/unit/test_telemetry_provider.py tests/unit/test_evaluation_query_adapter.py tests/contract/test_provider_capabilities.py tests/contract/test_provider_errors.py -q
# green-unit-r4.log，exit0，169通过
$env:M1_TEST_DB='m1_test_m4_sc_117e8d'
.venv/Scripts/python.exe -m pytest tests/integration/test_single_product_risk_jobs.py -q
# green-joined-r4.log，中途源码8通过，exit0
$env:M1_TEST_DB='m1_test_m4_sc_34b7c1'
.venv/Scripts/python.exe -m pytest tests/integration/test_single_product_risk_jobs.py -k 'before_slot or after_slot' tests/integration/test_diagnostic_output_contract.py tests/integration/test_output_contract_boundaries.py tests/integration/test_evaluation_split_ledger.py tests/integration/test_evaluation_run_adapter.py -q
# green-integration-r2.log，4个Mongo setup errors／71 deselected，exit1
.venv/Scripts/python.exe output/m6-single-product-canary-20261031/prepare_canary.py
# preflight-r1.log，最初驱动尚无--mode；Mongo拒绝，exit1，原日志保留
.venv/Scripts/python.exe output/m6-single-product-canary-20261031/prepare_canary.py --mode freeze-only
# freeze-r2.log，exit0；无数据库或推理
.venv/Scripts/python.exe output/m6-single-product-canary-20261031/sdk_wire_precheck.py
# saved-sdk-mock-r3.log，exit0；保存输入Mock，无真实请求
.venv/Scripts/python.exe output/m6-single-product-canary-20261031/audit_package.py
# delivery-audit-r1.log，exit0
```

初始feature缺失红测、中途导入重名、正式job解析ValidationError、Mongo恢复报错、显式关闭红测、追加冻结红测及Mock空流失败均保留，不覆盖；逐命令收据及日志hash见私有command-receipts-r2.json和delivery-audit-r1.json。最终源码的槽前／后退出、continuation及旧共享集成不得据中途8例或169离线推断通过。

## 计账与保护

旧六流23480／16506＋唯一已消费非产品探测102／4096＝本诊断前值23582／20602，未重置。累计预算仍input1477632／output212992。新产品stream0，新本地推理0；本次真实usage没有新增项。历史精确HTTP与费用仍null；本单次未来产品的实际付费输出上界仍unknown，4096仅为请求限制，未改写旧六流超限事实。

固定产品槽仅有计划及追加代码冻结；started／settled均不存在。原48 job全暂停；旧非产品探测槽已消费，不再探测。没有正式质量、human、assistant审阅、校准、gate或proof写入。真实控制／目标库没有本包实验写入；故障测试仅随机隔离库，全部保留。

本轮138文件及历史336／597／1314保护清单逐项hash匹配；private-identity未读取。源码保护确认检索、切片、AF和prompt构造未变。未重扫现场向量、默认指针或历史run_events；不声称全库／TTL全部不变。原件、私有答案、缓存、日志、tmp均未上传或清理。

## 退出与唯一接续

**暂停在运行前置，不能执行产品调用。** 用户确认维护结束后，执行方先在新随机库补完最终源码的定向隔离集成，再执行`prepare_canary.py --mode readonly-preflight`，核精确缓存无miss、input12293、context／reference_map／受审关系与prompt全等；缺项即停。全部满足后才沿既有正式接口消费本地诊断配置、创建并执行唯一版1新版05-a job，按原handoff封存一次结果即停止。无需重问同一模型授权，不自动恢复48题，不拿纯Mock替代此硬前置。

技术实现尚未完成全部执行自验，也未由总控独立关闭。本轮没有产品答案可供归属／引用／可用性诊断；未知保持未知。M6仍5/7：04保持验收，05缺有效反馈proof，08缺有效新候选质量及阶段验收；M7不启动。旧两处输出保护及对象关系等总控关闭结论保持。
