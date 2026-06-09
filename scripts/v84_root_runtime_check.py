from __future__ import annotations
from pathlib import Path
import json, re, sys, zipfile

ROOT = Path.cwd()
ACTIVE_ALLOWED = {
    "00_DOUBLE_CLICK_THIS_FIRST_BUILD_SETUP_EXE.bat", "00_STEP_1_BUILD_SETUP_EXE.bat", "00_STEP_2_PORTABLE_INSTALL_NOW.bat", "00_STEP_3_START_PROGRAM.bat",
    "0_BUILD_WINDOWS_INSTALLER_EXE.bat", "1_INSTALL_NOW.bat", "2_START_PROGRAM.bat", "3_CREATE_SHORTCUTS_ONLY.bat", "4_REPAIR_ENVIRONMENT.bat", "5_OPEN_OUTPUTS.bat", "6_RUN_DIAGNOSTICS.bat",
    "14_V84_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat", "45_V84_FIRST_RUN_RUNTIME_CHECK.bat", "46_V84_ROOT_CLEANUP_CHECK.bat", "BUILD_V84_SETUP_EXE.bat", "OPEN_V84_INNO_SCRIPT.bat", "START_WINDOWS.bat", "run_cleanup_old_versions_v84.bat"
}

def main() -> int:
    root_bats = {p.name for p in ROOT.glob("*.bat")}
    old_visible = sorted(x for x in root_bats if re.search(r"V(4[0-9]|5[0-9]|6[0-9]|7[0-9]|8[0-3])", x, re.I) and "V84" not in x)
    unexpected = sorted(root_bats - ACTIVE_ALLOWED)
    checks = []
    def add(name, ok, detail=""):
        checks.append({"name":name,"ok":bool(ok),"detail":detail})
        print(("PASS" if ok else "FAIL") + " - " + name + (f" - {detail}" if detail else ""))
    add("root old-version BAT files hidden", not old_visible, ", ".join(old_visible[:12]))
    add("root BAT count is manageable", len(root_bats) <= 18, str(len(root_bats)))
    add("main build BAT exists", (ROOT/"0_BUILD_WINDOWS_INSTALLER_EXE.bat").exists())
    add("double-click helper exists", (ROOT/"00_DOUBLE_CLICK_THIS_FIRST_BUILD_SETUP_EXE.bat").exists())
    add("manual Inno script opener exists", (ROOT/"OPEN_V84_INNO_SCRIPT.bat").exists())
    add("v84 Inno script exists", (ROOT/"installer"/"KakaoEmoticonSetup_v84.iss").exists())
    add("v84 build script exists", (ROOT/"scripts"/"build_inno_installer_v84.py").exists())
    add("legacy archive exists", (ROOT/"_legacy_tools"/"root_old_bat_archive").exists())
    report={"version":"84", "root_bat_count":len(root_bats), "old_visible":old_visible, "unexpected":unexpected, "checks":checks}
    out=ROOT/"outputs"/"v84_root_runtime_check_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report: {out}")
    return 0 if all(c["ok"] for c in checks) else 1

if __name__ == "__main__":
    raise SystemExit(main())
