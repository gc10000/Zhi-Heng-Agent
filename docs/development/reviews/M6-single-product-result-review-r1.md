# M6唯一新版05-a实际结果总控独立复核 r1

日期：2026-11-01，Asia/Shanghai。角色：总控独立复核；不是执行自验转述、正式双轮评分或阶段验收。

## 裁定

本轮启动HEAD为执行提交`3017a61573f2e6d34edd95f9bb39e88824e0e4b7`，缓存origin/main为`6960af72c8bf7b541acce638ac654053cd9f4750`，工作区仅tmp。审查对象是唯一版1新版`m6-g540-05-a`的实际封存结果，保留d41b3a4与6960af7既有技术结论，不重跑历史75项集成或整轮预检。

**独立通过并关闭“05-a机身／具名配件归属的单次真实答案效果”和“该次正式执行／usage／固定槽结算闭合”两个子项。** 实际答案先以机身RJ45回答原问题，再将LAN明确具名归属HUAWEI MateDock 3并声明不能套写为机身接口；引用与实际所选证据及已审关系相符。这个结果有真实可见正文，不再写为“新答案效果尚未验证”或“待总控复核”。

关闭范围仅此结果；不将一次成功写成全部问题、所有题或正式质量通过。原48 job保持暂停，唯一槽已消费不可重领；本轮没有批准或执行更多生成。

## 完整核验矩阵

| 边界 | 独立实际结果 | 裁定 |
| --- | --- | --- |
| 授权／输入身份 | 封存Git授权、完整150题／85 dev、当前app源码、runtime、prepared配置、请求与实际wire匹配；prompt／context／分组／reference_map沿精确输入锚 | passed，旧准入关闭保持 |
| 原始输出／持久结果 | 原SSE重组530个JSON事件、1个DONE，所有choice为index0；正文272字符、reasoning正文3022字符；finish仅stop；原流正文＝Run＝公开结果＝完整attempt，未截断 | passed，实际可见结果成立 |
| 机身答案 | 首段回答RJ45；引用1对应同修订机身表行，物理p5 exact | passed，限定诊断关闭 |
| 配件具名归属 | 第二段具名HUAWEI MateDock 3的LAN并明确与机身分开；引用2按真实切片／元数据重新attach已审Git成员关系，全等 | passed，限定诊断关闭 |
| 出处边界 | LAN行physical_pages为空、page_status unknown、citation页码null；标题p13／表p14仅作表级已审关系 | passed，未把表级证据冒充行定位 |
| 正式链与来源 | 一个请求实验、一个登记配置实验、一个账户；实验／Run completed、attempt1／一题；题级关联、checkpoint、完整冻结outcome与当前只读Mongo一致 | passed，该次正式链关闭 |
| 原始usage | 独立读原SSE并重算，raw usage合法／完整；input5165、output1702含reasoning1510、total6867；与SDK raw验证、Run账户、磁盘settled全等 | passed，该次计量闭合 |
| 调用前与结算 | 网络hook封存同Run的pending、input预留12293及logical_reservations1，started文件hash全等；最终单次settled、pending空、unknown_windows空 | passed，该次结算闭合；账户open不产生第二次额度 |
| 缓存与调用范围 | 1编码缓存／20 pair／3检索响应命中，miss0、无本地推理fallback；一个逻辑stream，观察到1次request hook及200 response hook | passed；不充作端到端HTTP总次数证明 |
| 证据与保护 | 41项交付文件封存hash及138／336／597／1314历史保护组匹配；本轮5448项来源／状态／流事件／文件断言通过，组间重叠 | passed，不计为唯一测试数或质量分 |

本轮未重新找PDF或重审已关闭的原件归属语义，只核已审Git证明／成员在实际输入及回答中的消费。旧05-a、旧候选blocked、旧评分、原失败与48未执行清单保持，不把新单题替换成旧候选结果或从旧清单扣除。

## 身份和账本

