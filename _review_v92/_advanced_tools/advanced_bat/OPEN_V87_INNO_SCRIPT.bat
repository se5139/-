@echo off
cd /d "%~dp0\..\.."
echo [v87] Opening Inno Setup script...
if exist "installer\KakaoEmoticonSetup_v87.iss" start "" "installer\KakaoEmoticonSetup_v87.iss"
if not exist "installer\KakaoEmoticonSetup_v87.iss" echo [ERROR] installer\KakaoEmoticonSetup_v87.iss not found.
pause
