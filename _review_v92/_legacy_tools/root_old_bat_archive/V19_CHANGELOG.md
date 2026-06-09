# V19 CHANGELOG - Data Safety Backup/Migration

- Added Data Safety / Backup / Migration tab.
- Added `modules/data_safety` with backup, verify, safe restore, and migration helpers.
- Added update-before-backup ZIP generation with manifest and SHA-256 hash.
- Added safe restore to a separate folder to avoid accidental overwrite.
- Added user data directory separation under LOCALAPPDATA on Windows.
- Added `8_BACKUP_USER_DATA.bat` and `9_DATA_SAFETY_CHECK.bat`.
- Updated quick_check to verify backup/report generation.
