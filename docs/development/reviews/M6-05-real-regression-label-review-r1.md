# M6-05：两个 001 候选的独立原件标签审阅 r1

日期：2026-10-30。实际执行者：本次总控独立复核会话，assistant 身份；区别于 12666e5 的候选创建执行。本文件记录实际原件审阅，不是 human 判断、答案评分、数据库 annotation 或整条反馈关闭。

## 被审身份

| 来源反馈 | 不可变候选 ID / SHA | 完整补充映射 SHA |
| --- | --- | --- |
| `c34496c4-c065-5765-93a5-4ba9a9167e55` | `a0f98e3ff68798ca6c36a9a71bd0c367fa00330f6c8a298173608b768e392a15` | `445444bba7d1e559f97a8d92f44a1b8211c65c662d359b055caed22ea5826765` |
| `ff45ecf4-4b82-5f3b-a31d-808ec5ae485e` | `ab753fa532340bef7734801b5be116d220d0ca46052e7c16c2ac53d6a14840d4` | `b2e81e97b67b792607ff854b618d22723a9be275bd75a6bcc96932ce5b9972de` |

完整题目：**根据2014年6W100版手册，LA2608-GM/GU可以与任意品牌无线控制器互通吗？** 两个候选题目/expected/allowed_evidence 内容相同，反馈及其映射身份各自独立。

用于正式 `annotation.review.subject_sha256` 的题目内容 SHA：`70e83b6a1c8c1bdace5c156eaf336b704f19a495a4e7d7056cebfa9831714bea`。按正式校验口径排除 annotation 及 allowed_evidence 内可验证派生的 source_span 后，使用 `validate_dataset.fingerprint()` 计算；候选全文指纹仍按上表不变。不得混用这两种指纹。

## 本次独立读取与结论

直接读取本机原 PDF，重算 SHA：`72983cc9b60f7f165bf89d3f6cbe39d56c4db148fd4b894c70c37378f8be5c8e`。渲染并目视检查封面及物理第 4 页；封面资料版本为 `6W100-20140227`。物理第 4 页（印刷第 1 页）1.1 概述明确：

> H3C LA2608-GM/GU 室内无线网关（以下简称 LA2608）……
>
> 目前，LA2608 只支持与 H3C 公司的无线控制器互通。

**审阅通过：** 题目所限定手册版本下，不能支持“与任意品牌互通”；应回答该版原件只支持与 H3C 无线控制器互通，并保留版本范围。GM/GU 完整写法与简称关系有直接依据。候选 expected 的核心点及 permitted source/page 与原件相符，无需让用户再次查找或判断。

限制：该结论不代表所有现售固件/型号的永久兼容性，不推出 GM/GU 之外任意后缀的等价关系，不据此给旧答案打分或重判图片用途。旧 human 双轮及其低分来源保留原身份。

## 部分反馈映射分别处理

- completed 来源：001 版本内兼容性可由本标签覆盖；原操作性、证据、配图用途/相关性低分仍须对应实际新答案的正式质量链证明，不能因标签审过就关闭整条反馈。
- awaiting_input 来源：001 版本内兼容性及完整 GM/GU 简称关系可覆盖；ZZ/FAKE 和追加斜线属于另行路由回归，不能自动声称已解决，也不能向旧 Run 补造引用。

本轮还通过正式服务的只读 `source()` / `check_evidence()` 重建当前来源：两候选哈希、完整映射哈希、原反馈字节及 Run 来源哈希一致；补充资料 document `d8e7cf8d-7725-56c6-bcd6-8336f4aeec7d`、revision `5d6d6ca5-2ab2-5dea-9fa0-39535c7fe40e` 仍在授权范围且原件 SHA 匹配。当前正式 annotations/bindings/proofs 仍为 0。

## 后续正式消费

本文件提交后可作为 `review.artifact`；artifact_sha256 应按该提交中的 Git blob 字节计算，commit 填实际包含本文件的提交。`method=independent_source_audit`，subject 使用上述固定 SHA。

本文件不预填数据库 reviewer ID，也不创建账号、改角色或以候选作者自签。执行方须将本次真实独立审阅绑定合法授权的实际审核者身份，经正式 `RegressionService.review()` 或对应 API 持久化，再按正式入口派生父版本和绑定；不得把任意新账号名当实际独立性。若候选、来源、映射或题目发生变化，本审阅不可继续沿用。正式 API 记录未产生前，C05 只关闭内容复核子步骤，不能宣称全部完成。

原页渲染、提取文本、完整候选与只读校验日志仅保存在本机 `output/m6-recall-review-20261030/`，不上传 PDF 或原始证据。
