"""왼쪽 사이드바: 파일, 기준월, 조회기간, 적정선·경고 기준, 보고서 내보내기."""
import io

import streamlit as st

import config
from core import monthly, quality, settings
from core.view import View
from reports import excel_report, html_report


@st.cache_data(show_spinner="엑셀 읽는 중…")
def _load(data: bytes):
    """엑셀 내용(bytes)을 표로 읽습니다. 같은 파일은 다시 읽지 않고 기억해 둡니다."""
    return monthly.load_monthly(io.BytesIO(data))


def _pick_file():
    """업로드한 파일이 있으면 그것을, 없으면 data/ 폴더의 파일을 고르게 합니다."""
    uploaded = st.file_uploader("엑셀 파일 올리기", type=["xlsx"])
    if uploaded is not None:
        return uploaded.name, uploaded.getvalue()
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        return None
    path = st.selectbox("또는 data 폴더에서 선택", files, format_func=lambda p: p.name)
    return path.name, path.read_bytes()


def _options(saved: dict, months: list):
    """기준월·조회기간·적정선·경고 기준을 고르고, 바뀐 설정은 파일에 저장합니다."""
    st.markdown('<div class="side-h">조회 조건</div>', unsafe_allow_html=True)
    month = st.selectbox("기준월", months[::-1], format_func=lambda m: f"{m.year}년 {m.month}월")
    span = st.segmented_control("조회기간", config.SPAN_CHOICES, default=saved["span"],
                                format_func=lambda n: f"{n}개월") or saved["span"]
    st.markdown('<div class="side-h">환경설정</div>', unsafe_allow_html=True)
    bed = st.number_input("병상가동율 적정선(%)", 50.0, 100.0, float(saved["bed_target"]), 0.5)
    warn = st.number_input("확인 필요 기준 (12개월 평균 대비 ±%)", 1.0, 100.0, float(saved["warn_pct"]), 1.0)
    new = dict(saved, span=span, bed_target=bed, warn_pct=warn)
    if new != saved:
        settings.save(config.SETTINGS_PATH, new)
    return month, new


def render() -> View | None:
    """사이드바를 그리고 지금 보고 있는 조건(View)을 돌려줍니다. 파일이 없으면 None."""
    with st.sidebar:
        st.markdown('<div class="brand"><i>📊</i><div><b>경영통계</b><span>요양병원 월별 통계 자동화</span>'
                    '</div></div><div class="side-h">데이터</div>', unsafe_allow_html=True)
        picked = _pick_file()
        if picked is None:
            st.caption(f"버전 {config.VERSION}")
            return None
        name, data = picked
        try:
            df = _load(data)
        except Exception:  # 양식이 다른 파일 등
            st.error(f"'{name}'을(를) 읽을 수 없습니다. '{config.MONTHLY_SHEET}' 시트가 있는지 확인하세요.")
            return None
        # 0이 나올 수 없는 항목이 0인 칸 → '미입력 의심'으로 표시하고 그래프에서는 빈칸 처리
        df = quality.blank_suspects(df, quality.find_suspects(df, config.NEVER_ZERO))
        all_months = monthly.available_months(df)
        if not all_months:
            st.error("값이 들어 있는 달이 없습니다.")
            return None
        st.caption(f"{name} · {all_months[0]} ~ {all_months[-1]}")
        month, opts = _options(settings.load(config.SETTINGS_PATH), all_months)
    return View(df=df, month=month, months=monthly.recent_months(df, month, opts["span"]),
                bed_target=opts["bed_target"], warn_pct=opts["warn_pct"], file_name=name, settings=opts)


def render_exports(v: View) -> None:
    """사이드바 아래쪽: 보고서 내보내기 버튼 + 보안 안내."""
    with st.sidebar:
        st.markdown('<div class="side-h">보고서 내보내기</div>', unsafe_allow_html=True)
        stamp = f"{v.month.year}-{v.month.month:02d}"
        st.download_button("📥 엑셀 보고서", excel_report.build(v), f"경영통계보고서_{stamp}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        st.download_button("🖨 인쇄용 보고서 (PDF 저장)", html_report.build(v).encode("utf-8"),
                           f"경영통계보고서_{stamp}.html", "text/html", width="stretch",
                           help="받은 파일을 열고 [인쇄] → 'PDF로 저장'을 고르면 PDF가 됩니다.")
        st.caption("그래프는 오른쪽 위 📷 아이콘으로 이미지(PNG) 저장")
        st.info("🔒 이 PC 안에서만 처리 · 외부 전송 없음\n\n생성형 AI에 병원 파일을 올리지 마세요.")
        st.caption(f"버전 {config.VERSION}")
