"""데이터 점검: 올린 엑셀에서 프로그램이 쓰는 항목을 모두 찾을 수 있는지 확인합니다.

병원 실제 파일을 넣었을 때 "어떤 항목 이름을 맞추면 되는지"를 바로 알 수 있게 합니다.
(데이터 값은 보지 않고, 항목 이름이 있는지만 봅니다)
"""
from dataclasses import dataclass

import pandas as pd

import config
from core import monthly


@dataclass
class Item:
    where: str     # 어디서 쓰는지. 예) '개요 카드', '비용 탭'
    name: str      # 화면 이름
    path: str      # 엑셀에서 찾는 이름. 예) '총진료비 > 합계 > 소계'
    found: bool


def _specs() -> list[tuple[str, str, tuple]]:
    """(어디서, 이름, 찾을 항목 이름들) 목록. 같은 항목은 한 번만."""
    groups = [("개요 카드", [(n, l) for n, l, _ in config.KPIS]),
              ("확인 필요 항목", [(n, l) for n, l, _ in config.ALERT_ITEMS]),
              ("미입력 검사", list(config.NEVER_ZERO)),
              ("환자·병상 표", [(n, l) for n, l, _ in config.PATIENT_DETAIL]),
              ("수익 표", [(n.strip(), l) for n, l, _ in config.REVENUE_DETAIL]),
              ("비용 탭", list(config.COST_ITEMS)),
              ("환자·병상 탭", [("병상가동율", ("병상가동율",)), ("실입원수", ("입원환자수", "실입원수")),
                             ("실퇴원수", ("퇴원환자수", "실퇴원수"))]),
              ("비용 탭", [("간병 총수입", ("간병", "총수입", "합계")), ("간병 손익", ("간병", "손익")),
                         ("위생소모품 매출", ("위생소모품", "매출", "합계")),
                         ("기저귀 처리비용", ("기저귀폐기물", "처리비용"))])]
    seen, out = set(), []
    for where, items in groups:
        for name, labels in items:
            if tuple(labels) not in seen:
                seen.add(tuple(labels))
                out.append((where, name, tuple(labels)))
    return out


def check(df: pd.DataFrame) -> list[Item]:
    """프로그램이 쓰는 항목·구역을 엑셀에서 찾을 수 있는지 모두 확인합니다."""
    items = []
    for where, name, labels in _specs():
        try:
            monthly.find_index(df, *labels)
            ok = True
        except KeyError:
            ok = False
        items.append(Item(where, name, " > ".join(labels), ok))
    sections = set(df["대분류"])
    for tab, section in config.CHART_SECTIONS:
        items.append(Item(f"{tab} 그래프", section, section, section in sections))
    return items
