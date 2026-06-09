from __future__ import annotations
import json, re, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
API_KEY_PATTERN = re.compile(r"sk-(?:proj|[A-Za-z0-9])[-_A-Za-z0-9]{20,}")

def main() -> int:
    from modules.coding_toolchain_manager import CodingToolchainManager
    report = {"checks": {}, "errors": []}
    required = [
        ROOT/"modules"/"coding_toolchain_manager.py",
        ROOT/"templates"/"v64_coding_toolchain_manager"/"toolchain_report.html.j2",
        ROOT/"docs"/"v64_coding_program_toolchain.md",
        ROOT/"requirements-dev.txt",
        ROOT/".vscode"/"settings.json",
        ROOT/".gitignore",
    ]
    for p in required:
        ok = p.exists()
        report["checks"][f"exists:{p.relative_to(ROOT)}"] = ok
        if not ok: report["errors"].append(f"missing {p}")
    mgr = CodingToolchainManager()
    res = mgr.render_toolchain_bundle("v64_check_project", ROOT/"outputs"/"v64_coding_toolchain_check")
    d = res.to_dict()
    report["checks"]["render_ok"] = bool(d.get("ok"))
    report["checks"]["has_python_final_rule"] = any("Python" in row["tools"] for row in d.get("toolchain", []))
    report["checks"]["has_jinja_primary"] = any(row["engine"] == "Jinja2" and "Primary" in row["decision"] for row in d.get("template_engines", []))
    report["checks"]["has_tool_categories"] = len(d.get("toolchain", [])) >= 10
    report["checks"]["package_zip_valid"] = zipfile.is_zipfile(d["package_zip_path"])
    for path_key in ["html_report_path","prompt_pack_path","toolchain_matrix_path","template_engine_matrix_path","install_checklist_path","manifest_path"]:
        text = Path(d[path_key]).read_text(encoding="utf-8-sig", errors="ignore")
        if API_KEY_PATTERN.search(text):
            report["errors"].append(f"api key leaked in {path_key}")
    report["checks"]["no_api_key_leak"] = not report["errors"]
    ok = all(report["checks"].values()) and not report["errors"]
    report["ok"] = ok
    out = ROOT/"kakao_emoticon_profit_system_v64_verification_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1
if __name__ == "__main__":
    raise SystemExit(main())
