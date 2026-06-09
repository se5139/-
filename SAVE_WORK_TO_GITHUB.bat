@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  Save current work to GitHub
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

echo [INFO] Current changes:
git status --short
echo.

for /f "delims=" %%S in ('git status --porcelain') do goto :has_changes
echo [OK] No changes to save.
pause
exit /b 0

:has_changes
set "COMMIT_MSG="
set /p COMMIT_MSG=Commit message: 
if "%COMMIT_MSG%"=="" set "COMMIT_MSG=Update project"

git add -A
if errorlevel 1 (
  echo [ERROR] git add failed.
  pause
  exit /b 1
)

git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
  echo [ERROR] git commit failed.
  pause
  exit /b 1
)

echo.
echo [INFO] Syncing with GitHub before push...
git pull --rebase origin main
if errorlevel 1 (
  echo.
  echo [ERROR] Rebase failed. Resolve conflicts, then run:
  echo git add .
  echo git rebase --continue
  echo git push origin main
  pause
  exit /b 1
)

git push origin main
if errorlevel 1 (
  echo.
  echo [ERROR] Push failed. Check GitHub login or network status.
  pause
  exit /b 1
)

echo.
echo [OK] Work saved to GitHub.
pause
