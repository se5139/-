@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
echo [v56] Building fallback self-extracting EXE with Windows IExpress...
if not exist "%SystemRoot%\System32\iexpress.exe" (
  echo [ERROR] iexpress.exe was not found on this Windows system.
  pause
  exit /b 1
)
echo This fallback is less polished than Inno Setup.
"%SystemRoot%\System32\iexpress.exe" /N "%CD%\installer\KakaoEmoticonSetup_v56_IExpress.sed"
echo Done. Check installer\Output.
pause
