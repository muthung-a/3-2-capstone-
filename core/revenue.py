"""수익 관련 계산: 재활치료 분류, 금액 그래프 눈금."""
import math

import pandas as pd

from core import monthly


def rehab_split(df: pd.DataFrame, months: list) -> pd.DataFrame:
    """재활치료 매출을 '급여 재활치료 / 도수치료 / 크라이오' 세 줄로 묶습니다.

    엑셀의 재활치료 구역은 MM105 같은 급여 코드 줄들 + 도수치료(급여·비급여·관리급여) + 크라이오로 되어 있습니다.
    """
    frame = monthly.section_frame(df, "재활치료", months)
    group = []
    for name in frame.index:
        if name.startswith("도수치료"):
            group.append("도수치료")
        elif name.startswith("크라이오"):
            group.append("크라이오")
        else:
            group.append("급여 재활치료")
    out = frame.groupby(group, sort=False).sum(min_count=1)
    return out.reindex([g for g in ("급여 재활치료", "도수치료", "크라이오") if g in out.index])


def rehab_items(df: pd.DataFrame, month) -> pd.Series:
    """기준월의 급여 재활치료 항목별 금액 (큰 순서, 0·빈칸 제외). 이름 예) '중추신경계발달재활치료'"""
    frame = monthly.section_frame(df, "재활치료", [month])
    frame = frame[~frame.index.str.startswith(("도수치료", "크라이오"))]
    s = frame[month]
    s.index = [name.split(" ", 1)[-1] for name in s.index]  # 'MM105 중추신경…' → '중추신경…'
    return s[s > 0].sort_values(ascending=False)


def money_ticks(values: list, from_zero: bool = True) -> tuple[list, list]:
    """금액 그래프 세로축 눈금을 억/만 단위 글자로 만듭니다.

    예) 최대 8.5억 → 눈금 [0, 2.5억, 5억, 7.5억, 10억]
    from_zero=False: 꺾은선처럼 0부터 시작하지 않는 그래프용 (데이터 범위에 맞춤)
    돌려주는 값: (눈금 위치 목록, 눈금 글자 목록). 값이 없으면 ([], []).
    """
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not vals or max(vals) <= 0:
        return [], []
    vmax = max(vals)
    vmin = min(0, min(vals)) if from_zero else min(vals)
    raw = (vmax - vmin) / 4 or vmax / 4
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.floor(vmin / step) * step
    ticks = [start + i * step for i in range(int((vmax - start) // step) + 2)]
    if vmax >= 1e8:
        unit, div = "억", 1e8
    elif vmax >= 1e4:
        unit, div = "만", 1e4
    else:  # 식단가처럼 1만 원 미만은 원 단위로
        unit, div = "원", 1

    def label(v):
        x = v / div
        if v == 0:
            return "0"
        return f"{x:,.0f}{unit}" if abs(x - round(x)) < 1e-9 else f"{x:,.1f}{unit}"
    return ticks, [label(v) for v in ticks]
