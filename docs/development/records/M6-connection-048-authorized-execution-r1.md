# M6连接048完整授权执行记录

## 2026-11-03 · 048已正式执行并在供应商前失败封存；输入顺序补修自验完成

用户明确授权后，已连续完成Git授权/引用、完整r4冻结、4次现场Strong标量582成员核对、实际模型权重/runtime核验及唯一正式job。experiment `0c3c2f9c-811f-475f-a418-3f42c20f32b3`、Run `0eeb1e48-b010-4eec-b129-31aa88226d10`，attempt1，均failed；持久遥测provider invoke/stream=0/0、usage=0/0，新账本未创建/预留/结算，halt已封存。真实检索及本地embedding/reranking已执行，有本次正式记录写入；旧账户及累计56239/30516保持。不重试，不把无答案记成质量拒绝分。

实证根因是freezer按检索后产品顺序写prompt，而正式Run按题目输入顺序；来源/引用/装配/分组/预算相同，只有展示顺序不同。补修freezer遵循原题顺序；1红/1绿后83离线、4同/分库正式合成job通过。r5完整582重冻，prompt `dd72ee38868e3b0780d5fcc670ecad3f01e10aebb4a004bd85884c69f099b225` 与本次真实Run重算结果一致，调用前独立持久输入hash亦核清；r5是关闭catalog，不授权二次派发。

本轮授权引用接线与freezer顺序修复为总控实施自验，补充变更尚无不同身份独立技术复核；原7c1288a独立报告及三算法关闭保留。没有新真实答案，M6仍5/7、04保持、05反馈复评proof与08候选质量/阶段证据open。下一步定向复核两项补充变更，再经新单题明确授权验证完整答案；43/heldout65/M7不启动。本轮未另委派。详见[完整执行与补修报告](../reviews/M6-connection-048-authorized-execution-r1.md)及同名validation.json；以下历史按时点保留。

命令与原始过程见私有authorize_and_prepare.py、execute_one.py、audit_execution.py、diagnose_no_call.py、seal_no_call_failure.py、final_saved_audit.py及各轮日志；未重新运行旧脚本覆盖历史。Git授权正文fafd2ca、引用5a73e3e；源码补修及最终交付SHA由提交后的接续核验补记，不自包含伪造。
