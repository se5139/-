@echo off
cd /d "%~dp0"
echo [v85] Opening Inno Setup script manually.
echo [v85] If Inno Setup opens, click Build ^> Compile.
start "" "%CD%\installer\KakaoEmoticonSetup_v85.iss"
pause
