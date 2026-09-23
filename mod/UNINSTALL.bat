@echo off
REM Uninstaller: restores the original bink2w32.dll.
setlocal
cd /d "%~dp0"

if not exist "_bink2w32_orig.dll" (
  echo No backup ^(_bink2w32_orig.dll^) found. The mod may not be installed.
  pause & exit /b 1
)

if exist "bink2w32.dll" del /Q "bink2w32.dll"
ren "_bink2w32_orig.dll" "bink2w32.dll"
echo [OK] Original restored. Mod uninstalled.
pause
