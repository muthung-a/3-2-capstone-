"""월별 경영 통계표('Sample data' 시트)를 읽어서 표(DataFrame)로 만듭니다.

엑셀 모양:
    A~E열 = 항목 이름 (대분류 → 중분류 → 소분류 → 세부 → 비고, 셀 병합 있음)
    F열~  = 월별 값 (1행에 날짜), 맨 끝에 '합계(최근1년)' 같은 요약 열
    2행   = 그 달의 일수

결과 표 모양:
    대분류 | 중분류 | 소분류 | 세부 | 비고 | 2022-05 | 2022-06 | ...
"""
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

import config

LABEL_COLS = ["대분류", "중분류", "소분류", "세부", "비고"]
_N_LABELS = len(LABEL_COLS)
_FIRST_DATA_ROW = 3  # 1행: 날짜, 2행: 일수, 3행부터 항목


def clean_label(value) -> str:
    """항목 이름 정리: 줄바꿈 제거, 한글 사이 공백 제거.

    예) '총\\n진\\n료\\n비' → '총진료비', '합   계' → '합계', '월말 재원환자수' → '월말재원환자수'
    """
    if value is None:
        return ""
    text = str(value).replace("\n", "").strip()
    text = re.sub(r"(?<=[가-힣])\s+(?=[가-힣])", "", text)  # 한글 사이 공백 제거
    return re.sub(r"\s+", " ", text)


def to_number(value):
    """숫자로 바꿉니다. 빈칸이나 ' - ' 같은 글자는 NaN(값 없음)으로."""
    if isinstance(value, bool):
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value)
    return float("nan")


def _fill_labels(rows: list[list]) -> list[list[str]]:
    """병합 셀 때문에 비어 있는 항목 이름을 위쪽 값으로 채웁니다.

    어떤 단계의 이름이 새로 나오면, 그보다 아래 단계는 초기화합니다.
    """
    current = [""] * _N_LABELS
    filled = []
    for row in rows:
        labels = [clean_label(v) for v in row[:_N_LABELS]]
        for level, text in enumerate(labels):
            if text:
                current[level] = text
                current[level + 1:] = [""] * (_N_LABELS - level - 1)
        filled.append(list(current))
    return filled


def _pseudonymize(labels: list[list[str]]) -> None:
    """이름이 들어 있는 구역(config.PSEUDONYM_SECTIONS)의 이름을 가명으로 바꿉니다."""
    for section, prefix in config.PSEUDONYM_SECTIONS.items():
        names: dict[str, str] = {}
        for row in labels:
            if row[0] != section:
                continue
            for level in range(1, _N_LABELS):
                name = row[level]
                if name and name != "합계":
                    names.setdefault(name, f"{prefix}_{len(names) + 1}")
                    row[level] = names[name]


def load_monthly(path: str | Path, sheet: str = config.MONTHLY_SHEET) -> pd.DataFrame:
    """엑셀 파일의 월별 통계표 시트를 읽어 표로 돌려줍니다."""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = [list(r) for r in wb[sheet].iter_rows(values_only=True)]
    finally:
        wb.close()

    header = rows[0]
    month_cols = [i for i, v in enumerate(header) if isinstance(v, datetime)]
    body = [r for r in rows[_FIRST_DATA_ROW - 1:] if any(clean_label(v) for v in r[:_N_LABELS])]

    labels = _fill_labels(body)
    _pseudonymize(labels)

    months = [pd.Timestamp(header[i]).to_period("M") for i in month_cols]
    values = [[to_number(r[i]) if i < len(r) else float("nan") for i in month_cols] for r in body]

    df = pd.concat([pd.DataFrame(labels, columns=LABEL_COLS),
                    pd.DataFrame(values, columns=months)], axis=1)
    return df


def month_columns(df: pd.DataFrame) -> list:
    """표에서 월 열만 골라 돌려줍니다."""
    return [c for c in df.columns if isinstance(c, pd.Period)]


def available_months(df: pd.DataFrame) -> list:
    """값이 하나라도 들어 있는 달만 돌려줍니다. (미래의 빈 달 제외)"""
    return [m for m in month_columns(df) if df[m].notna().any()]


def recent_months(df: pd.DataFrame, month, n: int) -> list:
    """기준월(month)까지 값이 있는 달 중 최근 n개월."""
    months = available_months(df)
    idx = months.index(month)
    return months[max(0, idx - n + 1): idx + 1]


def section_frame(df: pd.DataFrame, section: str, months: list, sub: str | tuple | None = None,
                  exclude: tuple = ("합계", "소계")) -> pd.DataFrame:
    """대분류 하나(필요하면 그 아래 단계까지)의 줄들을 '항목 × 월' 표로 꺼냅니다.

    예) section_frame(df, "월말재원환자수", months)
        → 행: 공단 / 보호 / 자보 (합계 줄은 exclude 로 뺌), 열: months
    예) section_frame(df, "청구금액", months, sub="합계")
        → 청구금액 > 합계 아래의 '의과 외래', '의과 입원' …
    예) section_frame(df, "간병", months, sub=("총수입", "보험종별"))
        → 간병 > 총수입 > 보험종별 아래의 '보험', '보호', '자보'
    sub 는 대분류 다음의 '비어 있지 않은' 이름부터 차례로 맞춥니다. (엑셀마다 중분류가 비어 있기도 해서)
    행 이름은 고른 단계 아래의 이름을 이어 붙입니다. 예) 'A2 의료고도'
    """
    path = (sub,) if isinstance(sub, str) else tuple(sub or ())
    keep_idx, names = [], []
    for idx, row in df[df["대분류"] == section][LABEL_COLS[1:]].iterrows():
        lower = [x for x in row if x]
        if tuple(lower[:len(path)]) != path:
            continue
        lower = lower[len(path):]
        if not lower or any(x in exclude for x in lower):
            continue
        keep_idx.append(idx)
        names.append(" ".join(lower))
    out = df.loc[keep_idx, months].astype(float)
    out.index = names
    return out


def find_row(df: pd.DataFrame, *labels: str) -> pd.Series:
    """항목 이름으로 한 줄을 찾아 월별 값(Series)으로 돌려줍니다.

    예) find_row(df, "월말재원환자수", "합계")
        → 대분류가 '월말재원환자수'이고 아래 단계 어딘가에 '합계'가 있는 줄
    이름은 대분류부터 순서대로 적되, 빈 단계는 건너뛰어도 됩니다.
    """
    return df.loc[find_index(df, *labels), month_columns(df)].astype(float)


def find_index(df: pd.DataFrame, *labels: str):
    """find_row 와 같은 방법으로 찾은 줄의 번호(index)를 돌려줍니다."""
    mask = pd.Series(True, index=df.index)
    for wanted in labels:
        mask &= df[LABEL_COLS].eq(wanted).any(axis=1)
    hits = df.index[mask]
    if len(hits) == 0:
        raise KeyError(f"항목을 찾을 수 없습니다: {' > '.join(labels)}")
    return hits[0]
