# v59 Safe Old-Version Cleanup Installer

## Fixed
- v58/v56 설치마법사에서는 이전 버전 정리 옵션을 체크하지 않으면 C:\ 에 직접 압축 해제된 오래된 폴더가 남을 수 있었다.
- v58 `run_cleanup_old_versions_v58.bat`가 실제 삭제 인자 `--yes`를 전달하지 않아 dry-run 리포트만 생성되는 문제가 있었다.
- 일부 활성 BAT 파일에 v53/v57 표시와 경로가 남아 있었다.

## Added
- `scripts/cleanup_old_versions_v59.py`: Python 기반 안전 정리 엔진.
- `run_cleanup_old_versions_v59.bat`: 설치 후 실제 정리 실행.
- `14_V59_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat`: 사용자가 수동으로 이전 버전을 다시 정리할 수 있는 실행 파일.
- `26_V59_SAFE_CLEANUP_CHECK.bat`: v59 정리 기능 자체 점검.
- Inno Setup 설치마법사에서 `Run safe old-version cleanup after install` 기본 체크.
- 바탕화면 바로가기: `Kakao Emoticon Profit System v59 - Clean Old Versions`.

## Safety
- 삭제 대상은 이름이 `kakao_emoticon_profit_system_vXX`, `KakaoEmoticonProfitSystemVXX`, `KakaoEmoticonVXX` 형태이고 현재 버전보다 낮은 폴더만 해당.
- `outputs`, `user_data`, `settings`, `reports`, `projects`, `database`, `history`, `performance`, `backups` 등 사용자 데이터 폴더는 삭제 전 백업.
- 현재 v59 설치 폴더와 실행 중인 폴더는 보호.
- 전체 C드라이브, 사용자 홈, LocalAppData 루트 자체는 삭제하지 않음.
