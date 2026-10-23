# M0：基线与正确性开发 ToDo

> 执行方式：按任务逐项开发；使用 superpowers:executing-plans 技能。任务中的步骤采用勾选框跟踪；不自行派发子代理。

**目标：**交付“基线与正确性”阶段可独立验收的能力。
**架构：**沿现有 Python/FastAPI/LangGraph 链路做小步适配；Vue 3 前端只消费统一 API 与事件契约。保留旧入口与数据直至本阶段验收通过。
**技术栈：**Vue 3 / TypeScript / FastAPI / MongoDB / Milvus / MinIO；具体测试工具与依赖在对应任务中建立。
**设计依据：**[优化方案](../2026-10-22-technical-support-optimization.md)、[接口与数据契约](../DEVELOPMENT_CONTRACTS.md)、[开发总清单](../DEVELOPMENT_TODO.md)。

## 进入条件与执行约束

无前置阶段；本阶段是首次开发入口。

- 以下文件均为**计划创建/修改**，不表示已经存在；执行前用 `rg` 核对真实接口与源码。
- 本阶段遵守总清单中的 Vue 3、中文注释、数据隔离、配置脱敏和完成证据规则。
- 每个代码任务先增加能揭示错误的用例，再做最小实现；文档、样式等低影响变更按实际结果检查，不写镜像测试。
- 每完成一个任务，记录验证命令、输出摘要、涉及文件和遗留问题；验证通过后才勾选[总清单](../DEVELOPMENT_TODO.md)，并更新[进度](../../development/PROGRESS.md)与[变更记录](../../development/CHANGELOG.md)。
- 命令均从项目根目录运行；`pnpm -C frontend` 命令需 M3-01 建立对应 scripts 后才存在。依赖安装和测试数据准备不表示任务验收通过。
- 每个任务验证其直接影响的行为，阶段验收时再执行阶段回归；不要重复运行无关全量测试。

<a id="m0-01"></a>
### M0-01：环境与数据保护基线

**依赖：**无。
**文件：**`docs/development/baseline.md`; `scripts/verification/check_environment.py`; `.env.example`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M0-01.1** 记录 Python/依赖/硬件及现有接口。
- [x] **M0-01.2** 只检查配置项名称和是否存在，不记录值。
- [x] **M0-01.3** 列出现有集合/桶并规划独立测试命名空间。
- [x] **M0-01.V** 验证：.venv/Scripts/python.exe scripts/verification/check_environment.py --redact。
- [x] **M0-01.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**报告区分历史入库记录与本次实测；没有写入原知识库；缺项以变量名列出。

<a id="m0-02"></a>
### M0-02：独立测试入口

**依赖：**M0-01。
**文件：**`pyproject.toml`; `uv.lock`; `tests/conftest.py`; `tests/unit/test_io_isolation.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M0-02.1** 增加 pytest 开发依赖和 unit/contract/integration/e2e 标记。
- [x] **M0-02.2** 默认只收集 tests/unit 与 tests/contract。
- [x] **M0-02.3** 外部客户端用作用域明确的 fake，禁止无标记联网和下载模型。
- [x] **M0-02.4** 为正常模块导入建立 IO 隔离边界：先注入 fake 仓储/客户端再导入旧节点或 API；补 `history_store.seed/last_sort` 夹具。若模块导入仍触发真实服务，将初始化移到调用边界并补导入无副作用用例；不把 AST 抽取当作最终应用回归。
- [x] **M0-02.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_io_isolation.py -q。
- [x] **M0-02.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**无密钥、无 Docker 时单元测试可运行；意外联网会明确失败；既有 test/ 手工脚本不被批量收集。

<a id="m0-03"></a>
### M0-03：最近历史窗口修复 A01

**依赖：**M0-02。
**文件：**`app/clients/mongo_history_utils.py`; `tests/unit/test_history_window.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M0-03.1** 先复现 20 取 10 返回最早记录。
- [x] **M0-03.2** 改为 ts/_id 倒序取窗口后反转，校验 limit。
- [x] **M0-03.3** 覆盖同时间戳、空历史与不同会话。
- [x] **M0-03.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_history_window.py -q。
- [x] **M0-03.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**返回最新十条且按时间正序；同时间戳排序稳定；limit 小于 1 明确拒绝。

