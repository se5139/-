# v66 멀티툴 개발 실행/검증 파이프라인

v66은 지금까지 반영한 전문 IDE, 템플릿 엔진, 설치마법사, 검증 도구를 실제 개발 흐름으로 묶는 단계입니다.

## 원칙

- 최종 사용자는 Python 중심 로컬 PC 설치형 프로그램을 받습니다.
- PyCharm, VS Code, Visual Studio, WebStorm, Android Studio 등은 개발 효율을 높이는 보조 도구입니다.
- Jinja2는 HTML 리포트, 프롬프트, 모션 계획 같은 템플릿 산출물을 분리하는 주 템플릿 엔진입니다.
- Inno Setup은 Windows 설치마법사 생성에 사용합니다.
- 모든 수정 후 compileall, AST, Jinja 렌더링, ZIP 무결성, API 키 누출 검사를 수행합니다.

## 적용 단계

1. ChatGPT로 요구사항 정리
2. Python/PyCharm/VS Code로 핵심 로직 구현
3. Streamlit UI 연결
4. Jinja2 템플릿으로 리포트/프롬프트 분리
5. Pillow/pandas/openpyxl로 이미지·데이터 처리
6. pytest/ruff/mypy/compileall로 품질 검사
7. Inno Setup으로 설치마법사 생성
8. Git/GitHub Actions로 변경 이력과 자동검증 구조 준비
