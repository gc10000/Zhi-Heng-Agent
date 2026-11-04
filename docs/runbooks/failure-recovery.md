# 故障与恢复操作

只对明确的随机预览项目操作。先核`preview.json`项目/端口与runtime.env命名空间，禁止默认`docker compose down`误触旧调试服务。

| 故障 | 判据 | 恢复与保留 |
| --- | --- | --- |
| worker停止 | Mongo pending/attempt0，dispatcher已派发 | start本轮worker；Mongo claim保护，终态重复消息无第二attempt；不手改lease或retryable |
| 缺模型宿主 | Markdown可解析，索引前配置失败 | 保留原件/parsed检查点；本轮不补供应商凭据或启动推理；真实修复后新授权范围决定是否重试 |
| 供应商429/超时/断流 | 正式Run failed，安全错误码，部分输出不冒充成功 | 合成注入验证协议；正式unknown usage不补0，沿既有账户停止和结算规则；不自动新建Run重发 |
| MinIO不可用 | live200、ready503且minio unavailable | start本轮MinIO并只读ready；禁止改旧桶policy、删缓存或用空原件替代 |
| SSE断开 | 浏览器停止订阅但Run持久存在 | Last-Event-ID只读恢复；410读冻结快照，不能重新执行模型来恢复画面 |
| API换IP后502 | 服务名直连live成功、Nginx旧上游IP失败 | 候选已采用Docker DNS动态解析；等DNS窗口后核同源live；不能长期靠重启所有旧容器掩盖 |
| 恢复中断 | restore_control failed/started与部分产物 | 保留未知现场；新目标恢复，不删锁或覆盖；源三元绑定可回切 |
| 恢复目标竞争 | 共享控制库任一DB/桶/集合claim已占用 | 拒绝冲突恢复；失败/未知/部分claim全部保留，不能改共享控制身份绕过；使用全部独立的新目标 |

复现入口`scripts/verification/fault_preview.py`要求显式host/runtime/browser合成配置及新output目录；只停本轮worker和MinIO，finally恢复。会话负载入口`load_support.py`只写标记工程fixture并验证存储/事件/权限，**不是模型吞吐测试**。不将HTTP未观测或费用未知写0，不把生成关闭后的拒绝当答案质量成功。

正式评测旧账本仍halt，两blocked gate不改；M7故障演练不恢复168已消费范围或旧43题。

## operational-r1首失败处理

资料准备误删同一行必要事实在provider前被独立截获；STOP后正式DemoLedger保存halt，8槽未消费仍不重领。修正来源只离线验证、不重新导入；本地embedding已消费5文本不退款。Docker/WSL不稳定与模型质量分别记录，完整Linux未过不掩盖也不重启旧服务。最后worker/dispatcher及宿主已停、generation=false；最终Ubuntu停止命令超时需只读确认，不宣称全部系统进程已停。恢复只观察、未知usage/费用null、不得删slot/lease/claim解锁。

## WSL宿主内存耗尽（2026-11-04实证）

WSL内核记录全局OOM并杀死既有Mongo，Docker stats ping发生deadline timeout；Mongo WiredTiger默认缓存上限约3.3GiB，实测resident约4.9GiB。主库容器按原策略自动恢复。本轮只读检查后停止自身新项目，不动原项目、缓存/内存参数、daemon或机器。preview create现有前后双资源门禁；拒绝时先核明确的资源所有者/维护窗口，不能反复启动、降低阈值或自动停止服务。
