@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 경영통계 대시보드 설치
echo ============================================
echo   경영통계 대시보드 설치 (처음 한 번만)
echo ============================================
echo.

rem 1) Python 3.12 확인
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [필요] Python 3.12 가 설치되어 있지 않습니다.
    echo.
    echo   1. https://www.python.org/downloads/ 에서 Python 3.12 를 내려받아 설치하세요.
    echo   2. 설치 첫 화면에서 "Add python.exe to PATH" 에 체크하세요.
    echo   3. 설치가 끝나면 이 설치.bat 을 다시 더블클릭하세요.
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('py -3.12 --version') do echo [확인] %%v

rem 2) 가상환경(.venv) 만들기 - 이미 있으면 건너뜀
if exist ".venv\Scripts\python.exe" (
    echo [확인] 가상환경 .venv 가 이미 있습니다.
) else (
    echo [진행] 가상환경 .venv 를 만드는 중...
    py -3.12 -m venv .venv
    if errorlevel 1 goto :fail
)

rem 3) 패키지 설치 (requirements.txt 의 정해진 버전 그대로) - 인터넷이 필요합니다
echo [진행] 필요한 패키지를 설치하는 중... (처음에는 몇 분 걸릴 수 있습니다)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :fail

rem 4) 설치 확인
".venv\Scripts\python.exe" -c "import streamlit, pandas, plotly, openpyxl" >nul 2>&1
if errorlevel 1 goto :fail

echo.
echo ============================================
echo   설치 완료!  이제 "실행.bat" 을 더블클릭하세요.
echo ============================================
pause
exit /b 0

:fail
echo.
echo [오류] 설치 중 문제가 생겼습니다.
echo   - 인터넷이 연결되어 있는지 확인하세요. (패키지를 내려받아야 합니다)
echo   - 병원 보안 프로그램이 막고 있다면 전산 담당자에게 문의하세요.
echo   - 그래도 안 되면 .venv 폴더를 지우고 설치.bat 을 다시 실행해 보세요.
pause
exit /b 1
