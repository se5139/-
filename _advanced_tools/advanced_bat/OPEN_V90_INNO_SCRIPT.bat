@echo off
cd /d "%~dp0\..\.."
echo [v90] Opening Inno Setup script...
if exist "installer\KakaoEmoticonSetup_v90.iss" start "" "installer\KakaoEmoticonSetup_v90.iss"
if not exist "installer\KakaoEmoticonSetup_v90.iss" echo [ERROR] installer\KakaoEmoticonSetup_v90.iss not found.
pause
