"""자동 요약 문장과 '확인 필요 항목' 만들기.

화면(맨 위)과 보고서 내보내기에서 함께 씁니다. 문장 안의 <b>…</b> 는 굵은 글씨 표시입니다.
"""
import math
from dataclasses import dataclass

import pandas as pd

import config
from core import cost, monthly, quality
from core.kpi import format_value

TOTAL = ("총진료비", "합계", "소계")
CLAIM = ("총진료비", "청구금액(입원+외래)", "소계")
INSURANCE = ["공단", "보호", "자보"]


@dataclass
class Alert:
    level: str   # "r"=빨강(주의), "y"=노랑(확인), "g"=초록(정상)
    badge: str   # 배지 글자. 예) '감소', '적정선 미달'
    text: str    # 설명


def _nan(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _val(df: pd.DataFrame, labels: tuple, m) -> float:
    """항목·달의 값. 없으면 NaN."""
    try:
        return float(monthly.find_row(df, *labels).get(m, float("nan")))
    except KeyError:
        return float("nan")


def pct(cur: float, base: float) -> float:
    """증감률(%). 비교할 수 없으면 NaN."""
    if _nan(cur) or _nan(base) or base == 0:
        return float("nan")
    return (cur - base) / abs(base) * 100


def fmt_p(p: float) -> str:
    """증감률 글자. 예) +3.2% / −1.5% / 비교불가"""
    return "비교불가" if _nan(p) else f"{'+' if p >= 0 else '−'}{abs(p):.1f}%"


def avg12(df: pd.DataFrame, labels: tuple, month) -> float:
    """기준월 직전 12개월 평균 (값 있는 달만)."""
    months = monthly.available_months(df)
    before = months[max(0, months.index(month) - 12): months.index(month)]
    vals = [_val(df, labels, m) for m in before]
    vals = [v for v in vals if not _nan(v)]
    return sum(vals) / len(vals) if vals else float("nan")


def summary_lines(df: pd.DataFrame, month) -> list[str]:
    """기준월 자동 요약 문장 목록."""
    P, Y = month - 1, month - 12
    money = lambda v: format_value(v, "money")
    lines = []
    tot = _val(df, TOTAL, month)
    if not _nan(tot):
        lines.append(f"{month.year}년 {month.month}월 총진료비는 <b>{money(tot)}</b>으로 전월 대비 "
                     f"{fmt_p(pct(tot, _val(df, TOTAL, P)))}, 전년 동월 대비 {fmt_p(pct(tot, _val(df, TOTAL, Y)))}입니다.")
    claim = _val(df, CLAIM, month)
    if not _nan(claim) and claim:
        parts = [(s, _val(df, ("총진료비", "청구금액(입원+외래)", s), month)) for s in INSURANCE]
        share = ", ".join(f"{s} {v / claim * 100:.1f}%" for s, v in parts if not _nan(v))
        lines.append(f"보험자 청구금액은 <b>{money(claim)}</b>(전월 대비 {fmt_p(pct(claim, _val(df, CLAIM, P)))})이며, "
                     f"{share} 비중입니다.")
        drops = [(s, v - _val(df, ("총진료비", "청구금액(입원+외래)", s), P)) for s, v in parts]
        drops = [(s, d) for s, d in drops if not _nan(d) and d < 0]
        if drops:
            s, d = min(drops, key=lambda x: x[1])
            lines.append(f"청구금액 감소 폭이 가장 큰 보험 구분은 <b>{s}</b>(전월 대비 {money(abs(d))} 감소)입니다.")
    bed = _val(df, ("병상가동율",), month)
    if not _nan(bed):
        prev = format_value(_val(df, ("병상가동율",), P), "ratio")
        lines.append(f"병상가동율은 <b>{bed:.1%}</b>(전월 {prev}), 평균 재원환자 "
                     f"{_val(df, ('평균재원환자수', '합계'), month):,.1f}명, 실입원 "
                     f"{_val(df, ('입원환자수', '실입원수'), month):,.0f}명 / 실퇴원 "
                     f"{_val(df, ('퇴원환자수', '실퇴원수'), month):,.0f}명입니다.")
    rehab = _val(df, ("재활치료", "소계"), month)
    if not _nan(rehab):
        lines.append(f"재활치료(급여)는 <b>{money(rehab)}</b>으로 전월 대비 "
                     f"{fmt_p(pct(rehab, _val(df, ('재활치료', '소계'), P)))}입니다.")
    costs = cost.cost_breakdown(df, [month], config.COST_ITEMS)[month]
    if costs.notna().any():
        missing = [s.name for s in quality.suspects_in(df, [month])]
        note = f" ({', '.join(missing)} 미입력 의심 — 합계에서 빠짐)" if missing else ""
        lines.append(f"주요 비용 합계는 <b>{money(costs.sum())}</b>{note}입니다.")
    return lines


def alerts(df: pd.DataFrame, month, warn_pct: float, bed_target: float) -> list[Alert]:
    """'확인 필요 항목' 목록. bed_target 은 % (예: 95.0)."""
    out = []
    bed = _val(df, ("병상가동율",), month)
    if not _nan(bed) and bed * 100 < bed_target:
        out.append(Alert("r", "적정선 미달", f"병상가동율 {bed:.1%} (적정선 {bed_target:.1f}%)"))
    for s in quality.suspects_in(df, [month]):
        out.append(Alert("y", "미입력 의심", f"{s.name} 값이 0 — 입력이 됐는지 확인"))
    for name, labels, kind in config.ALERT_ITEMS:
        cur, base = _val(df, labels, month), avg12(df, labels, month)
        p = pct(cur, base)
        if not _nan(p) and abs(p) >= warn_pct:
            out.append(Alert("r" if p < 0 else "y", "감소" if p < 0 else "증가",
                             f"{name} {format_value(cur, kind)} · 12개월 평균 대비 {fmt_p(p)}"))
    P = month - 1
    if P in monthly.month_columns(df):
        frame = monthly.section_frame(df, "재활치료", [P, month])
        for item, row in frame.iterrows():
            if not item[:1].isupper() or not item[:2].isalpha():  # 'MM105 …' 같은 수가코드 줄만
                continue
            prv, cur = row[P], row[month]
            p = pct(cur, prv)
            if not _nan(p) and abs(p) >= 30 and max(cur, prv) >= 5e6:
                out.append(Alert("r" if p < 0 else "y", "감소" if p < 0 else "증가",
                                 f"재활 {item} {format_value(cur, 'money')} · 전월 대비 {fmt_p(p)}"))
    order = {"r": 0, "y": 1, "g": 2}
    return sorted(out, key=lambda a: order[a.level]) or [Alert("g", "정상", "기준을 벗어난 항목이 없습니다.")]
