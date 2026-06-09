카카오 이모티콘 자동생성 프로그램 v90

이번 v90은 v89의 자동 업그레이드 정리 기능과 Windows 파일명 안전화를 유지하면서,
사용자 흐름을 더 단순하게 만들기 위해 출력 구조를 정리한 버전입니다.

핵심 변경:
- 안 움직이는 이모티콘 최종 후보: PNG 32개
- 움직이는 이모티콘 최종 후보: GIF 24개
- JPG는 제출용이 아니라 확인용 미리보기로만 별도 생성
- 최종 출력 폴더를 static_png_submit / animated_gif_submit / preview_jpg 로 분리
- 업그레이드 설치 성공 후 v89 이하 이전 버전 폴더 자동 백업 후 정리
- 현재 v90 폴더와 v90 이상 폴더는 정리 대상에서 제외

권장 실행 순서:
1. ZIP을 새 폴더에 압축 해제합니다.
   권장 위치: C:\KakaoEmoticonV90

2. 먼저 점검 파일을 실행합니다.
   47_V90_SIMPLE_PNG_GIF_OUTPUT_CHECK.bat

3. 설치마법사 EXE를 만들려면 실행합니다.
   00_DOUBLE_CLICK_THIS_FIRST_BUILD_SETUP_EXE.bat

4. 설치마법사 없이 바로 설치하려면 실행합니다.
   00_STEP_2_PORTABLE_INSTALL_NOW.bat

5. 프로그램 실행:
   00_STEP_3_START_PROGRAM.bat

v90 출력 구조:
- static_png_submit: 정지형 PNG 32개
- animated_gif_submit: 움직이는 GIF 24개
- preview_jpg: 확인용 JPG 미리보기
- metadata: 원문 문구와 파일 매핑 manifest

주의:
- JPG는 투명 배경이 필요한 최종 제출용으로 쓰지 않습니다.
- 제출 전에는 카카오 이모티콘 스튜디오의 최신 수량/용량/크기 기준을 다시 확인해야 합니다.
- 실제 KakaoEmoticonSetup_v90.exe 컴파일은 Windows PC에 Inno Setup이 설치되어 있어야 완료됩니다.
