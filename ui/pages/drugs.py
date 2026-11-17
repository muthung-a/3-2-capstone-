"""'약품' 탭: 약품 처방 원 데이터(시트 6~11) → 진료과별 처방금액 · 상위 약품 (자동 계산 + 검산)."""
import plotly.graph_objects as go
import streamlit as st

from core import drugs, kpi, revenue
from core.view import View
from ui import theme


def _cards(d, month: int) -> None:
    s = drugs.summary(d, month)
    ok = drugs.verify(d, month)
    check = {True: "일치 ✅", False: "불일치 ⚠", None: "소계 없음"}[ok]
    change = s["전월 대비(%)"]
    arrow = "－" if change != change else (f"▲ {change:.1f}%" if change >= 0 else f"▼ {abs(change):.1f}%")
    cards = [("💊", "#8b5cf6", "총 처방금액", kpi.format_value(s["총 처방금액"], "money"), f"전월 대비 {arrow}"),
             ("📋", "#3b82f6", "처방 품목 수", f"{s['품목 수']:,}개", "금액이 있는 약품"),
             ("🧾", "#10b981", "처방 횟수", f"{s['처방횟수']:,.0f}회", "모든 약품 합계"),
             ("✔️", "#f59e0b", "검산", check, "약품 합계 vs 엑셀 소계")]
    st.markdown('<div class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr))">' + "".join(
        f'<div class="kpi" style="--accent:{c};--tint:{c}1a"><div class="hd"><div class="l">{lab}</div>'
        f'<div class="ic">{ic}</div></div><div class="v" style="font-size:22px">{val}</div>'
        f'<div class="c">{sub}</div></div>' for ic, c, lab, val, sub in cards) + "</div>", unsafe_allow_html=True)


def _dept_trend(d) -> None:
    theme.panel_title("진료과별 처방금액 추이", "시트 6~11 · 진료과별 금액 칸 기준")
    table = drugs.dept_by_month(d)
    x = [theme.month_label(m) for m in d.months]
    fig = go.Figure()
    for i, (dept, row) in enumerate(table.iterrows()):
        fig.add_bar(x=x, y=row.tolist(), name=dept, marker_color=theme.PALETTE[i % len(theme.PALETTE)],
                    hovertemplate="%{fullData.name}: %{y:,.0f}원<extra></extra>")
    fig.update_layout(barmode="stack")
    theme.show_chart(fig, money=True, legend_right=True)


def _dept_share(d, month: int) -> None:
    theme.panel_title("진료과별 비중", f"{month}월")
    s = drugs.dept_by_month(d)[month]
    s = s[s > 0]
    fig = go.Figure(go.Pie(labels=s.index, values=s.values, hole=0.55, sort=False,
                           marker_colors=theme.PALETTE[:len(s)], texttemplate="%{label}<br>%{percent:.0%}",
                           hovertemplate="%{label}: %{value:,.0f}원<extra></extra>"))
    fig.update_layout(showlegend=False,
                      annotations=[dict(text=kpi.format_value(s.sum(), "money"), showarrow=False, font_size=18)])
    theme.show_chart(fig)


def _top(d, month: int) -> None:
    theme.panel_title("처방금액 상위 10개 약품", f"{month}월")
    s = drugs.top_items(d, month, 10)
    names = [n if len(n) <= 22 else n[:21] + "…" for n in s.index]  # 긴 약품명은 줄임 (마우스 올리면 전체)
    fig = go.Figure(go.Bar(x=s.values[::-1], y=names[::-1], orientation="h", marker_color="#8b5cf6",
                           customdata=list(s.index[::-1]), hovertemplate="%{customdata}: %{x:,.0f}원<extra></extra>"))
    theme.base_layout(fig, 340)
    fig.update_xaxes(type="linear", showgrid=True, gridcolor="#f3f4f6")
    fig.update_yaxes(type="category")
    ticks, text = revenue.money_ticks(list(s.values))
    fig.update_xaxes(tickvals=ticks, ticktext=text)
    st.plotly_chart(fig, width="stretch", config=theme.CHART_CFG, key=theme.next_key("chart"))


def _table(d) -> None:
    theme.panel_title("진료과 × 월 처방금액", "엑셀로 받으면 원래 숫자")
    theme.show_table(drugs.dept_by_month(d), "money", "약품_진료과별")


def render(v: View) -> None:
    """약품 탭을 그립니다."""
    st.subheader("💊 약품 처방 (원 데이터 → 자동 계산)")
    d = v.drugs
    if d is None:
        st.info("이 엑셀에는 약품 처방 시트(이름이 '6', '7' 처럼 달 숫자인 시트)가 없습니다.")
        return
    st.caption("시트 이름(6~11)을 달로 봅니다. 연도는 시트에 없어서 사이드바 기준월과는 따로 고릅니다. "
               "약품 이름이 없는 줄은 엑셀의 구역 소계라 계산에서 빼고 검산에만 씁니다.")
    month = st.radio("볼 달", d.months, index=len(d.months) - 1, horizontal=True,
                     format_func=theme.month_label, key="drug_month")
    theme.safe(_cards, d, month)
    left, right = st.columns([1.4, 1])
    with left.container(border=True):
        theme.safe(_dept_trend, d)
    with right.container(border=True):
        theme.safe(_dept_share, d, month)
    left, right = st.columns([1.4, 1])
    with left.container(border=True):
        theme.safe(_top, d, month)
    with right.container(border=True):
        theme.safe(_table, d)
