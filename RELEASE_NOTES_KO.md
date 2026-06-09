# Kakao Emoticon Maker v100 Clean 릴리즈 노트

## 현재 배포본

- 배포 파일: `release/kakao_emoticon_v100_clean_latest.zip`
- 실행 방식: 내 PC에서만 열리는 무료 로컬 웹서버
- 기본 주소: `http://127.0.0.1:8520`
- 첫 실행 파일: `START_WINDOWS.bat`
- 실행 전 점검 파일: `VERIFY_PACKAGE.bat`

## 핵심 기능

- 러프 스케치와 콘셉트 기반 이모티콘 시안 생성
- 일반/미니, 정지형/움직이는 모드 분리
- PNG/GIF 제출 후보 ZIP 생성
- 용량 최적화와 제출 전 검사 리포트 생성
- 사람 제작 증빙 패키지 생성
- 자료 수집/분석, 저작권/AI 정책 리스크 점검
- API 한도 도달 시 무료 수집/분석 방식으로 fallback
- 다른 PC 이동용 portable ZIP 자동 생성

## 다른 PC 실행 순서

1. `kakao_emoticon_v100_clean_latest.zip` 압축 풀기
2. `VERIFY_PACKAGE.bat` 실행
3. 통과하면 `START_WINDOWS.bat` 실행
4. 브라우저가 열리지 않으면 `http://127.0.0.1:8520` 직접 열기

## 주의사항

- 카카오 이모티콘 정책과 제출 규격은 바뀔 수 있으므로 최종 제출 전 최신 공식 화면에서 다시 확인해야 합니다.
- 생성 결과는 제작 보조/시안이며, 실제 제출은 사람이 직접 만든 원본과 작업 증빙을 기준으로 준비해야 합니다.
- API 키는 필수가 아닙니다. 키를 쓰는 경우에도 앱 자체 한도와 fallback 정책을 사용합니다.
