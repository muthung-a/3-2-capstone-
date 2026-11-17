"""시연판(demo_app.py)과 가짜 데이터 생성기(core/sample.py) 테스트. 실제 파일 없이 돌아갑니다."""
import io

from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

import config
from core import check, drugs, monthly, quality, sample


def test_sample_has_every_item_the_app_uses():
    df = monthly.load_monthly(io.BytesIO(sample.build_workbook()))
    assert [i.path for i in check.check(df) if not i.found] == []
    assert len(monthly.available_months(df)) == sample.MONTHS


def test_sample_is_reproducible():
    # 같은 seed → 같은 숫자 (엑셀 파일의 저장 시각 같은 정보는 다를 수 있어 표로 비교)
    a = monthly.load_monthly(io.BytesIO(sample.build_workbook(seed=1)))
    b = monthly.load_monthly(io.BytesIO(sample.build_workbook(seed=1)))
    assert a.equals(b)


def test_sample_drugs_verify_and_suspect_shown():
    data = sample.build_workbook()
    d = drugs.load_drugs(io.BytesIO(data))
    assert d.months == [6, 7, 8, 9, 10, 11] and all(drugs.verify(d, m) for m in d.months)
    df = monthly.load_monthly(io.BytesIO(data))
    assert [s.name for s in quality.find_suspects(df, config.NEVER_ZERO)] == ["인건비"]  # 시연용 미입력 예시


def test_sample_has_no_personal_info():
    """시연 데이터는 인터넷에 올라가므로 개인 정보 형태의 글자가 없어야 합니다."""
    wb = load_workbook(io.BytesIO(sample.build_workbook()), read_only=True)
    text = " ".join(str(v) for ws in wb.worksheets for row in ws.iter_rows(values_only=True) for v in row if v)
    for word in ("성명", "이름", "주민", "면허", "생년월일"):
        assert word not in text
    assert wb.sheetnames == ["Sample data", "6", "7", "8", "9", "10", "11"]


def test_demo_app_runs_without_upload():
    at = AppTest.from_file(str(config.BASE_DIR / "demo_app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.tabs) == 6
    assert len(at.get("file_uploader")) == 0          # 시연판에는 파일 올리기 칸이 없음
    assert any("시연용" in i.value for i in at.sidebar.info)
