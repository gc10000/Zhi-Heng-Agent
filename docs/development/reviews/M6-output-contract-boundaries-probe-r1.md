# M6 输出合同保护补修及一次4096设置探测

日期：2026-10-31，Asia/Shanghai。角色：执行方补修、自验与实际探测，不是总控独立验收。接续`c7448da87af0725a06df905232700a1f4adf1fcb`，开始HEAD＝origin/main＝远程main，工作区仅`tmp/`。依据[固定授权Prompt](../handoffs/M6-output-contract-boundaries-probe-r1.md)；历史报告不改。

## 实际结果与边界

- 两处保护已完成源码补修和定向自验，**待总控独立核验**。没有自行关闭输出合同技术审查。
- 唯一授权的非产品探测已执行：**input102、含reasoning总output4096、reasoning4096、finish=`length`**，SDK归一化前usage合法一致。分类仅为`observed_limit_4096_at_fixed_profile`。
- 该观测不是全域硬限证明，也不证明旧产品`max_tokens`字段语义；正常合同能力保持`unknown`，没有登记`verified`或`server_hard_limit=true`。`output_minus_reasoning=0`，未据此宣称已测可见token。
- 48个产品job（46答案＋2澄清）全部暂停，新05-a未执行；没有产品答案、实验、评分、attest、校准、gate或proof写入。M6保持**5/7**，04保持验收，05／08未验收，M7未启动。

## 根因及补修

### 单份生成的有效身份

修前实际安装SDK的MockTransport已复现typed `n=2`及`model_kwargs.n=2`穿过合同，实际wire生成份数改变而身份不变。这没有证明旧六流使用过n=2。

`OutputContract`升级为显式`diagnostic_total_output_v2`，严格绑定`n=1`。n进入合同、能力证明匹配及有效参数hash，后者同时绑定`usage_validation=raw_usage_v2`。拒绝typed非单份、所有诊断model_kwargs、default_query、未绑定extra_body及limit／thinking冲突；安装SDK最终payload必须符合单份ChatCompletions合同，SDK重试仍为0。

原有配置→Run→执行关联→题级检查点→恢复验证消费新身份。旧显式v1不原地升级，不能假装新配置已经执行；同ledger_id的账户键保留旧命名空间，合同变化冲突，不能借改版本重置预算。缺省null的普通客户端、旧非诊断发参和遥测结构保持。

### 原始usage不能被归一化洗掉

修前总output8、reasoning9／-1／True的正式合成job能completed且账本open；另有float／数字字符串被转成缺失。补修过程中进一步用安装SDK发现：**bool和数字字符串在LangChain之前已被OpenAI SDK强制转换**，只在LangChain层抓取不足以保留原类型。

新增仅用于显式诊断的`diagnostic_usage.py`：在固定安装SDK的SSE解码口／非流JSON响应hook捕获字段存在性、类型、安全值及容器状态，不增加请求、不改原响应。ContextVar隔离每次调用；普通客户端不安装该hook。任意嵌套非计量数据只留hash，不保存供应商任意内容或凭据。

合法reasoning为非布尔非负整数且≤含reasoning总output；缺失／null与非法明细分开，可信总量不强求reasoning。非法字段、alias／total冲突、累计倒退及前坏后好均不能被擦除。校验与reported总量沿生成节点→telemetry／Run→账本保存；非法统计的可信总量为null，reported数字单列，不以max或0伪造实付量。调用后账本blocked，正式job不能completed，下一次begin／派发拒绝。原CAS、幂等全等结算、未知窗口及累计预算保持。

生产改动仅8文件：`output_contract.py`、新增`diagnostic_usage.py`、`lm_utils.py`、`node_answer_output.py`、`query_runner.py`、`query_adapter.py`、`telemetry.py`、`events.py`。没有改prompt模板、prompt构造、检索、切片或受审对象关系代码；没有新增环境变量或公开API。

## 红绿与实际命令

新证据目录：`output/m6-output-contract-boundaries-probe-20261031/`。原探针审阅后复制到新目录运行，旧脚本、失败和证据不覆盖。准确参数列表、退出码与日志SHA见[脱敏摘要](M6-output-contract-boundaries-probe-validation-r1.json)的`commands`。

| 检查 | 实际结果 | 证据 |
| --- | --- | --- |
| 原独立输出矩阵修前 | 7失败、4通过，exit1 | `red-matrix.log` |
| 正式合成job修前 | 3失败，exit1 | `red-formal.log` |
| 新增unit修前 | 26失败、2通过，exit1 | `red-added-unit.log` |
| 最终相关离线／契约 | 143通过，exit0 | `unit-final.log` |
| 最终随机隔离Mongo／正式job集成 | 52通过，exit0 | `integration-final-r1.log` |
| 原独立探针原样副本 | 17通过，exit0 | `original-probes-final.log` |
| 私有一次探测防重放 | 7通过，exit0 | `probe-guards-r2.log` |
| 原件／prompt／源码保护和OpenAPI | 通过，exit0 | `protection-preprobe.log`及最终只读核验 |
| 同SDK实际wire Mock | 通过，新增真实推理0，exit0 | `probe-mock-command-r1.log` |
| 唯一真实探测 | 完成并封存，exit0 | `probe-execute-r1.log` |

各组有重叠，不累计为唯一测试总数或答案质量分。最终143项含一个预期Pydantic warning，来自刻意非法float夹具。

