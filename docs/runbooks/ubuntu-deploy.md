# 同源应用部署候选

本轮只授权本机隔离预览。Linux容器实际运行于Windows Docker Desktop，不等于目标Ubuntu主机实测；外部部署、TLS域名/防火墙验收及公开Release未执行。

拓扑：浏览器→Nginx8080→FastAPI8000；API→Mongo/MinIO/Milvus/Redis；dispatcher按Mongo事实账本派发仅含job_id的消息→Redis→Linux Celery worker；模型仍在受控宿主，不进入轻量应用镜像。评测catalog为空，独立评测队列不启动消费者。所有卷/网络以随机Compose项目隔离，不设置container_name。

按[quickstart](quickstart.md)生成配置及启动。Compose只发布回环端口；Mongo/Redis仅限本机隔离演练，不是生产无认证配置的批准。生产前须准备外部TLS入口、Mongo/Redis认证、MinIO最小权限服务账户、Milvus访问限制和备份密钥管理，候选不得直接改成0.0.0.0公开。`M7_GENERATION_ENABLED=false`为本轮硬限制，不以免责声明替代已知质量缺陷修复。

`deploy/nginx.conf`采用Docker DNS动态解析API，容器换IP可恢复；SSE关闭proxy_buffering/request_buffering/cache/gzip，保留持久游标；PDF Range/If-Range转交受控资产API，不暴露MinIO预签名URL或bucket/key。Cookie同源HTTP-only/SameSite Strict，公网HTTPS时须API_COOKIE_SECURE=true并限制API_ALLOWED_ORIGINS。密钥只用服务端env_file，不用VITE_变量或构建ARG。

Windows模型宿主使用host.docker.internal；Ubuntu使用extra_hosts的host-gateway或受控内网DNS。不要把Windows权重目录挂进Linux/API，也不要把模型宿主端口开放公网。健康探针不加载权重、不发收费请求；供应商状态仅配置已填，不能写成连通已验证。

运行和回滚顺序：记录源码SHA、所有image ID、锁hash、配置hash（不输出值）及备份manifest hash；停写、做跨存储小样备份，先独立目标恢复验证，才切换API的M2_DB_NAME/M2_OBJECT_BUCKET/M2_MILVUS_COLLECTION三元绑定。必要时停API/worker/dispatcher，将完整三元绑定切回原环境并用原image ID重建应用，保留两个目标和失败记录。禁止只换向量集合、原地覆盖或删除锁续跑。外部目标批准前不执行该步骤。

MinIO使用deploy/minio/Dockerfile的固定源码发行构建；在无本地镜像的新机器也须构建，不从不明tag替换。服务日志json-file限10MiB×3；备份及output容量由维护者保留，不自动清理。Desktop资源不足时停止**本轮项目**后继续，不重启/清理旧服务解决测试。Milvus线程限定仅工程资源约束，不宣称性能提升。

固定本轮候选而不重新构建：先在授权目标离线load本机封存的application-images-r1.tar，核候选清单image ID，再以compose.delivery.yaml加docs/development/releases/M7-delivery-r1.compose.json执行up --no-build。该覆盖文件只固定应用image ID，不含私有配置；存储基础镜像仍按base文件digest拉取。镜像归档本轮只留output，未上传或转移外部。重新构建可能产生新ID，须形成新候选，不能沿用旧验证身份。
