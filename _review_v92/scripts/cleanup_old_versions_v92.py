from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

APP_PREFIXES = (
    "kakao_emoticon_profit_system_",
    "kakaoemoticonprofitsystemv",
    "kakaoemoticonv",
)
CURRENT_VERSION_DEFAULT = 90
CONFIRM_MOVE = "MOVE_OLD_KAKAO_VERSIONS"
CONFIRM_DELETE = "DELETE_OLD_KAKAO_VERSIONS"

VERSION_RE = re.compile(r"(?:^|[_\-\s])v?(\d{1,3})(?:\D|$)", re.IGNORECASE)
SAFE_NAME_RE = re.compile(r"[^0-9A-Za-z가-힣._\-]+")

PRESERVE_DIR_NAMES = {
    "outputs",
    "output",
    "user_data",
    "userdata",
    "data",
    "settings",
    "reports",
    "report",
    "backups",
    "backup",
    "exports",
    "export",
    "projects",
    "project_data",
}
PRESERVE_EXTENSIONS = {
    ".db", ".sqlite", ".sqlite3", ".json", ".csv", ".xlsx", ".xls", ".txt", ".md", ".html",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".zip",
}
NEVER_DELETE_NAMES = {
    "windows", "program files", "program files (x86)", "users", "documents and settings",
    "programdata", "$recycle.bin", "perflogs", "intel", "inetpub",
}


@dataclass
class Candidate:
    path: str
    name: str
    version: int | None
    location_type: str
    reason: str
    size_bytes: int
    file_count: int
    action: str = "preview"
    result: str = "not_run"
    error: str | None = None


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def normalize_key(path: Path) -> str:
    try:
        return str(path.resolve()).casefold()
    except Exception:
        return str(path).casefold()


def safe_folder_name(value: str) -> str:
    cleaned = SAFE_NAME_RE.sub("_", value).strip("._ ")
    return cleaned[:90] or "old_kakao_folder"


def extract_version(name: str) -> int | None:
    lower = name.lower()
    # Prefer explicit vNN markers.
    for pat in [r"v(\d{1,3})", r"_v(\d{1,3})", r"version[_\-\s]?(\d{1,3})"]:
        m = re.search(pat, lower)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    # Fallback for names like KakaoEmoticonProfitSystemV87.
    m = re.search(r"systemv(\d{1,3})", lower)
    if m:
        return int(m.group(1))
    # Last-resort version-looking number.
    candidates = []
    for m in VERSION_RE.finditer(lower):
        try:
            candidates.append(int(m.group(1)))
        except Exception:
            pass
    return max(candidates) if candidates else None


def looks_like_kakao_version_folder(path: Path) -> bool:
    name = path.name.strip()
    lower_compact = re.sub(r"[^a-z0-9_]+", "", name.lower())
    lower = name.lower()
    if name.lower() in NEVER_DELETE_NAMES:
        return False
    if not path.is_dir():
        return False
    if lower.startswith("kakao_emoticon_profit_system_"):
        return True
    if lower_compact.startswith("kakaoemoticonprofitsystemv"):
        return True
    if lower_compact.startswith("kakaoemoticonv"):
        return True
    return False


def folder_size_and_count(path: Path) -> tuple[int, int]:
    total = 0
    count = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                count += 1
                total += item.stat().st_size
        except Exception:
            continue
    return total, count


def default_scan_roots() -> list[Path]:
    roots: list[Path] = []
    env = os.environ
    # User screenshot shows extracted folders directly under C:\.
    system_drive = env.get("SystemDrive") or "C:"
    if os.name == "nt":
        roots.append(Path(system_drive + "\\"))
    else:
        # Non-Windows test fallback: script root only unless --scan-root is supplied.
        roots.append(Path.cwd())

    for key in ["LOCALAPPDATA", "APPDATA", "USERPROFILE"]:
        value = env.get(key)
        if value:
            roots.append(Path(value))
    return unique_existing_dirs(roots)


