# M6已审来源关系048单次真实验证执行报告 r1

日期：2026-11-01，Asia/Shanghai。执行方自验及来源诊断；本包结果待总控独立复核，不自签独立关闭或M6验收。

## 实际结果与停止

**唯一版1 support-v1-048已实际执行，技术完成，来源诊断拒绝，已封存停止。** 新正式实验`8043541e-678d-4103-aee3-56d02e54e555`，Run `5b6a0133-7880-423e-9547-a513b4cf7a63`。1个job／attempt／逻辑stream；finish stop、可见正文1317字符、未截断。先合法结算6116／859，再逐项来源诊断；没有重抽或追加调用。

正文确实引用了LA2608管理用3G/4G→运营商无线控制器，以及CB304n Cable／同轴／入户接口。但CB304n小节和最终“上联／核心管理／业务链路”比较仍合并了客户端有线／无线访问设备与设备上联两个层级，且没有解释已在输入中的EoC排障语义与条件。局部“供用户接入”措辞存在，仍不足以消除最终同层比较的实质歧义；未把它夸写成答案明确断言无线回程。管理目的有原文引用，但GM/GU手册版本范围也未明确。由此不能接受本题上联比较，不由审核方补答。

这是实际回答的关系消费失败；必要证据、明确“您→CB304n”的关系、Web访问及条件性同轴检查已经进入精确prompt，不能再归因为漏召回。未修改角色抽取、检索、答案prompt、供应商设置或评分；已关闭角色边界及旧技术结论保持。

技术completed的Run、job及冻结outcome保持原状；通过正式来源决定`accepted=false`及`single_result_sealed`停止新账户。固定批次`m6-source-relation-048-canary-r1`、唯一槽`m6-sr048-r1-v1-support-v1-048`均不能重领；started／settled／source-review及根halt齐全。账户blocked、cursor 0、pending null、unknown_windows空、仅一次job与stream预留及一次结算。旧nonthinking blocked、两槽及43题未执行保持，不接版2、不恢复43题。

## 来源诊断的范围

七项断言逐一封存在本机source-decision：管理目的／版本、Cable与EoC条件、客户端与设备端点、实际分别引用的上联比较、CB304n必要正文、p30与unknown、诚实限定。前五项及最终范围存在缺失或实质歧义；p30、未知字段、无现场成功断言检查保持。它们是逐断言诊断，不换算分数。

本题10个选中引用page_status实际均exact；引用4保持已审物理p30／印刷5-1。关系中的unknown保持unknown，答案未新增精确页码或现场已成功结论。来源编号对应实际选中证据，但编号有效不自动证明推导正确。完整输入、实际回答、逐断言摘录及证据关系只留私有HTML／JSON，不上传。

## 身份与最小准入

启动HEAD＝origin/main＝实际远程main实核`4cc94e61cf22e3c3339301440da8f1517e7ba9f5`，工作区仅tmp、暂存空。授权从该提交的Git blob读取，路径`docs/development/reviews/M6-source-relation-048-canary-authorization-r1.json`、SHA256 `2ea1b4868be934979d3d62f1524b3df18aa0c72028760b8acf466c9be7a75129`，没有以工作树授权冒充封存来源。

新增默认关闭的内部`diagnostic_source_relation_048_v1`合同／限定profile，只允许一个授权成员。直接复用RemainingLedger的CAS、唯一在途、磁盘exclusive、结算、来源决定和停止机制，继承非思考客户端及模式观测；只增加合同路由、必要联合类型、正式恢复适配器及原始reasoning观测接线。未复制账本／调度器，未改变旧AUTHORIZED_GIT、旧账户或普通v2 unknown拒绝路径。

授权绑定完整题集、原题目／history、旧blocked快照、四种锚hash及最终code／runtime。仅允许experiment_id、versions.code、output_contract、output_token_field四处配置差异。完整150题＝85 dev＋65 heldout文件及manifest保留，仅执行授权dev单题。无新环境变量、全局默认或公开API，OpenAPI与已存规范全等。

最终app canonical：`064bf60d6b58d6989c23a5a9bbd030360db5f9f60bf006154193e22e4354f349`；角色抽取文件SHA256：`91d9f065c05639428176fc73b8f14d0482c191b8907bbe23677161a23c6ad10f`，与已审版本不变。manifest canonical：`3101798563cabe255a2b27a41bc1d0e2f4f28b05637336f9c1ac58931e707be7`；配置canonical：`439446058b43c4ee0677af31a84c30a97396b7c387f2a06d491a364a206f4ed3`；request canonical：`12300c46a6ed08688d16cdb1253e9cb42aa33afae8f8c1c9db09b9872489e8f5`；checkpoint：`52e9f20bfc4b44647750c7a596669bbb0342889b47346a54b19e61bdd27f4148`。锚文件SHA、prompt UTF8 SHA、result／config canonical及原配置文件hash分别记录在同名validation JSON，算法不混用。

