"""화면 꾸미기(색, 글꼴, CSS, 그래프·표 모양).

밝은 모던 스타일: Tremor·TailAdmin 같은 대시보드 디자인을 참고했습니다.
  - 연회색 바탕 + 흰 카드(둥근 모서리, 얇은 테두리, 아주 옅은 그림자)
  - 파란 기본색, 증감은 알약 모양 배지 (국내 관례: 증가 빨강 / 감소 파랑)
기본 색은 .streamlit/config.toml 의 [theme] 에서 정하고, 나머지는 여기 CSS 에 넣습니다.
"""
import io
from html import escape

import pandas as pd
import streamlit as st

from core.kpi import format_value
from core.revenue import money_ticks

# ------------------------------------------------------------------ 색 (Tailwind 500 계열)
PRIMARY = "#3b82f6"                                  # 기본 파랑
UP, DOWN = "#e11d48", "#2563eb"                      # 국내 관례: 증가 빨강, 감소 파랑
GRAY = "#9ca3af"
PALETTE = ["#3b82f6", "#f59e0b", "#10b981", "#8b5cf6", "#f43f5e", "#06b6d4", "#6366f1", GRAY]
COLORS = {"공단": "#3b82f6", "보호": "#f59e0b", "자보": "#10b981", "일반": GRAY}  # 보험 구분별 색
_FONT = '"Pretendard","Malgun Gothic","맑은 고딕","Apple SD Gothic Neo","Noto Sans KR",sans-serif'

# ------------------------------------------------------------------ CSS
_CSS = """
<style>
html, body, [class*="css"], .stMarkdown, button, input, select, textarea { font-family: FONT !important; }
[data-testid="stHeader"] { background: transparent; height: 0; }
.block-container { padding: 1.4rem 2rem 3rem; max-width: 1480px; }
h1 { font-size: 1.55rem !important; font-weight: 700 !important; color: #111827; letter-spacing: -.02em; }
h3 { font-size: 1.1rem !important; font-weight: 600 !important; color: #111827; }
[data-testid="stSidebar"] { border-right: 1px solid #e5e7eb; }

/* 카드(테두리 있는 칸) */
[data-testid="stVerticalBlockBorderWrapper"] { background: #fff; border-radius: 12px !important;
  border-color: #e5e7eb !important; box-shadow: 0 1px 2px rgba(16,24,40,.05); }

/* 패널 제목 */
.ptitle { display:flex; justify-content:space-between; align-items:baseline; gap:8px; margin: 0 0 6px; }
.ptitle span { font-size: 14.5px; font-weight: 600; color:#111827; }
.ptitle small { font-size: 12px; color:#6b7280; text-align:right; }

/* KPI 카드 */
.kpis { display:grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap: 14px; margin: 4px 0 8px; }
@media (max-width: 1200px) { .kpis { grid-template-columns: repeat(3, minmax(0,1fr)); } }
@media (max-width: 640px)  { .kpis { grid-template-columns: repeat(2, minmax(0,1fr)); } }
.kpi { background:#fff; border:1px solid #e5e7eb; border-radius:12px; padding:16px 18px 14px;
  box-shadow: 0 1px 2px rgba(16,24,40,.05); }
.kpi .l { font-size: 13px; color:#6b7280; font-weight: 500; }
.kpi .v { font-size: 26px; font-weight: 700; color:#111827; letter-spacing:-.02em;
  font-variant-numeric: tabular-nums; margin: 4px 0 8px; }
.kpi .s { display:flex; justify-content:space-between; align-items:flex-end; gap: 6px; }
.kpi .c { font-size: 12px; color:#6b7280; line-height: 1.9; }
.kpi.warn { border-color:#fcd34d; background:#fffbeb; }

/* 증감 배지 (알약 모양) */
.up, .dn, .fl { display:inline-block; font-size:12px; font-weight:600; padding:1px 8px; border-radius:9999px; }
.up { color:#e11d48; background:#fff1f2; } .dn { color:#2563eb; background:#eff6ff; } .fl { color:#6b7280; background:#f3f4f6; }

/* 상태 배지 */
.badge { font-size: 11.5px; font-weight:600; padding: 2px 8px; border-radius: 9999px; white-space:nowrap;
  vertical-align: middle; }
.badge.r { color:#be123c; background:#fff1f2; } .badge.y { color:#b45309; background:#fef3c7; }
.badge.g { color:#047857; background:#ecfdf5; } .badge.b { color:#1d4ed8; background:#eff6ff; }
.kpi .v .badge { font-size: 11.5px; letter-spacing: 0; }

/* 자동 요약 · 확인 필요 항목 */
.sumlist { margin:0; padding:0; list-style:none; font-size:14px; line-height:1.75; color:#1f2937; }
.sumlist li { padding-left:16px; position:relative; margin: 2px 0; }
.sumlist li:before { content:""; position:absolute; left:3px; top:10px; width:6px; height:6px;
  background:#3b82f6; border-radius:9999px; }
.sumlist b { color:#111827; }
.alerts { list-style:none; margin:0; padding:0; font-size:13px; color:#1f2937; }
.alerts li { display:flex; gap:8px; align-items:flex-start; padding:7px 0; border-bottom:1px solid #f3f4f6; }
.alerts li:last-child { border-bottom:0; }

/* 탭: 밑줄 스타일 */
[data-testid="stTab"] p { font-size: 14px !important; font-weight: 500; }
[role="tabpanel"] { padding-top: 12px; }
</style>
""".replace("FONT", _FONT)

