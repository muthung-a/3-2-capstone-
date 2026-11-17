"""약품 처방 원 데이터(월별 시트 '6', '7' …) → 진료과별 처방금액 · 상위 약품 통계.

원 데이터 → 통계를 자동으로 계산하는 부분입니다. (회의 요구: 진료과별 통계)
엑셀 모양 (시트 하나 = 한 달):
    1행 머리글: 정의코드 | 청구코드 | 명칭 | … | 처방횟수 | 단가 | 총수량 | 총금액 | (빈칸)
               | 진료과별 수량 … | (빈칸) | 진료과별 금액 … | 합계
진료과별 '금액' 칸(마지막 빈칸 ~ 합계 사이)을 기준으로 계산합니다. 같은 진료과 이름이 두 번 나오면 합칩니다.
약품 이름이 없는 줄은 구역별 '소계' 줄이라 빼고 계산하고, 대신 검산에 씁니다. (약품 합계 = 소계 합계인지)
개인 정보는 없습니다(약품·진료과 이름만).
"""
import re
from dataclasses import dataclass

import pandas as pd
from openpyxl import load_workbook

import config
from core.monthly import clean_label

@dataclass
class Drugs:
    items: pd.DataFrame   # 월, 약품, 분류번호, 처방횟수, 금액  (약품 한 줄 = 한 행)
    depts: pd.DataFrame   # 월, 약품, 진료과, 금액              (금액 > 0 인 칸만)
    months: list          # 시트 순서대로 달 번호. 예) [6, 7, 8, 9, 10, 11]
    subtotals: dict       # 검산용: {달: 엑셀 소계 줄 합계}


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def _parse_sheet(rows: list, month: int) -> tuple[list, list, float] | None:
    """시트 하나를 (약품 행들, 진료과 금액 행들, 소계 합계)로. 양식이 아니면 None."""
    header = [clean_label(h) for h in rows[0]]
    if "명칭" not in header or "합계" not in header:
        return None
    name_i, total_i = header.index("명칭"), len(header) - 1 - header[::-1].index("합계")
    blanks = [i for i in range(total_i) if header[i] == ""]
    if not blanks:
        return None
    amount_cols = [i for i in range(blanks[-1] + 1, total_i) if header[i]]  # 마지막 빈칸 ~ 합계 사이 = 진료과별 금액
    cls_i = header.index("분류번호") if "분류번호" in header else None
    cnt_i = header.index("처방횟수") if "처방횟수" in header else None
    items, depts, subtotal = [], [], 0.0
    for r in rows[1:]:
        r = list(r) + [None] * (len(header) - len(r))
        name = clean_label(r[name_i])
        amounts = {i: _num(r[i]) for i in amount_cols}
        total = sum(amounts.values())
        if not name:      # 약품 이름 없는 줄 = 구역 소계 → 계산에서 빼고 검산용으로만
            subtotal += total
            continue
        if total == 0:    # 처방 금액이 없는 약품
            continue
        items.append({"월": month, "약품": name, "분류번호": str(r[cls_i] or "") if cls_i is not None else "",
                      "처방횟수": _num(r[cnt_i]) if cnt_i is not None else 0.0, "금액": total})
        for i, amount in amounts.items():
            if amount:
                depts.append({"월": month, "약품": name, "진료과": header[i], "금액": amount})
    return items, depts, subtotal


def load_drugs(path) -> Drugs | None:
    """엑셀에서 약품 처방 시트(이름이 숫자 1~12)를 모두 읽습니다. 없으면 None."""
    pattern = re.compile(config.DRUG_SHEET_PATTERN)
    wb = load_workbook(path, read_only=True, data_only=True)
    items, depts, months, subtotals = [], [], [], {}
    try:
        for name in wb.sheetnames:
            if not pattern.match(name.strip()):
                continue
            rows = [list(r) for r in wb[name].iter_rows(values_only=True)]
            parsed = _parse_sheet(rows, int(name)) if rows else None
            if parsed:
                items += parsed[0]
                depts += parsed[1]
                months.append(int(name))
                subtotals[int(name)] = parsed[2]
    finally:
        wb.close()
    if not months:
        return None
    return Drugs(pd.DataFrame(items), pd.DataFrame(depts), months, subtotals)


def verify(d: Drugs, month: int) -> bool | None:
    """검산: 약품 합계가 엑셀 소계 합계와 같은지 (1원 단위 반올림 차이 허용). 소계 줄이 없으면 None."""
    sub = d.subtotals.get(month, 0.0)
    if not sub:
        return None
    total = float(d.items.loc[d.items["월"] == month, "금액"].sum())
    return abs(total - sub) <= max(10.0, sub * 1e-6)


def month_label(m: int) -> str:
    return f"{m}월"


def dept_by_month(d: Drugs) -> pd.DataFrame:
    """진료과 × 월 처방금액 표 (금액 큰 진료과가 위)."""
    t = d.depts.pivot_table(index="진료과", columns="월", values="금액", aggfunc="sum", fill_value=0.0)
    t = t.reindex(columns=d.months, fill_value=0.0)
    return t.loc[t.sum(axis=1).sort_values(ascending=False).index]


def top_items(d: Drugs, month: int, n: int = 10) -> pd.Series:
    """그 달 처방금액 상위 n개 약품."""
    s = d.items[d.items["월"] == month].groupby("약품")["금액"].sum()
    return s.sort_values(ascending=False).head(n)


def summary(d: Drugs, month: int) -> dict:
    """그 달 요약: 총 처방금액, 품목 수, 처방횟수 합계, 전월 대비 금액 증감(%)."""
    cur = d.items[d.items["월"] == month]
    total = float(cur["금액"].sum())
    prev_m = d.months[d.months.index(month) - 1] if d.months.index(month) > 0 else None
    prev = float(d.items.loc[d.items["월"] == prev_m, "금액"].sum()) if prev_m else float("nan")
    change = (total - prev) / prev * 100 if prev and prev == prev else float("nan")
    return {"총 처방금액": total, "품목 수": int(len(cur)),
            "처방횟수": float(cur["처방횟수"].sum()), "전월 대비(%)": change}
