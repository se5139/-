from __future__ import annotations
import json, re, os
from pathlib import Path
from datetime import datetime
ROOT = Path(__file__).resolve().parents[1]

def read(p: Path) -> str:
    return p.read_text(encoding='utf-8', errors='ignore') if p.exists() else ''

def check(cond, msg, failures):
    if not cond:
        failures.append(msg)

def main() -> int:
    failures=[]
    active = [
        '0_BUILD_WINDOWS_INSTALLER_EXE.bat','1_INSTALL_NOW.bat','2_START_PROGRAM.bat','3_CREATE_SHORTCUTS_ONLY.bat','4_REPAIR_ENVIRONMENT.bat','START_WINDOWS.bat',
        'OPEN_V84_INNO_SCRIPT.bat','BUILD_V84_SETUP_EXE.bat','14_V84_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat','run_cleanup_old_versions_v84.bat',
        'installer/KakaoEmoticonSetup_v84.iss','scripts/build_inno_installer_v84.py','scripts/create_shortcuts_v84.py','scripts/cleanup_old_versions_v84.py'
    ]
    for rel in active:
        check((ROOT/rel).exists(), f'missing active v84 file: {rel}', failures)
    start=read(ROOT/'START_WINDOWS.bat')
    install=read(ROOT/'1_INSTALL_NOW.bat')
    shortcuts=read(ROOT/'3_CREATE_SHORTCUTS_ONLY.bat')
    repair=read(ROOT/'4_REPAIR_ENVIRONMENT.bat')
    build=read(ROOT/'0_BUILD_WINDOWS_INSTALLER_EXE.bat')
    iss=read(ROOT/'installer'/'KakaoEmoticonSetup_v84.iss')
    check('[v84]' in start and 'v84_ready.txt' in start and 'Kakao Emoticon v84 Server' in start, 'START_WINDOWS.bat is not v84 first-run visible launcher', failures)
    check('KakaoEmoticonProfitSystemV84' in install and '[v84]' in install, '1_INSTALL_NOW.bat does not target v84', failures)
    check('create_shortcuts_v84.py' in shortcuts and '[v84]' in shortcuts, '3_CREATE_SHORTCUTS_ONLY.bat does not call v84 shortcut helper', failures)
    check('v84_ready.txt' in repair and '[v84]' in repair, '4_REPAIR_ENVIRONMENT.bat does not rebuild v84 env', failures)
    check('build_inno_installer_v84.py' in build and 'KakaoEmoticonSetup_v84.iss' in build, 'build BAT not connected to v84 builder/iss', failures)
    check('KakaoEmoticonProfitSystemV84' in iss and 'KakaoEmoticonSetup_v84' in iss, 'Inno script not targeting v84', failures)
    # ensure active files do not still print stale v60/v81/v82 labels, except explanatory text allowed in old legacy files.
    for rel in ['START_WINDOWS.bat','1_INSTALL_NOW.bat','3_CREATE_SHORTCUTS_ONLY.bat','4_REPAIR_ENVIRONMENT.bat','0_BUILD_WINDOWS_INSTALLER_EXE.bat']:
        txt=read(ROOT/rel)
        for stale in ['[v60]','Kakao Emoticon v60','V60','[v81]','Kakao Emoticon v81','[v82]','Kakao Emoticon v82']:
            check(stale not in txt, f'active {rel} still contains stale marker {stale}', failures)
    # sensitive key pattern check
    key_pattern=re.compile(r"sk-(?:proj|live|test|[A-Za-z0-9])[-_A-Za-z0-9]{20,}")
    leaked=[]
    for path in ROOT.rglob('*'):
        if path.is_file() and path.suffix.lower() in {'.py','.bat','.iss','.md','.txt','.json','.csv','.html','.env'}:
            if key_pattern.search(read(path)):
                leaked.append(str(path.relative_to(ROOT)))
    check(not leaked, 'possible API key patterns found: ' + ', '.join(leaked[:5]), failures)
    out=ROOT/'outputs'/'v84_first_run_runtime_check_report.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    report={'version':'83','ok':not failures,'failures':failures,'root':str(ROOT),'time':datetime.now().isoformat(timespec='seconds')}
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1
if __name__ == '__main__':
    raise SystemExit(main())
