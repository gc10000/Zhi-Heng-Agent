# M7隔离工程容量与故障范围

2026-11-04；Windows Docker Desktop/Linux；引擎内存上限7.602GiB；RTX4050 Laptop 6141MiB，驱动610.60。未新加载模型。采样时GPU已用382MiB不归因本任务，不是本轮峰值。

| 工作负载 | 最大会话耗时ms（一次多接口组合） |
| --- | ---: |
| 1会话 | 712.15 |
| 2会话 | 145.19 |
| 4会话 | 235.43 |

四个独立合成用户，经实际同源Nginx访问me/资料/产品/Run/引用/PDF Range、SSE断连恢复和生成拒绝；首事件16.42ms时Run尚未终态。不是LLM首token或真实导入+问答容量，不以冷/暖缓存一轮结果宣称性能提升。并发上限只测4，未测更高。

采样（非峰值）新项目API123MiB、web15.89MiB、worker53.11MiB、dispatcher71.85MiB、Mongo248.6MiB、Milvus121.7MiB、MinIO99.36MiB、Redis5.91MiB、etcd26.94MiB。旧Mongo同时占约4.221GiB，保持未操纵；共享主机有资源干扰，不能套用生产容量。真实峰值内存/显存与生成吞吐unknown。

worker停止/恢复、重复消息一次attempt、缺模型宿主明确失败、MinIO unavailable/recovery、SSE持久游标通过；供应商429/超时/断流/非法usage由同API镜像的合成集成验证，不等于真实网关压测。日志与资源采样只留本机output，细节见[M7报告](../development/reviews/M7-delivery-first-r1.md)。
