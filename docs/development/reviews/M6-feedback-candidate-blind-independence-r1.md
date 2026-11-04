# M6完整候选双盲独立性总控核验 r1

2026-11-04。结论：**在可观察工具调用、原件和provenance边界内成立**。两位新Agent均以不继承父会话的身份创建，分别独立完成两版各85条完整结果，共340判断；不是同一判断重复转录。总控实施准入并运输原件，没有参与本批原始评分，不能将本报告写成不同实现身份的技术审查。独立技术结论另见[M6-feedback-candidate-independent-review-r1](M6-feedback-candidate-independent-review-r1.md)。

| 轮次 | 真实task | 最早正式begin UTC | 最晚正式seal UTC | 原始判断SHA256 | provenance SHA256 |
| --- | --- | --- | --- | --- | --- |
| 1 | `/root/feedback_full_blind_round1` | 2026-11-04T05:30:24.058042+00:00 | 2026-11-04T05:47:58.017545+00:00 | `f66d718f876a505053b1679fbbebd55c78b8128a9f6d4b16f48731f0eab3c431` | `698d29543861aa42a2adb8ab05bbb57c8f587f1c292d58cc4eeed1651ec9d8d6` |
| 2 | `/root/feedback_full_blind_round2` | 2026-11-04T05:48:24.485982+00:00 | 2026-11-04T06:04:41.668404+00:00 | `3750101c606348ec6d6c16dced303a67ec73ab8e9c2ebdf4ede383f23ecbc4a4` | `11b01032258ba3baa4266043213bb6f52a0ca52c45c4e23edba27c78568539b4` |

第一轮两版完整seal均早于第二轮任何begin。协调方在begin后发送START；第二轮只收到本轮纯输入、原PDF白名单、规则和字段/进度提醒，没有收到第一轮题号、分数、结论或任何报告。用户已明确授权两个新Agent依次盲审，未增加第三票或额外委派。两轮均禁止网络/数据库/子Agent及父目录、源码、expected、annotation、基线分、校准、其他轮产物；作者可见工具轨迹与本人声明未出现这些主动访问。系统自动元信息及工具后台轨迹无法全审计。

总控实核两轮输入、4份原PDF与作者产物hash、分批初稿逐项全等、170唯一subject、四维/类型/长度/适用性结构，以及seal和正式submit对同一原始判断hash的绑定。两审核包的170条完整答案、状态、行为、引用和候选列表均与正式发布结果相同。每轮170原件已正式运输，共340条；总控没有改分、补写判断、重定适用性、删unknown/critical或按另一轮纠错。判断原文和原PDF仅本机，不随本报告提交。

两位作者直接读取4份原PDF、提取77物理页文本，分别实际查看16和38个物理页的渲染；渲染但未查看的页面没有冒作已查看。第一轮原件含开始时间限制：未捕获精确START时刻，只有正式begin后原件访问checkpoint、作者结束及seal可核；第二轮记录START后首次时钟读数，不冒称消息精确收件时间。精确审核模型/provider、token、HTTP和费用均不可观察，保留null。

这是基于实际task、工具层可见访问、受控原件与服务端时间顺序的总控核验，**不是OS沙箱、内核访问审计或后台全轨迹证明**。独立性成立不意味着答案质量通过；原始低分、unknown、critical和分歧仍由正式政策消费者处理，human发布继续pending。评分原件hash、来源PDF的脱敏身份、正式回执hash和限制见[机器摘要](M6-feedback-candidate-blind-independence-r1.json)。
