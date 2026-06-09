# V63 CHANGELOG - Template Engine Manager

## 핵심 변경
- Jinja2를 주 템플릿 엔진으로 유지하고, HTML 리포트/프롬프트/모션 계획/룰북 템플릿을 분리 관리합니다.
- Mako를 선택 보조 템플릿 엔진으로 requirements에 추가했습니다.
- Django Template, Chameleon, Handlebars/Mustache 계열은 비교·검토 대상으로 두되 현재 Streamlit 로컬 앱에는 불필요한 런타임 의존성으로 판단하여 기본 탑재하지 않습니다.
- 새 좌측 메뉴: `53 템플릿 엔진 관리/분리 구조`.
- API 키 원문 저장 방지 검사를 유지합니다.

## 설계 기준
- 최종 프로그램은 Python 중심 로컬 PC 설치형 유지.
- 템플릿은 코드에서 분리하지만, 사용자 창작 데이터와 추상 트렌드 신호만 렌더링.
- 기존 기능 삭제 없음.
