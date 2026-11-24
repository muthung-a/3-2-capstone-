r"""웹판(GitHub Pages) 파일 모으기: 설치 없이 브라우저에서 돌아가는 버전을 _site 폴더에 만듭니다.

웹판은 stlite 를 씁니다. 파이썬이 '접속한 사람의 브라우저 안에서' 돌아가므로,
병원에서 올린 엑셀은 그 PC 밖(GitHub·인터넷 서버)으로 나가지 않습니다.

- 앱 실행에 필요한 파일만 복사합니다. (README·CLAUDE.md·docs·data·.bat 은 올리지 않음)
- files.json: 브라우저가 불러올 파일 목록 (web/index.html 이 읽음)
- GitHub 에 올리면 .github/workflows/pages.yml 이 이 스크립트를 자동으로 실행합니다.

내 PC에서 미리 보기:
  .venv\Scripts\python scripts\build_web.py
  .venv\Scripts\python -m http.server 8000 -d _site    → 브라우저에서 http://localhost:8000
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 앱 실행에 필요한 것: 진입 파일, 설정, 계산(core), 화면(ui), 보고서(reports), 화면 색 설정
SOURCES = ["app.py", "config.py", "core", "ui", "reports", ".streamlit/config.toml"]
SKIP_DIRS = {"__pycache__", "output"}


def url_path(rel: str) -> str:
    """사이트에 올릴 때의 경로. GitHub Pages 배포는 점(.)으로 시작하는 폴더를 빼므로 '.streamlit' → 'streamlit'."""
    return "/".join(part.lstrip(".") for part in rel.split("/"))


def collect(root: Path = ROOT) -> list[str]:
    """복사할 파일들의 상대 경로 (슬래시 '/' 로 구분)."""
    files = []
    for src in SOURCES:
        path = root / src
        if path.is_file():
            files.append(src)
            continue
        for f in sorted(path.rglob("*.py")):
            rel = f.relative_to(root)
            if not SKIP_DIRS.intersection(rel.parts):
                files.append(rel.as_posix())
    return files


def build(out: Path, root: Path = ROOT) -> list[str]:
    """out 폴더를 새로 만들고 웹판 파일을 채웁니다. 복사한 파일 목록을 돌려줍니다."""
    shutil.rmtree(out, ignore_errors=True)  # 미리 보기 중이라 못 지운 폴더는 그대로 두고 덮어씀
    out.mkdir(parents=True, exist_ok=True)
    files = collect(root)
    for rel in files:
        target = out / url_path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / rel, target)
    shutil.copyfile(root / "web" / "index.html", out / "index.html")
    shutil.copyfile(root / "web" / "guide.html", out / "guide.html")  # 사용 설명서 (…/guide.html)
    # {브라우저 안 파이썬에서의 경로: 사이트 주소 경로}
    mapping = {rel: url_path(rel) for rel in files}
    (out / "files.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")  # 밑줄(_)로 시작하는 파일도 그대로 올리기
    return files


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_site"
    copied = build(target)
    print(f"웹판 파일 {len(copied)}개를 {target} 에 만들었습니다.")
