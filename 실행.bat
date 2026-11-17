@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [오류] .venv 가상환경이 없습니다. README.md 의 "처음 한 번만 할 일"을 따라 하세요.
    pause
    exit /b 1
)
echo 경영통계 대시보드를 시작합니다... (이 창을 닫으면 종료)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
