"""'비용' 탭: 주요 비용, 인건비, 관리비, 식자재, 의약품, 간병·위생소모품 손익."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from core import cost, kpi, monthly
from core.view import View
from ui import theme

_PALETTE = theme.PALETTE
_HOVER_WON = "%{fullData.name}: %{y:,.0f}원<extra></extra>"


def _bars(frame: pd.DataFrame, x: list, stack: bool = True) -> go.Figure:
    """항목별 막대그래프 (stack=True 면 쌓기, False 면 나란히)."""
    fig = go.Figure()
    for i, (name, row) in enumerate(frame.iterrows()):
        fig.add_bar(x=x, y=row.tolist(), name=name, marker_color=_PALETTE[i % len(_PALETTE)],
                    hovertemplate=_HOVER_WON)
    fig.update_layout(barmode="stack" if stack else "group")
    return fig


def _lines(frame: pd.DataFrame, x: list, unit: str = "원") -> go.Figure:
    """항목별 꺾은선그래프."""
    fig = go.Figure()
    for i, (name, row) in enumerate(frame.iterrows()):
        fig.add_scatter(x=x, y=row.tolist(), name=name, mode="lines+markers",
                        line=dict(color=_PALETTE[i % len(_PALETTE)], width=2.2),
                        hovertemplate="%{fullData.name}: %{y:,.0f}" + unit + "<extra></extra>")
    return fig


def _profit_line(fig: go.Figure, x: list, values: list, name: str) -> None:
    """손익 꺾은선(빨강)과 0 기준선을 그래프에 더합니다."""
    fig.add_scatter(x=x, y=values, name=name, mode="lines+markers", hovertemplate=_HOVER_WON,
                    line=dict(color=theme.UP, width=2.4))
    fig.add_hline(y=0, line_color="#d1d5db", line_width=1)


def _total_trend(df, months, x) -> None:
    theme.panel_title("주요 비용 추이", "엑셀에 있는 비용 항목 합계 · 빈 달은 미입력")
    theme.show_chart(_bars(cost.cost_breakdown(df, months, config.COST_ITEMS), x), money=True,
                     legend_right=True)


def _share(df, month) -> None:
    theme.panel_title("비용 구성", f"{month.year}년 {month.month}월")
    s = cost.cost_breakdown(df, [month], config.COST_ITEMS)[month].dropna()
    s = s[s > 0]
    if s.empty:
        st.caption("이 달은 값이 없습니다.")
        return
    fig = go.Figure(go.Pie(labels=s.index, values=s.values, hole=0.55, sort=False,
                           marker_colors=_PALETTE[:len(s)], texttemplate="%{label}<br>%{percent:.0%}",
                           hovertemplate="%{label}: %{value:,.0f}원<extra></extra>"))
    fig.update_layout(showlegend=False,
                      annotations=[dict(text=kpi.format_value(s.sum(), "money"), showarrow=False, font_size=18)])
    theme.show_chart(fig)


def _labor(df, months, x) -> None:
    theme.panel_title("인건비", "직종별 · 퇴직금·복리후생비·일용직 제외")
    frame = monthly.section_frame(df, "인건비(퇴직금,복리후생비,일용직제외)", months)
    frame.index = [name.split(" ", 1)[0] for name in frame.index]  # '간호인력 간호사, 간호조무사' → '간호인력'
    theme.show_chart(_bars(frame, x), money=True, legend_right=True)


def _overhead(df, months, x) -> None:
    theme.panel_title("관리비", "항목별")
    theme.show_chart(_bars(monthly.section_frame(df, "관리비", months), x), money=True, legend_right=True)


def _food(df, months, x) -> None:
    theme.panel_title("식자재", "업체별 매입액")
    theme.show_chart(_bars(monthly.section_frame(df, "식자재", months, sub="식자재"), x), money=True,
                     legend_right=True)


def _meal_price(df, months, x) -> None:
    theme.panel_title("식단가", "한 끼당 원가 · 원")
    theme.show_chart(_lines(monthly.section_frame(df, "식자재", months, sub="식단가"), x), money=True)


def _drugs(df, months, x) -> None:
    theme.panel_title("의약품 환자당 투약비", "급여 / 비급여 · 원")
    frame = monthly.section_frame(df, "의약품", months, sub="환자당투약")
    theme.show_chart(_bars(frame, x), money=True)


def _caregiving(df, months, x) -> None:
    theme.panel_title("간병 손익", "막대: 총수입·지급수수료 / 빨간 선: 손익")
    pl = cost.caregiving_pl(df, months)
    fig = _bars(pl.loc[["총수입", "지급수수료"]], x, stack=False)
    _profit_line(fig, x, pl.loc["손익"].tolist(), "손익")
    theme.show_chart(fig, money=True)


def _hygiene(df, months, x) -> None:
    theme.panel_title("위생소모품 손익", "막대: 매출·매입·폐기물 처리비 / 빨간 선: 최종 손익")
    pl = cost.hygiene_pl(df, months)
    fig = _bars(pl.loc[["매출", "매입", "폐기물 처리비용"]], x, stack=False)
    _profit_line(fig, x, pl.loc["최종 손익"].tolist(), "최종 손익")
    theme.show_chart(fig, money=True)


def _detail_table(df, months) -> None:
    theme.panel_title("상세 통계표", "금액 단위: 억 / 만 원")
    theme.show_table(cost.cost_breakdown(df, months, config.COST_ITEMS), "money", f"비용_{months[-1]}")


def render(v: View) -> None:
    """비용 탭을 그립니다."""
    df, month, months = v.df, v.month, v.months
    x = [theme.month_label(m) for m in months]
    st.subheader(f"🧾 비용 ({x[0]} ~ {x[-1]})")

    pairs = [((_total_trend, (df, months, x)), (_share, (df, month))),
             ((_labor, (df, months, x)), (_overhead, (df, months, x))),
             ((_food, (df, months, x)), (_meal_price, (df, months, x))),
             ((_caregiving, (df, months, x)), (_hygiene, (df, months, x))),
             ((_drugs, (df, months, x)), (_detail_table, (df, months)))]
    for (left_fn, left_args), (right_fn, right_args) in pairs:
        left, right = st.columns(2)
        with left.container(border=True):
            theme.safe(left_fn, *left_args)
        with right.container(border=True):
            theme.safe(right_fn, *right_args)
