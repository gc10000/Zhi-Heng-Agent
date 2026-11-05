# M7 r2运行包执行封存

本轮依据用户明确“授权”执行r2新批及1位新独立审查者。从`13b50934a8bc4ee088075e928c7c6e33a76a8193`接续，保留原分支及历史。**本批在正式导入准备阶段首失败，未执行provider问答；r2永久停止，不得复用未消费槽位。** 修复和技术验证不解除停止。

## 实际执行与停止

新隔离项目创建并运行API/web/存储，复用固定基础镜像，新API构建成功。使用修正后的CC0自制资料，经正式上传登记1份文档、原件、修订和导入job；原件SHA256为`249c38af8708bb62cd15f058b70ddd31fc72ddfd0674c9eb70252c1e9a766b6e`，离线解析6chunk、0图片，必要事实完整。不同身份审查者只批准一次导入准备，尚未批准provider临发。

私有`prepare_demo.py`轮询正式import job时Mongo读取发生`_OperationCancelled`，进程exit1，立即写入`STOP.json`，未重跑。后续只读发现普通租约自动接管已使job从attempt1进入attempt2，最后为`failed / embedding_pending / upstream_connection_failed / retryable=true`。这是受控导入次数限制缺陷，不是手工重试，也不能把它隐藏成“一次attempt合规”。原job、lease、retryable和检查点原样保留。

精确停止本轮worker、dispatcher和模型宿主。首次compose停止遇Docker500，失败保留；之后精确容器停止成功，独立只读确认两个消费者exited、宿主PID不存在、`M7_GENERATION_ENABLED=false`。新控制账户、执行manifest/budget未创建，Run为0、流目录空；不是“账户已halt”。停止依据是文件STOP、缺失正式准入材料及消费者停止。旧r1账户只读确认halt、未消费，未更改旧账本。

## 计量与身份

| 项目 | 本轮事实 |
| --- | --- |
| 新provider stream / Run | 0 / 0；未进入provider准入及调用阶段 |
| provider input/output、HTTP、费用 | null / null / null / null；未知不补0 |
| 本地embedding | 持久预留6文本，仅1条receipt；实际推理完成数量unknown |
| 本地rerank / pair | 持久预留0 / 0；不把预留计量当完成计量 |
| 槽01至08 | 全部未派发；整个r2停止，不能续批或转移未消费额度 |
| 真实存储写入 | 已有上传、解析原件、修订、导入job；不是0写入 |
| 网关硬限 / 付费输出上限 / 费用上限 | unknown，未得到新证明 |
| 历史M6完整批实际usage | 809676 / 30791，旧168stream及两blocked gate/0proof/halt不改；本轮无新provider usage可追加 |

导入时应用来源身份为`29c8f4f6ebe4cd58c412db6f49a23714e8b9027aa409fefe1bc09d0c9c042280`；运行API镜像为`sha256:4e8fb4cac8f1903002bb2c74f1e5e05be82fffc34fb87de4b4dbb20fac2ea1f8`。其210个app/prompts来源经独立重算匹配。导入补修后的最终应用身份为`912c8a9960ca2271c271e472681860364af6afa5230782d92e7d4f1adc7be6b9`；已运行镜像不包含该补修，未以新代码重启r2。

## 缺陷、补修与退出边界

| 根因 | 反例 | 修复与退出条件 |
| --- | --- | --- |
| 准备读取Mongo被取消 | prepare脚本在读取job时失败；不是产品回答错误 | r2停止并封存。随后Mongo恢复不解除STOP，不重启本批 |
| 正式导入沿普通租约恢复，未冻结一次attempt约束 | 已保存job真实attempt2；私有终态assert不能约束worker | 新增可选`IMPORT_MAX_ATTEMPTS=1..10`，新任务register持久冻结；claim/retry使用原子次数条件，dispatcher及过期重排拒绝已耗尽任务，过期/已耗尽pending封存failed。对外retryable=false，保留原错误。未配置的普通任务继续原恢复；不回填真实历史 |
| 运行验证间歇Mongo/Docker故障 | 红r1和绿r1存在setup错误、停止首次500 | 保留原失败。新随机合成库重现实红，采用直连配置的后续定向验证分列，不将失败组宣称通过；不把Desktop容量重新设为用户前置 |

受控新导入必须在API登记前设置上限，数据库字段是后续消费依据。补修不自动把所有普通导入改成一次，不回填旧任务；部署新代码和设置该变量也不授权恢复已STOP批次。

## 验证及证据限制

执行证据位于本机`output/m7-operational-20261105-r2/`，独立证据位于`output/m7-r2-independent-20261105-r1/`，均不上传。

- provider/local r2增量实现自验中途为37 passed；其中v1参数下4项r2专属用例未执行断言，最终验证已明确改成skip，不把空分支作为技术覆盖。
- 导入红测`import-limit-red-r2.log`：7 failed / 1 passed，业务断言实际失败，exit1。更早红r1为3 failed / 5连接setup errors，原样保留。
- 补修定向`import-limit-green-r2.log`：12 passed，exit0；10项新边界及2项旧恢复兼容。之前绿r1为7 passed / 5连接setup errors，不能作为全绿。
- 最终合并`final-targeted-r1.log`：37 passed / 4 skipped / 6 Mongo setup errors，exit1。4项skip为历史v1不适用r2专属边界，6项错误均在Mongo setup；不能宣称最终整组全绿。该轮包含最终导入补修，不重复无关历史整轮。
- 补修镜像`build-attempt-limit-r1.log/json`：Docker API `_ping`返回500，构建exit1，无新镜像身份、未部署。之前成功的4e8镜像只是导入前源码，不能冒充最终补修制品。确切收据另见[脱敏validation](M7-operational-r2-validation-r1.json)。
- 新独立审查者38项正式Run/SDK协议及13项r2身份/预算通过；补修独立12项纯离线展示/非法配置边界通过，CAS代码静态复核与实现方真实Mongo12项收据核对分开。独立terminal观察组因Mongo阻断，未完成，不计通过。

独立结论以[独立报告](M7-operational-r2-independent-review-r1.md)为准，本执行报告不代签。合成供应商及测试库不证明真实答案、容量或付费上界。完整真实1/2/4问答、恢复08、问答引用支持反馈浏览器链均未执行；不拿旧答案、mock或只读页面冒充。本轮没有Linux服务器部署，没有公开Release或main合并；既有工程恢复和许可证据保持原范围，不在本轮重新签全阶段。

## 交付与唯一下一项

本轮预览入口为`http://127.0.0.1:57652`，仅内部生成关闭状态；最后只读ready200、models/tools disabled是瞬时观测，不保证持续可用。不要启动worker/dispatcher或模型宿主来“恢复演示”，不提供会重发失败批次的启动命令。

唯一下一项由执行方在Linux目标运行环境准备**新批身份**和导入前持久上限核验方案，再按具体来源、预算、目标、停止和回滚材料申请新的真实范围；本批未消费余额不自动授权下一批。目标Linux主机实测、真实容量/完整演示、许可责任与公开范围仍缺证据。M6的对象、时序、数量、引用和审核适用性质量债务保持；04已验收，05缺真实反馈proof，08缺有效新候选质量及阶段证据，不改评分或门禁。
