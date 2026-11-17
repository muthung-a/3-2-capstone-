r"""CLAUDE.md 의 규칙을 자동으로 검사하는 테스트.

실행: .venv\Scripts\python -m pytest
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".venv", "__pycache__"}
MAX_LINES = 300


def _project_py_files():
    for path in ROOT.rglob("*.py"):
        if not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            yield path


def _imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def test_core_does_not_import_streamlit():
    for path in [*(ROOT / "core").rglob("*.py"), *(ROOT / "reports").rglob("*.py")]:
        assert "streamlit" not in set(_imported_modules(path)), f"{path.name}: core 에서 streamlit 사용 금지"


def test_no_eval_or_exec():
    for path in _project_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec"}, f"{path.name}:{node.lineno} eval/exec 금지"


def test_files_are_short():
    for path in _project_py_files():
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines <= MAX_LINES, f"{path.name}: {lines}줄 (최대 {MAX_LINES}줄)"


def test_every_page_has_render():
    for path in (ROOT / "ui" / "pages").glob("*.py"):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        assert "render" in names, f"{path.name}: render() 함수가 필요합니다"
