r"""대시보드 진입점: 화면을 '조립'만 합니다.

계산은 core/, 화면 조각은 ui/, 보고서 파일은 reports/ 에 두고 여기서는 불러와서 배치만 합니다.
실행: 실행.bat 더블클릭 (또는 .venv\Scripts\python -m streamlit run app.py)
"""
import streamlit as st

import config
from ui import sidebar, theme
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


def main() -> None:
    st.set_page_config(page_title=config.APP_TITLE, page_icon=config.APP_ICON, layout="wide")
    theme.apply()
    view = sidebar.render()  # 지금 보고 있는 조건(파일·기준월·조회기간·적정선) 또는 None

    theme.header(view)  # 맨 위 배너
    if view is None:
        st.info("왼쪽 사이드바에서 엑셀 파일을 올리거나 선택하세요.")
        return
    sidebar.render_exports(view)  # 사이드바 아래: 엑셀·인쇄용 보고서 내보내기
    tab_objects = st.tabs([name for name, _ in TABS])
    for tab, (_, page) in zip(tab_objects, TABS):
        with tab:
            page.render(view)


main()
