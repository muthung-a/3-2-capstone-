# -*- coding: utf-8 -*-
"""
심사청구 통계보고서 자동화 - 프로토타입 v2 (경대재활요양병원 연계 캡스톤디자인 과제)

실행 방법:
    pip install -r requirements.txt
    streamlit run app.py

※ 이 프로토타입은 더미(가상) 데이터 기준으로 작동합니다.
   실제 병원 데이터를 받으면 REQUIRED_COLUMNS와 집계 로직을 실제 컬럼명에 맞게 조정해야 합니다.

v2에서 추가된 것:
    1) 자동 인사이트 문장 (사람이 쓴 것처럼 통계를 문장으로 요약)
    2) PDF 요약 보고서 다운로드 (엑셀 외에 PDF 형태로도 결과물 제공)
    3) 월별 추이 차트를 보기 쉬운 이중축 그래프로 정리
"""

import io
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------------------------
st.set_page_config(page_title="심사청구 통계보고서 자동화", layout="wide")

# 업로드 파일에 반드시 있어야 하는 컬럼 (더미 데이터 기준. 실제 데이터 확보 후 수정 필요)
REQUIRED_COLUMNS = [
    "청구월", "청구번호", "진료과", "환자구분", "급여구분",
    "청구일자", "청구금액", "심사결과", "조정삭감금액", "조정삭감사유",
]

RESULT_ORDER = ["승인", "조정", "삭감", "반려"]
RESULT_COLORS = {
    "승인": "#2E7D32",
    "조정": "#F9A825",
    "삭감": "#C62828",
    "반려": "#757575",
}

# 한글 PDF를 위한 폰트 경로 (같은 폴더의 fonts/ 디렉토리에 폰트 파일이 있어야 함)
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "NanumGothic.ttf")
FONT_BOLD_PATH = os.path.join(FONT_DIR, "NanumGothicBold.ttf")


# ---------------------------------------------------------------------------
# 데이터 로드 & 검증
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file, sheet_name="청구데이터")
        except ValueError:
            df = pd.read_excel(file, sheet_name=0)
    return df


def validate(df: pd.DataFrame) -> list[str]:
    errors = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"필수 컬럼 누락: {', '.join(missing)}")
        return errors  # 컬럼이 없으면 이후 검증은 의미 없음

    if df["청구월"].isna().any():
        errors.append("청구월이 비어 있는 행이 있습니다.")
    if (df["청구금액"] < 0).any():
        errors.append("청구금액에 음수 값이 있습니다.")
    bad_result = set(df["심사결과"].dropna().unique()) - set(RESULT_ORDER)
    if bad_result:
        errors.append(f"심사결과에 알 수 없는 값이 있습니다: {bad_result}")

    return errors


# ---------------------------------------------------------------------------
# 집계 함수 (여기가 실제 통계보고서 로직의 핵심 - 항목 추가/변경 시 이 부분만 수정)
# ---------------------------------------------------------------------------
def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("청구월").agg(
        청구건수=("청구번호", "count"),
        청구총액=("청구금액", "sum"),
        조정삭감총액=("조정삭감금액", "sum"),
    ).reset_index()
    g["조정삭감률(%)"] = (g["조정삭감총액"] / g["청구총액"] * 100).round(2)
    return g


def dept_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("진료과").agg(
        청구건수=("청구번호", "count"),
        청구총액=("청구금액", "sum"),
        조정삭감총액=("조정삭감금액", "sum"),
    ).reset_index()
    g["조정삭감률(%)"] = (g["조정삭감총액"] / g["청구총액"] * 100).round(2)
    return g.sort_values("청구총액", ascending=False)


def result_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("심사결과").size().reindex(RESULT_ORDER, fill_value=0).reset_index(name="건수")
    g["비율(%)"] = (g["건수"] / g["건수"].sum() * 100).round(1)
    return g


