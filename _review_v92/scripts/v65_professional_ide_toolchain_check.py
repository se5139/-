
from __future__ import annotations
import ast, json, re, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
API_KEY_PATTERN = re.compile(r"sk-(?:proj|[A-Za-z0-9])[-_A-Za-z0-9]{20,}")
def main() -> int:
    report = {"checks": {}, "errors": []}
    required = [
        ROOT/"modules"/"professional_ide_toolchain_manager.py",
        ROOT/"templates"/"v65_professional_ide_toolchain"/"ide_toolchain_report.html.j2",
        ROOT/"templates"/"v65_professional_ide_toolchain"/"ide_matrix.csv.j2",
        ROOT/"templates"/"v65_professional_ide_toolchain"/"developer_install_guide.md.j2",
        ROOT/"docs"/"v65_professional_ide_toolchain.md",
        ROOT/".vscode"/"extensions.json",
        ROOT/"requirements-dev.txt",
    ]
    for p in required:
        ok = p.exists(); report["checks"][f"exists:{p.relative_to(ROOT)}"] = ok
        if not ok: report["errors"].append(f"missing {p}")
    ast.parse((ROOT/"app.py").read_text(encoding="utf-8")); report["checks"]["app_ast_ok"] = True
    from modules.professional_ide_toolchain_manager import ProfessionalIDEToolchainManager
    mgr = ProfessionalIDEToolchainManager(); res = mgr.render_bundle("v65_check_project", ROOT/"outputs"/"v65_professional_ide_toolchain_check"); d = res.to_dict()
    report["checks"]["render_ok"] = bool(d.get("ok"))
    for key, tool in [("has_pycharm","PyCharm Professional"),("has_vscode","Visual Studio Code"),("has_visual_studio","Visual Studio"),("has_android_studio","Android Studio")]:
        report["checks"][key] = any(row["tool"] == tool for row in d.get("ide_tools", []))
    report["checks"]["tool_count_10"] = len(d.get("ide_tools", [])) >= 10
    report["checks"]["package_zip_valid"] = zipfile.is_zipfile(d["package_zip_path"])
    report["checks"]["final_python_rule"] = "Python-centered" in Path(d["manifest_path"]).read_text(encoding="utf-8")
    for path_key in ["html_report_path","ide_matrix_path","stack_policy_path","install_guide_path","vscode_recommendations_path","pycharm_note_path","manifest_path"]:
        text = Path(d[path_key]).read_text(encoding="utf-8-sig", errors="ignore")
        if API_KEY_PATTERN.search(text): report["errors"].append(f"api key leaked in {path_key}")
    report["checks"]["no_api_key_leak"] = not report["errors"]
    report["checks"]["app_menu_has_v65"] = "55 전문 IDE/코딩 프로그램 적용 기준" in (ROOT/"app.py").read_text(encoding="utf-8")
    ok = all(report["checks"].values()) and not report["errors"]; report["ok"] = ok
    out = ROOT/"kakao_emoticon_profit_system_v65_verification_report.json"; out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if ok else 1
if __name__ == "__main__": raise SystemExit(main())
