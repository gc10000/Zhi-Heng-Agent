# M6连接048授权引用与输入顺序补充变更独立复核

2026-11-03，审查基点`7c1288a8fc3248d34703e4cc66ddbf3fde28cdae`，最终HEAD `a7218da427a8fe36bba3f34dae90667f479d41a5`。用户明确授权后，由未参与实现的原独立审查Agent定向核验`b8b611d/5a73e3e`的授权引用加载与LF属性，以及`a7218da`的freezer产品展示顺序。未再委派，未改业务源码、已有测试、项目index/HEAD，未提交或推送；父级仅另有导航/说明文档更新。

**独立技术结论：通过，限以下实际验证边界。** 未发现新增且未关闭的业务缺陷。原独立报告及三算法关闭结论保持；此结论不授权再次派发048，不签真实答案质量或M6阶段验收。

## 两项变更的独立结论

`load_authorization_reference`只从固定路径读取GitEvidence引用，严格比较工作树引用与HEAD中的原字节，并限定本次专属授权正文路径。独立临时Git仓库实际创建提交、检出及消费证据，核缺失、未提交、脏字节、CRLF漂移、旧路径、畸形JSON均在相应边界拒绝；正文hash不匹配及不存在的commit由真实GitEvidence消费者拒绝。正向使用实际Git、实际hash验证，未仅mock一个git成功返回。`core.autocrlf=true`下实际`checkout-index`验证`.gitattributes`保留LF，当前真实引用及授权正文的Git字节亦核验通过。临时仓库仅属合成测试，未在项目仓库创建新授权或提交。

新profile的引用在模块导入时冻结为`AUTHORIZED_GIT`；已加载常量不会随文件热改更新，显式重新加载函数则会检查漂移。独立新模块导入分别核有效、缺失、脏引用：有效载入，缺失关闭，脏引用抛错。新进程默认`create_app()`不提前导入该可选048 profile，故该引用不牵连默认启动路径。这里验证的是部署时加载约束，没有新增“热撤销”承诺；切换引用需重启相应执行进程，停止仍由固定批次halt及账本约束。该边界已由父级同步配置说明。

freezer现在按原题`product_names`映射到本轮selected产品，再追加本轮新增产品；比较身份仍保留selected顺序。与正式adapter建立输入产品快照、QueryRunner优先按输入快照展示产品的行为一致。新增全链14例都显式将题名顺序设置成实际selected顺序的反向，并在模型wire处核精确prompt全等，避免只拿第二份离线渲染自证。保存真实失败Run的输入顺序也独立重算，r5字节与之匹配。

## 独立实际验证

| 检查 | 实际结果与覆盖 |
| --- | --- |
| 最终离线/契约 | **148 passed**，0失败/错误/跳过；包括新增真实Git/模块导入14项、r5保存输入审计4项，以及已有授权、合同、清单、完整输入、wire和OpenAPI回归 |
| 最终隔离Mongo矩阵 | **90 passed**，0失败/错误/跳过；包含下述新增14项完整链和76项既有新风险/连接job、输入持久化、恢复/结束边界 |
| 新完整链 | **14项已计入90**：同/分库各7场景，正常后review(false)、正常后review(true)、非法选择、异常finish、usage缺失、输入锚写失败和SDK流读取中断；每例均检查恢复零新增stream、唯一风险Run及旧合成账户未变 |
| 首条完整链 | 夹具完善后先实际1 passed，再扩为最终矩阵；与最终14重叠，不另加数量 |

新增完整链实际贯通：临时Git引用加载→真实GitEvidence/SHA→专属`sources`→完整`build_manifest/prepare_manifest`→真实EvaluationService登记→正式job/adapter/QueryRunner与execution link→调用前独立输入锚→实际安装SDK的内存模拟stream→专属账本结算→review/halt→重新建立实验观察同一成功/失败Run、无再次调用。专属`validate_config/validate_runtime/validate_previous_account/validate_prompt/validate_client`只包调用计数，内部仍执行原实现，未以空函数放行。

正向模型传输回调在输出前实际核输入锚与当前prompt state匹配、Run身份匹配、账户pending及started文件存在；正常完成后再从完整Run核持久输入hash。正常review(true)的合成出口核cursor已推进到1，再halt；该“接受”仅是测试状态决定，不是质量评分。预留后故障均保留唯一额度并blocked，输入锚写失败则0stream、无账户/预留/结算，不伪造receipt，另封存halt。所有场景恢复时账户及旧合成r8账户不变。

