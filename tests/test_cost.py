"""core/cost.py 와 section_frame(sub=여러 단계) 테스트."""
import pandas as pd
import pytest

import config
from core import cost, monthly

M = [pd.Period("2024-01", "M"), pd.Period("2024-02", "M")]


def _df(rows):
    labels = pd.DataFrame([r[:5] for r in rows], columns=monthly.LABEL_COLS)
    values = pd.DataFrame([r[5:] for r in rows], columns=M, dtype=float)
    return pd.concat([labels, values], axis=1)


SAMPLE = _df([
    ["식자재", "", "식자재", "업체A", "", 10, 20],
    ["식자재", "", "식자재", "합계", "", 10, 20],
    ["식자재", "", "식단가", "경관식", "", 1000, 1100],
    ["간병", "", "총수입", "보험종별", "보험", 5, 6],
    ["간병", "", "총수입", "보험종별", "합계", 5, 6],
    ["간병", "", "지급수수료", "간병수수료", "", 8, 9],
    ["간병", "", "지급수수료", "합계", "", 8, 9],
    ["간병", "", "손익", "간병비-인건비", "", -3, -3],
    ["관리비", "", "전력비", "", "", 1, 2],
    ["관리비", "", "합계", "", "", 1, 2],
])


def test_section_frame_skips_empty_middle_level():
    # 중분류가 비어 있어도 sub 가 '다음 이름'(소분류)과 맞춰짐
    frame = monthly.section_frame(SAMPLE, "식자재", M, sub="식자재")
    assert list(frame.index) == ["업체A"]
    assert list(monthly.section_frame(SAMPLE, "식자재", M, sub="식단가").index) == ["경관식"]


def test_section_frame_with_path():
    frame = monthly.section_frame(SAMPLE, "간병", M, sub=("총수입", "보험종별"))
    assert list(frame.index) == ["보험"]


def test_cost_breakdown_skips_missing():
    items = [("식자재", ("식자재", "식자재", "합계")), ("관리비", ("관리비", "합계")), ("없음", ("없는것",))]
    out = cost.cost_breakdown(SAMPLE, M, items)
    assert list(out.index) == ["식자재", "관리비"]
    assert out.loc["식자재"].tolist() == [10, 20]


def test_caregiving_pl():
    pl = cost.caregiving_pl(SAMPLE, M)
    assert pl.loc["총수입"].tolist() == [5, 6]
    assert pl.loc["지급수수료"].tolist() == [8, 9]
    assert pl.loc["손익"].tolist() == [-3, -3]


def test_cost_tab_labels_exist_in_real_file():
    """비용 탭이 쓰는 항목이 실제 가상 데이터에 모두 있는지 확인."""
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    real = monthly.load_monthly(files[0])
    months = monthly.available_months(real)[-13:]
    assert len(cost.cost_breakdown(real, months, config.COST_ITEMS)) == len(config.COST_ITEMS)
    cost.caregiving_pl(real, months)
    cost.hygiene_pl(real, months)
    assert len(monthly.section_frame(real, "식자재", months, sub="식단가")) == 3
    assert list(monthly.section_frame(real, "의약품", months, sub="환자당투약").index) == ["급여", "비급여"]
    assert len(monthly.section_frame(real, "인건비(퇴직금,복리후생비,일용직제외)", months)) == 5
