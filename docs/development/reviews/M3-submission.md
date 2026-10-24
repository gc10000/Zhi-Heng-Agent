# M3 Vue 3工作台 · 执行提交

2026-10-24，分支main，阶段执行自验完成，等待总控独立审查。M4未授权。M3-01至M3-11共11/11；未完成任务无。M0/M1/M2通过是前置历史，不作为本轮结果。

## 实现与行为

前端采用Vue3/TypeScript/Vite/Router/Pinia/Vue Query、Reka与shadcn改编组件、PDF.js及markdown-it，版本与integrity锁定。没有React。Windows脚本Node22.17.1、pnpm11.25.0（独立安装器内置Node24.22.1）、Edge155.0.4283.62。Python/CUDA依赖未变。

|任务|交付与验证入口|
|---|---|
|M3-01/02|独立工程、OpenAPI输入类型、同源Cookie/CSRF/API错误与身份恢复；原生fetch上下文、迟到身份与401完整清理有红绿证据|
|M3-03/04|1500px三栏与390px抽屉、目录/历史分页、URL恢复、身份/kb隔离；切会话拒绝旧增量|
|M3-05/06|按run/seq去重、断连/410回快照、退避、终态关流；独立取消、展示version确认及409重新选择；进度为真实事件|
|M3-07/08|编号定位稳定引用；授权来源、原图、精确修订原件；禁HTML/危险链接/未知图像；本地PDF worker/字体/文本层/缩放旋转与bbox，拒绝迟到渲染|
|M3-09|设备/资料、用途/关联/新修订上传、幂等请求、job URL恢复/重试、切片/来源/质量与修订比较、发布/撤回/回滚CAS；查看者无维护入口|
|M3-10|键盘跳转与焦点、IME、reduced-motion、长内容/大图/坏图、等待、401/403/409及404拒绝资产；按需加载页面/PDF|
|M3-11|正式页面真实两轮问答和澄清、精确引用、刷新、桌面/手机与真实上传发布；完整回归、原件/持久产物只读核对、新快照|

文件范围以[M3独立清单](M3-artifact-manifest.json)为准；任务详见[阶段步骤](../../plans/tasks/M3-vue-workbench.md)及records/M3-01.md至M3-11.md。新增frontend、scripts/verification/m3_environment.py、recheck_m3_live.py、build_m3_artifacts.py及前端说明/复用记录。后端最小兼容改动仅app/knowledge/citation_api.py：按精确修订登记增加可空original，读取重新授权；新增tests/integration/test_m3_citation_original.py真实原件/Range/撤权用例。不迁移旧数据、不改变桶策略。

## 本轮实际验证

完整命令、退出码、JUnit/Playwright结果路径、原始报告hash见[验证摘要](M3-validation-summary.json)。所有下列成功命令退出0。

|检查|实际结果|
|---|---|
|后端阶段 `pytest tests/unit tests/contract tests/integration -m 'not live_provider'`|346 passed、2 deselected、0 skipped，365.12秒；180单元/83契约/83集成目录|
|既有 `unittest discover -s test -p test_document_reimport.py -v`|3项通过，0.592秒|
|前端 `pnpm -C frontend test:unit`|34 passed、0 skipped，8文件，6.94秒|
|默认 `pnpm -C frontend test:e2e`|14 passed、0 skipped，23.9秒；离线协议与合成PDF，真实测试2文件按配置排除|
|显式环境 `test:e2e -- support-flow.spec.ts`|1 passed、0 skipped，最终续验6.5秒；复用已完成两轮，不能把6.5秒作为模型时延|
|显式环境 `test:e2e -- auth-client.spec.ts`|1 passed，3.4秒；真实Cookie登录|
|只读 `recheck_m3_live.py --config ... --flow ... --output ...`|8检查通过；历史user/assistant/user/assistant、两轮引用、事件唯一终态/顺序、真实上传发布/设备关联、两原件hash|
|`install --frozen-lockfile`、`typecheck`、`build`|各退出0；Vite727模块，构建8.01秒|

