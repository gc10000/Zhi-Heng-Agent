# M6-08：新001人工双轮只读核对（2026-10-27）

用户报告已提交第二轮。通过已登录评测API只读核验：审阅、实验和结果接口HTTP均为200；实验878abb8c-6d55-483e-b1a1-b7458c19d0e0处于completed，当前仅含support-v1-001，结果有答案。找到2条human审阅，轮次为1和2，均来自同一登录审核者；本人声明与原件核对标记均为true，两个审阅均绑定当前结果指纹。没有提交或改写审阅、没有创建校准、没有调用模型。

两轮结果及各维度判断均按原样保存在隔离账本，其中有unknown；未将评分明细写入Git交付材料。当前基线校准门禁不接受含unknown的结果；本轮没有尝试绕过门槛或建立校准。此为一个dev题样例的双轮核对，不代表完整固定报告审阅或质量通过。旧045记录不变。

正式反馈草稿是在本次新真实查询之后创建；因此反馈后复评仍未完成。M6-04/05/08继续未验收，M6核心4/7，M7未授权。

精确只读检查命令（项目根PowerShell；账号从本机私有session读取，不向终端输出凭据）：

~~~powershell
node tmp/verify_user_review.cjs > output/m6-08/001-repaired-r1-20261026/human-review-r1.json
~~~

退出码0。报告：output/m6-08/001-repaired-r1-20261026/human-review-r1.json。脚本通过登录获取隔离账号会话，随后只GET审阅/实验/结果接口；未POST评分或校准。无业务代码或测试更改，无模型调用。原始私有账本和证据仍留本机。

整理脱敏文档的临时脚本曾两次因读取字段名不一致而退出1，未访问或写入账本；修正字段名后完成。属于报告编排错误，不是业务测试或审阅保存失败。

快照检查命令：`.venv/Scripts/python.exe -m scripts.verification.build_m6_artifacts --summary docs/development/reviews/M6-08-001-human-review-validation-r1.json --manifest docs/development/reviews/M6-08-001-human-review-manifest-r1-final-v5.json --base bef9cb14728323c5445e044a1bdc777f7ce9d874 --check`，退出码0；`git diff --check`退出码0。文件哈希/链接快照见[M6-08-001-human-review-manifest-r1-final-v5.json](M6-08-001-human-review-manifest-r1-final-v5.json)。

后续如需重新评估未知维度，尊重审阅记录不可覆盖约束；不能改写历史记录来满足门槛。
