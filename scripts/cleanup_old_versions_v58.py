from __future__ import annotations
import argparse, json, os, re, shutil
from pathlib import Path
from datetime import datetime

DATA_DIR_NAMES = {"outputs", "user_data", "settings", "reports", "projects", "database", "history", "performance", "backups"}
VERSION_RE = re.compile(r"(?:kakao_emoticon_profit_system_v|KakaoEmoticonProfitSystemV|KakaoEmoticonV)(\d+)", re.I)

def get_version(path: Path) -> int | None:
    m = VERSION_RE.search(path.name)
    return int(m.group(1)) if m else None

def backup_data_dirs(folder: Path, backup_root: Path, report: dict):
    for name in DATA_DIR_NAMES:
        src = folder / name
        if src.exists():
            dst = backup_root / folder.name / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = backup_root / folder.name / f"{name}_{datetime.now().strftime('%H%M%S')}"
            try:
                shutil.copytree(src, dst)
                report.setdefault("backed_up", []).append({"from": str(src), "to": str(dst)})
            except Exception as e:
                report.setdefault("backup_errors", []).append({"path": str(src), "error": str(e)})

def is_protected(p: Path, protected: list[Path]) -> bool:
    try:
        rp = p.resolve()
        for q in protected:
            try:
                rq = q.resolve()
                if rp == rq or rq in rp.parents or rp in rq.parents:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False

def candidate_dirs(current_version: int) -> list[Path]:
    roots = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        roots.append(Path(local))
    roots += [Path("C:/"), Path.home()]
    cands = []
    for root in roots:
        if not root.exists():
            continue
        try:
            for child in root.iterdir():
                if child.is_dir():
                    v = get_version(child)
                    if v is not None and v < current_version:
                        cands.append(child)
        except Exception:
            continue
    out = []
    seen = set()
    for c in cands:
        s = str(c).lower()
        if s not in seen:
            seen.add(s)
            out.append(c)
    return out

def desktop_shortcut_candidates() -> list[Path]:
    user = Path.home()
    roots = [user / "Desktop", user / "OneDrive" / "Desktop", user / "OneDrive" / "바탕 화면", user / "바탕 화면"]
    cands = []
    for r in roots:
        if not r.exists():
            continue
        try:
            for f in r.glob("*.lnk"):
                if "Kakao" in f.name or "kakao" in f.name or "이모티콘" in f.name:
                    cands.append(f)
        except Exception:
            pass
    return cands

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--current-version", type=int, default=55)
    ap.add_argument("--protect", action="append", default=[])
    args = ap.parse_args()
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    backup_root = local / "KakaoEmoticonProfitSystemUserData" / "old_version_cleanup_backups" / ("v58_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    backup_root.mkdir(parents=True, exist_ok=True)
    protected = [Path(p) for p in args.protect]
    report = {"current_version": args.current_version, "backup_root": str(backup_root), "removed_dirs": [], "removed_shortcuts": [], "skipped": [], "errors": []}
    for d in candidate_dirs(args.current_version):
        if is_protected(d, protected):
            report["skipped"].append({"path": str(d), "reason": "protected"})
            continue
        if not args.yes:
            report["skipped"].append({"path": str(d), "reason": "dry-run"})
            continue
        try:
            backup_data_dirs(d, backup_root, report)
            shutil.rmtree(d)
            report["removed_dirs"].append(str(d))
        except Exception as e:
            report["errors"].append({"path": str(d), "error": str(e)})
    if args.yes:
        for lnk in desktop_shortcut_candidates():
            try:
                lnk.unlink()
                report["removed_shortcuts"].append(str(lnk))
            except Exception as e:
                report["errors"].append({"path": str(lnk), "error": str(e)})
    report_path = backup_root / "cleanup_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
