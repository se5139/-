from pathlib import Path
import re, sys, zipfile, compileall
root = Path(__file__).resolve().parents[1]
errors = []

def read(p):
    return (root / p).read_text(encoding='utf-8', errors='ignore')

required = [
    '1_INSTALL_NOW.bat',
    '3_CREATE_SHORTCUTS_ONLY.bat',
    '14_V54_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat',
    '21_V54_INSTALLER_HOTFIX_CHECK.bat',
    'scripts/create_shortcuts_v54.ps1',
    'scripts/cleanup_old_versions_v54.ps1',
    'app.py',
]
for item in required:
    if not (root / item).exists():
        errors.append(f'missing required file: {item}')

install = read('1_INSTALL_NOW.bat')
if 'set "SRC=%CD%"' not in install:
    errors.append('installer does not use no-trailing-backslash source path')
# cd /d %~dp0 is allowed; passing %~dp0 as a PowerShell argument is not.
if '-ProtectSource "%~dp0' in install or '-AppDir "%~dp0' in install:
    errors.append('installer passes raw %~dp0 as PowerShell path argument')
if 'KakaoEmoticonProfitSystemV54' not in install:
    errors.append('installer target is not v54')
if 'cleanup_old_versions_v54.ps1' not in install:
    errors.append('installer does not call v54 cleanup script')
if 'create_shortcuts_v54.ps1' not in install:
    errors.append('installer does not call v54 shortcut script')

for ps in ['scripts/create_shortcuts_v54.ps1', 'scripts/cleanup_old_versions_v54.ps1']:
    data = (root / ps).read_bytes()
    if any(b >= 128 for b in data):
        errors.append(f'{ps} is not ASCII-only')
    text = data.decode('ascii', errors='ignore')
    if 'Test-Path $targetPath' in text and '-LiteralPath' not in text:
        errors.append(f'{ps} has non-literal Test-Path style')
    if '카카오' in text:
        errors.append(f'{ps} contains Korean text; can mojibake in Windows PowerShell 5.1')
    if 'TrimEnd' not in text:
        errors.append(f'{ps} may not trim trailing backslash safely')

createbat = read('3_CREATE_SHORTCUTS_ONLY.bat')
if 'set "APPDIR=%CD%"' not in createbat:
    errors.append('shortcut bat does not use no-trailing-backslash APPDIR')
if 'create_shortcuts_v54.ps1' not in createbat:
    errors.append('shortcut bat does not call v54 shortcut script')

cleanbat = read('14_V54_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat')
if 'set "APPDIR=%CD%"' not in cleanbat:
    errors.append('cleanup bat does not use no-trailing-backslash APPDIR')
if 'cleanup_old_versions_v54.ps1' not in cleanbat:
    errors.append('cleanup bat does not call v54 cleanup script')

if not compileall.compile_dir(str(root), quiet=1):
    errors.append('compileall failed')

if errors:
    print('[v54] FAIL')
    for e in errors:
        print('-', e)
    sys.exit(1)
print('[v54] PASS')
print('root:', root)
