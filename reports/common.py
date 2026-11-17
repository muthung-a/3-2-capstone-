"""보고서(엑셀·인쇄용)에 공통으로 들어가는 내용 모으기. streamlit 은 쓰지 않습니다."""
import re

import pandas as pd

import config
from core import cost, kpi, summary
from core.view import View


def plain(text: str) -> str:
    """<b> 같은 표시를 뺀 글자."""
    return re.sub(r"<[^>]+>", "", text)


def kpi_table(v: View) -> pd.DataFrame:
    """핵심 지표 표: 항목, 당월, 전월, 전월 대비, 전년 대비 (글자로 꾸민 값)."""
    rows = []
    for k in kpi.build_kpis(v.df, v.month, config.KPIS):
        unit = "%p" if k.kind == "ratio" else "%"
        fmt = lambda p: "-" if p != p else f"{p:+.1f}{unit}"
        rows.append({"항목": k.label,
                     "당월": "0 (미입력 의심)" if k.suspect else kpi.format_value(k.value, k.kind),
                     "전월": kpi.format_value(k.prev, k.kind),
                     "전월 대비": "-" if k.suspect else fmt(k.change),
                     "전년 대비": "-" if k.suspect else fmt(k.yoy_change)})
    return pd.DataFrame(rows)


def sections(v: View) -> list[tuple[str, pd.DataFrame, dict | str]]:
    """상세 통계표 묶음: [(제목, 숫자 표, 표시 종류)]."""
    patient, pk = kpi.detail_frame(v.df, v.months, config.PATIENT_DETAIL)
    revenue, rk = kpi.detail_frame(v.df, v.months, config.REVENUE_DETAIL)
    costs = cost.cost_breakdown(v.df, v.months, config.COST_ITEMS)
    return [("환자·병상", patient, pk), ("수익", revenue, rk), ("비용", costs, "money")]


def summary_and_alerts(v: View) -> tuple[list[str], list[summary.Alert]]:
    return summary.summary_lines(v.df, v.month), summary.alerts(v.df, v.month, v.warn_pct, v.bed_target)
