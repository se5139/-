# 작업상태 동기화 가이드

이 문서는 현재 PC의 작업상태를 다른 PC로 옮기는 방법입니다.

## 내보내기: 현재 PC

1. 현재 PC의 앱 폴더에서 `EXPORT_SYNC_STATE.bat`을 실행합니다.
2. `release/sync_state_export_latest.zip`이 생성됩니다.
3. 이 ZIP을 USB, 클라우드, GitHub, 메신저 등으로 다른 PC에 옮깁니다.

포함되는 내용:

- `memory/evolution_memory.json`
- `memory/api_usage_ledger.json`
- 최근 `outputs/` 결과 폴더 10개
- `IMPORT_SYNC_STATE.bat`
- `scripts/import_sync_state.py`
- `SYNC_STATE_MANIFEST.json`

## 가져오기: 다른 PC

1. 먼저 프로그램 ZIP `kakao_emoticon_v100_clean_latest.zip`을 압축 해제합니다.
2. 그 폴더 안에 `sync_state_export_latest.zip`도 압축 해제합니다.
3. `IMPORT_SYNC_STATE.bat`을 실행합니다.
4. 완료 후 `START_HERE.bat`을 실행합니다.

## 안전장치

- 기존 메모리 파일은 `.backup_날짜시간` 이름으로 백업한 뒤 교체합니다.
- 기존 `outputs/` 폴더는 삭제하지 않고, 동기화 ZIP 안의 최근 결과물만 추가/덮어씁니다.
- API 키 자체는 포함하지 않습니다. 키는 환경변수로 따로 설정해야 합니다.

## 주의

- 전체 `outputs/`는 용량이 커질 수 있어 기본으로는 최근 10개만 포함합니다.
- 전체 결과물을 옮기고 싶으면 `outputs/` 폴더를 별도로 압축해서 옮기세요.
