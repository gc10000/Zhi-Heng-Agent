# M6-08 R2分库接线补修计划

用户已授权补修R2/P1并复审，不重复确认。起点34a98da；R1独立核验通过保留，M6仍4/7、04/05/08未验收、M7未授权；按AGENTS顺序执行，不使用子代理。

1. 保留原复审探针，独立目录复现同库通过/分库失败，再加入仓库回归。
2. 正式job显式给adapter控制数据库能力，不从冻结target推断控制库，不把连接或token写入来源。当前worker/lease先在控制库核验，避免无效身份产生conversation/checkpoint/Run；绑定前重验以保留租约门禁。
3. 目标库仍存Run/checkpoint/execution link/continuation，link固定控制库与目标库映射；父实验查控制库，父题级关联查目标库。无隐式fallback、实验复制、历史回填或修改target；跨库窗口不承诺事务原子性，pending仅由正式恢复收敛。
4. 同库/分库正式job覆盖首题与completed复用，分库覆盖合法后续、错误父/旧attempt拒绝、创建后崩溃重建幂等、错误worker/过期lease及缺控制库能力在副作用前拒绝；保留R1计量与历史缺链门禁回归。
5. 定向回归、原探针重跑、r3的520只读及45历史hash核验、OpenAPI/语法/链接与候选检查。同步契约/workbench/ADR/交接报告和脱敏摘要；只自验，不自行关闭R2。
6. 正常审阅提交推送、核对远程完整SHA；tmp/output/evals/原始evidence保留不上传，不启动真实模型或服务。
