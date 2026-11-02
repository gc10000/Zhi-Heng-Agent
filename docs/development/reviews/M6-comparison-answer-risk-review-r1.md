# M6-048风险合同与单槽账本独立复核 r1

日期：2026-11-02

复核对象：`857a4dd`基线上的048风险合同、EvaluationService准入、输出合同路由、CAS账本与本包定向测试改动。复核方独立读取了实现和测试，并在当前工作树重新运行所列验证；不把前序实现自验当作本报告证据。

## 裁定

**有界技术子项通过；风险档案整体不放行，M6质量阶段不变。**

独立关闭范围仅包括默认关闭合同的解析/路由、缺少新Git授权时在实验创建前与客户端/清单动作前失败关闭、对已消费048账户采用正确来源collection并校验冻结材料、以及新单槽CAS账本的隔离结算和不重领边界。不能据此认定授权后的完整profile已验证，更不代表模型调用获准、真实比较答案通过或M6验收。

## 独立通过项

- `ComparisonAnswer048Contract`显式限定版本、模型/SDK、非思考模式、输出字段、单次预留和累计预算；缺省关闭时不进入有效输出合同payload。解析类型虽已注册，但不能绕过风险处理器。
- 真实catalog保持`output_contract=null`。风险profile的`AUTHORIZED_GIT`为空时，service返回稳定准入拒绝且不创建experiment/slot；风险profile的直接source/manifest/client入口也拒绝。Git证据读取超时回归同样在创建前失败关闭。
- 新profile具有独立batch、slot、ledger_id及account collection。旧已消费账户检查绑定source-relation批次的snapshot、planned manifest、halt和settlement哈希，并从旧profile自己的collection读取现场；定向回归验证了collection选择和快照篡改拒绝。
- 随机隔离Mongo证明同库/分库寻址、单槽CAS并发单赢家、结算后不可重领，以及未知usage/中断转blocked；这些只证明账本机制，不证明供应商运行或实际答案质量。
- QueryRunner将比较Run正文、finish/truncation与非思考观测交由账本结算；当前未发现新增公开API、OpenAPI或默认问答策略变化。

## 仍开放的边界

1. **授权后的正向路径未验证。** 当前专属Git授权不存在，因此冻结授权清单、正向`validate_config`/`validate_runtime`和模型端点身份核验均未实际通过；也没有新的完整运行manifest。该边界保持关闭是正确行为，但不能把入口拒绝等同于风险profile全路径技术通过。
2. **真实执行与答案质量均未知。** 本轮真实stream/HTTP、本地推理和正式评测库写入为0。没有真实048比较答案，无法判断回答是否完整给出比较结论并正确区分设备上联、客户端访问、管理连接和排障检查。原文摘录不构成比较回答。
3. **正式质量任务仍缺证据。** M6-05仍缺反馈复评proof，M6-08仍缺有效候选质量与阶段证据；M6保持5/7。M6-04保持已验收，43题继续暂停，heldout 65题未运行，M7未启动。

## 本轮验证

- 9个相关单元模块：`164 passed`，1条既有Pydantic序列化警告。
- 专用账本与旧比较/source-relation隔离Mongo矩阵：`52 passed`（新账本5、旧接线47），均使用随机`m1_test_m4_`数据库名。
- OpenAPI契约：`2 passed`；`compileall app`、`git diff --check`通过。
- 集成首次启动因工作树夹具未加载根目录dotenv而缺少`MONGO_URL`，52项均在测试体前失败、没有库写入；在测试进程中静默加载仓库根配置后，同一矩阵`52 passed`。首次启动失败记录留本机`output/m6-comparison-answer-risk-review-20261102/`。

## 下一步与退出条件

本包可提交并保留为有界技术通过记录；**不创建或推断新Git授权，不登记正式实验，不派发048，也不恢复43题**。之后只有在取得独立的新专属授权、模型/端点身份与完整冻结输入后，才可先补做授权正向路径的无调用验证并由总控复核；任何真实stream仍需另行明确许可。质量问题的退出条件是新身份048产生完整比较答案并按既定完整回答目标复核，而不是通过枚举摘录或降低比较要求。

本报告不重新打开此前关闭的技术项，也未重扫真实向量库、全体历史Run或质量全库。历史usage保持`53089/30412`；reasoning、HTTP、费用及付费输出上界仍未知。
