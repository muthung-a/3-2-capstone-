@echo off
rem Setup (first time only). Messages are printed by scripts\install.py.
rem Keep this file English/ASCII only: Korean text inside .bat breaks cmd parsing.
cd /d "%~dp0"
title Dashboard setup
py -3.12 --version >nul 2>&1
if errorlevel 1 goto nopy
py -3.12 scripts\install.py
set RC=%errorlevel%
pause
exit /b %RC%

:nopy
echo.
echo [!] Python 3.12 is required.
echo     1. Download Python 3.12 from https://www.python.org/downloads/
echo     2. On the first install screen, check "Add python.exe to PATH".
echo     3. Run this file again.
echo.
pause
exit /b 1
