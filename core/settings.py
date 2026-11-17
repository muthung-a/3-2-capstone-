"""사용자 설정(조회기간, 적정선, 경고 기준, 즐겨찾기)을 이 PC의 파일에 저장·불러오기.

파일: user_settings.json (프로젝트 폴더). 외부로 보내지 않습니다.
"""
import json
from pathlib import Path

DEFAULTS = {
    "span": 6,             # 조회기간(개월)
    "bed_target": 95.0,    # 병상가동율 적정선(%)
    "warn_pct": 10.0,      # 확인 필요 기준: 직전 12개월 평균 대비 ±%
    "favorites": [],       # 즐겨찾기 항목 이름들
}


def load(path: str | Path) -> dict:
    """설정 파일을 읽습니다. 없거나 깨졌으면 기본값을 돌려줍니다."""
    data = dict(DEFAULTS, favorites=[])
    try:
        saved = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return data
    for key, default in DEFAULTS.items():
        if isinstance(saved.get(key), type(default)) or (isinstance(default, float) and isinstance(saved.get(key), int)):
            data[key] = saved[key]
    return data


def save(path: str | Path, data: dict) -> bool:
    """설정을 파일에 저장합니다. 성공하면 True."""
    try:
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False
