# 048必要表行的独立原件来源审阅 r1

2026-10-30；审查对象为执行提交`12da97ed7c31bccbb7ed7a5b118917ba66293b26`的D5隔离修订。总控独立读取已保存原PDF、重新渲染并目视核对物理第30页，核对完整单元格文本与原Provider表格；不是执行自验转述，不是human声明或答案双轮评分。

## 限定通过的来源

- 原PDF SHA256：`aa246f20a8b2a059b9e2c67410d0eccc2d86f3c643cc71a7b3eff6d7acff1523`。
- Provider缓存 SHA256：`09c8e9c3f99f2e54f7d2e2e514257d1898194f022301a77aba9dd11af0ed36cd`。
- 原缓存block索引364（从0计）；HTML表格SHA256：`22abb5ea1e88b7e6dd03411f87ad91fa9c4ddd817f3dc58aa3bcf93311ba4076`。
- 物理页30，印刷页`5-1`，表5-1“故障排除”。表头第1行和目标第3行（均从1计）已核清；不扩展为整张跨页表格的出处证明。
- 第1行单元格：`常见问题`、`故障排除`。完整cell列表的规范JSON SHA256：`9a5e0fa0ec14fdf02820e3e58a8937462af48acb5602168905c0e4a6e9202f14`。
- 第3行左单元格：`设备的Cable指示灯始终不亮`。右单元格说明Cable链路未建立时检查设备Cable口同轴电缆、另一端入户接口连接；仍不亮时联系运营商确认远端机房EoC业务或网络链路故障。完整cell列表的规范JSON SHA256：`5a278ee41b4707ca14d666071dc461c8e6b178193c853cbc9ac95ddf12666bb9`。

这里的规范JSON为UTF-8、ensure_ascii=false、sort_keys=true、separators=(',', ':')，列表及字符串保留Provider原值。完整原文和本轮渲染只保存在本机新output目录；不上传PDF或截图。

## 精确映射与消费边界

本轮对应document=`006ccd8a-ff17-573b-afb6-70bc3bfae000`，revision=`f5aab7c5-8d2d-56d7-b2bc-241600ef6d19`，ordinal268，chunk=`3f9c9a54-ee87-5450-944b-3720f1075b72`。该chunk正文与第3行完整cell拼接一致；当前refs仍为page=null，本轮未写回。

本审阅只证明该版本资料中上述表头、故障条件与说明的物理页关联。不得将其扩张为所有型号/未来版本的上联结论、题目答案正确性或术语投影规则。不能把故障排查文字注入048查询来追答案。

允许执行方复用本次实际已完成的独立审阅，按已有受控原件补证方式固定本报告的Git commit/path/blob SHA256及上述原件/缓存/表格/行指纹，在**新隔离处理身份和新修订**中消费；必须保持表头与数据行关系，不回填现有修订、旧结果或旧缓存。只运输既有审阅，不另造新独立判断或要求用户再找原件。最终来源与检索配置就绪后仍需正式无生成预检；本报告本身不代表召回、答案或M6验收通过。

私有证据：`output/m6-layout-terminology-review-20261030/source-review-proof.json`、`D5-p30-source-review.png`及`source-calls-checks.json`。原PDF/Provider缓存/行文本、当前页码保持原状。独立报告与统一执行范围见[M6定向复审](M6-layout-terminology-review-r1.md)。
