# PDF → Markdown 转换指南

> 更新日期：2026-05-28 | 模块：`src/convert2md/`、`src/utils/util_pdf_to_markdown.py`

---

## 一、技术方案

基于 [Mineru](https://github.com/opendatalab/MinerU) 3.1 pipeline 原生 API，将 PDF 转为结构化 Markdown。

### 1.1 两种模式

| 模式 | 脚本后缀 | 并发 | 适用场景 |
|------|---------|------|---------|
| CPU | `*_to_md.py` | 单进程 | 无 GPU 环境 |
| GPU | `*_to_md_gpu.py` | 单进程串行 | 有 CUDA 显卡 |

> **GPU 模式已改为串行**（2026-06-01）。此前多进程并行方案因 mineru ONNX OCR 引擎不支持多进程 GPU 访问，`OCR-det` 步骤频繁死锁。实测 4080S 单进程串行 105 秒跑完 40 份（2.6 秒/份），反比多进程快 10 倍且无卡死。

### 1.2 核心参数

| 参数 | 值 | 说明 |
|------|------|------|
| `backend` | `pipeline` | 模型驱动解析 |
| `parse_method` | `txt` | 提取内嵌文字，不走 OCR |
| `table_enable` | `True` | 保留表格识别 |
| `formula_enable` | `False` | 不要公式识别 |
| `image_analysis` | `False` | 关闭公章识别（避免 GPU 卡死） |

---

## 二、行业研报

### 2.1 脚本

| 文件 | 模式 |
|------|------|
| `src/convert2md/convert_industry_report_to_md.py` | CPU |
| `src/convert2md/convert_industry_report_to_md_gpu.py` | GPU |
| `scripts/convert_industry_report_to_md.sh` | CPU Shell |
| `scripts/convert_industry_report_to_md_gpu.sh` | GPU Shell |

### 2.2 使用方法

```bash
# CPU（默认 2024 年起）
bash scripts/convert_industry_report_to_md.sh 2025-01-01

# GPU（2025 年起）
bash scripts/convert_industry_report_to_md_gpu.sh 2025-01-01
```

### 2.3 数据规模

| 范围 | 记录数 | CPU 预估 | GPU 预估 |
|------|-------|---------|---------|
| 2024+ | 48,275 | ~100 天 | ~36 小时 |
| 2025+ | 27,223 | ~30 天 | ~20 小时 |

### 2.4 输出结构

```
/mnt/e/files/行业研报/银行/民生证券/20240101/
├── H3_xxx.pdf              # 原始 PDF
├── H3_xxx.md               # 生成的 Markdown
└── images/                 # 正文图片（仅被引用的保留）
```

---

## 三、个股研报

### 3.1 脚本

| 文件 | 模式 |
|------|------|
| `src/convert2md/convert_stock_report_to_md.py` | CPU |
| `src/convert2md/convert_stock_report_to_md_gpu.py` | GPU |
| `scripts/convert_stock_report_to_md.sh` | CPU Shell |
| `scripts/convert_stock_report_to_md_gpu.sh` | GPU Shell |

### 3.2 使用方法

```bash
# CPU
bash scripts/convert_stock_report_to_md.sh 2025-01-01

# GPU
bash scripts/convert_stock_report_to_md_gpu.sh 2025-01-01
```

### 3.3 数据规模

| 范围 | 记录数（关注板块） | CPU 预估 | GPU 预估 |
|------|-----------------|---------|---------|
| 2024+ | 7,970 | ~4 天 | ~6 小时 |
| 2025+ | 3,690 | ~2 天 | ~3 小时 |

### 3.4 输出结构

```
/mnt/e/files/个股研报/000001.SZ/中信证券/20250115/
├── H3_xxx.pdf
├── H3_xxx.md
└── images/
```

---

## 四、上市公司公告

### 4.1 脚本

| 文件 | 模式 |
|------|------|
| `src/convert2md/convert_anns_d_to_md.py` | CPU |
| `src/convert2md/convert_anns_d_to_md_gpu.py` | GPU |
| `scripts/convert_anns_d_to_md.sh` | CPU Shell |
| `scripts/convert_anns_d_to_md_gpu.sh` | GPU Shell |

### 4.2 使用方法

```bash
# CPU
bash scripts/convert_anns_d_to_md.sh 2025-01-01

# GPU
bash scripts/convert_anns_d_to_md_gpu.sh 2025-01-01
```

### 4.3 数据规模

| 范围 | 记录数 | CPU 预估 | GPU 预估 |
|------|-------|---------|---------|
| 2024+ | 450,886 | ~80 天 | ~13 天 |
| 2025+ | 239,010 | ~45 天 | ~7 天 |

> 公告包含少量长文档（年报 ~150 页），占比 <5%，整体平均 11 页。

### 4.4 输出结构

```
/mnt/e/files/上市公司公告/600036.SH/202503/
├── 招商银行xxx.pdf
└── 招商银行xxx.md           # 仅 Markdown，不保留图片
```

---

## 五、断点续跑

所有脚本支持中断后继续：

1. `md_locate` 已写入 DB 的记录不再查询
2. MD 文件已存在的跳过下载
3. Ctrl+C 后 GPU 进程组自动清理

```bash
# 被中断后直接重跑
bash scripts/convert_stock_report_to_md_gpu.sh 2025-01-01 10
```

---

## 六、GPU 注意事项

| 问题 | 原因 | 解决 |
|------|------|------|
| `OCR-det ch` 冻结 | ONNX OCR 引擎不支持多进程 GPU 访问 | 已改为串行模式，彻底消除 |
| 多进程显存泄漏 | mineru 内部 spawn 孤儿进程 | 已无用（不再 spawn 子进程） |
| 显存不足 | — | 串行模式单文件用 ~2GB，无瓶颈 |

> **性能实测**（4080S 16GB）：串行 105 秒 / 40 份个股研报 = **2.6 秒/份**。单文件 mineru 内部 batch_ratio=8 自动吃满 GPU，外部多进程反而抢资源。

---

## 七、单文件转换

```bash
# 测试用
bash scripts/convert_pdf_to_md.sh /path/to/file.pdf -o /output/dir
```

---

## 八、清理未引用图片

```bash
bash scripts/clean_images.sh /mnt/e/files/个股研报
```
