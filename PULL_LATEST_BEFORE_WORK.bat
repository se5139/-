@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  Pull latest before work
echo ============================================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git is not installed or not in PATH.
  echo Install Git for Windows first: https://git-scm.com/download/win
  pause
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo [ERROR] This folder is not a Git repository.
  echo Clone again: git clone https://github.com/se5139/my-app.git
  pause
  exit /b 1
)

for /f "delims=" %%S in ('git status --porcelain') do (
  echo [STOP] You have local changes.
  echo Save or back up your work before pulling latest files.
  echo.
  git status --short
  pause
  exit /b 1
)

echo [INFO] Local folder is clean. Pulling latest main branch...
git pull --ff-only origin main
if errorlevel 1 (
  echo.
  echo [ERROR] Pull failed. Check the message above.
  pause
  exit /b 1
)

echo.
echo [OK] Latest files are ready.
pause
