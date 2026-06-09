# v37 변경사항 — 1차 포맷 추천 + 단계별 확장 전략 엔진

## 핵심 변경
- 처음부터 모든 포맷을 제작하지 않고, 현재 캐릭터와 데이터 상태에 맞는 1차 제작 포맷 1개를 추천합니다.
- 미니/큰/움직이는/시리즈 포맷은 보류 후보로 저장하고, 심사·품질·판매 반응 데이터가 쌓인 뒤 다시 판단합니다.
- v20 성장형 학습 엔진, v29 반려 사유 개선, v30 제출 전 잠금 체크리스트, v36 카카오 규격 검수와 연결되는 운영 전략 리포트를 생성합니다.

## 추가 파일
- `modules/format_strategy/format_strategy_engine.py`
- `modules/format_strategy/__init__.py`
- `v37_format_strategy_check.py`

## 생성 리포트
- `format_strategy_v37.html`
- `format_strategy_v37.json`
- `format_strategy_v37_scores.csv`
- `format_strategy_v37_roadmap.csv`
- `format_strategy_v37_data_requirements.csv`
- `format_strategy_v37_notes.txt`
- `format_strategy_v37.zip`

## 설계 원칙
- 첫 제작은 가장 근거가 강한 1개 포맷만 선택합니다.
- 전체 포맷 변환/자동 제작은 선택형 도구로만 유지합니다.
- 확장 판단에는 심사 결과, 반려 사유, 품질 점수, 채팅 미리보기 점수, 판매/사용 반응 데이터를 사용합니다.
