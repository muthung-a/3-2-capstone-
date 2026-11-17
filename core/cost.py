"""비용 관련 계산: 주요 비용 묶음, 간병·위생소모품 손익."""
import pandas as pd

from core import monthly


def cost_breakdown(df: pd.DataFrame, months: list, items: list) -> pd.DataFrame:
    """주요 비용(config.COST_ITEMS)을 '비용 이름 × 월' 표로 모읍니다. 없는 항목은 건너뜁니다."""
    rows = {}
    for name, labels in items:
        try:
            rows[name] = monthly.find_row(df, *labels)[months]
        except KeyError:
            continue
    return pd.DataFrame([r.tolist() for r in rows.values()], index=list(rows), columns=months, dtype=float)


def caregiving_pl(df: pd.DataFrame, months: list) -> pd.DataFrame:
    """간병 손익: 총수입, 지급수수료, 손익(엑셀의 '간병비-인건비' 줄) 세 줄."""
    return pd.DataFrame({
        "총수입": monthly.find_row(df, "간병", "총수입", "합계")[months],
        "지급수수료": monthly.find_row(df, "간병", "지급수수료", "합계")[months],
        "손익": monthly.find_row(df, "간병", "손익")[months],
    }).T.astype(float)


def hygiene_pl(df: pd.DataFrame, months: list) -> pd.DataFrame:
    """위생소모품 손익: 매출, 매입, 기저귀 폐기물 처리비용, 최종 손익(엑셀 값) 네 줄."""
    return pd.DataFrame({
        "매출": monthly.find_row(df, "위생소모품", "매출", "합계")[months],
        "매입": monthly.find_row(df, "위생소모품", "매입", "합계")[months],
        "폐기물 처리비용": monthly.find_row(df, "기저귀폐기물", "처리비용")[months],
        "최종 손익": monthly.find_row(df, "기저귀폐기물", "위생소모품수익 - 처리비용")[months],
    }).T.astype(float)
