"""core/kpi.py 테스트."""
import math

import pandas as pd
import pytest

import config
from core import kpi, monthly


def _df():
    """월말재원환자수 합계와 병상가동율이 3개월 있는 작은 표."""
    months = [pd.Period("2024-01", "M"), pd.Period("2024-02", "M"), pd.Period("2024-03", "M")]
    labels = pd.DataFrame([["월말재원환자수", "", "", "합계", ""], ["병상가동율", "", "", "%", ""]],
                          columns=monthly.LABEL_COLS)
    values = pd.DataFrame([[100.0, 110.0, 99.0], [0.90, 0.95, 0.95]], columns=months)
    return pd.concat([labels, values], axis=1), months


SPECS = [("재원", ("월말재원환자수", "합계"), "count"),
         ("가동율", ("병상가동율",), "ratio"),
         ("없는항목", ("없음",), "money")]


def test_build_kpis_values_and_change():
    df, months = _df()
    cards = kpi.build_kpis(df, months[1], SPECS)
    assert [c.label for c in cards] == ["재원", "가동율"]  # 없는 항목은 건너뜀
    assert cards[0].value == 110 and cards[0].prev == 100
    assert cards[0].change == pytest.approx(10.0)       # +10%
    assert cards[1].change == pytest.approx(5.0)        # +5%p
    assert cards[0].history == [100, 110]


def test_first_month_has_no_change():
    df, months = _df()
    card = kpi.build_kpis(df, months[0], SPECS)[0]
    assert math.isnan(card.prev) and math.isnan(card.change)


def test_format_value():
    assert kpi.format_value(437857330, "money") == "4.38억"
    assert kpi.format_value(5966000, "money") == "597만"
    assert kpi.format_value(0.975, "ratio") == "97.5%"
    assert kpi.format_value(174, "count") == "174명"
    assert kpi.format_value(float("nan"), "money") == "-"


def test_all_config_kpis_exist_in_real_file():
    """config.KPIS 의 항목 이름이 실제 가상 데이터에 모두 있는지 확인."""
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    df = monthly.load_monthly(files[0])
    month = monthly.available_months(df)[-1]
    assert len(kpi.build_kpis(df, month, config.KPIS)) == len(config.KPIS)
