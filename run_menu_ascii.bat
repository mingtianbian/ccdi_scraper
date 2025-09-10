@echo off
setlocal enabledelayedexpansion

REM Simple ASCII-only launcher to avoid garbled text in cmd.
REM Place this file in the same folder as scraper.py.

REM Prefer py -3 if available, else python
set "PY=python"
py -3 -V >nul 2>nul && set "PY=py -3"

set "ROOT=%~dp0"
set "SCRIPT=%ROOT%scraper.py"
set "REQ=%ROOT%requirements.txt"
set "EXPORT_DIR=%ROOT%export"

if not exist "%SCRIPT%" (
  echo ERROR: scraper.py not found next to this .bat
  pause
  exit /b 1
)

:menu
cls
echo ================= CCDI SCRAPER ================
echo 1) Run crawl (all categories, max 200 pages)
echo 2) Install/Update env (pip install -r requirements.txt)
echo 3) Export CSV
echo 4) Export XLSX
echo 5) Run only one category
echo 6) Reparse a single detail URL
echo 7) Open export folder
echo 0) Exit
echo ==============================================
set /p choice=Enter choice: 

if "%choice%"=="1" goto run_all
if "%choice%"=="2" goto install
if "%choice%"=="3" goto export_csv
if "%choice%"=="4" goto export_xlsx
if "%choice%"=="5" goto run_only
if "%choice%"=="6" goto reparse
if "%choice%"=="7" goto open_export
if "%choice%"=="0" goto end
goto menu

:run_all
%PY% "%SCRIPT%" run --max-pages 200
pause
goto menu

:install
%PY% -m pip install -r "%REQ%"
pause
goto menu

:export_csv
%PY% "%SCRIPT%" export --format csv
pause
goto menu

:export_xlsx
%PY% "%SCRIPT%" export --format xlsx
pause
goto menu

:run_only
set /p onlycat=Enter category label (e.g. Shengguan Ganbu^>Zhiji Shencha): 
%PY% "%SCRIPT%" run --max-pages 200 --only "%onlycat%"
pause
goto menu

:reparse
set /p theurl=Paste detail URL: 
%PY% "%SCRIPT%" reparse --url "%theurl%"
pause
goto menu

:open_export
if not exist "%EXPORT_DIR%" mkdir "%EXPORT_DIR%"
start "" "%EXPORT_DIR%"
goto menu

:end
exit /b 0
