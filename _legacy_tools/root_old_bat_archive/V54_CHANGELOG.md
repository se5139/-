# v54 Windows Installer Hotfix

This version fixes installer and shortcut issues found on Windows screenshots.

## Fixed
- Removed trailing backslash parameter bug that created paths like `folder"\file.bat`.
- Rebuilt cleanup and shortcut PowerShell scripts as ASCII-only to avoid Windows PowerShell mojibake regex errors.
- Added C:\ extracted package folder cleanup detection.
- Added OneDrive Desktop shortcut support.
- Kept user-data backup before deleting old folders.
- Installation target is now `%LOCALAPPDATA%\KakaoEmoticonProfitSystemV54`.

## Safety
- Does not delete Documents, Downloads, Pictures, or unrelated folders.
- Does not delete current v54 source folder or current install target.
- Only removes old Kakao Emoticon program folders/shortcuts after user types Y.
