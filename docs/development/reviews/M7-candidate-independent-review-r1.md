# M7内部候选定向独立技术复核 r1

2026-11-04；独立审查身份 `/root/independent_m7_candidate_review`。该身份未参与业务实现，仅编写自己的隔离验证与证据；补修由总控 `/root` 完成，原审查者独立复测，没有再委派或执行Git提交。

**结论：最终固定本机内部候选的限定定向技术复核通过，R1/R2已关闭，`open_findings=[]`。** 这不是M7整阶段、M6质量、Ubuntu、真实模型容量、生产热备、许可核清或公开发布通过。逐项状态、命令、文件hash及边界见[机器报告](M7-candidate-independent-review-r1.json)。

## 身份与冻结范围

- 工程基准：`fe2d957b35256907d1e990ff66f8362fc267c1e3`；初始应用候选：`ebb8ef93ddca4b41d736f23e980c59fb03f02b10`；接收HEAD：`2bc736adff4249d97b269c02fcc6d417bb76f360`。
- 最终实现提交：`b4d3ec77ed49d090766072fa3e1fa04386db9b16`；分支 `codex/m6-source-bound-comparison`。本报告随后单独提交，不循环绑定自身SHA。总控报告首次普通push遇GitHub Internal Server Error，随后正常重试已成功同步相同SHA；独立方未自行查询远程或执行Git写入。
- 当前入口 `http://127.0.0.1:18080`，仅随机项目 `zh-m7-05d09f`。未访问private-identity、打印.env秘密、写真实业务库、改旧Run/lease/slot/gate/proof、启动模型宿主或执行模型推理。
- 新provider stream **0**、本地推理 **0**。只访问6个PyTorch公开包索引核官方wheel hash；供应商HTTP/费用观测为null，不伪称零费用实测。
- 私有证据目录全新创建为 `output/m7-independent-review-20261104-r1/`，红测/绿测/失败目标保留，不提交output。仅在当前合成预览新建1个独立工程事件Run，并在finally只结束该新Run；未改任何既有Run。

## 两项实红、补修与独立复测

### R1 · 恢复任务可覆盖已经完成的向量目标（P1，已关闭）

初始 `snapshot.restore` 分别检查目标不存在后，只在目标Mongo库插入exclusive记录；不同数据库和桶共用Milvus集合时没有共享排他。独立真实隔离复现安排B通过预检/建桶后暂停，A完整恢复并标记completed，随后B继续复用A的集合并upsert相同UID。两者均返回completed，A的正文由合成A变成合成B，控制状态仍completed。

