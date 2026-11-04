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

复现入口`scripts/verification/fault_preview.py`要求显式host/runtime/browser合成配置及新output目录；只停本轮worker和MinIO，finally恢复。会话负载入口`load_support.py`只写标记工程fixture并验证存储/事件/权限，**不是模型吞吐测试**。不将HTTP未观测或费用未知写0，不把生成关闭后的拒绝当答案质量成功。

正式评测旧账本仍halt，两blocked gate不改；M7故障演练不恢复168已消费范围或旧43题。
