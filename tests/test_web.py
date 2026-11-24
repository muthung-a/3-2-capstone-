"""웹판(GitHub Pages, scripts/build_web.py) 테스트: 필요한 파일은 다 올리고, 올리면 안 되는 파일은 빼는지."""
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_web  # noqa: E402


def test_build_copies_app_files_only(tmp_path):
    out = tmp_path / "site"
    files = build_web.build(out)
    mapping = json.loads((out / "files.json").read_text(encoding="utf-8"))
    assert list(mapping) == files
    assert (out / "index.html").exists() and (out / ".nojekyll").exists()
    for url in mapping.values():
        assert (out / url).exists()
        # GitHub Pages 배포는 점(.)으로 시작하는 폴더·파일을 빼므로 사이트 경로에는 없어야 함
        assert not any(part.startswith(".") for part in url.split("/")), url
    assert mapping[".streamlit/config.toml"] == "streamlit/config.toml"
    assert "app.py" in files and ".streamlit/config.toml" in files
    # 병원 자료·문서·설치 파일·가상데이터는 인터넷 사이트에 올리지 않음
    for rel in files:
        assert not rel.startswith(("data/", "docs/", "tests/", "scripts/")), rel
        assert not rel.endswith((".xlsx", ".xls", ".csv", ".md", ".bat", ".json")), rel


def test_every_imported_project_module_is_included():
    """앱이 import 하는 우리 모듈이 웹판 목록에 빠지면 브라우저에서 ModuleNotFoundError 가 납니다."""
    files = set(build_web.collect())
    for rel in [f for f in files if f.endswith(".py")]:
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in {"core", "ui", "reports"}:
                base = node.module.replace(".", "/")
                for alias in node.names:
                    assert f"{base}/{alias.name}.py" in files or f"{base}.py" in files, f"{rel}: {node.module}.{alias.name}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in {"config", "app"}:
                        assert f"{alias.name}.py" in files, rel


def test_index_html_loads_file_list():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "files.json" in html and 'entrypoint: "app.py"' in html
    assert "@stlite/browser@" in html and "@latest" not in html  # 버전 고정
