@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Open Kakao Emoticon v82 Inno Script

echo [v82] Opening Inno Setup script manually.
echo [v82] If Inno Setup opens, click Build ^> Compile.
echo [v82] Script: %CD%\installer\KakaoEmoticonSetup_v82.iss
echo.
start "" "%CD%\installer\KakaoEmoticonSetup_v82.iss"
pause
