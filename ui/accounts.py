"""계정 관리 창(관리자 전용)과 '내 비밀번호 바꾸기' 창."""
import streamlit as st

import config
from core import auth


def _save(users: dict, message: str) -> None:
    if auth.save(config.ACCOUNTS_PATH, users):
        st.session_state["_accounts_msg"] = message
        st.rerun(scope="fragment")  # 창은 열어 둔 채 목록만 새로 그림
    st.error("저장하지 못했습니다. 다시 시도해 주세요.")


@st.dialog("👥 계정 관리", width="large")
def manage_dialog(me: dict) -> None:
    """관리자: 계정 목록 · 추가 · 비밀번호 초기화 · 역할 변경 · 삭제."""
    users = auth.load(config.ACCOUNTS_PATH)
    if msg := st.session_state.pop("_accounts_msg", None):
        st.success(msg)
    st.dataframe([{"아이디": n, "역할": auth.ROLE_NAMES[u["role"]] + (" (나)" if n == me["name"] else "")}
                  for n, u in sorted(users.items())], hide_index=True, width="stretch")
    st.caption("관리자: 계정 관리·환경설정 변경 / 사용자: 대시보드 보기·보고서 받기")

    add_tab, edit_tab = st.tabs(["➕ 계정 추가", "✏️ 계정 수정·삭제"])
    with add_tab, st.form("add_user", clear_on_submit=True):
        name = st.text_input("아이디")
        c1, c2 = st.columns(2)
        pw = c1.text_input(f"비밀번호 ({auth.MIN_PASSWORD}자 이상)", type="password")
        pw2 = c2.text_input("비밀번호 확인", type="password")
        role = st.radio("역할", [auth.USER, auth.ADMIN], format_func=auth.ROLE_NAMES.get, horizontal=True)
        if st.form_submit_button("계정 추가", type="primary"):
            name = name.strip()
            problem = auth.check_new(users, name, pw, pw2)
            if problem:
                st.error(problem)
            else:
                _save(auth.add(users, name, pw, role), f"'{name}' 계정을 만들었습니다. ({auth.ROLE_NAMES[role]})")

    with edit_tab:
        others = sorted(n for n in users if n != me["name"])
        if not others:
            st.info("수정할 다른 계정이 없습니다. 내 비밀번호는 사이드바의 '내 비밀번호 바꾸기'에서 바꿉니다.")
            return
        target = st.selectbox("계정 선택", others)
        current = users[target]["role"]
        with st.form("reset_pw", clear_on_submit=True):
            st.markdown("**비밀번호 초기화**")
            c1, c2 = st.columns(2)
            pw = c1.text_input("새 비밀번호", type="password")
            pw2 = c2.text_input("새 비밀번호 확인", type="password")
            if st.form_submit_button("비밀번호 바꾸기"):
                problem = auth.check_password(pw, pw2)
                if problem:
                    st.error(problem)
                else:
                    _save(auth.set_password(users, target, pw), f"'{target}'의 비밀번호를 바꿨습니다.")
        c1, c2 = st.columns(2)
        other_role = auth.USER if current == auth.ADMIN else auth.ADMIN
        if c1.button(f"역할을 '{auth.ROLE_NAMES[other_role]}'(으)로 바꾸기", width="stretch"):
            changed = dict(users, **{target: dict(users[target], role=other_role)})
            _save(changed, f"'{target}'의 역할을 {auth.ROLE_NAMES[other_role]}(으)로 바꿨습니다.")
        if c2.button(f"🗑 '{target}' 삭제", width="stretch"):
            try:
                _save(auth.remove(users, target), f"'{target}' 계정을 삭제했습니다.")
            except ValueError as err:
                st.error(str(err))


@st.dialog("🔑 내 비밀번호 바꾸기")
def password_dialog(me: dict) -> None:
    users = auth.load(config.ACCOUNTS_PATH)
    with st.form("my_pw"):
        old = st.text_input("지금 비밀번호", type="password")
        pw = st.text_input(f"새 비밀번호 ({auth.MIN_PASSWORD}자 이상)", type="password")
        pw2 = st.text_input("새 비밀번호 확인", type="password")
        if not st.form_submit_button("바꾸기", type="primary"):
            return
    if auth.verify(users, me["name"], old) is None:
        st.error("지금 비밀번호가 맞지 않습니다.")
    elif problem := auth.check_password(pw, pw2):
        st.error(problem)
    elif auth.save(config.ACCOUNTS_PATH, auth.set_password(users, me["name"], pw)):
        st.toast("비밀번호를 바꿨습니다.")
        st.rerun()
    else:
        st.error("저장하지 못했습니다. 다시 시도해 주세요.")
