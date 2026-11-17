"""core/revenue.py 와 section_frame(sub=...) 테스트."""
import pandas as pd
import pytest

import config
from core import monthly, revenue

M = [pd.Period("2024-01", "M"), pd.Period("2024-02", "M")]


def _df(rows):
    labels = pd.DataFrame([r[:5] for r in rows], columns=monthly.LABEL_COLS)
    values = pd.DataFrame([r[5:] for r in rows], columns=M, dtype=float)
    return pd.concat([labels, values], axis=1)


REHAB = _df([
    ["재활치료", "", "MM105", "중추신경계발달재활치료", "", 100, 200],
    ["재활치료", "", "MM301", "매트및이동치료", "", 50, 0],
    ["재활치료", "", "소계", "", "", 150, 200],
    ["재활치료", "", "도수치료", "급여(자보)", "", None, 10],
    ["재활치료", "", "도수치료", "비급여", "", 30, 40],
    ["재활치료", "", "크라이오", "", "", None, None],
    ["재활치료", "", "소계", "", "", 30, 50],
])


def test_rehab_split_groups_rows():
    out = revenue.rehab_split(REHAB, M)
    assert list(out.index) == ["급여 재활치료", "도수치료", "크라이오"]
    assert out.loc["급여 재활치료"].tolist() == [150, 200]
    assert out.loc["도수치료"].tolist() == [30, 50]


def test_rehab_items_sorted_without_zero():
    s = revenue.rehab_items(REHAB, M[1])
    assert list(s.index) == ["중추신경계발달재활치료"]  # 0원 항목은 빠짐
    assert list(revenue.rehab_items(REHAB, M[0]).index) == ["중추신경계발달재활치료", "매트및이동치료"]


def test_section_frame_with_sub():
    df = _df([
        ["청구금액", "공단", "의과", "입원", "", 1, 2],
        ["청구금액", "합계", "의과", "입원", "", 10, 20],
        ["청구금액", "합계", "의과", "외래", "", 3, 4],
        ["청구금액", "합계", "", "", "", 13, 24],   # 맨 아래 총합 줄 (이름 없음 → 빠짐)
    ])
    frame = monthly.section_frame(df, "청구금액", M, sub="합계")
    assert list(frame.index) == ["의과 입원", "의과 외래"]
    assert frame.loc["의과 입원"].tolist() == [10, 20]


def test_money_ticks():
    ticks, text = revenue.money_ticks([0, 8.5e8])
    assert text == ["0", "2.5억", "5억", "7.5억", "10억"]
    ticks, text = revenue.money_ticks([1_200_000, 4_100_000])
    assert all(t.endswith("만") or t == "0" for t in text)
    ticks, text = revenue.money_ticks([3_800_000, 4_300_000], from_zero=False)
    assert len(ticks) >= 3 and ticks[0] <= 3_800_000 and ticks[-1] >= 4_300_000 and ticks[0] > 0
    ticks, text = revenue.money_ticks([1100, 1500], from_zero=False)
    assert all(t.endswith("원") for t in text)          # 1만 원 미만은 '1,200원' 처럼
    assert revenue.money_ticks([]) == ([], [])
    assert revenue.money_ticks([float("nan")]) == ([], [])


def test_revenue_tab_labels_exist_in_real_file():
    """수익 탭이 쓰는 항목이 실제 가상 데이터에 있는지 확인."""
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    real = monthly.load_monthly(files[0])
    months = monthly.available_months(real)[-13:]
    assert list(monthly.section_frame(real, "총진료비", months, sub="합계").index) == ["공단", "보호", "자보", "일반"]
    assert len(monthly.section_frame(real, "청구금액", months, sub="합계")) == 4
    assert "공단" in monthly.section_frame(real, "평균진료비", months, sub="총진료비/평균재원").index
    assert list(revenue.rehab_split(real, months).index)[0] == "급여 재활치료"
    for _, labels, _ in config.REVENUE_DETAIL + config.PATIENT_DETAIL + config.ALERT_ITEMS:  # 표·경고 항목 확인
        monthly.find_row(real, *labels)
