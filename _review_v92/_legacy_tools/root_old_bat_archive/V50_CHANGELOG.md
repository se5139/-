# v50 무료 API 수집 안전모드 + 로컬 우선 품질 진화

## 추가 기능
- API 키 입력 영역 분리: YouTube / Google Search / OpenAI
- 최근 30일 수집 기준 고정
- 쿼터 카운터 표시: YouTube 검색, 영상 상세, 댓글, Google Search, OpenAI 분석
- 기본 유료 호출 차단: `paid_calls_allowed=False`
- 로컬 파일/ZIP 분석 우선: 이미지, GIF, TXT, CSV, JSON, SRT, VTT, ZIP
- API 키 원문 저장 금지: 리포트에는 masked preview만 기록
- 수집 결과를 표현 은행/텍스트 초안/정지형·움직이는형 제작 흐름에 적용

## 안전 원칙
- 초기 기본값은 비용 0원 모드
- 사용자가 직접 켜지 않으면 OpenAI/Google Search는 실행 대상으로 표시하지 않음
- 외부 자료는 기존 캐릭터 복제 목적이 아니라 감정 빈도·문구 길이·포즈 유형·모션 리듬 같은 추상 신호만 반영