def reason_summary(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["조정삭감사유"].astype(str).str.strip() != ""]
    if sub.empty:
        return pd.DataFrame(columns=["조정삭감사유", "건수", "금액"])
    g = sub.groupby("조정삭감사유").agg(
        건수=("청구번호", "count"),
        금액=("조정삭감금액", "sum"),
    ).reset_index().sort_values("건수", ascending=False)
    return g


# ---------------------------------------------------------------------------
# 자동 인사이트 문장 생성
# (사람이 보고서에 쓸 법한 한 줄 코멘트를 통계 수치 기반으로 자동 생성)
# ---------------------------------------------------------------------------
def generate_insights(monthly: pd.DataFrame, dept: pd.DataFrame) -> list[str]:
    insights = []
    if len(monthly) == 0:
        return ["표시할 데이터가 없습니다."]

    m = monthly.sort_values("청구월").reset_index(drop=True)

    # 1) 최신월 vs 이전월 비교
    if len(m) >= 2:
        last, prev = m.iloc[-1], m.iloc[-2]
        diff = last["조정삭감률(%)"] - prev["조정삭감률(%)"]
        direction = "상승" if diff > 0 else ("하락" if diff < 0 else "동일")
        insights.append(
            f"📈 {last['청구월']} 조정·삭감률은 {last['조정삭감률(%)']}%로, "
            f"전월({prev['조정삭감률(%)']}%) 대비 {abs(diff):.2f}%p {direction}했습니다."
        )
        claim_diff = last["청구건수"] - prev["청구건수"]
        c_dir = "증가" if claim_diff > 0 else ("감소" if claim_diff < 0 else "동일")
        insights.append(
            f"🧾 {last['청구월']} 청구건수는 {last['청구건수']:,}건으로, "
            f"전월 대비 {abs(claim_diff):,}건 {c_dir}했습니다."
        )
    else:
        only = m.iloc[-1]
        insights.append(f"📈 {only['청구월']} 조정·삭감률은 {only['조정삭감률(%)']}%입니다.")

    # 2) 전체 기간 최고/최저 조정삭감률 월
    max_row = m.loc[m["조정삭감률(%)"].idxmax()]
    min_row = m.loc[m["조정삭감률(%)"].idxmin()]
    insights.append(
        f"⚠️ 조회 기간 중 조정·삭감률이 가장 높았던 달은 {max_row['청구월']}({max_row['조정삭감률(%)']}%), "
        f"가장 낮았던 달은 {min_row['청구월']}({min_row['조정삭감률(%)']}%)입니다."
    )

    # 3) 진료과 중 조정삭감률 최고
    if len(dept) > 0:
        worst_dept = dept.loc[dept["조정삭감률(%)"].idxmax()]
        insights.append(
            f"🏥 진료과 중에서는 '{worst_dept['진료과']}'의 조정·삭감률이 "
            f"{worst_dept['조정삭감률(%)']}%로 가장 높아, 청구 시 유의가 필요합니다."
        )

    return insights


# ---------------------------------------------------------------------------
# 엑셀 보고서 생성
# ---------------------------------------------------------------------------
def build_excel_report(raw, monthly, dept, result, reason, insights) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        cover = pd.DataFrame({
            "항목": ["보고서명", "생성일시", "대상 기간", "총 청구건수"],
            "값": [
                "심사청구 통계보고서 (자동생성)",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                f"{raw['청구월'].min()} ~ {raw['청구월'].max()}",
                len(raw),
            ],
        })
        cover.to_excel(writer, sheet_name="표지", index=False)

        insight_df = pd.DataFrame({"자동 요약 코멘트": insights})
        insight_df.to_excel(writer, sheet_name="요약코멘트", index=False)

        monthly.to_excel(writer, sheet_name="월별통계", index=False)
        dept.to_excel(writer, sheet_name="진료과별통계", index=False)
        result.to_excel(writer, sheet_name="심사결과통계", index=False)
        reason.to_excel(writer, sheet_name="조정삭감사유통계", index=False)
        raw.to_excel(writer, sheet_name="원본데이터", index=False)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF 요약 보고서 생성
