# M6-05 regression来源闭环与隔离验证 r1

日期2026-10-29；基线`e76651f1db48efb7c6075331b2cfb2d65282b4e0`。开始及fetch后HEAD、origin/main、GitHub main一致，工作区仅未跟踪tmp/。本轮为执行方实现与自验，待总控独立复审；不宣告M6子项验收。

## 实际交付

完成服务端“已确认regression反馈→完整标签候选→独立助手标签审核→已有冻结dev题绑定/必要派生→正式实验与Run消费来源→服务端复评证明”接线。四条新写入API使用现有登录、writer、知识范围和原件授权；浏览器页面本轮未新增，不将API能力写成完整交互验收。

| 环节 | 实现与证据 |
| --- | --- |
| 标签候选及审核 | 完整Question保留题目、Expected、原件证据与完整来源快照；候选只能draft/dev。审核者必须另一个当前合法账号，具名independent_assistant_review，subject hash校验，并核验提交中审阅文档的字节SHA。入口不接受human声明。不可变候选、审核记录独立于答案双轮。 |
| 未变题绑定 | 从受控catalog解析完整题目，必须reviewed/eligible/dev、题目与反馈一致、原件scope包含于反馈精确资料修订；自动精确匹配另要求反馈预期字面等于已审key_points（规范空白）或完整Expected JSON。不同文本不猜语义等价，须独立审核完整题目与反馈映射。固定dataset/manifest/config、题级SHA、审核内容SHA、反馈审核版本及原Run结果/输入指纹。直接使用已有版本，不重复派生。 |
| 变化或新增题 | 先完整候选和独立审核，再派生JSONL、manifest、config；保留父dataset/manifest/version、前后题级SHA。heldout与跨split题目族拒绝；保留旧文件、catalog、其他题目。新配置为完整dev，不继承父question_ids子集；父源码/模型/prompt与资料快照身份仍保持原值，本轮不自动改写，未来真实执行仍须通过现有runtime_versions/接受材料校验。新原件必须已经在父来源清单登记，不能借反馈偷偷扩大来源。 |
| 目录可见性 | 在原受控catalog根目录的regression-versions内容地址目录落盘，文件不可覆盖；entry.json最后发布，未完成目录不可解析。同身份恢复校验全部字节，冲突拒绝；父catalog字节不变。正式登记eval-set与创建实验仍是独立动作，不因半写绑定被视为已运行或通过。 |
| 正式消费 | ExperimentInput.regression_source={id,sha256}进入请求hash和持久实验；创建/job/每题及Run写前重验。job运行配置加入source和独立regression_execution_key，参与manifest/attempt及evaluation_items检查点hash；正式execution link记录source与控制/目标库映射。标签/证据不进入生成prompt。 |
| 预校准与独立生成 | 带反馈来源的候选若绑定baseline，须同时绑定regression_calibration_id，创建前核验当前基线双轮/校准及同版本同范围，job重验。不同实验执行key使候选不复用基线Run；continuation只在相同source/校准下继承执行key及既有正式父题级协议。未提供baseline的运行仅作为基线，不能生成复评通过证明。 |
| 服务端证明 | 独立regression-proof接口读ReviewService当前gate/current result_attempt/quality、精确题集范围、校准先于candidate、来源绑定先于实验、baseline和校准身份、目标库每题正式link与结果Run。服务端生成不可变证明hash，含subjects/quality/calibration/link/gate指纹；不接受客户端passed、分数或自动发布。 |

新的regression反馈控制账本与评测控制账本须一致，Run目标库允许独立；source_database只读服务端已存映射，HTTP不能提交库名。旧无映射反馈保持原同库行为，旧记录不回填、不复制Run。正式worker继续在现有入口核验当前owner权限；来源资料撤权或hash变化时拒绝。

## 实际验证与红测

原始日志、确切命令、JUnit、派生文件和合成job manifest/results位于本机新目录`output/m6-feedback-regression-wiring-20261029/`，不上传。

