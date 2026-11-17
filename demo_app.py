r"""인터넷 시연판 진입점 (Streamlit Community Cloud 등에 올릴 때 이 파일을 지정).

- 코드로 만든 가상 데이터(core/sample.py)만 씁니다. 파일 올리기 칸이 없어 실제 병원 데이터가 들어올 수 없습니다.
- 병원에서 쓰는 버전은 app.py (PC 설치형, 실행.bat) 입니다.
내 PC에서 미리 보기:  .venv\Scripts\python -m streamlit run demo_app.py
"""
import app

app.main(demo=True)
