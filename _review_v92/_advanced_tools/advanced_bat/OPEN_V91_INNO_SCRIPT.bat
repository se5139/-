@echo off
cd /d "%~dp0\..\.."
echo [v91] Opening Inno Setup script...
if exist "installer\KakaoEmoticonSetup_v91.iss" start "" "installer\KakaoEmoticonSetup_v91.iss"
if not exist "installer\KakaoEmoticonSetup_v91.iss" echo [ERROR] installer\KakaoEmoticonSetup_v91.iss not found.
pause
