"""로그인 화면과 사이드바의 '로그인한 사람' 칸.

- 계정이 하나도 없으면(처음 실행) 관리자 계정 만들기 화면이 나옵니다.
- 로그인한 사람은 st.session_state["user"] = {"name": 아이디, "role": "admin"/"user"} 로 기억합니다.
"""
import time
from html import escape

import streamlit as st

import config
from core import auth
from ui import accounts


def _card_columns():
    return st.columns([1, 1.3, 1])[1]


def _first_admin() -> None:
    """처음 실행: 관리자 계정 만들기."""
    with _card_columns():
        st.markdown("#### 🔐 처음 사용 · 관리자 계정 만들기")
        st.caption("이 PC에서 처음 여셨습니다. 계정을 관리할 **관리자** 계정을 먼저 만들어 주세요. "
                   "계정은 이 PC에만 저장됩니다.")
        with st.form("first_admin"):
            name = st.text_input("관리자 아이디")
            pw = st.text_input(f"비밀번호 ({auth.MIN_PASSWORD}자 이상)", type="password")
            pw2 = st.text_input("비밀번호 확인", type="password")
            ok = st.form_submit_button("관리자 계정 만들기", type="primary", width="stretch")
        if ok:
            name = name.strip()
            problem = auth.check_new({}, name, pw, pw2)
            if problem:
                st.error(problem)
            elif not auth.save(config.ACCOUNTS_PATH, auth.add({}, name, pw, auth.ADMIN)):
                st.error("계정을 저장하지 못했습니다. 다시 시도해 주세요.")
            else:
                st.session_state["user"] = {"name": name, "role": auth.ADMIN}
                st.rerun()


def _login_form(users: dict) -> None:
    limit, wait = config.LOGIN_LOCK
    with _card_columns():
        st.markdown("#### 🔐 로그인")
        st.caption("관리자에게 받은 아이디와 비밀번호를 입력하세요.")
        locked_until = st.session_state.get("_login_locked_until", 0)
        with st.form("login"):
            name = st.text_input("아이디")
            pw = st.text_input("비밀번호", type="password")
            ok = st.form_submit_button("로그인", type="primary", width="stretch")
        if not ok:
            return
        if time.time() < locked_until:
            st.error(f"비밀번호를 {limit}번 틀려서 잠시 막았습니다. {int(locked_until - time.time()) + 1}초 뒤에 다시 시도하세요.")
            return
        role = auth.verify(users, name.strip(), pw)
        if role:
            st.session_state.pop("_login_fails", None)
            st.session_state["user"] = {"name": name.strip(), "role": role}
            st.rerun()
        fails = st.session_state.get("_login_fails", 0) + 1
        st.session_state["_login_fails"] = fails
        if fails >= limit:
            st.session_state["_login_fails"] = 0
            st.session_state["_login_locked_until"] = time.time() + wait
            st.error(f"비밀번호를 {limit}번 틀려서 {wait}초 동안 로그인을 막습니다.")
        else:
            st.error(f"아이디 또는 비밀번호가 맞지 않습니다. ({fails}/{limit})")
        st.caption("비밀번호를 잊었으면 관리자에게 초기화를 요청하세요.")


def gate() -> dict | None:
    """로그인한 사람 {"name", "role"}. 아직 로그인 전이면 로그인 화면을 그리고 None."""
    users = auth.load(config.ACCOUNTS_PATH)
    user = st.session_state.get("user")
    if user and users.get(user["name"], {}).get("role") == user["role"]:
        return user
    st.session_state.pop("user", None)  # 계정이 지워졌거나 역할이 바뀌었으면 다시 로그인
    if users:
        _login_form(users)
    else:
        _first_admin()
    return None


def user_box(user: dict) -> None:
    """사이드바 맨 위: 로그인한 사람, 내 비밀번호 바꾸기, (관리자) 계정 관리, 로그아웃."""
    with st.sidebar:
        role = auth.ROLE_NAMES[user["role"]]
        st.markdown(f'<div class="side-h">로그인</div><div>👤 <b>{escape(user["name"])}</b> · {role}</div>',
                    unsafe_allow_html=True)
        cols = st.columns(2)
        if user["role"] == auth.ADMIN and cols[0].button("👥 계정 관리", width="stretch"):
            accounts.manage_dialog(user)
        if cols[1].button("로그아웃", width="stretch"):
            st.session_state.pop("user", None)
            st.rerun()
        if st.button("🔑 내 비밀번호 바꾸기", type="tertiary"):
            accounts.password_dialog(user)
