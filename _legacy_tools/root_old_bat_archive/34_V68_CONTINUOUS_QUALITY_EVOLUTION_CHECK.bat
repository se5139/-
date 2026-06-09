@echo off
cd /d "%~dp0"
set PYEXE=python
if exist ".venv\Scripts\python.exe" set PYEXE=.venv\Scripts\python.exe
%PYEXE% "%~dp0scripts\v68_continuous_quality_evolution_check.py"
pause
