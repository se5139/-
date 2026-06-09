@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [v84] Opening Inno Setup script manually...
echo [v84] In Inno Setup, click Build - Compile.
start "" "installer\KakaoEmoticonSetup_v84.iss"
pause
