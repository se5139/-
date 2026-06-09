from __future__ import annotations
import json, zipfile, sys, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.template_engine_manager import TemplateEngineManager, API_KEY_PATTERN


def main() -> int:
    report = {"version": "v63", "checks": {}, "errors": []}
    try:
        engine = TemplateEngineManager()
        result = engine.render_manager_bundle(
            project_name="v63_template_manager_check",
            concept_text="하찮은 공감형 캐릭터. 정지형과 움직이는형을 같은 identity lock으로 관리한다.",
            intended_outputs=["HTML report", "Prompt template", "Style rulebook", "Motion template"],
            selected_template_policy="Jinja2 primary + Mako optional adapter",
            trend_signals=["짧은 답장", "GIF 즉시 미리보기", "단순 실루엣", "가독성"],
            out_dir=ROOT / "outputs" / "v63_template_engine_manager_check",
        )
        data = result.to_dict()
        report["result"] = data
        for key in ["html_report_path", "prompt_template_path", "style_rulebook_path", "motion_template_path", "engine_matrix_path", "manifest_path", "package_zip_path"]:
            path = Path(data[key])
            report["checks"][f"exists_{key}"] = path.exists() and path.stat().st_size > 0
        zpath = Path(data["package_zip_path"])
        with zipfile.ZipFile(zpath, "r") as zf:
            bad = zf.testzip()
            report["checks"]["zip_integrity"] = bad is None
            report["zip_files"] = zf.namelist()
        leak_files = []
        for key in ["html_report_path", "prompt_template_path", "style_rulebook_path", "motion_template_path", "engine_matrix_path", "manifest_path"]:
            path = Path(data[key])
            if API_KEY_PATTERN.search(path.read_text(encoding="utf-8-sig", errors="ignore")):
                leak_files.append(path.name)
        report["checks"]["api_key_raw_leak_absent"] = not leak_files
        report["checks"]["jinja2_available"] = importlib.util.find_spec("jinja2") is not None
        report["checks"]["mako_optional_available_current_env"] = importlib.util.find_spec("mako") is not None
        req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        report["checks"]["requirements_jinja_latest_floor"] = "Jinja2>=3.1.6" in req
        report["checks"]["requirements_mako_latest_floor"] = "Mako>=1.3.12" in req
        ok_required = all(v for k, v in report["checks"].items() if k != "mako_optional_available_current_env")
        report["ok"] = bool(ok_required)
    except Exception as exc:
        report["ok"] = False
        report["errors"].append(repr(exc))
    out = ROOT / "kakao_emoticon_profit_system_v63_verification_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
