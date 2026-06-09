# v56 Windows 설치마법사 빌드 가이드

## 목적
v56는 기존 ZIP + BAT 방식에서 발생한 경로/인코딩/PowerShell 문제를 줄이기 위해 Inno Setup 설치마법사 방식으로 전환한 버전입니다.

## Windows에서 설치마법사 EXE 만들기
1. Inno Setup 6 설치
2. 이 폴더에서 `BUILD_V56_SETUP_EXE.bat` 실행
3. 생성 파일 확인: `installer\Output\KakaoEmoticonSetup_v56.exe`

## 설치마법사 기능
- 설치 위치: `%LOCALAPPDATA%\KakaoEmoticonProfitSystemV56`
- 바탕화면 바로가기 생성
- 시작 메뉴 바로가기 생성
- Windows 앱 제거/삭제 항목 등록
- 선택 시 이전 버전 정리 helper 실행
- 설치 후 Python 환경 준비/프로그램 실행 선택 가능

## 주의
이 샌드박스는 Windows Inno Setup Compiler를 실행할 수 없어 실제 EXE 컴파일은 못 했습니다. 대신 Inno Setup 스크립트, 빌드 BAT, Python 검증은 완료했습니다.
