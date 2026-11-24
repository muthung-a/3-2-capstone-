"""사용 기록: 누가 · 언제 · 무엇을 했는지 (로그인, 파일 열기, 보고서 받기, 계정·설정 변경).

- 엑셀 안의 내용(숫자·이름)은 기록하지 않습니다. 파일 이름과 '한 일'만 남깁니다.
- 기록 파일(activity_log.jsonl)은 이 PC에만 저장합니다. (웹판은 그 PC 브라우저 저장소)
- 한 줄에 기록 하나(JSON). 너무 커지지 않게 최근 MAX_ROWS 개만 남깁니다.
"""
import json
from datetime import datetime
from pathlib import Path

MAX_ROWS = 2000


def add(path: str | Path, who: str, action: str, detail: str = "", now: datetime | None = None) -> bool:
    """기록 한 줄을 더합니다. 성공하면 True. (기록에 실패해도 프로그램은 멈추지 않음)"""
    row = {"time": (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
           "who": who, "action": action, "detail": detail}
    path = Path(path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        lines = [ln for ln in lines if ln.strip()][-(MAX_ROWS - 1):] + [json.dumps(row, ensure_ascii=False)]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def load(path: str | Path, limit: int | None = None) -> list[dict]:
    """기록 목록 (최근 것이 먼저). 깨진 줄은 건너뜁니다."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for ln in reversed(lines):
        try:
            row = json.loads(ln)
        except ValueError:
            continue
        if isinstance(row, dict) and {"time", "who", "action"} <= row.keys():
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    return rows