## 精确前置与正式执行

正式消费者只重建这一题：双路候选、486已存分数缓存、排序、context／reference_map／groups、非policy预算及prompt与授权锚全等。两次embedding缓存命中、20分数命中、6检索响应命中；零miss、编码／重排／导入／摘要0。保守输入预留15097、limit28416，和实际供应商input6116是不同口径。原25题35必要单元与582来源／修订／产品／67资产依封存hash保护，没有重跑整54／25或冒称全量现场扫描。

安装SDK的单份Mock逐字核messages及固定wire，不消费产品槽。临发只读核主体、旧账户、新账户／请求／checkpoint／link／outcome及新槽缺席；服务五项健康。本轮未启停基础服务、worker或修改Docker配置。

实际沿EvaluationService.create_experiment → execute_job → 默认RealQueryExecutor；没有executor_factory或私有SDK直连。只包装embedding／rank和已存检索读取口，保留正式索引授权、对象关系、预算及风险门禁。请求hook再次核共享CAS预留、Run／link和started关联及wire全等后才联网。真实wire、原始响应字节、SDK归一化前usage、Run、完整attempt、冻结outcome与单次结算链均保留。

## 计量与风险

历史46973／29553＋本次6116／859＝累计**53089／30412**，在本包75389／33649观测限内；reasoning已经包括于output。raw未提供reasoning计数，保留null；未观测到非空reasoning内容，不把它当内部思考关闭的证明。新增本地推理、非产品探测、模型审核0。

固定qwen3.8-flash，SDK 1.1.11／2.28.0，n1、temperature .1、stream＋usage、extra_body enable_thinking=false及max_completion_tokens4096，retry0、timeout120、无max_tokens／effort／fallback／redirect。检索weighted .5/.5、20／20／20／20／10及32768／4096／256／12000保持。

实际请求／响应hook各1是观察值；**精确HTTP总数、费用、visible tokens仍null；付费输出上界与网关能力unknown，未登记verified或server_hard_limit=true。** 4096请求值和timeout不作为硬费用保证。

## 实际验证与限制

| 范围 | 实际结果 | 限制 |
| --- | --- | --- |
| 最终相关单元／契约 | 64通过，exit0 | 最终源码green-unit-r2，保留首轮64通过记录 |
| 最终隔离正式job／故障窗口 | 42通过，exit0 | 新40＋受影响旧路由2，随机m1_test_m4_sr048_e72945库保留，合成流 |
| 初始红测 | 1失败、22 fixture errors，exit1 | 新路由未实现及新模块缺失的fixture导入错误；不写成23行为红测 |
| 旧账户及保护前置 | 9659断言通过，exit0 | 指定消费面／4686文件；不累计为质量分 |
| 唯一题消费者／SDK Mock | 通过，exit0 | 精确全等、推理0；不替代真实答案 |
| 实际结果技术审计 | 28项通过，exit0 | 原始流／完成性／模式观测／计量／正式关联；不接受语义 |
| 完整attempt补核 | 4项通过，exit0 | 完整attempt＝文件result，与outcome fingerprint一致 |
| 最终只读审计 | 9629断言通过，exit0 | 4686文件、旧43指定未执行、新单槽blocked及结算保持 |

中途仅本机来源诊断脚本误设“必须存在unknown页码”的断言失败，exit1原日志保留；实际十引用页码均exact。修正为核实际unknown关系字段后通过，发生于正式来源决定之前，无模型重发／业务源码修改，不作为产品前置或usage失败。

历史138／336／597／1314组hash保持，组间重叠不累计唯一总数；4686指定唯一文件保护集合保持。没有全量重扫现场向量、默认指针、TTL、所有历史run_events或旧质量全库，不声称这些集合现场全部未变。未创建正式候选、评分、attest、校准、gate或反馈proof；不跑heldout、不切默认、不重签001。

## 交付与唯一下一动作

私有目录`output/m6-source-relation-048-canary-20261101/`，导航`唯一048诊断与封存.html`及逐题HTML含真实原件／来源决定；原件、所有失败、旧槽、tmp与缓存保留，不上传私有产物。公共只交源码、合成测试、脱敏报告／JSON和导航更新。正常提交／推送后的SHA及远程状态由最终回执记录，不用自包含SHA反复amend。

唯一下一动作由执行方承担：将本次真实输入、来源拒绝、单次原流／结算及固定槽交总控独立复核，再由总控裁定后续；本包不能以完成性通过授权恢复43题或质量链。

**M6保持5/7；04保持验收，05缺真实反馈复评proof，08缺有效新候选质量及阶段验收，M7未启动。** 先前独立关闭项保持，本包自验不冒充总控关闭或正式质量结论。
