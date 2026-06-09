from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
checks: list[dict] = []

def add(name: str, ok: bool, detail: str = '') -> None:
    checks.append({'name': name, 'ok': bool(ok), 'detail': detail})
    if not ok:
        errors.append(f'{name}: {detail}')

# Syntax checks
for rel in ['app.py', 'modules/constants.py', 'modules/static_to_animated_apply/__init__.py']:
    p = ROOT / rel
    try:
        ast.parse(p.read_text(encoding='utf-8'))
        add(f'python_ast_{rel}', True)
    except Exception as exc:
        add(f'python_ast_{rel}', False, str(exc))

# Installer checks
install = (ROOT / '1_INSTALL_NOW.bat').read_text(encoding='ascii', errors='ignore')
add('installer_targets_v53', 'KakaoEmoticonProfitSystemV53' in install and 'cleanup_old_versions_v53.ps1' in install and 'create_shortcuts_v53.ps1' in install)
add('installer_does_not_call_v52_cleanup', 'cleanup_old_versions_v52.ps1' not in install)

# Shortcut checks
shortcut_bat = (ROOT / '3_CREATE_SHORTCUTS_ONLY.bat').read_text(encoding='ascii', errors='ignore')
add('shortcut_bat_calls_v53', 'create_shortcuts_v53.ps1' in shortcut_bat and 'create_shortcuts_v48.ps1' not in shortcut_bat)
ps = (ROOT / 'scripts/create_shortcuts_v53.ps1').read_text(encoding='utf-8')
for target in ['2_START_PROGRAM.bat','4_REPAIR_ENVIRONMENT.bat','6_RUN_DIAGNOSTICS.bat','5_OPEN_OUTPUTS.bat','14_V53_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat','20_V53_INSTALL_CLEANUP_SHORTCUT_CHECK.bat']:
    add(f'shortcut_target_exists_{target}', (ROOT / target).exists())
    add(f'shortcut_target_referenced_{target}', target in ps)
add('shortcut_script_multiple_desktops', 'OneDrive\\Desktop' in ps and "GetFolderPath('DesktopDirectory')" in ps)

# Cleanup checks
cleanup = (ROOT / 'scripts/cleanup_old_versions_v53.ps1').read_text(encoding='utf-8')
add('cleanup_scans_c_root', "Add-Root 'C:\\'" in cleanup)
add('cleanup_matches_extracted_zip_folders', 'kakao_emoticon_profit_system_v' in cleanup)
add('cleanup_matches_localappdata_installs', 'KakaoEmoticonProfitSystemV' in cleanup)
add('cleanup_protects_current_paths', 'ProtectSource' in cleanup and 'ProtectTarget' in cleanup and 'Is-ProtectedPath' in cleanup)
add('cleanup_backs_up_user_data', 'preserved_user_data' in cleanup and 'outputs' in cleanup and 'user_data' in cleanup)
add('cleanup_not_broad_personal_folders', 'Add-Root (Join-Path $env:USERPROFILE \'Downloads\')' not in cleanup and 'Add-Root (Join-Path $env:USERPROFILE \'Documents\')' not in cleanup and 'Add-Root (Join-Path $env:USERPROFILE \'Pictures\')' not in cleanup)

# Version constants
const = (ROOT / 'modules/constants.py').read_text(encoding='utf-8')
add('constants_v53', 'v53' in const and '53.0.0' in const)

# BAT ASCII safety
for p in ROOT.glob('*.bat'):
    try:
        p.read_text(encoding='ascii')
        add(f'bat_ascii_{p.name}', True)
    except UnicodeDecodeError as exc:
        add(f'bat_ascii_{p.name}', False, str(exc))

report = {'status': 'PASS' if not errors else 'FAIL', 'errors': errors, 'checks': checks}
out = ROOT / 'v53_install_cleanup_shortcut_check_report.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0 if not errors else 1)
