"""'개요' 탭: 맨 위 자동 요약·확인 필요 항목 → KPI 카드 → 즐겨찾기 지표."""
from html import escape

import streamlit as st

import config
from core import custom, kpi, summary
from core.view import View
from ui import theme


def _arrow(change: float, kind: str) -> str:
    """증감 ▲(빨강) ▼(파랑) 배지."""
    unit = "%p" if kind == "ratio" else "%"
    if change != change:  # NaN(값 없음)
        return '<span class="fl">－</span>'
    if change > 0.05:
        return f'<span class="up">▲ {abs(change):.1f}{unit}</span>'
    if change < -0.05:
        return f'<span class="dn">▼ {abs(change):.1f}{unit}</span>'
    return f'<span class="fl">－ 0.0{unit}</span>'


def _spark(values: list, w: int = 86, h: int = 26) -> str:
    """최근 13개월 미니 추이 선 그래프(SVG)."""
    pts = [(i, v) for i, v in enumerate(values) if v == v]
    if len(pts) < 2:
        return ""
    lo, hi = min(v for _, v in pts), max(v for _, v in pts)
    hi = hi if hi != lo else lo + 1
    n = len(values)
    xy = [(i * (w - 4) / (n - 1) + 2, h - 3 - (v - lo) / (hi - lo) * (h - 6)) for i, v in pts]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    lx, ly = xy[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true">'
            f'<polyline points="{line}" fill="none" stroke="{theme.PRIMARY}" stroke-width="1.6"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.6" fill="{theme.PRIMARY}"/></svg>')


def _card(k: kpi.Kpi) -> str:
    if k.suspect:  # 0이 나올 수 없는 항목이 0 → 값은 보여주되 증감은 계산하지 않음
        value = f'{kpi.format_value(0, k.kind)} <span class="badge y">미입력 의심</span>'
        change = '<span class="fl">증감 계산 안 함</span>'
        warn = " warn"
    else:
        value, warn = kpi.format_value(k.value, k.kind), ""
        change = f"전월 {_arrow(k.change, k.kind)}<br>전년 {_arrow(k.yoy_change, k.kind)}"
    return (f'<div class="kpi{warn}"><div class="l">{escape(k.label)}</div>'
            f'<div class="v">{value}</div>'
            f'<div class="s"><div class="c">{change}</div>{_spark(k.history)}</div></div>')


def _summary(v: View) -> None:
    left, right = st.columns([1.75, 1])
    with left.container(border=True, height=250):
        theme.panel_title(f"자동 요약 — {v.month.year}년 {v.month.month}월",
                          f"비교: 전월 {v.month - 1} · 전년 동월 {v.month - 12}")
        lines = summary.summary_lines(v.df, v.month)  # 숫자·고정 문구만 들어 있어 안전한 HTML
        st.markdown('<ul class="sumlist">' + "".join(f"<li>{ln}</li>" for ln in lines) + "</ul>",
                    unsafe_allow_html=True)
    with right.container(border=True, height=250):
        items = summary.alerts(v.df, v.month, v.warn_pct, v.bed_target)
        n = sum(1 for a in items if a.level != "g")
        theme.panel_title("확인 필요 항목", f"{n}건 · 기준 ±{v.warn_pct:.0f}%")
        st.markdown('<ul class="alerts">' + "".join(
            f'<li><span class="badge {a.level}">{escape(a.badge)}</span><span>{escape(a.text)}</span></li>'
            for a in items) + "</ul>", unsafe_allow_html=True)


def _favorites(v: View) -> None:
    favs = v.settings.get("favorites", [])
    table = custom.favorites_table(v.df, favs, v.month) if favs else None
    if table is None or table.empty:
        st.caption("⭐ '사용자 정의 통계' 탭에서 자주 보는 항목을 즐겨찾기에 추가하면 여기에 나옵니다.")
        return
    with st.container(border=True):
        theme.panel_title("⭐ 즐겨찾기 지표", "사용자 정의 통계 탭에서 추가·해제")
        shown = table.copy()
        for col in ("당월", "전월", "전년 동월"):
            shown[col] = shown[col].map(lambda x: kpi.format_value(x, "number"))
        for col in ("전월 대비(%)", "전년 대비(%)"):
            shown[col] = shown[col].map(summary.fmt_p)
        st.dataframe(shown.set_index("항목"), width="stretch")


def render(v: View) -> None:
    """개요 탭을 그립니다."""
    _summary(v)
    st.subheader(f"{v.month.year}년 {v.month.month}월 핵심 지표")
    cards = kpi.build_kpis(v.df, v.month, config.KPIS)
    if not cards:
        st.warning("KPI 항목을 찾지 못했습니다. config.py 의 KPIS 이름을 확인하세요.")
        return
    st.markdown('<div class="kpis">' + "".join(_card(k) for k in cards) + "</div>", unsafe_allow_html=True)
    st.caption("▲ 빨강 = 증가, ▼ 파랑 = 감소. 오른쪽 작은 선은 최근 13개월 추이입니다.")
    _favorites(v)
