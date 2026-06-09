# 카카오 이모티콘 자동생성 프로젝트

이 저장소는 카카오 이모티콘 제작을 돕는 Windows 중심 로컬 앱입니다.  
현재 실사용 기준 앱은 `_review_v92` 폴더에 있으며, Streamlit 기반으로 실행됩니다.

## 핵심 기능

- 러프 스케치 기반 자동완성: 사용자가 대충 원, 몸통, 팔다리 또는 자유 형태를 그리면 완성형 이모티콘 후보를 생성합니다.
- 정지형/움직이는형 생성: 러프 입력 기반으로 32개 PNG 후보와 24개 GIF 후보를 만들 수 있습니다.
- 창작 기록 보관: 러프 원본, 생성 설정, 해시, 생성 로그, 권리 확인 메모를 함께 저장합니다.
- 품질 검사: PNG/GIF 크기, 파일명 위험, 대비 부족, 잘림 가능성 등을 점검합니다.
- 자동저장/이어 만들기: 최근 작업 상태를 저장하고 다시 불러올 수 있습니다.
- 학습/분석 보조: 인터넷/영상/수동 입력 자료는 복제용이 아니라 제작 방향 참고 신호로 정리합니다.
- Windows 설치파일: `_deliverables_v92` 폴더에 실행형 설치 파일이 포함되어 있습니다.

주의: 이 프로그램은 제작 보조 도구입니다. 카카오 심사 통과, 수익, 법률 적합성을 보장하지 않습니다. 제출 전 최신 카카오 공식 기준, 저작권, 상표권, 유사성 여부는 직접 다시 확인해야 합니다.

## 폴더 구조

```text
.
├─ _review_v92/              # 현재 실행 기준 앱 소스
├─ _deliverables_v92/        # Windows 설치용 EXE와 소스 ZIP
├─ kakao_emoticon_v100_clean/# 실험/정리본
├─ README.md                 # 이 문서
└─ .gitignore                # 캐시, outputs, 로컬 도구 제외
```

## 다른 PC에서 실행하는 방법

### 방법 1. 설치파일로 실행

1. 이 저장소를 clone 또는 ZIP 다운로드합니다.
2. `_deliverables_v92` 폴더로 이동합니다.
3. `KakaoEmoticonSetup_v92_DirectCreationHotfix.exe`를 실행합니다.
4. 설치/압축 해제가 끝나면 안내에 따라 프로그램을 시작합니다.

### 방법 2. 소스에서 바로 실행

Windows 기준:

```bat
cd _review_v92
START_WINDOWS.bat
```

처음 실행 시 자동으로 `.venv` 가상환경을 만들고 `requirements.txt` 패키지를 설치합니다.  
브라우저가 자동으로 열리지 않으면 아래 주소를 직접 열면 됩니다.

```text
http://127.0.0.1:8520
```

### 방법 3. 수동 실행

Python 3.10 이상이 설치되어 있어야 합니다.

```bat
cd _review_v92
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1 --server.port 8520
```

## 빠른 점검

실행 전 주요 생성/검사 흐름을 확인하려면:

```bat
cd _review_v92
python quick_check.py
```

권한 문제로 `AppData` 쓰기가 막히는 환경에서는 `LOCALAPPDATA`를 사용자 쓰기 가능한 폴더로 지정한 뒤 실행할 수 있습니다.

## 현재 v92 설치 산출물

`_deliverables_v92` 폴더:

- `KakaoEmoticonSetup_v92_DirectCreationHotfix.exe`
- `kakao_emoticon_profit_system_v92_direct_creation_hotfix.zip`
- 각 파일의 `.sha256.txt` 체크섬

## 개발 메모

- 생성 결과물은 각 앱 폴더의 `outputs/` 아래에 만들어지며 Git에는 올리지 않습니다.
- `.venv`, `__pycache__`, 테스트 로컬 데이터, Codex가 내려받은 `_tools`는 Git에서 제외합니다.
- API 키, 비밀키, 개인 설정 파일은 저장소에 올리지 않습니다.

## GitHub 원격 저장소

이 프로젝트는 다음 저장소로 올리는 것을 기준으로 합니다.

```text
https://github.com/se5139/-.git
```
