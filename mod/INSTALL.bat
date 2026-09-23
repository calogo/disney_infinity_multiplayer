@echo off
REM Installer for the Disney Infinity 3.0 (PC/Steam) Local Co-op mod.
REM Copy this whole folder's files into the game folder (where DisneyInfinity3.exe is),
REM then run this .bat.
setlocal
cd /d "%~dp0"

if not exist "coop_bink2w32.dll" (
  echo [ERROR] coop_bink2w32.dll not found next to this installer.
  pause & exit /b 1
)
if not exist "bink2w32.dll" (
  echo [ERROR] bink2w32.dll not found. Copy this installer INTO the game folder
  echo         ^(where DisneyInfinity3.exe is^) and run it again.
  pause & exit /b 1
)

if exist "_bink2w32_orig.dll" (
  echo Original already backed up ^(_bink2w32_orig.dll^). Leaving it.
) else (
  ren "bink2w32.dll" "_bink2w32_orig.dll"
  echo Original backed up as _bink2w32_orig.dll
)

copy /Y "coop_bink2w32.dll" "bink2w32.dll" >nul
echo.
echo [OK] Mod installed.
echo Launch the game, enter a Toy Box or a Play Set with 2 controllers,
echo press START on controller 2 to join Player 2.
echo Press LB+RB together on controller 2 to change Player 2's character.
echo To uninstall: run UNINSTALL.bat
pause
