# M7运行环境：资源故障定位与启动门禁

本次在已推送`5156971`后响应“继续推进”，只调查本机新隔离项目和Windows/WSL/Docker资源；没有新模型派发。

## 根因证据

Docker Desktop的WSL内核日志记录global OOM，并杀死既有主项目Mongo (`mongod` RSS约4.87GiB)。Docker backend同期对内部`/ping`出现21条deadline超时，另报累计OOM kill计数5。原Mongo只读serverStatus显示resident约4.77GiB、WiredTiger最大缓存约3.30GiB、当前约1.64GiB。该证据说明全局内存压力与Docker超时相关联；不推断为唯一根因，也不据此改主库缓存、内存限额、容器或重启服务。

发现期间Windows首样本可用物理内存约0.52GiB；Docker daemon内存上限约7.60GiB。只停止本轮新项目`zh-m7-23a6e6`的所有容器，保留全部容器及卷；原项目保持运行/由既有restart策略恢复。未执行down、删除、prune或模型服务启动。

## Linux可复现边界

Ubuntu WSL中最终源码快照可compileall，Linux私有配置权限600、工作目录700，固定Windows Docker CLI桥可解析私有runtime和Compose覆盖；该操作没有启动容器。Docker daemon仍由Docker Desktop/desktop-linux提供，不是原生Ubuntu daemon。

当前最新只读预检测得宿主可用物理内存1,719,939,072字节（约1.60GiB）；daemon总量8,162,193,408字节，运行容器采样6,919,180,774字节，估算余量1,243,012,634字节（约1.16GiB）。低于预览要求的宿主2GiB及daemon余量3GiB，故未重新部署。该统计只是一刻快照；daemon/VM额外消耗、内存增长与可持续容量仍未知。入口停止后不可用是预期结果。

## 代码保护和验证

`preview.py create`现在在创建配置前和镜像构建后分别运行只读资源检查。host API失败、daemon查询超时、stats格式/容器状态未知、内存不足均拒绝；拒绝时不建目录/服务（构建后失败则保留配置/镜像但不启动），不自动停其他Compose项目、清理日志/卷或降低阈值。当前阈值是本机安全启发式，不是模型/生产容量证明。

定向回归37通过、1个Windows symlink用例skip；包含单位/畸形值、未知采样失败关闭、OOM现场量、daemon超时不重试/不泄密、其他容器统计、创建前拒绝及构建后资源下降不启动。Linux源compileall和Compose config exit0；部署被资源门禁明确拒绝。详细文件hash及私有日志索引见[脱敏validation](M7-runtime-resource-recovery-validation-r2.json)。

## 下一步

执行方继续负责：等有资源余量后运行`python -m scripts.operations.runtime_resources`重核；通过后才重启本轮API/web并观察ready和稳定性。若依然不足，需要获授权维护者释放/增加可用内存，或单独评估既有主项目的资源配置/停写窗口；本轮没有修改该主项目。M7真实问答需要另外的新批明确授权，当前不启动。M6保持5/7，04验收，05/08 open。