为取得实际确定性检索的种子/计划，每个新增全链用例先做一次独立的合成baseline正式Run，在prompt构造处主动停止，模型调用0；之后采用新题集版本及风险配置运行唯一风险Run。测试断言的是风险Run唯一，并未隐藏这份独立baseline失败记录。合成完整题集150题、85 dev/65 heldout，只选择support-v1-048；不执行其他题。

## 替换端口与证据限制

真实Mongo仅限随机短`m1_test_m4_`合成库；没有删除库或集合。使用上轮已审`checks.py --mongo`作为用户允许的静默配置入口，仅为隔离测试消费MONGO_URL，不打印连接串；新增探针不直接读取凭据，不访问private-identity。

GitEvidence、SHA及授权消费者保留，只把合成commit的底层`git show`寻址到实际临时仓库。技术/usage报告、固定来源配置、旧blocked账户和receipt是明确的合成数据。全链采用2资料3载荷；真实保存的4资料582成员由另4项离线审计覆盖，不能说90例都执行582来源的完整真实检索。资源工厂注入合成knowledge/index/originals/embedder/ranker，正式adapter、corpus校验、服务、job、Run、link和持久化仍运行；没有初始化真实模型或核新权重。

模型使用实际安装的preserving ChatOpenAI/openai及httpx.MockTransport，发送合成key和synthetic.invalid地址，没有网络模型传输。后预留场景各观察1次内存stream，输入锚失败场景0；这不能推断未来真实HTTP精确次数、网关硬限或费用。返回空选择协议由既有确定性程序渲染，未冒称模型给出真实完整比较或真实质量proof。

## 夹具失败历史

独立探针构造阶段三次失败均保留，不写成生产缺陷或产品红测：

1. `full-first`：选定的合成题名顺序恰好与selected一致，逆序条件断言失败；改为按实际selected反转题名。
2. `full-first-r2`：把50题改为150题仍登记同一set/version，被正式服务正确409拒绝；改为新合成题集版本。
3. `full-first-r3`：模型回调直接对尚未完成、未持久比较proof字段的Run计算完整输入身份，断言抛错；改为模型前按实际state核独立输入记录，完成后按完整Run核验。

调整后`full-first-r4`1通过，最终完整矩阵14通过。另有初始真实Git10项、离线146项通过，扩充后为14/148；均与最终有重叠，不累计。只有一条既有Pydantic浮点usage序列化警告。XML/log、可复跑探针及各文件hash在`output/m6-connection-048-supplement-independent-review-20261103-r1/`，同名JSON逐一列出`validation_artifacts`，不以实现侧自验补充独立数字。

## 完整保存输入与原失败保护

当前关闭候选为`output/m6-connection-comparison-048-input-r5/`。独立执行完整anchor重装配、582成员全等、4资料冻结scope、10份上下文及连续引用1–10、10340/28416且无省略、当前code/prompt身份和实际catalog预检。保存真实失败Run的context/引用/装配与r5一致；按该Run输入快照顺序构造的prompt字节及独立`comparison_generation_inputs`记录hash均与r5匹配。保存失败Run/输入记录/根因/停止摘要均按执行报告记录hash核对，未查询真实业务库或重签记录。

- 当前代码指纹：`765f62502e3aef14016567547ec164ab961aebadc0370d4a751f22761d245ef9`。
- r5 anchor SHA256：`0ef711349aac0628e89051a7b7eed9a61d265f873d2a3886763b171d1bcf62ef`。
- prompt SHA256：`dd72ee38868e3b0780d5fcc670ecad3f01e10aebb4a004bd85884c69f099b225`。
- result SHA256：`32a301571bb1f670ada85bbc2298baa45fbdb4cd84c79e13efe95f0d4ccde5ec`。

旧授权无法消费修后候选；本地本批halt保持，started/settled仍不存在。当前授权引用非None是此前已提交、已首失败封存的r1引用，不是本轮新调用许可。未重试正式失败、解锁账户、换槽、创建新正式授权或进行真实模型调用。原独立JSON与三算法hash保持，最终报告绑定同名JSON `final_candidate`的15个文件原字节hash。

本轮未新增provider、本地推理、真实业务库读写或现场标量查询。未新核真实账户/Milvus/vector现场、模型权重/runtime、真实付费wire或答案质量。归档实际累计仍56239/30516，精确HTTP/费用/reasoning明细null、硬限unknown。真实答案质量与新单题调用授权保持open；M6仍5/7、04保持，05反馈复评proof与08候选质量/阶段证据未关闭，43题暂停、heldout65/M7未启动，不新增同角色/同用途或EoC/GM/GU字样门槛。
