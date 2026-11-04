# M7运行收尾：执行结果与受限候选

2026-11-04；分支 `codex/m6-source-bound-comparison`，从 `69d55c3dce5d9b254c7c2c6fae93091ed0cff66b` 接续。用户明确采用[完整工作包](../handoffs/M7-operational-closure-execution-r1.md)，授权8槽及有限本地模型和唯一不同实现身份审查者。提交SHA由本包Git提交记录及最终交付给出，不反向修改报告以包含自身SHA。

**本批在供应商前因资料准备丢失必要事实而停止；provider stream和Run均0，没有新模型答案。** 已完成新准入实现及限定独立技术复核、新API构建、实际小样备份/新目标恢复/完整绑定回切、实际浏览器资料路径和候选库存。离线修复不能解除本批STOP或借剩余额度重试。Linux完整部署、真实问答/恢复后08、真实1/2/4容量和完整草稿反馈演示仍open。

## 本批消费与终态

| 项目 | 实际值及证据边界 |
| --- | --- |
| 新provider stream / Run / 持久输入 / observation | 0 / 0 / 0 / 0；固定wire/raw目录空，独立现场核对，不仅凭结果行推断 |
| 8槽 | 01–08均未派发，账户 `halt=true`，reserved0、pending/settled空；不能重用 |
| provider usage、精确HTTP、费用 | null；无新增provider已知token，但计量不可观测字段不补0；付费输出/网关/费用硬限unknown |
| 本地模型 | 正式导入1份自制资料、5chunk、attempt1；embedding文本预留/实际记录5，rerank0/pair0；无下载/替换权重 |
| 本地余额 | 不退款、不改旧SQLite；未消费额度不解除停止。后续新批单列，不从历史减回5 |
| M6历史 | 168stream/170结果/340判断、usage809676/30791、两blocked gate、proof0及halt保持 |

首失败材料、STOP、错误原件、manifest、导入、测试红/绿、中间失败与未知窗口均在 `output/m7-operational-20261104-r1/` 保留，不提交Git。原件正式字节SHA `51d0e13991c39e0faa56621f8955745778c9810cfcb675ae0ae027d32448d047`；manifest canonical SHA `008dd946355a1f853ede21c3be613bff64813d6972f29b46b92773ad22d1a1da`。原件文本归一换行hash不是该字节hash。

## 实证缺陷集中矩阵

| 根因 | 反例与影响 | 修复/退出条件 | 当前结论 |
| --- | --- | --- | --- |
| 私有准备脚本按整行删旧状态 | 最后一行同时含“设备标识、当前修订和引用原文，再由用户决定”；固定06必要事实被删。审查未签manifest gate，未发provider | 新 `demo_source.py` 仅删除唯一完整状态句，缺失/重复拒绝；新CC0资料保留所有其他字符；下一批重新正式导入并独立核来源 | 离线补修通过；本批停止，不是模型质量失败 |
| 稀疏维度键表示漂移 | JSON字符串键与Milvus整数键数值相同，但canonical排序不同，第一次实际恢复误判不等 | 只正规化合法非负整型维度键为字符串；非法/重复拒绝，不舍入、不改数值；全新目标精确恢复 | 独立12项与新目标现场核验通过；旧failed目标/claims保留 |
| 安装元数据缺Name | 库存脚本排序崩溃，r1为0字节 | 保留name/version null及unknown，不丢记录 | 红→绿与最终库存JSON通过；不是法律批准 |

没有重开r3已关闭的共享恢复预留和重排分批问题，也没有扩展成新供应商或调度框架。

## 新准入与证据身份

默认不配置的 `m7_operational_demo_v1` 仅在新隔离实例注入固定8题白名单。固定模型 `qwen3.8-flash`、n=1、`enable_thinking=false`、单一 `max_completion_tokens=4096`、stream+usage、SDK重试0，无fallback/redirect。输入上限28416、窗口32768/reserve256、上下文12000字符/10文档。正式Run、完整prompt/docs/reference_map、执行租约、来源及配置在账户CAS/联网前持久化；独立控制库不会随知识恢复而回滚。未知usage/思考/异常finish/断流/前置失败持久halt，恢复只观察，不重发。HTTP正文及SSE原流排他落私有证据，不落凭据/端点。

宿主专用SQLite以 `BEGIN IMMEDIATE` 预留64文本/8重排/512pair，绑定既有模型配置及账本路径，失败不退款、重启不重领。本轮未开启其他模型角色。渲染字数不充模型token；不修改原输出硬限判定。

最终应用来源身份 `2496384dbe86159a64667740420ce8100627b47c20efe4235e8faef5c207149f` 覆盖app/prompts的规范化LF源码；scripts/examples/docs另由发布提交及文件hash绑定。不能用应用hash代替全仓库身份。

## 实际验证，分列不累计

