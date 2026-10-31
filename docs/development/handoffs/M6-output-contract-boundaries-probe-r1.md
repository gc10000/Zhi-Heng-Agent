# 执行Prompt：输出合同两项保护补修与一次4096设置探测

你是执行修复方；总控独立验收由另一会话承担。仓库`D:\Desktop\AnXin\ansen_code\Product-Knowledge-Rag`，Windows／PowerShell，2026-10-31，Asia/Shanghai。先读适用AGENTS、PROGRESS、REVIEW_STATUS、TODO、M6任务、contracts和GIT_WORKFLOW，确认HEAD／工作区／origin／远程；有新提交先核差异，不回退。

权威审查对象`739ee439e75f91377359759e6e299c2081b25b13`；先读`docs/development/reviews/M6-diagnostic-subject-usage-fix-review-r1.md`及validation JSON，证据在`output/m6-diagnostic-subject-usage-fix-review-20261031/`。上一执行报告`M6-diagnostic-subject-usage-fix-r1.md`及摘要保留。

## 已关闭与本包边界

受审对象关系消费、12成员、54输入回放／原25题35单元已总控独立通过并关闭。LAN归MateDock3、RJ45机身独立、LAN旧unknown与表级p14分开。不要再找PDF、重审语义、重建账号／001或重跑检索／编码／重排；不重开P2、p30、组合与恢复协议。

本包业务修复只限同一输出合同剩余两处：**实际wire的生成份数身份**与**usage原始合法性／一致性及结算阻断**。保留已通过的unknown门禁／累计预算／CAS／恢复路径。M6 5/7、04已验收保持，05／08未验收，M7不启动。

本包允许上述必要源码、合成测试、配置及契约／文档更新。真实模型预算只有下文一个非产品探测，且必须修复验证后执行；**不恢复48job、不重跑05-a、不生成任何产品答案、不开正式候选／评分／attest／校准／gate／proof**。不开子Agent。不读private-identity、不输出.env值／端点／凭据；tmp保留；旧Run／state／lease／slot／retryable、原分与blocked不改。

## A．一次补齐有效wire身份

当前`OutputContract.identity()`只hash限额／thinking及SDK重试。独立实际安装SDK＋MockTransport已证实：typed n=2及model_kwargs.n=2可穿过strict_options，以n=2上wire，hash却与n=1相同。该反例没有证明旧真实六流用过n=2，不改旧账。

本诊断限定实际单份生成n=1，须进入能力／生效参数身份；在typed、model_kwargs、extra_body等有效入口上统一核验，拒绝覆盖／冲突及影响生成份数或限额语义的未绑定参数。不是只检查一个字段或silent覆盖n=1。利用安装客户端有效参数／最终请求的确定规则落实，不新增一套通用供应商框架或公开API。关闭新合同的旧非诊断路径等值。

模型、端点hash、客户端版本、limit字段、thinking／预算、n及有效发参hash进入新配置、Run、执行关联、检查点和恢复核验；漂移拒绝。旧合同／旧Run不能被原地补字段，使用显式新身份，相关缓存／旧成功检查点不得假装新配置执行过。未变的原件／向量／分数继续精确复用。

## B．把非法／矛盾明细与真正缺失分开

独立矩阵已证实总output=8时reasoning=9、-1、True、9.5、'9'仍放行；reasoning提取会先把部分坏值擦成None。正式合成job再证9／-1／True均completed且账本open，不是私有函数假设。

先保留安全的原始字段存在性、类型／值及校验结果，再生成规范收据。合法reasoning存在时必须为非布尔非负整数且≤含reasoning总output；显式矛盾或非法不能洗成None／0后放行。正常reasoning缺失不新增为业务前置：有足够证据可信的总量仍可按合同结算。对未知总量、矛盾、异常原流、空值与上游已归一化信息缺失逐层区分，不能为了过测试改写原流或旧usage。

非法／矛盾必须持久阻断并保留原因；不把未知实付量写0或凭max(total,reasoning)补造。总量未知与已知下界分开。校验结果沿step_3→telemetry／Run→OutputLedger→正式job及恢复可追溯，拒绝后续begin／dispatch；同一结算重放幂等、改变收据拒绝，CAS不放宽。保留历史23480／16506及两处原超4096窗口，不回填旧六流。

## C．固定直接边界矩阵，红绿后才可探测

总控脚本会写新文件，先审阅再复制到全新output目录，不原地重跑。把合成反例落实为仓库测试，不把私有原件／真实prompt写入tests。

| 矩阵 | 必须结果 |
| --- | --- |
| n=1／typed n=2／model_kwargs.n=2及冲突入口 | 正常单份通过；非单份或冲突在真实请求前拒绝，身份不能相同。安装SDK Mock记录实际wire。 |
| reasoning缺失／0／等于total | 可信总量语义下正常通过，非空明细不增加实际output。 |
| reasoning>total／负数／bool／浮点／数字字符串 | 原始异常保留，调用后账本blocked且拒绝下一题。 |
| 正式job三例reasoning=9／-1／True、total8 | 实验不得completed假通过，异常校验不可在中间层丢失。 |
| 原cap、缺总usage、超限、超时／中断／pending、累计、重复结算、CAS | 既有保护保持；不把count或费用未知写0，不自动重试。 |
| 关闭／回切、创建关联崩溃、同分库、成功复用、continuation与参数漂移 | 旧路径等值，新身份受控拒绝漂移，不跨配置继承答案。 |

