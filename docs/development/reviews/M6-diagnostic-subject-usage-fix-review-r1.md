# M6 对象关系与输出合同补修：总控独立复核 r1

日期：2026-10-31，Asia/Shanghai。审查对象：`739ee439e75f91377359759e6e299c2081b25b13`。本轮实际确认HEAD＝origin/main＝远程main，开始仅`tmp/`，不是复述执行回执。

角色：独立审查方；本轮只改脱敏文档，不实现业务修复、不运行真实模型或产品答案。私有证据在全新`output/m6-diagnostic-subject-usage-fix-review-20261031/`。原始失败、旧分、旧blocked及既有技术关闭保持。

## 一次性裁定矩阵

| 范围 | 独立裁定 | 证据与退出边界 |
| --- | --- | --- |
| 受审对象关系消费 | **passed，技术子项关闭** | 从原件／缓存／冻结载荷重新编译12成员binding，与执行封存全等；正式授权／输入／Run／检查点／continuation的相关隔离回归通过。LAN具名MateDock3与机身RJ45分开，LAN行unknown未改。不是已登记真实binding或新答案质量通过。 |
| 54保存输入及原25题保护 | **passed，保存输入子项关闭** | 审阅旧脚本后只改新输出／输入路径，重新走正式消费者；54份结果逐项全等，52答案prompt中20变化、32不变，2澄清为缓存复用；原25题35必要单元仍在，048双方及p30保留。不是54次真实job或新检索。 |
| 输出合同既有正常路径 | **passed，保留** | unknown调用前拒绝、缺总usage／超限／中断／累计额度／CAS／同分库／恢复及缺省旧路径回归通过，不整体推翻。 |
| 输出合同：有效wire身份 | **open，同一输出合同剩余边界A** | 实际安装SDK＋MockTransport证明n=1与n=2共用合同及生效参数hash，strict_options允许n=2发出；typed n及model_kwargs覆盖均可达。须固定单份生成及全部影响生成份数的参数，拒绝冲突／漂移。 |
| 输出合同：usage一致性 | **open，同一输出合同剩余边界B** | output=8、reasoning=9仍结算open且可begin下一题；非法负数／布尔／小数／字符串被归一成None也放行。正式合成job进一步复现9／-1／True三例全部completed、账本open。须保留非法／矛盾事实并阻断，不能把坏值洗成缺失。 |
| 实际网关4096能力 | **unknown** | 本轮无真实探测，无新适用网关合同。上包A／64提案未执行；它既未触及4096，也可能只是自然短答，不能作放行证据。 |
| 余48产品job／新05-a | **继续暂停** | 本轮不放行。下一包可先修两项输出保护，再按限定授权做一次非产品4096设置探测；其结果不自动授权答案或证明全域硬限。 |

M6核心仍**5/7**：04已验收保持，05待有效服务端反馈复评proof，08待有效新候选质量链与阶段验收。M7不启动。几何P2、p30、001、检索组合及既有恢复关闭项不重开；来源消费关闭后，不再让执行方重找PDF或重做两表语义审阅。

## A：有效参数hash没有覆盖生成份数

位置：`app/infrastructure/providers/output_contract.py`的`identity()`与`strict_options()`（当前约56、103、119行）。identity只列extra_body限额／thinking和SDK重试；strict_options未检查实际客户端n，也未拒绝model_kwargs.n。

本轮用同一合成能力证明、同一endpoint／model／SDK和4096合同，实际安装的ChatOpenAI以MockTransport记录请求：

| 直接边界 | 实际wire n | 严格入口拒绝 | 结果 |
| --- | ---: | --- | --- |
| n=1正常对照 | 1 | 否 | passed |
| 客户端typed n=2 | 2 | 否 | failed |
| typed n=1、model_kwargs.n=2 | 2 | 否 | failed |

三者的`output_parameters_sha256`相同。证明的是**参数漂移未进身份也未被拒绝**；没有证明过去真实六流使用过n=2，亦未声称真实网关已因此超支。Mock只替代远端响应，实际本机SDK构造／序列化路径没有替代。

