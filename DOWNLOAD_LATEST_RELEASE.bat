@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "ZIP_URL=https://raw.githubusercontent.com/se5139/-/main/release/kakao_emoticon_v100_clean_latest.zip"
set "SHA_URL=https://raw.githubusercontent.com/se5139/-/main/release/kakao_emoticon_v100_clean_latest.sha256.txt"
set "OUT_DIR=%~dp0downloaded_release"
set "ZIP_PATH=%OUT_DIR%\kakao_emoticon_v100_clean_latest.zip"
set "SHA_PATH=%OUT_DIR%\kakao_emoticon_v100_clean_latest.sha256.txt"

title Kakao Emoticon v100 Latest Release Downloader

echo.
echo ============================================================
echo  Kakao Emoticon Maker v100 Clean - Latest ZIP Downloader
echo ============================================================
echo [download] Target folder: %OUT_DIR%
echo.

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%ZIP_URL%' -OutFile '%ZIP_PATH%' -UseBasicParsing; Invoke-WebRequest -Uri '%SHA_URL%' -OutFile '%SHA_PATH%' -UseBasicParsing; exit 0 } catch { Write-Host $_; exit 1 }"
if errorlevel 1 (
  echo.
  echo [FAIL] Download failed.
  echo Check your internet connection or open DOWNLOAD_LATEST_FROM_GITHUB_KO.md manually.
  pause
  exit /b 1
)

echo.
echo [OK] Download complete.
echo [file] %ZIP_PATH%
echo [sha]  %SHA_PATH%
echo.
echo Next:
echo 1. Unzip kakao_emoticon_v100_clean_latest.zip
echo 2. Run VERIFY_PACKAGE.bat
echo 3. Run START_WINDOWS.bat
echo.
pause
exit /b 0
