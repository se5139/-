# Kakao Emoticon Profit System v90

Python 중심의 Windows 로컬 PC 실행/설치형 카카오톡 이모티콘 제작 보조 프로그램입니다.

이 저장소는 v90 간편 PNG/GIF 출력 구조를 기준으로 정리되어 있습니다.

## 핵심 출력 규칙

- 정지형 최종 제출 후보: `static_png_submit` 폴더의 PNG 32개
- 움직이는형 최종 제출 후보: `animated_gif_submit` 폴더의 GIF 24개
- `preview_jpg`는 눈으로 확인하는 미리보기 전용입니다.
- `v90_submit_only_png_gif.zip`에는 JPG가 들어가지 않습니다.
- 특수문자 문구 원문은 화면, CSV, JSON에 보존하고 파일명만 Windows 안전 이름으로 바꿉니다.
- 유료 API는 기본 OFF입니다.

## 기본 메뉴 5개 흐름

1. 제작 시작 · 정지형/움직이는형 미리보기
2. 세트 구성 · 32개/24개 품질 진화
3. 검사 · 자동보정 · 제출 전 승인
4. 반려 대응 · 캡처/OCR · 재생성
5. 최종 납품 · 백업/리포트/재검사

세부 기능은 고급 메뉴 안에 유지합니다.

## Windows에서 실행

처음 받은 PC에서는 먼저 Python 3.10 이상을 설치하고, 설치할 때 `Add Python to PATH`를 선택하세요.

```bat
00_STEP_2_PORTABLE_INSTALL_NOW.bat
```

설치가 끝나면 실행합니다.

```bat
00_STEP_3_START_PROGRAM.bat
```

브라우저가 자동으로 열리지 않으면 아래 주소를 직접 엽니다.

```text
http://127.0.0.1:8520
```

## 설치마법사 EXE

릴리스 산출물은 `release` 폴더에 있습니다.

- `release/KakaoEmoticonSetup_v90.exe`
- `release/KakaoEmoticonSetup_v90.exe.sha256.txt`
- `release/kakao_emoticon_profit_system_v90_simple_png_gif_output_hotfix_codex_fixed.zip`
- `release/FINAL_VALIDATION_RESULT_KO.txt`

설치마법사 EXE를 실행하면 Windows PC에 v90 프로그램을 설치하는 흐름으로 진행됩니다.

## 검증

기본 검사는 다음 BAT를 실행합니다.

```bat
47_V90_SIMPLE_PNG_GIF_OUTPUT_CHECK.bat
```

검증 항목:

- Python compileall
- 핵심 모듈 import
- PNG 32개 실제 생성
- GIF 24개 실제 생성
- JPG preview 56개 생성
- submit-only ZIP 내 JPG 미포함
- manifest JSON/CSV 카운트 일치
- Windows 파일명 금지문자 검사
- 특수문자 문구 원문 보존
- 기본 메뉴 5개 유지
- 루트 BAT 8개 이하
- v89 이하 이전 버전 정리 fake-flow
- API 키 원문 패턴 검사
- ZIP 무결성 검사

## 환경 복구

패키지 설치나 실행이 실패하면 아래 파일을 실행합니다.

```bat
4_REPAIR_ENVIRONMENT.bat
```

이 스크립트는 `.venv`를 다시 만들고 `requirements.txt`를 설치한 뒤 진단을 실행합니다.

## 데이터 보호

이전 버전 정리 기능은 현재 v90 이상 폴더를 제외합니다.

v89 이하로 보이는 이전 버전 폴더를 정리할 때는 사용자 데이터 후보를 먼저 백업한 뒤 처리합니다.

보존 후보:

- `outputs`, `output`, `user_data`, `data`, `settings`, `reports`, `backups`, `exports`, `projects`
- DB, JSON, CSV, Excel, TXT, HTML, PNG, JPG, GIF, ZIP

## 개발 메모

GitHub에는 실행 소스와 작은 릴리스 산출물만 올리는 것을 권장합니다.

생성 결과물, 가상환경, 캐시, 테스트용 로컬 데이터는 `.gitignore`로 제외합니다.
