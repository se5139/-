
from __future__ import annotations
import ast
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.free_api_safety import FreeApiSafetyConfig, FreeApiSafetyEngine

out_dir = ROOT / "outputs" / "v50_verification"
out_dir.mkdir(parents=True, exist_ok=True)
report = {
    "version": "v50",
    "checks": [],
}

def add(name, ok, detail=""):
    report["checks"].append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")

# Syntax checks
ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
add("app.py_ast_parse", True)
ast.parse((ROOT / "modules" / "free_api_safety" / "free_api_safety_engine.py").read_text(encoding="utf-8"))
add("v50_engine_ast_parse", True)

# Engine smoke test with local TXT and ZIP
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    txt = tmp_path / "notes.txt"
    txt.write_text("직장인 공감 넵 확인했습니다 피곤 퇴근 통통 점프 눈깜빡임 말풍선", encoding="utf-8")
    zpath = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("inside.csv", "phrase,emotion\n넵,확인\n퇴근하고 싶어요,피곤\n")
    config = FreeApiSafetyConfig(
        project_name="v50_check",
        days=30,
        youtube_enabled=True,
        openai_enabled=False,
        paid_calls_allowed=False,
        daily_youtube_search_limit=20,
        daily_openai_call_limit=0,
    )
    result = FreeApiSafetyEngine().build_report(
        out_dir / "sample_report",
        config=config,
        local_input_paths=[txt, zpath],
        manual_notes="유료 호출 차단 로컬 분석 우선",
        youtube_api_key="TEST_YOUTUBE_KEY_123456",
        openai_api_key="",
        search_keywords="직장인 공감 이모티콘",
    ).to_dict()
add("v50_engine_smoke", result["mode"] == "FREE_LOCAL_FIRST", result.get("mode", ""))
add("paid_call_block_default", result["paid_call_guard"]["paid_calls_allowed"] is False)
add("raw_api_key_not_stored", "TEST_YOUTUBE_KEY_123456" not in json.dumps(result, ensure_ascii=False))
add("local_zip_analysis", len(result["local_source_summary"]) >= 2, str(len(result["local_source_summary"])))
add("workflow_application", bool(result["workflow_application"].get("expression_seed_phrases")), "seed phrases present")

# Static Streamlit widget key check: reject duplicate explicit keys within v50 block.
app_text = (ROOT / "app.py").read_text(encoding="utf-8")
keys = []
for m in __import__('re').finditer(r'key\s*=\s*["\']([^"\']+)["\']', app_text):
    keys.append(m.group(1))
dups = sorted({k for k in keys if keys.count(k) > 1})
add("streamlit_explicit_key_duplicates", not dups, ", ".join(dups[:10]))
add("v50_tab_marker", "v50 무료 API 수집 안전모드" in app_text)
add("v50_import_marker", "from modules.free_api_safety" in app_text)

# Version markers
constants_text = (ROOT / "modules" / "constants.py").read_text(encoding="utf-8")
add("app_version_50", 'APP_VERSION = "50.0.0"' in constants_text)

report_path = out_dir / "v50_check_report.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
