@echo off
cd /d "%~dp0"
echo [v86] Opening Inno Setup script manually.
echo [v86] If Inno Setup opens, click Build ^> Compile.
start "" "%CD%\installer\KakaoEmoticonSetup_v86.iss"
pause
