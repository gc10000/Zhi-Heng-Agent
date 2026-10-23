# 原课程全部产品资料入库

本轮范围：原课程 `code_PythonProject16/doc` 下的 85 份 PDF 和 1 份 Excel。85 份 PDF 合计 6,253 页，约 423 MB。`设备手册汇总.zip` 中 80 份 PDF 的 SHA-256 均与目录文件相同，无需重复提交。

## 来源与处理原则

- 原件已复制到本项目 `doc/`，逐文件校验 SHA-256；原课程目录不修改。
- 同内容但文件名指向不同产品型号的资料，保留各自的来源与识别结果。
- 课程 `output/` 中的历史上传、解析 ZIP、OCR 中间 PDF、旧图片摘要不作为额外产品文档重复入库。
- Excel 全部非空单元格按工作表、行号及单元格坐标转为 Markdown，保留公式及缓存值（如存在），原工作簿不修改。它属于课程项目计划资料，单独标记来源，避免误写成设备操作说明。
- 厂商手册、生成的 Markdown、图片及运行证据沿用 `.gitignore` 中的 `doc/`、`output/` 规则，不自动提交到 GitHub。

## 全量资料暴露的问题

1. 原切片和产品索引按 `item_name` 删除旧数据，会导致同产品的不同手册相互覆盖。改为按 `file_title` 更新；3 项回归用例覆盖切片更新、缺失来源保护、产品索引更新。
2. 实际 MinerU `vlm` 接口返回单份最多 200 页，超长 PDF 按 150 页拆分，解析后合并正文及图片，再作为一份原始文档导入。
3. 联想海豚手册直接上传被 MinerU 多次拒绝；重写 PDF 结构并按 40 页拆分后成功解析，结果合并为原始来源。
4. 部分视觉摘要会回显 Markdown 图片标签；批处理先清除摘要中的嵌套图片标签，避免生成指向本地的无效图片链接。
5. Windows 会短暂锁住正在读取的 JSON；进度采用临时文件替换并重试。

## 进度与续传

批处理和明细位于本机 `output/course-import/`：

- `manifest.json`：原件名称、SHA-256、页数、准备进度、Markdown 路径。
- `receipts.json`：最终 API 导入任务和状态。
- `documents/`：逐份解析缓存、图片摘要缓存、合并后的文档。
- `run_import.py --prepare-only`：并行解析、生成图片摘要、上传 MinIO。
- `import_ready.py`：逐份消费已准备 Markdown，经现有 API 完成主体识别、切片、BGE 向量与 Milvus 入库。

准备完成不等于入库成功。最终以回执、Milvus 中逐来源的切片检查和真实问答验收为准。失败任务保留单独的错误文件，重试优先复用解析和图片摘要，减少重复调用。

## 最终结果（2026-10-21）

**86/86 份资料完成入库，逐来源核验全部通过，没有缺少必填配置的项目。**

| 核对项 | 结果 |
| --- | --- |
| 原始资料 | 85 份 PDF（6,253 页）+ 1 份 Excel |
| API 任务回执 | 86 份均 completed |
| 来源覆盖 | 86 份均同时具备正文切片和产品索引 |
| 本批正文切片 | 6,612 条 |
| 本批产品索引 | 86 条（按文档存储，部分产品存在多份手册） |
| 全库切片 / 索引 | 6,616 / 87，另含之前的 H3C 节选联调样本 |
| 原件 MinIO 检查 | 86/86 均存在，大小与原件一致 |
| 全库 Markdown 图片链接 | 9,842/9,842 实际 HTTP 读取成功且为图片类型 |
| 原件副本 | `doc/` 中全部 SHA-256 与原课程一致 |
| 防覆盖回归 | 3 项通过 |

MinerU 等待时间较长的分段使用本地补齐：`hl3070使用说明书.pdf` 第 151—205 页、`LJ2680DN用户手册.pdf` 第 151—241 页、`M3070系列用户手册.pdf` 第 601—630 页，共 176 页。保留原生中文正文，并以整页图片保留矢量图、表格与版式，再走视觉摘要及 MinIO 上传。其他页复用成功的 MinerU 结果。本地补齐不等同于 MinerU 结构化解析，表格和阅读顺序仍可能存在差异；本轮未逐页人工审核 6,253 页。

真实问答回归中，H3C LA2608 返回 `display wlan ap` 与 `R/M` 状态及引用；新入库的联想 LJ2268/LJ2268W 返回维护相关手册内容及有效切片引用；最后入库的至像 M3070 返回 PC-FAX 接收设置步骤、有效切片引用和配图。全量入库的覆盖验证不代表对所有型号的问答质量评测已完成。

完整证据在 `output/course-import/index-verification.json`、`storage-verification.json`、`receipts.json`、`native-segments.json` 和 `query-*.json`。原件、派生内容和凭据不自动纳入公开源码。

## 本机 GPU 环境

本机 NVIDIA RTX 4050 Laptop GPU，6 GB 显存。全量导入将环境切换为 `torch==2.10.0+cu128`、`torchvision==0.25.0+cu128`、`torchaudio==2.10.0+cu128`；已确认 CUDA 可用。

本机 `.env` 的 `BGE_DEVICE=cuda:0`、`BGE_FP16=1` 已保存，重排器保持 CPU。BGE 模型、1024 维向量与检索参数沿用原配置；半精度可能带来微小数值差异。安装 CUDA 轮子没有修改 API 密钥。

若重新创建环境或执行依赖同步后恢复为 CPU 轮子，需要重新安装：

```powershell
# 先退出使用当前虚拟环境的 Python 服务，避免 Windows 文件锁。
& "$env:USERPROFILE/.local/bin/uv.exe" pip install --python .venv/Scripts/python.exe torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 --index-url https://download.pytorch.org/whl/cu128 --no-deps
```

可用 `.venv/Scripts/python.exe -c "import torch; print(torch.cuda.is_available())"` 核对。无显卡设备使用原 CPU 方案，并将 BGE 设备改回 `cpu`、FP16 改回 `0`。

本轮结束时导入 API 监听 127.0.0.1:8002（PID 35348），问答 API 监听 127.0.0.1:8001（PID 42284），四个 Docker 服务健康。进程号随重启变化。批量准备与消费任务均已结束，服务保留运行。
