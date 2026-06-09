@echo off
setlocal
cd /d "%~dp0"
start "" "installer\KakaoEmoticonSetup_v75.iss"
echo If Inno Setup opened, choose Build / Compile.
pause
