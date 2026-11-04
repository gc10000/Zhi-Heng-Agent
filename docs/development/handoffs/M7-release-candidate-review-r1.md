2026-11-04执行更新：用户已明确授权1位未参与实现Agent；唯一审查者`/root/independent_m7_candidate_review`已执行。原冻结范围保留如下。发现的恢复竞争/重排协议两项缺陷由总控补修，候选r3、自验及最终身份见[补修报告](../reviews/M7-candidate-review-repair-r1.md)；原审查者继续复测并签署独立报告。以下未授权表述仅代表提案原时点，不撤销本次授权。

# 固定M7内部候选定向独立复核范围 r1

源码候选固定`ebb8ef93ddca4b41d736f23e980c59fb03f02b10`，镜像/证据以M7-delivery-first-validation-r1.json为准；最终回复SHA为后续安装锁及文档冻结提交，分支codex/m6-source-bound-comparison；main未合并。用户当前只授权工程执行，不含新Agent委派；本文件是具体可审阅请求，不自称已获授权。

拟授权范围：仅一位不同身份的技术复核者，默认只读本机http://127.0.0.1:18080、源码/镜像身份及封存证据；不新模型调用、不启模型宿主、不访问private-identity、不写真实业务库、不修改旧lease/slot/gate/proof。新增provider stream/本地推理预算均0，费用/供应商HTTP不适用且不虚构0费用观测。若需重现合成存储边界，仅随机短m1_test_m4_及独立桶/集合；不复用任何失败恢复目标。

核验点：Windows CPU/GPU安装/导入证据与官方wheel hash（不重做推理或动主CUDA）、镜像/锁/源码hash，PROJECT_ROOT无.env启动，受控宿主重排协议，live/ready零推理，生成硬关闭，SSE终态前flush/断线游标，个人Run/引用与KB资产权限，原件Range，复合索引有序快照、三目标防覆盖及实际绑定回切；文件公开候选清单/许可限制。复核只需受影响边界，不重跑M6整轮、旧43、基线或heldout。

目标与回滚：仅本机随机项目zh-m7-05d09f；原项目zh-m7-6a86a0已停但卷保留。只读检查无回滚写入；合成故障按failure-recovery runbook finally恢复本轮服务；新恢复失败目标保留并停在失败，不删除锁或覆盖。不因复核未获授权阻塞本轮已完成工程交付。

独立结果需逐项passed/open/证据限制，不能把实现自验签成不同身份独立通过。该请求不包含Ubuntu外部服务器部署、合并main、镜像注册表上传或公开Release；这些应针对具体目标、访问范围、质量限制和回滚另行批准。新真实质量请求也须另有新身份/精确输入/预留结算方案，不搬旧槽。
