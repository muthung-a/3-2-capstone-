"""로그인 계정: 관리자·사용자 계정 만들기, 비밀번호 확인, 삭제.

- 계정 파일(accounts.json)은 이 PC에만 저장합니다. (웹판은 그 PC 브라우저 저장소)
- 비밀번호는 그대로 저장하지 않고 PBKDF2-SHA256 해시(소금값 포함)로만 저장합니다.
- 역할: "admin"(관리자) = 계정 관리·환경설정 변경 / "user"(사용자) = 보기·보고서 받기
"""
import hashlib
import hmac
import json
import os
import re
from pathlib import Path

ADMIN, USER = "admin", "user"
ROLE_NAMES = {ADMIN: "관리자", USER: "사용자"}
ITERATIONS = 60_000
MIN_PASSWORD = 6
_NAME_RULE = re.compile(r"^[0-9A-Za-z가-힣_.-]{2,20}$")


_IPAD, _OPAD = bytes(x ^ 0x36 for x in range(256)), bytes(x ^ 0x5C for x in range(256))


def _pbkdf2_sha256(password: bytes, salt: bytes, iterations: int) -> bytes:
    """hashlib.pbkdf2_hmac('sha256', …) 와 같은 결과 (32바이트).

    웹판(브라우저 안 파이썬)에는 hashlib.pbkdf2_hmac 이 없어서 표준(RFC 8018) 그대로 직접 계산합니다.
    """
    key = hashlib.sha256(password).digest() if len(password) > 64 else password
    key = key.ljust(64, b"\0")
    inner, outer = hashlib.sha256(key.translate(_IPAD)), hashlib.sha256(key.translate(_OPAD))

    def prf(msg: bytes) -> bytes:
        i, o = inner.copy(), outer.copy()
        i.update(msg)
        o.update(i.digest())
        return o.digest()

    u = prf(salt + b"\x00\x00\x00\x01")
    total = int.from_bytes(u, "big")
    for _ in range(iterations - 1):
        u = prf(u)
        total ^= int.from_bytes(u, "big")
    return total.to_bytes(32, "big")


def _hash(password: str, salt: bytes, iterations: int) -> str:
    data = password.encode("utf-8")
    if hasattr(hashlib, "pbkdf2_hmac"):
        return hashlib.pbkdf2_hmac("sha256", data, salt, iterations).hex()
    return _pbkdf2_sha256(data, salt, iterations).hex()


def load(path: str | Path) -> dict:
    """계정 목록 {아이디: {role, salt, hash, iter}}. 파일이 없거나 깨졌으면 빈 목록."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    users = data.get("users") if isinstance(data, dict) else None
    if not isinstance(users, dict):
        return {}
    return {name: u for name, u in users.items()
            if isinstance(u, dict) and u.get("role") in ROLE_NAMES and u.get("salt") and u.get("hash")}


def save(path: str | Path, users: dict) -> bool:
    """계정 목록을 저장합니다. 성공하면 True."""
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({"users": users}, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def check_new(users: dict, name: str, password: str, password2: str) -> str | None:
    """새 계정 입력이 올바른지 확인합니다. 문제가 있으면 안내 문구, 없으면 None."""
    if not _NAME_RULE.match(name or ""):
        return "아이디는 2~20자의 한글·영문·숫자(_ . - 가능)로 입력하세요."
    if name in users:
        return f"'{name}'은(는) 이미 있는 아이디입니다."
    return check_password(password, password2)


def check_password(password: str, password2: str) -> str | None:
    """비밀번호 규칙 확인. 문제가 있으면 안내 문구, 없으면 None."""
    if len(password or "") < MIN_PASSWORD:
        return f"비밀번호는 {MIN_PASSWORD}자 이상으로 입력하세요."
    if password != password2:
        return "비밀번호 확인이 일치하지 않습니다."
    return None


def add(users: dict, name: str, password: str, role: str) -> dict:
    """계정을 추가(또는 비밀번호·역할을 바꾼) 새 목록을 돌려줍니다. 원래 목록은 그대로 둡니다."""
    if role not in ROLE_NAMES:
        raise ValueError(f"알 수 없는 역할: {role}")
    salt = os.urandom(16)
    record = {"role": role, "salt": salt.hex(), "hash": _hash(password, salt, ITERATIONS), "iter": ITERATIONS}
    return dict(users, **{name: record})


def set_password(users: dict, name: str, password: str) -> dict:
    """비밀번호만 바꾼 새 목록 (역할은 그대로)."""
    return add(users, name, password, users[name]["role"])


def remove(users: dict, name: str) -> dict:
    """계정을 지운 새 목록. 마지막 관리자는 지울 수 없습니다(ValueError)."""
    if users.get(name, {}).get("role") == ADMIN and admin_count(users) <= 1:
        raise ValueError("관리자가 한 명은 있어야 합니다.")
    return {k: v for k, v in users.items() if k != name}


def admin_count(users: dict) -> int:
    return sum(1 for u in users.values() if u["role"] == ADMIN)


def verify(users: dict, name: str, password: str) -> str | None:
    """아이디·비밀번호가 맞으면 역할("admin"/"user"), 틀리면 None."""
    user = users.get(name)
    if not user:
        _hash(password or "", b"0" * 16, ITERATIONS)  # 없는 아이디도 같은 시간이 걸리게
        return None
    try:
        expected = _hash(password or "", bytes.fromhex(user["salt"]), int(user.get("iter", ITERATIONS)))
    except ValueError:
        return None
    return user["role"] if hmac.compare_digest(expected, user["hash"]) else None
