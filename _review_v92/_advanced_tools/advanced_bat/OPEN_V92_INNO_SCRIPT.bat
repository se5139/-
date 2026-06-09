@echo off
cd /d "%~dp0\..\.."
echo [v92] Opening Inno Setup script...
if exist "installer\KakaoEmoticonSetup_v92.iss" start "" "installer\KakaoEmoticonSetup_v92.iss"
if not exist "installer\KakaoEmoticonSetup_v92.iss" echo [ERROR] installer\KakaoEmoticonSetup_v92.iss not found.
pause
