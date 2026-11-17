# 경영통계 대시보드 (캡스톤)

Streamlit으로 만드는 대시보드입니다. 지금은 **뼈대만** 있어서 실행하면 빈 화면이 뜹니다.

---

## 처음 한 번만 할 일 (설치)

> 이미 `.venv` 폴더가 있다면 건너뛰세요.

1. Python **3.12**가 설치되어 있어야 합니다.
2. 이 폴더에서 PowerShell(또는 명령 프롬프트)을 열고 아래를 차례로 입력합니다.

```
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

- 첫 줄: 이 프로젝트 전용 파이썬 공간(**가상환경**, `.venv` 폴더)을 만듭니다.
  다른 프로젝트와 패키지가 섞이지 않게 해 줍니다.
- 둘째 줄: `requirements.txt`에 적힌 패키지를 **정해진 버전 그대로** 설치합니다.

## 실행하기

- `실행.bat`을 **더블클릭**하면 브라우저에 http://localhost:8501 이 열립니다.
- 끄려면 까만 창을 닫으면 됩니다.

## 테스트 돌리기

```
.venv\Scripts\python -m pytest
```

`tests/test_rules.py`가 아래 "규칙"을 잘 지켰는지 자동으로 검사합니다.

---

## 폴더와 파일 설명

```
캡스톤_경영통계_대시보드/
├─ app.py              ← 시작 파일. 화면 조각을 "조립"만 함
├─ config.py           ← 설정값 모음 (제목, 버전, 저장 폴더 등)
├─ core/               ← 계산하는 코드 (화면 코드 X)
├─ ui/                 ← 화면 코드
│  ├─ theme.py         ← 색·글꼴 등 꾸미기
│  ├─ sidebar.py       ← 왼쪽 사이드바
│  └─ pages/           ← 탭 화면들 (탭 하나 = 파일 하나)
│     └─ overview.py   ← "개요" 탭
├─ reports/            ← 엑셀·HTML 보고서 파일을 만드는 코드
├─ tests/              ← 자동 테스트
├─ .streamlit/config.toml ← Streamlit 설정 (보안 설정 포함, 지우지 마세요)
├─ requirements.txt    ← 설치할 패키지와 버전
├─ 실행.bat            ← 더블클릭 실행 파일
├─ CLAUDE.md           ← AI(Claude)가 지켜야 할 규칙
├─ .venv/              ← 가상환경 (직접 건드리지 않음)
└─ _기존_프로토타입/   ← 예전 프로토타입 보관 (참고용)
```

### 각 폴더에 무엇을 넣나요?

| 위치 | 넣는 것 | 예시 | 넣으면 안 되는 것 |
|---|---|---|---|
| `app.py` | 탭 목록, 화면 배치 | `TABS = [("개요", overview)]` | 계산 코드, 긴 화면 코드 |
| `config.py` | 바뀔 수 있는 값 | 제목, 기준선 숫자, 폴더 경로 | 함수, 계산 |
| `core/` | 숫자를 계산하는 함수 | `월별_합계(df)`, `증감률(이번달, 지난달)` | `import streamlit` |
| `ui/theme.py` | 화면 꾸미기 | CSS | 계산 |
| `ui/sidebar.py` | 사이드바 위젯 | 파일 업로드, 기준월 선택 | 계산 |
| `ui/pages/` | 탭 화면 파일 | `trend.py`, `detail.py` | 계산 (core에서 불러다 씀) |
| `reports/` | 보고서 파일 저장 코드 | `엑셀로_저장(결과, 경로)` | `import streamlit` |
| `tests/` | `test_`로 시작하는 테스트 파일 | `test_core.py` | 실제 병원 데이터 |

### 왜 이렇게 나누나요?

- **계산(core)과 화면(ui)을 나누면** 계산이 맞는지 화면 없이 테스트로 확인할 수 있습니다.
- **탭 하나 = 파일 하나**로 하면 파일이 짧아져서 찾기·고치기가 쉽습니다.
- 파일이 300줄을 넘으면 너무 길다는 신호입니다. 나눠 주세요.

---

## 새 탭 추가하는 법 (예: "추이" 탭)

1. `ui/pages/trend.py` 파일을 만들고 아래처럼 씁니다.

   ```python
   import streamlit as st


   def render() -> None:
       st.write("추이 화면")
   ```

2. `app.py`를 열어 두 곳을 고칩니다.

   ```python
   from ui.pages import overview, trend   # trend 추가

   TABS = [
       ("개요", overview),
       ("추이", trend),                    # 이 줄 추가
   ]
   ```

3. `실행.bat`을 다시 실행하면 탭이 생깁니다.

---

## 규칙 (중요)

1. **병원 엑셀 파일은 AI(Claude, ChatGPT 등)에게 보여주거나 올리지 않습니다.**
2. `core/`, `reports/`에서는 `streamlit`을 쓰지 않습니다.
3. `eval()`, `exec()`는 쓰지 않습니다.
4. 파이썬 파일 하나는 300줄 이하로 유지합니다.
5. 병원 데이터는 이 PC 안에서만 처리합니다. 외부 서버(Streamlit Cloud 등)에 올리지 않습니다.