| 组 | 结果与退出码 |
| --- | --- |
| 初始版本/来源测试 | 缺模块时collection分别退出2；红测原样保留。 |
| 正式链首跑 | 5失败，退出1：原结果白名单不保存run_id；新反馈实验现保存Run关联，旧无来源实验投影保持。 |
| 结果发布窗口红测 | 1失败，退出1：恢复跳过成功题导致当前attempt无link。补修为只读核对成功Run及此前正式关联，登记本attempt观察复用，不新调用。 |
| 调用账本红测 | 1失败，退出1：恢复发布仍带旧“本次新增1”。补修后保留累计1、本次新增0，缺测null；历史attempts不改。 |
| 深目录产物验证 | 10失败/19通过，退出1：Windows路径预算超限。缩短目录与临时文件名，完整SHA仍固定；现场保留。 |
| 并发扩展回归 | 215通过/1失败，退出1：Windows并发创建目录期间对不存在路径resolve偶发越界误判。改为目录存在后的strict解析及两级边界核对，聚焦组重跑通过。 |
| 精确预期红测 | 1失败，退出1：题目相同但预期相反仍可自动绑定；增加字面匹配或独立审核映射要求。 |
| 相关共享回归 | 212 passed，退出0，170.72秒；2条SWIG弃用warning，进程另有既有swigvarlink warning。包括catalog/dataset/labels/adapter/reviews/feedback/jobs/continuation/分库。 |
| 最终共享确认 | 217 passed，退出0，180.25秒；包含上述已补修并发及预期匹配，2条既有SWIG warning。原212通过及215通过/1失败记录保留。 |
| 最终新增链路组 | 33 passed，退出0，49.10秒。含未变及派生版本两条全链、同库/分库、题标签不入prompt、预校准先行拒绝、来源更改拒绝、并发绑定/派生、预期相反拒绝、文件4写点、候选/审核/绑定3写点应答丢失、Run创建/关联/结果发布3窗口、continuation及证明应答丢失恢复。 |
| API契约与类型 | OpenAPI与create_app().openapi()一致，generate:api退出0，frontend typecheck退出0。无UI行为变更，本轮未重复浏览器测试。 |
| 历史保护 | 既有三份清单821/404/294项逐项匹配；组间可能重叠，不累计唯一数。 |

命令主体：`.venv/Scripts/python.exe -m pytest`。最终共享组的17个文件及完整参数保存在本机commands.json（accepted-shared），JUnit为accepted-shared.xml；最终组为`tests/integration/test_feedback_regression_lineage.py tests/unit/test_regression_versions.py tests/integration/test_regression_formal_execution.py -q --basetemp=output/m6-feedback-regression-wiring-20261029/rechecked-work --junitxml=output/m6-feedback-regression-wiring-20261029/rechecked.xml`。Mongo仅显式`M1_TEST_DB=m1_test_m4_regression_lineage`随机子库，分库为对应随机库的_ctrl，不清库。不同组有重叠，不相加为唯一总数。

审核artifact成功路径在新闭环集成中明确注入合成审核夹具，实际artifact缺失拒绝亦覆盖；合成human两轮通过正式ReviewService保存于随机测试库，仅证明质量门禁接线。没有将合成审阅说成真实审核。无供应商调用、真实答案离线回放或真实质量写入；未重跑85题原件分析。

## 身份、费用及保护边界

本轮供应商逻辑调用未启动，合成Model.stream在隔离正式QueryRunner执行并记录遥测，不视为供应商效果。真实历史精确HTTP次数/token/费用未知继续为null，不从结果行数推导0。恢复窗口新增0有隔离遥测与prompt计数佐证；累积来自Run持久遥测。没有新增真实dev/heldout、正式human、observation、calibration、candidate或真实反馈绑定。

未访问正式Mongo业务集合，未核对或声称历史22集合全部不变；只核验本机历史保护文件。run_events TTL差异仍单列。冻结r3仍为85条19继承+66执行，历史stream19/新增61，精确HTTP/费用未知；旧a560…failed/attempt2/provider_invalid_response/retryable=false/results0身份保持，不把调用写0。未重导入、切默认、覆盖修订/答案、清理tmp/output/evals或上传私有产物。

## 验收阻塞矩阵与下一动作

| 项 | 已满足 | 未满足与责任 |
| --- | --- | --- |
| M6-04 | AF等技术审查已关闭；85题及25题assistant分析保留；正式双轮/校准机制已有 | 全范围新规则真实human双轮、未知/适用性收敛及有效预校准，须真实审核者提交；助手不代签。执行方提供已存结果与原件定位，用户不需重找PDF。 |
| M6-05 | 本轮来源、版本、正式消费者和证明服务端链路隔离自验 | 本次新增实现待总控独立定向核验；真实反馈标注审阅/来源绑定与真实反馈后同范围复评尚未执行，不受合成证明替代。执行方负责核对及正式关联，不重复建反馈。 |
| M6-08 | r3运行与旧证据、隔离真实检索/新答案和助手分析均保留 | 真实闭环、同范围质量比较及固定报告未验收；四题对象/配件实际提示词效果与019/021/022/048召回仍未解决；执行方继续技术诊断，真实生成前另交身份/幂等/费用范围。65题heldout不运行。 |

**唯一下一动作：总控对本轮新增regression来源/派生/正式消费者/证明链作独立定向核验。** 执行方交付可直接重跑的33项合成链路及共享回归；通过后由执行方只读匹配既有真实regression草稿与已审dev内容，决定精确绑定或必要派生，不将所有反馈强送revision。实际资料变化才走revision affected→full，正式答案双轮→预校准→同范围candidate→复评规则保持。

技术回切：正常反向提交新增接线，关闭新入口/停止新引用，保留已有绑定/版本/证明与所有旧文件；不删索引/Run/结果，不重写历史。本轮不发布知识、不自行关闭M6-04/05/08，**M6保持4/7，M7未启动**。