修复限定为本诊断的单份生成合同：实际n=1须可验证、计入生效身份；typed、model_kwargs、extra_body等入口不能覆盖它。其他会改变生成份数或限制语义的未知参数须拒绝或有明确绑定，不能只再添一个局部if。旧非诊断路径等值，不借机重构全部供应商框架。

## B：矛盾usage可沿正式路径结算为正常

位置：`output_contract.py`的`usage_receipt()`／`OutputLedger.settle()`（约138、198、201行）；`node_answer_output.py`的reasoning提取（约97—101行）。

`known`只检查input／output有数；`good`不核reasoning是否为合法的总量子集。reasoning>output时只把差值置None；负数、布尔、小数和字符串在提取或归一化时变None，失去“供应商提供了非法明细”的事实。

独立11例矩阵：**7 failed／4 passed，exit 1**。其中wire两例失败；usage五例失败（9、-1、True、9.5、'9'，总output固定8）；None、0、8及单份wire四个对照通过。缺reasoning本身不新增为阻塞前置：在已有可信总量语义下，明细缺失与明细非法要区分。

另走正式EvaluationService→execute_job→QueryRunner→安装的业务结算路径，用随机隔离Mongo和合成stream验证reasoning=9／-1／True三例；**3 failed，exit 1**，实际实验completed／账本open。不是仅调用私有辅助函数的假设，也没有真实供应商或业务库写入。

这些反例不改写旧六流账；旧23480／16506及其明细仍保留。下一包须保存原始异常与安全校验状态，可信总量不足时新增总量仍unknown、已知下界另存；不把非法明细改0、改None后继续，也不凭max(reasoning,total)补造实付量。单次结算幂等、CAS、原始异常、下一题拒绝应集中修完。

## 实际运行与证据限制

- 同一相关离线／契约命令：**184 passed，20.74s**；含OpenAPI一致性。
- 同一四组随机隔离Mongo集成：**68 passed，106.28s**；短`m1_test_m4_`前缀，保留现场。
- 审阅并适配到新目录的正式消费者回放：54请求，20变化；另25题／35单元保护通过。
- 独立审计：**2045项通过**，包括执行产物hash、597／1314文件清单、原件／缓存／冻结582载荷、两表重编译、54逐项及25保护结果全等、源码身份及unknown拒绝。
- 新增完整输出矩阵：**7 failed／4 passed**；正式usage补证：**3 failed**。最初3例探针的2 failed／1 passed亦保留，各组重叠，绝不相加成质量分或独立唯一总数。

本轮真实业务状态只读：没有访问真实质量库，没有重新扫描live582／867／67资产或默认指针；582指封存载荷，不是live扫描。数据库写入只在随机合成测试库；所有模型响应均Mock／合成，真实编码／重排／供应商／答案／评分／校准／proof／子Agent新增0。业务源码与执行提交一致。

## 下一包：两项保护补修＋最多一次适用设置探测

完整执行指令见[输出合同限定补修与一次4096探测](../handoffs/M6-output-contract-boundaries-probe-r1.md)。下一包不重复对象关系、检索、账号、原件审阅或旧基线／评分流程。

**不采用旧A／64提案作为退出探测。** 改为一个全新、非产品、明显长于限额的固定输入；相同endpoint hash／model／SDK，`n=1`，`extra_body.max_completion_tokens=4096`，保留网关默认thinking，无fallback、无重试，stream usage；最多一次、timeout120秒。必须先完成两项保护的红绿与相关回归；失败则本包新真实调用仍0。

授权仅此一次能力诊断，**明确接受其真实付费输出上界尚未知**，不把“请求4096”写成保证；HTTP／费用未观测保持null。它不属于产品答案、不创建质量Run，不改正常入口unknown拒绝，也不提供第二个字段或第二次试词机会。本轮未执行。此为已授权开发范围内由总控作出的有限探测裁定，不是M6新增验收门槛。

结果分类一次固定：参数拒绝／输出>4096＝该设置未通过；自然提前停止＝不充分；到达4096边界且含reasoning总usage一致＝该固定设置的一次经验。任何单次未超都不能自动声称全域服务端硬保证、登记verified／server_hard_limit=true或恢复48job。若能力仍不足，停止并交付**适用网关合同或明确风险／配置范围决策**，不再开展无停止条件探测循环。
