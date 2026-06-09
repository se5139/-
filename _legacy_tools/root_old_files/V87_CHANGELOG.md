# Kakao Emoticon Profit System v87

## 목적
v87은 새 대형 기능 추가 버전이 아니라, v86 기준의 **초보자 흐름 정리 + 실제 생성 검사 강화 핫픽스**입니다.

## 변경 사항
- v86 Windows 파일명 안전화 유지
- 루트 폴더 BAT 17개 → 8개로 축소
- 점검/진단/정리용 BAT는 `_advanced_tools/root_bat_archive_v86_visible/` 안으로 이동
- 기본 UI는 5개 큰 흐름 유지
- 고급 세부 기능은 Streamlit 사이드바의 “고급 세부 메뉴 보기” 안에 유지
- `47_V87_FULL_USER_FLOW_FILENAME_SAFETY_CHECK.bat` 추가
- 특수문자/한글/띄어쓰기/긴 문구/Windows 예약어를 실제 32개·24개 생성 흐름에 투입하는 검사 추가
- ZIP 내부 파일명까지 Windows 금지문자 검증
- API 키 원문 패턴 검사 추가

## 검증 결과 요약
- Python compileall: PASS
- 핵심 모듈 import: PASS
- 정지형 32개 생성: PASS
- 움직이는 후보 24개 생성: PASS
- GIF 5개 생성: PASS
- Windows 금지문자 파일명 검사: PASS
- 후보 ZIP 내부 파일명 검사: PASS
- 5개 기본 메뉴 유지 검사: PASS
- 루트 BAT 8개 이하 검사: PASS
- API 키 원문 패턴 검사: PASS
- ZIP 무결성 및 압축 해제 후 재검사: PASS

## 제한 사항
- 이 환경은 Linux 기반이므로 Windows용 Inno Setup EXE 컴파일은 직접 완료하지 못했습니다.
- Windows PC에서 Inno Setup 설치 후 `00_DOUBLE_CLICK_THIS_FIRST_BUILD_SETUP_EXE.bat` 실행이 필요합니다.
