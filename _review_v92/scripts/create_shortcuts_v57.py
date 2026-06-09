from __future__ import annotations
import argparse, os, json, subprocess
from pathlib import Path
from datetime import datetime

APP_TITLE = "Kakao Emoticon Profit System v57"

def desktop_dirs() -> list[Path]:
    user = Path.home()
    candidates = [user / "Desktop", user / "OneDrive" / "Desktop", user / "OneDrive" / "바탕 화면", user / "바탕 화면"]
    dirs = [p for p in candidates if p.exists()]
    if not dirs:
        dirs.append(user / "Desktop")
    unique = []
    for d in dirs:
        if d not in unique:
            unique.append(d)
    return unique

def start_menu_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_TITLE

def make_lnk(target_lnk: Path, batch_file: Path, workdir: Path, description: str) -> bool:
    target_lnk.parent.mkdir(parents=True, exist_ok=True)
    vbs = target_lnk.parent / ("_make_shortcut_v57_" + str(os.getpid()) + ".vbs")
    lines = [
        'Set oWS = WScript.CreateObject("WScript.Shell")',
        'Set oLink = oWS.CreateShortcut("' + str(target_lnk) + '")',
        'oLink.TargetPath = "' + str(batch_file) + '"',
        'oLink.WorkingDirectory = "' + str(workdir) + '"',
        'oLink.Description = "' + description + '"',
        'oLink.Save',
        '',
    ]
    vbs.write_text("\n".join(lines), encoding="utf-16")
    try:
        res = subprocess.run(["cscript.exe", "//nologo", str(vbs)], capture_output=True, text=True, timeout=30)
        return res.returncode == 0 and target_lnk.exists()
    finally:
        try:
            vbs.unlink()
        except Exception:
            pass

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-dir", required=True)
    args = ap.parse_args()
    app_dir = Path(args.app_dir).resolve()
    targets = {
        "Start Program": app_dir / "2_START_PROGRAM.bat",
        "Diagnostics": app_dir / "6_RUN_DIAGNOSTICS.bat",
        "Open Outputs": app_dir / "5_OPEN_OUTPUTS.bat",
        "Repair Environment": app_dir / "4_REPAIR_ENVIRONMENT.bat",
    }
    report = {
        "created": [],
        "missing": [str(p) for p in targets.values() if not p.exists()],
        "desktop_dirs": [str(x) for x in desktop_dirs()],
        "time": datetime.now().isoformat(timespec="seconds"),
    }
    if os.name != "nt":
        report["warning"] = "Shortcut creation is only available on Windows."
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    for desk in desktop_dirs():
        for name, bat in targets.items():
            if bat.exists():
                lnk = desk / f"{APP_TITLE} - {name}.lnk"
                if make_lnk(lnk, bat, app_dir, f"{APP_TITLE} {name}"):
                    report["created"].append(str(lnk))
    sm = start_menu_dir()
    for name, bat in targets.items():
        if bat.exists():
            lnk = sm / f"{name}.lnk"
            if make_lnk(lnk, bat, app_dir, f"{APP_TITLE} {name}"):
                report["created"].append(str(lnk))
    (app_dir / "v57_shortcut_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
