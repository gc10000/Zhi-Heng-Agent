# 内部候选演示路径

登录→资料管理→查看自制资料/活动修订→问答入口（新生成明确未执行）→受控引用/PDF Range→支持草稿编辑与确认→待审反馈→刷新/事件游标恢复。

自制`examples/preview/manual.md`使用CC0，仅虚构ZH-DEMO-1与Dock，不含课程PDF、真实产品手册或真实用户数据。bootstrap用实际解析/索引/验证/发布接口登记；向量明确合成，不证明检索质量。

`frontend/tests/e2e/delivery-live.spec.ts`通过专用`playwright.delivery.config.ts`访问**实际部署后台**，不route.fulfill，不发供应商请求。其Run由工程fixture通过RunService/RunCommands/EventLedger生成，界面及正文明确“工程合成，非模型回答”。草稿确认和待审反馈真实持久化，不能登记M6 feedback proof、质量候选、评分或校准。默认浏览器套件排除此live用例，必须显式配置，防误运行。

截图、trace、录屏只保存在本轮output，不提交；含合成登录凭据的browser.json也仅本地。真实问答/澄清新生成与真实模型容量本轮未执行；演示不能剪掉该限制或把旧答案充作新调用。正式公开演示前，需新定向真实确认或获接受的明确受限范围，并完成来源许可证/发布批准。
