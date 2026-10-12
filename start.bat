@echo off
rem Windows: double-click this file to start Marshie.  To pick a mode, use:  start.bat kiosk
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 marshie.py %*
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python marshie.py %*
  ) else (
    echo Python is not installed. Get it from https://www.python.org/downloads/
    echo During setup, tick "Add python.exe to PATH", then double-click this file again.
  )
)
echo.
pause
