from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "kakao_emoticon_profit_system_v59_verification_report.json"


def load_cleanup_module():
    path = ROOT / "scripts" / "cleanup_old_versions_v59.py"
    spec = importlib.util.spec_from_file_location("cleanup_old_versions_v59", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def is_ascii_file(path: Path) -> bool:
    try:
        path.read_text(encoding="ascii")
        return True
    except Exception:
        return False


def run_simulation() -> dict:
    mod = load_cleanup_module()
    tmp = Path(tempfile.mkdtemp(prefix="v59_cleanup_check_"))
    old1 = tmp / "kakao_emoticon_profit_system_v44_final_delivery"
    old2 = tmp / "kakao_emoticon_profit_system_v56_inno_compiler_detector"
    cur = tmp / "KakaoEmoticonProfitSystemV59"
    old1.mkdir()
    old2.mkdir()
    cur.mkdir()
    (old1 / "outputs").mkdir()
    (old1 / "outputs" / "keep.txt").write_text("keep", encoding="utf-8")
    old_desktop = tmp / "Desktop"
    old_desktop.mkdir()
    (old_desktop / "Kakao Emoticon Profit System v56.lnk").write_text("dummy", encoding="utf-8")

    old_env = dict(os.environ)
    os.environ["LOCALAPPDATA"] = str(tmp)
    os.environ["USERPROFILE"] = str(tmp)
    try:
        # dry run must not remove
        rc1 = mod.main(["--current-version", "59", "--protect", str(cur)])
        dry_ok = old1.exists() and old2.exists() and cur.exists()
        # actual run must remove old and keep current
        rc2 = mod.main(["--yes", "--current-version", "59", "--protect", str(cur)])
        actual_ok = (not old1.exists()) and (not old2.exists()) and cur.exists()
        backup_base = tmp / "KakaoEmoticonProfitSystemUserData" / "old_version_cleanup_backups"
        backups = list(backup_base.glob("v59_*/cleanup_report.json"))
        return {"rc_dry": rc1, "rc_actual": rc2, "dry_ok": dry_ok, "actual_ok": actual_ok, "report_count": len(backups)}
    finally:
        os.environ.clear(); os.environ.update(old_env)
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    checks = []
    def add(name: str, ok: bool, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    cleanup = ROOT / "scripts" / "cleanup_old_versions_v59.py"
    batch = ROOT / "run_cleanup_old_versions_v59.bat"
    manual = ROOT / "14_V59_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat"
    iss = ROOT / "installer" / "KakaoEmoticonSetup_v59.iss"
    build = ROOT / "scripts" / "build_inno_installer_v59.py"
    shortcuts = ROOT / "scripts" / "create_shortcuts_v59.py"

    add("cleanup script exists", cleanup.exists())
    add("cleanup script avoids powershell cleanup", ("subprocess" not in cleanup.read_text(encoding="utf-8", errors="ignore").lower() and ".ps1" not in cleanup.read_text(encoding="utf-8", errors="ignore").lower()))
    add("run cleanup batch exists", batch.exists())
    add("manual cleanup batch exists", manual.exists())
    add("installer v59 exists", iss.exists())
    add("build script v59 exists", build.exists())
    add("shortcut script v59 exists", shortcuts.exists())

    if batch.exists():
        text = batch.read_text(encoding="utf-8", errors="ignore")
        add("installer cleanup batch uses --yes", "--yes" in text and "--current-version 59" in text)
    if iss.exists():
        text = iss.read_text(encoding="utf-8", errors="ignore")
        add("installer cleanup task checked", 'Name: "cleanupold"' in text and 'Flags: checkedonce' in text)
        add("installer runs v59 cleanup", "run_cleanup_old_versions_v59.bat" in text)
        add("installer v59 output exe", "KakaoEmoticonSetup_v59" in text)
        add("installer clean shortcut created", "Clean Old Versions" in text)
    # app constants
    const = (ROOT / "modules" / "constants.py").read_text(encoding="utf-8", errors="ignore")
    add("constants v59", 'APP_VERSION = "59.0.0"' in const and "V59_SAFE_CLEANUP_INSTALLER" in const)

    # Python compileall on main modified files
    for py in [cleanup, build, shortcuts, ROOT / "app.py", ROOT / "modules" / "constants.py"]:
        if py.exists():
            res = subprocess.run([sys.executable, "-m", "py_compile", str(py)], capture_output=True, text=True)
            add(f"py_compile {py.name}", res.returncode == 0, (res.stderr or res.stdout)[-500:])

    sim = run_simulation()
    add("cleanup dry-run and actual simulation", sim.get("dry_ok") and sim.get("actual_ok") and sim.get("report_count", 0) >= 1, json.dumps(sim, ensure_ascii=False))

    # Make sure known old broken patterns were not used in v59 launcher files.
    combined = "\n".join((ROOT / name).read_text(encoding="utf-8", errors="ignore") for name in ["1_INSTALL_NOW.bat", "START_WINDOWS.bat", "4_REPAIR_ENVIRONMENT.bat"] if (ROOT/name).exists())
    add("active BAT version strings v59", "[v59]" in combined and "[v53]" not in combined and "KakaoEmoticonProfitSystemV57" not in combined)

    report = {"version": "v59", "ok": all(x["ok"] for x in checks), "checks": checks}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
