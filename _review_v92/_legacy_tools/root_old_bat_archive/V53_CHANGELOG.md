# v53 설치 정리/바탕화면 아이콘 안정화

- 이전 버전 LocalAppData 설치 폴더 정리뿐 아니라 C:\ 아래에 압축 해제된 `kakao_emoticon_profit_system_vXX...` 폴더도 정리 후보로 탐지합니다.
- 현재 실행 중인 v53 원본 폴더와 설치 대상 폴더는 보호합니다.
- `outputs`, `user_data`, `settings`, `reports`, `projects`, `database` 등 사용자 데이터 후보는 백업 후 정리합니다.
- 바탕화면 바로가기를 `DesktopDirectory`, `사용자 Desktop`, `OneDrive\Desktop` 후보에 생성합니다.
- `3_CREATE_SHORTCUTS_ONLY.bat`의 오래된 v48 스크립트 호출 문제를 수정했습니다.
