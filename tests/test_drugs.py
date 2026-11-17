"""core/drugs.py (약품 처방 원 데이터 → 진료과별 통계) 테스트."""
import pytest
from openpyxl import Workbook

import config
from core import drugs

HEADER = ["정의코드", "청구코드", "명 칭", "제약회사", "구입거래처", "분류번호", "효능코드", "단위",
          "처방횟수", "단가", "총수량", "총금액", None, "EM", "내과2", "내과2", None, "EM", "내과2", "내과2", "합계"]


def _row(name, count, em, n1, n2):
    total = em + n1 + n2
    return ["c", "c", name, "회사", None, 214, None, "정", count, 1, 1, total, None,
            1, 1, 1, None, em, n1, n2, total]


def _make(path):
    wb = Workbook()
    wb.active.title = "Sample data"           # 약품 시트가 아님 → 무시
    for month, scale in (("6", 1), ("7", 2)):
        ws = wb.create_sheet(month)
        ws.append(HEADER)
        ws.append(_row("약A", 10, 100 * scale, 50 * scale, 0))
        ws.append(_row("약B", 5, 0, 30 * scale, 20 * scale))
        ws.append([None] * 17 + [100 * scale, 80 * scale, 20 * scale, 200 * scale])  # 구역 소계 줄 (이름 없음)
        ws.append(_row("약C", 1, 0, 0, 0))     # 금액 0 → 빠짐
    wb.create_sheet("간호등급").append(["연번", "성명"])  # 다른 시트 → 무시
    wb.save(path)


@pytest.fixture
def d(tmp_path):
    path = tmp_path / "drug.xlsx"
    _make(path)
    return drugs.load_drugs(path)


def test_reads_only_month_sheets(d):
    assert d.months == [6, 7]


def test_subtotal_rows_are_not_counted(d):
    s = drugs.summary(d, 6)
    assert s["총 처방금액"] == 200          # 약A 150 + 약B 50 (소계 200 을 또 더하지 않음)
    assert s["품목 수"] == 2 and s["처방횟수"] == 15
    assert drugs.verify(d, 6) is True       # 약품 합계 = 소계


def test_same_dept_name_is_merged(d):
    table = drugs.dept_by_month(d)
    assert table.loc["내과2", 6] == 100     # 내과2 두 칸(50+0, 30+20) 합침
    assert table.loc["EM", 7] == 200
    assert list(table.index)[0] in ("내과2", "EM")


def test_top_items_and_change(d):
    assert list(drugs.top_items(d, 7, 1).index) == ["약A"]
    assert drugs.summary(d, 7)["전월 대비(%)"] == pytest.approx(100.0)


def test_no_drug_sheets_returns_none(tmp_path):
    path = tmp_path / "none.xlsx"
    Workbook().save(path)
    assert drugs.load_drugs(path) is None


def test_real_sample_verifies():
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    d = drugs.load_drugs(files[0])
    assert d.months == [6, 7, 8, 9, 10, 11]
    assert all(drugs.verify(d, m) for m in d.months)  # 6개월 모두 약품 합계 = 엑셀 소계
