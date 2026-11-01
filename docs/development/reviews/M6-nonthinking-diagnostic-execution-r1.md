# M6显式非思考模式有界诊断执行报告 r1

日期：2026-11-01，Asia/Shanghai。角色：执行方自验及来源诊断；**待总控独立复核，不自签技术关闭或M6验收**。

## 实际结论

唯一变量为实际wire增加`enable_thinking=false`。全45成员预检通过后，按封存顺序只实际创建、执行2个新正式单题job／stream：

| 成员 | 实际行为及来源决定 | input／output | 实验／Run |
| --- | --- | --- | --- |
| 新版版1 17-b | stop、完整可见正文；具名MateDock 3、USB-C充电／不支持数据传输及实际引用3正确，执行方限定诊断通过 | 4689／198 | `2f7d2b73-5915-42ea-a171-71bd8fe7ae0b`／`74cc67e2-abde-4a44-aa51-b2f71b6d80a7` |
| 版1 048 | stop、完整正文，但把用户有线／无线访问设备的资料用作无线侧上联依据，**来源错误，首停止** | 4743／722 | `1bf2d418-af11-41c4-8c79-46a1cb9dde1d`／`6448be8e-b9a0-49a0-8201-beb7e875772f` |

新批次`m6-nonthinking-diagnostic-r1`已持久blocked，pending null、unknown_windows为空、cursor 1，两个固定槽均started／settled，来源决定分别接受／拒绝。其余43成员在指定请求、Run、checkpoint、关联、outcome和固定槽消费面均未执行；不重抽048、不换参、不继续版2。原旧批blocked、根halt、4个已消费槽以及旧44未执行身份全部只读保留，新模式不冒充旧attempt续跑或扣除旧清单。

048的正式Run／job及完整outcome仍为技术completed，来源诊断拒绝单独封存，未手改历史state或评分。故障不在输出完成性或缺同轴证据：引用4实际消费了p30 Cable／同轴／入户接口／EoC来源，LA2608的SIM及3G／4G控制器描述也有引用支持；错误是将“客户端接入设备”与“设备向运营商上联”两个关系层级混用。完整断言→选中证据→实际正文链和来源拒绝原件在私有目录，不上传答案。

## 身份与实现

起点HEAD、origin/main及实际远程均实核`0e61ada4795f495b31593ab56e9be8b857968a58`，初始工作区仅tmp/，暂存区为空。唯一授权消费该Git提交的`docs/development/reviews/M6-nonthinking-diagnostic-authorization-r1.json`原始blob，SHA256 `eb49a82f33415255a122318a82926ea6fec62e3b41290e7e3027d2fc8821388b`。

最终app源码fingerprint：`b971b22c4cb5a66e5b39695d47fa35cd15f9aeeeaa70cd067af190fdffe06925`。完整45成员manifest canonical SHA256：`4a1605fefe66219e78d5d9054bb0d42c3a45ed2be75ea29238ebbd2022ab1e5c`。两版完整150题＝85 dev＋65 heldout原字节保留；本包只运行授权dev成员，无heldout执行。各成员请求、checkpoint、配置canonical／文件hash、父来源、实验、Run、attempt及槽hash见同目录validation JSON，不以catalog文件hash代替配置canonical hash。

新增默认关闭内部合同`diagnostic_nonthinking_manifest_r1`及限定handler，严格要求显式布尔false。复用已审remaining CAS／固定槽／来源决定核心，仅增加显式profile依赖，旧调用缺省仍使用旧handler；新账户集合`diagnostic_nonthinking_accounts`跨两个原控制库共用原版1控制库中的唯一账户。新调用前只读核旧blocked账户与封存快照全等；不修改旧授权、目录或前值。

SDK归一化前独立观测raw reasoning_content，任一非空内容或任一usage片正reasoning计数阻断后续；推理内容不作为正文。旧raw usage结构、普通v2 unknown拒绝及原单题路径保持。AnswerBudget／InternalRunInput联合类型接线，OpenAPI全等，无新环境变量、全局默认或检索／prompt修改。

