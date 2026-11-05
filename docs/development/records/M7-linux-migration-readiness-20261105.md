# M7 Linux迁移就绪核验

日期：2026-11-05，Asia/Shanghai。用户确定后续运行目标为Linux服务器，并明确Windows Docker Desktop资源不足可以跳过。本轮无新增真实provider调用或本地推理。

## 本机可复现检查

Ubuntu WSL2（Linux 6.6.114.1-microsoft-standard-WSL2，Python 3.14.4）检查结果：

- `python3 -m compileall -q app scripts`：退出0。
- 现有冻结候选 `compose.delivery.yaml` + `M7-operational-r1.compose.json`，采用本机既有私有runtime执行 `docker-compose ... config --quiet`：退出0；不打印配置值。
- WSL Docker integration 未启用，WSL内没有可用Docker Engine，因此未在WSL启动或重建容器。Linux语法与配置解析不等于Linux容器实际部署或目标服务器实测。
- Docker Desktop当前已有内部候选只读检查：`/health/live=200`、`/health/ready=200`，Mongo、MinIO、Milvus、Redis为ok，模型及工具均disabled。没有启动worker的新任务或产品模型调用。

## 目标和剩余范围

依用户本轮决定，不再以Windows Desktop宿主可用内存或daemon余量门槛阻塞Linux迁移准备，也不把该Windows快照外推到Linux。目标主机容量、cgroup、Docker Engine、持续稳定性必须到真实目标环境实测；本轮没有目标服务器，因此M7-02的Linux实际部署验收仍open。

已知M7-operational-r1因资料准备首失败进入STOP/halt；provider stream为0。候选源修正提案r2使用新批次、新账户和新请求身份，旧批未消费额度不转移。当前工作只完成Linux无调用准备，未重启旧批或执行提案的新stream。本记录不授权外部部署，也不表示新真实模型调用已获批。

下一项由执行方承担：取得明确的新批调用授权前，保持零provider；目标Linux服务器实际可用后，在该主机按冻结r3候选和隔离配置完成构建/启动、健康/SSE/Range/凭据隔离验证，逐项记录目标资源。M6仍5/7，04保持，05/08 open。
