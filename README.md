# 카카오 이모티콘 자동생성 프로젝트

현재 실행 기준 소스는 `_review_v92` 폴더입니다. Windows에서 Streamlit 기반 프로그램으로 실행합니다.

## 핵심 기능

- 러프 스케치 기반 자동완성: 사용자가 대충 얼굴, 몸통, 팔다리 또는 자유 형태를 그리면 완성형 이모티콘 후보를 생성합니다.
- 제출 패키지 생성: 정지형 PNG 32개, 움직이는 GIF 24개 후보와 제출용 ZIP을 만듭니다.
- 창작 기록 보관: 원본 러프, 생성 설정, 해시, 생성 로그, 권리 확인 메모를 함께 저장합니다.
- 사전 검수: PNG/GIF 크기, 파일명 위험, 대비 부족, 글자 잘림 가능성을 확인합니다.
- 자동 저장과 이어서 만들기: 최근 작업 상태를 저장하고 다시 불러올 수 있습니다.
- Windows 설치파일: `_deliverables_v92` 폴더에 설치 EXE와 배포 ZIP이 있습니다.

주의: 이 프로그램은 제작 보조 도구입니다. 카카오 심사 통과, 수익, 법적 적합성을 보장하지 않습니다. 제출 전 최신 카카오 공식 기준, 저작권, 상표권, 초상권 문제를 직접 확인해야 합니다.

## 빠른 실행

```bat
cd _review_v92
START_WINDOWS.bat
```

브라우저가 자동으로 열리지 않으면 아래 주소를 직접 엽니다.

```text
http://127.0.0.1:8520
```

## Windows 설치파일로 실행

1. `_deliverables_v92` 폴더로 이동합니다.
2. `KakaoEmoticonSetup_v92_DirectCreationHotfix.exe`를 실행합니다.
3. 설치 후 바탕화면의 `Kakao Emoticon Profit System v92` 바로가기를 실행합니다.
4. 바로가기가 안 생기면 `_review_v92\00_STEP_5_CREATE_DESKTOP_SHORTCUTS.bat`를 실행합니다.

## 다른 PC에서 이어가기

```bat
git clone https://github.com/se5139/-.git kakao-emoticon
cd kakao-emoticon
cd _review_v92
START_WINDOWS.bat
```

수동 실행이 필요하면:

```bat
cd _review_v92
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1 --server.port 8520
```

## 바탕화면 바로가기 문제 해결

바로가기가 안 생기는 주된 원인은 다음 중 하나입니다.

- 기존 스크립트가 `pywin32`가 없으면 바로가기 생성을 건너뛰었습니다.
- OneDrive 또는 한국어 Windows의 `바탕 화면` 경로를 제대로 찾지 못했습니다.
- 설치 프로그램이 아니라 Git 소스에서 바로 실행한 경우 바로가기 생성 단계가 실행되지 않았습니다.
- 보안 프로그램이나 권한 설정이 `.lnk` 생성을 막았습니다.

현재 v92는 `pywin32` 없이도 PowerShell COM 방식으로 `.lnk`를 생성하고, 실패하면 `.bat` 실행 파일을 대체 생성합니다.

```bat
cd _review_v92
00_STEP_5_CREATE_DESKTOP_SHORTCUTS.bat
```

## 빠른 점검

```bat
cd _review_v92
python quick_check.py
```

## 배포 파일

`_deliverables_v92` 폴더:

- `KakaoEmoticonSetup_v92_DirectCreationHotfix.exe`
- `kakao_emoticon_profit_system_v92_direct_creation_hotfix.zip`
- 각 파일의 `.sha256.txt` 체크섬

## GitHub 저장소

```text
https://github.com/se5139/-.git
```
