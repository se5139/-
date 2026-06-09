@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kakao Emoticon v90 - Safe Old Version Cleanup

echo.
echo ============================================================
echo  Kakao Emoticon Profit System v90 - Safe Old Version Cleanup
echo ============================================================
echo [v90] This tool scans old Kakao emoticon program folders such as:
echo       C:\kakao_emoticon_profit_system_v66_...
echo       C:\kakao_emoticon_profit_system_v80_...
echo       %%LOCALAPPDATA%%\KakaoEmoticonProfitSystemV86
echo.
echo [SAFETY] Nothing is deleted automatically.
echo [SAFETY] Current version v90 is excluded.
echo [SAFETY] User data is backed up before permanent delete mode.
echo.

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)
if "%PY_CMD%"=="" (
  echo [ERROR] Python was not found. Install Python 3.10+ and check Add Python to PATH.
  pause
  exit /b 1
)

echo Select cleanup mode:
echo.
echo   1 = Scan only / preview report. Recommended first.
echo   2 = Move old folders to safe quarantine folder. Recommended cleanup.
echo   3 = Permanently delete old folders after preserving user data. Use carefully.
echo   0 = Cancel.
echo.
set /p MODE_CHOICE=Enter number: 

if "%MODE_CHOICE%"=="0" goto CANCEL
if "%MODE_CHOICE%"=="1" goto PREVIEW
if "%MODE_CHOICE%"=="2" goto QUARANTINE
if "%MODE_CHOICE%"=="3" goto DELETE

echo [ERROR] Unknown selection.
pause
exit /b 1

:PREVIEW
echo.
echo [v90] Running preview only...
%PY_CMD% scripts\cleanup_old_versions_v90.py --mode preview --current-version 90 --current-path "%CD%"
goto DONE

:QUARANTINE
echo.
echo [v90] Quarantine mode moves old version folders into a backup/quarantine folder.
echo [v90] This is safer than permanent deletion because you can still inspect them.
echo.
echo To continue, type exactly: MOVE_OLD_KAKAO_VERSIONS
set /p CONFIRM_MOVE=Confirm: 
if not "%CONFIRM_MOVE%"=="MOVE_OLD_KAKAO_VERSIONS" (
  echo [CANCELLED] Confirmation did not match.
  pause
  exit /b 1
)
%PY_CMD% scripts\cleanup_old_versions_v90.py --mode quarantine --yes --confirm MOVE_OLD_KAKAO_VERSIONS --current-version 90 --current-path "%CD%"
goto DONE

:DELETE
echo.
echo [WARNING] Permanent delete mode removes old version folders after preserving likely user data.
echo [WARNING] Use preview first. Close the program if old folders are currently open/running.
echo.
echo To continue, type exactly: DELETE_OLD_KAKAO_VERSIONS
set /p CONFIRM_DELETE=Confirm: 
if not "%CONFIRM_DELETE%"=="DELETE_OLD_KAKAO_VERSIONS" (
  echo [CANCELLED] Confirmation did not match.
  pause
  exit /b 1
)
%PY_CMD% scripts\cleanup_old_versions_v90.py --mode delete --yes --confirm DELETE_OLD_KAKAO_VERSIONS --current-version 90 --current-path "%CD%"
goto DONE

:CANCEL
echo [v90] Cancelled. No files changed.
pause
exit /b 0

:DONE
echo.
echo [v90] Cleanup tool finished.
echo [v90] A JSON report was saved under outputs\cleanup_reports or the user-data cleanup report folder.
echo.
pause
exit /b %ERRORLEVEL%
