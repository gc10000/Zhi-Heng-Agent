# 知衡 Vue 工作台

Windows运行Node 22.17.1（`.node-version`）、pnpm 11.25.0；本机独立pnpm安装器内置Node 24.22.1，实际脚本经`pnpm exec node --version`为22.17.1，engine兼容22–24。依赖锁定，不执行Python全量同步。

从项目根目录：`pnpm -C frontend install --frozen-lockfile`，`pnpm -C frontend dev --port 5173 --strictPort`。根目录`.env`配置后端的`API_ALLOWED_ORIGINS=http://127.0.0.1:5173`及本机HTTP专用`API_COOKIE_SECURE=false`。前端代理默认127.0.0.1:8000；改地址用进程环境`API_PROXY_TARGET`，仅Vite服务端使用，禁止填供应商密钥或添加`VITE_*`密钥。

验证：`pnpm -C frontend typecheck`、`build`、`test:unit`、`test:e2e`。Playwright当前使用本机Edge通道（本轮155.0.4283.62），默认测试是明确标注的离线协议模拟；真实测试须显式`M3_LIVE_CONFIG`指向本地忽略的隔离环境账号文件。不要把该文件上传或打印。OpenAPI输入类型由`generate:api`生成；响应目前无schema，`src/lib/api/types.ts`按实际后端公开字段补充，不将unknown假称全自动生成响应类型。

独立真实小样：`.venv/Scripts/python.exe scripts/verification/m3_environment.py --config docs/development/evidence/<新名字>.json`。建立随机m1_test库、集合和对象前缀，运行真实模型桥接/Linux worker/API/Vite；保留数据，结束时创建同名`.stop`文件，仅停止自己的进程。真实问答产生费用。原课程数据、原桶策略与旧入口不改。复用许可见根目录THIRD_PARTY_NOTICES.md。

正式工作台已接会话目录/历史、设备范围确认、可恢复SSE、授权图文引用/PDF原件、资料上传与修订发布。处理记录和评测入口明确未开放，未伪造数据。CompatibilityPage纵向试验页已由正式组件替代，历史提交与原始验收证据保留。

默认test:e2e仅选择离线/合成PDF用例，真实登录和阶段链路以配置选择，选择排除不是测试通过。在项目根设置`$env:M3_LIVE_CONFIG='../docs/development/evidence/<新名字>.json'`后运行`pnpm -C frontend test:e2e -- support-flow.spec.ts`。配置路径相对frontend，含临时凭据，严禁输出/上传。录屏工具用`pnpm -C frontend exec playwright install ffmpeg`安装，仅工具二进制，未改Python环境。

真实脚本将run/job与完成步骤写入配置同名.flow.json，失败后优先续验，不新建会话重复计费。截图/录屏/trace留本机evidence；原始trace可能含Cookie或登录表单，禁止上传。浏览器测试、构建与另一个Playwright必须顺序执行：build复制public PDF资源会触发Vite重载。静态产物发布和生产代理未在M3部署验收。


缓存会话切回后，界面先显示历史并等待目录/历史本轮刷新；再按当前活动运行恢复，快照请求按会话与请求代次隔离。未读完历史且无活动指针时先加载后续页，发送保持禁用。

目录搜索/分页所选设备会保留当前用户和知识范围下的描述。首100项以外的设备使用现有授权目录按型号有界核对（最多100项）并精确匹配ID；核对通过才显示型号并允许提交。等待、失效或目录错误会明确禁发，可主动清空选择或重新选择；极端同名超过100项时不无限遍历。切知识范围、退出或401同时清除ID与描述。旧描述不能代替授权核对。


## M5 支持记录

已完成问答下可进入处理记录：确认设备/现象，核对原文操作清单并记录用户自报；无效步骤不重复初始化，全部无效或缺证据转交。更正影响未来轮，旧引用/确认记录保留当时版本；草稿编辑先保存，再显式确认与导出。反馈仅进入待审。页面依赖真实M5 API，不使用本地存储冒充已保存状态。有限工具只有内部只读端口，外网MCP延期。错误或版本冲突时刷新服务状态核对，结束后不会由迟到响应恢复。

离线浏览器：`pnpm exec playwright test support-case.spec.ts`（从frontend目录），协议模拟不等于全链路。真实独立环境以本机`M5_LIVE_CONFIG`和`M5_UI_BASE`显式选择，`support-live.spec.ts`默认排除；临时账号/trace/视频不提交。命令和范围见[M5验收记录](../docs/development/records/M5-08.md)。
