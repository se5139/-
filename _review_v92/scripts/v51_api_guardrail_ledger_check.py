
from __future__ import annotations

import json
import py_compile
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs" / "v51_verification"
OUT.mkdir(parents=True, exist_ok=True)

results = []

def add(name: str, ok: bool, detail: str = "") -> None:
    results.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

try:
    py_compile.compile(str(ROOT / "app.py"), doraise=True)
    add("app.py compile", True)
except Exception as exc:
    add("app.py compile", False, str(exc))

try:
    from modules.api_guardrail_ledger import V51ApiGuardrailConfig, V51ApiGuardrailLedgerEngine
    add("v51 module import", True)
except Exception as exc:
    add("v51 module import", False, str(exc))

try:
    from modules.api_guardrail_ledger import V51ApiGuardrailConfig, V51ApiGuardrailLedgerEngine
    sample = OUT / "sample.txt"
    sample.write_text("넵 확인했습니다 퇴근 피곤 감사 움직이는 문구형", encoding="utf-8")
    report = V51ApiGuardrailLedgerEngine().build_report(
        OUT / "engine_smoke",
        config=V51ApiGuardrailConfig(youtube_enabled=True, daily_youtube_search_limit=10),
        local_input_paths=[sample],
        manual_notes="정지형 기준 프레임 유지",
        search_keywords="직장인 공감 이모티콘, 짧은 답장",
        youtube_api_key="AIza-test-key-example",
    )
    data = report.to_dict()
    add("v51 engine smoke", bool(data.get("quota_ledger")) and bool(data.get("workflow_application")))
    raw = json.dumps(data, ensure_ascii=False)
    add("raw api key not stored", "AIza-test-key-example" not in raw)
    add("paid call blocked default", data.get("cost_guard", {}).get("external_api_called_by_v51") is False)
    add("report package zip exists", Path(data.get("zip_path", "")).exists())
except Exception as exc:
    add("v51 engine smoke", False, str(exc))

try:
    for bat in ["1_INSTALL_NOW.bat", "START_WINDOWS.bat", "4_REPAIR_ENVIRONMENT.bat", "18_V51_API_GUARDRAIL_LEDGER_CHECK.bat"]:
        text = (ROOT / bat).read_text(encoding="ascii")
        add(f"{bat} ASCII", True)
        add(f"{bat} no v49 marker", "[v49]" not in text and "v49" not in text.lower())
        add(f"{bat} no v50 marker", "[v50]" not in text and "v50" not in text.lower())
except Exception as exc:
    add("BAT ASCII/no stale marker", False, str(exc))

try:
    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    required = ["48 API 키/쿼터 장부/유료차단", "V51ApiGuardrailLedgerEngine", "v51_apply_to_workflow"]
    add("v51 UI markers", all(x in app_text for x in required), str([x for x in required if x not in app_text]))
except Exception as exc:
    add("v51 UI markers", False, str(exc))

ok_all = all(r["status"] == "PASS" for r in results)
report_path = OUT / "v51_check_report.json"
report_path.write_text(json.dumps({"ok": ok_all, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": ok_all, "report_path": str(report_path), "results": results}, ensure_ascii=False, indent=2))
raise SystemExit(0 if ok_all else 1)
