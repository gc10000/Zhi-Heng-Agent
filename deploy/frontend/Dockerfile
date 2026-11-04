FROM node:22.17.1-alpine@sha256:5539840ce9d013fa13e3b9814c9353024be7ac75aca5db6d039504a56c04ea59 AS build
WORKDIR /frontend
ENV NODE_OPTIONS=--max-old-space-size=768
RUN npm install --global pnpm@11.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml ./
COPY frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --network-concurrency=4 --child-concurrency=1
COPY frontend/ ./
RUN pnpm typecheck && pnpm build

FROM nginx:1.29-alpine@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /frontend/dist /usr/share/nginx/html
COPY NOTICE.md THIRD_PARTY_NOTICES.md /usr/share/nginx/html/licenses/
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1:8080/health/live || exit 1
