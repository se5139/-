# Kakao Emoticon Profit System v92

Python 중심 로컬 PC 실행/설치형 카카오톡 이모티콘 제작 보조 프로그램입니다.

## v92 핵심

- 정지형 최종 후보 PNG 32개
- 움직이는형 최종 후보 GIF 24개
- 확인용 JPG 56개
- 제출용 ZIP에는 PNG/GIF만 포함하고 JPG/JPEG 제외
- Windows 파일명 금지문자 안전화
- 특수문자 문구 원문 CSV/JSON 보존
- v91 이하 이전 버전 자동 정리 흐름
- 오류 ID 기반 안전 오류진단/로그 기능
- API 키/비밀번호/토큰 형태 값 마스킹
- 로그 저장 위치를 사용자 데이터 폴더로 분리

## 실행 순서

```bat
47_V92_ERROR_DIAGNOSTICS_OUTPUT_CHECK.bat
00_STEP_2_PORTABLE_INSTALL_NOW.bat
00_STEP_3_START_PROGRAM.bat
```

## 설치마법사 생성

Windows PC에서 Inno Setup 설치 후:

```bat
00_DOUBLE_CLICK_THIS_FIRST_BUILD_SETUP_EXE.bat
```

생성 위치:

```text
installer\Output\KakaoEmoticonSetup_v92.exe
```

## 기본 메뉴

1. 제작 시작 · 정지형/움직이는형 미리보기
2. 세트 구성 · 32개/24개 품질 진화
3. 검사 · 자동보정 · 제출 전 승인
4. 반려 대응 · 캡처/OCR · 재생성
5. 최종 납품 · 백업/리포트/재검사

## 안전 원칙

- 자동 제출 없음
- 타 캐릭터/상표/유명 캐릭터 복제 금지
- 온라인 자료는 추상 신호만 사용
- 유료 API 기본 OFF
- API 키 원문 저장 금지
- 사용자 데이터 승인 없는 삭제/덮어쓰기 금지
