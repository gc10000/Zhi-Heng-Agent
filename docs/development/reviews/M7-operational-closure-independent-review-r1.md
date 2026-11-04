# M7运行收尾：限定独立复核

本轮审查者为新建的 `/root/m7_operational_independent_review`，未参与业务实现，未调用供应商、embedding或reranker，未修改真实业务状态、未委派其他Agent。审查以最终应用来源身份 `2496384dbe86159a64667740420ce8100627b47c20efe4235e8faef5c207149f` 为锚；该身份覆盖app/prompts，补充脚本及样例另行核对，不能用它代替完整发布提交或镜像身份。

**结论：八槽准入技术定向通过；实际来源临发复核拒绝。本批provider未执行，不能签真实演示、恢复后问答、质量通过或M7整阶段通过。** 首失败是制作演示资料时丢失必要事实，已在供应商派发前发现。离线补修通过仍不解除本批STOP，需要新的明确授权后才能恢复真实派发。

## 定向检查

| 对象 | 结果 | 本轮证据与边界 |
| --- | --- | --- |
| 八槽身份、固定profile及正式Run准入 | passed | 独立38项定向合成检查，exit0；随机 `m1_test_m4_ir_` Mongo，使用正式RunRepository/RunCommands/QueryRunner/SDK及MockTransport，无真实模型。 |
| 输入冻结、CAS、停止及结算 | passed | 固定请求/owner/会话/波次/恢复目标；模型前输入和租约；重复槽拒绝；1/2/4/恢复累计；未知usage、迟到正文、断流及前置失败持久halt；幂等结算。 |
| 非思考wire与流式缓冲 | passed | 安装SDK核model/n/temperature、`enable_thinking=false`、单一4096限制、stream+usage、重试0；拒绝异常终止/finish后正文/思考；Mock不能证明网关遵从或实际付费硬限。 |
| 本地宿主限量 | passed | SQLite并发预留64文本/8重排/512pair、模型和账本路径漂移拒绝；合成测试不证明真实模型容量。 |
| 本轮资料制作及固定06来源 | **rejected before dispatch** | 整行删旧状态时同时删掉设备标识/当前修订/引用原文/用户决定这一事实；已导入5chunk的错误原件及manifest原样保留。 |
| 资料制作离线补修 | passed limited | 新脚本仅移除唯一状态句；版本化样例与原文的差异精确为这一句。独立4项通过，实现2项同次执行通过，分列不冒称6项独立。未重新导入、不改变旧输入。 |
| 恢复稀疏向量JSON表示补修 | passed limited | 独立12项通过：维度键规范为字符串；JSON往返和排序稳定、原记录不变、数值不舍入；bool/float/负数/非规范字符串/重复维度拒绝，1e-9数值差异仍不相等。实际恢复另行核验。 |
| 真实provider演示及答案 | not executed | 未签 `manifest-approved.json`；未产生真实Run或产品答案，不能将合成回答或相关原文展示当真实效果。 |
| 新工程目标恢复 | passed limited | 独立现场只读核14普通集合/索引及5个chunk claims、3对象hash、5向量数值、权限注册关系、源向量不变及失败目标保留；不包含08。 |
| 浏览器资料路径与生成拒绝 | passed limited | 已阅实际1项浏览器绿日志并查看2张截图：登录/资料/修订/切片/原件byte SHA/刷新/HTTP503拒绝。无mock答案，不包含完整真实QA闭环。 |
| 最终安全停态 | passed at observation | 独立现场核API运行、worker/dispatcher exited且三进程generation=false，模型宿主停止，调用账本halt/0消费、STOP及空流目录；后续daemon稳定性仍open。 |
| 保存镜像与受审源码映射 | passed | 独立流式核镜像归档SHA/50成员、API层210个app/prompts文件与应用来源身份相同、snapshot.py与恢复补修字节hash相同、descriptor blob自hash相同；不启动容器。 |
| Linux部署与持续环境可用性 | open | Ubuntu工具/700目录已核，但完整部署尝试超时；Desktop daemon多次间歇失败，不签原生Ubuntu或持续可用性。 |

