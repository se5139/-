# GitHub에서 최신 배포 ZIP 받기

이 프로젝트의 최신 다른 PC 이동용 파일은 항상 아래 이름으로 유지됩니다.

```text
release/kakao_emoticon_v100_clean_latest.zip
```

## 바로 다운로드 링크

아래 주소를 브라우저 주소창에 붙여 넣으면 최신 ZIP을 바로 받을 수 있습니다.

```text
https://raw.githubusercontent.com/se5139/-/main/release/kakao_emoticon_v100_clean_latest.zip
```

체크섬 파일:

```text
https://raw.githubusercontent.com/se5139/-/main/release/kakao_emoticon_v100_clean_latest.sha256.txt
```

## 받은 뒤 실행 순서

1. `kakao_emoticon_v100_clean_latest.zip` 압축 풀기
2. 압축이 풀린 `kakao_emoticon_v100_clean` 폴더 열기
3. `VERIFY_PACKAGE.bat` 실행
4. OK가 나오면 `START_WINDOWS.bat` 실행
5. 브라우저가 열리지 않으면 `http://127.0.0.1:8520` 직접 열기

## 참고

- GitHub 화면에서 직접 받을 때는 `release` 폴더의 `kakao_emoticon_v100_clean_latest.zip`을 선택한 뒤 Download 버튼을 누르면 됩니다.
- 첫 실행에는 Python 3.10 이상이 필요합니다.
- API 키가 없어도 기본 기능은 실행됩니다.
