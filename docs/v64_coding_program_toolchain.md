# v65 코딩 프로그램/툴체인 반영 문서

## 고정 기준

최종 납품 파일은 Python 중심 로컬 PC 실행/설치형 프로그램으로 유지한다. 다른 코딩 프로그램은 프로젝트 목적에 맞을 때만 보조로 사용한다.

## 포함한 코딩 프로그램 분류

1. 프로그래밍 언어: Python 중심, JavaScript/TypeScript/HTML/CSS는 UI/웹 보조 검토.
2. 코드 편집기/IDE: VS Code, PyCharm, Visual Studio를 개발 보조 도구로 분류.
3. 버전관리: Git/GitHub를 버전 이력, 롤백, 릴리스 태그용으로 분류.
4. 빌드/패키징: PyInstaller, Inno Setup, ZIP, SHA-256 검증을 사용.
5. AI 코딩 보조: ChatGPT, Copilot, Cursor, Replit AI는 개발 보조로만 사용.
6. 템플릿 엔진: Jinja2를 주 엔진으로 사용하고 Mako는 선택 보조 어댑터로 유지.

## 적용 원칙

- Streamlit은 현재 UI 계층으로 유지한다.
- Jinja2는 HTML 리포트, 프롬프트 팩, CSV/JSON 텍스트 산출물 생성에 사용한다.
- Mako는 고급 프롬프트/코드형 템플릿에 한해 선택적으로 사용한다.
- Django Template, Chameleon, Handlebars/Mustache는 구조 검토 대상으로 기록하되 기본 의존성으로 무리하게 넣지 않는다.
- API 키 원문은 문서, 리포트, ZIP에 저장하지 않는다.
