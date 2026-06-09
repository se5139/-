# V90 Changelog

## 목적

v90은 새 기능을 무리하게 늘리는 버전이 아니라, 사용자가 제안한 간단한 출력 흐름을 반영한 핫픽스입니다.

## 변경 사항

- 정지형 최종 결과를 PNG 32개로 분리
- 움직이는형 최종 결과를 GIF 24개로 분리
- JPG는 확인용 미리보기로만 생성
- `v90_simple_png_gif_output` 폴더 생성
- `v90_submit_only_png_gif.zip` 생성
- `v90_simple_output_package.zip` 생성
- manifest JSON/CSV에 원문 문구와 안전 파일명 매핑 저장
- v89 이하 이전 버전 자동 백업 후 정리 유지
- 기본 5개 큰 흐름 유지
- 고급 세부 기능은 삭제하지 않고 유지

## 검증 항목

- Python compileall
- 핵심 모듈 import
- 정지형 PNG 32개 생성
- 움직이는 GIF 24개 생성
- JPG preview 생성
- Windows 파일명 금지문자 검사
- 특수문자 문구 원문 보존
- 기본 메뉴 5개 유지
- 루트 BAT 수 제한 유지
- 이전 버전 자동 정리 fake-flow 검사
- API 키 원문 검사
- ZIP 무결성 검사
- 압축 해제 후 재검사

## 제한

Windows Inno Setup EXE 컴파일은 Linux 기반 검증 환경에서 직접 수행하지 못했습니다. Windows PC에서 Inno Setup 설치 후 `00_DOUBLE_CLICK_THIS_FIRST_BUILD_SETUP_EXE.bat`로 생성해야 합니다.
