@echo off
setlocal
cd /d "%~dp0"
if exist "installer\KakaoEmoticonSetup_v70.iss" (
  start "" "installer\KakaoEmoticonSetup_v70.iss"
) else (
  echo Missing installer\KakaoEmoticonSetup_v70.iss
  pause
)
