# M6 attributed_assertions_v1 有界真实诊断执行 r1

2026-10-31，Asia/Shanghai。接续本地899219ca42732643956b39e85a7ecdf6c26ba5de；业务源码及prompt仍为独立通过的b6ce85a，未开同类补修包。开始仅未跟踪tmp/；origin/main缓存仍b6ce85a，直连远程核验exit 1（443连接超时），不能将本地追踪引用当成GitHub即时状态。

## 实际退出结果

**有界诊断停在答案调用前，未产生新答案。** 完整固定两版各27题、54份单题子配置后，正式计划／查询投影与精确缓存预检在版1第3题 `m6-g540-03-a` 发现缺项，按“任一缓存缺失即停”规则退出；没有补编码、重排、重导入或抽样重试，没有创建正式实验或Run。

缺失精确key：`3370e416d3237939d907a7f6cc12cd762a7db0c792ebbee08c975cdd3e0fec3b`；查询hash：`d2cf8c2d88fc83d2ecc984de1befd57cde4ec6a98227e07689af68d522cfb547`。它对应现行`plan_query → scoped_subject_v1 → source_network_terms_v1`得到的单条query输入，模型／device／runtime／单文本batch均使用原封存缓存键合同。实际计划与该题旧正式Run计划全等，不是改题、换词或漏算产品投影导致的任意key。

扫描44条可识别的已完成query缓存，位于原真实检索、masked-v2、术语及比较诊断的model-cache/embedding_query目录，保留所有旧文件；已有两种格式key/value/value_sha256及value/sha256均按原合同核验，整数稀疏键还原后校验value hash。版1前两题02-a／02-b精确查询缓存匹配，**仅是缓存匹配，不是完成两题生成／语义诊断**。第3题缺项后停止，其他范围缓存覆盖、重排pair、最终context／prompt以及真实授权／当前索引预检尚未继续，不能声称其通过。未声称全机器任意未知格式缓存不存在，也不能说全范围只缺1项。

## 已固定身份与保护

正式runtime实际核得源码 `bcbc147ce1183fb5cf774099c8080838bc11284919bc2939d346f6e3de9932da`、prompt `5c0cb39e58800fc437c1f32b48b05540363ea8dbb8a147f5e030aa84a59aa9dc`、模型 `565fbfe4c795fb52f84183f7b2708491fd7824fa07f2de9fd546e9d6d6e5bb90`，与授权全等；实际供应商模型名称 `qwen3.8-flash`，端点仅存hash，未输出.env值。沿用旧候选相同的本地模型运行overlay，不改.env或永久Git配置，不加载或下载模型做新推理。

在新目录固定完整题目顺序、两版本原题集／manifest／反馈派生身份、旧实验／Run／subject／prompt／答案hash、四原件及解析缓存SHA、产品／修订／组合术语／p30审阅证明和唯一归属策略。54份新子配置均经EvaluationCatalog及策略合同解析；保持完整150题（85 dev／65 heldout）文件及原descriptor不变，只选一个dev题，明确无quality_policy／校准／regression_source／baseline。没有真实题集重登记或复用旧19／旧v2检查点。

首版本机准备辅助result hash读取包装层错误，尚未执行即发现；原封存不覆盖，`prepared-r2/`补齐真实subject/result/answer/prompt hash并重新计算稳定请求键。首版缓存读取器不兼容既存旧格式，exit 1日志保留；r2读取器兼容原格式后得到真实缺项，exit 2是本包规定停止，不是质量通过。它们均不是新业务源码补修或清理历史失败。

本包新增答案stream／编码／重排均0，累计和本次新增分账均0；未创建实验／Run／质量记录，无新子Agent，047正式零答案对照也尚未执行。已核历史336逻辑stream、input644642／output355857仅为指定基线／候选口径，不是全项目总量；历史精确HTTP／费用及本包未知usage保持null，不用结果行数推断历史0。没有访问真实数据库、重扫向量或默认指针；停止前的本机文件检查不冒称live状态审计。

四原件和两版本解析缓存文件SHA匹配；1182份开工保护及既有1205／240／609文件清单逐项hash全匹配，组间重叠不累计。退出审计实际3741条断言核验主身份、54配置、54旧subject/result/answer、44缓存文件和保护清单，**仅证明准备和保护完整性，不是答案质量分**。旧v2 blocked、原分、失败及04验收结论保持。

## 命令、材料与下一步

| 实际命令（均为本机新目录脚本） | 退出 | 结论 |
| --- | --- | --- |
| `.venv/Scripts/python.exe output/m6-attributed-evidence-diagnostic-20261031/startup.py` | 0 | runtime全等、54单题配置初步准备，无模型调用 |
| `.venv/Scripts/python.exe output/m6-attributed-evidence-diagnostic-20261031/cache_preflight.py` | 1 | 读取器初版旧格式KeyError；原日志保留 |
| `.venv/Scripts/python.exe output/m6-attributed-evidence-diagnostic-20261031/cache_preflight_r2.py` | 2 | 版1 03-a固定精确查询缓存缺失，按约停止 |
| `.venv/Scripts/python.exe output/m6-attributed-evidence-diagnostic-20261031/audit_and_deliver.py` | 0 | 实际退出材料及保护审计通过，不运行真实服务；原始回执保留于audit-delivery.log |

本机 `output/m6-attributed-evidence-diagnostic-20261031/` 保留两版准备、原始失败、stop.json、完整54条未执行清单及`有界诊断执行对照.html`；无新答案可评分，不另做空评分表或要求用户找PDF。脱敏[验证摘要](M6-attributed-evidence-diagnostic-execution-validation-r1.json)列明逐题身份、缺项和未执行边界。所有PDF／完整旧答案／缓存／私有日志不上Git，tmp保留。

**唯一下一动作：总控裁定该固定请求缓存缺项的受控补齐授权与预算。** 当前指令禁止任何新增编码／重排，因此执行方未以52个答案stream授权扩大这两类调用；获得明确处理后才继续原范围的完整缓存预检，再决定是否派发正式单题job。剩余覆盖未知，不先承诺只需一次编码、不改策略或自动扩大生成。无需用户重找原件、账号或重评分。

技术三项关闭结论保留。本包没有新策略真实答案效果结论或有效完整候选质量证据。M6保持5/7，04已验收，05待有效反馈proof、08待有效完整候选质量链及阶段验收；M7未启动。

收口时直连远程核验已恢复：同一`ls-remote`命令exit 0，GitHub main实际为`b6ce85acf8ec9b7e9b8694ac573219f92f5c6169`，与本地origin/main缓存匹配，本地899219c尚在其后。开工网络失败记录保留；后续按正常快进推送，实际提交／推送结果见交付回执，不将此推送前读数写成最终已同步。
