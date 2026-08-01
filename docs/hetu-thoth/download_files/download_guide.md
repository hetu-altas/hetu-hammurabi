# PDF 文件下载指南

> 更新日期：2026-05-28 | 模块：`src/download_files/`

---

## 一、研报下载

### 1.1 数据源

| 表 | 字段 | 说明 |
|------|------|------|
| `research_report` | `url` | Tushare 研报下载链接 |
| `research_report` | `report_type` | 行业研报 / 个股研报 |
| `research_report` | `file_locate` | 下载完成后写入的本地路径 |

### 1.2 下载策略

| 研报类型 | 目录结构 | 限速 |
|---------|---------|------|
| 行业研报 | `行业研报/ind_name/inst_csname/YYYYMMDD/文件名.pdf` | 0.1~0.2s/次 |
| 个股研报 | `个股研报/ts_code/inst_csname/YYYYMMDD/文件名.pdf` | 0.1~0.2s/次 |

### 1.3 使用方法

```bash
# 全量下载
bash scripts/download_research_report.sh

# 按日下载
bash scripts/download_research_report.sh -d 20250115

# 按区间下载
bash scripts/download_research_report.sh -s 20250101 -e 20250131
```

---

## 二、上市公司公告下载

### 2.1 数据源

| 表 | 字段 | 说明 |
|------|------|------|
| `anns_d` | `url` | 巨潮公告详情页 URL |
| `anns_d` | `ts_code` | 股票代码 |
| `anns_d` | `ann_date` | 公告日期 |
| `anns_d` | `file_locate` | 下载完成后写入的本地路径 |

### 2.2 下载方案

通过巨潮 API 获取 PDF 真实地址后下载：

| 域名 | 用途 |
|------|------|
| `www.cninfo.com.cn` | POST API 获取 `adjunctUrl` |
| `static.cninfo.com.cn` | PDF 实际下载域名 |

### 2.3 关注板块过滤

`conf/favourite_conf.json` 中配置 13 个行业板块的股票列表，下载范围和转换范围均受限。

### 2.4 使用方法

```bash
# 关注板块 + 2024年起（默认）
bash scripts/download_anns_d_pdf.sh

# 2025年起
bash scripts/download_anns_d_pdf.sh -s 20250101

# 全量日期
bash scripts/download_anns_d_pdf.sh -a
```

### 2.5 数据规模

| 范围 | 记录数 | PDF 大小预估 |
|------|-------|------------|
| 关注板块 2024+ | 452,080 | ~67 GB |
| 关注板块 2025+ | 239,831 | ~36 GB |

---

## 三、国家政策内容抓取

### 3.1 数据源

| 表 | 字段 | 说明 |
|------|------|------|
| `npr` | `url` | gov.cn 政策页面 |
| `npr` | `content_html` | Tushare 返回的截断内容 |
| `npr` | `file_locate` / `attach_locate` | 生成的 Markdown 和附件路径 |

### 3.2 抓取方案

Tushare 的 `content_html` 严重截断（仅 2KB），需从 `url` 抓取完整页面，用 BeautifulSoup 提取正文并转 Markdown。

### 3.3 使用方法

```bash
bash scripts/convert_npr_to_markdown.sh
```

---

## 四、配置

### dir_conf.json

| 键 | 说明 | 示例 |
|------|------|------|
| `file_dir` | 下载根目录 | `/mnt/backup/files` |
| `md_dir` | Markdown 输出根目录 | `/mnt/e/files` |

### favourite_conf.json

```json
{
  "favourite_sectors": {
    "银行": [{"ts_code": "000001.SZ", "name": "平安银行"}],
    ...
  }
}
```

---

## 五、已知问题

| 问题 | 原因 | 解决 |
|------|------|------|
| datacloud 链接 403 | 巨潮旧版数据云接口需认证 | 少量缺失，不影响主力使用 |
| 部分研报 URL 为 `pdf_link` 占位符 | Tushare 未返回真实链接 | 跳过即可 |
