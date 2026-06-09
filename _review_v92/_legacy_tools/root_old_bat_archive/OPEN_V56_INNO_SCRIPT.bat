@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "%CD%\installer\KakaoEmoticonSetup_v56.iss" (
  echo [ERROR] installer\KakaoEmoticonSetup_v56.iss was not found.
  pause
  exit /b 1
)
echo [v56] Opening installer script with the default Inno Setup association...
start "" "%CD%\installer\KakaoEmoticonSetup_v56.iss"
echo If Inno Setup opens, click Build or Compile to create installer\Output\KakaoEmoticonSetup_v56.exe.
pause
exit /b 0