| 验证身份 | 最终结果 | 限制 |
| --- | --- | --- |
| 实现自验 | 32 passed / 1 Windows symlink skip，`final-targeted-r1.log` | 本包准入/本地预算、来源、库存、恢复键及旧护栏定向；不是M6全轮或独立质量 |
| 最后离线/前端补核 | 8 passed / exit0；pnpm typecheck exit0 | 与32项重叠不累计；前端产品代码未变，未声称新web构建 |
| 不同实现身份 | 38准入/正式Run/安装SDK MockTransport；来源4；稀疏键12分别通过 | 组间重叠不累计；合成调用不是供应商效果/网关硬限证明 |
| 真实工程恢复 | 15集合、3对象、5真实向量备份；全新工程目标完成并独立现场核 | 14普通集合及5chunk claims、索引/权限/注册/原件/数值精确；session不恢复；无08 |
| 真实绑定消费 | API/worker/dispatcher完整三元切换新目标，读资料/5切片/原件hash；finally回源再读，停idle消费者 | 工程目标另建，不篡改八槽manifest，不发问答 |
| 浏览器实际后台 | 1项通过，登录→published资料/真实切片→原件字节hash→刷新→新生成503；独立看日志/截图 | 无mock/预写答案；前两次失败保留；不包含答案引用、草稿确认和反馈完整闭环 |
| Linux现场 | Ubuntu发行版、Python3.14.4、WSL2；工具及本地目录700通过 | Docker为Desktop29.5.2/desktop-linux；无Ubuntu原生daemon；完整部署及最后分步启动超时，未通过 |

错误的资料并未被用来取得新答案，不能声称答案已退化或改善。完整原文保留也不等于完整回答。详见[唯一审查者报告](M7-operational-closure-independent-review-r1.md)及[脱敏验证清单](M7-operational-closure-validation-r1.json)。

## 入口、构建与安全停态

新项目 `zh-m7-23a6e6`，入口 <http://127.0.0.1:61587>；原18080不改。本批API/worker/dispatcher固定新API image `sha256:969f425f295064a76346a426991ee711cea63756623e63de6aeed2523488a138`；web/MinIO复用已核r3来源，精确[覆盖](../releases/M7-operational-r1.compose.json)不能省略。API构建成功不等于web/MinIO干净重建；inspect.Id、RepoDigests及构建config digest各自封存，不混为同一字段。审查者从镜像归档210个app/prompts文件独立重算应用hash及snapshot.py补修hash，镜像descriptor自hash一致，完成离线源码到镜像映射；未冒充额外容器内重算或daemon稳定性。镜像归档296086016字节，SHA256 `25bfd26c04fe04e6623a53ca374d73776cda415cbbd42825fd5bea6574b569e1`，save exit0、tar可读50成员；仅私有output保存，未上传注册表。

审查现场API运行、worker/dispatcher exited、三进程generation=false，宿主PID已不存在，账户halt且无未知调用窗口。后续Docker多次间歇失败，最后Linux启动和仅terminate Ubuntu也18秒超时；Ubuntu最终停态unknown。未重启机器/daemon、未操纵旧服务。瞬时安全停态通过不代表服务持续可用，当前入口需要按实际health确认；不能承诺此刻一定响应。

在Docker恢复正常后，仅恢复已有本轮只读入口（不启动worker/dispatcher或模型）的精确命令，从工作树执行：

```powershell
$env:PYTHONUTF8='1'
$m7Runtime='output/m7-operational-20261104-r1/preview/runtime.env'
docker compose --env-file $m7Runtime -f compose.delivery.yaml -f docs/development/releases/M7-operational-r1.compose.json config --quiet
docker compose --env-file $m7Runtime -f compose.delivery.yaml -f docs/development/releases/M7-operational-r1.compose.json up -d --no-build --no-deps api web
& 'D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.venv/Scripts/python.exe' scripts/verification/check_readiness.py --url http://127.0.0.1:61587
```

该runtime已核generation=false；不使用准备过但从未启动的generation版env。密码沿preview.py copy-password静默复制，不打印env。此命令只针对保留的本轮卷/存储，不能作为新机器完整部署命令；原候选回滚仍使用原r3覆盖及原18080配置，不把新API替换到旧项目。

## 发布与后续

[依赖候选](../releases/M7-operational-dependencies-r1.json)分列API实际106包/API锁105、API Debian87系统包及copyright hash、前端许可索引和四锁hash。7个API声明许可unknown保留，不能用宿主177记录替代API。六份固定上游原文在 `docs/reuse/licenses/m7-operational-r1/`；Mongo取7.0族r7.0.0许可，不冒称现场补丁精确源码；Redis最初404和正确LICENSE.txt成功均留证。完整系统/模型权重、课程底座授权及AGPL/SSPL义务仍open，legal_approval=false。

生产前具体差距与负责人工作在[发布准入](../releases/M7-operational-release-readiness-r1.md)：认证/TLS/最小权限/备份加密及停写/质量范围/目标平台/许可逐项留证。可公开文件范围是脱敏源码、合成测试、配置模板、CC0样例、导航/许可原文；output/evals/原件/流/截图/日志/权重/凭据全部排除。分支push不是公开Release、镜像上传或外部部署批准。暂存全量diff --check返回2，唯一发现是Mongo上游许可原文11处尾空白；保留原字节及已核SHA，不修改许可。排除这一原文后的源码/文档检查exit0，JSON/新链接及明显凭据扫描通过。

当前唯一下一项为[修正来源的新批明确授权提案](../handoffs/M7-operational-demo-r2-proposal.md)：至多8新stream，预计新增本地14文本/8重排/48pair（上限封存），新身份、新控制账户和独立准入；原批不重领。执行方承担准备与临发核对，不要求用户查路径/评分。授权前不实施或发调用。

M6保持5/7，04已验收，05真实反馈复评proof和08有效新候选质量及阶段证据open；M0–M5既有验收保持。M7工程依赖例外有效，但本包不签M7整阶段、生产或公开发布通过；不创建正式评分/候选/gate/feedback proof，不运行heldout或旧批。
