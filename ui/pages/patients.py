"""'환자·병상' 탭: 재원환자, 병상가동율, 입퇴원, 환자군 추이."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from core import kpi, monthly
from core.view import View
from ui import theme

def _stacked_bar(frame: pd.DataFrame, x: list, colors: dict | None = None) -> go.Figure:
    """항목별로 쌓은 막대그래프."""
    fig = go.Figure()
    for name, row in frame.iterrows():
        color = (colors or {}).get(name)
        fig.add_bar(x=x, y=row.tolist(), name=name, marker_color=color)
    fig.update_layout(barmode="stack")
    return fig


def _inpatients(df, months, x) -> None:
    theme.panel_title("월말 재원환자", "보험 구분별 · 명")
    frame = monthly.section_frame(df, "월말재원환자수", months)
    theme.show_chart(_stacked_bar(frame, x, theme.COLORS))


def _bed_rate(df, months, x, target: float) -> None:
    theme.panel_title("병상가동율", f"점선 = 적정선 {target:.0%} (사이드바에서 변경)")
    rate = monthly.find_row(df, "병상가동율")[months]
    fig = go.Figure()
    fig.add_scatter(x=x, y=rate.tolist(), mode="lines+markers+text", name="병상가동율",
                    line=dict(color=theme.PRIMARY, width=2.4), text=[f"{v:.1%}" for v in rate],
                    textposition="top center", textfont=dict(size=10))
    fig.add_hline(y=target, line_dash="dot", line_color=theme.UP)
    fig.update_yaxes(range=[min(rate.min(), target) - 0.03, 1.02])
    theme.show_chart(fig, yfmt=".0%")


def _admissions(df, months, x) -> None:
    theme.panel_title("입원 · 퇴원", "실입원수 / 실퇴원수 · 명")
    fig = go.Figure()
    fig.add_bar(x=x, y=monthly.find_row(df, "입원환자수", "실입원수")[months].tolist(),
                name="실입원수", marker_color=theme.PRIMARY)
    fig.add_bar(x=x, y=monthly.find_row(df, "퇴원환자수", "실퇴원수")[months].tolist(),
                name="실퇴원수", marker_color="#93c5fd")
    fig.update_layout(barmode="group")
    theme.show_chart(fig)


def _patient_groups(df, months, x) -> None:
    theme.panel_title("환자군 구성", "A1 의료최고도 ~ A7 선택입원군 · 명")
    frame = monthly.section_frame(df, "환자군수", months)
    theme.show_chart(_stacked_bar(frame, x), legend_right=True)


def _detail_table(df, months) -> None:
    theme.panel_title("상세 통계표", "최근 월이 오른쪽")
    raw, kinds = kpi.detail_frame(df, months, config.PATIENT_DETAIL)
    theme.show_table(raw, kinds, f"환자병상_{months[-1]}")


def render(v: View) -> None:
    """환자·병상 탭을 그립니다."""
    df, months = v.df, v.months
    x = [theme.month_label(m) for m in months]
    st.subheader(f"환자 · 병상 ({theme.month_label(months[0])} ~ {theme.month_label(months[-1])})")

    left, right = st.columns(2)
    with left.container(border=True):
        _inpatients(df, months, x)
    with right.container(border=True):
        _bed_rate(df, months, x, v.bed_target / 100)

    left, right = st.columns(2)
    with left.container(border=True):
        _admissions(df, months, x)
    with right.container(border=True):
        _patient_groups(df, months, x)

    with st.container(border=True):
        _detail_table(df, months)
