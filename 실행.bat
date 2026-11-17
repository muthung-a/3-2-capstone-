@echo off
rem Start the dashboard. Installs first if needed.
rem Keep this file English/ASCII only: Korean text inside .bat breaks cmd parsing.
cd /d "%~dp0"
title Dashboard
if exist ".venv\Scripts\python.exe" goto run
py -3.12 --version >nul 2>&1
if errorlevel 1 goto nopy
py -3.12 scripts\install.py --from-run
if errorlevel 1 goto stop

:run
echo.
echo Starting the dashboard. A browser window will open soon.
echo To stop the dashboard, close this window.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py

:stop
pause
exit /b

:nopy
echo.
echo [!] Python 3.12 is required.
echo     1. Download Python 3.12 from https://www.python.org/downloads/
echo     2. On the first install screen, check "Add python.exe to PATH".
echo     3. Run this file again.
echo.
pause
exit /b 1
