# V91 Changelog

## 목적

v91은 새 기능 추가보다 초보자 실행 안정성과 안내 품질을 높이는 핫픽스입니다.
v90 Codex fixed 작업본의 개선사항을 유지하면서, 파일명은 KO인데 내용이 영어였던 초보자 안내문을 한국어로 보정하고 v91 버전 표기를 정리했습니다.

## 유지된 v90 Codex fixed 개선점

- 이전 버전 정리 current-version 표기 오류 보정 흐름 유지
- Inno Setup 빌드 리포트 버전 표기 보정 흐름 유지
- Jinja2 미설치 시 기본 HTML 리포트 fallback 유지
- 동일 초 내 생성 폴더 충돌 방지 suffix 유지
- preview_jpg 56개 정확 검사 유지
- 제출용 ZIP JPG/JPEG 미포함 검사 유지
- manifest JSON items 56개, manifest CSV row 56개 검사 유지

## v91 변경 사항

- `00_BEGINNER_RUN_GUIDE_KO.txt`를 한국어 초보자 안내문으로 전면 보정
- v91 실행/점검 BAT 표기 정리
- v91 Inno Setup 스크립트 추가
- v91 build/cleanup/shortcut/check 스크립트 추가
- 업그레이드 정리 기준을 v90 이하 이전 버전 정리로 갱신
- 현재 v91 및 v91 이상 폴더는 정리 제외

## 검증 항목

- Python compileall
- 핵심 모듈 import
- quick_check.py
- v91 simple PNG/GIF output check
- 정지형 PNG 32개 생성
- 움직이는 GIF 24개 생성
- JPG preview 56개 생성
- 제출용 ZIP JPG/JPEG 미포함
- manifest JSON/CSV 카운트 일치
- Windows 파일명 금지문자 검사
- 특수문자 문구 원문 보존
- 기본 메뉴 5개 유지
- 루트 BAT 수 제한 유지
- 이전 버전 자동 정리 fake-flow 검사
- API 키 원문 검사
- ZIP 무결성 검사
- 압축 해제 후 재검사

## 제한

Windows Inno Setup EXE 컴파일은 Linux 기반 검증 환경에서 직접 수행하지 못했습니다.
Windows PC에서 Inno Setup 설치 후 `00_DOUBLE_CLICK_THIS_FIRST_BUILD_SETUP_EXE.bat`로 생성해야 합니다.
