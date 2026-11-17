"""'수익' 탭: 총진료비, 입원·외래 청구, 인당 진료비, 재활치료, 한의사별, 산소·기타 행위."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from core import kpi, monthly, revenue
from core.view import View
from ui import theme

_INSURANCE_COLORS = theme.COLORS
_CARE_COLORS = {"의과 입원": "#3b82f6", "의과 외래": "#93c5fd", "한방 입원": "#10b981", "한방 외래": "#6ee7b7"}
_HOVER = "%{fullData.name}: %{y:,.0f}원<extra></extra>"

def _stacked_bar(frame: pd.DataFrame, x: list, colors: dict) -> go.Figure:
    fig = go.Figure()
    for name, row in frame.iterrows():
        fig.add_bar(x=x, y=row.tolist(), name=name, marker_color=colors.get(name), hovertemplate=_HOVER)
    fig.update_layout(barmode="stack")
    return fig


def _total_trend(df, months, x) -> None:
    theme.panel_title("총진료비 추이", "청구금액 + 본인부담금 · 보험 구분별")
    frame = monthly.section_frame(df, "총진료비", months, sub="합계")
    theme.show_chart(_stacked_bar(frame, x, _INSURANCE_COLORS), money=True)


def _insurance_share(df, month) -> None:
    theme.panel_title("보험 구분별 비중", f"{month.year}년 {month.month}월 총진료비")
    s = monthly.section_frame(df, "총진료비", [month], sub="합계")[month].dropna()
    s = s[s > 0]
    fig = go.Figure(go.Pie(labels=s.index, values=s.values, hole=0.55, sort=False,
                           marker_colors=[_INSURANCE_COLORS.get(n) for n in s.index],
                           texttemplate="%{label}<br>%{percent:.1%}", hovertemplate="%{label}: %{value:,.0f}원<extra></extra>"))
    fig.update_layout(showlegend=False,
                      annotations=[dict(text=kpi.format_value(s.sum(), "money"), showarrow=False, font_size=18)])
    theme.show_chart(fig)


def _care_type(df, months, x) -> None:
    theme.panel_title("입원 · 외래 청구금액", "의과 / 한방")
    frame = monthly.section_frame(df, "청구금액", months, sub="합계")
    frame = frame.reindex([k for k in _CARE_COLORS if k in frame.index])
    theme.show_chart(_stacked_bar(frame, x, _CARE_COLORS), money=True)


def _per_patient(df, months, x) -> None:
    theme.panel_title("인당 총진료비", "총진료비 ÷ 평균재원환자수 · 월")
    frame = monthly.section_frame(df, "평균진료비", months, sub="총진료비/평균재원").drop("일반", errors="ignore")
    fig = go.Figure()
    for name, row in frame.iterrows():
        fig.add_scatter(x=x, y=row.tolist(), name=name, mode="lines+markers", hovertemplate=_HOVER,
                        line=dict(color=_INSURANCE_COLORS.get(name), width=2.2))
    theme.show_chart(fig, money=True)


def _rehab_trend(df, months, x) -> None:
    theme.panel_title("재활치료 매출", "급여 재활치료 / 도수치료 / 크라이오")
    colors = {"급여 재활치료": theme.PRIMARY, "도수치료": "#f59e0b", "크라이오": "#8b5cf6"}
    theme.show_chart(_stacked_bar(revenue.rehab_split(df, months), x, colors), money=True)


def _rehab_items(df, month) -> None:
    theme.panel_title("급여 재활치료 항목별", f"{month.year}년 {month.month}월 · 큰 순서")
    s = revenue.rehab_items(df, month)
    if s.empty:
        st.caption("이 달은 값이 없습니다.")
        return
    fig = go.Figure(go.Bar(x=s.values[::-1], y=s.index[::-1], orientation="h", marker_color=theme.PRIMARY,
                           hovertemplate="%{y}: %{x:,.0f}원<extra></extra>"))
    theme.base_layout(fig, 300)
    fig.update_xaxes(type="linear", showgrid=True, gridcolor="#f3f4f6")
    fig.update_yaxes(type="category", gridcolor="rgba(0,0,0,0)")
    ticks, text = revenue.money_ticks(list(s.values))
    fig.update_xaxes(tickvals=ticks, ticktext=text)
    st.plotly_chart(fig, width="stretch", config=theme.CHART_CFG)


def _doctors(df, months, x) -> None:
    theme.panel_title("한의사별 총진료비", "이름은 가명으로 표시")
    frame = monthly.section_frame(df, "한의사별총진료비", months)
    fig = go.Figure()
    for name, row in frame.iterrows():
        fig.add_bar(x=x, y=row.tolist(), name=name, hovertemplate=_HOVER)
    fig.update_layout(barmode="stack")
    theme.show_chart(fig, money=True)


def _etc_items(df, months, x) -> None:
    theme.panel_title("의료용산소 · 기타 행위", "산소: 포괄수가(실청구X) / 행위별(실청구O)")
    frame = monthly.section_frame(df, "의료용산소", months)
    for name in ("방광스캐너", "고빈도흉벽진동요법"):  # 행위별 총진료비 줄
        try:
            frame.loc[f"{name} 총진료비"] = monthly.find_row(df, name, "총진료비")[months]
        except KeyError:
            pass
    frame = frame.dropna(how="all")
    if frame.empty:
        st.caption("조회기간에 값이 없습니다. (엑셀에 산소·기타 행위 값이 입력되지 않음)")
        return
    colors = dict(zip(frame.index, theme.PALETTE))
    theme.show_chart(_stacked_bar(frame, x, colors), money=True)


def _detail_table(df, months) -> None:
    theme.panel_title("상세 통계표", "금액 단위: 억 / 만 원")
    raw, kinds = kpi.detail_frame(df, months, config.REVENUE_DETAIL)
    theme.show_table(raw, kinds, f"수익_{months[-1]}")


def render(v: View) -> None:
    """수익 탭을 그립니다."""
    df, month, months = v.df, v.month, v.months
    x = [theme.month_label(m) for m in months]
    st.subheader(f"수익 ({x[0]} ~ {x[-1]})")

    rows = [((_total_trend, (df, months, x)), (_insurance_share, (df, month))),
            ((_care_type, (df, months, x)), (_per_patient, (df, months, x))),
            ((_rehab_trend, (df, months, x)), (_rehab_items, (df, month)))]
    for (left_fn, left_args), (right_fn, right_args) in rows:
        left, right = st.columns(2)
        with left.container(border=True):
            left_fn(*left_args)
        with right.container(border=True):
            right_fn(*right_args)

    left, right = st.columns(2)
    with left.container(border=True):
        _doctors(df, months, x)
    with right.container(border=True):
        _etc_items(df, months, x)
    with st.container(border=True):
        _detail_table(df, months)
