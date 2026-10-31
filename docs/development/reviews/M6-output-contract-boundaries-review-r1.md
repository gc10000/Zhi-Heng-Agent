# M6 输出保护及唯一4096观测：总控独立复核

日期：2026-10-31，Asia/Shanghai。角色：总控独立审查，审查执行提交`aa63cf943a230976f301ec6a6e5444678762ce2d`，前一总控提交`c7448da87af0725a06df905232700a1f4adf1fcb`。执行方报告与自验只作输入，本页结论依据本轮源码审阅、重新执行的定向测试与原流重算。

## 裁定

1. **关闭实际生成份数身份缺口。** `diagnostic_total_output_v2`绑定n=1；typed、model_kwargs、extra_body与最终SDK请求中的非单份／冲突在发送前拒绝，旧显式v1不静默升级。
2. **关闭原始usage合法性／一致性及持久阻断缺口。** 在固定SDK归一化前保留异常类型与存在性；非法、矛盾或未知计量不能变成可信0／正常结算。正式job、Run遥测、账本与下一派发路径已独立连接验证。
3. **通过唯一探测的限定来源与计账核验。** 原始SSE重算为input102、含reasoning总output4096、reasoning4096、finish=length。只支持固定profile的一次经验，不支持全域硬限或旧max_tokens语义。
4. **原流可见正文确实为空。** 1267个JSON事件、1个usage事件、1个DONE；可见content为0字符，reasoning_content为15839字符。字符数不是token计量。可见token仍null，output减reasoning的算术差值不能冒充实测可见token。此次没有证明产品能给出有效答案。
5. 不再追加非产品探测，不把全域硬限证明新增为整个M6的永久退出条件。总控在既有诊断裁量范围内选择**最多一次新版05-a产品验证，显式接受该单次付费输出上界未知**；这是下一包限定授权，不是当前unknown能力被验证。当前正常合同仍拒绝unknown，未恢复48 job。

M6保持**5/7**：04保持验收；05仍待有效真实反馈proof，08仍待有效新候选质量与阶段验收。测试数、覆盖数、固定探测或单题诊断均不代替这些证据。M7未授权。

## 当前边界矩阵

| 边界 | 独立结果 | 退出／限制 |
| --- | --- | --- |
| n身份、typed／kwargs／extra_body、SDK最终wire | passed，技术关闭 | 正常单份保留，冲突在请求前拒绝；不能声称旧六流曾用n=2。 |
| 原始reasoning缺失／0／等于总量 | passed | 可选明细真正缺失不新增前置；可信总量仍可结算。 |
| 原始reasoning越总量／负数／bool／float／数字字符串 | passed，技术关闭 | 异常类型不被SDK归一化洗掉；可信总量为null，reported另存。 |
| 正式job→Run→遥测→账本→下一派发 | passed | 本轮另用实际安装SDK＋MockTransport贯通7个合法／非法用例，非法全部failed／blocked，拒绝下一begin。 |
| 缺usage、总量／alias冲突、前坏后好、累计倒退、pending／异常窗口、幂等／恢复 | passed，受影响保护保持 | 未知不能重置成0；旧合同／配置漂移不能复用成功。 |
| 固定探测来源、planned／started／wire／raw／settled、固定槽防重放 | passed，仅限定证据 | 唯一槽已经消费；本轮没有再执行真实探测。 |
| 真实网关全域硬限、旧max_tokens字段 | unknown | 不登记verified或server_hard_limit=true；单次经验不能扩张。 |
| 新版05-a的具名LAN归属与可见答案 | open，尚无新版生成 | 下一包限定一次产品验证；不改prompt、thinking、模型或预算来试答案。 |
| 同范围有效新候选、gate及反馈proof | open | 本轮不创建、不运行、不改旧分或blocked。 |

受审对象关系消费、两表12成员、54保存输入、原25题35必要单元、048双方／p30、P2、001以及其他既有关闭项保持；没有重新审阅PDF、标签或整轮检索。受审关系真实登记及新答案效果与“输入消费代码已关闭”分别记录。

## 本轮实际执行

私有证据只写全新`output/m6-output-contract-boundaries-review-20261031/`。旧探针经审阅后原样复制到新目录；探测脚本只被Mock防重放测试导入，未运行真实execute。随机Mongo均为短`m1_test_m4_or_...`／`m1_test_m4_oj_...`隔离合成库，现场保留。

| 组 | 本轮结果 | 本机证据 |
| --- | --- | --- |
| 受影响离线／契约 | 143 passed，exit0 | unit.log／unit.xml；1个预期非法float夹具Pydantic warning。 |
| 相关隔离Mongo／正式job | 52 passed，exit0 | integration.log／integration.xml。 |
| 原总控反例副本 | 17 passed，exit0 | original.log／original.xml；没有覆盖原红测。 |
| 固定探测防重放，仅Mock | 7 passed，exit0 | probe-guards.log／probe-guards.xml。 |
| 新独立连接与直接边界 | 14 passed，exit0 | joined.log／joined.xml：7个SDK原流正式job、6个总量／alias／容器异常及1个ContextVar隔离用例。 |
| 独立封存／来源／保护审计 | 2356项断言通过，exit0 | audit.py、audit.log、audit.json、audit-checks.json。 |

