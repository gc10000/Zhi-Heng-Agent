> 2026-11-04补修更新：当前运行候选已升级r3，见[补修报告](M7-candidate-review-repair-r1.md)。原r1报告及镜像证据按历史保留；已有runtime.env仍含旧tag，恢复必须使用补修报告的r3精确覆盖。独立复核结果另由审查者签署。

# M7交付工程与内部发布候选 r1

2026-11-04；分支`codex/m6-source-bound-comparison`，启动锚`fe2d957b35256907d1e990ff66f8362fc267c1e3`。本报告为同一执行方实现自验，不是独立技术通过、M6质量关闭、Ubuntu主机验收或发布批准。最终源码提交锚`ebb8ef93ddca4b41d736f23e980c59fb03f02b10`；后续文档及Windows模型安装锁补充不改变应用源码/镜像，镜像与证据hash见[脱敏清单](M7-delivery-first-validation-r1.json)。

## 可用交付

实际入口 **http://127.0.0.1:18080**，当前独立项目`zh-m7-05d09f`，合成数据库`m1_test_m4_dlv_05d09f`。主仓库Python不改CUDA；从当前开发工作树启动：

```powershell
$py='D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.venv/Scripts/python.exe'
& $py scripts/operations/preview.py status --env-file output/m7-delivery-first-20261104-r1/clean-preview/runtime.env
& $py scripts/operations/preview.py copy-password --env-file output/m7-delivery-first-20261104-r1/clean-preview/runtime.env
```

用户名preview_admin，密码只在本机私有文件/剪贴板，不写报告。新机器按[quickstart](../../runbooks/quickstart.md)创建全新项目；API/worker/dispatcher共用轻量镜像，Vue/Nginx同源入口、Mongo/MinIO/Milvus/etcd/Redis均独立卷/队列。原compose和原业务账本未用于故障写入，第一预览项目已停止但所有卷/失败保留。没有操作旧服务的stop/recreate、改指针、改评分或清理tmp。

| 状态 | 实际结论 |
| --- | --- |
| 应用构建 | API CPU轻量锁定安装、Vue frozen install/typecheck/build、Nginx配置通过；镜像身份封存 |
| 本机预览 | Windows Docker Desktop/Linux容器，两个全新项目/数据卷复现；当前最终镜像可用 |
| 目标环境 | Windows全新CPU/GPU环境安装/导入与CUDA设备可见性通过；独立Ubuntu主机未实测 |
| 公开发布 | 未执行；未合并main、未推镜像注册表、未建Release或写外部服务器 |

## 三个工作包

A：固定API完整传递hash锁、Node22.17.1/pnpm11.25.0、基础镜像digest与实际MinIO源码/image ID；保护现有torch2.10.0+cu128三件套；另建短路径CPU/GPU环境，锁定共同依赖及官方三件套wheel hash。新增live/ready分类，模型仅配置/已加载状态，不预热推理；新预览明确关闭生成并在写Run前503拒绝。补齐受控宿主rerank桥接，保留原normalize=True、候选及分数排序逻辑。Nginx禁SSE缓冲、转交Range，使用Docker动态DNS处理API换IP；服务端秘密不进前端。

B：停写跨存储快照绑定活动修订、权限/用户摘要、Mongo索引/选项、完整向量与原件hash/版本；外部manifest hash必填、三独立新目标、防覆盖及失败保留。实际恢复17集合/5对象/6向量，切换API到新目标后登录/引用/PDF Range可用，再回切源三元绑定；源未覆盖，会话不恢复。不是只生成压缩包。该工具当前只放行隔离小样，不是生产热备；真实模型恢复后问答未执行。

worker停时任务pending/attempt0，dispatcher实际入队；worker启动后保存解析检查点，并因无模型配置明确失败，重复消息无第二attempt。MinIO停止时live200/ready503，恢复ready200。SSE断连按持久游标恢复，终态前即可收到首事件。跨用户Run/引用拒绝；共享资料资产按KB授权，撤权拒绝；CSRF/Origin/路径穿越、原件Range、危险Markdown单元与镜像秘密排除已检查。没有以KB共享资产误称个人私有资产。

C：知衡/Zhi-Heng命名、贡献/来源许可、自制CC0样例、quickstart、实际后台演示、故障/恢复/回滚及公开文件候选清单已准备。新数据卷复现不是另一独立Ubuntu主机安装。浏览器访问真实部署后台，无API mock：登录→资料→合成历史Run/引用原件→支持草稿确认→待审反馈→刷新恢复；新生成实际503。工程Run正文明确非模型答案，待审反馈不是M6 proof；真实问答/澄清新生成仍未执行。

## 定向验证

原始证据只保存在`output/m7-delivery-first-20261104-r1/`，不提交。各组有重叠，不累计为唯一总数或质量分。

