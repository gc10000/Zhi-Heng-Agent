# M6-048下一次受控执行边界 r3

旧048 r2授权已因预调度`eval_set_version_conflict`按fail-stop封存，不能解锁、重试、退款或重领。错误来自重复登记已存在的题集，不是题集缺失、模型目录缺失或模型调用失败。新的只读路径已核对：复用登记descriptor即可；该版本dataset/manifest匹配，题集注册者仍有目标KB维护权限，正式实验和预算账户为空。

若继续真实验证，必须建立全新、明确授权的身份：仅`support-v1-048`，题集`fb-07c584730833908571fe9dd7c7c890afa3cf9e66`，模型/endpoint/SDK/提示词/检索输入/输出参数均沿已核冻结值；唯一行为差异是移除重复`register_set`并使用新experiment/request/batch/slot身份。仍限最多一个provider stream，费用上限仍unknown，首次失败停止。历史计量53089/30412不变；输入/输出预留28416/4096，累计算术上限81505/34508。实际usage、HTTP、费用按运行回执记录，缺失保留unknown。旧source-relation blocked账本和本r2 halt保持。

授权前可继续离线测试和只读预检；不得创建正式experiment、slot、Run或调用模型。只有新的单次执行授权被明确给出并绑定到新Git授权文件后，才执行一题并首失败停止。结果即使技术成功也不自动证明答案完整或质量通过；必须判断用户是否收到双方上联结论和逐项证据，而不是摘录。

本机BGE-M3和reranker-large已存在并与冻结model fingerprint匹配，无需重下或手工查账号。M6仍5/7：04保持，05缺反馈复评proof，08缺候选质量及阶段证据；43题暂停，heldout65未运行，M7未授权。
