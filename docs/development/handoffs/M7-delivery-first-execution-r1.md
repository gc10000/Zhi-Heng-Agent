# 下一执行Agent完整Prompt：交付优先与M7工程建设

下面全文可直接作为下一执行Agent的用户任务。用户采用此Prompt执行，表示授权其中的工程建设顺序调整；不包含额外付费模型调用、子Agent委派、合并main或外部生产发布。

---

你是本项目下一位交付执行Agent。现在将推进重点调整为“先把产品工程和部署交付做完整，再持续优化答案质量”。请直接读取仓库、连续完成下面整个工作包，不停在复述计划、重复阶段数字、等待全量质量重评或让我填路径/重新选架构。

一、当前仓库及真实状态

- Windows/PowerShell，Asia/Shanghai。
- 主仓库：D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag
- 开发工作树：D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.worktrees/m6-source-bound-comparison
- 分支：codex/m6-source-bound-comparison。已知功能基点5225e8fb8bfbf634fd46b6e41b09a8df1dc30ecd；规划文件可能有后续提交，启动后只读核HEAD/origin/实际远程和差异，以实际新状态接续，不回退。
- main仍以实际核验为准；不要切main实施，不擅自合并、强推、reset或清理tmp。普通提交和push已授权，显式暂存，不git add .。
- Python使用主仓库.venv/Scripts/python.exe，工作树没有独立.venv；不盲目全量sync破坏CUDA环境。
- Vue 3/TypeScript/Vite、FastAPI/LangGraph、MongoDB/Milvus/MinIO、Redis/Celery保持；不重选模型、embedding/reranker或检索方案。
- M0至M5既有验收保持。M6仍5/7，04保持、05/08open。此前已完成168真实provider stream、170结果、340独立判断，usage809676/30791；两gate blocked、proof存量0，账本halt。不能写成尚未调用，也不能重用旧槽/改原分。
- 5225e8f已补修来源关系提示、内部规则外泄拒绝、澄清呈现快照；自验389离线/101隔离Mongo/62前端单元/6浏览器及类型构建通过。三连接算法未改；新差异独立技术open，补修后真实答案质量未证。

二、本次工程授权和推进原则

本任务授权启动M7开发、构建、本机隔离验证及完整发布候选准备。明确允许M6-05/08保持open时开展上述工程工作，不再让完整双版85题复评阻塞M7建设。先同步计划/依赖例外、REVIEW_STATUS/DECISIONS，注明这是工程推进顺序调整，不是M6质量通过。不要勾选未满足的旧验收项、改旧门禁/rubric/评分或伪造proof。

这次不授权新付费模型调用或子Agent委派；旧168范围已消费。不要自行启动或唤醒任何Agent。需要新调用/独立复核时，先做完可审阅准备、列出准确预算/身份/范围，再一次提出授权；等待时继续其他独立任务。本任务也不授权外部服务器写入、公开发布、合并main或公开Release；这些必须在完整候选及回滚准备后办理最终批准。heldout/M7之外新功能、旧43题、基线重跑不做。

不要把全量质量零下降、适用性分歧清零或通用自由答案语义校验作为每个工程任务前置。已知错对象/操作时序问题仍记为真实缺陷；内部预览明确需核对原文和人工确认，不能以免责声明宣称修好。公开开放相应能力前应定向确认或明确限制范围，并如实保留原质量未通过结论。不要把完整回答偷偷降为摘录以提高通过率。

三、先读这些材料，再立即实施

读取适用AGENTS.md、docs/development/GIT_WORKFLOW.md、PROGRESS、REVIEW_STATUS、docs/plans/DEVELOPMENT_TODO.md、DEVELOPMENT_CONTRACTS.md、docs/plans/tasks/M7-delivery.md。
读取docs/superpowers/plans/2026-11-04-delivery-first-r1.md、docs/development/reviews/M6-candidate-quality-repair-r1.md、docs/evaluation/M6-feedback-candidate-development-quality-r1.md及相关实际源码。
现有compose.yaml和deploy/worker可复用；M7任务中列出的应用镜像/健康/备份文件只是计划，先用rg核实际存在和接口，不照文件名臆造接线。

