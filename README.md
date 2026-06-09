# Kakao Emoticon Profit System

Python 중심의 로컬 PC 실행형 카카오톡 이모티콘 제작 보조 프로그램입니다.

현재 저장소 루트는 사용자가 요청한 **v90 간편 PNG/GIF 출력 hotfix 기준**으로 실행할 수 있게 정리되어 있습니다. GitHub 원격 저장소에 이미 있던 v92/v100 관련 자료는 삭제하지 않고 보존했습니다.

## 빠른 실행

### Windows에서 처음 실행

1. Python 3.10 이상을 설치합니다.
2. Python 설치 화면에서 `Add Python to PATH`를 체크합니다.
3. 이 저장소를 받습니다.

```powershell
git clone https://github.com/se5139/-.git
cd -
```

4. 설치 배치 파일을 실행합니다.

```powershell
.\00_STEP_2_PORTABLE_INSTALL_NOW.bat
```

5. 프로그램을 시작합니다.

```powershell
.\00_STEP_3_START_PROGRAM.bat
```

또는 루트 실행 파일을 직접 실행할 수 있습니다.

```powershell
.\START_WINDOWS.bat
```

6. 브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:8520
```

### 설치 마법사로 실행

Windows PC에서는 아래 설치 파일을 사용할 수 있습니다.

```text
release/KakaoEmoticonSetup_v90.exe
```

무결성 확인용 SHA-256 파일은 함께 들어 있습니다.

```text
release/KakaoEmoticonSetup_v90.exe.sha256.txt
```

## 기본 메뉴

프로그램은 v90 기준의 5개 큰 흐름을 유지합니다.

1. 제작 시작, 정지형/움직이는형 미리보기
2. 세트 구성, 32개/24개 품질 진화
3. 검사, 자동보정, 제출 전 승인
4. 반려 대응, 캡처/OCR, 재생성
5. 최종 납품, 백업/리포트/재검사

세부 기능과 고급 도구는 `_advanced_tools/` 아래에 보관되어 있습니다.

## 제출 파일 기준

- 정지형 최종 제출 파일: PNG 32개
- 움직이는형 최종 제출 파일: GIF 24개
- JPG는 확인용 preview 파일로만 사용합니다.
- 제출용 ZIP에는 JPG가 들어가면 안 됩니다.
- Windows 파일명 금지문자는 안전하게 치환합니다.
- 특수문자 문구 원문은 화면, CSV, JSON에 보존합니다.
- API 키 원문은 리포트, ZIP, CSV, JSON에 포함하지 않습니다.
- 유료 API는 기본 OFF입니다.

## 검증

v90 핵심 검사는 아래 파일로 실행할 수 있습니다.

```powershell
.\47_V90_SIMPLE_PNG_GIF_OUTPUT_CHECK.bat
```

Codex 검증 산출물은 `release/` 폴더에 함께 보관했습니다.

```text
release/FINAL_VALIDATION_RESULT_KO.txt
release/00_BEGINNER_RUN_GUIDE_KO.txt
release/kakao_emoticon_profit_system_v90_simple_png_gif_output_hotfix_codex_fixed.zip
release/kakao_emoticon_profit_system_v90_simple_png_gif_output_hotfix_codex_fixed.zip.sha256.txt
```

## 사용자 데이터 보호

이 프로젝트는 사용자 데이터를 삭제하거나 덮어쓰지 않는 방향을 우선합니다. 버전 정리 스크립트는 이전 버전 후보를 백업 대상으로 먼저 분류하고, 현재 버전과 상위 버전은 삭제 대상에서 제외하도록 설계되어 있습니다.

## 보존된 이전/상위 버전 자료

원격 저장소에 이미 있던 자료는 병합 과정에서 보존했습니다.

```text
_review_v92/
_deliverables_v92/
KAKAO_SAFE_WORKFLOW.md
RESEARCH_SOURCES.md
memory/
```

v92 설치 파일은 아래 위치에 있습니다.

```text
_deliverables_v92/KakaoEmoticonSetup_v92_DirectCreationHotfix.exe
```

원격 이력에 있던 v100 관련 문서도 유지했지만, 이 저장소 루트에서 바로 실행되는 기본 프로그램은 v90 기준입니다.
