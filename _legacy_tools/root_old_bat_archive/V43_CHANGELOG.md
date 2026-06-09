# V43_CHANGELOG

## v43: 설치형 안정화/실행 오류 진단 강화

### 추가 기능
- `44 설치형 안정화/오류 진단` 탭 추가
- Python 버전, OS, 필수 파일, requirements.txt, 핵심 패키지, outputs 쓰기 권한 검사
- 사용자 데이터 분리 폴더 `%LOCALAPPDATA%/KakaoEmoticonProfitSystem/UserData` 확인/생성
- Streamlit 포트 충돌 검사: 8520, 8521, 8522, 8501
- 설치 경로 길이/특수문자 위험 경고
- `.venv` 존재 여부와 실행 BAT 파일 확인
- 오류 원인별 권장 복구 순서 자동 생성
- 경량 백업 및 지원용 ZIP 생성
- `10_V43_DIAGNOSE_AND_REPAIR.bat`, `11_V43_COLLECT_SUPPORT_PACKAGE.bat` 자동 생성 기능

### 유지 원칙
- 기존 v42까지의 제작/분석/학습/재패키징 기능 유지
- 원본 파일과 사용자 데이터 삭제 금지
- 자동 복구는 원본 삭제 없이 진단/재설치 안내/포트 정리/리포트 수집 중심
- 최종 설치형 안정화 전 단계로 사용
