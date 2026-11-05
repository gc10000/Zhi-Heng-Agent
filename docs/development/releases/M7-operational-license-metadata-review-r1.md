# M7依赖许可元数据技术分诊

日期：2026-11-05。对象为固定候选API镜像`sha256:969f425f295064a76346a426991ee711cea63756623e63de6aeed2523488a138`及其[依赖清单](M7-operational-dependencies-r1.json)。本记录只分诊已封存元数据，不改写候选、不替代法律审阅。

## 发现

依赖清单中7个API包的`declared_license`为unknown。逐项检查其同一候选的记录：

| 包 | 精确版本 | 上游分类器线索 | 随包许可文件记录 | 技术状态 |
| --- | --- | --- | --- | --- |
| loguru | 0.7.3 | MIT | 未记录许可文件 | 未解决：需核候选制品/上游对应版本的原始许可文本与再分发义务 |
| markdown-it-py | 4.0.0 | MIT | LICENSE、LICENSE.markdown-it，hash已在依赖清单 | 候选线索，待法律核对 |
| marshmallow | 3.26.2 | MIT | LICENSE，hash已在依赖清单 | 候选线索，待法律核对 |
| mdurl | 0.1.2 | MIT | LICENSE，hash已在依赖清单 | 候选线索；NOTICE另记录Joyent归属，待法律核对 |
| prompt_toolkit | 3.0.53 | BSD | LICENSE，hash已在依赖清单 | 候选线索，待法律核对 |
| pymilvus | 2.6.10 | Apache | LICENSE，hash已在依赖清单 | 候选线索，待法律核对 |
| wcwidth | 0.9.4 | MIT | LICENSE，hash已在依赖清单 | 候选线索，待法律核对 |

分类器字符串不是许可证文本或法律结论。现有inventory中的unknown保持不变；没有从开发环境的不同包版本反推候选镜像内容。

清单另将Redis 7.4.6上游原文来源状态标为unknown。历史下载记录有一次`COPYING` 404，之后保存了`LICENSE.txt`；该文本 hash 不能单独证明其与精确镜像/源码发行件完整映射。需继续比对固定镜像来源和许可文件。

## 仍未闭合的发布责任

- 对上述候选许可文本和NOTICE逐项进行法律/再分发义务审阅；不因hash或包管理器安装即视为满足义务。
- 明确基础镜像及87项系统包的完整许可义务、PyMuPDF/MinIO AGPL与Mongo/Redis SSPL适用责任。
- 获取课程底座代码与资料的再分发授权；确认模型权重及其训练/分发许可。
- 形成责任人、发行场景、源码/目标制品及义务履行证据。未经审阅不把`legal_approval=false`改为true，不做公开Release。

本轮没有运行供应商或本地模型、没有构建/启动新容器、没有访问目标服务器。M7-07文档来源说明和候选准备不因此变为法律验收通过；M7-09保持open。技术原清单见[operational依赖inventory](M7-operational-dependencies-r1.json)，发布差距见[release readiness](M7-operational-release-readiness-r1.md)。
