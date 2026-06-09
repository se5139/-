@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "%CD%\installer\KakaoEmoticonSetup_v57.iss" (
  echo [ERROR] installer\KakaoEmoticonSetup_v57.iss was not found.
  pause
  exit /b 1
)
echo [v57] Opening installer script with the default Inno Setup association...
start "" "%CD%\installer\KakaoEmoticonSetup_v57.iss"
echo If Inno Setup opens, click Build or Compile to create installer\Output\KakaoEmoticonSetup_v57.exe.
pause
exit /b 0
