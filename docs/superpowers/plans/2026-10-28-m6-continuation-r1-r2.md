# M6-08 continuation R1/R2补修计划

用户已明确要求先补修并复审R1/R2；不重复确认已授权修复。本会话按receiving-code-review、systematic-debugging、TDD与verification-before-completion顺序执行，不使用子代理。起点715f639；tmp保留，真实dev/heldout/评分/校准均不运行。

1. 保留原只读探针和r3证据，先在新本机目录复现2失败/1通过，再将新增回归加入仓库。
2. R1：M6结果logical_provider_calls取持久Run累计，另存本次adapter调用差值及计数范围。完成与澄清路径一致，未知null；汇总只用Run累计，不把复用0覆盖历史1。覆盖结果落盘前退出、重建、结果日志/汇总、未知及澄清零值。
3. R2：正式job向adapter传递当前experiment/attempt/worker身份；模型执行之前持久化题级execution link（experiment/attempt/question/input/config/checkpoint/Run）。来源是当次执行或当次观察复用，保留两者身份，不追认旧记录。continuation在创建新Run之前核验指定父experiment/attempt对应同输入、配置、checkpoint与Run的link，来源hash进入后续账本；不匹配或历史缺失明确拒绝，不自动回填。覆盖错误父实验/attempt/输入、合法链路、完成项复用关联、重复及崩溃。
4. 将R1/R2合并定向验证，补强正式job与adapter组合验证；复制独立探针到新目录做兼容性复核，旧探针保留不改。不以旧“复用差值0”断言作为Run累计契约。
5. 同步契约/workbench/前端结果类型/ADR/进度/审查交接及脱敏摘要；只读重核45证据hash及原三文件。自验不能代替原总控独立复审，M6仍4/7、04/05/08未验收、M7未授权。
6. 审查候选文件，正常提交推送，核实远程一致；不提交output、evals、tmp或原始evidence。
