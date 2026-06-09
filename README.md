# Kakao Emoticon Maker

이 저장소는 카카오 이모티콘 제작 보조 프로그램입니다. 현재 기본 실행 기준은 원격 저장소의 `v100 clean` 구조이고, 기존 v92 패키지는 `_review_v92`와 `_deliverables_v92`에 보관되어 있습니다.

## 먼저 실행

Windows에서 가장 간단한 실행:

```bat
START_HERE.bat
```

또는:

```bat
START_WINDOWS.bat
```

브라우저가 자동으로 열리지 않으면 아래 주소를 직접 엽니다.

```text
http://127.0.0.1:8520
```

## 다른 PC에서 이어가기

```bat
git clone https://github.com/se5139/my-app.git kakao-emoticon
cd kakao-emoticon
START_HERE.bat
```

실행 전 점검:

```bat
VERIFY_PACKAGE.bat
```

최신 배포 ZIP을 GitHub에서 받는 방법은 `DOWNLOAD_LATEST_FROM_GITHUB_KO.md`와 `DOWNLOAD_LATEST_RELEASE.bat`을 참고합니다.

## 주요 기능

- 러프 스케치 업로드와 캐릭터 일관성 보조
- 정지형 PNG와 움직이는 GIF 후보 생성
- 카카오 제출 전 규격, 용량, 문구, 위험 표현 점검
- 사람 제작 증빙 패키지 생성
- 조사 URL/메모 기반 로컬 진화 메모리 저장
- API 키 없이 기본 작동
- API 사용 시 비용 방지를 위한 호출 한도 장부 적용
- 최근 결과물, 갤러리, ZIP, 리포트 확인 페이지 제공

주의: 이 프로그램은 제작 보조 도구입니다. 카카오 심사 통과, 수익, 법적 적합성을 보장하지 않습니다. 최종 제출 전 최신 카카오 공식 기준, 저작권, 상표권, 초상권, 생성형 AI 관련 정책을 직접 확인해야 합니다.

## v92 설치파일

기존 v92 설치파일과 배포 ZIP은 `_deliverables_v92` 폴더에 있습니다.

- `KakaoEmoticonSetup_v92_DirectCreationHotfix.exe`
- `kakao_emoticon_profit_system_v92_direct_creation_hotfix.zip`
- 각 파일의 `.sha256.txt` 체크섬

v92 소스에서 직접 실행:

```bat
cd _review_v92
START_WINDOWS.bat
```

## 바탕화면 바로가기 문제 해결

`Codex 앱 자체 바로가기`는 이 프로젝트 설치파일이 만들 수 없습니다. Codex는 별도 앱/도구이므로 Windows에 설치된 Codex 실행 파일이나 앱 설정에서 바로가기를 만들어야 합니다.

`이모티콘 프로그램 바로가기`가 안 생기는 경우는 이번 v92 수정으로 보완했습니다.

원인:

- 기존 v92 스크립트가 `pywin32`가 없으면 바로가기 생성을 건너뜀
- OneDrive 또는 한국어 Windows의 `바탕 화면` 경로 탐지 실패
- Git 소스에서 바로 실행해 설치 단계가 실행되지 않음
- 보안 프로그램이나 권한 설정이 `.lnk` 생성을 차단

해결:

```bat
cd _review_v92
00_STEP_5_CREATE_DESKTOP_SHORTCUTS.bat
```

현재 v92는 `pywin32` 없이도 PowerShell COM 방식으로 `.lnk` 생성을 시도합니다. `.lnk` 생성이 차단되면 실행 가능한 `.url` 대체 바로가기를 생성합니다.

## 동기화 상태 옮기기

현재 PC의 메모리와 최근 결과물을 다른 PC로 옮기려면:

```bat
EXPORT_SYNC_STATE.bat
```

다른 PC에서는:

```bat
IMPORT_SYNC_STATE.bat
```

자세한 내용은 `SYNC_STATE_GUIDE_KO.md`를 확인합니다.

## API 사용 정책

기본 실행에는 API 키가 필요 없습니다.

- 필수 API 없음
- OpenAI API 없음
- YouTube API 없음
- 검색 API 없음

API를 쓰려면 키와 호출 한도 환경변수를 함께 설정해야 합니다. 한도가 없거나 0이면 호출하지 않습니다.

예:

- `YOUTUBE_API_KEY` + `YOUTUBE_API_DAILY_CALL_LIMIT`
- `SEARCH_API_KEY` + `SEARCH_API_DAILY_CALL_LIMIT`
- `GEMINI_API_KEY` + `GEMINI_API_DAILY_CALL_LIMIT`
- `OPENAI_API_KEY` + `OPENAI_API_31D_CALL_LIMIT`

사용량은 `memory/api_usage_ledger.json`에 저장됩니다.

## 결과물

생성 결과는 기본적으로 `outputs/` 아래에 저장됩니다.

- 제출 후보 ZIP
- PNG/GIF 후보
- 미리보기 갤러리
- 검증 리포트
- 문구 품질 리포트
- 사람 제작 증빙 패키지

`outputs/`, `.venv/`, `__pycache__/`, `.git/`, 로그, 기존 ZIP/EXE 산출물은 배포 ZIP에서 제외됩니다.
