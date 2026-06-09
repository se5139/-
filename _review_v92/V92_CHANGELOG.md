# V92_CHANGELOG

## v92 오류진단/로그 안정화 핫픽스

v92는 v91의 한국어 초보자 안내와 간편 PNG/GIF 출력 구조를 유지하면서, 오류 발생 시 원인 추적이 쉬워지도록 안전 오류진단/로그 구조를 추가한 안정화 버전입니다.

### 핵심 변경

- `modules/system_safety/error_logging.py` 추가
- 오류 ID 기반 중앙 오류 기록 추가
- 사용자 행동 로그 추가
- PNG/GIF 생성 및 주요 흐름 성능 로그 추가
- API 키/비밀번호/토큰 형태 값 저장 전 마스킹
- 로그 저장 위치를 프로그램 코드 폴더가 아니라 사용자 데이터 폴더로 분리
- 로그 파일 용량 제한 및 롤링 보관 적용
- 5번 `최종 납품 · 백업/리포트/재검사` 안에 `v92 안전 오류진단 · 로그/성능 리포트` 고급 진단 영역 추가
- `47_V92_ERROR_DIAGNOSTICS_OUTPUT_CHECK.bat` 추가
- `scripts/v92_error_diagnostics_output_check.py` 추가
- `scripts/cleanup_old_versions_v92.py`, `scripts/build_inno_installer_v92.py`, `scripts/create_shortcuts_v92.py` 추가
- `installer/KakaoEmoticonSetup_v92.iss` 추가

### 유지된 기능

- 기본 메뉴 5개 큰 흐름 유지
- 고급 세부 기능 숨김 유지
- 정지형 최종 후보 PNG 32개
- 움직이는형 최종 후보 GIF 24개
- 확인용 JPG 56개
- 제출용 ZIP에 JPG/JPEG 미포함
- Windows 파일명 금지문자 안전화
- 특수문자 문구 원문 CSV/JSON 보존
- v91 이하 이전 버전 자동 정리 흐름
- API 키 원문 저장 금지
- 유료 API 기본 OFF
- 로컬 파일/ZIP 분석 우선

### 로그 저장 위치

Windows 기준:

```text
%LOCALAPPDATA%\KakaoEmoticonProfitSystemV92\logs
```

Linux/macOS 테스트 환경 기준:

```text
~/.local/share/KakaoEmoticonProfitSystemV92/logs
```

### 주의

v92는 오류진단/로그 안정화 핫픽스입니다. 카카오 이모티콘 스튜디오 제출 기준은 변경될 수 있으므로 제출 직전 공식 기준을 다시 확인해야 합니다.
