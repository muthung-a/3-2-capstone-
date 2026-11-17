"""화면 전체에서 함께 쓰는 '지금 보고 있는 조건' 묶음.

사이드바에서 고른 파일·기준월·조회기간·적정선 등을 하나로 묶어 각 탭에 넘깁니다.
"""
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class View:
    df: pd.DataFrame          # 월별 통계표 (미입력 의심 칸은 빈칸 처리됨)
    month: object             # 기준월 (pd.Period)
    months: list              # 조회기간에 들어가는 달들 (기준월 포함, 오래된 순)
    bed_target: float = 95.0  # 병상가동율 적정선(%)
    warn_pct: float = 10.0    # 확인 필요 기준(±%)
    file_name: str = ""       # 불러온 파일 이름
    settings: dict = field(default_factory=dict)  # 저장된 사용자 설정 (즐겨찾기 등)
