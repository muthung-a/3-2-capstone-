"""core/quality.py ('미입력 의심' 0 찾기) 테스트."""
import math

import pandas as pd
import pytest

import config
from core import kpi, monthly, quality

M = [pd.Period("2024-01", "M"), pd.Period("2024-02", "M")]
SPECS = [("인건비", ("인건비", "합계"))]


def _df():
    labels = pd.DataFrame([["인건비", "", "합계", "", ""], ["청구금액", "", "한방", "외래", ""]],
                          columns=monthly.LABEL_COLS)
    values = pd.DataFrame([[100.0, 0.0], [0.0, 0.0]], columns=M)
    return pd.concat([labels, values], axis=1)


def test_only_listed_items_are_suspect():
    found = quality.find_suspects(_df(), SPECS)
    assert [(s.name, str(s.month)) for s in found] == [("인건비", "2024-02")]  # 한방 외래 0 은 진짜 0


def test_blank_keeps_original_and_blanks_copy():
    df = _df()
    clean = quality.blank_suspects(df, quality.find_suspects(df, SPECS))
    assert math.isnan(monthly.find_row(clean, "인건비", "합계")[M[1]])
    assert monthly.find_row(df, "인건비", "합계")[M[1]] == 0          # 원본은 그대로
    assert monthly.find_row(clean, "청구금액", "외래")[M[1]] == 0      # 목록에 없는 0 은 그대로


def test_kpi_marks_suspect():
    df = _df()
    clean = quality.blank_suspects(df, quality.find_suspects(df, SPECS))
    card = kpi.build_kpis(clean, M[1], [("인건비", ("인건비", "합계"), "money")])[0]
    assert card.suspect and math.isnan(card.change)
    assert not kpi.build_kpis(clean, M[0], [("인건비", ("인건비", "합계"), "money")])[0].suspect


def test_suspects_in_months():
    df = _df()
    clean = quality.blank_suspects(df, quality.find_suspects(df, SPECS))
    assert len(quality.suspects_in(clean, [M[1]])) == 1
    assert quality.suspects_in(clean, [M[0]]) == []


def test_real_file_flags_labor_cost():
    """가상 데이터의 2026년 9월 인건비 0 이 '미입력 의심'으로 잡히는지."""
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    real = monthly.load_monthly(files[0])
    found = quality.find_suspects(real, config.NEVER_ZERO)
    assert ("인건비", "2026-09") in [(s.name, str(s.month)) for s in found]
    names = {s.name for s in found}
    assert all(name in {n for n, _ in config.NEVER_ZERO} for name in names)
