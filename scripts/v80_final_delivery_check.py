
from __future__ import annotations
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.final_delivery_pipeline import V80FinalDeliveryPipelineEngine


def main() -> int:
    out = ROOT / "outputs" / "v80_final_check"
    result = V80FinalDeliveryPipelineEngine().build_bundle(out_dir=out)
    data = result.to_dict()
    checks = []
    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("final_status_ready", data["final_status"] == "FINAL_DELIVERY_READY", data["final_status"])
    add("pipeline_steps_passed", data["passed_pipeline_steps"] == data["total_pipeline_steps"], f"{data['passed_pipeline_steps']}/{data['total_pipeline_steps']}")
    add("v76_report_exists", Path(data["v76_regeneration_report_html"]).exists(), data["v76_regeneration_report_html"])
    add("v73_report_exists", Path(data["v73_approval_report_html"]).exists(), data["v73_approval_report_html"])
    add("final_html_exists", Path(data["final_html_report"]).exists(), data["final_html_report"])
    add("final_manifest_exists", Path(data["final_manifest_json"]).exists(), data["final_manifest_json"])
    add("final_master_zip_exists", Path(data["final_master_delivery_zip"]).exists(), data["final_master_delivery_zip"])
    add("api_key_plaintext_not_found", not data["api_key_plaintext_found"], "sensitive token scan")
    zpath = Path(data["final_master_delivery_zip"])
    zip_ok = False
    zip_members = 0
    if zpath.exists():
        try:
            with zipfile.ZipFile(zpath) as zf:
                bad = zf.testzip()
                zip_members = len(zf.namelist())
                zip_ok = bad is None and zip_members >= 5
        except Exception as exc:
            add("zip_integrity", False, repr(exc))
        else:
            add("zip_integrity", zip_ok, f"members={zip_members}")
    ok = all(c["ok"] for c in checks)
    report = {"ok": ok, "result": data, "checks": checks}
    report_path = ROOT / "v80_final_delivery_check_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
