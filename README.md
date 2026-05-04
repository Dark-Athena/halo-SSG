# Halo-SSG

将 [Halo](https://halo.run/) 博客生成全静态站点，可部署到 GitHub Pages 作为故障备用。

## 功能

- 通过 Halo 公开 API 获取所有文章元数据
- 抓取渲染后的 HTML 页面，提取文章正文
- 下载所有图片等静态资源到本地，站点完全独立
- URL 路径与原站一致（`/archives/slug`）
- 支持增量同步，仅抓取变更内容
- 生成 RSS feed 和 sitemap
- 纯 HTML/CSS 输出，零 JavaScript 依赖

## 安装

```bash
pip install -e .
```

## 使用

```bash
# 复制并编辑配置文件
cp config.example.yaml config.yaml

# 完整同步（首次运行）
halo-ssg sync --force

# 增量同步（后续运行，仅抓取变更内容）
halo-ssg sync

# 本地预览
halo-ssg serve --port 8000

# 查看同步状态
halo-ssg status
```

## 配置

编辑 `config.yaml`：

```yaml
site:
  base_url: "https://www.darkathena.top"  # 你的 Halo 博客地址
  title: "DA-技术分享"
  description: "Database & Tech Blog"
  author: "DarkAthena"
  language: "zh-CN"

output:
  dir: "./output"
  clean_before_build: true

crawl:
  rate_limit: 2.0    # 请求间隔（秒）
  timeout: 30
  max_retries: 3

assets:
  download_images: true
  max_image_size_mb: 10
```

## 部署到 GitHub Pages

1. 推送代码到 GitHub
2. 在仓库 Settings → Pages 中启用 GitHub Actions 部署
3. 手动触发 Actions workflow `deploy.yml`

可选：配置自定义域名（如 `backup.darkathena.top`），在 `deploy.yml` 中设置 `cname`。

## 项目结构

```
src/halo_ssg/
├── api/halo_client.py       # Halo API 客户端
├── crawler/
│   ├── page_fetcher.py      # 页面抓取（限速、重试）
│   ├── content_extractor.py # HTML 内容提取
│   └── asset_downloader.py  # 图片资源下载
├── builder/
│   ├── site_builder.py      # 构建编排
│   ├── page_generator.py    # 页面生成
│   ├── index_generator.py   # 列表页生成
│   ├── rss_generator.py     # RSS 生成
│   └── sitemap_generator.py # Sitemap 生成
├── templates/               # Jinja2 模板
├── sync/state.py            # 增量同步状态管理
└── cli.py                   # CLI 入口
```

## 同步机制

- 首次运行：全量抓取所有页面和图片
- 后续运行：对比 API 返回的 `lastModifyTime` 与本地状态文件，仅抓取变更内容
- 状态记录在 `state/sync_state.json`

## 依赖

- Python >= 3.10
- httpx、beautifulsoup4、jinja2、click、pyyaml、rich
