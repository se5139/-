from __future__ import annotations

import ast
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_KEY_RE = re.compile(r"sk-(?:proj|[A-Za-z0-9])[-_A-Za-z0-9]{20,}")


def check(cond: bool, name: str, details: str = "") -> dict:
    return {"name": name, "status": "PASS" if cond else "FAIL", "details": details}


def main() -> int:
    results = []
    sys.path.insert(0, str(ROOT))

    # Syntax checks.
    for rel in ["app.py", "modules/jinja_template_engine.py", "modules/constants.py"]:
        p = ROOT / rel
        try:
            ast.parse(p.read_text(encoding="utf-8"))
            results.append(check(True, f"syntax:{rel}"))
        except Exception as exc:
            results.append(check(False, f"syntax:{rel}", repr(exc)))

    # Import and smoke test.
    try:
        from modules.jinja_template_engine import JinjaTemplateEngine
        engine = JinjaTemplateEngine()
        out_dir = ROOT / "outputs" / "v62_check"
        report = engine.render_bundle(
            project_name="v62_check",
            concept_text="짧은 답장형 캐릭터 " + "sk-" + "proj-DUMMY_SHOULD_BE_MASKED_1234567890",
            style_preset="하찮은 공감형",
            selected_suggestions=["정지형 외형 고정", "움직이는형 GIF 미리보기"],
            trend_signals=["짧은 문구", "미니 리액션"],
            v61_report={"static_png_path":"sample.png", "primary_gif_path":"sample.gif", "kakao_24_plan":[1,2,3]},
            out_dir=out_dir,
        )
        rd = report.to_dict()
        results.append(check(rd.get("ok") is True, "engine smoke test", rd.get("html_report_path", "")))
        required = ["html_report_path", "prompt_path", "motion_plan_path", "manifest_path", "package_zip_path"]
        results.append(check(all(Path(rd[k]).exists() for k in required), "rendered output files"))
        leak_files = []
        for k in required:
            p = Path(rd[k])
            if p.suffix.lower() == ".zip":
                with zipfile.ZipFile(p) as zf:
                    for name in zf.namelist():
                        data = zf.read(name).decode("utf-8-sig", errors="ignore")
                        if API_KEY_RE.search(data):
                            leak_files.append(f"{p.name}:{name}")
            else:
                text = p.read_text(encoding="utf-8-sig", errors="ignore")
                if API_KEY_RE.search(text):
                    leak_files.append(p.name)
        results.append(check(not leak_files, "API key raw leakage check", ", ".join(leak_files)))
    except Exception as exc:
        results.append(check(False, "engine smoke test", repr(exc)))

    # Requirements and template checks.
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    results.append(check("Jinja2" in req, "requirements include Jinja2"))
    templates = [
        ROOT / "templates/v62_jinja/kakao_report.html.j2",
        ROOT / "templates/v62_jinja/prompt_pack.md.j2",
        ROOT / "templates/v62_jinja/motion_plan.csv.j2",
    ]
    results.append(check(all(p.exists() for p in templates), "Jinja2 template files exist"))

    # App routing markers.
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    results.append(check("52 Jinja2 템플릿 리포트/프롬프트 엔진" in app, "sidebar menu label"))
    results.append(check("if selected_page_index == 51" in app, "v62 page route"))
    results.append(check("JinjaTemplateEngine" in app, "app imports engine"))

    # Installer markers.
    iss = ROOT / "installer/KakaoEmoticonSetup_v62.iss"
    results.append(check(iss.exists(), "v62 Inno Setup script exists"))
    if iss.exists():
        txt = iss.read_text(encoding="utf-8")
        results.append(check("KakaoEmoticonSetup_v62" in txt and "KakaoEmoticonProfitSystemV62" in txt, "v62 installer markers"))

    report_path = ROOT / "kakao_emoticon_profit_system_v62_verification_report.json"
    report = {"version": "v62", "ok": all(r["status"] == "PASS" for r in results), "results": results}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
