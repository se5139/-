# v60 Installer Build Fix

- Fixes the v59 video error where `build_inno_installer_v59.py` could be run without the required `--iss` argument.
- The v60 installer builder now infers root and `.iss` paths automatically when no arguments are supplied.
- `0_BUILD_WINDOWS_INSTALLER_EXE.bat` now calls the v60 builder without fragile path arguments.
- Adds v60 Inno Setup script, v60 cleanup script, v60 shortcut helper, and v60 verification script.
- Keeps Python-centered local PC program structure.
- Keeps old-version cleanup and user data backup safety rules.
