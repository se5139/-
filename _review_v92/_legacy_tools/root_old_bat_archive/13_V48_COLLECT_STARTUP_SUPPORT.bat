@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "OUT=outputs\v48_startup_support"
if not exist "%OUT%" mkdir "%OUT%"
echo [v48] Collecting startup support package...
python --version > "%OUT%\python_version.txt" 2>&1
where python > "%OUT%\where_python.txt" 2>&1
where py > "%OUT%\where_py.txt" 2>&1
dir /s /b > "%OUT%\file_list.txt" 2>&1
if exist "%LOCALAPPDATA%\KakaoEmoticonProfitSystemV48_install_logs\install_copy_log.txt" copy "%LOCALAPPDATA%\KakaoEmoticonProfitSystemV48_install_logs\install_copy_log.txt" "%OUT%\install_copy_log.txt" >nul
if exist outputs\installer_diagnostics xcopy /E /I /Y outputs\installer_diagnostics "%OUT%\installer_diagnostics" >nul
powershell -NoProfile -Command "Compress-Archive -Path '%OUT%\*' -DestinationPath '%OUT%\v48_startup_support_package.zip' -Force"
echo [v48] Support package: %OUT%\v48_startup_support_package.zip
pause
