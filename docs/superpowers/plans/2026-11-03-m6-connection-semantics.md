# M6连接语义消费实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用superpowers:executing-plans顺序实施；用户未授权子Agent，不委派。按任务核对红绿证据。

**Goal:** 让程序以同一冻结来源生成完整、限定、带引用的连接比较，补齐已证实的来源依赖和互斥分类问题。

**Architecture:** 新来源装配器在现有预算内保留各产品的完整介绍/连接scope；新语义消费者将话语形式、连接角色、介质、用途和状态分开。新比较器只比较被证据支持的属性，输出限定自然语言；以新行为/输入身份接入既有证明、缓存与恢复合同。

**Tech Stack:** Python、Pydantic、pytest、既有冻结payload和Run/outcome；隔离Mongo只用随机短m1_test_m4_前缀。

**Spec:** [2026-11-03-m6-connection-semantics-design.md](../specs/2026-11-03-m6-connection-semantics-design.md)。总控已自行审阅并批准零调用实施；本计划未执行，不是业务代码交付。

## 全局约束

- 默认关闭、缺省comparison_answer_v1；v1/v2/v3及既有关闭项按原范围保留。
- 新行为connection_comparison_v1尚未注册；不得直接写入已消费r8配置或复用旧风险合同。
- 不改检索排序、索引、旧角色抽取或题集/rubric/旧分。新装配只消费同一显式冻结范围的原资料依赖。
- 禁止产品名/题号/评分标签硬编码；源码和生产输入均不能读取expected/allowed_evidence。
- 不读private-identity，不输出.env值；原始输入、日志、草案仅留全新output目录，不覆盖旧证据或清理tmp。
- 不调用供应商/本地推理，不写真实业务库，不运行43题、heldout65或M7。不同实现身份复核和正式质量证明分别保留。
- 新增11项的审计输入不是正式配置；装配必须遵守context_limit=10及原字符/token预算，完整资料放不下须可观测拒绝。

## 任务1：来源依赖装配与预算（下一实施任务）

**Files:** 新增app/answering/comparison_context.py、tests/unit/test_comparison_context.py；测试夹具用合成来源，不提交真实切片。

**Interfaces:** `assemble_comparison_context(selected_docs, frozen_pool, *, product_ids, frozen_payloads, max_docs, max_chars)`；返回`ContextAssembly(documents, dependencies, dropped, status, identity_sha256)`。documents是最终引用顺序，dependencies记录理由/完整scope及原payload身份，dropped记录候选移出项，status为complete/ambiguous/required_source_budget_exceeded。frozen_pool由已授权装载端提供，装配器不建客户端。

- [ ] 先写并运行红测：两个合成产品各有连接证据及介绍、另有纯版权项；预算4时保留两个连接及两个介绍，预算3返回required_source_budget_exceeded且documents为空。
- [ ] 红测另外覆盖：介绍已存在不重复、单产品介绍缺失、多个不同介绍冲突、共享多产品主体、错误payload、跨修订、产品越界、unknown页码、介绍条件超字符预算。期待不是静默截断或随机选第一条。
- [ ] 实现严格身份核对：每个候选按V2Index.payload兼容投影重算hash，并比对scope、产品和冻结成员；标题只按spec登记语法处理。去重和顺序稳定，必要段完整占预算，纯版权等未贡献事实/条件的项在候选选择时移出，不改原Run。
- [ ] 实跑以上回归以及现有test_source_prerequisites/test_evidence_attribution相关单元；测试只能用显式合成pool，禁止自动读真实库或下载模型。
- [ ] 在新的私有output读取本轮已保存唯一概述和旧输入，产出预算内新装配、引用映射和hash；核对源文件保护hash，不写正式Run。若通用规则无法得到正确概述，修规则或明确拒绝，不能为048追加uid白名单。
- [ ] 维护报告/配置合同并显式暂存内聚提交；不接生产路由。

**回归接口示例（待实现合同，非已运行结果）：**

```python
def test_required_sources_do_not_silently_overflow(four_required_sources):
    selected, pool, scope = four_required_sources
    result = assemble_comparison_context(selected, pool, **scope, max_docs=3, max_chars=6000)
    assert result.status == 'required_source_budget_exceeded'
    assert result.documents == []
```

## 任务2：多维事实与有依据的比较

**Files:** 新增app/answering/connection_semantics.py、app/answering/connection_comparison.py、tests/unit/test_connection_semantics.py、tests/unit/test_connection_comparison.py；旧comparison_answers.py仅新增显式版本分派时才修改，不在此任务改旧函数。

