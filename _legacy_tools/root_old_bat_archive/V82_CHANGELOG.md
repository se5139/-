# V82 변경사항 - 단계 분리 설치 빌드/진단 핫픽스

v82는 새 기능 추가 버전이 아니라, v80/v81에서 사용자가 겪은 “검은 창만 보이고 멈춘 것처럼 보이는 빌드 문제”를 더 잘 확인하도록 만든 설치 빌드 안정화 버전입니다.

## 핵심

- `0_BUILD_WINDOWS_INSTALLER_EXE.bat` 실행 즉시 진행 로그 출력
- Inno Setup 탐지 과정을 단계별로 표시
- Inno Setup 컴파일 출력을 실시간으로 표시
- 느린 바로가기 재귀 탐색 제거
- 실패 시 `installer/v82_inno_build_report.json` 생성
- 수동 대체 경로 `OPEN_V82_INNO_SCRIPT.bat` 제공
- 기능 추가보다 설치/빌드 흐름 분리 검증에 집중

## 사용 순서

1. v82 ZIP을 짧은 경로에 압축 해제: `C:\KakaoEmoticonV82`
2. `44_V82_STEPWISE_BUILD_CHECK.bat` 실행
3. `0_BUILD_WINDOWS_INSTALLER_EXE.bat` 실행
4. 성공 시 `installer\Output\KakaoEmoticonSetup_v82.exe` 실행
5. 실패 시 `installer82_inno_build_report.json`을 확인
