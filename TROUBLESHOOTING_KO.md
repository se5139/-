# 문제 해결 가이드

## 1. Python을 찾을 수 없다고 나올 때

증상:

- `[ERROR] Python was not found.`
- `py` 또는 `python` 명령을 찾을 수 없음

해결:

1. Python 3.10 이상을 설치합니다.
2. 설치 화면에서 `Add Python to PATH`를 체크합니다.
3. 명령 프롬프트를 새로 열고 다시 `START_HERE.bat`을 실행합니다.

## 2. 패키지 설치가 실패할 때

증상:

- `Package installation failed`
- `pip install -r requirements.txt` 실패

해결:

1. 인터넷 연결을 확인합니다.
2. 보안 프로그램이 Python 또는 pip를 막는지 확인합니다.
3. 다시 `START_HERE.bat`을 실행합니다.

참고: 현재 필수 패키지는 `Pillow` 하나입니다.

## 3. 브라우저가 자동으로 열리지 않을 때

아래 주소를 Chrome 또는 Edge 주소창에 직접 입력하세요.

```text
http://127.0.0.1:8520
```

## 4. 포트 8520이 이미 사용 중일 때

`START_WINDOWS.bat`은 실행 전에 `scripts/stop_port.py`로 기존 8520 서버를 정리하려고 시도합니다.

그래도 안 되면:

1. 열려 있는 `Kakao Emoticon v100 Server` 창을 닫습니다.
2. 다시 `START_HERE.bat`을 실행합니다.
3. 필요하면 PC를 재부팅한 뒤 다시 실행합니다.

## 5. VERIFY_PACKAGE.bat이 실패할 때

가능한 원인:

- ZIP 압축을 완전히 풀지 않음
- 일부 파일만 복사함
- 보안 프로그램이 `.bat` 또는 `.py` 파일을 격리함

해결:

1. `kakao_emoticon_v100_clean_latest.zip`을 다시 받습니다.
2. ZIP 전체를 새 폴더에 압축 해제합니다.
3. `VERIFY_PACKAGE.bat`을 다시 실행합니다.

## 6. GitHub 자동 다운로드가 실패할 때

저장소가 비공개이거나 로그인이 필요하면 raw 다운로드가 실패할 수 있습니다.

해결:

1. `DOWNLOAD_LATEST_RELEASE.bat`이 열어주는 GitHub release 폴더로 이동합니다.
2. GitHub에 로그인합니다.
3. `kakao_emoticon_v100_clean_latest.zip`을 직접 다운로드합니다.

## 7. API 키가 없어도 되는지

기본 기능은 API 키 없이 실행됩니다.

- 이모티콘 시안 생성
- 제출 후보 ZIP 생성
- 검수 리포트 생성
- 수동 URL/조사 메모 기반 분석

API 키는 향후 고도화 기능용이며 필수 조건이 아닙니다.
