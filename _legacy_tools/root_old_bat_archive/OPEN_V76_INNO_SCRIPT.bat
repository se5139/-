@echo off
setlocal
cd /d "%~dp0"
start "" "installer\KakaoEmoticonSetup_v76.iss"
echo If Inno Setup opened, choose Build / Compile.
pause
