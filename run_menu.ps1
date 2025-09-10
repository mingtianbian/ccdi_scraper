# -*- coding: utf-8 -*-
# Top-level trap to prevent flash-close on errors
trap {
    Write-Host ("FATAL: {0}" -f $_.Exception.Message) -ForegroundColor Red
    if ($_.InvocationInfo -and $_.InvocationInfo.PositionMessage) {
        Write-Host $_.InvocationInfo.PositionMessage -ForegroundColor DarkRed
    }
    [void](Read-Host "Press Enter to exit...")
    break
}

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $root 'config.json'
$script = Join-Path $root 'scraper.py'
$req = Join-Path $root 'requirements.txt'
$exportDir = Join-Path $root 'export'

function Load-Config {
    if (Test-Path $configPath) {
        try { return Get-Content $configPath -Raw | ConvertFrom-Json } catch { return @{ lang = "zh" } }
    } else { return @{ lang = "zh" } }
}
function Save-Config($cfg) { ($cfg | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 $configPath }
$CFG = Load-Config
if (-not $CFG.lang) { $CFG.lang = "zh" }

$L = @{
  zh = @{
    title = "CCDI 抓取器 - 菜单";
    run_all = "1) 开始抓取(全部分类, 最多 200 页/类)";
    install = "2) 安装/更新运行环境(pip install -r requirements.txt)";
    exp_csv = "3) 导出 CSV";
    exp_xlsx = "4) 导出 Excel(.xlsx)";
    run_only = "5) 仅抓取某一分类";
    reparse = "6) 调试解析单个详情页";
    open_export = "7) 打开导出目录";
    lang = "8) 切换语言(当前: 中文)";
    exit = "0) 退出";
    prompt = "请选择";
    enter_cat = "请输入分类名称(例如: 省管干部>执纪审查): ";
    enter_url = "粘贴详情页 URL: ";
    missing = "错误: 找不到 scraper.py, 请确认脚本与本菜单在同一目录。";
    anykey = "请输入回车返回菜单...";
    installing = "正在安装/更新依赖...";
    running = "开始抓取...";
    csv_done = "CSV 导出完成。";
    xlsx_done = "XLSX 导出完成。";
    switched = "语言已切换为: 中文";
    open_export_msg = "正在打开导出目录...";
    select_cat = "请选择一个分类 (请输入 1-6，或 0 返回菜单):";
  };
  en = @{
    title = "CCDI Scraper - Menu";
    run_all = "1) Run crawl (all categories, max 200 pages)";
    install = "2) Install/Update env (pip install -r requirements.txt)";
    exp_csv = "3) Export CSV";
    exp_xlsx = "4) Export XLSX";
    run_only = "5) Run only one category";
    reparse = "6) Reparse a single detail URL";
    open_export = "7) Open export folder";
    lang = "8) Switch language (current: English)";
    exit = "0) Exit";
    prompt = "Enter choice";
    enter_cat = "Enter category label (e.g., 省管干部>执纪审查): ";
    enter_url = "Paste detail URL: ";
    missing = "ERROR: scraper.py not found next to this menu.";
    anykey = "Press Enter to return to menu...";
    installing = "Installing/updating requirements...";
    running = "Starting crawl...";
    csv_done = "CSV export done.";
    xlsx_done = "XLSX export done.";
    switched = "Language switched to: English";
    open_export_msg = "Opening export folder...";
    select_cat = "Select a category (enter 0 to return):";
  };
}
function T($k) { $lang = $CFG.lang; if (-not $L.ContainsKey($lang)) { $lang = "zh" }; return $L[$lang][$k] }
function PyCmd { if (Get-Command py -ErrorAction SilentlyContinue) { 'py -3' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { $null } }
function Pause-Menu { [void](Read-Host (T 'anykey')) }

if (-not (Test-Path $script)) { Write-Host (T 'missing') -ForegroundColor Red; Pause-Menu; exit 1 }
if (-not (Test-Path $exportDir)) { New-Item -ItemType Directory -Path $exportDir | Out-Null }

while ($true) {
  Clear-Host
  Write-Host ("==== {0} ====" -f (T 'title'))
  Write-Host (T 'run_all')
  Write-Host (T 'install')
  Write-Host (T 'exp_csv')
  Write-Host (T 'exp_xlsx')
  Write-Host (T 'run_only')
  Write-Host (T 'reparse')
  Write-Host (T 'open_export')
  Write-Host (T 'lang')
  Write-Host (T 'exit')
  $choice = Read-Host (T 'prompt')

  switch ($choice) {
    '1' { Write-Host (T 'running'); iex "$(PyCmd) `"$script`" run --max-pages 200"; Pause-Menu }
    '2' { Write-Host (T 'installing'); iex "$(PyCmd) -m pip install -r `"$req`""; Pause-Menu }
    '3' { iex "$(PyCmd) `"$script`" export --format csv"; Write-Host (T 'csv_done'); Pause-Menu }
    '4' { iex "$(PyCmd) `"$script`" export --format xlsx"; Write-Host (T 'xlsx_done'); Pause-Menu }
    '5' {
      while ($true) {
        Write-Host (T 'select_cat')
        iex "$(PyCmd) `"$script`" list"
        $cid = Read-Host "请输入 1-6 / 0"
        if ($cid -eq '0') { break }
        if ($cid -match '^[1-6]$') {
          iex "$(PyCmd) `"$script`" run --max-pages 200 --only-id $cid"
          break
        }
      }
      Pause-Menu
    }
    '6' { $url = Read-Host (T 'enter_url'); iex "$(PyCmd) `"$script`" reparse --url `"$url`""; Pause-Menu }
    '7' { Write-Host (T 'open_export_msg'); ii $exportDir }
    '8' { if ($CFG.lang -eq "zh") { $CFG.lang = "en" } else { $CFG.lang = "zh" }; Save-Config $CFG; Write-Host (T 'switched'); Start-Sleep -Milliseconds 700 }
    '0' { break }
    default { }
  }
}
Pause-Menu