def unique_existing_dirs(paths: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        try:
            pp = Path(p).expanduser()
            if pp.exists() and pp.is_dir():
                key = normalize_key(pp)
                if key not in seen:
                    seen.add(key)
                    out.append(pp)
        except Exception:
            continue
    return out


def scan_candidates(scan_roots: list[Path], current_version: int, current_path: Path | None) -> list[Candidate]:
    candidates: list[Candidate] = []
    current_key = normalize_key(current_path) if current_path else ""
    seen: set[str] = set()

    for root in scan_roots:
        try:
            entries = list(root.iterdir())
        except Exception:
            continue
        for entry in entries:
            try:
                if not looks_like_kakao_version_folder(entry):
                    continue
                key = normalize_key(entry)
                if key in seen:
                    continue
                seen.add(key)
                if current_key and key == current_key:
                    continue
                version = extract_version(entry.name)
                if version is not None and version >= current_version:
                    continue
                size, count = folder_size_and_count(entry)
                location_type = "C_DRIVE_EXTRACTED" if re.match(r"^[A-Za-z]:\\?$", str(root)) else "USER_APP_OR_LOCAL_FOLDER"
                reason = "이전 카카오 이모티콘 프로그램 폴더로 보이는 이름이며 현재 버전보다 낮습니다."
                candidates.append(Candidate(
                    path=str(entry),
                    name=entry.name,
                    version=version,
                    location_type=location_type,
                    reason=reason,
                    size_bytes=size,
                    file_count=count,
                ))
            except Exception:
                continue

    candidates.sort(key=lambda c: (c.version if c.version is not None else -1, c.name.lower(), c.path.lower()))
    return candidates


def copy_preserve_files(src: Path, dst_root: Path) -> dict:
    preserved: list[str] = []
    errors: list[str] = []
    for item in src.rglob("*"):
        try:
            if not item.is_file():
                continue
            rel = item.relative_to(src)
            parts_lower = {p.lower() for p in rel.parts[:-1]}
            should_preserve = bool(parts_lower & PRESERVE_DIR_NAMES) or item.suffix.lower() in PRESERVE_EXTENSIONS
            if not should_preserve:
                continue
            dst = dst_root / safe_folder_name(src.name) / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst)
            preserved.append(str(rel))
        except Exception as exc:
            errors.append(f"{item}: {exc}")
    return {"preserved_count": len(preserved), "preserved_sample": preserved[:200], "errors": errors[:100]}


def quarantine_folder(src: Path, quarantine_root: Path) -> str:
    quarantine_root.mkdir(parents=True, exist_ok=True)
    dst = quarantine_root / safe_folder_name(src.name)
    if dst.exists():
        dst = quarantine_root / f"{safe_folder_name(src.name)}_{now_stamp()}"
    shutil.move(str(src), str(dst))
    return str(dst)


def delete_folder(src: Path) -> None:
    shutil.rmtree(src)


def build_output_root(custom: str | None = None) -> Path:
    if custom:
        return Path(custom).expanduser()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("USERPROFILE") or str(Path.home())
        return Path(base) / "KakaoEmoticonProfitSystem_UserData" / "cleanup_reports"
    return Path.cwd() / "outputs" / "cleanup_reports"


