from __future__ import annotations
import json
import os
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""

def assert_true(cond: bool, msg: str, failures: list[str]):
    if not cond:
        failures.append(msg)

def main() -> int:
    failures=[]
    required = [
        ROOT/"0_BUILD_WINDOWS_INSTALLER_EXE.bat",
        ROOT/"OPEN_V82_INNO_SCRIPT.bat",
        ROOT/"installer"/"KakaoEmoticonSetup_v82.iss",
        ROOT/"scripts"/"build_inno_installer_v82.py",
        ROOT/"scripts"/"v82_stepwise_build_check.py",
    ]
    for p in required:
        assert_true(p.exists(), f"missing required file: {p.relative_to(ROOT)}", failures)
    bat=read(ROOT/"0_BUILD_WINDOWS_INSTALLER_EXE.bat")
    builder=read(ROOT/"scripts"/"build_inno_installer_v82.py")
    iss=read(ROOT/"installer"/"KakaoEmoticonSetup_v82.iss")
    assert_true("[v82]" in bat, "build BAT does not print v82 visible logs", failures)
    assert_true("build_inno_installer_v82.py" in bat, "build BAT does not call v82 builder", failures)
    assert_true("stream_process" in builder, "builder does not stream compiler output", failures)
    assert_true("recursive scan" in builder and "without recursive" in builder, "builder does not avoid slow recursive shortcut scan", failures)
    assert_true("KakaoEmoticonSetup_v82.exe" in builder, "builder output exe name is not v82", failures)
    assert_true("KakaoEmoticonProfitSystemV82" in iss, "Inno install dir is not v82", failures)
    assert_true("run_cleanup_old_versions_v82.bat" in iss, "Inno cleanup run does not target v82", failures)
    assert_true("KakaoEmoticonSetup_v82" in iss, "Inno output base is not v82", failures)
    # sensitive key pattern check
    key_pattern=re.compile(r"sk-(?:proj|live|test|[A-Za-z0-9])[-_A-Za-z0-9]{20,}")
    leaked=[]
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".py", ".bat", ".iss", ".md", ".txt", ".json", ".csv", ".html", ".env"}:
            txt=read(path)
            if key_pattern.search(txt):
                leaked.append(str(path.relative_to(ROOT)))
    assert_true(not leaked, "possible API key patterns found: " + ", ".join(leaked[:5]), failures)
    report={"version":"82", "ok": not failures, "failures": failures, "root": str(ROOT)}
    out=ROOT/"outputs"/"v82_stepwise_build_check_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
