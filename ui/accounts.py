"""계정 관리 창(관리자 전용: 계정 추가·수정·삭제, 사용 기록)과 '내 비밀번호 바꾸기' 창."""
import pandas as pd
import streamlit as st

import config
from core import audit, auth


def _save(users: dict, me: dict, action: str, target: str, message: str) -> None:
    """계정 목록을 저장하고 사용 기록에 남깁니다. 창은 열어 둔 채 목록만 새로 그립니다."""
    if auth.save(config.ACCOUNTS_PATH, users):
        audit.add(config.AUDIT_PATH, me["name"], action, target)
        st.session_state["_accounts_msg"] = message
        st.rerun(scope="fragment")
    st.error("저장하지 못했습니다. 다시 시도해 주세요.")


def _add_tab(users: dict, me: dict) -> None:
    with st.form("add_user", clear_on_submit=True):
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
                label = auth.ROLE_NAMES[role]
                _save(auth.add(users, name, pw, role), me, "계정 추가", f"{name} ({label})",
                      f"'{name}' 계정을 만들었습니다. ({label})")


def _edit_tab(users: dict, me: dict) -> None:
    others = sorted(n for n in users if n != me["name"])
    if not others:
        st.info("수정할 다른 계정이 없습니다. 내 비밀번호는 사이드바의 '내 비밀번호 바꾸기'에서 바꿉니다.")
        return
    target = st.selectbox("계정 선택", others)
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
                _save(auth.set_password(users, target, pw), me, "비밀번호 초기화", target,
                      f"'{target}'의 비밀번호를 바꿨습니다.")
    c1, c2 = st.columns(2)
    other_role = auth.USER if users[target]["role"] == auth.ADMIN else auth.ADMIN
    label = auth.ROLE_NAMES[other_role]
    if c1.button(f"역할을 '{label}'(으)로 바꾸기", width="stretch"):
        changed = dict(users, **{target: dict(users[target], role=other_role)})
        _save(changed, me, "역할 변경", f"{target} → {label}", f"'{target}'의 역할을 {label}(으)로 바꿨습니다.")
    if c2.button(f"🗑 '{target}' 삭제", width="stretch"):
        try:
            _save(auth.remove(users, target), me, "계정 삭제", target, f"'{target}' 계정을 삭제했습니다.")
        except ValueError as err:
            st.error(str(err))


def _log_tab() -> None:
    rows = audit.load(config.AUDIT_PATH)
    if not rows:
        st.info("아직 기록이 없습니다.")
        return
    table = pd.DataFrame(rows).rename(columns={"time": "시각", "who": "아이디", "action": "한 일", "detail": "내용"})
    people = ["전체"] + sorted(table["아이디"].unique())
    c1, c2 = st.columns([1, 2])
    who = c1.selectbox("사람", people)
    if who != "전체":
        table = table[table["아이디"] == who]
    c2.caption(f"최근 {len(table)}건 · 최근 것이 위 · 엑셀 내용은 기록하지 않습니다 (누가·언제·무엇을 했는지만)")
    st.dataframe(table, hide_index=True, width="stretch", height=320)
    st.download_button("⬇ 사용 기록 받기 (CSV)", table.to_csv(index=False).encode("utf-8-sig"),
                       "사용기록.csv", "text/csv")


@st.dialog("👥 계정 관리", width="large")
def manage_dialog(me: dict) -> None:
    """관리자: 계정 목록 · 추가 · 비밀번호 초기화 · 역할 변경 · 삭제 · 사용 기록."""
    users = auth.load(config.ACCOUNTS_PATH)
    if msg := st.session_state.pop("_accounts_msg", None):
        st.success(msg)
    st.dataframe([{"아이디": n, "역할": auth.ROLE_NAMES[u["role"]] + (" (나)" if n == me["name"] else "")}
                  for n, u in sorted(users.items())], hide_index=True, width="stretch")
    st.caption("관리자: 계정 관리·환경설정 변경·사용 기록 보기 / 사용자: 대시보드 보기·보고서 받기")
    add_tab, edit_tab, log_tab = st.tabs(["➕ 계정 추가", "✏️ 계정 수정·삭제", "📋 사용 기록"])
    with add_tab:
        _add_tab(users, me)
    with edit_tab:
        _edit_tab(users, me)
    with log_tab:
        _log_tab()


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
        audit.add(config.AUDIT_PATH, me["name"], "내 비밀번호 변경")
        st.toast("비밀번호를 바꿨습니다.")
        st.rerun()
    else:
        st.error("저장하지 못했습니다. 다시 시도해 주세요.")
