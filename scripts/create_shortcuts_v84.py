from __future__ import annotations
import os
import sys
from pathlib import Path

VERSION="84"
APP_NAME=f"Kakao Emoticon Profit System v{VERSION}"

def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    root = root.resolve()
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    onedrive = os.environ.get("OneDrive")
    desktops = [desktop]
    if onedrive:
        desktops.append(Path(onedrive) / "Desktop")
        desktops.append(Path(onedrive) / "바탕 화면")
    targets = {
        APP_NAME: root / "2_START_PROGRAM.bat",
        f"{APP_NAME} - Repair": root / "4_REPAIR_ENVIRONMENT.bat",
        f"{APP_NAME} - Diagnostics": root / "6_RUN_DIAGNOSTICS.bat",
        f"{APP_NAME} - Outputs": root / "5_OPEN_OUTPUTS.bat",
        f"{APP_NAME} - Clean Old Versions": root / f"14_V{VERSION}_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat",
    }
    try:
        import win32com.client  # type: ignore
    except Exception:
        print("[v84][WARN] pywin32 is not installed; shortcuts can be created by Inno Setup instead.")
        return 0
    shell = win32com.client.Dispatch("WScript.Shell")
    count = 0
    for desk in dict.fromkeys(desktops):
        try:
            desk.mkdir(parents=True, exist_ok=True)
            for name, target in targets.items():
                if not target.exists():
                    print(f"[v84][WARN] Missing shortcut target: {target}")
                    continue
                lnk = desk / f"{name}.lnk"
                sc = shell.CreateShortCut(str(lnk))
                sc.Targetpath = os.environ.get("ComSpec", "cmd.exe")
                sc.Arguments = f'/C "{target}"'
                sc.WorkingDirectory = str(root)
                sc.IconLocation = os.environ.get("SystemRoot", "C:\\Windows") + "\\System32\\shell32.dll,44"
                sc.save()
                count += 1
        except Exception as e:
            print(f"[v84][WARN] Could not create shortcuts in {desk}: {e}")
    print(f"[v84] Created shortcut count: {count}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
