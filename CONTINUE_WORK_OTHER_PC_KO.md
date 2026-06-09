# 다른 PC에서 이어서 작업하기

이 문서는 `https://github.com/se5139/my-app.git` 저장소를 다른 Windows PC에서 받아서 실행하고, 수정한 뒤 다시 GitHub에 저장하는 흐름을 정리한 안내입니다.

## 1. 처음 한 번만 준비

1. Git for Windows를 설치합니다.
2. Python 3.10 이상을 설치합니다.
3. Python 설치 화면에서 `Add Python to PATH`를 체크합니다.
4. 작업할 폴더에서 PowerShell을 엽니다.
5. 저장소를 받습니다.

```powershell
git clone https://github.com/se5139/my-app.git
cd my-app
```

6. 실행 환경을 설치합니다.

```powershell
.\00_STEP_2_PORTABLE_INSTALL_NOW.bat
```

7. 프로그램을 실행합니다.

```powershell
.\00_STEP_3_START_PROGRAM.bat
```

브라우저 주소:

```text
http://127.0.0.1:8520
```

## 2. 작업 시작 전 최신 내용 받기

다른 PC에서 작업을 시작하기 전에는 항상 최신 내용을 먼저 받는 것이 안전합니다.

```powershell
.\PULL_LATEST_BEFORE_WORK.bat
```

이 파일은 현재 PC에 저장하지 않은 변경사항이 있으면 자동으로 멈춥니다. 이때는 먼저 변경사항을 저장하거나 백업한 뒤 다시 실행하세요.

## 3. 수정 후 GitHub에 저장하기

수정이 끝나면 아래 파일을 실행합니다.

```powershell
.\SAVE_WORK_TO_GITHUB.bat
```

실행하면 커밋 메시지를 물어봅니다. 예:

```text
Fix v90 preview generation
Update beginner guide
Add installer note
```

스크립트는 아래 순서로 처리합니다.

1. 변경 파일 확인
2. 전체 변경사항 stage
3. commit 생성
4. GitHub 최신 내용 rebase
5. GitHub에 push

## 4. 충돌이 났을 때

동시에 여러 PC에서 같은 파일을 고치면 Git 충돌이 날 수 있습니다.

초보자 기준으로는 아래 순서를 권장합니다.

1. 충돌 메시지가 나오면 창을 닫지 말고 그대로 둡니다.
2. `git status`를 실행해서 충돌 파일명을 확인합니다.
3. 충돌 파일을 열어 `<<<<<<<`, `=======`, `>>>>>>>` 표시를 정리합니다.
4. 정리 후 아래 명령을 실행합니다.

```powershell
git add .
git rebase --continue
git push origin main
```

어렵다면 충돌난 파일명과 화면 메시지를 그대로 복사해서 도움을 요청하면 됩니다.

## 5. 작업 규칙

- 작업 전에는 `PULL_LATEST_BEFORE_WORK.bat`를 먼저 실행합니다.
- 작업 후에는 `SAVE_WORK_TO_GITHUB.bat`로 저장합니다.
- API 키나 비밀번호가 들어간 파일은 GitHub에 올리지 않습니다.
- `outputs/`, `.venv/`, 임시 테스트 폴더는 GitHub에 올리지 않습니다.
- 사용자 데이터는 삭제하지 말고 필요한 경우 먼저 백업합니다.

## 6. 현재 기준

- 기본 실행 저장소: `https://github.com/se5139/my-app.git`
- 기본 브랜치: `main`
- 루트 실행 기준: v90 간편 PNG/GIF 출력 hotfix
- Windows 설치 파일: `release/KakaoEmoticonSetup_v90.exe`
- 다른 PC 동기화 ZIP: `release/sync_state_export_latest.zip`