# ------------------------------------------------------------------ 그래프(plotly) 모양
# 그래프 오른쪽 위 도구 막대 설정: 로고 숨김, PNG 저장 2배 크기, 잘 안 쓰는 버튼 제거
CHART_CFG = {"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2},
             "modeBarButtonsToRemove": ["lasso2d", "select2d", "zoomIn2d", "zoomOut2d", "autoScale2d"]}


def apply() -> None:
    """추가 스타일을 화면에 적용합니다. app.py 에서 한 번 부릅니다."""
    st.markdown(_CSS, unsafe_allow_html=True)


def base_layout(fig, h=300, yfmt=None):
    """plotly 그래프에 공통 모양(글꼴, 여백, 범례, 옅은 격자, 둥근 막대)을 입힙니다."""
    fig.update_layout(height=h, margin=dict(l=4, r=4, t=28, b=4), hovermode="x unified",
                      legend=dict(orientation="h", y=1.14, x=0, font=dict(size=12, color="#374151"),
                                  traceorder="normal"),
                      font=dict(family=_FONT.replace('"', ""), size=12, color="#6b7280"),
                      plot_bgcolor="#ffffff", paper_bgcolor="rgba(0,0,0,0)", bargap=.35,
                      barcornerradius=4, colorway=PALETTE,
                      hoverlabel=dict(bgcolor="#ffffff", bordercolor="#e5e7eb", font_color="#111827"))
    fig.update_xaxes(showgrid=False, type="category", showline=False, ticks="")
    fig.update_yaxes(gridcolor="#f3f4f6", zeroline=False, showline=False, tickformat=yfmt or ",~f")
    return fig


def _money_axis(fig) -> None:
    """세로축 눈금을 억/만 단위로 바꿉니다. 쌓은 막대는 합계 높이까지 고려합니다."""
    ys = [list(tr.y or []) for tr in fig.data]
    values = [v for y in ys for v in y]
    if fig.layout.barmode == "stack" and ys:
        n = max(len(y) for y in ys)
        values += [sum((y[i] or 0) for y in ys if i < len(y) and y[i] == y[i]) for i in range(n)]
    has_bar = any(tr.type == "bar" for tr in fig.data)  # 막대는 0부터, 꺾은선은 데이터 범위에 맞춤
    ticks, text = money_ticks(values, from_zero=has_bar)
    if ticks:
        fig.update_yaxes(tickvals=ticks, ticktext=text)


def show_chart(fig, h=300, yfmt=None, legend_right=False, money=False) -> None:
    """공통 모양을 입혀서 그래프를 화면에 그립니다.

    legend_right=True: 항목이 많아 범례가 그래프를 가릴 때, 범례를 오른쪽 세로로 옮깁니다.
    money=True: 금액 그래프. 세로축을 '2억, 4억' 처럼 표시합니다.
    """
    base_layout(fig, h, yfmt)
    if legend_right:
        fig.update_layout(legend=dict(orientation="v", x=1.01, y=1, traceorder="reversed"))
    if money:
        _money_axis(fig)
    st.plotly_chart(fig, width="stretch", config=CHART_CFG)


def show_table(raw: pd.DataFrame, kinds: dict | str, filename: str) -> None:
    """'항목 × 월' 숫자 표를 보기 좋게 보여주고, 아래에 '엑셀로 받기' 버튼을 붙입니다.

    raw: 원래 숫자 표 (엑셀 파일에는 이 숫자가 그대로 들어감)
    kinds: 줄마다 표시 종류 {항목: "money"/"count"/"ratio"}, 또는 모든 줄에 같은 종류 "money"
    표 기능: 첫 열(항목 이름) 고정, 열 머리글 눌러 정렬, 오른쪽 위 돋보기로 검색.
    """
    shown = pd.DataFrame(
        [[format_value(v, kinds if isinstance(kinds, str) else kinds.get(name, "money")) for v in row]
         for name, row in raw.iterrows()],
        index=raw.index, columns=[month_label(m) for m in raw.columns])
    st.dataframe(shown, width="stretch")
    buf = io.BytesIO()
    out = raw.copy()
    out.columns = [str(c) for c in out.columns]
    out.to_excel(buf, sheet_name="통계")
    st.download_button("⬇ 엑셀로 받기", buf.getvalue(), file_name=f"{filename}.xlsx", key=f"dl_{filename}",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def panel_title(title: str, sub: str = "") -> None:
    """패널(카드) 제목 + 오른쪽 작은 설명."""
    st.markdown(f'<div class="ptitle"><span>{escape(title)}</span><small>{escape(sub)}</small></div>',
                unsafe_allow_html=True)


def month_label(m) -> str:
    """그래프 x축용 짧은 월 이름. 예) 2026-09 → '26.09'"""
    return f"{m.year % 100}.{m.month:02d}"