def run(mode: str, scan_roots: list[Path], current_version: int, current_path: Path | None, output_root: Path, confirm: str | None, yes: bool) -> dict:
    timestamp = now_stamp()
    output_root.mkdir(parents=True, exist_ok=True)
    backup_root = output_root / f"preserved_user_data_{timestamp}"
    quarantine_root = output_root / f"old_version_quarantine_{timestamp}"

    candidates = scan_candidates(scan_roots, current_version=current_version, current_path=current_path)
    report = {
        "tool_version": "92.0.0",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "current_version": current_version,
        "current_path": str(current_path) if current_path else None,
        "scan_roots": [str(p) for p in scan_roots],
        "candidate_count": len(candidates),
        "backup_root": str(backup_root),
        "quarantine_root": str(quarantine_root),
        "safety_rules": [
            "수동 실행 기본은 preview입니다. 설치/업그레이드 완료 후에는 백업 후 이전 버전 삭제 흐름을 실행할 수 있습니다.",
            "현재 버전 이상 폴더는 대상에서 제외합니다.",
            "C:\\Windows, Program Files, Users 같은 시스템 폴더명은 대상에서 제외합니다.",
            "수동 삭제 모드는 정확한 확인 문구가 있어야 실행됩니다. 설치/업그레이드 자동 정리도 현재 버전 미만 폴더만 대상으로 합니다.",
            "삭제 전 outputs/data/settings/report/CSV/JSON/이미지/ZIP 계열 파일을 보존 백업합니다.",
        ],
        "candidates": [],
        "errors": [],
        "summary": {},
    }

    if mode == "preview":
        report["candidates"] = [asdict(c) for c in candidates]
    elif mode == "quarantine":
        if not yes or confirm != CONFIRM_MOVE:
            report["errors"].append(f"Quarantine requires --yes --confirm {CONFIRM_MOVE}")
            report["candidates"] = [asdict(c) for c in candidates]
        else:
            for c in candidates:
                src = Path(c.path)
                c.action = "quarantine"
                try:
                    if not src.exists():
                        c.result = "missing"
                    else:
                        moved = quarantine_folder(src, quarantine_root)
                        c.result = f"moved_to::{moved}"
                except Exception as exc:
                    c.result = "failed"
                    c.error = repr(exc)
                report["candidates"].append(asdict(c))
    elif mode == "delete":
        if not yes or confirm != CONFIRM_DELETE:
            report["errors"].append(f"Delete requires --yes --confirm {CONFIRM_DELETE}")
            report["candidates"] = [asdict(c) for c in candidates]
        else:
            for c in candidates:
                src = Path(c.path)
                c.action = "backup_then_delete"
                try:
                    if not src.exists():
                        c.result = "missing"
                    else:
                        preserve = copy_preserve_files(src, backup_root)
                        delete_folder(src)
                        c.result = f"deleted_after_preserve::{preserve.get('preserved_count', 0)}_files"
                except Exception as exc:
                    c.result = "failed"
                    c.error = repr(exc)
                report["candidates"].append(asdict(c))
    else:
        report["errors"].append(f"Unknown mode: {mode}")
        report["candidates"] = [asdict(c) for c in candidates]

    acted = [c for c in report["candidates"] if c.get("result") not in {"not_run", None}]
    failed = [c for c in report["candidates"] if c.get("result") == "failed"]
    report["summary"] = {
        "status": "FAIL" if report["errors"] or failed else "PASS",
        "found": len(candidates),
        "acted": len(acted),
        "failed": len(failed),
        "total_size_bytes_preview": sum(c.size_bytes for c in candidates),
    }
    report_path = output_root / f"v92_old_version_cleanup_{mode}_{timestamp}.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Kakao Emoticon v92 safe old-version cleanup tool")
    ap.add_argument("--mode", choices=["preview", "quarantine", "delete"], default="preview")
    ap.add_argument("--scan-root", action="append", default=[], help="Folder to scan one level deep. Can be repeated.")
    ap.add_argument("--current-version", type=int, default=CURRENT_VERSION_DEFAULT)
    ap.add_argument("--current-path", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--confirm", default=None)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.scan_root:
        scan_roots = unique_existing_dirs(Path(p) for p in args.scan_root)
    else:
        scan_roots = default_scan_roots()
    current_path = Path(args.current_path).expanduser() if args.current_path else None
    output_root = build_output_root(args.output_root)
    report = run(
        mode=args.mode,
        scan_roots=scan_roots,
        current_version=args.current_version,
        current_path=current_path,
        output_root=output_root,
        confirm=args.confirm,
        yes=args.yes,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("summary", {}).get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