<a id="m0-04"></a>
### M0-04：上下文预算修复 A02/A03

**依赖：**M0-02。
**文件：**`app/answering/context_budget.py`; `app/query_process/agent/nodes/node_answer_output.py`; `tests/unit/test_context_budget.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M0-04.1** 抽出 pack_prompt_inputs 纯函数。
- [x] **M0-04.2** 首块放不下继续尝试后续块，历史优先最近可容纳完整消息。
- [x] **M0-04.3** 计入头部和分隔符，返回 used_chunk_ids。
- [x] **M0-04.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_context_budget.py -q。
- [x] **M0-04.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**首块 12001 字时短块仍被纳入；13000 字单条历史不越界；图片标记与 URL 不被截断；本阶段仍明确使用字符预算。

<a id="m0-05"></a>
### M0-05：型号歧义修复 A04

**依赖：**M0-02。
**文件：**`app/query_process/agent/nodes/node_item_name_confirm.py`; `tests/unit/test_product_resolution.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M0-05.1** 先复现 M3070 对 DHF/DXF 近分自动选第一。
- [x] **M0-05.2** 保留精确型号匹配，多个高分非精确命中走候选确认。
- [x] **M0-05.3** 把现有阈值提成具名配置并记录只是基线。
- [x] **M0-05.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_product_resolution.py -q。
- [x] **M0-05.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**0.91/0.90 返回两个候选而非确认；精确 M3070DHF 可确认；低分无匹配；不把分数称为概率。

<a id="m0-06"></a>
### M0-06：短章节边界修复 A05

