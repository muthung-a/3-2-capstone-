"""인쇄용 보고서(HTML) 만들기: 브라우저에서 열고 [인쇄] → 'PDF로 저장' 하면 PDF가 됩니다.

인터넷에서 아무것도 불러오지 않는 파일 하나짜리 보고서입니다. streamlit 은 쓰지 않습니다.
"""
from datetime import datetime
from html import escape

import pandas as pd

from core.kpi import format_value
from core.view import View
from reports.common import kpi_table, sections, summary_and_alerts

_CSS = """
*{box-sizing:border-box} body{margin:0;background:#f8fafc;color:#111827;
 font:14px/1.6 "Pretendard","Malgun Gothic","Apple SD Gothic Neo",sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:28px 20px 60px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;
 border-bottom:2px solid #111827;padding-bottom:12px;margin-bottom:18px}
h1{font-size:22px;margin:0} .meta{font-size:12px;color:#6b7280;text-align:right}
section{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px 18px;margin-bottom:14px;break-inside:avoid}
h2{font-size:15px;margin:0 0 10px} ul{margin:0;padding-left:18px} li{margin:3px 0}
table{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}
th,td{padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right;white-space:nowrap}
th{background:#f9fafb;color:#374151;font-weight:600} th:first-child,td:first-child{text-align:left}
.tbl{overflow-x:auto} .badge{font-size:11px;font-weight:600;padding:1px 7px;border-radius:9999px;margin-right:6px}
.r{color:#be123c;background:#fff1f2}.y{color:#b45309;background:#fef3c7}.g{color:#047857;background:#ecfdf5}
button{font:inherit;font-size:13px;padding:7px 14px;border:1px solid #d1d5db;background:#fff;border-radius:8px;cursor:pointer}
.note{font-size:12px;color:#6b7280}
@media print{body{background:#fff}.noprint{display:none}section{border-color:#ccc}.wrap{padding:0}}
"""


def _table(df: pd.DataFrame, index_name: str | None = None) -> str:
    """표를 HTML 로. 모든 글자는 이스케이프합니다."""
    cols = ([index_name] if index_name else []) + [str(c) for c in df.columns]
    head = "".join(f"<th>{escape(c)}</th>" for c in cols)
    body = ""
    for idx, row in df.iterrows():
        cells = ([escape(str(idx))] if index_name else []) + [escape(str(x)) for x in row]
        body += "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
    return f'<div class="tbl"><table><tr>{head}</tr>{body}</table></div>'


def _formatted(frame: pd.DataFrame, kinds) -> pd.DataFrame:
    shown = pd.DataFrame([[format_value(x, kinds if isinstance(kinds, str) else kinds.get(name, "money"))
                           for x in row] for name, row in frame.iterrows()],
                         index=frame.index, columns=[f"{m.year % 100}.{m.month:02d}" for m in frame.columns])
    return shown


def build(v: View) -> str:
    """인쇄용 보고서 HTML 글자를 돌려줍니다."""
    lines, alerts = summary_and_alerts(v)
    title = f"경영통계 보고서 — {v.month.year}년 {v.month.month}월"
    meta = (f"조회기간 {v.months[0]} ~ {v.months[-1]}<br>원자료 {escape(v.file_name)}<br>"
            f"작성 {datetime.now():%Y-%m-%d %H:%M}" + (f" · 작성자 {escape(v.author)}" if v.author else "")
            + " · 이 PC에서 생성")
    parts = [f"<header><div><h1>{escape(title)}</h1></div><div class='meta'>{meta}</div></header>",
             "<p class='noprint'><button onclick='window.print()'>🖨 인쇄 / PDF로 저장</button> "
             "<span class='note'>인쇄 창에서 대상을 'PDF로 저장'으로 고르세요.</span></p>",
             # 요약 문장은 숫자·고정 문구로만 만들어져 <b> 표시를 그대로 씁니다
             "<section><h2>1. 자동 요약</h2><ul>" + "".join(f"<li>{t}</li>" for t in lines) + "</ul></section>",
             "<section><h2>2. 확인 필요 항목</h2><ul>" + "".join(
                 f"<li><span class='badge {a.level}'>{escape(a.badge)}</span>{escape(a.text)}</li>"
                 for a in alerts) + "</ul></section>",
             f"<section><h2>3. 핵심 지표</h2>{_table(kpi_table(v).set_index('항목'), '항목')}</section>"]
    for i, (name, frame, kinds) in enumerate(sections(v), start=4):
        parts.append(f"<section><h2>{i}. {escape(name)} 상세</h2>{_table(_formatted(frame, kinds), '항목')}</section>")
    return (f"<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width, initial-scale=1'><title>{escape(title)}</title>"
            f"<style>{_CSS}</style></head><body><div class='wrap'>{''.join(parts)}</div></body></html>")
