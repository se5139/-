# GitHub에서 최신 배포 ZIP 받기

현재 기준 저장소:

```text
https://github.com/se5139/my-app.git
```

최신 다른 PC 이동용 ZIP은 항상 아래 경로에 둡니다.

```text
release/kakao_emoticon_v100_clean_latest.zip
```

## 바로 다운로드 링크

저장소가 공개 상태라면 아래 링크로 최신 ZIP을 받을 수 있습니다.

```text
https://raw.githubusercontent.com/se5139/my-app/main/release/kakao_emoticon_v100_clean_latest.zip
```

체크섬 파일:

```text
https://raw.githubusercontent.com/se5139/my-app/main/release/kakao_emoticon_v100_clean_latest.sha256.txt
```

저장소가 비공개이거나 로그인이 필요한 경우 raw 링크가 `404`처럼 보일 수 있습니다. 그때는 GitHub에 로그인한 뒤 아래 폴더에서 직접 다운로드합니다.

```text
https://github.com/se5139/my-app/tree/main/release
```

## 실행 순서

1. `kakao_emoticon_v100_clean_latest.zip`을 다운로드합니다.
2. 원하는 위치에 압축을 풉니다.
3. 압축 해제된 폴더에서 `START_HERE.bat`을 실행합니다.
4. 실행 전 점검만 하고 싶으면 `VERIFY_PACKAGE.bat`을 먼저 실행합니다.
5. 브라우저가 열리지 않으면 `http://127.0.0.1:8520`을 직접 엽니다.

## Git으로 이어가기

Git을 사용할 수 있으면 ZIP보다 아래 방식이 더 편합니다.

```bat
git clone https://github.com/se5139/my-app.git kakao-emoticon
cd kakao-emoticon
START_HERE.bat
```

## 참고

- Windows에서는 `DOWNLOAD_LATEST_RELEASE.bat`을 실행하면 최신 ZIP과 SHA256 파일을 `downloaded_release` 폴더로 받을 수 있습니다.
- 첫 실행에는 Python 3.10 이상이 필요합니다.
- 첫 실행 중 Pillow 설치가 필요할 수 있어 인터넷 연결이 필요할 수 있습니다.
- API 키가 없어도 기본 기능은 작동합니다.