实验`281d874c-0a8c-4520-b214-a69c54b0b0be`，Run `d3649c7a-e79b-4b91-9165-b83462634cb4`，固定槽`m6-05a-product-canary-r1`已started／settled，只能只读复用。

- app源码：`b50b1f5b0eab66d7a4eb2a32314bcd415dba2624354cfb0ece59d2efce17ab8b`。
- 配置canonical：`22d0e525ba1074336a6d7af973cc50427eb96e4c3f5ad28d9a3c60e37ff65efc`。
- catalog配置文件SHA：`288f014ee987675a93151e54c40c54a83ea9996968f6a7c593157d17fb0e2b04`。正式实验存此文件hash，题级关联另存canonical；两者用途分开，不强行改成同一值。
- manifest：`0e94544429f865b2f2e35193f9f915e06282de9c1faf85fafe27d4891bb85533`。
- 原响应SHA：`52005c2445c2ff21aaebd88be00f8dfdfaffe522e150e586ae99c51a7700d462`。

| 分账 | input | output（含reasoning） |
| --- | --- | --- |
| 原六流＋非产品探测前值 | 23582 | 20602 |
| 执行方此次唯一产品流 | 5165 | 1702 |
| 本诊断累计观测 | 28747 | 22304 |
| 本轮总控新增推理 | 0 | 0 |

reasoning1510已含于1702，不再相加；192只是算术差值，不称实测可见token。visible_tokens、精确HTTP总次数、费用仍null。请求4096及此次output1702不证明网关全域硬限；能力和最大付费输出上界仍unknown，不登记verified、不恢复其他题。本诊断累计不是全项目历史总量。

## 审计失败、限制与保护

私有目录为`output/m6-single-product-result-review-20261101/`。本轮审阅旧审计脚本后另写独立只读脚本，没有原地运行会写旧目录的脚本。首轮审计将catalog登记文件hash误按canonical hash查实验，计数断言失败；只读定位确认正式catalog源码使用file_sha，关联同时保存registered_config_sha256与canonical。r2按各自定义校验后完整通过。原脚本、失败日志、count-diagnosis及成功r2日志全部保留；未改正式数据或重新生成。执行方此前两次审计投影／日期导出失败亦按41项封存文件原样核对。

真实Mongo仅find／count读取，无索引登记、无实验创建、无state／lease／slot手改，无正式质量写入。未全量扫描582／867向量、所有旧质量记录、默认指针、run_events或TTL；历史内容保护限于封存文件hash，不称全库逐文档证明。私有原流、答案、缓存、PDF与日志不提交，private-identity未读，tmp保留。

## 剩余问题与退出边界

本次已不再卡在05-a能否消费具名归属、单题能否产生可见答案或本次能否合法结算。仍未满足的是：

| 剩余范围 | 当前事实／具体退出条件 |
| --- | --- |
| 其余诊断及题目效果 | 原48 job暂停，04-a／05-b／17-b及048等不由此单题成功替代；没有本批新答案与完整质量证据。后续范围必须单独裁定，不能复用已消费槽或自动扩批。 |
| 输出运行边界 | 正常v2 unknown门禁保持；本次仅消费一次限定风险授权，不产生对余题的授权或全域能力结论。 |
| M6-08 | 有效新候选、同范围政策与配置绑定的独立双轮、有效校准／gate及阶段验收证据仍未闭合；本结果不是对旧blocked候选的改分。 |
| M6-05 | 001正式标签消费保持关闭；仍缺与有效实际实验、精确版本和校准关联的真实反馈服务端复评proof。 |

M6保持5/7，04保持验收，05／08未验收；M7未授权。下一动作是交付本次独立关闭结论并保留停机边界；不再对本题追加生成、重新评分或重复复核，也不在本包裁定扩大范围。后续若接续剩余质量链，需以本结论为已完成证据组织一包明确范围，不能把同一个05-a再作为准备任务。

提交同步沿普通push，保留执行提交3017a61本身及本轮独立文档提交；实际远程结果以最终回执为准。