集成目录包含真实隔离Mongo/Milvus/MinIO/Linuxworker/本机BGE，也包含模型端口注入，不把83项全部称为真实供应商链路。后端2项付费测试按选择排除，真实UI单独执行。本阶段付费回答累计4次：M3-01为2（含首次脚本未完成验收已产答案），M3-11为2。MD小样解析不调MinerU/VL；嵌入重排在本机；只读核对与续验不重复调用模型。

正常完成和错误传播由unit/浏览器回归覆盖，真实小样验证登录→设备→未指定型号提问→澄清（刷新恢复候选）→两轮完成→引用→刷新历史→手机来源→上传并导入→活动发布→切片。M3-01实际取消停在澄清、未额外计费；本轮最终真实脚本未再次付费重做取消。

## 原始失败、证据与数据边界

原始evidence和evals/仅留本机，不上传。81份本轮原始输出/报告/媒体hash由摘要登记；临时账号配置排除。截图位于evidence/M3-11-desktop.png、M3-11-mobile.png、M3-11-import.png，已目视核对布局与来源。录屏为M3-11-flow-resume-artifacts及M3-11-flow-final-artifacts中的video.webm，包含已持久回答回放、真实上传/发布及续验；不宣称一次无中断完整录像。trace可能包含Cookie/登录信息，禁止发布。

正式红测包括原生fetch Illegal invocation、401选择残留、缺键盘跳转、重复终态通知和PDF文本层迟到返回；各任务记录保留红绿数量。以下单独记录为脚本/环境问题：缺ffmpeg、Vite启动尚未监听、手机已自动模态仍点击遮罩后顶栏、多个切片的严格locator断言、只读脚本括号/GBK诊断错误。首次全浏览器与build并行触发public资源更新和页面重载，13通过1失败；保留原输出/trace，停止构建后顺序重跑14通过，没有削弱断言或删除有效测试。

数据仅随机m1_test_m3库、独立owner/集合/对象前缀；原课程原件、解析缓存、集合、桶策略保留。真实环境准备还留有一次未就绪时创建的隔离小样，无付费、不删除现场。后端整个回归同样使用独立测试库。环境停止仅限脚本创建进程/容器，所有测试数据保留。

前端源文件与dist进行本机敏感配置值扫描，真实浏览器无供应商外域请求/运行异常；不将静态扫描当作生产渗透审计。PDF库439.53KB、worker1046.21KB独立按需产物，首屏无PDF请求，未声称性能提升。

## 配置、风险、回滚与Git

API_PROXY_TARGET仅Vite服务端，后端显式Origin与本机Cookie配置见[配置](../../CONFIGURATION.md)、[前端说明](../../../frontend/README.md)。不新增供应商配置，不改Python依赖/模型，不部署。许可与上游映射见[复用清单](../../reuse/manifest.json)。动态响应缺schema时为手写类型；旧未登记原件original为null；生产代理、全库、大文档/长期/压力和生产灾备未验收。PDF浏览器为合成小文件完整200读取；服务端真实206/416/撤权另有集成验证，未声称浏览器对真实供应商大PDF已完成Range验收。

M3-01至09逐项已推送（5b99924、390d582、aa2552c、ba6595d、0564a92、3805157、189b182、60bef02、d4f8f3e）；M3-10为7691b5d，默认代理失败后直连推送成功。交付自身SHA及最终远程状态在交接补记，不循环amend。若网络未恢复，保留本地提交，不能称全部已同步。Git推送不等于阶段通过。

回滚以反向提交撤回M3前端及可空字段适配，停止本轮脚本创建进程；保留旧入口、数据、历史快照与失败原件，不删除测试库或桶。M4及后续未授权；下一动作仅等待总控审查M3。
