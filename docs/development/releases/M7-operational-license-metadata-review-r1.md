# M7依赖许可元数据技术分诊

日期：2026-11-05。原对象为固定候选API镜像`sha256:969f425f295064a76346a426991ee711cea63756623e63de6aeed2523488a138`及其[依赖清单](M7-operational-dependencies-r1.json)。本次继续读取原制品和官方源码，补齐Loguru原文并构建新候选；原镜像、清单和历史失败保持。本记录不替代法律审阅。

## 发现

依赖清单中7个API包的`declared_license`为unknown。逐项检查其同一候选的记录：

| 包 | 精确版本 | 上游分类器线索 | 随包许可文件记录 | 技术状态 |
| --- | --- | --- | --- | --- |
| loguru | 0.7.3 | MIT | 原镜像/该版PyPI源码包均未附；官方tag原文已取 | 原镜像漏带原文，新候选已补入并核hash；法律责任仍待核对 |
| markdown-it-py | 4.0.0 | MIT | LICENSE、LICENSE.markdown-it，hash已在依赖清单 | 候选线索，待法律核对 |
| marshmallow | 3.26.2 | MIT | LICENSE，hash已在依赖清单 | 候选线索，待法律核对 |
| mdurl | 0.1.2 | MIT | LICENSE，hash已在依赖清单 | 候选线索；NOTICE另记录Joyent归属，待法律核对 |
| prompt_toolkit | 3.0.53 | BSD | LICENSE，hash已在依赖清单 | 候选线索，待法律核对 |
| pymilvus | 2.6.10 | Apache | LICENSE，hash已在依赖清单 | 候选线索，待法律核对 |
| wcwidth | 0.9.4 | MIT | LICENSE，hash已在依赖清单 | 候选线索，待法律核对 |

分类器字符串不是许可证文本或法律结论。现有inventory中的unknown保持不变；没有从开发环境的不同包版本反推候选镜像内容。

Redis 7.4.6清单实际有两条记录：历史`COPYING` 404（status=unknown），以及成功的`LICENSE.txt`（retrieved_original，HTTP200）。本次核成功记录与已提交原文SHA一致（abffee3703161c0a6a0cd7f635b2c1ebb3b81bd199e9d18ea89652d678ae4287）；不得把首条失败误报为未取得许可原文。精确发行件完整映射与责任判断仍按发布准入处理。

## 制品补修与实际验证

从停止的原候选容器读取7个包的dist-info；6个包的全部已登记许可文件hash与原库存一致。原Loguru包及从PyPI下载、按发布SHA校验的0.7.3源码包均无LICENSE，第一次查找失败保留。改读官方`Delgan/loguru`固定tag 0.7.3归档，19个Python文件与镜像安装件逐字节一致，LICENSE为1056字节、SHA256 b35d026cc7aca9d5859a02eb87ddf7a386a24c986838651bd1f283f94e003327。

原文保存在[API许可补充目录](../../../deploy/api/licenses/loguru-0.7.3.txt)，[来源清单](../../../deploy/api/licenses/SOURCES.json)记录URL/归档SHA/成员；Dockerfile仅增加COPY到`/licenses/third-party/`。旧镜像缺文件的红检查保留；新API镜像`sha256:b777e4b5e3dfec31f25f2fb77bf216098f21849d2f8611d5bf69622dcf8c3d48`构建退出0，离线读回原文SHA一致，212个app和11个prompts文件与旧镜像一致；六包许可hash再次全匹配。验证容器network=none，仅create，从未start。未重建web/MinIO或切换运行服务。

新[Compose覆盖](M7-license-supplement-r1.compose.json)固定新API/worker/dispatcher镜像，沿用原web/MinIO，配置解析exit0；该覆盖是待部署制品，不能把旧候选运行/独立结论套成新镜像运行通过。完整[脱敏验证摘要](M7-license-supplement-validation-r1.json)及私有`output/m7-license-artifact-audit-20261105-r1/`保留读取、首失败、构建和核对证据。

## 仍未闭合的发布责任

- 对上述候选许可文本和NOTICE逐项进行法律/再分发义务审阅；不因hash或包管理器安装即视为满足义务。
- 明确基础镜像及87项系统包的完整许可义务、PyMuPDF/MinIO AGPL与Mongo/Redis SSPL适用责任。
- 获取课程底座代码与资料的再分发授权；确认模型权重及其训练/分发许可。
- 形成责任人、发行场景、源码/目标制品及义务履行证据。未经审阅不把`legal_approval=false`改为true，不做公开Release。

本轮没有运行供应商或本地模型、没有启动新服务、没有访问目标服务器；新镜像实际构建、验证容器仅创建。M7-07文档来源说明和候选准备不因此变为法律验收通过；M7-09保持open。技术原清单见[operational依赖inventory](M7-operational-dependencies-r1.json)，发布差距见[release readiness](M7-operational-release-readiness-r1.md)。
