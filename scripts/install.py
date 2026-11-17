"""설치 도우미: 설치.bat / 실행.bat 이 부릅니다. (직접 실행: py -3.12 scripts\\install.py)

하는 일: ① 가상환경(.venv) 만들기 ② requirements.txt 의 정해진 버전으로 패키지 설치 ③ 설치 확인
한글 안내는 여기서 출력합니다. (.bat 파일에 한글을 넣으면 Windows 명령 창이 줄을 잘못 읽는 버그가 있어서)
"""
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"
LINE = "=" * 44


def say(msg: str = "") -> None:
    print(msg, flush=True)


def _fail() -> int:
    say()
    say("[오류] 설치 중 문제가 생겼습니다.")
    say("  - 인터넷이 연결되어 있는지 확인하세요. (패키지를 내려받아야 합니다)")
    say("  - 병원 보안 프로그램이 막고 있다면 전산 담당자에게 문의하세요.")
    say("  - 그래도 안 되면 .venv 폴더를 지우고 다시 실행해 보세요.")
    return 1


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # 출력 글자 문제로 멈추지 않게
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    from_run = "--from-run" in sys.argv
    say(LINE)
    say("  경영통계 대시보드 설치 (처음 한 번만)")
    say(LINE)
    say(f"[확인] Python {sys.version.split()[0]}")
    if sys.version_info[:2] != (3, 12):
        say("[주의] Python 3.12 가 아닙니다. 패키지가 설치되지 않을 수 있습니다.")

    if VENV_PY.exists():
        say("[확인] 가상환경 .venv 가 이미 있습니다.")
    else:
        say("[진행] 가상환경 .venv 를 만드는 중")
        try:
            venv.create(VENV_DIR, with_pip=True, clear=True)  # 반쯤 만들어진 .venv 가 있으면 지우고 새로
        except Exception as err:  # 권한·디스크 문제 등
            say(f"  ({type(err).__name__}: {err})")
            return _fail()

    say("[진행] 필요한 패키지를 설치하는 중 (처음에는 몇 분 걸릴 수 있습니다)")
    pip = subprocess.run([str(VENV_PY), "-m", "pip", "install", "--disable-pip-version-check", "-q",
                          "-r", str(ROOT / "requirements.txt")])
    if pip.returncode != 0:
        return _fail()

    check = subprocess.run([str(VENV_PY), "-c", "import streamlit, pandas, plotly, openpyxl"],
                           capture_output=True)
    if check.returncode != 0:
        return _fail()

    say()
    say(LINE)
    say("  설치 완료! 대시보드를 시작합니다." if from_run else '  설치 완료! 이제 "실행.bat" 을 더블클릭하세요.')
    say(LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
