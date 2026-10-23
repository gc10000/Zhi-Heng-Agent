# 从 MinIO 官方固定提交构建社区版，不依赖历史 minio/minio 镜像。
# 对应 RELEASE.2025-10-15T17-29-55Z：
# https://github.com/minio/minio/commit/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a
FROM golang:1.24.8-bookworm AS build

ENV CGO_ENABLED=0 GOTOOLCHAIN=local

# 使用固定 Go 模块版本及默认校验数据库校验源码；限制编译并发，减少内存需求。
RUN go install -p 2 -trimpath -ldflags="-s -w" \
    github.com/minio/minio@v0.0.0-20251015172955-9e49d5e7a648
RUN mkdir -p /licenses && \
    cp /go/pkg/mod/github.com/minio/minio@v0.0.0-20251015172955-9e49d5e7a648/LICENSE /licenses/LICENSE && \
    cp /go/pkg/mod/github.com/minio/minio@v0.0.0-20251015172955-9e49d5e7a648/CREDITS /licenses/CREDITS

FROM debian:bookworm-slim

# curl 用于 Compose 健康检查；证书用于服务向外部 HTTPS 端点发起请求。
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*
COPY --from=build /go/bin/minio /usr/local/bin/minio
COPY --from=build /licenses /licenses
LABEL org.opencontainers.image.source="https://github.com/minio/minio" \
      org.opencontainers.image.revision="9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"

EXPOSE 9000 9001
VOLUME ["/data"]
ENTRYPOINT ["/usr/local/bin/minio"]
CMD ["server", "/data", "--console-address", ":9001"]
