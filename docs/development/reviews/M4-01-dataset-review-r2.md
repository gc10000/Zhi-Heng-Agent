# M4-01 题集修订定向复核 r2

日期：2026-10-24。审查对象：`95c372b2fad75c4536579d3951190d43f4989b93`及本机support-v1-r2。总控助手独立复核，承接[首轮题集审阅](M4-01-dataset-review.md)与[修订回交](M4-01-dataset-revision-r2.md)。

**结论：七题修订通过，关闭R1-R3和四项补充意见；未发现本次修订的新阻塞项。M4-01.2题集标注/审阅完成，可以继续独立语料、资产映射、真实配置及dev原链路基线。M4-01整体仍未验收，M4仍1/10，M5未授权。**

本轮没有运行模型、基线、heldout或真实供应商链路；付费调用和服务写入均0。原件核查仅针对七题相关内容，不重复声称重审全部50题。

## 七题逐项结论

| 题目ID | 结论 | 定向核对依据 |
| --- | --- | --- |
| support-v1-001 | 接受 | 题干/标准答案明确2014年6W100、GM/GU及该版手册范围，与LA物理第4页一致；不扩大为现售全部型号的永久事实。 |
| support-v1-023 | 接受 | 主体限定CB304n本机DHCP服务，与CB第15页表项一致；不推出其他DHCP服务器或静态配置失效。 |
| support-v1-037 | 接受 | 依据XR第3页的米家APP接入及电脑网卡要求，修订没有将所有子设备解释为直接WiFi连接。 |
| support-v1-038 | 接受 | 新第3页起始步骤与原第4页后续流程各为必需证据组；引文、顺序、物理页正确。旧第4页截图本来已有入口，不将旧版重新定性为完全缺证。 |
| support-v1-042 / R1 | 关闭 | 收窄为两项组成与默认间隔，明确绿米网关身份；与XR第11页文字及此前已核截图一致。不复述示例凭据、不冒充站号拼接语法设备实测。 |
| support-v1-043 / R2 | 关闭 | 题干和关键点均指定采集端，本轮再次目视原第12页裁图；目标字段与采集端一致，转发端同名字段不再构成题目歧义。 |
| support-v1-047 / R3 | 关闭 | 保留clarify和三资料范围，清空强制引用组；实际evidence_metrics返回组召回null、behavior true、human_answer_correctness null，没有改运行器来制造通过。 |

## 身份、内容绑定与冻结

接受新增`independent_assistant_review`，其身份与真实人工明确分开。校验器要求已审助手记录含审阅文档路径/hash、40位提交、方法、审阅人及不含annotation的原始内容指纹；原草稿与真实人工协议继续兼容。该协议校验结构与内容绑定，不是对任意调用者身份的认证，本次另由总控实际对照Git字节与来源完成确认。

独立探针分别改动问题、关键点、禁止项、历史、产品、证据引文、来源范围和split，八种变动均使旧助手已审状态被拒绝。没有将合成测试中的人工角色当作真实题集人工签字。

新旧逐项对比确认：内容只改七题，其余43题内容相同；50题ID、问题族、35/15划分、第044题历史、第047题来源范围不变。三份原件hash/页数一致，三份裁图hash与完整解码通过，完整可读稿的50份JSON与r2逐字段相同。回交快照在本次文档更新前只读通过：13个公开文件hash、16份本机证据hash、4份Python语法、210个本地链接，67份旧材料hash不变；旧快照按95c372b时点保存，不回写。

绑定对象：

- r2题集SHA256：`4a35321fc21a28f5b2986a84d8c8c77cf7c43b9da258cfe6ed3d5ebbf5e0a98c`。
- r2 manifest SHA256：`e91f599e1b180f3ad8651ebe70e987c347d78dc9c2d9b44cdf9872977635a3ae`。
- 七题不含annotation的逐题内容指纹，见[本轮独立摘要](M4-01-dataset-review-validation-r2.json)。原43题的首轮审阅仍绑定b02242b及旧内容指纹。

冻结r2不覆盖：其内部仍显示43 reviewed/7 draft、真实人工0，这是回交时状态。本次结论及独立摘要补充绑定七题当前内容，因此有效来源审阅累计50题完成，可以据此继续基线准备；无需仅为将计数改成50而改写冻结文件。以后若将七题状态内嵌回题集，另建版本并绑定本结论及七题当前内容指纹即可，不需要重新审查不变事实。

## 本轮独立验证与接续

从项目根设置`PYTHONIOENCODING=utf-8`，使用现有.venv：

- `.venv/Scripts/python.exe -m pytest tests/unit/test_evaluation_dataset.py tests/unit/test_evaluation_query_adapter.py tests/unit/test_evaluation_versions.py -q --junitxml=docs/development/evidence/M4-01-review-r2-offline.xml`：**39 passed，12.75秒，退出0，无跳过/排除**；JUnit独立解析39项，无failure/error/skipped。
- 新旧两版`app.evaluation.validate_dataset`各50题校验通过，分别显式传入r2 manifest与原split-manifest。
- 原回交`M4-01-r2-verify.py`不带`--build`只读通过；另行独立内容差异/八种变更拒绝/审阅Git字节/原件及裁图/可读稿检查通过。本机完整记录`output/evals/assistant-review-r2/audit.json`，原始证据不上传。

继续按既有M4授权建立独立三资料语料、实际索引载荷/准确图片资产映射和baseline-r2.yaml，绑定源码/prompt/本机模型权重；运行时显式使用r2 dataset、r2 manifest和新输出目录，保存本次接受结论的指纹，不混用旧检查点。完成dev原链路真实基线后才验收M4-01并推进依赖任务。

本次题集定向复核解除原题集等待项，不新增逐项许可流程。heldout继续只用于策略选定后的最终评价，不能用于调参；现有类别覆盖不均的限制保留，无质量提升或性能提升结论。未重跑历史437项、既有重导入或供应商HTTP，不将本轮39项离线测试称作供应商端到端。
