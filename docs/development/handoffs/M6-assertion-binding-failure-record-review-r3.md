# M6 assertion_binding失败材料补修r3独立复核交接

实现报告：[M6 assertion_binding失败材料补修r3](../reviews/M6-assertion-binding-failure-record-review-r3.md)，脱敏摘要：[验证摘要](../reviews/M6-assertion-binding-failure-record-review-r3-validation.json)。源码基线为`82de2981235075f538ee962928ec3a5a51565c2d`。

唯一新问题：完整选择流结束后，`bind_response`因超过4096字符拒绝，但失败分支此前将未截断`final_text`存入`answer_binding_failure`。复核统一失败记录构造器是否覆盖断流和完整拒绝两分支，确认字符上限、总长度、有限失败类别、输入hash以及prompt/map/policy身份。

复核同库／分库超长非法输出集成结果：Run保持failed、持久raw最多4096字符、事件payload和公开Run snapshot无原始JSON、评测无outcome、无第二次调用。检查老断流失败材料、旧策略兼容及R1/R3正常结果不被此改动破坏。测试只用隔离合成Mongo，不跑真实调用、43题或heldout。

此包只是实现自验，独立复核待办。不能据此独立关闭全部assertion_binding生命周期，也不能将原文摘录写成048完整比较答案。M6保持5/7，04保持验收，05／08仍open，M7未启动，新048未授权。
