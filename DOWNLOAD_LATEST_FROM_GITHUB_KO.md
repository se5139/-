# GitHub에서 최신 배포 ZIP 받기

이 프로젝트의 최신 다른 PC 이동용 파일은 항상 아래 이름으로 유지됩니다.

```text
release/kakao_emoticon_v100_clean_latest.zip
```

## 바로 다운로드 링크

저장소가 공개 상태이면 아래 주소로 최신 ZIP을 바로 받을 수 있습니다.

```text
https://raw.githubusercontent.com/se5139/-/main/release/kakao_emoticon_v100_clean_latest.zip
```

체크섬 파일:

```text
https://raw.githubusercontent.com/se5139/-/main/release/kakao_emoticon_v100_clean_latest.sha256.txt
```

저장소가 비공개이거나 로그인이 필요한 상태이면 raw 링크가 `404`처럼 보일 수 있습니다. 이 경우 아래 GitHub 폴더를 브라우저에서 열고 로그인한 뒤 직접 받으세요.

```text
https://github.com/se5139/-/tree/main/release
```

## 받은 뒤 실행 순서

1. `kakao_emoticon_v100_clean_latest.zip` 압축 풀기
2. 압축이 풀린 `kakao_emoticon_v100_clean` 폴더 열기
3. `VERIFY_PACKAGE.bat` 실행
4. OK가 나오면 `START_WINDOWS.bat` 실행
5. 브라우저가 열리지 않으면 `http://127.0.0.1:8520` 직접 열기

## 참고

- GitHub 화면에서 직접 받을 때는 `release` 폴더의 `kakao_emoticon_v100_clean_latest.zip`을 선택한 뒤 Download 버튼을 누르면 됩니다.
- Windows에서는 `DOWNLOAD_LATEST_RELEASE.bat`을 실행해 최신 ZIP과 체크섬을 `downloaded_release` 폴더로 받고 SHA256 검증까지 할 수 있습니다.
- 자동 다운로드가 실패하면 배치 파일이 GitHub release 폴더를 열어줍니다. 로그인 후 수동 다운로드하면 됩니다.
- 첫 실행에는 Python 3.10 이상이 필요합니다.
- API 키가 없어도 기본 기능은 실행됩니다.
