"""core/monthly.py 테스트.

테스트용 작은 엑셀을 직접 만들어서 씁니다. (data/ 의 파일이 없어도 돌아감)
"""
import math
from datetime import datetime

import pandas as pd
import pytest
from openpyxl import Workbook

import config
from core import monthly


def _make_excel(path):
    """실제 양식을 흉내 낸 작은 엑셀."""
    wb = Workbook()
    ws = wb.active
    ws.title = config.MONTHLY_SHEET
    ws.append(["구분", None, None, None, None, datetime(2024, 1, 1), datetime(2024, 2, 1),
               datetime(2024, 3, 1), "합계(최근1년)"])
    ws.append([None, None, None, None, None, 31, 29, 31, None])
    ws.append(["월말 재원환자수", None, None, "공단", None, 100, 110, None, 210])
    ws.append([None, None, None, "보호", None, 50, " - ", None, 50])
    ws.append([None, None, None, "합   계", None, 150, 110, None, 260])
    ws.append(["총\n진\n료\n비", "청구금액\n(입원+외래)", None, "공단", None, 1000, 2000, None, 3000])
    ws.append([None, "본인부담금", None, "공단", None, 10, 20, None, 30])
    ws.append(["한의사별\n총진료비", None, "홍길동", None, None, 5, 6, None, 11])
    ws.append([None, None, "김철수", None, None, 7, 8, None, 15])
    ws.append([None, None, "합   계", None, None, 12, 14, None, 26])
    wb.save(path)


@pytest.fixture
def df(tmp_path):
    path = tmp_path / "sample.xlsx"
    _make_excel(path)
    return monthly.load_monthly(path)


def test_clean_label():
    assert monthly.clean_label("총\n진\n료\n비") == "총진료비"
    assert monthly.clean_label("합   계") == "합계"
    assert monthly.clean_label("월말 재원환자수") == "월말재원환자수"
    assert monthly.clean_label(None) == ""


def test_month_columns_only_dates(df):
    months = monthly.month_columns(df)
    assert [str(m) for m in months] == ["2024-01", "2024-02", "2024-03"]  # '합계(최근1년)' 제외


def test_available_months_skips_empty(df):
    assert [str(m) for m in monthly.available_months(df)] == ["2024-01", "2024-02"]


def test_merged_labels_are_filled(df):
    s = monthly.find_row(df, "월말재원환자수", "보호")
    assert s.iloc[0] == 50
    assert math.isnan(s.iloc[1])  # ' - ' → 값 없음


def test_lower_levels_reset(df):
    # '본인부담금' 줄은 '청구금액' 이 아니라 '본인부담금' 아래에 있어야 함
    assert monthly.find_row(df, "총진료비", "청구금액(입원+외래)", "공단").iloc[0] == 1000
    assert monthly.find_row(df, "총진료비", "본인부담금", "공단").iloc[0] == 10


def test_names_are_pseudonymized(df):
    text = df[monthly.LABEL_COLS].to_string()
    assert "홍길동" not in text and "김철수" not in text
    assert monthly.find_row(df, "한의사별총진료비", "한의사_1").iloc[0] == 5
    assert monthly.find_row(df, "한의사별총진료비", "합계").iloc[0] == 12


def test_find_row_missing(df):
    with pytest.raises(KeyError):
        monthly.find_row(df, "없는항목")


def test_real_sample_file_if_present():
    """data/ 에 가상 데이터가 있으면 실제 파일로도 읽어 봅니다."""
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    real = monthly.load_monthly(files[0])
    assert len(monthly.available_months(real)) > 0
    assert isinstance(monthly.find_row(real, "병상가동율"), pd.Series)
    names = real.loc[real["대분류"] == "한의사별총진료비", "소분류"]
    assert names.str.match(r"^(한의사_\d+|합계)$").all()


def test_recent_months(df):
    feb = monthly.available_months(df)[1]
    assert [str(m) for m in monthly.recent_months(df, feb, 1)] == ["2024-02"]
    assert [str(m) for m in monthly.recent_months(df, feb, 13)] == ["2024-01", "2024-02"]


def test_section_frame_excludes_total(df):
    months = monthly.available_months(df)
    frame = monthly.section_frame(df, "월말재원환자수", months)
    assert list(frame.index) == ["공단", "보호"]  # '합계' 줄은 빠짐
    assert frame.loc["공단"].tolist() == [100, 110]


def test_patients_tab_labels_exist_in_real_file():
    """환자·병상 탭이 쓰는 항목이 실제 가상 데이터에 있는지 확인."""
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    real = monthly.load_monthly(files[0])
    months = monthly.available_months(real)[-13:]
    assert len(monthly.section_frame(real, "월말재원환자수", months)) == 3   # 공단·보호·자보
    assert len(monthly.section_frame(real, "환자군수", months)) == 5         # A1~A7
    for labels in [("퇴원환자수", "실퇴원수"), ("평균재원환자수", "합계"), ("퇴원환자수", "사망")]:
        monthly.find_row(real, *labels)
