@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kakao Emoticon v65 Coding Toolchain Check
echo [v65] Running coding toolchain check...
python scripts\v65_coding_toolchain_check.py
if errorlevel 1 (
  echo [v65] Check failed.
  pause
  exit /b 1
)
echo [v65] Check passed.
pause
exit /b 0
