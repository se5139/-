# v48 후보 적용 / 정지형 캐릭터 품질 진화 업데이트

## 핵심 수정

1. 사용자가 실행 영상에서 확인한 `StreamlitDuplicateElementId` 문제를 수정했습니다.
   - 여러 `radio`/입력 위젯에 고유 key를 부여했습니다.
   - v48 검증 스크립트에서 반복 라벨·무key 위젯을 정적 검사합니다.

2. 후보가 표로만 보이고 끝나는 문제를 수정했습니다.
   - 최근 30일 트렌드 추천 문구를 표현 은행에 적용할 수 있습니다.
   - v28 누락 정보 후보 선택값을 v27 텍스트 초안, 표현 은행, 후보 갤러리 흐름에 적용할 수 있습니다.
   - v48 진화형 품질 프로필을 현재 제작 흐름에 적용할 수 있습니다.

3. 정지형 캐릭터 품질 개선 엔진을 추가했습니다.
   - 유튜브/인터넷 참고 메모, 영상 제목, 댓글 경향, URL 메모를 입력합니다.
   - 기존 캐릭터를 복제하지 않고 감정 빈도, 문구 길이, 포즈 유형, 선명도, 실루엣 같은 추상 신호만 분석합니다.
   - 정지형 품질 점수, 독창성 방어 점수, 개선 액션, 32개 표현 씨앗, 품질 보드 PNG, HTML/JSON/CSV/ZIP 리포트를 생성합니다.

4. 설치/정리 안정성을 유지했습니다.
   - v48 설치 경로: `%LOCALAPPDATA%\KakaoEmoticonProfitSystemV48`
   - 이전 버전 정리는 사용자가 Y를 입력해야만 실행됩니다.
   - 이전 버전 사용자 데이터는 백업 후 보존합니다.

## 추가 파일

- `modules/evolution_quality/character_evolution_engine.py`
- `15_V48_CANDIDATE_APPLY_EVOLUTION_CHECK.bat`
- `scripts/v48_candidate_apply_evolution_check.py`
- `V48_CHANGELOG.md`
- `V48_FIRST_RUN_GUIDE.txt`

## 주의

유튜브/인터넷 자료는 자동 무단 크롤링이나 캐릭터 복제용이 아닙니다. 공식 API, 사용자가 직접 입력한 메모, CSV/캡처 입력, 약관을 지키는 수집 방식을 기준으로 합니다.
