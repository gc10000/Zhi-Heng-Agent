# 助手开发验收政策 v1 接线说明

状态：2026-10-29总控对9cbccd2独立实现复核通过，见[核验报告与授权范围](../development/reviews/M6-convergence-execution-review-r1.md)。本轮尚未登记真实政策或写真实评分；允许最终题集/配置及实际独立审核执行前置满足后，通过下列正式接口使用。批准文档为 [总控决策](assistant-development-policy-decision-v1.md)，本文件不修改该已冻结文档。原 human 发布门槛独立保留。

所有接口均位于 `/api/v1`，沿用登录、CSRF、维护角色、实验所有者和知识范围授权；路径中的 ID 只选服务端登记内容，不接收任意文件或数据库路径。

| 顺序 | 接口／字段 | 核验及恢复 |
| --- | --- | --- |
| 1 | `POST /evaluation-quality-policies/{kb_id}` | 总控 admin 在授权知识范围登记批准政策；不可变引用为 `{id,sha256}`，批准文档内容变化须新政策版本，不能沿用v1。 |
| 2 | 正式创建实验：`quality_policy` | 请求与冻结配置必须同引用；省略仍走原human规则。job和Run前重验，运行配置加入本实验`quality_execution_key`参与checkpoint身份。 |
| 3 | `POST /experiments/{eid}/review-executions` | 完成结果上登记`client_request_id/round/execution_id/reviewer_model/source_manifest[{source_id,sha256}]`。轮次键由服务端固定；两轮执行ID唯一，不能使用生成实验或Run ID。第二轮须在第一轮封存后开始。 |
| 4 | `POST /experiments/{eid}/review-executions/{execution_id}/seal` | `{reviews:[ReviewInput...]}`一次封存完整同范围题目。真实assistant、四维依据、question-purpose-v1、当前subjectSHA及policy必须一致；应答只返`id/sha256/created_at`。保存封存后响应丢失，按相同请求重放，不能改分或开第三轮。 |
| 5 | 原 `POST /experiments/{eid}/reviews` | 逐题提交与该执行封存完全一致的判断；固定请求键不变。两轮封存前，GET reviews/observations不暴露第一轮判断。旧单轮不隐式导入。 |
| 6 | `POST /experiments/{eid}/review-independence` | 不同于两轮审核者的总控admin提交`seal_ids[2]`及`artifact{commit,path,sha256}`。Git路径限受控review Markdown，hash按Git blob字节；服务端核验完整结果、hash和时间顺序。总控须独立检查实际执行来源/模型/原件和无先看评分，不能仅凭换ID签署。 |
| 7 | `POST /experiments/{eid}/calibrations` | 必须显式`quality_policy`，与实验相同，双轮有效且无unknown/未核实来源/关键错误才创建。两轮取最低有效分，低分如实保留；不靠平均分通过。 |
| 8 | 独立候选请求 | 绑定`baseline_experiment_id`与`quality_calibration_id`；有回归来源时，`regression_calibration_id`须相同。创建、job和每题前重读基线/校准/来源/选题范围，配置必须预先冻结，不能覆盖父配置。 |
| 9 | `GET /experiments/{eid}/development-gate?calibration_id=...`；原regression-proof接口 | 服务端重读当前质量/来源/题级执行关系和顺序。proof标注`purpose=development_acceptance`、`automatic_publish=false`、human pending；客户端不可提交passed。 |

未知追加使用 `POST /experiments/{eid}/reviews/{review_id}/development-resolutions`，仅原审核者解决本人该轮全部unknown；请求保存新原件manifest和逐维resolution，不改确定分数或原记录。追加后旧独立性证明不再有效，总控须对新resolution hash再核验。未核实来源的旧判断不能通过该接口变成“已核实”。事实不得N/A、操作适用性不能翻转、实际答案图不能跳过，关键错误只可保留或增加。

`release-gate`、revision quality-proof和发布门禁固定human-only，不能消费开发校准。前端对policy实验仅展示受控流程已允许读取的记录；政策操作由受控执行接口完成，不让用户逐题填170条。

随机隔离验证中，供应商/审核/原件均为明确合成夹具，并有同库/分库、首次快照前退出、结果发布前退出、幂等、错误身份、盲审顺序和旧human对照。实现已独立通过，合成结果仍不代表真实答案质量。接续按召回/标签就绪→冻结配置及无生成预检→有效同范围基线双轮→预校准→独立候选双轮→真实反馈proof推进；实际审核执行及原件依据的独立性仍须总控核验，不重复索取用户已有判断。新供应商调用前须说明来源、固定身份、幂等及累计/新增/未知费用记账；本技术通过不授权立即生成。
