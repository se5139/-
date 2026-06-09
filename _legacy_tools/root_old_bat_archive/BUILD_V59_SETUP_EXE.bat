@echo off
setlocal
cd /d "%~dp0"
python scripts\build_inno_installer_v59.py --root "%~dp0" --iss "%~dp0installer\KakaoEmoticonSetup_v59.iss"
if errorlevel 1 pause