独立38项运行后再次计算应用来源身份不变。私有证据：`output/m7-operational-independent-20261104-r1/final-2496384-r1.log`、`admission-r1.json`。此前审查脚本连接路径错误、Mongo不可达及Milvus连接失败日志保留；它们不是通过用例，也不冒充业务源码技术失败。

## 首失败、消费与安全边界

原 `examples/preview/manual.md` 最后一行同时包含产品事实和“本机预览禁用新增模型生成。”。私有准备脚本按整行删除旧运行状态，导致固定06“决定后续操作前，需要核对哪些信息？”缺少已指定的必要依据。该问题与检索召回、模型能力或M6历史质量无关，不能靠继续派发验证绕过。

审查者在发现后直接只读核Mongo及SQLite：真实Run=0、输入冻结记录=0、观察记录=0、供应商流文件为空；当时八槽账户尚未建立。本地账本预留5个embedding文本、0次rerank/0pair，正式导入attempt1完成且索引5行。执行方随后封存STOP并通过正式DemoLedger保存halt，收据为halt=true、streams_reserved=0、pending/settled均空，usage/HTTP/费用保持null。known_input/output的0是账本已知累计，不能把null计量字段改成0。

独立只读证据为 `post-finding-state-r1.json`；来源反例为 `source-fact-red-r1.json`，其中两个文本SHA按读入文本后UTF8计算，换行归一化；正式已登记原件字节SHA为 `51d0e13991c39e0faa56621f8955745778c9810cfcb675ae0ae027d32448d047`，不得混用。固定manifest canonical SHA为 `008dd946355a1f853ede21c3be613bff64813d6972f29b46b92773ad22d1a1da`，保持历史原件。

本批8槽未消费不等于还能继续派发。STOP有效；旧M6槽及账户未借用。供应商实际硬限、付费输出硬上界、精确HTTP次数及费用仍unknown。本批没有新provider usage，未生成质量结果。

本次独立确认模型宿主PID已不存在；私有活动runtime/host配置均为generation=false。初次Docker现场检查失败原日志保留；后续安全现场已独立通过（`safe-state-r1.json`、`safe-state-r2.log`）：API运行，worker/dispatcher exited，三进程同镜像 `sha256:969f425f295064a76346a426991ee711cea63756623e63de6aeed2523488a138` 且generation=false；STOP有效、账本现场halt/0消费、Run/input/observation0，宿主停止、本地预留仍5/0/0。再次额外重算容器内源码hash时Docker查询又失败，未执行该额外命令；后续改为从保存镜像层独立只读重算，已补齐源码映射。不能把瞬时安全停态通过写成daemon持续稳定或目标环境完整通过。

保存镜像归档SHA `25bfd26c04fe04e6623a53ca374d73776cda415cbbd42825fd5bea6574b569e1`、296086016字节/50成员已独立核对；API各层210个app/prompts文件重算为上述应用来源身份，恢复脚本snapshot.py字节SHA `be42c4556a3809265810bb5306a793f9e11c5fe2ba5c2c70144d2cc0d7e51e63` 与受审补修精确相同。descriptor blob自hash与实际镜像Id一致；未启动容器。私有证据 `image-archive-source-r1.json/log`。

## 环境、恢复和分发证据限制

已阅Ubuntu工具检查及Linux本地目录700权限记录；Docker为Desktop daemon，内核为WSL2。Linux部署尝试超时；最终诊断开始时Ubuntu显示Stopped，随后启动和仅终止本轮Ubuntu的命令均18秒超时，因此最终WSL停态unknown，不能宣称Ubuntu已成功收尾。没有扩大为系统重启或其他发行版操作。不能签完整Ubuntu部署，更不能签原生Ubuntu服务器验收。已阅备份收据15集合/3对象/5向量；首次恢复为ValueError保留现场。差异核对Mongo全等、5个向量数值全等，错误在JSON字符串维度键与Milvus整数键的canonical排序表示；已定向补修并独立12项通过。未改变数值比较、共享目标预留或失败claims。

