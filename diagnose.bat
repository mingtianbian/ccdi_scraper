@echo off
setlocal
set "ROOT=%~dp0"
echo Running diagnostic mode...
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Continue'; & '%ROOT%run_menu.ps1'; Read-Host 'Press Enter to exit...'"
endlocal
