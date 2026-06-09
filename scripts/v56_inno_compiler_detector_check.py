from __future__ import annotations
import json, pathlib, py_compile
ROOT = pathlib.Path(__file__).resolve().parents[1]
errors=[]
checks={}

def read(path, enc='ascii'):
    return (ROOT/path).read_text(encoding=enc)

def require(path):
    p=ROOT/path
    ok=p.exists()
    checks[f"exists:{path}"]=ok
    if not ok: errors.append(f"missing {path}")
    return p

required=[
    "app.py", "modules/constants.py", "installer/KakaoEmoticonSetup_v56.iss",
    "BUILD_V56_SETUP_EXE.bat", "0_BUILD_WINDOWS_INSTALLER_EXE.bat", "OPEN_V56_INNO_SCRIPT.bat",
    "scripts/build_inno_installer_v56.py", "scripts/cleanup_old_versions_v56.py", "scripts/create_shortcuts_v56.py",
]
for x in required: require(x)
for x in ["app.py", "scripts/build_inno_installer_v56.py", "scripts/cleanup_old_versions_v56.py", "scripts/create_shortcuts_v56.py"]:
    try:
        py_compile.compile(str(ROOT/x), doraise=True)
        checks[f"compile:{x}"]=True
    except Exception as e:
        checks[f"compile:{x}"]=False
        errors.append(f"compile {x}: {e}")
for x in ["BUILD_V56_SETUP_EXE.bat", "0_BUILD_WINDOWS_INSTALLER_EXE.bat", "OPEN_V56_INNO_SCRIPT.bat", "1_INSTALL_NOW.bat", "3_CREATE_SHORTCUTS_ONLY.bat", "run_cleanup_old_versions_v56.bat", "installer/KakaoEmoticonSetup_v56.iss"]:
    try:
        read(x, 'ascii')
        checks[f"ascii:{x}"]=True
    except Exception as e:
        checks[f"ascii:{x}"]=False
        errors.append(f"non-ascii {x}: {e}")
iss=read("installer/KakaoEmoticonSetup_v56.iss")
for token in ["KakaoEmoticonSetup_v56", "KakaoEmoticonProfitSystemV56", "WizardStyle=modern", "[Icons]", "[Run]", "run_cleanup_old_versions_v56.bat"]:
    ok=token in iss
    checks[f"iss_token:{token}"]=ok
    if not ok: errors.append(f"missing iss token {token}")
build=read("BUILD_V56_SETUP_EXE.bat")
for token in [r"scripts\build_inno_installer_v56.py", "KakaoEmoticonSetup_v56.iss", "OPEN_V56_INNO_SCRIPT.bat"]:
    ok=token in build
    checks[f"build_bat_token:{token}"]=ok
    if not ok: errors.append(f"missing build bat token {token}")
finder=read("scripts/build_inno_installer_v56.py", 'utf-8')
for token in ["LOCALAPPDATA", "ProgramFiles", "shutil.which", "Compil32.exe", "ISCC.exe", "CreateShortcut", "ISCC_PATH"]:
    ok=token in finder
    checks[f"finder_token:{token}"]=ok
    if not ok: errors.append(f"missing finder token {token}")
const=read("modules/constants.py", 'utf-8')
ok='APP_VERSION = "56.0.0"' in const and 'v56' in const
checks["constants_v56"]=ok
if not ok: errors.append("constants.py not updated to v56")
active=["BUILD_V56_SETUP_EXE.bat", "0_BUILD_WINDOWS_INSTALLER_EXE.bat", "OPEN_V56_INNO_SCRIPT.bat", "1_INSTALL_NOW.bat", "3_CREATE_SHORTCUTS_ONLY.bat", "run_cleanup_old_versions_v56.bat", "installer/KakaoEmoticonSetup_v56.iss"]
for x in active:
    txt=read(x)
    bad_any=[]
    for pat in ["KakaoEmoticonSetup_v55", "KakaoEmoticonProfitSystemV55", "cleanup_old_versions_v55", "create_shortcuts_v55", "v55.iss"]:
        if pat in txt:
            bad_any.append(pat)
    checks[f"no_v55_refs:{x}"]=not bad_any
    if bad_any: errors.append(f"old v55 refs in {x}: {bad_any}")
report={"ok": not errors, "errors": errors, "checks": checks}
print(json.dumps(report, ensure_ascii=False, indent=2))
(ROOT/"v56_inno_compiler_detector_check_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
raise SystemExit(0 if not errors else 1)
