"""로그인 계정(core/auth.py)과 로그인 화면(ui/login.py) 테스트. 계정 파일은 임시 폴더에 만듭니다."""
import json

import pytest
from streamlit.testing.v1 import AppTest

import config
from core import auth


def test_password_is_hashed_and_verified(tmp_path):
    users = auth.add({}, "관리자1", "secret123", auth.ADMIN)
    path = tmp_path / "accounts.json"
    assert auth.save(path, users)
    text = path.read_text(encoding="utf-8")
    assert "secret123" not in text                      # 비밀번호 원문은 저장하지 않음
    loaded = auth.load(path)
    assert auth.verify(loaded, "관리자1", "secret123") == auth.ADMIN
    assert auth.verify(loaded, "관리자1", "wrong-pw") is None
    assert auth.verify(loaded, "없는사람", "secret123") is None


def test_browser_hash_matches_standard():
    """웹판용 직접 계산이 표준 함수와 같은 값을 내야 PC판·웹판 계정이 같은 방식이 됩니다."""
    import hashlib
    for pw, salt in [(b"secret123", b"0123456789abcdef"), ("한글비번".encode(), b"salt"), (b"x" * 100, b"s")]:
        assert auth._pbkdf2_sha256(pw, salt, 1000) == hashlib.pbkdf2_hmac("sha256", pw, salt, 1000)


def test_same_password_gets_different_hash():
    users = auth.add(auth.add({}, "a1", "same-pw", auth.USER), "b1", "same-pw", auth.USER)
    assert users["a1"]["hash"] != users["b1"]["hash"]   # 사람마다 소금값이 달라서


def test_new_account_rules():
    users = auth.add({}, "kim", "123456", auth.USER)
    assert auth.check_new(users, "kim", "abcdef", "abcdef")          # 같은 아이디
    assert auth.check_new(users, "x", "abcdef", "abcdef")            # 너무 짧은 아이디
    assert auth.check_new(users, "lee", "123", "123")                # 짧은 비밀번호
    assert auth.check_new(users, "lee", "abcdef", "abcdeg")          # 확인 불일치
    assert auth.check_new(users, "이간호사", "abcdef", "abcdef") is None


def test_last_admin_cannot_be_removed():
    users = auth.add(auth.add({}, "boss", "123456", auth.ADMIN), "staff", "123456", auth.USER)
    with pytest.raises(ValueError):
        auth.remove(users, "boss")
    assert "staff" not in auth.remove(users, "staff")
    two = auth.add(users, "boss2", "123456", auth.ADMIN)
    assert "boss" not in auth.remove(two, "boss")


def test_set_password_keeps_role():
    users = auth.set_password(auth.add({}, "kim", "old-pw1", auth.USER), "kim", "new-pw1")
    assert auth.verify(users, "kim", "new-pw1") == auth.USER
    assert auth.verify(users, "kim", "old-pw1") is None


def test_broken_file_is_empty(tmp_path):
    path = tmp_path / "accounts.json"
    path.write_text("{깨진 파일", encoding="utf-8")
    assert auth.load(path) == {}
    path.write_text(json.dumps({"users": {"x": {"role": "god", "salt": "00", "hash": "00"}}}), encoding="utf-8")
    assert auth.load(path) == {}                         # 알 수 없는 역할은 무시


@pytest.fixture
def accounts_file(tmp_path, monkeypatch):
    path = tmp_path / "accounts.json"
    monkeypatch.setattr(config, "ACCOUNTS_PATH", path)
    return path


def _app():
    return AppTest.from_file(str(config.BASE_DIR / "app.py"), default_timeout=120)


def test_first_run_creates_admin(accounts_file):
    at = _app().run()
    assert not at.exception
    assert any("관리자 계정 만들기" in m.value for m in at.markdown)
    assert len(at.get("file_uploader")) == 0              # 로그인 전에는 파일을 올릴 수 없음
    at.text_input[0].input("원장")
    at.text_input[1].input("pass1234")
    at.text_input[2].input("pass1234")
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert auth.verify(auth.load(accounts_file), "원장", "pass1234") == auth.ADMIN
    assert len(at.get("file_uploader")) == 1             # 로그인 후 파일 올리기 칸이 보임


def test_login_and_roles(accounts_file):
    users = auth.add(auth.add({}, "boss", "pass1234", auth.ADMIN), "nurse", "pass5678", auth.USER)
    auth.save(accounts_file, users)
    at = _app().run()
    at.text_input[0].input("nurse")
    at.text_input[1].input("wrong!!")
    at.button[0].click().run()
    assert any("맞지 않습니다" in e.value for e in at.error)
    at.text_input[0].input("nurse")
    at.text_input[1].input("pass5678")
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["user"] == {"name": "nurse", "role": auth.USER}
    labels = [b.label for b in at.sidebar.button]
    assert "👥 계정 관리" not in labels and "로그아웃" in labels   # 사용자에게는 계정 관리 없음


def test_admin_sees_account_button(accounts_file):
    auth.save(accounts_file, auth.add({}, "boss", "pass1234", auth.ADMIN))
    at = _app()
    at.session_state["user"] = {"name": "boss", "role": auth.ADMIN}
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "👥 계정 관리" in [b.label for b in at.sidebar.button]
    assert any("엑셀 파일을 올려" in i.value for i in at.info)