# ---------------------------------------------------------------------------
def _register_korean_font():
    """한글 폰트를 reportlab에 등록. 폰트 파일이 없으면 False 반환."""
    if "NanumGothic" in pdfmetrics.getRegisteredFontNames():
        return True
    if not (os.path.exists(FONT_REGULAR_PATH) and os.path.exists(FONT_BOLD_PATH)):
        return False
    pdfmetrics.registerFont(TTFont("NanumGothic", FONT_REGULAR_PATH))
    pdfmetrics.registerFont(TTFont("NanumGothic-Bold", FONT_BOLD_PATH))
    return True


def build_pdf_report(raw, monthly, dept, result, insights) -> bytes:
    has_korean_font = _register_korean_font()
    font_name = "NanumGothic" if has_korean_font else "Helvetica"
    font_bold = "NanumGothic-Bold" if has_korean_font else "Helvetica-Bold"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title_KR", parent=styles["Title"], fontName=font_bold, fontSize=18)
    h2_style = ParagraphStyle("H2_KR", parent=styles["Heading2"], fontName=font_bold, fontSize=13,
                               spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle("Body_KR", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=15)

    elements = []
    elements.append(Paragraph("심사청구 통계보고서 (자동생성)", title_style))
    elements.append(Paragraph(
        f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
        f"대상 기간: {raw['청구월'].min()} ~ {raw['청구월'].max()} · 총 청구건수: {len(raw):,}건",
        body_style,
    ))
    elements.append(Spacer(1, 8))

    # ---- 요약 코멘트 ----
    # PDF용 폰트에는 이모지 글리프가 없어 화면(Streamlit)용 이모지 접두어를 제거하고 출력
    import re
    elements.append(Paragraph("1. 요약", h2_style))
    for line in insights:
        clean_line = re.sub(r"^[^\w가-힣]+", "", line).strip()
        elements.append(Paragraph(f"• {clean_line}", body_style))
    elements.append(Spacer(1, 6))

    # ---- 월별 통계표 ----
    elements.append(Paragraph("2. 월별 통계", h2_style))
    table_data = [list(monthly.columns)] + monthly.astype(str).values.tolist()
    t = Table(table_data, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))

    # ---- 진료과별 통계표 ----
    elements.append(Paragraph("3. 진료과별 통계", h2_style))
    table_data2 = [list(dept.columns)] + dept.astype(str).values.tolist()
    t2 = Table(table_data2, hAlign="LEFT")
    t2.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 10))

    # ---- 심사결과 분포표 ----
    elements.append(Paragraph("4. 심사결과 분포", h2_style))
    table_data3 = [list(result.columns)] + result.astype(str).values.tolist()
    t3 = Table(table_data3, hAlign="LEFT")
    t3.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
    ]))
    elements.append(t3)

    doc.build(elements)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("📊 심사청구 통계보고서 자동화 (프로토타입 v2)")
st.caption("경대재활요양병원 연계 캡스톤디자인 과제 · 데모용 — 실제 데이터 연동 전 단계")

with st.sidebar:
    st.header("1️⃣ 데이터 업로드")
    uploaded = st.file_uploader(
        "청구 데이터 파일 (xlsx 또는 csv)",
        type=["xlsx", "csv"],
        help="더미 데이터 파일(심사청구_더미데이터_2026상반기.xlsx)을 그대로 업로드해보세요.",
    )
    st.markdown("---")
    st.markdown("**필수 컬럼**\n\n" + "\n".join(f"- {c}" for c in REQUIRED_COLUMNS))

if uploaded is None:
    st.info("왼쪽에서 파일을 업로드하면 통계가 자동으로 계산됩니다. "
            "테스트하려면 더미 데이터 엑셀 파일을 업로드해보세요.")
    st.stop()

try:
    raw_df = load_data(uploaded)
except Exception as e:
    st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
    st.stop()

errors = validate(raw_df)
if errors:
    st.error("데이터 검증에 실패했습니다:")
    for e in errors:
        st.write(f"- {e}")
    st.stop()

st.success(f"✅ 데이터 검증 통과 — 총 {len(raw_df):,}건 로드됨")

