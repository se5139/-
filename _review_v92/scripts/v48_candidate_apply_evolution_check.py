from __future__ import annotations

import ast
import compileall
import hashlib
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "v48_verification"
OUT.mkdir(parents=True, exist_ok=True)

CHECKS: List[Dict[str, Any]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})


def read_text(path: Path, encoding: str = "utf-8") -> str:
    try:
        return path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        return path.read_text(encoding="cp949", errors="replace")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_required_files() -> None:
    required = [
        "app.py",
        "requirements.txt",
        "1_INSTALL_NOW.bat",
        "2_START_PROGRAM.bat",
        "START_WINDOWS.bat",
        "14_V48_CLEAN_OLD_VERSIONS.bat",
        "modules/constants.py",
        "modules/evolution_quality/character_evolution_engine.py",
        "scripts/cleanup_old_versions_v48.ps1",
        "scripts/create_shortcuts_v48.ps1",
        "scripts/v48_candidate_apply_evolution_check.py",
        "V48_CHANGELOG.md",
        "V48_FIRST_RUN_GUIDE.txt",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    record("required files", not missing, "missing=" + ", ".join(missing) if missing else f"{len(required)} files present")


def check_versions() -> None:
    constants = read_text(ROOT / "modules" / "constants.py")
    app = read_text(ROOT / "app.py")
    install = read_text(ROOT / "1_INSTALL_NOW.bat", encoding="utf-8")
    start = read_text(ROOT / "START_WINDOWS.bat", encoding="utf-8")
    clean_bat = read_text(ROOT / "14_V48_CLEAN_OLD_VERSIONS.bat", encoding="utf-8")
    ok = all(token in constants for token in ["v48", "48.0.0"]) and "KakaoEmoticonProfitSystemV48" in install and "v48_ready.txt" in start and "-CurrentVersion 48" in clean_bat
    stale = [t for t in ["KakaoEmoticonProfitSystemV36", "Installing Kakao Emoticon Profit System v36", "Kakao Emoticon v47", "-CurrentVersion 47"] if t in install + start + constants + clean_bat]
    record("version strings", ok and not stale, f"stale={stale}" if stale else "v48 constants/install/start/cleanup markers present")
    record("v48 app tab present", "45 후보 적용/정지형 품질 진화" in app and "CharacterTrendEvolutionEngine" in app, "v48 tab/import markers checked")


def check_bat_ascii_and_paths() -> None:
    bat_files = sorted(ROOT.glob("*.bat"))
    bad_ascii = []
    bad_quotes = []
    for path in bat_files:
        data = path.read_bytes()
        # Root BAT files are intentionally ASCII-safe to avoid Korean CMD mojibake.
        if any(b > 127 for b in data):
            bad_ascii.append(path.name)
        text = data.decode("ascii", errors="ignore")
        if "\\" + chr(34) in text:
            bad_quotes.append(path.name)
    record("root BAT ASCII-safe", not bad_ascii, ", ".join(bad_ascii) if bad_ascii else f"{len(bat_files)} BAT files ASCII-only")
    record("root BAT path quoting", not bad_quotes, ", ".join(bad_quotes) if bad_quotes else "no suspicious escaped quotes")


def check_cleanup_safety() -> None:
    cleanup = read_text(ROOT / "scripts" / "cleanup_old_versions_v48.ps1")
    required_terms = [
        "KakaoEmoticonProfitSystemUserData",
        "old_version_cleanup_backups",
        "CurrentVersion",
        "ReportOnly",
        "AutoConfirm",
        "Compress-Archive",
        "Remove-Item",
    ]
    missing = [t for t in required_terms if t not in cleanup]
    dangerous = [t for t in ["Remove-Item $env:USERPROFILE", "Remove-Item C:\\\\", "Remove-Item $HOME"] if t in cleanup]
    record("cleanup safety terms", not missing and not dangerous, f"missing={missing}, dangerous={dangerous}")


def check_python_compile() -> None:
    ok = compileall.compile_dir(str(ROOT), quiet=1, force=True, maxlevels=10)
    record("python compileall", bool(ok), "compile_dir returned " + str(ok))


def check_imports_and_engine_smoke() -> None:
    sys.path.insert(0, str(ROOT))
    try:
        constants = importlib.import_module("modules.constants")
        version_ok = getattr(constants, "APP_VERSION", "") == "48.0.0"
        record("constants import", version_ok, f"APP_VERSION={getattr(constants, 'APP_VERSION', None)}")
    except Exception as exc:
        record("constants import", False, repr(exc))
        return
    try:
        mod = importlib.import_module("modules.evolution_quality.character_evolution_engine")
        engine = mod.CharacterTrendEvolutionEngine()
        report = engine.build_report(
            output_dir=OUT / "engine_smoke",
            project_name="v48_smoke_static_quality",
            character_concept="팽이버섯 캐릭터, 예의 바른 직장인 말투",
            issue_text="정지형 캐릭터가 밋밋하고 후보가 적용되지 않음",
            source_text="짧은 문구, 큰 실루엣, 표정 대비, 확인, 감사, 피곤, 퇴근",
            source_urls="https://example.com/memo-only",
            target_format="static_text",
            priority="정지형 품질 우선",
        )
        paths = [report.json_path, report.csv_path, report.html_path, report.board_png_path, report.zip_path]
        missing = [p for p in paths if not Path(p).exists()]
        record("v48 evolution engine smoke", not missing and report.static_quality_score >= 60, f"score={report.static_quality_score}, missing={missing}")
        if Path(report.zip_path).exists():
            with zipfile.ZipFile(report.zip_path) as z:
                record("v48 evolution report zip integrity", z.testzip() is None, "report zip checked")
    except Exception as exc:
        record("v48 evolution engine smoke", False, repr(exc))


def check_app_static_features() -> None:
    app_path = ROOT / "app.py"
    app = read_text(app_path)
    markers = [
        "v48_apply_trend_to_expression_bank",
        "v48_apply_missing_candidates",
        "v48_apply_evolution_profile",
        "active_generation_profile",
        "active_text_prompt",
        "v48_evolution_report",
        "CharacterTrendEvolutionEngine",
    ]
    missing = [m for m in markers if m not in app]
    record("v48 apply-flow markers", not missing, "missing=" + ", ".join(missing) if missing else "candidate apply markers present")
    try:
        tree = ast.parse(app)
        repeated_unkeyed: List[str] = []
        seen: Dict[str, int] = {}
        widget_names = {"button", "radio", "selectbox", "text_input", "text_area", "number_input", "slider", "checkbox", "download_button", "file_uploader"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in widget_names:
                has_key = any(k.arg == "key" for k in node.keywords)
                if has_key or not node.args:
                    continue
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    label = f"{node.func.attr}:{first.value}"
                    seen[label] = seen.get(label, 0) + 1
        repeated_unkeyed = [k for k, v in seen.items() if v > 1]
        record("streamlit repeated unkeyed widget scan", not repeated_unkeyed, "; ".join(repeated_unkeyed[:20]) if repeated_unkeyed else "no repeated unkeyed labels detected")
    except Exception as exc:
        record("streamlit repeated unkeyed widget scan", False, repr(exc))


def check_video_diagnosis_reference() -> None:
    # This checks that the exact class of issue from the user video has a corresponding fix marker.
    app = read_text(ROOT / "app.py")
    needed_keys = ["v48_trend_mode_radio", "v48_candidate_source_radio", "v48_refine_source_radio", "v48_missing_mode_radio", "v48_v40_source_mode_radio"]
    missing = [k for k in needed_keys if k not in app]
    record("duplicate radio key fix markers", not missing, "missing=" + ", ".join(missing) if missing else "radio keys present")


def main() -> int:
    check_required_files()
    check_versions()
    check_bat_ascii_and_paths()
    check_cleanup_safety()
    check_python_compile()
    check_imports_and_engine_smoke()
    check_app_static_features()
    check_video_diagnosis_reference()
    payload = {
        "version": "v48",
        "root": str(ROOT),
        "checks": CHECKS,
        "summary": {
            "passed": sum(1 for c in CHECKS if c["status"] == "PASS"),
            "failed": sum(1 for c in CHECKS if c["status"] == "FAIL"),
        },
    }
    report_path = OUT / "v48_candidate_apply_evolution_check_report.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    for c in CHECKS:
        print(f"[{c['status']}] {c['name']} - {c['detail']}")
    return 0 if payload["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
