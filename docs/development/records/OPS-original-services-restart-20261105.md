# 原项目基础服务恢复

日期：2026-11-05，Asia/Shanghai。执行锚为`d6ecf6be7fa4dad350ab29b8107b510d01d5ab35`，工作分支`codex/m6-source-bound-comparison`。用户明确允许启动，沿既有原项目停止/恢复授权执行；不扩大为新M7预览或新模型派发。

## 实际动作与结果

初始Docker Desktop未运行，引擎管道不存在。执行`docker desktop start`后，引擎恢复；既有restart策略同时恢复了此前运行的容器，包括原etcd/MinIO/Redis和原内部预览。没有对其他项目单独发送start/stop或修改restart策略。

仅对已核验属于`product-knowledge-rag`的原Mongo容器`ee05f0747fd9`执行一次start。日志显示非正常退出后从检查点恢复，初期端口拒绝连接、健康从starting到unhealthy；保留全部采样，不重启、不执行repair、不改缓存或内存配置。进程继续工作后转为healthy，再对原Milvus容器`5470c3eed59f`执行一次start并转为healthy。

2026-11-05 09:45:22只读复核结果：

- etcd、MinIO、Redis、Mongo、Milvus五项均running/healthy，当前OOMKilled=false。
- 启动前后五个容器ID和完整挂载映射相同。
- 五个原业务命名卷及Mongo原匿名`/data/configdb`配置卷均存在，共六卷。未删除、重建、清理或换卷。
- 无主动应用写入、新模型派发或本地模型推理；数据库正常恢复/checkpoint属于服务自身运行。未做全库内容审计，卷身份保留不等于全库逐文档完整性证明。

## 资源与证据边界

最终只读资源采样：宿主可用613011456字节（约0.57GiB）、daemon总量8162185216字节、容器采样6881637558字节、估算余量1280547658字节（约1.19GiB）。新增预览门禁仍因host_memory_low及daemon_headroom_low拒绝；未调低2/3GiB阈值、未启动新预览。原项目恢复依本次授权单独执行，服务健康只证明该时点可用，不证明持续稳定、模型容量或OOM风险消除。

私有证据保存在`output/m7-original-services-restart-20261105-r1/`，包括before.txt、各阶段健康采样、私有恢复日志及verified-result.json；检查脚本退出0。日志/配置/数据不提交。先前45秒等有界等待窗口退出3表示尚未健康，后续同一次启动成功；失败样本原样保留。

本次没有源码、配置或契约变更，不新增测试或业务任务勾选。M6保持5/7、04保持验收、05/08 open，旧批halt/评分/gate/proof不改。未唤醒或新增Agent。远程读取首次因配置的本机代理端口未响应而失败；Git交付实际结果另见最终回复。

下一项由执行方承担：资源门禁通过后继续零调用Linux部署实测；若仍拒绝，不追加服务。新M7真实演示必须使用新授权包，不恢复已halt旧批。
