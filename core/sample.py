"""시연용 가짜 데이터: 병원 월별 통계표·약품 처방 시트와 '같은 모양'의 엑셀을 코드로 만듭니다.

- 값은 모두 난수(무작위)이고, 사람 이름·주민번호 같은 개인 정보 형태는 전혀 없습니다.
- 인터넷에 올리는 시연판(demo_app.py)과 테스트에서 씁니다. 실제 병원 파일은 필요 없습니다.
- 같은 seed 면 언제나 같은 숫자가 나옵니다.
"""
import io
from datetime import datetime

import numpy as np
from openpyxl import Workbook

MONTHS = 24          # 2024-10 ~ 2026-09
START = (2024, 10)
BEDS = 215
INS = ["공단", "보호", "자보"]


def _months():
    y, m = START
    out = []
    for _ in range(MONTHS):
        out.append(datetime(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


class _Sheet:
    """통계표 한 줄씩 쌓기: add(['대분류','중분류','소분류','세부','비고'], 월별 값)"""

    def __init__(self):
        self.rows = []

    def add(self, labels, values):
        cells = [x or None for x in labels] + [None] * (5 - len(labels))  # 빈 이름은 빈칸으로
        self.rows.append((cells, [float(v) for v in values]))
        return np.asarray(values, dtype=float)


def _walk(rng, base, vol, n=MONTHS, trend=0.0):
    """기준값 근처에서 조금씩 움직이는 월별 값."""
    steps = rng.normal(trend, vol, n).cumsum()
    return np.maximum(base * (1 + steps), 0)


def _monthly(rng) -> _Sheet:
    s, n = _Sheet(), MONTHS
    days = np.array([(m.replace(month=m.month % 12 + 1, year=m.year + m.month // 12) - m).days for m in _months()])
    # 환자
    adm = rng.integers(25, 45, n)
    s.add(["입원환자수", "", "", "입원"], adm - 3)
    s.add(["입원환자수", "", "", "재입원"], np.full(n, 2))
    s.add(["입원환자수", "", "", "전원"], np.full(n, 1))
    s.add(["입원환자수", "", "", "실입원수"], adm)
    dis = adm + rng.integers(-4, 5, n)
    s.add(["퇴원환자수", "", "", "전원"], np.full(n, 2))
    s.add(["퇴원환자수", "", "", "퇴원"], dis - 6)
    s.add(["퇴원환자수", "", "", "사망"], np.full(n, 4))
    s.add(["퇴원환자수", "", "", "실퇴원수"], dis)
    census = {k: np.round(_walk(rng, b, 0.01)) for k, b in zip(INS, (125, 80, 3))}
    for k in INS:
        s.add(["월말재원환자수", "", "", k], census[k])
    s.add(["월말재원환자수", "", "", "합계"], sum(census.values()))
    avg = {k: census[k] * rng.uniform(0.98, 1.02, n) for k in INS}
    for k in INS:
        s.add(["총재원환자수", "", "", k], avg[k] * days)
        s.add(["평균재원환자수", "", "", k], avg[k])
    avg_total = s.add(["평균재원환자수", "", "", "합계"], sum(avg.values()))
    s.add(["병상가동율", "", "", "%"], avg_total / BEDS)
    groups = [("A1", "의료최고도", 2), ("A2", "의료고도", 50), ("A3", "의료중도", 90), ("A6", "의료경도", 50), ("A7", "선택입원군", 18)]
    g_total = np.zeros(n)
    for code, name, b in groups:
        g_total += s.add(["환자군수", "", code, name], np.round(_walk(rng, b, 0.03)))
    s.add(["환자군수", "", "합계"], g_total)
    # 진료비 (보험자 청구 + 본인부담)
    claim = {k: avg[k] * rng.uniform(2.6e6, 3.2e6, n) for k in INS}
    copay = {k: claim[k] * r for k, r in zip(INS, (0.18, 0.02, 0.0))}
    copay["일반"] = rng.uniform(2e5, 1.5e6, n)
    for k in INS:
        s.add(["총진료비", "청구금액(입원+외래)", "", k], claim[k])
    s.add(["총진료비", "청구금액(입원+외래)", "", "소계"], sum(claim.values()))
    for k in INS + ["일반"]:
        s.add(["총진료비", "본인부담금(입원+외래)", "", k], copay[k])
    s.add(["총진료비", "본인부담금(입원+외래)", "", "소계"], sum(copay.values()))
    total = {k: claim.get(k, 0) + copay[k] for k in INS + ["일반"]}
    for k in INS + ["일반"]:
        s.add(["총진료비", "합계", "", k], total[k])
    s.add(["총진료비", "합계", "", "소계"], sum(total.values()))
    for k in INS:
        s.add(["평균진료비", "총진료비/평균재원", "", k], total[k] / avg[k])
    s.add(["평균진료비", "총진료비/평균재원", "", "일반"], copay["일반"] / avg_total)
    sums = {(c, d): np.zeros(n) for c in ("의과", "한방") for d in ("외래", "입원")}
    for k in INS:
        for c, share in (("의과", 0.95), ("한방", 0.05)):
            for d, part in (("외래", 0.002), ("입원", 0.998)):
                v = claim[k] * share * part
                sums[(c, d)] += s.add(["청구금액", k, c, d], v)
    for (c, d), v in sums.items():
        s.add(["청구금액", "합계", c, d], v)
    s.add(["청구금액", "합계"], sum(claim.values()))
    # 재활치료 · 기타 행위 · 한의사
    rehab = [("MM105", "중추신경계발달재활치료", 1.4e7), ("MM112", "작업치료-복합작업치료", 1e6),
             ("MM113", "작업치료-특수작업치료", 7e6), ("MM151", "기능적전기자극치료", 6e6),
             ("MM301", "재활기능치료-매트및이동치료", 8e6), ("MX141", "연하장애재활치료", 1.3e6)]
    r_total = np.zeros(n)
    for code, name, b in rehab:
        r_total += s.add(["재활치료", "", code, name], _walk(rng, b, 0.04))
    s.add(["재활치료", "", "소계"], r_total)
    manual = s.add(["재활치료", "", "도수치료", "비급여"], _walk(rng, 5e6, 0.05))
    cryo = s.add(["재활치료", "", "크라이오"], _walk(rng, 4e5, 0.05))
    s.add(["재활치료", "", "소계"], manual + cryo)
    for name in ("고빈도흉벽진동요법", "방광스캐너"):
        s.add([name, "", "행위별", "실인원"], rng.integers(2, 9, n))
        s.add([name, "", "행위별", "총진료비"], _walk(rng, 6e5, 0.06))
    o1 = s.add(["의료용산소", "", "포괄수가(실청구X)"], _walk(rng, 9e5, 0.05))
    o2 = s.add(["의료용산소", "", "행위별수가(실청구O)"], _walk(rng, 4e5, 0.05))
    s.add(["의료용산소", "", "합계"], o1 + o2)
    k_total = np.zeros(n)
    for i, b in enumerate((9e6, 1.2e7, 8e6)):
        k_total += s.add(["한의사별총진료비", "", f"한방진료{i + 1}"], _walk(rng, b, 0.05))
    s.add(["한의사별총진료비", "", "합계"], k_total)
    _costs(s, rng, avg_total, total)
    return s


def _costs(s: _Sheet, rng, avg_total, total) -> None:
    n = MONTHS
    vendors = [s.add(["식자재", "", "식자재", f"식자재업체{c}"], _walk(rng, b, 0.04))
               for c, b in (("A", 1.8e7), ("B", 1.1e7), ("C", 4e6))]
    s.add(["식자재", "", "식자재", "합계"], sum(vendors))
    for name, b in (("경관식", 3000), ("환자식", 16000), ("직원식", 4000)):
        s.add(["식자재", "", "식수", name], _walk(rng, b, 0.02))
    for name, b in (("경관식", 1200), ("환자+직원식", 1500), ("총식단가", 1450)):
        s.add(["식자재", "", "식단가", name], _walk(rng, b, 0.02))
    drug_in = [s.add(["의약품", "", "입고", f"의약품업체{c}"], _walk(rng, b, 0.06)) for c, b in (("A", 2.4e7), ("B", 1.5e6))]
    s.add(["의약품", "", "입고", "합계"], sum(drug_in))
    pay = s.add(["의약품", "", "환자당투약", "급여"], _walk(rng, 1.15e5, 0.03))
    non = s.add(["의약품", "", "환자당투약", "비급여"], _walk(rng, 1.5e4, 0.05))
    s.add(["의약품", "", "환자당투약", "합계"], pay + non)
    buy = [s.add(["위생소모품", "", "매입", k], _walk(rng, b, 0.05)) for k, b in (("기저귀", 8.5e6), ("점보롤외", 2e6))]
    buy_t = s.add(["위생소모품", "", "매입", "합계"], sum(buy))
    sell = [s.add(["위생소모품", "", "매출", k], _walk(rng, b, 0.05)) for k, b in (("기저귀", 1.05e7), ("소모품", 2.6e6))]
    sell_t = s.add(["위생소모품", "", "매출", "합계"], sum(sell))
    profit = s.add(["위생소모품", "", "수익"], sell_t - buy_t)
    waste = s.add(["기저귀폐기물", "", "처리비용"], _walk(rng, 3.2e6, 0.02))
    s.add(["기저귀폐기물", "", "위생소모품수익 - 처리비용"], profit - waste)
    med = [s.add(["의료소모품", "", f"의료소모품업체{c}", "", item], _walk(rng, b, 0.08))
           for c, item, b in (("A", "소모품", 3e6), ("B", "당뇨시험지", 5e5), ("C", "약포장기", 5e5))]
    s.add(["의료소모품", "", "합계"], sum(med))
    inc = {k: avg_total * share * rng.uniform(7500, 9500, n) * 30
           for k, share in (("보험", 0.6), ("보호", 0.38), ("자보", 0.02))}
    for k, v in inc.items():
        s.add(["간병", "", "총수입", "보험종별", k], v)
    inc_t = s.add(["간병", "", "총수입", "보험종별", "합계"], sum(inc.values()))
    fee = s.add(["간병", "", "지급수수료", "간병수수료"], inc_t * rng.uniform(1.35, 1.55, n))
    assoc = s.add(["간병", "", "지급수수료", "협회수수료"], np.full(n, 2.16e6))
    s.add(["간병", "", "지급수수료", "합계"], fee + assoc)
    s.add(["간병", "", "손익", "간병비-인건비"], inc_t - fee - assoc)
    labor_name = "인건비(퇴직금,복리후생비,일용직제외)"
    staff = [("의사인력", "의사,한의사", 6.5e7), ("간호인력", "간호사,간호조무사", 2.1e8),
             ("필요인력", "약사,의료기사,사회복지사", 7e7), ("조리종사자", "영양사,조리사,조리원", 4.2e7),
             ("행정,관리", "행정,관리,기타", 4.5e7)]
    labor = [s.add([labor_name, "", g, d], _walk(rng, b, 0.02)) for g, d, b in staff]
    labor_t = sum(labor)
    labor_t[-1] = 0.0  # 시연: 마지막 달 인건비 '미입력' (0) → 미입력 의심 표시를 보여주기 위함
    s.add([labor_name, "", "합계"], labor_t)
    over = [s.add(["관리비", "", k], _walk(rng, b, 0.06)) for k, b in
            (("전력비", 1.1e7), ("상하수도", 3e6), ("지급수수료", 1.5e6), ("수선비", 1e5))]
    s.add(["관리비", "", "합계"], sum(over))


def _drug_sheet(wb, month: int, rng) -> None:
    """약품 처방 시트(시트 이름 = 달). 진료과별 수량·금액, 구역마다 소계 줄."""
    depts = ["EM", "내과1", "내과2", "신경외과", "내과2", "정형외과", "당직의사"]
    ws = wb.create_sheet(str(month))
    ws.append(["정의코드", "청구코드", "명 칭", "제약회사", "구입거래처", "분류번호", "효능코드", "단위",
               "처방횟수", "단가", "총수량", "총금액", None] + depts + [None] + depts + ["합계"])
    code = 640000000
    for section, count in (("정", 18), ("주", 8), ("비급여", 4)):
        sub = np.zeros(len(depts))
        for i in range(count):
            code += 1
            price = float(rng.integers(50, 3000)) if section != "비급여" else float(rng.integers(20000, 90000))
            qty = np.where(rng.random(len(depts)) < 0.4, rng.integers(1, 120, len(depts)), 0).astype(float)
            amt = qty * price
            sub += amt
            ws.append([code, code, f"가상약품{code % 1000:03d}{section}", f"가상제약{i % 5}", None, 200 + i,
                       None, section, int(rng.integers(5, 200)), price, float(qty.sum()), float(amt.sum()), None]
                      + qty.tolist() + [None] + amt.tolist() + [float(amt.sum())])
        ws.append([None] * 13 + [None] * len(depts) + [None] + sub.tolist() + [float(sub.sum())])  # 구역 소계


def build_workbook(seed: int = 7) -> bytes:
    """시연용 가짜 엑셀 파일 내용(bytes)."""
    rng = np.random.default_rng(seed)
    wb = Workbook()
    ws = wb.active
    ws.title = "Sample data"
    months = _months()
    ws.append(["구분", None, None, None, None] + months + ["합계(최근1년)"])
    ws.append([None] * 5 + [31] * len(months))
    for labels, values in _monthly(rng).rows:
        ws.append(labels + values)
    for month in range(6, 12):
        _drug_sheet(wb, month, rng)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