补修后的全新工程目标 `m1_test_m4_res_63f2b0` 已独立现场只读通过：备份manifest SHA `d4bdb87f14c5ed598138673cec1f48cf2f2d1b2b8a9ff6d7d401a1302ad7cca7`，文件hash全核、14普通Mongo集合内容/索引及5个chunk claims、5向量精确数值与3对象hash、活动修订和owner/kb权限注册关系、session未恢复、源向量不变。首次失败目标f62fc7及failed claim保留，新工程target/claim completed，外部调用控制账户仍halt，源/恢复Run均0。私有证据 `restore-live-r1.json/log`。已阅三进程完整三元覆盖、实际切换后读资料/5切片/原件hash及finally回切源同样读取的执行收据，最后停worker/dispatcher。该项为工程绑定/回切消费，不改8槽manifest、不执行08；不重新开启r3已独立关闭的共享目标及重排桥接技术项。

实际浏览器r3限定路径1项通过，审查者已阅日志并查看资料注册/生成拒绝2张截图：登录→资料→当前published修订/切片→原件字节SHA→刷新→生成HTTP503拒绝。前两次失败原日志/截图保留，r1是测试LF/CRLF文本比较，r2是存储不稳定期间切片不可见；不把它们隐藏成首轮通过。未获供应商答案，因此该路径不能替代真实问答→引用→草稿确认→反馈闭环。恢复后08没有执行。

依赖候选库存r2为有效JSON，4个源码锁hash与当前文件匹配，177个宿主安装记录、105项API锁记录及前端许可索引存在，无Name元数据记录保留unknown；旧0字节r1失败产物保留。另阅实际API镜像安装库存r3：106记录、143个许可文件hash、7个声明许可unknown，未拿Windows库存代替API库存。公开候选的105锁项全部匹配，镜像额外仅pip25.0.1；87个API系统包及copyright hash另列，明确不覆盖宿主/其他镜像系统。上游原文获取收据包含Mongo/Milvus/etcd/MinIO/PyMuPDF，以及Redis首次404后修正固定版本LICENSE.txt成功；6份落地原文byte SHA均独立匹配收据。此为候选库存，不等于系统/模型的完整SBOM、课程底座许可核清或AGPL/SSPL义务签署。法律批准标志保持false，公开发布未授权。

最终文档定向核验：执行validation所列43份私有证据的字节长度/SHA均与现场文件一致；4份主交付/独立/新批提案/发布准入文档的本地链接存在，独立JSON登记的6份源码/脚本hash与当前文件一致，应用来源身份未变。执行方最后8项离线和前端typecheck退出0收据已阅，保留为实现自验，不叠加独立计数。修正来源字节SHA `249c38af8708bb62cd15f058b70ddd31fc72ddfd0674c9eb70252c1e9a766b6e` 已核；6chunk/0image为离线解析，不是新导入或推理。新v2/r2提案明确尚未实现、登记或授权，不能复用本批halt额度。

## 后续唯一变量与阶段界限

离线补修只删除旧运行状态句，保留全部产品事实；已导入错误原件、5个embedding文本预留、本批manifest与halt不得修改或重领。后续若申请新真实验证，应冻结修复来源、新身份及独立额度，清楚列出已有消费、拟新增本地推理和至多8stream的具体请求，并沿正式来源登记/Run/结算流程；本次报告不授予新调用。

M6仍5/7，04保持验收，05缺真实反馈复评proof，08缺有效新候选质量及阶段证据。原168stream/170结果/340判断、两blocked gate、0proof/halt及原43题暂停保持。自制演示不构成M6双轮盲审或质量proof；M7工程推进依赖例外也不自动授予公开上线。
