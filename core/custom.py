"""사용자 정의 통계·즐겨찾기: 통계표의 '모든 항목'을 이름으로 골라 쓰기.

엑셀에 새 항목(행)이 생기면 코드 수정 없이 자동으로 목록에 나타납니다.
"""
import pandas as pd

from core import monthly
from core.summary import pct


def row_labels(df: pd.DataFrame) -> pd.Series:
    """줄마다 '대분류 > 중분류 > …' 이름. 같은 이름이 또 나오면 ' (2)' 를 붙여 구분합니다."""
    seen: dict[str, int] = {}
    names = []
    for row in df[monthly.LABEL_COLS].itertuples(index=False):
        name = " > ".join(x for x in row if x)
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return pd.Series(names, index=df.index)


def frame_for(df: pd.DataFrame, chosen: list[str], months: list) -> pd.DataFrame:
    """고른 항목들을 '항목 × 월' 숫자 표로. 목록에 없는 이름은 건너뜁니다."""
    labels = row_labels(df)
    idx = {name: i for i, name in labels.items()}
    rows = [c for c in chosen if c in idx]
    out = df.loc[[idx[c] for c in rows], months].astype(float)
    out.index = rows
    return out


def favorites_table(df: pd.DataFrame, chosen: list[str], month) -> pd.DataFrame:
    """즐겨찾기 표: 당월, 전월, 전월 대비(%), 전년 동월, 전년 대비(%)."""
    cols = monthly.month_columns(df)
    P, Y = month - 1, month - 12
    frame = frame_for(df, chosen, [m for m in (month, P, Y) if m in cols])
    rows = []
    for name, r in frame.iterrows():
        cur, prv, yoy = r.get(month), r.get(P, float("nan")), r.get(Y, float("nan"))
        rows.append({"항목": name, "당월": cur, "전월": prv, "전월 대비(%)": pct(cur, prv),
                     "전년 동월": yoy, "전년 대비(%)": pct(cur, yoy)})
    return pd.DataFrame(rows, columns=["항목", "당월", "전월", "전월 대비(%)", "전년 동월", "전년 대비(%)"])
