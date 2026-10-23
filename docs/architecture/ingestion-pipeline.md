# M1同步知识导入与回看

`IngestionService`注入范围仓储、ParserRouter、V2Index、OriginalStore、AssetStore、图摘要服务和嵌入函数；`import_file(path,request_id,expected_active,document_id=None,name=None,product_ids=(),purpose='unknown')`贯通已批准M1领域能力。它是同步Python入口，无新HTTP任务路由、Celery或M2运行协议。服务只操作注入仓储及对象前缀；调用端在后续API阶段提供鉴权，不从文件名推断归属。

先验证真实格式和适配器，再注册资料/修订。原件与解析JSON分别按hash存储，解析中间产物记录hash/版本；图片来源身份冻结并保存对象字节快照，重试从快照恢复，不受本地同路径图片替换影响。MinerU自行复用成功段。处理模型/prompt/切片预算/解析配置身份绑定修订，换配置需要新修订。图摘要必须completed，pending/failed或缺失/远程未解析图片抛错误并保留当前失败attempt，原活动版本不变。解析得到project_plan用途时只将未知用途补全，显式technical分类不被覆盖。随后结构化切片、双路编码、读回验证和CAS发布。调用者必须传入期望活动指针，不能无条件覆盖新版。

失败记录只保留异常类型，不把供应商响应、链接、密钥写进状态。只有当前staged attempt可以置failed；已validated/切换指针窗口由Publisher核对，避免把已发布结果改成失败。完成请求重试不重解析/编码，也不会把后来已回滚的版本自动激活。

`read_original(revision_id)`按授权仓储读取原件并校验hash；`read_chunk(revision_id,chunk_uid)`只能读该修订的切片；`read_asset(revision_id,asset_id)`先查资料/修订关联再读取并验hash。这些领域方法尚无外部下载URL/API。Markdown本地配图以asset_ids关联原图/摘要，原文图片语法保留；未建立的远程图片不可视作可回看的原图。真实来源精度按PDF物理页、Markdown行/章节、Excel sheet/cell分别保存。

本机隔离验收命令和付费开关见records/M1-11.md。测试默认禁止网络；真实测试须显式M1_TEST_DB=m1_test_前缀。真实供应商单独需要M1_LIVE_PROVIDER=1。当前旧导入/问答公开入口保持原链路，M2后再切新任务入口。

运行限制：同步导入需调用方持有本地原件路径和有效解析work_dir；大规模任务调度/下载鉴权在后续阶段。缓存租约过期、上传成功但本地确认前硬崩溃不承诺供应商exactly-once。MinerU若provider.json保留batch_id但uploaded=false，应先核对供应商批次；原批次可取结果时沿用，确认未上传且临时上传URL不可恢复时，保留原provider.json副本，再明确标记failed=true后重试建立新批次，旧batch进入previous_batches；不改成功segment.json。此人为恢复窗口未做破坏性真实故障演练，不能声称所有供应商崩溃窗口自动恢复。

审查修复版本：MarkdownParser.version=2，chunking.VERSION=2，处理身份包含两者。旧处理身份与新版不同，旧请求继续处理会明确ConflictError，需新请求创建新修订；历史read_original/read_chunk/read_asset不重解析。Markdown表格row_numbers是物理行映射，首个SourceRef为数据行范围，附表头独立来源；Excel数据中的短横线不能当分隔语法，PDF未知行保持null。
