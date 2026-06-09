from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

CURRENT_VERSION_DEFAULT = 60
DATA_DIR_NAMES = {
    "outputs", "user_data", "settings", "reports", "report", "projects", "project",
    "database", "db", "history", "performance", "backups", "backup", "exports",
    "generated", "logs", "install_logs", "user_files"
}

# ASCII-only patterns to avoid Windows PowerShell/Korean regex problems.
VERSION_PATTERNS = [
    re.compile(r"^kakao_emoticon_profit_system_v(\d+).*", re.IGNORECASE),
    re.compile(r"^KakaoEmoticonProfitSystemV(\d+).*", re.IGNORECASE),
    re.compile(r"^KakaoEmoticonV(\d+).*", re.IGNORECASE),
]
SHORTCUT_HINTS = ("Kakao Emoticon", "KakaoEmoticon", "kakao_emoticon", "이모티콘")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def version_from_name(name: str) -> int | None:
    for pat in VERSION_PATTERNS:
        m = pat.match(name)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    return None


def safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except Exception:
        return path.absolute()


def is_same_or_inside(path: Path, base: Path) -> bool:
    try:
        p = safe_resolve(path)
        b = safe_resolve(base)
        return p == b or b in p.parents
    except Exception:
        return False


def is_dangerous_root(path: Path) -> bool:
    p = safe_resolve(path)
    dangerous = [Path("C:/"), Path.home(), Path(os.environ.get("USERPROFILE", str(Path.home())))]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dangerous.append(Path(local))
    for d in dangerous:
        try:
            if p == safe_resolve(d):
                return True
        except Exception:
            pass
    return False


def is_protected(path: Path, protected: list[Path]) -> bool:
    p = safe_resolve(path)
    for item in protected:
        if not item:
            continue
        if is_same_or_inside(path, item) or is_same_or_inside(item, path):
            return True
    return False


def scan_roots() -> list[Path]:
    roots: list[Path] = []
    for key in ("LOCALAPPDATA", "USERPROFILE"):
        val = os.environ.get(key)
        if val:
            roots.append(Path(val))
    roots.append(Path.home())
    roots.append(Path("C:/"))
    # Optional Desktop paths where users sometimes extract ZIPs.
    user = Path(os.environ.get("USERPROFILE", str(Path.home())))
    roots.extend([user / "Desktop", user / "OneDrive" / "Desktop", user / "OneDrive" / "바탕 화면", user / "바탕 화면"])
    out: list[Path] = []
    seen: set[str] = set()
    for r in roots:
        try:
            rr = safe_resolve(r)
            key = str(rr).lower()
            if rr.exists() and rr.is_dir() and key not in seen:
                seen.add(key)
                out.append(rr)
        except Exception:
            continue
    return out


def find_old_version_dirs(current_version: int) -> list[Path]:
    candidates: list[Path] = []
    for root in scan_roots():
        try:
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                v = version_from_name(child.name)
                if v is not None and 0 <= v < current_version:
                    candidates.append(child)
        except PermissionError:
            continue
        except Exception:
            continue
    # de-duplicate
    out: list[Path] = []
    seen: set[str] = set()
    for c in candidates:
        key = str(safe_resolve(c)).lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    out.sort(key=lambda x: str(x).lower())
    return out


def find_old_shortcuts(current_version: int) -> list[Path]:
    user = Path(os.environ.get("USERPROFILE", str(Path.home())))
    roots = [user / "Desktop", user / "OneDrive" / "Desktop", user / "OneDrive" / "바탕 화면", user / "바탕 화면"]
    candidates: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        try:
            for lnk in root.glob("*.lnk"):
                name = lnk.name
                if not any(hint.lower() in name.lower() for hint in SHORTCUT_HINTS):
                    continue
                v = version_from_name(name.replace(" ", ""))
                # Some shortcuts are named 'Kakao Emoticon Profit System v56.lnk'
                if v is None:
                    m = re.search(r"v(\d+)", name, re.IGNORECASE)
                    if m:
                        v = int(m.group(1))
                if v is None or v < current_version:
                    candidates.append(lnk)
        except Exception:
            continue
    out: list[Path] = []
    seen: set[str] = set()
    for c in candidates:
        key = str(safe_resolve(c)).lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def backup_data_dirs(folder: Path, backup_root: Path, report: dict) -> None:
    for name in DATA_DIR_NAMES:
        src = folder / name
        if not src.exists():
            continue
        dst = backup_root / folder.name / name
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = backup_root / folder.name / f"{name}_{now_stamp()}"
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            report.setdefault("backed_up", []).append({"from": str(src), "to": str(dst)})
        except Exception as exc:
            report.setdefault("backup_errors", []).append({"path": str(src), "error": repr(exc)})