先复现保留红测，再实现。运行上述新增矩阵和受影响的output_contract／provider／telemetry／diagnostic_output_contract相关测试；只有改动触及其他边界时才扩相应回归，不机械重跑全部M6或对象关系审查。若改动影响prompt／证据，再做受影响零推理回放；否则只核来源保护hash，不重做已关闭的54输入整轮。

任一修复矩阵／相关回归未通过，**停止探测**，新增真实推理0；把完整失败矩阵交总控，不靠追加调用掩盖代码故障。

## D．一次非产品网关设置探测：明确有限授权

旧`A／max_completion_tokens=64`提案本轮不采用；它未触及4096，且自然短答无法区分忽略限额与正确限额。替换为以下**最多一次逻辑stream**，不为任意后续试词／改字段留余地。

固定授权槽：`m6-output-cap-4096-probe-r1`。适用endpoint SHA=`7cbf2306d7facc55fd08ea52e1d6891e0dc6bc6af6d5442df34f17403670ad2a`；model=`qwen3.8-flash`；langchain-openai=`1.1.11`、openai=`2.28.0`。任何实际身份改变均停止，不把授权迁移到其他服务或模型。

固定输入（只此字符串，UTF-8）：

```text
Print the integers from 1 through 10000, in order, separated by single spaces. Start immediately. Do not use ellipses, skip values, explain, or stop early.
```

固定候选field=`max_completion_tokens`，以extra_body透传4096，禁止同时带max_tokens；n=1，stream且请求usage；thinking保持网关默认，不新增开关／thinking_budget／reasoning_effort，不切模型。其他当前冻结runtime不随意变化，保存实际有效参数hash。SDK max_retries=0，timeout120秒；不预热、不卡后再试、不fallback、不增加第二字段试验。

输入预留1024 token；固定短输入及消息封装先按既有保守计数核验，超出则停止。请求输出限制4096是**待测参数，不是已保证的付费上界**；实际最大付费输出目前unknown，精确费用／HTTP未观测保持null。本授权明确接受仅此一次能力诊断的该未知上界风险，不修改原52产品答案授权或自动挪用其剩余stream。probe实际usage计入总调用账并与原六流分列，原累计输出212992／输入1477632不扩大；探测若越界／未知即停止，不继续消耗余量。

调用前封存本授权Git来源／blob hash、slot、完整输入与wire hash、endpoint hash、model／SDK／timeout、请求稳定键、历史与本次预算。稳定键必须包括所有以上身份及版本；同时用**固定授权槽**防止改nonce／key／目录再领一次。以原子独占＋fsync保存planned／started，started持久化后才发请求。任何进程已started而未结算，不自动重试或重新创建；completed只读复用。保留全部中间失败，不删除pending。

这是专门授权的能力诊断，不是产品QueryRunner答案：可使用受控私有探测脚本及相同安装SDK发送这一个请求，不创建业务Run／评分，也**不修改正常OutputContract的unknown拒绝分支**来开后门。不要借此写verified、server_hard_limit=true或替换正式配置。新建专用客户端，不修改进程全局缓存或默认配置；发请求前先用Mock证明真实wire n／字段／thinking／重试与封存全等。

保存原始请求（凭据仅运行时使用，不能写入产物）、所有原始响应分片、finish_reason、usage原始字段、reasoning、原流hash、实际新增逻辑调用、可观测HTTP与错误。总usage与reasoning不相加；部分流没有完整usage时保留null和可证下界，不用字符数充token。客户端超时／取消不保证服务端不继续计费，照实保留unknown，不补跑。

## E．一次固定结果分类及退出

- 参数拒绝／明确不支持：该设置失败，保留原响应脱敏码；不自动回落max_tokens。
- 含reasoning总output>4096：该请求限额未生效，失败；不提高预算。
- 先自然stop且未触及边界：inconclusive，不因短答未超就声称cap有效，不再换输入重跑。
- 到达4096边界、finish_reason对应限额且usage合法一致：记录`observed_limit_4096_at_fixed_profile`，仅本固定设置一次经验；不伪装全域服务端硬保证或自动登记verified。
- 超时／中断／缺usage／矛盾字段：unknown／invalid，停止并保存未结算窗口。

以上任一结果都不自动恢复48job或生成新版05-a。若没有适用服务合同、证据仍不足，交付明确的供应商能力／风险范围选择，不开展无界探测循环，不要求用户找账号／PDF／评分。下一真实产品答案接续仍由总控核精确来源／身份／预算与证据后裁定，不能复用旧六Run伪装新答案。

## 交付

全新output目录保留原失败、红绿、矩阵、受控探测前置／账／原流、保护hash及剩余48未执行列表。生成脱敏报告／JSON，分开：代码自验、真实探测观测、能力unknown、答案效果未验证、独立验收pending；不得以测试数或一次探测冒充质量。

维护PROGRESS、REVIEW_STATUS、TODO、M6任务、contracts、CHANGELOG、DECISIONS，保留历史。只显式暂存业务源码、合成测试及脱敏文档，普通commit／push并核本地／origin／远程；原件、缓存、完整流、日志和private-identity不上传。故障写库仅随机短`m1_test_m4_`合成库。M6仍5/7，04保持，05／08未验收，M7未授权。
