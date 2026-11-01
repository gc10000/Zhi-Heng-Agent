# M6原句约束r2独立复核交接

本包由总控按用户要求承担实现，现交独立复核。源码修复基线：`225e78cec843c2569c24885e31a09c3af9148eb7`。实现记录：[M6-assertion-binding-fix-r2.md](../reviews/M6-assertion-binding-fix-r2.md)，私有输入与日志只留本机。

只复核三个根因的最终差异及直接受影响消费者，不重做已关闭的M6协议，也不跑模型或旧43／heldout：

1. R1：完整`prompt_used_docs`是否落Run和结果身份；current frozen attribution是否重新派生source relation/map；协调改写doc、citations、map、answer和局部proof后，首次outcome／恢复均拒绝且无新增调用；缓存读取是否验证当前策略身份。
2. R2：同／分库断流时raw片段／失败原因／输入hash是否进入持久Run，用户delta无原始JSON，Run仍失败，usage未知保留、无outcome或重试。
3. R3：同／分库空检索的不足证据proof是否精确绑定固定回答和空来源；Run、evaluation result、checkpoint/outcome一致，模型调用为0，旧策略回归保持。

实现自验108离线与契约项通过，隔离Mongo 16项通过；这些不是独立通过。完整比较仍不支持：assertion_binding_v1仍是原文摘录。不得恢复旧048槽／blocked账户，不授权新调用，不创建正式质量记录；M6仍5/7，04保持验收，05／08未验收，M7未启动。