**依赖：**M0-02。
**文件：**`app/import_process/agent/nodes/node_document_split.py`; `tests/unit/test_chunk_structure.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M0-06.1** 先复现缺父标题的不同章节被合并。
- [x] **M0-06.2** 缺结构标识时保守不合并，同源有相同明确父标识才允许；R1 已在正常标题拆分生成本轮章节实例 ID，长块传播，不把标题文字当章节身份。
- [x] **M0-06.3** 合并前检查总大小且不原地污染输入。
- [x] **M0-06.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_chunk_structure.py -q；完整 step_2→step_4 红测 5 failed/17 passed，修复后 23 passed。
- [x] **M0-06.D** 保存修复与复验记录，更新总清单、进度和变更记录；保留首轮验收和总控重开历史。

**验收：**独立章节不合并；同父相邻短块可合并；不同资料/型号或表格边界不合并；标题和来源仍完整。

<a id="m0-07"></a>
### M0-07：生成失败与终态修复 A06

**依赖：**M0-02。
**文件：**`app/answering/errors.py`; `app/query_process/agent/nodes/node_answer_output.py`; `app/query_process/api/query_service.py`; `tests/unit/test_generation_failure.py`; `tests/contract/test_legacy_query_failure.py`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M0-07.1** 假客户端先 delta 再抛超时。
- [x] **M0-07.2** 定义携带 partial_answer 的 AnswerGenerationError 并传播至外层。
- [x] **M0-07.3** 仅成功路径保存成功消息并发 completed，失败保留部分文本和 error。
- [x] **M0-07.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_generation_failure.py tests/contract/test_legacy_query_failure.py -q。
- [x] **M0-07.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**注入超时后无 completed/final-success，任务为 failed；非流式失败同样处理；正常流仍完整结束且不重复终态。

<a id="m0-08"></a>
### M0-08：LLM 参数与日志基线修复

**依赖：**M0-02。
**文件：**`app/lm/lm_utils.py`; `app/conf/lm_config.py`; `app/query_process/agent/nodes/node_answer_output.py`; `tests/unit/test_llm_options.py`; `docs/CONFIGURATION.md`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M0-08.1** 保留 temperature=0。
- [x] **M0-08.2** 把 enable_thinking 改为按 provider 能力传入。
- [x] **M0-08.3** 停止默认打印完整 prompt 和签名 URL，记录阶段/ID/长度。
- [x] **M0-08.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit/test_llm_options.py -q。
- [x] **M0-08.D** 保存验证记录，更新总清单、进度和变更记录；接口/配置/复用变动时同步相关文档。

**验收：**fake 构造器收到合法零值；普通兼容供应商不收专属字段；日志用合成标记验证无完整知识/密钥泄漏。

<a id="m0-09"></a>
### M0-09：M0 阶段验收

**依赖：**M0-03,M0-04,M0-05,M0-06,M0-07,M0-08。
**文件：**`docs/development/records/M0-09.md`; `docs/development/PROGRESS.md`; `evals/datasets/baseline-manifest.json`。
**接口：**遵循[公共契约](../DEVELOPMENT_CONTRACTS.md)；本任务只建立本段列出的模块，供后续依赖任务使用。

- [x] **M0-09.1** 汇总 A01–A06 正式回归。
- [x] **M0-09.2** 运行既有重导入回归。
- [x] **M0-09.3** 原已知题/追问证据保留；R3复用原会话图片题83.858秒，准确拓扑真实HTTP/hash/解码及正文/final通过；正常配置新进程冷启动56.599秒通过。详见M0-submission-r3.md，原失败根因未复现，仍未知。
- [x] **M0-09.V** 验证：.venv/Scripts/python.exe -m pytest tests/unit tests/contract -q；.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q。
- [x] **M0-09.D** 保存r3真实报告与独立快照，105项单元/契约及3项既有重导入通过，同步清单/进度/变更/契约/配置/ADR-016；第3轮总控通过，M1实现已授权，见M0-review-r3.md。

**验收：**六项回归和既有用例通过；真实链路如缺配置则保持未完成并列出缺项；不凭历史截图通过本阶段。

## 第一批回归用例与接口草图

以下代码是开发时要落地的测试规格，当前仅保存在文档中。最终测试应通过正常模块导入/依赖注入运行，不能只 AST 抽取函数后声称线上链路通过。外部 IO 用 fake；M0-07 还必须覆盖外层 API 的终态。

#### M0-03：最近历史

在 `tests/unit/test_history_window.py` 使用 `monkeypatch` 替换模块的 `get_history_mongo_tool`；fake collection 支持 `find().sort().limit()`，并记录排序参数。

```python
def test_latest_ten_are_returned_in_chronological_order(history_store):
    from app.clients.mongo_history_utils import get_recent_messages
    history_store.seed([
        {"_id": f"{i:02}", "session_id": "s1", "ts": i, "text": str(i)}
        for i in range(1, 21)
    ])
    messages = get_recent_messages("s1", limit=10)
    assert [m["ts"] for m in messages] == list(range(11, 21))
    assert history_store.last_sort == [("ts", -1), ("_id", -1)]
```

`history_store` 在 M0-02 测试夹具中建立，暴露 `seed(records)` 与 `last_sort`。用例先在旧实现上失败，修复后再补同时间戳/空数据/其他会话/非法 limit。

#### M0-04：预算纯函数

拟新增接口：

```text
pack_prompt_inputs(docs: list[dict], history: list[dict], max_chars: int = 12000) -> dict
返回字段：context: str、history: str、used_chars: int、used_chunk_ids: list[str]
used_chars 包含实际打包的元信息和分隔符。
```

该函数只打包证据和历史，不调用 LLM。先整体放入能容纳的证据；单条证据过长则跳过并继续，M4 再加入结构化拆分/token 预算。历史按最近完整消息选取，再按时间正序输出。实际加入提示词的“无参考内容/无历史对话”占位文本也计入预算；纯函数可用空串返回，由调用方计入模板固定开销。

```python
def test_oversize_first_document_does_not_hide_later_evidence():
    from app.answering.context_budget import pack_prompt_inputs
    result = pack_prompt_inputs([
        {"chunk_id": "long", "text": "长" * 12001},
        {"chunk_id": "short", "text": "短证据"},
    ], [], max_chars=12000)
    assert "短证据" in result["context"]
    assert result["used_chunk_ids"] == ["short"]
    assert result["used_chars"] <= 12000


