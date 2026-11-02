# M6-048授权执行前置与风险档案绑定修复记录

日期：2026-11-02

## 范围

响应用户一次性授权，对 `support-v1-048` 进行执行前核验。只读检查正式catalog、注册题集、maintainer范围、正式控制库计数和旧消费账户；修复比较风险档案未区分来源实验数据库与本次EvaluationService控制数据库的问题。没有创建真实实验、Run、槽位、Git授权或输出manifest。

## 修复

比较风险授权现在可通过 `evaluation_control_database` 固定本次正式评测账本。通用成员构建器仅当该专用profile提供该授权解析器时使用；其他风险profile保持以来源母清单数据库为准。owner/KB、题集、题号、配置和源码约束保持不变。

## 验证

新增用例先在旧实现上失败，再通过修复；跨库授权冻结、正式配置校验及未授权控制库拒绝均由真实risk档案函数执行。风险档案与service准入关联单测16通过。实际Mongo只读复核确认正式控制库仍未产生新记录，旧048账户原样blocked。

## 未完成与退出条件

正式执行入口在 `app/evaluation/query_adapter.py` 调用 `runtime_versions()`，其配置的本地embedding/reranker目录均不存在。现存候选模型目录只读hash后，候选模型和当前代码指纹都与冻结配置不匹配，prompt指纹匹配；未下载、未改路径、未执行推理或调用模型。故本次停在实验创建前，答案质量没有证据。风险档案修复只有实现自验，需独立技术复核后才能标技术关闭。

恢复与冻结配置相同的代码和模型身份，或形成新的冻结运行身份并完成独立复核后，重新计算代码、prompt、embedding、reranker、provider runtime指纹；仅全部匹配且风险档案修复独立通过时，才可继续使用尚未消耗的单题授权准备manifest。任一差异都停止并重新形成有界方案。M6维持5/7，43题继续暂停，heldout未运行，M7未启动。

完整定向记录见[执行前置报告](../reviews/M6-comparison-answer-048-preflight-r1.md)与[验证摘要](../reviews/M6-comparison-answer-048-preflight-validation-r1.json)。
