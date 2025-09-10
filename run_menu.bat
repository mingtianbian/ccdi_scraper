@echo off
setlocal
set "ROOT=%~dp0"

where powershell >nul 2>nul
if errorlevel 1 (
  echo PowerShell not found. Falling back to ASCII menu.
  call "%ROOT%run_menu_ascii.bat"
  goto :eof
)

REM Use -NoExit so window stays open. Wrap call to show error details on failure.
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -NoExit -Command ^
  "$ErrorActionPreference='Stop'; try { & '%ROOT%run_menu.ps1' } catch { Write-Host 'ERROR: ' $_ -ForegroundColor Red; Read-Host 'Press Enter to exit...' }"

endlocal
