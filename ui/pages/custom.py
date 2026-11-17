"""'사용자 정의 통계' 탭: 통계표의 모든 항목 중 원하는 것을 골라 비교하고, 즐겨찾기로 저장.

회의 요구 "새 통계를 보고 싶을 때 쉽게 추가" 에 해당합니다.
엑셀에 새 항목(행)이 생기면 코드 수정 없이 자동으로 고를 수 있게 됩니다.
"""
import plotly.graph_objects as go
import streamlit as st

import config
from core import custom, settings
from core.view import View
from ui import theme


def _save_favorites(v: View, favs: list[str]) -> None:
    new = dict(v.settings, favorites=favs)
    if settings.save(config.SETTINGS_PATH, new):
        st.toast("즐겨찾기를 저장했습니다.")
    st.rerun()


def render(v: View) -> None:
    """사용자 정의 통계 탭을 그립니다."""
    st.subheader("🧩 사용자 정의 통계")
    labels = list(custom.row_labels(v.df))
    favs = [f for f in v.settings.get("favorites", []) if f in labels]
    with st.container(border=True):
        theme.panel_title("항목 고르기", f"전체 {len(labels)}개 항목 · 이름 일부를 입력해 검색")
        chosen = st.multiselect("비교할 항목", labels, default=favs[:4], placeholder="예: 식자재, 재활, 병상…")
        normalize = st.toggle("첫 달을 100으로 맞춰 비교 (단위가 다른 항목끼리 비교할 때)", value=False)
    if not chosen:
        st.info("위에서 항목을 하나 이상 고르면 그래프와 표가 나옵니다.")
        return

    frame = custom.frame_for(v.df, chosen, v.months)
    x = [theme.month_label(m) for m in v.months]
    with st.container(border=True):
        theme.panel_title("추이 비교", f"{x[0]} ~ {x[-1]}" + (" · 첫 달 = 100" if normalize else ""))
        fig = go.Figure()
        for i, (name, row) in enumerate(frame.iterrows()):
            first = row.dropna().iloc[0] if row.notna().any() else None
            ys = [(y / first * 100 if first else None) for y in row] if normalize else row.tolist()
            fig.add_scatter(x=x, y=ys, name=name, mode="lines+markers",
                            line=dict(color=theme.PALETTE[i % len(theme.PALETTE)], width=2.2))
        theme.show_chart(fig, h=340)
    with st.container(border=True):
        theme.panel_title("숫자 표", "엑셀로 받으면 원래 숫자가 들어갑니다")
        theme.show_table(frame, "number", f"사용자정의통계_{v.month}")

    left, right = st.columns(2)
    add = [c for c in chosen if c not in favs]
    if left.button(f"⭐ 고른 항목 즐겨찾기에 추가 ({len(add)}개)", disabled=not add, type="primary"):
        _save_favorites(v, favs + add)
    remove = [c for c in chosen if c in favs]
    if right.button(f"즐겨찾기에서 빼기 ({len(remove)}개)", disabled=not remove):
        _save_favorites(v, [f for f in favs if f not in remove])