# ---- 필터 ----
st.header("2️⃣ 필터")
col1, col2, col3 = st.columns(3)
with col1:
    months = sorted(raw_df["청구월"].unique())
    sel_months = st.multiselect("청구월", months, default=months)
with col2:
    depts = sorted(raw_df["진료과"].unique())
    sel_depts = st.multiselect("진료과", depts, default=depts)
with col3:
    types = sorted(raw_df["환자구분"].unique())
    sel_types = st.multiselect("환자구분", types, default=types)

df = raw_df[
    raw_df["청구월"].isin(sel_months)
    & raw_df["진료과"].isin(sel_depts)
    & raw_df["환자구분"].isin(sel_types)
]

if df.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

m = monthly_summary(df)
d = dept_summary(df)
r = result_summary(df)
rs = reason_summary(df)
insights = generate_insights(m, d)

# ---- 요약 카드 ----
st.header("3️⃣ 요약")
total_claims = len(df)
total_amount = df["청구금액"].sum()
total_adj = df["조정삭감금액"].sum()
adj_rate = round(total_adj / total_amount * 100, 2) if total_amount else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("총 청구건수", f"{total_claims:,} 건")
k2.metric("총 청구금액", f"{total_amount:,.0f} 원")
k3.metric("총 조정·삭감금액", f"{total_adj:,.0f} 원")
k4.metric("조정·삭감률", f"{adj_rate} %")

# ---- 자동 인사이트 ----
st.subheader("🤖 자동 요약 코멘트")
for line in insights:
    st.markdown(f"- {line}")

# ---- 차트 ----
st.header("4️⃣ 통계 차트")

c1, c2 = st.columns(2)
with c1:
    st.subheader("월별 청구건수 & 조정삭감률 추이")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=m["청구월"], y=m["청구건수"], name="청구건수", marker_color="#4472C4"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=m["청구월"], y=m["조정삭감률(%)"], name="조정삭감률(%)",
                    mode="lines+markers", line=dict(color="#C62828", width=3)),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="청구건수", secondary_y=False)
    fig.update_yaxes(title_text="조정삭감률(%)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("심사결과 분포")
    fig2 = px.pie(r, names="심사결과", values="건수",
                   color="심사결과", color_discrete_map=RESULT_COLORS, hole=0.4)
    st.plotly_chart(fig2, use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.subheader("진료과별 청구총액")
    fig3 = px.bar(d, x="진료과", y="청구총액", text_auto=".2s")
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("조정·삭감 사유별 건수")
    if rs.empty:
        st.write("조정·삭감 건이 없습니다.")
    else:
        fig4 = px.bar(rs, x="조정삭감사유", y="건수", text_auto=True)
        st.plotly_chart(fig4, use_container_width=True)

# ---- 상세 테이블 ----
st.header("5️⃣ 상세 통계표")
tab1, tab2, tab3 = st.tabs(["월별 통계", "진료과별 통계", "원본 데이터"])
with tab1:
    st.dataframe(m, use_container_width=True)
with tab2:
    st.dataframe(d, use_container_width=True)
with tab3:
    st.dataframe(df, use_container_width=True)

# ---- 보고서 다운로드 ----
st.header("6️⃣ 보고서 다운로드")
dl1, dl2 = st.columns(2)

with dl1:
    excel_bytes = build_excel_report(df, m, d, r, rs, insights)
    st.download_button(
        "📥 Excel 보고서 다운로드 (상세 데이터 포함)",
        data=excel_bytes,
        file_name=f"심사청구_통계보고서_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

with dl2:
    pdf_bytes = build_pdf_report(df, m, d, r, insights)
    st.download_button(
        "📄 PDF 요약 보고서 다운로드 (인쇄/공유용)",
        data=pdf_bytes,
        file_name=f"심사청구_통계보고서_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

st.caption("Excel 보고서는 표지/요약코멘트/월별·진료과별·심사결과·조정삭감사유 통계/원본데이터로 구성되며, "
           "PDF 보고서는 인쇄나 공유가 필요할 때 쓰는 요약본입니다.")