实红：`race-05cbbb/result.json`；脚本 `race_restore.py`。总控新增共享控制库，数据库/桶/向量集合分别唯一claim，全部预留后才写目标；完成、失败、部分预留和未知均不释放。补修位置：[共享预留](../../../scripts/operations/restore_reservations.py#L27)、[恢复入口](../../../scripts/operations/snapshot.py#L234)。

独立绿测 `race-green-ee8849/result.json` 使用全新资源和新共享控制库，三种共享目标竞争均在败方目标写入前拒绝；建桶前故障后，三个资源方向均不能重领。胜方completed、向量完整，源Mongo/向量前后相等，真实Mongo复合索引键顺序保持。失败/部分claim和资源全部保留。

限定条件：同一物理存储绑定的恢复进程必须共用同一控制身份；此协议不防绕开工具直接写存储或故意另换控制库。停写小样快照不等于生产热备或跨存储事务。

### R2 · 合法重排数量超过新增宿主协议单批上限（P2，已关闭）

`RetrievalPolicy`允许最多1000个重排输入，而原HostReranker一次提交全部pairs，宿主RankBatch仅收64个。独立纯协议复现使用实际FastAPI入口和全替身评分：20/64候选等价，合法65候选本地返回65，远端HTTP422且评分未调用；当前预览宿主关闭，未发生真实推理事故。

实红：`rerank-protocol-initial.json`。总控在[宿主客户端](../../../app/infrastructure/queue/model_client.py#L16)先预检全部输入，再按64对/256000字符分批，原顺序合并并逐批校验分数；各批共用剩余请求超时预算，不返回部分成功。

独立 `rerank-protocol-green.json`：20/64/65/1000候选、分数及排序与本地路径一致；65拆64+1，1000拆16批，4份100k字符拆2+2。后置单对超限在任何HTTP前拒绝；第二批NaN/bool/传输超时均抛错且不返回半批；fake单调时钟核剩余290→285秒及耗尽后不发下一批。未加载权重或访问真实宿主。请求预算验证不证明硬中断或真实推理容量。

## 独立实际验证

以下命令使用主仓库 `D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.venv/Scripts/python.exe`，PowerShell设 `PYTHONUTF8=1`。自编脚本位于上述私有目录；精确命令/退出码/证据hash列于机器报告，不累加重叠组数。

| 验证 | 实际结果与范围 |
| --- | --- |
| 初始离线定向pytest | 29 passed / 1 Windows符号链接skip，54.51秒；不是实现方日志转签 |
| 补修后定向pytest | 37 passed / 1同项skip，23.14秒，exit0；含health/bridge/lifecycle/restore guards/index/reranker/control identity |
| `identity_and_live.py` | 独立核45封存证据、11锁、276初始源码及4镜像ID全部相等；6个官方wheel index hash匹配 |
| 原短路径CPU/GPU环境 | 各171包依赖兼容；独立导入torch三件套及FlagEmbedding/Transformers等9组件；CPU2.10.0+cpu，GPU2.10.0+cu128/CUDA12.8/RTX4050可见。没有第二次安装或推理 |
| `http_isolated.py` | 新随机Mongo/独立桶的10项检查全绿：新生成503且不写Run、服务器事件终态前yield、个人Run/引用跨用户拒绝、同KB资产共享、撤权拒绝、Range、游标、CSRF/Origin和原件hash |
| 真实18080只读接口 | live/ready200，models disabled；catalog503；已有Run/引用可读，隐藏文件403；PDF前缀/后缀/开放Range206、越界/多段416；终态SSE游标排他、坏游标422 |
| `live_preterminal.py` | 最终r3实际Nginx在本次新Run仍running时收到首事件（143.516毫秒，只是工程首事件时延）；断线后游标恢复到本次合成failed终态，没有二次执行 |
| `image_boundary.py` | r3 API277文件逐字节匹配源码，web485文件有限检查；未含本轮合成秘密/.env/私有目录；网络关闭容器实际无.env加载prompt、启动/live/ready、旧/query404、无模型库导入；Linux符号链接越界拒绝补核Windows skip |
| `final_identity.py` | 最终提交、API/worker/dispatcher实际image ID及源三元绑定匹配，live/ready200；原45证据未变；归档字节/hash和93文件公开候选清单核对通过 |

保留的独立工具失败：首次Docker输出用默认GBK解码失败，改PYTHONUTF8后通过；首次shell找不到uv，改绝对路径后通过。它们不是候选技术缺陷。原导入日志手写 `imports=10` 不是测量值；此报告按实际9个组件名称及torch三件套说明，不用该字段累计。

## 最终源码、镜像和文件hash

- API/worker/dispatcher：`sha256:6beb232a74f39c1813d56adbda91f19b9932d9e49890c6a5734c6f904cc98882`。
- Web：`sha256:6db4189f8be95ae0b0fd9c908d382e1b782aa85183719a473b0aff0354dd6d7a`；MinIO：`sha256:48c2b3223491f99af2a36b68889c06f8d211afd388e3fc82e6522ad23df307c8`。
- 独立API277文件路径→原字节SHA256映射的canonical摘要：`17fc9a88bf571c48cbfd6f08ab11ed302db7bb17e777ab24571912f1d10b3c6d`。最终工作树源码与该提交无差异；映射逐文件与镜像相等。锁/关键文件hash与私有独立证据hash见机器报告。
- 本机归档296076800字节，SHA256 `db9f652e2ab4c8ee91e8cdc1b417350f2d5aaa870f0723eb00cfae18532ea8e5`，未上传。旧r1/r2镜像、证据与失败目标保留。
- [r3固定镜像覆盖](../releases/M7-delivery-r3.compose.json)与运行ID一致。已有runtime.env仍含旧tag，恢复必须显式使用该r3覆盖；不以通用不带覆盖的up命令指代当前固定候选。
- [公开候选清单](../releases/M7-public-files-r3.json)在实现SHA时93文件，hash `604035765a4eee32bda2e64c2e61bbbf6cc2c934083330953f7a12de6ddc1e93`，无缺文件/禁止项；这仅是脱敏候选范围。随后单独加入本报告的导航变更不属于该实现SHA。

## 核原证据与未审范围

已读实际受影响源码/差异、AGENTS/Git工作流/进度/授权/冻结提案、实现报告和实际封存证据。历史真实三元绑定切换/回切的命令、manifest、结果及hash已核，当前三服务源绑定已独立核对；**本审查者未再次故障切换历史项目**。worker/MinIO停启、62前端单元、47/74容器合成组合及真实后台浏览器场景属于实现方证据，不计为本人的独立重跑数。没有重做不受影响的M6质量、旧43、基线或heldout。

当前关闭承诺按已冻结配置成立：Run创建入口拒绝、问答扫描关闭，评测catalog/模型宿主/供应商凭据实际为空。不能把M7开关宣传为任意重新配置评测/worker模块后的全局模型急停。

Windows原清洁安装有封存收据，本人核原证据、现有独立环境依赖/导入和官方hash，没有冒称新做清洁安装。Ubuntu目标、真实问答/推理/吞吐/峰值显存、生产热备、完整漏洞扫描、完整MinIO源码干净重建、课程底座再分发许可及AGPL/SSPL等义务核清都未由本轮关闭；这些不列作本机限定候选的新技术缺陷，也不外推为通过。

M6仍5/7：04保持，05缺反馈复评proof，08缺有效候选质量/阶段证据；原168stream/170结果/340判断、两blocked gate、0proof/halt保持。本审查未访问或改写旧业务账本，不将保存输入回放、合成Run或待审反馈升级为真实质量proof。合并main、外部部署、镜像注册表上传及公开Release均不在本结论授权内。
