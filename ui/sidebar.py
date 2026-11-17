"""왼쪽 사이드바: 파일, 기준월, 조회기간, 적정선·경고 기준, 보고서 내보내기."""
import io

import streamlit as st

import config
from core import check, drugs, monthly, quality, sample, settings
from core.view import View
from reports import excel_report, html_report


@st.cache_data(show_spinner="엑셀 읽는 중…")
def _load(data: bytes):
    """엑셀 내용(bytes)을 표로 읽습니다. 같은 파일은 다시 읽지 않고 기억해 둡니다."""
    return monthly.load_monthly(io.BytesIO(data))


@st.cache_data(show_spinner="약품 처방 시트 읽는 중…")
def _load_drugs(data: bytes):
    """약품 처방 원 데이터 시트들(6, 7 …)을 읽습니다. 없거나 양식이 다르면 None."""
    try:
        return drugs.load_drugs(io.BytesIO(data))
    except Exception:  # 약품 시트는 없어도 나머지 화면은 그대로
        return None


@st.cache_data(show_spinner="시연용 가상 데이터 만드는 중…")
def _demo_file() -> bytes:
    """시연 모드용 가짜 엑셀 (core/sample.py). 개인 정보 형태 없음."""
    return sample.build_workbook()


def _pick_file():
    """올린 엑셀 파일 (이름, 내용). 아직 안 올렸으면 None.

    파일은 화면에서 올린 것만 씁니다. (폴더에 둔 엑셀을 자동으로 읽지 않음 → 어떤 파일을 쓰는지 사용자가 직접 고름)
    """
    uploaded = st.file_uploader("엑셀 파일 올리기", type=["xlsx"])
    if uploaded is None:
        return None
    return uploaded.name, uploaded.getvalue()


def _options(saved: dict, months: list, demo: bool = False):
    """기준월·조회기간·적정선·경고 기준을 고르고, 바뀐 설정은 파일에 저장합니다. (시연 모드는 저장 안 함)"""
    st.markdown('<div class="side-h">조회 조건</div>', unsafe_allow_html=True)
    month = st.selectbox("기준월 (분석할 달)", months[::-1], format_func=lambda m: f"{m.year}년 {m.month}월")
    # 라디오 버튼: 항상 하나가 선택된 상태 (버튼식은 다시 누르면 선택이 풀려서 헷갈림)
    choices = config.SPAN_CHOICES
    span = st.radio("조회기간 (그래프·표에 보여줄 개월 수)", choices, horizontal=True,
                    index=choices.index(saved["span"]) if saved["span"] in choices else 0,
                    format_func=lambda n: f"{n}개월")
    st.markdown('<div class="side-h">환경설정</div>', unsafe_allow_html=True)
    bed = st.number_input("병상가동율 적정선(%)", 50.0, 100.0, float(saved["bed_target"]), 0.5)
    warn = st.number_input("확인 필요 기준 (12개월 평균 대비 ±%)", 1.0, 100.0, float(saved["warn_pct"]), 1.0)
    new = dict(saved, span=span, bed_target=bed, warn_pct=warn)
    if new != saved and not demo:  # 시연판은 여러 사람이 함께 보므로 서버에 설정을 저장하지 않음
        settings.save(config.SETTINGS_PATH, new)
    return month, new


def _data_check(df) -> None:
    """데이터 점검: 프로그램이 쓰는 항목을 엑셀에서 찾았는지. 못 찾은 게 있으면 펼쳐서 보여줍니다."""
    items = check.check(df)
    missing = [i for i in items if not i.found]
    title = f"🔍 데이터 점검 · {len(items) - len(missing)}/{len(items)} 항목 찾음" + (" ⚠" if missing else " ✅")
    with st.expander(title, expanded=bool(missing)):
        if not missing:
            st.caption("프로그램이 쓰는 항목을 모두 찾았습니다.")
            return
        st.caption("아래 항목을 엑셀에서 찾지 못했습니다. 엑셀의 항목 이름을 맞추거나 config.py 의 이름을 고치면 됩니다.")
        st.dataframe([{"어디서": i.where, "찾는 이름": i.path} for i in missing], hide_index=True)


def render(demo: bool = False) -> View | None:
    """사이드바를 그리고 지금 보고 있는 조건(View)을 돌려줍니다. 파일이 없으면 None.

    demo=True (시연판): 파일 올리기 칸 없이 가짜 데이터로 바로 엽니다. 실제 데이터가 들어올 길을 막기 위함.
    """
    with st.sidebar:
        st.markdown('<div class="brand"><i>📊</i><div><b>경영통계</b><span>요양병원 월별 통계 자동화</span>'
                    '</div></div><div class="side-h">데이터</div>', unsafe_allow_html=True)
        if demo:
            st.info("🎬 **시연용** · 코드로 만든 가상 데이터입니다.\n\n실제 병원 데이터는 올릴 수 없습니다.")
            picked = ("시연용_가상데이터.xlsx", _demo_file())
        else:
            picked = _pick_file()
        if picked is None:
            st.caption(f"버전 {config.VERSION}")
            return None
        name, data = picked
        try:
            df = _load(data)
        except ValueError as err:  # 월별 통계표 시트를 못 찾음
            st.error(f"'{name}': {err}")
            return None
        except Exception as err:  # 엑셀이 아니거나 깨진 파일 등
            st.error(f"'{name}'을(를) 읽을 수 없습니다. ({type(err).__name__}) 엑셀(.xlsx) 파일인지 확인하세요.")
            return None
        if df.attrs.get("no_values"):
            st.error("숫자가 하나도 읽히지 않았습니다. 엑셀에서 파일을 열어 **저장**한 뒤 다시 올려 주세요. "
                     "(수식 결과가 저장되지 않은 파일일 수 있습니다)")
            return None
        # 0이 나올 수 없는 항목이 0인 칸 → '미입력 의심'으로 표시하고 그래프에서는 빈칸 처리
        df = quality.blank_suspects(df, quality.find_suspects(df, config.NEVER_ZERO))
        all_months = monthly.available_months(df)
        if not all_months:
            st.error("값이 들어 있는 달이 없습니다.")
            return None
        st.caption(f"{name} · 시트 '{df.attrs.get('sheet', '')}' · {all_months[0]} ~ {all_months[-1]}")
        _data_check(df)
        saved = dict(settings.DEFAULTS, favorites=[]) if demo else settings.load(config.SETTINGS_PATH)
        month, opts = _options(saved, all_months, demo)
    return View(df=df, month=month, months=monthly.recent_months(df, month, opts["span"]),
                bed_target=opts["bed_target"], warn_pct=opts["warn_pct"], file_name=name, settings=opts,
                drugs=_load_drugs(data), demo=demo)


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
        if v.demo:
            st.info("🎬 시연판입니다. 병원에서는 PC 설치형(실행.bat)을 쓰며, 데이터는 PC 밖으로 나가지 않습니다.")
        else:
            st.info("🔒 이 PC 안에서만 처리 · 외부 전송 없음\n\n생성형 AI에 병원 파일을 올리지 마세요.")
        st.caption(f"버전 {config.VERSION}")
