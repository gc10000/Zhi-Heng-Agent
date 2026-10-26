# M6-08 / 001 第二次定向修复提交

日期：2026-10-26。起点 main / `e295db53f354c2715e1754460ecb7b0873ec75be`。范围仅为 [R001-1 定向复核](M6-08-001-review.md)，提交总控定向复审；执行会话不自行关闭问题。M6 核心仍4/7，M6-04/05/08未验收，M7未授权。

## 修复与来源边界

移除 resolver 的通用字母后缀放行。新增 `app/products/equivalences.py`，仅把标准名 H3C LA2608 对应到完整 LA2608-GM/GU；记录原件名、SHA256 `72983cc9b60f7f165bf89d3f6cbe39d56c4db148fd4b894c70c37378f8be5c8e`、物理页4、1.1概述和短引文。标准名精确匹配，非空品牌须一致，其他品牌不继承；不自动生成单独GM、GU或其他后缀。正式目录完整别名仍有效。

普通和显式型号扫描均保留完整斜线身份，不能截取已知前缀绕过未知型号门禁。接口编号随完整token检查，保留原有限接口前缀和接口/端口语境限制。没有修改API、默认策略、模型、配置、依赖、索引、题集或历史运行。ADR-063替代原ADR-062，原失败记录保留。

| 边界 | 修复前 | 修复后正式入口 |
| --- | --- | --- |
| GM/GU普通与显式写法 | completed | completed，注入答案、引用和助手消息持久保存 |
| ZZ、显式FAKE | completed，错误调用生成 | awaiting_input，零模型调用、无答案/引用/助手消息 |
| GM/FAKE、GM/GU/FAKE | completed，错误截取前缀 | awaiting_input，同上 |
| GM/GU2、未知基础LA2609、独立AX-42 | awaiting_input | 仍awaiting_input |
| 正式目录斜线别名AX-24-M/N | 被截取误澄清 | 按完整别名回答（单元验证） |
| Other LA2608 | 错误继承通用后缀 | 不继承H3C来源映射（单元验证） |

## 本轮实际验证

所有命令在项目根执行，使用现有 `.venv/Scripts/python.exe`，`PYTHONUTF8=1`。原始输出在新目录 `output/m6-08/r001-1-r2/` 与 `output/m6-08/r001-1-r2-stage/`，不覆盖首轮提交、总控探针或916项历史结果。

| 验证 | 实际结果 | 退出码 | 原件 |
| --- | --- | --- | --- |
| 正式入口业务红测，修复前 | 4 failed、5 passed、7 deselected；0 error | 1 | red.txt / red.xml |
| 规划边界业务红测，修复前 | 6 failed、2 passed、32 deselected；0 error | 1 | unit-red.txt / unit-red.xml |
| 规划/解析/正式入口组合，修复后 | 63 passed：47 unit、16 integration，0 skipped | 0 | targeted.txt / targeted.xml |
| 原总控5项探针的新目录副本 | 5 passed | 0 | probe.txt / probe.xml及五项实际运行观察 |
| 共享后端阶段回归 | 933 passed、2 deselected、0 skipped；574 unit、135 contract、224 integration，7项既有SWIG弃用警告 | 0 | r001-1-r2-stage/backend.txt / backend.xml |
| 既有重导入 | 3 passed | 0 | r001-1-r2-stage/reimport.txt |
| 原定向审查证据完整性 | 9份hash一致 | 0 | original-integrity.json |

精确命令：

```powershell
$env:PYTHONUTF8='1'
$env:M1_TEST_DB='m1_test_m6_r001_red_20261026'
.venv/Scripts/python.exe -m pytest tests/integration/test_query_planning.py -k only_source_confirmed_full_variant -q --tb=short --junitxml=output/m6-08/r001-1-r2/red.xml
.venv/Scripts/python.exe -m pytest tests/unit/test_query_plans.py -k 'unregistered_full_variant or full_slash_alias or source_equivalence' -q --tb=short --junitxml=output/m6-08/r001-1-r2/unit-red.xml
$env:M1_TEST_DB='m1_test_m6_r001_green_20261026'
.venv/Scripts/python.exe -m pytest tests/unit/test_product_resolution.py tests/unit/test_query_plans.py tests/integration/test_query_planning.py -q --tb=short --junitxml=output/m6-08/r001-1-r2/targeted.xml
$env:M1_TEST_DB='m1_test_m6_r001_probe_20261026'
Copy-Item -LiteralPath output/m6-08/001-independent-review-20261026/test_variant_boundaries.py -Destination output/m6-08/r001-1-r2/test_variant_boundaries.py
.venv/Scripts/python.exe -m pytest output/m6-08/r001-1-r2/test_variant_boundaries.py -q --tb=short --junitxml=output/m6-08/r001-1-r2/probe.xml
.venv/Scripts/python.exe -m scripts.verification.run_m5_checks --output output/m6-08/r001-1-r2-stage --group backend
```

原探针会向自身目录写观察JSON，因此只运行新目录副本，原件与原失败证据不改。正常/显式写法、未知后缀、未知基础、已登记别名、品牌隔离、接口编号和正式外层状态均有覆盖；红测均到达业务断言，无ImportError或夹具错误冒充复现。阶段回归由脚本独立生成 `m1_test_m4_m5_stage_df0c259c` 前缀，逐命令参数/实际退出码见commands.json。63项和探针与阶段回归有重叠，不能相加宣称独立覆盖数。

## 数据、真实验证与遗留

新增正式入口使用真实独立Mongo，检索/模型端口注入，不是付费问答或真实答案质量证明。单元不联网；共享集成使用原有隔离数据边界。未重跑真实001、未运行heldout、未重调供应商，新增付费调用0，人工评分写入0。原定向审查的9份证据仅做hash核对，不宣称本轮真实HTTP通过。前端未修改，本轮未重跑前端；验证摘要中前端、真实小样和检查点字段明确标作历史材料，其hash复核不能替代当前真实验证。

新 [验证摘要](M6-08-001-validation-r2.json) 绑定实际XML/输出hash；新 [独立快照](M6-08-001-manifest-r2-final.json) 由现有检查器显式选择报告/快照生成。原件、tmp、evals、output和原始evidence不上传。Git为main正常小提交/推送，自身SHA和远程核对在最终交接补记，不循环amend。

回滚为反向本轮源码提交；不删除或覆盖原件、数据库、运行、评分和证据。回滚会重新引入通用后缀误确认，不能把回滚状态作为可用修复。后续先由总控定向复审R001-1，再在获准的新代码/新隔离版本上安排真实001及M6内反馈复评；本提交不宣称M6阶段通过。
