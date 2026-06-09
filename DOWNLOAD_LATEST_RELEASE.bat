@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "ZIP_URL=https://raw.githubusercontent.com/se5139/-/main/release/kakao_emoticon_v100_clean_latest.zip"
set "SHA_URL=https://raw.githubusercontent.com/se5139/-/main/release/kakao_emoticon_v100_clean_latest.sha256.txt"
set "GITHUB_RELEASE_PAGE=https://github.com/se5139/-/tree/main/release"
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
  echo This can happen if the GitHub repository is private or requires login.
  echo Opening the GitHub release folder page instead.
  start "" "%GITHUB_RELEASE_PAGE%"
  echo.
  echo Manual fallback:
  echo 1. Log in to GitHub if needed.
  echo 2. Open the release folder.
  echo 3. Download kakao_emoticon_v100_clean_latest.zip.
  echo 4. Read DOWNLOAD_LATEST_FROM_GITHUB_KO.md if you need the detailed steps.
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
