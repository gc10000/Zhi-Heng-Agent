# 测试工具不进入运行候选；沿同一API镜像安装固定测试依赖，测试源码只读挂载。
ARG API_IMAGE=zhi-heng-api:m7-r1
FROM ${API_IMAGE}
USER root
COPY deploy/verification/requirements.lock /tmp/verification.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/verification.lock
USER 10001:10001
