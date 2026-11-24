"""사용 기록(core/audit.py)과 자동 로그아웃·기록 연결 테스트. 파일은 임시 폴더에 만듭니다."""
import time
from datetime import datetime

import pytest
from streamlit.testing.v1 import AppTest

import config
from core import audit, auth


def test_add_and_load_newest_first(tmp_path):
    path = tmp_path / "log.jsonl"
    assert audit.add(path, "kim", "로그인", "사용자", now=datetime(2026, 11, 25, 9, 0))
    assert audit.add(path, "lee", "파일 열기", "a.xlsx", now=datetime(2026, 11, 25, 9, 5))
    rows = audit.load(path)
    assert [r["who"] for r in rows] == ["lee", "kim"]
    assert rows[1] == {"time": "2026-11-25 09:00:00", "who": "kim", "action": "로그인", "detail": "사용자"}
    assert len(audit.load(path, limit=1)) == 1


def test_log_keeps_only_recent_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "MAX_ROWS", 5)
    path = tmp_path / "log.jsonl"
    for i in range(8):
        audit.add(path, f"u{i}", "로그인")
    rows = audit.load(path)
    assert len(rows) == 5 and rows[0]["who"] == "u7" and rows[-1]["who"] == "u3"


def test_broken_lines_are_skipped(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text('{깨진 줄\n{"time": "t", "who": "a", "action": "로그인", "detail": ""}\n[1,2]\n', encoding="utf-8")
    assert [r["who"] for r in audit.load(path)] == ["a"]
    assert audit.load(tmp_path / "없음.jsonl") == []


@pytest.fixture
def files(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ACCOUNTS_PATH", tmp_path / "accounts.json")
    monkeypatch.setattr(config, "AUDIT_PATH", tmp_path / "log.jsonl")
    auth.save(config.ACCOUNTS_PATH, auth.add({}, "nurse", "pass5678", auth.USER))
    return tmp_path


def _app():
    return AppTest.from_file(str(config.BASE_DIR / "app.py"), default_timeout=120)


def test_login_and_failure_are_logged(files):
    at = _app().run()
    at.text_input[0].input("nurse")
    at.text_input[1].input("wrong!!")
    at.button[0].click().run()
    at.text_input[0].input("nurse")
    at.text_input[1].input("pass5678")
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    actions = [(r["who"], r["action"]) for r in audit.load(config.AUDIT_PATH)]
    assert actions[:2] == [("nurse", "로그인"), ("nurse", "로그인 실패")]
    assert "wrong" not in config.AUDIT_PATH.read_text(encoding="utf-8")   # 비밀번호는 기록하지 않음


def test_idle_user_is_logged_out(files):
    at = _app()
    at.session_state["user"] = {"name": "nurse", "role": auth.USER}
    at.session_state["_last_active"] = time.time() - (config.IDLE_LOGOUT_MIN * 60 + 5)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "user" not in at.session_state
    assert any("자동으로 로그아웃" in i.value for i in at.info)
    assert audit.load(config.AUDIT_PATH)[0]["action"] == "자동 로그아웃"


def test_active_user_stays_logged_in(files):
    at = _app()
    at.session_state["user"] = {"name": "nurse", "role": auth.USER}
    at.session_state["_last_active"] = time.time() - 60
    at.run()
    assert at.session_state["user"]["name"] == "nurse"
