from __future__ import annotations
import ast, json, re, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
API_KEY_PATTERN = re.compile(r"sk-(?:proj|[A-Za-z0-9])[-_A-Za-z0-9]{20,}")

def main() -> int:
    report = {"checks": {}, "errors": []}
    required = [
        ROOT/"modules"/"multi_tool_execution_pipeline.py",
        ROOT/"templates"/"v66_multi_tool_execution"/"execution_report.html.j2",
        ROOT/"templates"/"v66_multi_tool_execution"/"workflow.md.j2",
        ROOT/"templates"/"v66_multi_tool_execution"/"github_quality_check.yml.j2",
        ROOT/"docs"/"v66_multi_tool_execution_pipeline.md",
        ROOT/"installer"/"KakaoEmoticonSetup_v66.iss",
        ROOT/"scripts"/"build_inno_installer_v66.py",
        ROOT/"run_cleanup_old_versions_v66.bat",
        ROOT/"14_V66_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat",
    ]
    for p in required:
        ok = p.exists()
        report["checks"][f"exists:{p.relative_to(ROOT)}"] = ok
        if not ok:
            report["errors"].append(f"missing {p}")
    ast.parse((ROOT/"app.py").read_text(encoding="utf-8"))
    report["checks"]["app_ast_ok"] = True
    from modules.constants import APP_VERSION, V66_MULTI_TOOL_EXECUTION_PIPELINE
    report["checks"]["version_66"] = APP_VERSION.startswith("66") and bool(V66_MULTI_TOOL_EXECUTION_PIPELINE)
    from modules.multi_tool_execution_pipeline import MultiToolExecutionPipeline
    result = MultiToolExecutionPipeline().render_bundle("v66_check_project", ROOT/"outputs"/"v66_multi_tool_execution_check")
    d = result.to_dict()
    report["checks"]["render_ok"] = bool(d.get("ok"))
    report["checks"]["stage_count_10"] = len(d.get("stages", [])) >= 10
    report["checks"]["has_jinja_stage"] = any(s["primary_tool"] == "Jinja2" for s in d["stages"])
    report["checks"]["has_inno_stage"] = any(s["primary_tool"] == "Inno Setup" for s in d["stages"])
    report["checks"]["package_zip_valid"] = zipfile.is_zipfile(d["package_zip_path"])
    app_text = (ROOT/"app.py").read_text(encoding="utf-8")
    report["checks"]["app_menu_has_v66"] = "56 멀티툴 개발 실행/검증 파이프라인" in app_text
    build_text = (ROOT/"0_BUILD_WINDOWS_INSTALLER_EXE.bat").read_text(encoding="utf-8", errors="ignore")
    report["checks"]["active_build_script_v66"] = "build_inno_installer_v66.py" in build_text
    iss_text = (ROOT/"installer"/"KakaoEmoticonSetup_v66.iss").read_text(encoding="utf-8", errors="ignore")
    report["checks"]["inno_version_66"] = "AppVersion={#MyAppVersion}" in iss_text and 'MyAppVersion "66.0.0"' in iss_text
    for path_key in ["html_report_path", "workflow_markdown_path", "tool_usage_matrix_path", "qa_checklist_path", "manifest_path"]:
        text = Path(d[path_key]).read_text(encoding="utf-8-sig", errors="ignore")
        if API_KEY_PATTERN.search(text):
            report["errors"].append(f"api key leaked in {path_key}")
    scan_files = [ROOT/"app.py", ROOT/"modules"/"multi_tool_execution_pipeline.py", ROOT/"scripts"/"v66_multi_tool_execution_check.py"]
    for p in scan_files:
        if API_KEY_PATTERN.search(p.read_text(encoding="utf-8", errors="ignore")):
            report["errors"].append(f"api key pattern found in {p.relative_to(ROOT)}")
    report["checks"]["no_api_key_leak"] = not report["errors"]
    ok = all(report["checks"].values()) and not report["errors"]
    report["ok"] = ok
    out = ROOT/"kakao_emoticon_profit_system_v66_verification_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1
if __name__ == "__main__":
    raise SystemExit(main())
