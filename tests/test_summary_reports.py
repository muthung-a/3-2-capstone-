"""자동 요약 · 확인 필요 항목 · 설정 · 사용자 정의 통계 · 보고서 테스트."""
import io

import pandas as pd
import pytest
from openpyxl import load_workbook

import config
from core import custom, monthly, quality, settings, summary
from core.view import View
from reports import excel_report, html_report

M = list(pd.period_range("2024-01", periods=13, freq="M"))  # 2024-01 ~ 2025-01 (13개월)


def _df(values_by_label: dict) -> pd.DataFrame:
    labels = pd.DataFrame([list(k) + [""] * (5 - len(k)) for k in values_by_label], columns=monthly.LABEL_COLS)
    values = pd.DataFrame(list(values_by_label.values()), columns=M, dtype=float)
    return pd.concat([labels, values], axis=1)


def test_pct_and_fmt():
    assert summary.pct(110, 100) == pytest.approx(10)
    assert summary.fmt_p(summary.pct(90, 100)) == "−10.0%"
    assert summary.fmt_p(summary.pct(1, 0)) == "비교불가"


def test_alerts_bed_and_change():
    df = _df({("병상가동율", "", "", "%"): [0.97] * 12 + [0.90],
              ("총진료비", "합계", "", "소계"): [100.0] * 12 + [150.0]})
    items = summary.alerts(df, M[-1], warn_pct=10, bed_target=95)
    badges = [a.badge for a in items]
    assert "적정선 미달" in badges and "증가" in badges
    assert items[0].level == "r"                       # 빨강(주의)이 먼저


def test_alerts_normal_when_nothing():
    df = _df({("총진료비", "합계", "", "소계"): [100.0] * 13})
    assert [a.badge for a in summary.alerts(df, M[-1], 10, 95)] == ["정상"]


def test_summary_lines_mentions_total():
    df = _df({("총진료비", "합계", "", "소계"): [100.0] * 11 + [200_000_000.0, 210_000_000.0]})
    lines = summary.summary_lines(df, M[-1])
    assert "2.10억" in lines[0] and "+5.0%" in lines[0]


def test_settings_roundtrip(tmp_path):
    path = tmp_path / "s.json"
    assert settings.load(path)["span"] == 6                     # 파일 없으면 기본값
    settings.save(path, dict(settings.DEFAULTS, span=12, favorites=["A > B"]))
    loaded = settings.load(path)
    assert loaded["span"] == 12 and loaded["favorites"] == ["A > B"]
    path.write_text("깨진 파일", encoding="utf-8")
    assert settings.load(path)["span"] == 6


def test_row_labels_unique_and_favorites():
    df = _df({("재활치료", "", "소계"): [1.0] * 13, ("재활치료", "", "소계", ""): [2.0] * 13})
    labels = list(custom.row_labels(df))
    assert labels == ["재활치료 > 소계", "재활치료 > 소계 (2)"]
    table = custom.favorites_table(df, labels, M[-1])
    assert list(table["항목"]) == labels and table.loc[1, "당월"] == 2.0


def _real_view():
    files = sorted(config.DATA_DIR.glob("*.xlsx"))
    if not files:
        pytest.skip("data/ 폴더에 엑셀이 없습니다")
    df = monthly.load_monthly(files[0])
    df = quality.blank_suspects(df, quality.find_suspects(df, config.NEVER_ZERO))
    month = monthly.available_months(df)[-1]
    return View(df=df, month=month, months=monthly.recent_months(df, month, 6), file_name="<가상>&테스트.xlsx")


def test_reports_build_from_real_file():
    v = _real_view()
    wb = load_workbook(io.BytesIO(excel_report.build(v)))
    assert wb.sheetnames == ["요약", "핵심지표", "환자_병상", "수익", "비용"]
    html = html_report.build(v)
    assert "자동 요약" in html and "확인 필요 항목" in html and "비용 상세" in html
    assert "&lt;가상&gt;&amp;테스트.xlsx" in html                 # 파일 이름은 이스케이프됨
    assert "인건비 값이 0" in html                                 # 미입력 의심이 보고서에도 나옴