固定qwen3.8-flash、SDK 1.1.11／2.28.0、n1、temperature .1、stream＋usage、max_completion_tokens4096、SDK重试0、timeout120、无fallback／redirect。45份安装SDK Mock wire与对应旧wire相比仅增加false，messages全等。窗口32768、输出4096、reserve256、max_chars12000、input_limit28416及原检索、引用、分组、排序、对象关系均不变。

## 真实计量与模式限制

- 本包新增2产品stream、2正式单题job；本地编码／重排／导入、非产品探测、模型审核均0，最多1在途。
- 前值37541／28633由旧六流、探测、canary及旧批合法结算逐级hash证明，只计一次。新增9432／920，累计46973／29553；预算1477632／212992不扩大。
- 两次各一个DONE、finish stop，raw usage、Run、完整attempt、冻结outcome及共享单次结算一致。两个请求hook和两个响应hook是观察值，**精确HTTP总数仍null**，费用、visible tokens及最大付费输出上界仍null／unknown。
- 两次raw流均未观测到非空reasoning_content，reasoning_tokens明细均未提供，**保留null，不补0**。这支持本次可见答案对照，不证明当前网关／别名模型内部推理硬关闭或4096服务端硬限；能力status／semantics保持unknown，不登记verified。

## 实际验证与保留失败

| 范围 | 实际结果 | 限制 |
| --- | --- | --- |
| 最终源码相关单元／契约 | 142通过，exit0 | 1个既有非法float故障夹具Pydantic告警保留 |
| 最终源码定向隔离集成 | 110通过，exit0 | 随机短`m1_test_m4_ntf_874aa3`前缀，合成SDK流，无产品推理；覆盖新模式及受影响旧路由 |
| 首轮集成 | 82通过，exit0 | 早于省略旧版本字段兼容修正，不冒充最终源码全套 |
| 初始红测 | 3失败，exit1 | 新合同／模式捕获缺失，原日志保留 |
| 中途旧路由回归 | 132通过、10失败，exit1 | 新分支直接索引可省略版本字段；最小改为get后最终142通过，原失败保留 |
| 文件保护／前值／OpenAPI | 5262断言通过，exit0 | 字节及指定只读来源检查，不是质量分 |
| 全清单正式消费者预检 | 45通过，exit0，新增推理0 | 精确缓存无miss；prompt/context/引用/groups/budget与授权输入全等；Mock不代替真实答案 |
| 两结果技术审计 | 各28项通过 | 只证明完成性、模式观测、来源映射与计量结构，不自动接受语义 |
| 完整attempt补核 | 各4项通过 | 完整attempt结果与文件结果及正式outcome fingerprint一致 |
| 最终指定消费面及保护 | 2951断言通过，exit0 | 2已消费、43未执行、旧blocked与2891指定保护文件hash保持 |

138／336／597／1314历史保护组均匹配，有重叠，不相加成唯一总数。另保存本包2891个指定唯一文件保护集合。没有全量重扫582／867现场、旧质量全库、默认指针、TTL或历史run_events；复用旧封存hash不冒称本轮全量现场证明。未启动worker或改变Docker服务，基础5服务健康。

## 交付与唯一下一动作

私有证据：`output/m6-nonthinking-diagnostic-20261101/`。包括planned／started／settled、45输入与SDK wire、原始流及usage、正式Run／完整attempt／outcome、来源决定、最终账户、逐成员状态、红绿日志和逐题HTML。导航`逐题诊断与停止边界.html`含2个实际回答页及43个明确未执行页；tmp、历史失败、原件和缓存全部保留，不上传私有产物。

唯一下一动作由执行方承担：交总控独立复核本次原流、048来源层级错误、固定槽与计量，并仅裁定关系表达的下一有界包。本包不自行改prompt、修检索、换参数或扩大生成。

**M6仍5/7；04保持验收，05／08仍缺正式质量及真实反馈proof证据，M7未启动。** 已关闭05-a、两版047、旧05-b及既有技术结论保持；本包执行自验不冒充独立关闭。无正式候选、评分、attest、校准、gate或反馈proof，不切默认。
