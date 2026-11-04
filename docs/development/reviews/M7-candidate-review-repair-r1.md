# M7候选独立复核补修交付 r1

2026-11-04；分支`codex/m6-source-bound-comparison`；复核起点`2bc736adff4249d97b269c02fcc6d417bb76f360`。用户明确授权唯一不同实现身份审查者`/root/independent_m7_candidate_review`。本报告由总控实现方编写，只签实现补修与自验；独立结论由原审查者另签，不借用M6已审范围。

## 已定位和修复

1. **R1：不同恢复任务共享目标仍可覆盖。** 独立复现证明不同Mongo目标/桶共用同一向量集合时，B预检后暂停、A恢复、B继续会覆盖A。恢复现改为同一存储绑定共享控制库，database/bucket/collection三种资源各有唯一claim，全部取得后才写任何目标；成功、失败、部分及未知预留均无TTL、不释放。缺共享控制身份或与源/目标库重合则写前拒绝。既有随机预览按项目身份稳定派生兼容，新预览显式写`M7_RESTORE_CONTROL_DATABASE`。各进程必须共用控制库；不承诺防止绕开工具的直接存储写入。原审查者已独立复测三轴竞争及失败保留。
2. **R2：合法65至1000个重排候选经宿主桥接422。** 原桥接一次发送全部pairs，宿主单批最多64。现完整校验输入后按64对/256000字符分批、保序合并，单对超限在任何HTTP前拒绝；单Session/禁redirect/不重试，各批核分数数量、严格数值及有限性；共用deadline、下一批仅使用剩余timeout。requests读超时不等于硬墙钟上限，不宣称供应商硬限。原审查者以合成宿主独立比较20/64/65/1000分数与顺序、字符边界、异常及超时。

默认镜像tag及审计入口同步为`m7-r3`，审计可显式指定旧镜像；web仅为r1内容同一镜像的新alias。r1/r2镜像/精确覆盖/失败证据不删除，最终使用[r3精确覆盖](../releases/M7-delivery-r3.compose.json)。

## 实现自验与失败历史

- 共享恢复：首轮因未传隔离测试库而被测试护栏清除环境，4失败是夹具/权限问题；修正运行入口后真实红测2通过/2失败，补修后绿。
- 重排桥接：新增4反例先红（4失败/9通过），补修后通过。
- 主机最终受影响集：42通过/1Windows符号链接权限跳过；Linux镜像另测该边界通过。
- 最终r3 verification容器组合：74通过，包含受影响查询/输出/正式Run合成集成、重排桥接、控制身份、恢复guard及索引顺序；模型端口为合成，不是模型答案质量。恢复竞争的真实隔离存储用例在主机42组和独立复测执行，不冒称74组包含这些用例。组间重叠不累计。
- 最终镜像审计：API277文件逐字节匹配工作树源码，web485文件；有限秘密排除、API无torch通过。并非未知秘密全量扫描。live/ready均200，api/worker/dispatcher生成和评测关闭、模型key/host为空。

原始红绿、命令及JUnit保留`output/m7-review-coordination-20261104-r1/`；独立红绿保留`output/m7-independent-review-20261104-r1/`，不上传。脱敏hash及准确计数见[机器清单](M7-candidate-review-repair-r1.json)。独立最终签字仍由原审查者完成，不能用本报告替代。

## 当前可用候选和恢复

入口 **http://127.0.0.1:18080**，仍为独立随机预览项目。已有私有`runtime.env`保留原始`m7-r1`值以保护旧证据；必须叠加以下r3精确覆盖，不使用裸compose up回到旧镜像：

```powershell
docker compose --env-file output/m7-delivery-first-20261104-r1/clean-preview/runtime.env -f compose.delivery.yaml -f docs/development/releases/M7-delivery-r3.compose.json up -d --no-build
```

登录及密码复制仍按[原交付报告](M7-delivery-first-r1.md)，不输出密码。新建预览默认r3；目标存在仍拒绝覆盖。应用镜像仅在本机归档，未上传注册表。

## 退出边界

本轮真实provider stream/本地模型推理均0；已授权新Agent仅1名，独立合成库/对象/向量测试实际有读写，不能写作0数据库访问。未改旧Run/lease/slot/gate/proof，未合并main或公开发布。

M6仍5/7，04保持、05/08 open，原168stream/170结果/340判断、两blocked gate、0proof及halt保持。目标Ubuntu实机、真实模型生成/容量、生产备份准入、许可完结和完整阶段/公开发布不在本次通过范围。本次完成限定技术复核后，不再以全量M6复评阻断已授权工程交付。