主要最终测试命令（从仓库根执行）：

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_output_contract_boundaries.py tests/unit/test_output_contract.py tests/unit/test_telemetry_provider.py tests/unit/test_provider_clients.py tests/unit/test_context_budget.py tests/contract/test_provider_capabilities.py tests/contract/test_provider_errors.py -q --tb=short
.venv/Scripts/python.exe -m pytest tests/integration/test_output_contract_boundaries.py tests/integration/test_diagnostic_output_contract.py tests/integration/test_evaluation_run_adapter.py tests/integration/test_run_telemetry.py -q --tb=short
.venv/Scripts/python.exe -m pytest output/m6-output-contract-boundaries-probe-20261031/green-original/test_output_boundary_matrix.py output/m6-output-contract-boundaries-probe-20261031/green-original/test_formal_usage_path.py output/m6-output-contract-boundaries-probe-20261031/green-original/test_extra_contract_boundaries.py -q --tb=short
.venv/Scripts/python.exe -m pytest output/m6-output-contract-boundaries-probe-20261031/test_probe_guards.py -q --tb=short
```

保留中途失败：unit首轮10失败／72通过（SDK的n缺省None、离线根别名替身）；第二轮2失败／80通过（发现SDK先归一化）；integration首轮10失败／26通过（事件层丢可选遥测、旧cap合成夹具明细自相矛盾）；私有防重放夹具首轮2失败／5通过（把httpx类替成函数导致类型检查失败）。旧cap夹具仅把reasoning改为与各自总量一致，异常明细另设矩阵；没有修改旧六流或弱化正式门禁。全部红测及中途日志原样保留。

## 单次探测身份、观测与账

授权Git blob：commit `c7448da87af0725a06df905232700a1f4adf1fcb`、`M6-output-contract-boundaries-probe-r1.md`，blob SHA256为`723b609510fba414c643def17c9245dfb27f746fdfa71a6d3c372628e4f0dc41`。

| 身份 | 固定值 |
| --- | --- |
| slot | `m6-output-cap-4096-probe-r1` |
| 请求键 | `c427e2be4c71ea1fb08f59bd5ba9a6e0ec7084db44ccc494f079e7cdefc49238` |
| 实际wire SHA256 | `618ee9ec84ae4323f3d888a61e9a0b42d0cfdd565bf589092e267d09b7908be6` |
| endpoint SHA256 | `7cbf2306d7facc55fd08ea52e1d6891e0dc6bc6af6d5442df34f17403670ad2a` |
| model／SDK | qwen3.8-flash／langchain-openai1.1.11／openai2.28.0 |
| 生成配置 | extra_body.max_completion_tokens4096；不带max_tokens；n1；temperature0.1；stream＋usage |
| thinking／重试 | 无新增thinking或budget参数；timeout120；max_retries0；无fallback／redirect |
| 输入 | 授权的1至10000整数长输出固定字符串；UTF-8 SHA256 `fdad8bfe72f3c5d6b70f3432966e530a4f268727b5a761a9787668c33b0aaca9` |
| 输入预算 | 保守441≤预留1024；输出付费硬上界unknown，授权接受仅本次风险 |

调用前已封存源码、测试日志及同SDK Mock的精确wire。固定目录`output/m6-authorized-probes/m6-output-cap-4096-probe-r1/`使用原子独占和fsync的planned／started，started后才联网；started未结算禁止重试，已settled只读复用。该slot现在已消费，不可通过换key／目录／nonce再领一次。产品OutputContract的unknown拒绝分支没有放开。

实际耗时约67.05秒；观测1个逻辑stream、1次本机request hook／1次200 response hook。hook不等于可观测网关内部HTTP总量，精确HTTP及费用均null。原流SHA256为`98e186c3f123a37251b51d91747a7cc3381681008df82d6358ef8bca1f0b0a20`；完整请求、原始响应字节、SDK分片、finish_reason及原始usage仅存本机。

| 账目 | input | 含reasoning output | 身份 |
| --- | --- | --- | --- |
| 旧六流 | 23480 | 16506 | 原产品诊断；两处超4096窗口保持，不改旧账 |
| 本次 | 102 | 4096 | 唯一非产品设置探测；reasoning4096不重复相加 |
| 累计观测 | 23582 | 20602 | 累计上限仍1477632／212992，未扩大 |

本次usage无未知窗口，合法计量已封存；固定槽防重放仍保留。不能从本次已知usage反推过去HTTP／费用，也不能将本次观测写成正式产品能力声明。

## 保护、交接及下一条动作

336／597／1314三份本机历史清单逐文件hash匹配，私人身份文件未读取。额外确认40份相关源码及全部跟踪prompt模板未改变，prompt构造AST全等，OpenAPI导出一致；未重跑已关闭54输入审查。没有重新扫描live向量、867旧切片或默认指针，不把文件审计扩大成现场全库审计。

测试故障写入仅随机短`m1_test_m4_oc_...`隔离命名空间，测试库留存；真实控制库／业务库未访问。旧r3的19继承＋66执行、旧failed／attempt2及未知调用费用、原分及两版blocked全部保持。`tmp/`、output、evals、原件、缓存、日志及历史失败不清理不上传。

回切移除新诊断合同／设null并使用新请求身份；已启用v2 Run不能交旧消费者继续执行。需要源码回切时正常反向提交，不重写历史，不删除账本或原索引；不迁移旧合同为新成功结果。

**下一条动作由总控承担定向核验本包两处保护和一次固定观测，再裁定适用网关合同及下一次产品调用的精确身份／预算／未知上界风险范围。** 现有一次经验不足以自动满足正式硬限合同；不得再次探测或自动恢复48 job。后续若获新的产品执行授权，使用新身份与来源，不能复用旧六Run伪装新答案。无需用户重找PDF、查账号或补评分；05的有效反馈proof、08的新候选质量及阶段验收仍未完成。

只提交源码、合成测试、配置注释及脱敏文档；提交／推送结果由本轮最终交接补记，不为写入自身SHA反复amend。
