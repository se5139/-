from __future__ import annotations

import ast
import compileall
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "outputs" / "v49_verification"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def find_duplicate_streamlit_keys(app_text: str) -> list[str]:
    keys = re.findall(r"key\s*=\s*['\"]([^'\"]+)['\"]", app_text)
    seen = set()
    dup = []
    for k in keys:
        if k in seen and k not in dup:
            dup.append(k)
        seen.add(k)
    return dup


def root_bat_ascii_only() -> tuple[bool, str]:
    bad = []
    for bat in ROOT.glob("*.bat"):
        try:
            bat.read_text(encoding="ascii")
        except UnicodeDecodeError:
            bad.append(bat.name)
    return (not bad, ", ".join(bad))


def main() -> int:
    results = []
    results.append(check("ROOT_EXISTS", ROOT.exists(), str(ROOT)))
    results.append(check("APP_EXISTS", (ROOT / "app.py").exists(), "app.py"))
    results.append(check("V49_ENGINE_EXISTS", (ROOT / "modules" / "evolution_quality" / "static_animated_evolution_engine.py").exists(), "static_animated_evolution_engine.py"))

    compile_ok = compileall.compile_dir(str(ROOT / "modules"), quiet=1)
    try:
        py_compile_app = compile(str((ROOT / "app.py").read_text(encoding="utf-8")), "app.py", "exec") is not None
    except Exception as exc:
        py_compile_app = False
        results.append(check("APP_PY_COMPILE", False, str(exc)))
    else:
        results.append(check("APP_PY_COMPILE", py_compile_app, "compiled"))
    results.append(check("MODULES_COMPILEALL", bool(compile_ok), "compileall modules"))

    sys.path.insert(0, str(ROOT))
    try:
        from modules.constants import APP_NAME, APP_VERSION
        from modules.evolution_quality import StaticAnimatedEvolutionEngine
        import pandas  # noqa
        results.append(check("IMPORTS", True, f"{APP_NAME} / {APP_VERSION}"))
    except Exception as exc:
        results.append(check("IMPORTS", False, str(exc)))
        report_path = REPORT_DIR / "v49_static_animated_evolution_check_report.json"
        report_path.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1

    # Smoke test with multi files and zip.
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            img_path = tmp_dir / "static_reference.png"
            img = Image.new("RGBA", (360, 360), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((82, 72, 278, 272), fill=(246, 213, 143, 255), outline=(40, 36, 31, 255), width=7)
            draw.ellipse((130, 150, 150, 170), fill=(40, 36, 31, 255))
            draw.ellipse((210, 150, 230, 170), fill=(40, 36, 31, 255))
            draw.arc((145, 190, 215, 230), 0, 180, fill=(40, 36, 31, 255), width=5)
            img.save(img_path)
            txt_path = tmp_dir / "trend_notes.txt"
            txt_path.write_text("넵 확인했습니다 피곤 퇴근 통통 움직임 굵은 외곽선 큰 실루엣 표정", encoding="utf-8")
            zip_path = tmp_dir / "references.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(txt_path, "notes/trend_notes.txt")
                zf.write(img_path, "images/static_reference.png")
            report = StaticAnimatedEvolutionEngine().build_report(
                ROOT / "outputs" / "v49_engine_smoke",
                project_name="v49_smoke_test",
                character_concept="둥글고 예의 바른 직장인용 독창 캐릭터",
                issue_text="정지형과 움직이는형 모두 품질 개선 필요",
                source_text="짧은 답장, 표정이 선명한 캐릭터, 눈깜빡임, 말풍선 팝업",
                source_urls="https://example.com/reference-note",
                target_formats=["static", "animated"],
                target_style="귀엽고 세련된 카카오톡형",
                input_paths=[img_path, txt_path, zip_path],
            )
            data = report.to_dict()
            results.append(check("ENGINE_SMOKE", data.get("static_quality_score", 0) > 0 and data.get("animated_quality_score", 0) > 0, f"static={data.get('static_quality_score')} animated={data.get('animated_quality_score')}"))
            for key in ["html_path", "json_path", "csv_path", "board_png_path", "animated_preview_gif_path", "zip_path"]:
                p = Path(data.get(key, ""))
                results.append(check(f"OUTPUT_{key.upper()}", p.exists() and p.stat().st_size > 0, str(p)))
            results.append(check("ZIP_ANALYSIS", data.get("zip_count", 0) >= 1 and data.get("image_count", 0) >= 1 and data.get("text_count", 0) >= 1, f"zip={data.get('zip_count')} image={data.get('image_count')} text={data.get('text_count')}"))
    except Exception as exc:
        results.append(check("ENGINE_SMOKE", False, str(exc)))

    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    results.append(check("V49_TAB_PRESENT", "46 후보 적용/정지형/움직이는형 품질 진화" in app_text, "tab title"))
    results.append(check("V49_MULTI_UPLOAD_PRESENT", "accept_multiple_files=True" in app_text and "zip" in app_text.lower(), "multi upload + zip marker"))
    results.append(check("V49_APPLY_FLOW_PRESENT", "v49_apply_to_workflow" in app_text and "static_to_animated_plan" in app_text, "workflow apply marker"))
    duplicates = find_duplicate_streamlit_keys(app_text)
    results.append(check("STREAMLIT_DUPLICATE_KEY_STATIC_SCAN", not duplicates, ", ".join(duplicates[:20])))
    ascii_ok, ascii_detail = root_bat_ascii_only()
    results.append(check("ROOT_BAT_ASCII_ONLY", ascii_ok, ascii_detail or "ASCII-only"))
    for rel in ["1_INSTALL_NOW.bat", "START_WINDOWS.bat", "4_REPAIR_ENVIRONMENT.bat", "scripts/create_shortcuts_v49.ps1", "scripts/cleanup_old_versions_v49.ps1"]:
        text = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        results.append(check(f"VERSION_MARKER_{rel}", "v49" in text or "V49" in text, rel))
    install_text = (ROOT / "1_INSTALL_NOW.bat").read_text(encoding="utf-8", errors="ignore")
    results.append(check("NO_V48_TARGET_IN_INSTALLER", "KakaoEmoticonProfitSystemV48" not in install_text and "C:\\KakaoEmoticonV48" not in install_text, "installer target"))

    ok = all(r["status"] == "PASS" for r in results)
    report = {"ok": ok, "results": results}
    report_path = REPORT_DIR / "v49_static_animated_evolution_check_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
