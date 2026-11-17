"""데이터 품질 검사: '미입력 의심' 0 찾기.

병원 엑셀에는 진짜 0(예: 한방 외래 환자 없음)과 '아직 안 적은 0'이 섞여 있습니다.
그래서 0이 나올 수 없는 항목(config.NEVER_ZERO)만 골라서, 그 항목이 0이면 '미입력 의심'으로 봅니다.
값을 지우지는 않고, 그래프·계산에서만 빈칸으로 다룹니다. (원래 값은 Suspect.value 에 남음)
"""
from dataclasses import dataclass

import pandas as pd

from core import monthly


@dataclass(frozen=True)
class Suspect:
    name: str        # 화면에 보여줄 이름. 예) '인건비'
    labels: tuple    # 엑셀 항목 이름들
    month: object    # 해당 달 (pd.Period)
    value: float     # 엑셀에 적힌 원래 값 (0)


def find_suspects(df: pd.DataFrame, specs: list) -> list[Suspect]:
    """0이 나올 수 없는 항목이 0인 칸을 모두 찾습니다."""
    found = []
    for name, labels in specs:
        try:
            idx = monthly.find_index(df, *labels)
        except KeyError:
            continue
        for m in monthly.month_columns(df):
            if df.at[idx, m] == 0:
                found.append(Suspect(name, tuple(labels), m, 0.0))
    return found


def blank_suspects(df: pd.DataFrame, suspects: list[Suspect]) -> pd.DataFrame:
    """'미입력 의심' 칸을 빈칸(NaN)으로 바꾼 복사본을 돌려줍니다. 원본은 그대로."""
    out = df.copy()
    for s in suspects:
        out.at[monthly.find_index(out, *s.labels), s.month] = float("nan")
    out.attrs["suspects"] = list(suspects)  # 화면에서 '미입력 의심' 표시할 때 씀
    return out


def suspects_in(df: pd.DataFrame, months: list) -> list[Suspect]:
    """표에 기록된 '미입력 의심' 중 주어진 달에 해당하는 것만."""
    wanted = set(months)
    return [s for s in df.attrs.get("suspects", []) if s.month in wanted]


def is_suspect(df: pd.DataFrame, labels: tuple, month) -> bool:
    """이 항목·이 달이 '미입력 의심'인지."""
    return any(s.labels == tuple(labels) and s.month == month for s in df.attrs.get("suspects", []))
