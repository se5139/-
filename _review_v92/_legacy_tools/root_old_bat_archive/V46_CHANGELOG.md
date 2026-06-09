# V46 Old Version Cleanup Installer

## 핵심 변경

v46은 v45 시작/설치 안정화 버전을 기준으로, 최신 버전 설치 시 이전 버전 설치 파일과 바탕화면 바로가기가 계속 쌓이는 문제를 줄이기 위해 **이전 버전 정리 기능**을 추가한 버전입니다.

## 추가된 기능

- `scripts/cleanup_old_versions.ps1`
  - `%LOCALAPPDATA%` 내부의 `KakaoEmoticonProfitSystemV이전버전` 설치 폴더를 탐지합니다.
  - 바탕화면/OneDrive 바탕화면의 `Kakao Emoticon Profit System v이전버전` 바로가기를 탐지합니다.
  - 현재 버전 v46보다 낮은 버전만 정리 후보로 표시합니다.
  - 사용자가 `Y`를 입력한 경우에만 정리합니다.

- `14_V46_CLEAN_OLD_VERSIONS.bat`
  - 설치 후에도 수동으로 이전 버전 정리를 다시 실행할 수 있는 도구입니다.

- `1_INSTALL_NOW.bat` 개선
  - 설치 과정 초반에 이전 버전 정리 단계를 표시합니다.
  - 정리를 원하지 않으면 Enter 또는 N으로 건너뛸 수 있습니다.
  - 정리 후 v46 설치를 계속 진행합니다.

## 데이터 보호 원칙

정리 기능은 다음 원칙을 지킵니다.

1. 다운로드/문서/사진/바탕화면 전체 폴더 같은 개인 파일 영역은 자동 삭제하지 않습니다.
2. 정리 대상은 `%LOCALAPPDATA%` 안의 본 프로그램 이전 버전 폴더와 바탕화면 바로가기만입니다.
3. 이전 버전 폴더 안의 `outputs`, `user_data`, `settings`, `performance_data`, `strategy_reports`, `reports`, `projects`, `backups`, `data`, `databases` 등은 ZIP 백업 후 정리합니다.
4. 정리 리포트와 백업 ZIP은 `%LOCALAPPDATA%\KakaoEmoticonProfitSystemUserData\old_version_cleanup_backups` 아래에 저장됩니다.
5. 사용자가 승인하지 않으면 이전 버전 정리를 하지 않습니다.

## 유지된 기능

- v11~v45의 기존 기능 삭제 없음
- v45 설치/실행 안정화 구조 유지
- Python 중심 로컬 PC 실행/설치형 프로그램 구조 유지
- Streamlit 로컬 실행 방식 유지
- 진단/복구/지원 패키지 생성 기능 유지