- 最终主机定向离线/契约29通过、Windows符号链接1项skip；该路径另在Linux候选镜像实际验证拒绝成功。
- 修复后的备份/恢复组10通过、1项Windows skip，含真实隔离Mongo/MinIO/Milvus往返及恢复后仓储重新构造。
- 相关主机隔离集成首轮41通过/3失败（未配置测试桶）；新独立桶补核3通过，保留5条PyMuPDF已有弃用警告。
- 最终API镜像加独立测试工具层47项通过：合成429/超时/断流、输出拒绝及澄清快照、原始usage边界与持久Run恢复。测试只在随机m1_test_m4_库、供应商替身下执行，不证明真实网关、模型硬限或质量。
- 前端62单元、类型检查/生产构建通过；同源真实后台浏览器用例1通过。早期同题浏览器1通过与最终轮重叠，不算2个场景。
- 新清洁项目1/2/4 HTTP会话组分别最大712.15/145.19/235.43毫秒；每个会话是多接口存储/合成事件工作负载，非单请求或LLM延迟。首事件16.42毫秒且运行仍running。无真实模型容量/吞吐或峰值显存证据。
- Windows/Python3.12.7全新CPU/GPU环境各171包pip check通过，FlagEmbedding/Transformers及7个服务组件导入通过；CPU为2.10.0+cpu，GPU为2.10.0+cu128/CUDA12.8且RTX4050可见。只核安装与设备，无权重加载、推理或显存容量证据；原CUDA三件套版本保持。官方hash锁与已装版本匹配dry-run退出0，不伪称另做一次安装。
- 最终API镜像276文件、前端485文件有限审计通过；检查本轮合成秘密、.env/私有目录、默认镜像环境及API源码内容hash；不冒称扫描所有历史日志/凭据或完整漏洞审计。静态资源保留实际包许可记录。

完整命令、退出码、日志hash和镜像ID见脱敏JSON及本机收据。应用API/web/MinIO镜像已另存本机application-images-r1.tar（不含运行env/卷，不上传），hash与字节数封存；固定image ID覆盖文件见releases/M7-delivery-r1.compose.json。恢复演练时HEAD仍为fe2d957，manifest源版本字段不是最终源码冻结，最终代码身份另见候选清单。OpenAPI与当前工厂全等，前端schema已同步。MinIO完整干净源码重建本轮未执行，复用已核固定源码本地镜像；查询Go/Debian基础镜像digest时网络失败，不能冒称完整重建路径已验证。

## 失败与修复保留

1. pnpm11阻止安装脚本：精确允许oxide/esbuild/vue-demi后构建通过，未全局放行。
2. Desktop internal网络不发布宿主端口、一次别名丢失：改独立bridge，仅重建本轮项目；旧卷不删。
3. API替换后Nginx仍用旧IP：保留502与两侧IP证据，动态DNS修复，并在恢复切换/回切实测。
4. 初版备份canonical排序改变Mongo复合索引键顺序：真实恢复目标启动失败；红测后改为有序键对并显式记录格式，旧不充分清单拒绝，失败目标不改；新目标恢复/回切通过。
5. 镜像内根目录定位依赖.env：34失败/13通过暴露模板未加载；镜像设置PROJECT_ROOT=/workspace后47通过，不复制.env绕过。早一轮容器测试4个导入错误为PYTHONPATH配置，保留。
6. 一次构建Docker连接EOF/短暂引擎不可观测：未手动重启全局引擎；限制前端构建内存/并发后重建成功，不凭此断定全部根因已明。
7. 测试同名模块收集冲突已重命名单元用例；最初恢复网络前置未显式开放、保存旧失败。
8. 首次GPU离线安装缓存缺torch而拒绝；随后官方索引安装成功。深层工作树CPU环境虽pip check通过，Transformers常规open在260字符路径失败；扩展路径证实文件存在。保留失败环境，在主仓库output/m7i-r2短路径建全新CPU/GPU环境后导入通过，不修改注册表或主CUDA。所有红测/失败目标/日志保留。

## 剩余边界与下一动作

M7-01 Windows CPU/GPU安装、M7-03健康、M7-06限定安全交付检查、M7-07命名来源文档满足本轮实现自验；其余任务的已完成子步骤分别勾选，Ubuntu目标、真实问答容量/演示、生产级备份范围及独立最终验收仍open。工程候选已完整准备，不以全量质量复评阻塞本机交付。

M6仍5/7，04保持，05缺真实反馈复评proof，08缺有效新候选完整质量与阶段证据；原168/170/340及usage809676/30791、两blocked gate、0proof和halt保持。新增真实provider stream0、本地推理0；模型usage不适用（未调用），供应商HTTP观测/费用为null，不将渲染字符当token。已知质量问题见[M7质量债务](../../evaluation/M7-quality-debt.md)，不能靠辅助草稿提示宣布修好。

下一具体候选动作是[固定候选的定向独立技术复核提案](../handoffs/M7-release-candidate-review-r1.md)：零模型调用、默认只读本机预览与封存证据，不含Agent启动、外部部署或公开发布的现行授权。正式公开前还需课程再分发许可/AGPL等义务核清、访问安全配置与已知错误能力的定向真实确认或明确受限范围接受。未虚构目标服务器/登记ID/付费上界。