各组重叠，不累计为唯一总数或答案质量。准确命令、退出码与日志hash见[脱敏摘要](M6-output-contract-boundaries-review-validation-r1.json)。执行方的红测与中途失败原样保留，本轮未用修后结果替换历史失败。

本轮交付脚本首轮因未加入仓库sys.path而在导入fingerprint处失败；尚未写摘要或导航。仅修私有脚本入口后第二轮成功，失败收据与修后日志分别保留；不影响上述测试／原流审计，不隐去这次工具失败。

审计独立核Git授权blob、固定输入、稳定键、实际wire、安装包版本、调用前就绪日志hash、原SSE与SDK可见文本、封存usage、旧六流、源码／prompt及OpenAPI。当前40份相关源码、7份prompt模板和prompt构造AST保护通过；业务源码总指纹为`a2472f247a995057dab78375d60601a376e60b226a4c3b0be56ecacfb1a2a38e`。336／597／1314三份历史文件清单逐项匹配，组间重叠。

## 观测与计账

| 项 | input | 含reasoning output | 边界 |
| --- | --- | --- | --- |
| 旧六个产品诊断流 | 23480 | 16506 | 两处超过请求4096的窗口保留，未修历史账。 |
| 唯一非产品探测 | 102 | 4096 | reasoning4096已包含其中，不重复相加。 |
| 本诊断范围累计观测 | 23582 | 20602 | 不是整个项目历史总usage；累计预算1477632／212992不变。 |
| 本轮总控新增真实推理 | 0 | 0 | 无新增编码、重排、供应商或答案调用；没有正式质量写入。 |

固定slot为`m6-output-cap-4096-probe-r1`，请求键`c427e2be4c71ea1fb08f59bd5ba9a6e0ec7084db44ccc494f079e7cdefc49238`；wire SHA256为`618ee9ec84ae4323f3d888a61e9a0b42d0cfdd565bf589092e267d09b7908be6`，原流SHA256为`98e186c3f123a37251b51d91747a7cc3381681008df82d6358ef8bca1f0b0a20`。授权Git blob与`c7448da`中的固定Prompt全等。

封存slot显示1次逻辑stream、1个本机request hook及1个200 response hook，started先于请求，settled一致。本轮验证限于这条封存链；不能从本机hook证明网关内部HTTP总量或不存在任何未记录调用。精确HTTP与费用保持null。

## 下一包的明确决策

当前阻塞不是“n保护还待复审”或“再修usage”，这两项已经关闭。剩余问题是：新具名关系输入是否产生可用产品回答，以及固定4096设置在该产品输入上的实际行为。单次非产品观测全部用在reasoning，不能放行整批诊断。

采用[限定单题授权](M6-single-product-risk-authorization-r1.json)及[完整执行Prompt](../handoffs/M6-single-product-canary-r1.md)：

- 仅版1`m6-g540-05-a`，复用已审新版输入与精确缓存，最多1个新产品答案stream，不追加任何非产品探测、编码或重排。
- 新的显式单题风险准入身份，正常v2 unknown／verified分支保持；不能伪造硬限能力、临时monkeypatch门禁或直接SDK绕过正式job。
- 同一固定endpoint hash、model／SDK、n1、temperature0.1、max_completion_tokens4096、默认thinking、retries0、timeout120；不改prompt或提高预算。
- 正式路径中的最小准入接线和合成验证通过后，允许执行这一次，不需再问用户查资料／账号或手工评分。新来源binding／诊断配置只登记本题必需范围；不注册正式质量候选。
- 接受仅本次实际付费输出上界unknown；请求4096不是费用保证，取消不保证服务端停止。新／旧账分列，累计不重置，原48 job全部保持暂停。
- 该单题无论成功、失败、截断、空答或usage异常，均封存后结束本包，不自动扩大范围、不重抽。成功也只是来源诊断；随后才由总控决定旧诊断范围如何接续及新候选质量链。

这不是把“未知能力”改成“已验证能力”，也不是把批量产品授权自动延长。它以明确单次范围代替继续追求无法由有限探测证明的全域保证，并直接产生当前缺少的产品证据。

## 证据限制与交付

本轮未访问真实业务／质量库，未重扫582／867向量、原修订或默认指针；现场保护只依封存文件及hash，不宣称本轮live全库审计。没有子Agent、正式评分、attest、校准、gate、proof、heldout或默认切换。未读private-identity，未输出凭据，tmp保留。

开始只读复核本地HEAD／origin为`aa63cf9`；默认Git代理127.0.0.1:7890不可用，原命令失败后采用单命令关闭失效代理，远程main实际返回同一完整SHA，未改永久Git配置。交付只显式暂存脱敏文档，正常提交／push，最后再核本地／origin／远程；自身提交SHA与同步结果在最终回复补记，不反复amend。