**Interfaces:** `derive_connection_facts(assembly, product_ids)`返回带source/span/rule_id的事实；`compare_connections(target, product_ids, facts)`返回status、support_fact_ids、conflicts、missing；`render_connection_comparison(result, product_labels)`只读已验证事实生成自然语言。target沿用device_uplink，status增加限定比较结果，不把它伪装成全面能力结论。

- [ ] 将spec的6组来源判断和18个反例改写为通用新产品夹具并先运行红测；端点/介质/用途分别核对，不能只断言答案出现若干关键词。
- [ ] 实现scope语法规则：明确端点连接、用户访问、完整检查路径、单主体融合介绍；话语形式与角色独立。每项规则保存字面决定依据，未知/冲突不能升格。
- [ ] 固定介质映射按spec登记3G/4G网络及同轴电缆等；实现same/different、qualified_medium_difference和insufficient，分开关系不同和能力不同。
- [ ] 用户答复先比较、逐产品作答并引用；补介绍只支持介绍分句，不得替其他句补端点/用途；保留条件/否定/互通限制/unknown。完整原文留证据视图，动态文本惰性显示。
- [ ] 实跑合成矩阵、引用顺序/产品名替换、代码/HTML/假引用、冲突和预算边界，确保没有题号或型号特判。程序不得接触评分文件。
- [ ] 用分离输入做四格对照：A原10项+旧v3沿前包证据；B加概述+旧v3保持不足；C原输入+新程序必须暴露缺介绍而非编造；D预算内完整输入+新程序必须给出完整限定比较。保存每格身份和实际状态，不把人工草案冒充D的产品输出。
- [ ] 当前总控逐分句审阅D与原rubric，明确自验角色；若仍只得到摘录或改变问题含义，不进入接线。维护内聚提交。

**比较反例接口示例：**

```python
def test_client_access_is_not_compared_as_device_uplink(client_and_controller_facts):
    result = compare_connections('device_uplink', ['p', 'q'], client_and_controller_facts)
    assert result.status == 'insufficient'
    assert result.support_fact_ids == []

def test_diagnostic_path_is_not_live_state(diagnostic_path_assembly):
    facts = derive_connection_facts(diagnostic_path_assembly, ['p'])
    fact = next(f for f in facts if f.connection_role == 'documented_physical_path')
    assert fact.speech_act == 'diagnostic_instruction'
    assert fact.operational_status == 'not_observed'
```

## 任务3：显式版本接线、证明和恢复

**Files:** 修改app/answering/comparison_answers.py、app/query_process/agent/nodes/node_answer_output.py、app/runs/query_runner.py、app/runs/telemetry.py、app/evaluation/query_adapter.py、app/evaluation/repository.py、app/evaluation/execution_identity.py；按实际结构复用既有proof投影，新增tests/integration/test_connection_comparison_wiring.py。

**Interfaces:** 新模式从最终ContextAssembly生成prompt-used目录；proof增加assembly/rule/comparator/renderer版本、最终输入hash、源依赖及support_fact_ids。完成核验、缓存推送和恢复均调用同一个纯函数重算入口；失败记录保留既有raw_selection语义。缺省版本不执行任何新装配或派生代码。

- [ ] 先写红测：新模式自由文本/旧答案缓存绕过、最终资料与引用编号不一致、被移出项仍被引用、proof丢失、scope协调篡改、规则或策略漂移均拒绝。旧版本缺省序列化不新增字段。
- [ ] 只在显式新模式分派装配/新消费者；保持原选择JSON和缓冲协议，必要覆盖由程序核对，不信任模型自报角色。预算/来源失败发生在调用前，不静默回退。
- [ ] 同/分库回归覆盖成功、复用、首次outcome冻结前恢复、断流raw持久化、非法选择、失败结算可观测错误及不追加调用。故障只用随机短隔离合成Mongo库。
- [ ] 运行受影响单元/契约/OpenAPI与定向集成，使用实际前端renderEvidence做资料惰性呈现；只报告实际运行范围，不重复无关历史审计。
- [ ] 新模式不能沿r8风险路由创建正式Run：保留旧路由白名单拒绝，补拒绝回归；新真实路由如未来需要须单独风险提案和新授权。
- [ ] 生成脱敏报告/机器摘要、维护导航并普通push修复分支，核本地/origin/实际远程。

## 接线后退出与质量

不同实现身份按新差异定向复核才可记独立技术关闭。当前执行者不能通过自己复核自己补上该身份；不用子Agent绕过用户委派限制。技术通过后再决定正式新候选验证对象、身份与预算，不能继承旧槽、blocked账户或旧质量proof。

本计划不改变M6阶段门槛：04保持验收，05真实反馈复评proof、08有效候选质量与阶段证据仍缺。没有任何测试数量、原文展示或人工设计草案可替代这些证据。
