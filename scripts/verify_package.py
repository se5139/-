from __future__ import annotations

import py_compile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "app.py",
    "README.md",
    "QUICK_START_OTHER_PC_KO.txt",
    "requirements.txt",
    "START_WINDOWS.bat",
    "RUN_SERVER_NO_BROWSER.bat",
    "VERIFY_PACKAGE.bat",
    "KAKAO_SAFE_WORKFLOW.md",
    "RESEARCH_SOURCES.md",
    "memory/evolution_memory.json",
    "memory/api_usage_ledger.json",
    "scripts/stop_port.py",
    "scripts/wait_for_port.py",
    "scripts/verify_package.py",
]

FORBIDDEN_PATH_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "outputs",
    "release",
    "github_backup",
    "installer",
    "_legacy_tools",
    "_advanced_tools",
}


def check_required_files() -> list[str]:
    issues: list[str] = []
    for rel_path in REQUIRED_FILES:
        if not (ROOT / rel_path).is_file():
            issues.append(f"missing required file: {rel_path}")
    return issues


def check_forbidden_paths() -> list[str]:
    if not (ROOT / "RELEASE_MANIFEST.json").exists():
        print("[WARN] RELEASE_MANIFEST.json not found; skipping packaged-folder strict check in development tree")
        return []
    issues: list[str] = []
    for path in ROOT.rglob("*"):
        rel_parts = set(path.relative_to(ROOT).parts)
        found = sorted(rel_parts & FORBIDDEN_PATH_PARTS)
        if found:
            issues.append(f"forbidden packaged path: {path.relative_to(ROOT)}")
            if len(issues) >= 10:
                break
    return issues


def check_launcher_text() -> list[str]:
    issues: list[str] = []
    launcher = ROOT / "START_WINDOWS.bat"
    if launcher.exists():
        text = launcher.read_text(encoding="utf-8", errors="replace").lower()
        if "v100" not in text:
            issues.append("START_WINDOWS.bat does not look like the v100 launcher")
        if "streamlit" in text or "v90" in text:
            issues.append("START_WINDOWS.bat still contains v90/streamlit text")
    requirements = ROOT / "requirements.txt"
    if requirements.exists():
        text = requirements.read_text(encoding="utf-8", errors="replace").lower()
        if "pillow" not in text:
            issues.append("requirements.txt does not include Pillow")
        if "streamlit" in text:
            issues.append("requirements.txt still includes Streamlit")
    return issues


def check_python_files() -> list[str]:
    issues: list[str] = []
    for rel_path in ["app.py", "scripts/stop_port.py", "scripts/wait_for_port.py", "scripts/verify_package.py"]:
        path = ROOT / rel_path
        if not path.exists():
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            issues.append(f"python compile failed: {rel_path}: {exc}")
    return issues


def main() -> int:
    print(f"[check] root: {ROOT}")
    checks = [
        ("required files", check_required_files),
        ("forbidden folders", check_forbidden_paths),
        ("launcher text", check_launcher_text),
        ("python syntax", check_python_files),
    ]
    issues: list[str] = []
    for label, checker in checks:
        found = checker()
        if found:
            print(f"[FAIL] {label}")
            for issue in found:
                print(f"  - {issue}")
            issues.extend(found)
        else:
            print(f"[OK] {label}")
    if issues:
        print(f"[check] failed with {len(issues)} issue(s)")
        return 1
    print("[check] package is ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
