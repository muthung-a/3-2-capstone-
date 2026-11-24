"""엑셀 보고서 만들기: 요약 · 핵심지표 · 환자·병상 · 수익 · 비용 시트. streamlit 은 쓰지 않습니다."""
import io
from datetime import datetime

import pandas as pd

from core.view import View
from reports.common import kpi_table, plain, sections, summary_and_alerts


def _autofit(ws) -> None:
    """열 너비를 내용 길이에 맞춥니다 (한글은 2칸으로 계산)."""
    for col in ws.columns:
        width = max(sum(2 if ord(ch) > 127 else 1 for ch in str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 80)


def build(v: View) -> bytes:
    """엑셀 보고서 파일 내용(bytes)을 돌려줍니다."""
    lines, alerts = summary_and_alerts(v)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        made = f"작성 {datetime.now():%Y-%m-%d %H:%M}" + (f" · 작성자 {v.author}" if v.author else "")
        head = [f"경영통계 보고서 — {v.month.year}년 {v.month.month}월",
                f"조회기간 {v.months[0]} ~ {v.months[-1]} · 원자료 {v.file_name}", made, "", "■ 자동 요약"]
        body = head + [f"• {plain(t)}" for t in lines] + ["", "■ 확인 필요 항목"] + \
            [f"[{a.badge}] {a.text}" for a in alerts]
        pd.DataFrame({"내용": body}).to_excel(xw, sheet_name="요약", index=False)
        kpi_table(v).to_excel(xw, sheet_name="핵심지표", index=False)
        for title, frame, _ in sections(v):
            out = frame.copy()
            out.columns = [str(c) for c in out.columns]
            out.index.name = "항목"
            out.to_excel(xw, sheet_name=title.replace("·", "_"))
        for ws in xw.book.worksheets:
            _autofit(ws)
            for row in ws.iter_rows(min_row=2, min_col=2):
                for cell in row:
                    if isinstance(cell.value, float) and abs(cell.value) >= 10:
                        cell.number_format = "#,##0"
    return buf.getvalue()