def test_oversize_history_is_not_appended_before_checking():
    from app.answering.context_budget import pack_prompt_inputs
    result = pack_prompt_inputs([], [
        {"role": "user", "text": "长" * 13000},
        {"role": "user", "text": "最近的问题"},
    ], max_chars=12000)
    assert "最近的问题" in result["history"]
    assert result["used_chars"] <= 12000
```

#### M0-05：多高分候选

```python
def test_nearby_high_scores_require_product_clarification():
    from app.query_process.agent.nodes.node_item_name_confirm import step_5_align_item_names
    result = step_5_align_item_names([{
        "extracted_name": "M3070",
        "matches": [
            {"item_name": "M3070DHF", "score": 0.91},
            {"item_name": "M3070DXF", "score": 0.90},
        ],
    }])
    assert result["confirmed_item_names"] == []
    assert set(result["options"]) == {"M3070DHF", "M3070DXF"}
```

#### M0-06：结构边界

```python
def test_missing_parent_does_not_merge_unrelated_chapters():
    from app.import_process.agent.nodes.node_document_split import _merge_short_sections
    sections = [
        {"title": "# 安装", "content": "AAAAA"},
        {"title": "# 故障", "content": "BBBBB"},
    ]
    actual = _merge_short_sections(sections, min_length=100)
    assert len(actual) == 2
    assert [s["title"] for s in actual] == ["# 安装", "# 故障"]
```

#### M0-07：部分答案后失败

新增 `AnswerGenerationError` 继承 `RuntimeError`，包含 `partial_answer: str`。单元 fake LLM 先 yield 一个 `.content='部分答案'` 的块，再抛 `TimeoutError`。断言输出节点抛该类型且保留 partial_answer；契约测试替换外层 `query_app.invoke` 注入同一异常，断言任务 failed、无 completed 事件，且失败不会保存为成功助手消息。正常流与非流式错误均单独覆盖。

### 开发和验收命令

```powershell
# 在 M0-02 增加开发依赖组并锁定后执行。
uv sync --locked --group dev --python .venv/Scripts/python.exe
.venv/Scripts/python.exe -m pytest tests/unit/test_history_window.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_context_budget.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_product_resolution.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_chunk_structure.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_generation_failure.py tests/contract/test_legacy_query_failure.py -q
.venv/Scripts/python.exe -m unittest discover -s test -p test_document_reimport.py -q
```

首次运行目标回归应出现对应行为失败，不能把依赖缺失或 ImportError 当作行为已复现；修复后定向验证通过，再执行 M0 阶段回归。若包安装会改变当前 GPU 构建，先按 M0-01 保存环境并选择隔离测试环境，不能直接覆盖现有可用环境。


M0-09 实施补充：真实小样发现 FlagEmbedding 1.3.5 使用 devices 参数，旧 device 被忽略；最小修正并增加 test_reranker_options，记录 ADR-012。无模型升级或原数据迁移。history API 非法 limit 返回 422、多型号存在任一歧义优先澄清，补充外层边界回归。

2026-10-23 接续：阶段回归 73 passed、既有重导入 3 passed。真实已知题/追问通过，图片题失败尚待定位；Docker Desktop 启动被本机 dockerInference socket 错误阻塞，无法连接 Milvus。M0-09.3/D 与总任务保持未完成；提交部分结果供总控审查，恢复条件/精确命令见 records/M0-09.md。未进入 M1。

2026-10-23 第 2 轮：R1 已修复并完成 23 项切片回归；R2 共享图片检查的反例红测 10 failed/2 passed，补充边界后 19 passed，已确认图1准确对象/hash及可解码缓存。最新阶段回归 103 passed（实际新增30项），既有重导入 3 passed，见 M0-r2-validation.json。Docker 单次只读检查退出1，Linux 引擎管道仍不存在；未重复真实预检或云调用。R3 原图片异常根因、真实图片 HTTP/正文/final 和默认冷启动保持未完成。复审材料为 M0-submission-r2.md；旧提交、失败和 manifest 保留，新快照为 baseline-manifest-r2.json。
