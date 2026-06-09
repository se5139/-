# v56 Inno Setup Windows Installer Wizard

## Added
- Inno Setup installer script: `installer/KakaoEmoticonSetup_v56.iss`.
- Build helper: `BUILD_V56_SETUP_EXE.bat`.
- Installer wizard default path: `%LOCALAPPDATA%\KakaoEmoticonProfitSystemV56`.
- Windows desktop/start-menu shortcuts are created by Inno Setup instead of fragile PowerShell scripts.
- Python-based old-version cleanup helper: `scripts/cleanup_old_versions_v56.py`.
- Python-based shortcut fallback helper: `scripts/create_shortcuts_v56.py`.

## Limitation
The current sandbox cannot run Windows Inno Setup Compiler, so the actual `KakaoEmoticonSetup_v56.exe` must be built on Windows by running `BUILD_V56_SETUP_EXE.bat` after installing Inno Setup 6.
