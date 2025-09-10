# CCDI 六分类抓取器

功能：
- 抓取以下 6 个栏目，自动翻页直到无数据：
  - 中管干部 > 执纪审查（/scdcn/zggb/zjsc/）
  - 中管干部 > 党纪政务处分（/scdcn/zggb/djcf/）
  - 中央一级党和国家机关、国企和金融单位干部 > 执纪审查（/scdcn/zyyj/zjsc/）
  - 中央一级党和国家机关、国企和金融单位干部 > 党纪政务处分（/scdcn/zyyj/djcf/）
  - 省管干部 > 执纪审查（/scdcn/sggb/zjsc/）
  - 省管干部 > 党纪政务处分（/scdcn/sggb/djcf/）
- 解析详情页，自动提取：标题、发布时间、姓名（启发式）、地区（省级启发式）、正文文本
- SQLite 增量存储，支持断点续抓 & 内容更新（通过 MD5 判定）
- 导出 CSV / Excel 表格

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法
1) 运行抓取：
```bash
python scraper.py run --max-pages 200
```
> `--max-pages` 为每个栏目最大翻页数，上限越大抓得越深。程序会在遇到“无更多内容”时自动停止。

2) 导出数据：
```bash
python scraper.py export --format csv   # 导出 CSV
python scraper.py export --format xlsx  # 或导出 Excel
```

3) 单条页面调试：
```bash
python scraper.py reparse --url 'https://www.ccdi.gov.cn/scdcn/.../xxxx.html'
```

## 结果位置
- 数据库：`ccdi.sqlite3`
- 导出文件：`export/ccdi_YYYYMMDD_HHMMSS.csv|xlsx`

## 提示
- 网站结构可能有细微差异，已做容错；若个别栏目结构变化，可再定制列表选择器和详情选择器。
- 姓名与地区为启发式抽取，建议后续再加规则表或词典提升准确率。
- 如遇访问过于频繁被限流，可适当增大 `time.sleep` 的间隔，或加入代理池。
