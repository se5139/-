from __future__ import annotations
import ast, json, re, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT/rel).read_text(encoding='utf-8', errors='ignore')

checks=[]
def add(name, ok, detail=''):
    checks.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':detail})

# build script should not require args
bs=read('scripts/build_inno_installer_v60.py')
ast.parse(bs)
add('build script syntax', True)
add('optional root arg', 'add_argument("--root", required=False)' in bs)
add('optional iss arg', 'add_argument("--iss", required=False)' in bs)
add('infer paths fallback', 'infer_paths' in bs and 'SCRIPT_NAME' in bs)
add('no v59 builder required args in active 0 bat', 'build_inno_installer_v60.py' in read('0_BUILD_WINDOWS_INSTALLER_EXE.bat') and '--iss' not in read('0_BUILD_WINDOWS_INSTALLER_EXE.bat'))
add('v60 iss exists', (ROOT/'installer/KakaoEmoticonSetup_v60.iss').exists())
iss=read('installer/KakaoEmoticonSetup_v60.iss')
add('iss version v60', 'AppVersion={#MyAppVersion}' in iss and '60.0.0' in iss)
add('iss output filename v60', 'OutputBaseFilename=KakaoEmoticonSetup_v60' in iss)
add('iss cleanup v60', 'run_cleanup_old_versions_v60.bat' in iss)
add('cleanup script v60 exists', (ROOT/'scripts/cleanup_old_versions_v60.py').exists())
cs=read('scripts/cleanup_old_versions_v60.py')
ast.parse(cs)
add('cleanup current version 60', 'CURRENT_VERSION_DEFAULT = 60' in cs)
add('cleanup actual yes bat', '--yes --current-version 60' in read('run_cleanup_old_versions_v60.bat'))
add('manual cleanup bat v60', (ROOT/'14_V60_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat').exists())
add('shortcut script v60 exists', (ROOT/'scripts/create_shortcuts_v60.py').exists())
add('portable installer target v60', 'KakaoEmoticonProfitSystemV60' in read('1_INSTALL_NOW.bat'))
add('launcher title v60', 'v60' in read('START_WINDOWS.bat'))
# Ensure no concrete OpenAI API key is bundled.
# Generic validator regex examples are excluded by file path.
import re as _re
secret_re = _re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{40,}")
hits=[]
allowed_validation_files = {
    'modules/api_key_safety/openai_key_guard.py',
    'scripts/v58_api_key_safety_check.py',
    'scripts/v60_installer_build_fix_check.py',
}
for f in ROOT.rglob('*'):
    if f.is_file() and f.suffix.lower() in {'.py','.bat','.txt','.md','.json','.iss','.csv','.env'}:
        rel = str(f.relative_to(ROOT)).replace('\\','/')
        if rel in allowed_validation_files or '__pycache__' in rel:
            continue
        try:
            txt = f.read_text(encoding='utf-8', errors='ignore')
            if secret_re.search(txt):
                hits.append(rel)
        except Exception:
            pass
add('no concrete OpenAI API key bundled', not hits, ', '.join(hits[:5]))

ok=all(c['status']=='PASS' for c in checks)
report={'ok':ok,'checks':checks}
out=ROOT/'kakao_emoticon_profit_system_v60_verification_report.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0 if ok else 1)
