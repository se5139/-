# V56 Changelog - Inno Compiler Detector Fix

- Fixed v55 build failure where `ISCC.exe` was not found even when Inno Setup Compiler was installed.
- Added robust Inno compiler finder: PATH, Program Files, LocalAppData, per-user installs, shortcut target detection, and `Compil32.exe /cc` fallback.
- Added `0_BUILD_WINDOWS_INSTALLER_EXE.bat` as the main build entry point.
- Added `OPEN_V56_INNO_SCRIPT.bat` manual fallback for the Inno Setup GUI.
- Final app remains Python-centered; Inno Setup is only the Windows installer wrapper.
