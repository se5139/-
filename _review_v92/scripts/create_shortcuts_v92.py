from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VERSION = "92"
APP_NAME = f"Kakao Emoticon Profit System v{VERSION}"


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path.expanduser()).lower()
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def desktop_candidates() -> list[Path]:
    override = os.environ.get("KAKAO_SHORTCUT_DESKTOP_DIR")
    if override:
        return [Path(override)]

    home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    candidates = [
        home / "Desktop",
        home / "바탕 화면",
    ]

    for env_name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        base = os.environ.get(env_name)
        if base:
            candidates.extend([Path(base) / "Desktop", Path(base) / "바탕 화면"])

    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "Desktop")
            candidates.append(Path(os.path.expandvars(str(value))))
    except Exception:
        pass

    public = os.environ.get("PUBLIC")
    if public:
        candidates.append(Path(public) / "Desktop")

    return unique_paths(candidates)


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def create_lnk_with_powershell(lnk: Path, target: Path, root: Path, icon_index: int = 44) -> bool:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    safe_target = str(target).replace('"', '""')
    script = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            "$ws = New-Object -ComObject WScript.Shell",
            f"$sc = $ws.CreateShortcut({ps_quote(str(lnk))})",
            "$sc.TargetPath = $env:ComSpec",
            f"$sc.Arguments = '/C \"{safe_target}\"'",
            f"$sc.WorkingDirectory = {ps_quote(str(root))}",
            f"$sc.IconLocation = {ps_quote(system_root + r'\System32\shell32.dll,' + str(icon_index))}",
            "$sc.Save()",
        ]
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True,
            capture_output=True,
            timeout=20,
        )
        if completed.returncode == 0 and lnk.exists():
            return True
        if completed.stderr.strip():
            print(f"[v92][WARN] PowerShell shortcut failed: {completed.stderr.strip()}")
    except Exception as exc:
        print(f"[v92][WARN] PowerShell shortcut failed: {exc}")
    return False


def create_bat_fallback(bat_path: Path, target: Path) -> bool:
    try:
        bat_path.write_text(f'@echo off\r\ncall "{target}"\r\n', encoding="utf-8")
        return True
    except Exception as exc:
        print(f"[v92][WARN] BAT fallback failed for {bat_path}: {exc}")
        return False


def create_url_fallback(url_path: Path, target: Path, icon_index: int = 44) -> bool:
    try:
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        content = "\r\n".join(
            [
                "[InternetShortcut]",
                f"URL={target.resolve().as_uri()}",
                f"IconFile={system_root}\\System32\\shell32.dll",
                f"IconIndex={icon_index}",
                "",
            ]
        )
        url_path.write_text(content, encoding="utf-8")
        return True
    except Exception as exc:
        print(f"[v92][WARN] URL fallback failed for {url_path}: {exc}")
        return False


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    root = root.resolve()
    desktops = desktop_candidates()
    targets = {
        APP_NAME: root / "00_STEP_3_START_PROGRAM.bat",
        f"{APP_NAME} - Repair": root / "4_REPAIR_ENVIRONMENT.bat",
        f"{APP_NAME} - Diagnostics": root / "_advanced_tools" / "advanced_bat" / "6_RUN_DIAGNOSTICS.bat",
        f"{APP_NAME} - Outputs": root / "_advanced_tools" / "advanced_bat" / "5_OPEN_OUTPUTS.bat",
        f"{APP_NAME} - Clean Old Versions": root / "00_STEP_4_SAFE_CLEAN_OLD_VERSIONS.bat",
    }
    count = 0
    fallback_count = 0
    for desktop in desktops:
        try:
            desktop.mkdir(parents=True, exist_ok=True)
            for name, target in targets.items():
                if not target.exists():
                    print(f"[v92][WARN] Missing shortcut target: {target}")
                    continue
                lnk = desktop / f"{name}.lnk"
                if create_lnk_with_powershell(lnk, target, root):
                    count += 1
                elif create_url_fallback(desktop / f"{name}.url", target):
                    fallback_count += 1
                elif create_bat_fallback(desktop / f"{name}.bat", target):
                    fallback_count += 1
        except Exception as exc:
            print(f"[v92][WARN] Could not create shortcuts in {desktop}: {exc}")
    print(f"[v92] Desktop locations checked: {len(desktops)}")
    print(f"[v92] Created shortcut count: {count}")
    if fallback_count:
        print(f"[v92] Created fallback shortcut count: {fallback_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
