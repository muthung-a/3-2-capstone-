r"""대시보드 진입점: 화면을 '조립'만 합니다.

계산은 core/, 화면 조각은 ui/, 보고서 파일은 reports/ 에 두고 여기서는 불러와서 배치만 합니다.
실행: 실행.bat 더블클릭 (또는 .venv\Scripts\python -m streamlit run app.py)
"""
import streamlit as st

import config
from ui import login, sidebar, theme
from ui.pages import cost, custom, drugs, overview, patients, revenue

# 탭 이름과 그 탭을 그리는 파일. 탭을 추가하려면 ui/pages/에 파일을 만들고 여기 한 줄 추가.
# 순서 = 화면 순서. 자주 보는 탭을 앞에 두세요. (개요 탭 맨 위에 자동 요약이 나옵니다)
TABS = [
    ("🏠 개요", overview),
    ("🛏️ 환자·병상", patients),
    ("💰 수익", revenue),
    ("🧾 비용", cost),
    ("💊 약품", drugs),
    ("🧩 사용자 정의 통계", custom),
]


def main(demo: bool = False) -> None:
    """화면 전체. demo=True 는 인터넷 시연판(demo_app.py): 가상 데이터만, 파일 올리기 없음."""
    st.set_page_config(page_title=config.APP_TITLE, page_icon=config.APP_ICON, layout="wide")
    theme.apply()
    can_edit, author = True, ""  # 환경설정을 바꿀 수 있는지, 로그인한 사람
    if demo:  # 시연판은 가상 데이터라 로그인 없이 봄
        sidebar.brand()
    else:
        user = login.gate()  # 로그인 전이면 로그인 화면만 그리고 None
        if user is None:
            return
        sidebar.brand()
        login.user_box(user)  # 로그인한 사람 · 계정 관리 · 로그아웃 · 자리 비움 자동 로그아웃
        can_edit, author = user["role"] == "admin", user["name"]
    view = sidebar.render(demo, can_edit, author)  # 지금 보고 있는 조건(파일·기준월·조회기간·적정선) 또는 None

    theme.header(view)  # 맨 위 배너
    if view is None:
        st.info("왼쪽 사이드바에서 월별 통계표 엑셀 파일을 올려 주세요.")
        return
    sidebar.render_exports(view)  # 사이드바 아래: 엑셀·인쇄용 보고서 내보내기
    tab_objects = st.tabs([name for name, _ in TABS])
    for tab, (_, page) in zip(tab_objects, TABS):
        with tab:
            page.render(view)


if __name__ == "__main__":  # streamlit run app.py 로 실행할 때
    main()