def remove_dir(path: Path) -> None:
    # Extra guard: only remove folders that match version patterns.
    if version_from_name(path.name) is None:
        raise RuntimeError(f"refuse to remove non-version folder: {path}")
    if is_dangerous_root(path):
        raise RuntimeError(f"refuse to remove dangerous root: {path}")
    shutil.rmtree(path)


def write_reports(report: dict, backup_root: Path) -> None:
    backup_root.mkdir(parents=True, exist_ok=True)
    json_path = backup_root / "cleanup_report.json"
    txt_path = backup_root / "cleanup_report.txt"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "Kakao Emoticon v60 old-version cleanup report",
        f"time: {report.get('time')}",
        f"dry_run: {report.get('dry_run')}",
        f"current_version: {report.get('current_version')}",
        f"backup_root: {report.get('backup_root')}",
        "",
        f"removed_dirs: {len(report.get('removed_dirs', []))}",
        *["  - " + x for x in report.get("removed_dirs", [])],
        "",
        f"removed_shortcuts: {len(report.get('removed_shortcuts', []))}",
        *["  - " + x for x in report.get("removed_shortcuts", [])],
        "",
        f"skipped: {len(report.get('skipped', []))}",
        *["  - " + json.dumps(x, ensure_ascii=False) for x in report.get("skipped", [])],
        "",
        f"errors: {len(report.get('errors', []))}",
        *["  - " + json.dumps(x, ensure_ascii=False) for x in report.get("errors", [])],
    ]
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    report["json_report"] = str(json_path)
    report["txt_report"] = str(txt_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe cleanup for old Kakao Emoticon extracted/install folders.")
    parser.add_argument("--yes", action="store_true", help="Actually remove old folders/shortcuts. Without this, only dry-run report is created.")
    parser.add_argument("--current-version", type=int, default=CURRENT_VERSION_DEFAULT)
    parser.add_argument("--protect", action="append", default=[], help="Path to protect from removal. Can be supplied multiple times.")
    parser.add_argument("--show-candidates", action="store_true")
    args = parser.parse_args(argv)

    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    backup_root = local / "KakaoEmoticonProfitSystemUserData" / "old_version_cleanup_backups" / ("v60_" + now_stamp())
    protected = [Path(p) for p in args.protect if p]
    protected.append(Path.cwd())
    # Protect current installed app path by version name if present.
    current_app = local / f"KakaoEmoticonProfitSystemV{args.current_version}"
    protected.append(current_app)

    report = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "current_version": args.current_version,
        "dry_run": not args.yes,
        "backup_root": str(backup_root),
        "scan_roots": [str(x) for x in scan_roots()],
        "candidates": [],
        "shortcut_candidates": [],
        "removed_dirs": [],
        "removed_shortcuts": [],
        "backed_up": [],
        "backup_errors": [],
        "skipped": [],
        "errors": [],
    }

    dirs = find_old_version_dirs(args.current_version)
    shortcuts = find_old_shortcuts(args.current_version)
    report["candidates"] = [str(x) for x in dirs]
    report["shortcut_candidates"] = [str(x) for x in shortcuts]

    if args.show_candidates:
        print(json.dumps({"dirs": report["candidates"], "shortcuts": report["shortcut_candidates"]}, ensure_ascii=False, indent=2))

    for folder in dirs:
        v = version_from_name(folder.name)
        if v is None or v >= args.current_version:
            report["skipped"].append({"path": str(folder), "reason": "not_old_version"})
            continue
        if is_protected(folder, protected):
            report["skipped"].append({"path": str(folder), "reason": "protected"})
            continue
        if not args.yes:
            report["skipped"].append({"path": str(folder), "reason": "dry_run"})
            continue
        try:
            backup_data_dirs(folder, backup_root, report)
            remove_dir(folder)
            report["removed_dirs"].append(str(folder))
        except Exception as exc:
            report["errors"].append({"path": str(folder), "error": repr(exc)})

    for lnk in shortcuts:
        if is_protected(lnk, protected):
            report["skipped"].append({"path": str(lnk), "reason": "protected_shortcut"})
            continue
        if not args.yes:
            report["skipped"].append({"path": str(lnk), "reason": "dry_run_shortcut"})
            continue
        try:
            lnk.unlink()
            report["removed_shortcuts"].append(str(lnk))
        except Exception as exc:
            report["errors"].append({"path": str(lnk), "error": repr(exc)})

    write_reports(report, backup_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
