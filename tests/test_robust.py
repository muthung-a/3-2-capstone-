"""병원 실제 파일이 가상 데이터와 조금 달라도 버티는지 확인하는 테스트.

- 시트 이름이 다름 / 항목 이름 열 수가 다름 / 숫자가 없음 / 항목이 빠짐
- 화면 전체를 실제로 돌려 보고 오류가 없는지 (streamlit AppTest)
"""
from datetime import datetime

import pandas as pd
import pytest
from openpyxl import Workbook
from streamlit.testing.v1 import AppTest

import config
from core import check, monthly

DATES = [datetime(2024, m, 1) for m in range(1, 13)] + [datetime(2025, 1, 1)]


def _write(path, title="2026년 통계", n_labels=5, values=True, extra_sheet=True):
    wb = Workbook()
    if extra_sheet:
        wb.active.title = "메모"
        wb.active.append(["이 시트는 통계표가 아님"])
        ws = wb.create_sheet(title)
    else:
        ws = wb.active
        ws.title = title
    ws.append(["구분"] + [None] * (n_labels - 1) + DATES)
    ws.append([None] * n_labels + [31] * len(DATES))
    row = ["총진료비", "합계"] + [None] * (n_labels - 3) + ["소계"]
    ws.append(row + ([100.0 + i for i in range(len(DATES))] if values else ["=A1"] * len(DATES)))
    wb.save(path)


def test_finds_sheet_with_other_name(tmp_path):
    path = tmp_path / "real.xlsx"
    _write(path)
    df = monthly.load_monthly(path)
    assert df.attrs["sheet"] == "2026년 통계"
    assert monthly.find_row(df, "총진료비", "합계", "소계").iloc[-1] == 112.0


def test_fewer_label_columns(tmp_path):
    path = tmp_path / "four.xlsx"
    _write(path, n_labels=4)  # 항목 이름이 A~D 4열, 날짜가 E열부터
    df = monthly.load_monthly(path)
    assert len(monthly.month_columns(df)) == 13
    assert monthly.find_row(df, "총진료비", "소계").iloc[0] == 100.0


def test_no_month_sheet_gives_clear_error(tmp_path):
    path = tmp_path / "bad.xlsx"
    wb = Workbook()
    wb.active.append(["이름", "값"])
    wb.save(path)
    with pytest.raises(ValueError, match="월별 통계표 시트를 찾지 못했습니다"):
        monthly.load_monthly(path)


def test_formula_without_saved_values_is_flagged(tmp_path):
    path = tmp_path / "formula.xlsx"
    _write(path, values=False)
    assert monthly.load_monthly(path).attrs["no_values"] is True


def test_check_lists_missing_items(tmp_path):
    path = tmp_path / "real.xlsx"
    _write(path)
    items = check.check(monthly.load_monthly(path))
    found = {i.path for i in items if i.found}
    assert "총진료비 > 합계 > 소계" in found
    assert any(not i.found and i.path == "병상가동율" for i in items)


def test_check_real_sample_all_found():
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    missing = [i.path for i in check.check(monthly.load_monthly(files[0])) if not i.found]
    assert missing == []


def _pages_with_almost_empty_data():
    """항목이 '총진료비' 하나뿐인 표로 모든 탭을 그려 봅니다. (AppTest 안에서 실행)"""
    import pandas as pd
    from core import monthly
    from core.view import View
    from ui import theme
    from ui.pages import cost, custom, drugs, overview, patients, revenue
    months = list(pd.period_range("2024-01", periods=13, freq="M"))
    labels = pd.DataFrame([["총진료비", "합계", "", "소계", ""]], columns=monthly.LABEL_COLS)
    df = pd.concat([labels, pd.DataFrame([[100.0] * 13], columns=months)], axis=1)
    v = View(df=df, month=months[-1], months=months[-6:], file_name="test.xlsx")
    theme.apply()
    for page in (overview, patients, revenue, cost, drugs, custom):
        page.render(v)


def test_pages_survive_missing_items():
    at = AppTest.from_function(_pages_with_almost_empty_data, default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]


def test_app_without_file_shows_guide():
    """파일을 올리기 전: 오류 없이 '엑셀을 올리세요' 안내만 나옵니다."""
    at = AppTest.from_file(str(config.BASE_DIR / "app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("엑셀 파일을 올려" in i.value for i in at.info)
    assert len(at.tabs) == 0


def _all_pages_with_sample():
    """파일을 올린 뒤와 같은 과정(읽기 → 미입력 처리 → 약품)으로 모든 탭을 그립니다. (AppTest 안에서 실행)"""
    import config
    from core import drugs, monthly, quality
    from core.view import View
    from ui import theme
    from ui.pages import cost, custom, drugs as drug_page, overview, patients, revenue
    path = sorted(config.DATA_DIR.glob("*.xlsx"))[0]
    df = monthly.load_monthly(path)
    df = quality.blank_suspects(df, quality.find_suspects(df, config.NEVER_ZERO))
    month = monthly.available_months(df)[-1]
    v = View(df=df, month=month, months=monthly.recent_months(df, month, 6), file_name=path.name,
             drugs=drugs.load_drugs(path))
    theme.apply()
    for page in (overview, patients, revenue, cost, drug_page, custom):
        page.render(v)


def test_all_pages_run_on_sample():
    if not sorted(config.DATA_DIR.glob("*.xlsx")):
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    at = AppTest.from_function(_all_pages_with_sample, default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
