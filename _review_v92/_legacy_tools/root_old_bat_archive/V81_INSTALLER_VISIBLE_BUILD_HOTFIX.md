# v81 Installer Visible Build Hotfix

This version fixes the v80 user-visible build problem where `0_BUILD_WINDOWS_INSTALLER_EXE.bat` could open a black CMD window with no immediate progress.

Changes:
- The installer build BAT now prints progress immediately.
- Python launcher detection uses `py -3` first and falls back to `python`.
- The Inno Setup build script logs every step with `flush=True`.
- Build reports are written to `installer/v81_inno_build_report.json`.
- Manual fallback is available through `OPEN_V81_INNO_SCRIPT.bat`.
- No API keys are included.

This is a focused installer/build hotfix, not a new feature expansion.
