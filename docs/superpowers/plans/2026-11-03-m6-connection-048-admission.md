# M6连接模式单题风险准入实施计划

> 执行方式：当前总控顺序实施，采用superpowers:executing-plans。用户已要求直接实施、自行审阅取舍；不新增委派或设计确认环节。

**目标：**补齐connection_comparison_v1的专属单题风险接线及可实际消费的默认关闭catalog，所有验证零真实调用。

**方案：**沿用已受审的RemainingLedger/NonthinkingLedger的CAS生命周期；新增独立profile和合同类型，不能从旧r7/r8版本继承授权。静态catalog预检与派发授权分开：前者只读既有冻结文件，写新私有目录，后者必须有新的固定Git授权和精确prompt锚，本包AUTHORIZED_GIT保持None。保存输入333投影不充作582全scope预检。

**依据：**[既定方案](../../development/handoffs/M6-connection-comparison-048-proposal-r1.md)。Windows/PowerShell、Pydantic、Mongo；无API/环境变量新增。

## 全局边界

- batch/ledger `m6-connection-comparison-048-r1`；slot `m6-connection-comparison-048-r1-support-v1-048`；合同版本`diagnostic_connection_comparison_048_v1`；单题support-v1-048。
- 既定32768/4096/256/12000/10预算；历史56239/30516，累计预算上界84655/34612；网关和费用上限unknown；SDK不重试、n=1、不思考、失败停止。
- 题集150行、85 dev/65 heldout保持，仅选择原048，未运行其他题；新账户/请求/检查点身份不复用旧槽。M6 5/7及04/05/08证据边界不变。
- 不修改已独立通过的比较器、来源装配器、renderer；若新缺陷确实影响它们另记受影响边界。

## 任务1：合同与正式接线

文件：output_contract.py、evaluation/service.py、runs/models.py（如联合类型需要）、query_runner.py；新增connection_comparison_048_risk.py、test_connection_048_admission.py。

- [x] 先写并运行红测：关闭合同无伪授权可序列化；开启须新固定slot/path；旧合同不得借给新模式，新合同不得借给旧模式；未授权service在repo.create前422，require/client/manifest不能产生副作用。
- [x] 新合同验证固定模型/SDK/预算/历史来源；新profile默认AUTHORIZED_GIT=None，来源函数先拒绝；只复用生命周期实现，使用独立collection/version/key。
- [x] 新service按消费者模式配对合同版本；新合同进入受控账本路由及product_state/observed_reasoning结算分支；旧模式行为回归。

## 任务2：来源、授权与账本故障矩阵

文件：新profile、unit/integration定向测试。

- [x] 来源读取绑定已保存r8配置文件hash、已签技术报告Git hash和累计usage来源；未来新Git授权必须接受费用未知、唯一048及精确输入，不将本任务授权当调用许可。
- [x] 同/分库仅隔离合成：唯一预留、并发竞争、重复结算、未知usage/断流/异常stop、拒绝review/halt、后续重领拒绝、旧账户不写。
- [x] 缺授权/错配置/问题或prompt漂移/缺输入锚在相应边界拒绝，无额外调用；来源语境/比较证明继续使用已关闭恢复协议。

## 任务3：实际catalog静态预检与交付

文件：app/evaluation/connection_048_preflight.py、scripts/verification/prepare_m6_connection_048.py、定向测试及开发导航。

- [x] 只读已冻结原catalog/config/dataset/manifest和技术/usage证据，复制完整题集及四资料582成员快照；唯一改变既定生成包和新身份/源码版本/关闭风险合同。
- [x] 在方案给定绝对目录排他创建catalog与独立execution目录；实际EvaluationCatalog.resolve、策略/目标/成员/预算/快照核验通过；不构造客户端、不访问真实库、不读取private-identity或.env。
- [x] 明确静态预检passed与dispatch blocked/no authorization；精确生产prompt需将来全scope实际装配后冻结，当前不使用333投影补签。
- [x] 保存脱敏实现报告/摘要/记录，更新导航；显式暂存、提交、普通push当前分支，核本地/origin/实际远程；main/tmp保留。

实施完成自验，独立审查及真实质量仍open；结果见[M6-connection-048-admission-r1](../../development/reviews/M6-connection-048-admission-r1.md)。预检文件首次未观察红测的限制已明确记录，不补造历史。
