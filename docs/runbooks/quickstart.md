> 已有2026-11-04候选现为r3。旧`output/m7-delivery-first-20261104-r1/clean-preview/runtime.env`保持原tag，必须用下列精确覆盖恢复，不能对该旧配置裸执行通用up：
>
> ```powershell
> docker compose --env-file output/m7-delivery-first-20261104-r1/clean-preview/runtime.env -f compose.delivery.yaml -f docs/development/releases/M7-delivery-r3.compose.json up -d --no-build
> ```
>
> 入口仍为http://127.0.0.1:18080；[补修报告](../development/reviews/M7-candidate-review-repair-r1.md)说明身份与限制。以下通用创建/启动步骤用于本版脚本新建的默认r3预览。

# 知衡内部预览快速开始

范围是本机隔离交付候选：登录、资料、受控原件、合成工程流程及持久恢复。真实生成明确关闭；不把合成向量/答案fixture或待审反馈当M6质量证据。不会启动旧批、读取private-identity或覆盖旧Compose。

Windows从开发工作树执行（主仓库Python保留原CUDA环境）：

```powershell
$env:PYTHONUTF8='1'
$py='D:/Desktop/AnXin/ansen_code/Product-Knowledge-Rag/.venv/Scripts/python.exe'
& $py -m scripts.operations.runtime_resources
if ($LASTEXITCODE -ne 0) { throw '宿主/daemon资源不足或状态未知，拒绝创建预览' }
& $py scripts/operations/preview.py create
```

`preview create`自身会在写配置前和镜像构建后各执行只读资源门禁；上面的先行命令仅打印一次资源快照。门禁要求Windows可用物理内存至少2GiB、daemon总内存扣除全部运行容器当前RSS至少3GiB；格式未知、daemon超时或stats缺行均拒绝。该快照不证明持续容量，compose可能启动后变化。拒绝时不创建配置、不停其他项目、不清理卷或日志。

脚本生成`output/local-preview/runtime.env`及`preview.json`，随机数据库/桶/集合/队列、独立卷和空闲回环端口；固定镜像构建后等待存储并用现有解析/索引/发布接口登记自制样例。目录已存在时拒绝覆盖，保留失败；新试验显式使用`--output output/local-preview-r2`。已有候选镜像可加`--no-build`，这只证明新数据卷复现，不能称再次重建。

入口由preview.json给出，首选`http://127.0.0.1:18080`，占用时自动另选。用户名`preview_admin`，随机密码仅在本地私有文件；Windows可复制而不打印：

```powershell
& $py scripts/operations/preview.py copy-password --env-file output/local-preview/runtime.env
& $py scripts/verification/check_readiness.py --url http://127.0.0.1:18080
```

密码不要粘贴到共享日志。新环境端口以脚本实际输出为准。若需要本轮已经启动的环境，使用[候选报告](../development/reviews/M7-delivery-first-r1.md)中的明确入口与环境文件，无需重新生成。

```powershell
& $py scripts/operations/preview.py status --env-file output/local-preview/runtime.env
docker compose --env-file output/local-preview/runtime.env -f compose.delivery.yaml stop
docker compose --env-file output/local-preview/runtime.env -f compose.delivery.yaml up -d
```

`stop/up`保留卷；禁止`down -v`、清理旧卷或复用真实运行账本。关闭本轮预览不会修改旧compose服务。MinIO/模型缺项要按ready分类处理，不能改为成功或临时调用模型绕过。无模型宿主时上传可保存原件，后续索引任务明确失败，不把任务完成冒充发布。

需要可重复工程流程时，另用`scripts/verification/load_support.py --env-file <本轮host.env> --base-url <实际入口> --output <新私有目录>`。host.env只将runtime中的容器DNS改为该预览的回环发布端口，不从真实.env抄凭据；脚本明确写工程合成fixture，不能作为真实模型演示。正式新生成须另行形成具体身份/预算授权。

Linux命令入口为Python3.12（或Compose容器内`python -m scripts.operations.bootstrap_preview`）；Windows GPU依赖安装及设备可见性已验证，目标Ubuntu实测未完成，详见[部署](ubuntu-deploy.md)。

## 当前operational-r1只读入口

本轮新增入口http://127.0.0.1:61587，generation=false。由于来源临发首失败，8槽已halt、provider0；只读资料链浏览器通过，真实生成没有答案。精确镜像覆盖/已有私有runtime及仅启动api/web的命令见[执行报告](../development/reviews/M7-operational-closure-r1.md)。不要裸up整个新项目开启idle消费者，也不要使用从未部署过的generation版env。原18080仍用原r3覆盖。Docker/WSL后续间歇失败，入口是否在线需health实际核，不能保证持续可用。
