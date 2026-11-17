"""KPI(핵심 지표) 계산과 숫자 표시 형식.

기준월 값, 전월 값, 전월 대비 증감을 계산합니다. 화면 코드는 없습니다.
"""
import math
from dataclasses import dataclass

import pandas as pd

from core import monthly, quality


@dataclass
class Kpi:
    label: str        # 카드 이름
    kind: str         # "count" / "ratio" / "money"
    value: float      # 기준월 값
    prev: float       # 전월 값
    change: float     # 전월 대비 증감 (ratio 는 %p, 나머지는 %)
    history: list     # 최근 13개월 값 (미니 추이 그래프용)
    suspect: bool = False  # 기준월 값이 '미입력 의심'(0이 나올 수 없는데 0)인지
    yoy_change: float = float("nan")  # 전년 동월 대비 증감 (ratio 는 %p)


def _isnan(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def change_between(value: float, prev: float, kind: str) -> float:
    """전월 대비 증감. 비율은 %p(차이), 나머지는 %(증감률)."""
    if _isnan(value) or _isnan(prev):
        return float("nan")
    if kind == "ratio":
        return (value - prev) * 100
    if prev == 0:
        return float("nan")
    return (value - prev) / abs(prev) * 100


def build_kpis(df: pd.DataFrame, month, specs: list) -> list[Kpi]:
    """specs(config.KPIS) 목록대로 기준월 KPI를 계산합니다. 없는 항목은 건너뜁니다."""
    months = monthly.available_months(df)
    idx = months.index(month)
    prev_month = months[idx - 1] if idx > 0 else None
    result = []
    for label, labels, kind in specs:
        try:
            series = monthly.find_row(df, *labels)
        except KeyError:
            continue
        value = series[month]
        prev = series[prev_month] if prev_month is not None else float("nan")
        history = [series[m] for m in months[max(0, idx - 12): idx + 1]]
        suspect = quality.is_suspect(df, labels, month)
        yoy = series.get(month - 12, float("nan"))
        result.append(Kpi(label, kind, value, prev, change_between(value, prev, kind), history, suspect,
                          change_between(value, yoy, kind)))
    return result


def detail_frame(df: pd.DataFrame, months: list, specs: list) -> tuple[pd.DataFrame, dict]:
    """상세 통계표용: specs [(표 이름, 항목 이름들, 종류)] 대로 '항목 × 월' 숫자 표를 만듭니다.

    돌려주는 값: (숫자 표, {표 이름: 종류}). 없는 항목은 건너뜁니다.
    """
    rows, kinds = {}, {}
    for name, labels, kind in specs:
        try:
            rows[name] = monthly.find_row(df, *labels)[months]
        except KeyError:
            continue
        kinds[name] = kind
    frame = pd.DataFrame([r.tolist() for r in rows.values()], index=list(rows), columns=months, dtype=float)
    return frame, kinds  # 항목이 하나도 없어도 월 열은 있는 빈 표


def format_value(value: float, kind: str) -> str:
    """화면에 보여줄 글자로 바꿉니다. 예) 437857330 → '4.38억', 0.975 → '97.5%', 174 → '174명'"""
    if _isnan(value):
        return "-"
    if kind == "ratio":
        return f"{value * 100:.1f}%"
    if kind == "count":
        return f"{value:,.0f}명"
    if kind == "number":  # 단위를 모르는 항목 (사용자 정의 통계)
        return f"{value:,.0f}" if abs(value) >= 100 else f"{value:,.2f}"
    if abs(value) >= 1e8:
        return f"{value / 1e8:,.2f}억"
    if abs(value) >= 1e4:
        return f"{value / 1e4:,.0f}만"
    return f"{value:,.0f}원"