四、连续完成三个工作包

工作包A（M7-01/02/03）：环境与可运行部署。
固定依赖/镜像/Node和CPU/GPU路径，保护当前虚拟环境；补齐API、Vue静态资源、Nginx同源代理及worker/存储拓扑，SSE禁缓冲、PDF Range和受控引用可用，密钥留服务端。采用独立compose项目名、端口/卷和合成命名空间做本机预览，不覆盖现有服务。实现/复用live/ready，分类存储/模型/配置错误，健康探针零收费推理。实际构建、启动、验证并写dependencies/ubuntu-deploy runbook。

工作包B（M7-04/05/06）：备份恢复、故障容量、权限交付。
实现绑定Mongo/MinIO/Milvus、活动修订、版本/hash及权限的备份清单和防误覆盖恢复。用自制可再分发小样实际在独立目标恢复，核原件/索引/引用/注册关系及回切。隔离测试worker停止、429、存储故障、SSE断开、恢复不重复和1/2/4会话；合成供应商故障链不能冒称真实模型容量。核跨用户Run/citation/asset、路径穿越、危险Markdown/XSS、签名资源、镜像/前端凭据排除。验证5225e8f输出拒绝与澄清快照在部署组合中正常工作，但不自签独立通过。

工作包C（M7-07/08/09）：复现与发布候选。
沿用知衡/Zhi-Heng命名，整理README、贡献/许可证/复用来源、自制样例、quickstart和真实后台演示路径。串起登录→资料→问答/澄清→引用→支持草稿确认→反馈→任务恢复；模型生成若无新授权明确留缺口，不能以mock/旧答案充作新真实生成。完成可用干净环境复现。交付固定SHA/镜像身份/配置模板/安装命令/测试/备份/回滚/已知问题/可公开文件清单；分别标识构建、本机预览、目标环境实测和公开发布状态。

五、如何避免再次停滞

一次盘清既定M7九项，按依赖连续推进；遇Docker/GPU/目标环境不可用，记录真实缺口，立即继续其他可完成工程，不重复跑无关历史审计，不把环境未测写成通过。自行从已有配置/脚本/部署记录定位环境，不要求用户查PDF、模型目录或填写占位路径；不得读取private-identity，既定服务凭据只由相关运行工具静默消费，不打印或提交.env值。

维护一个具体清单：本次必须完成的工程、公开发布前需确认的实际阻断、上线后优化债务。提示冗长、一般措辞、非关键质量优化和全量双轮复评后移；越权、凭据泄露、数据丢失、错误终态及已知错误操作指引不能冒称已解决。

测试以受影响行为为准，保留失败和补修记录。Mongo故障仅用随机短m1_test_m4_隔离合成库，独立对象/向量命名空间；不改真实Run/lease/slot/blocked账户。output/evals/PDF/日志/缓存/权重/原始判断不提交。新增配置同步.env.example和CONFIGURATION。

六、交付要求

维护PROGRESS、REVIEW_STATUS、TODO、M7逐项记录、contracts、CONFIGURATION、CHANGELOG、DECISIONS及交付报告；仅实际满足的任务才勾选。报告分清实现自验、独立技术、真实模型质量和发布批准。
显式暂存、普通提交push当前分支，核本地/origin/实际远程。持续到所有当前授权且可执行工作完成；最终给出实际入口/启动命令、完成项、剩余真实缺口、候选SHA和下一次所需授权的具体范围。不要声称M6已通过、产品已公开上线或所有问题都已发现。

第一条回复简要说明“本轮转向M7交付工程，M6质量债务保留；先核仓库和部署拓扑，再连续完成三个工作包”，随后直接读库实施。
