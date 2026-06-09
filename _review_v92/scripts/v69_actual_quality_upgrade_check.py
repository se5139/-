from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.actual_quality_upgrade_engine import V69ActualQualityUpgradeEngine


def main() -> int:
    out_dir = ROOT / "outputs" / "v69_check_output"
    engine = V69ActualQualityUpgradeEngine()
    report = engine.build_bundle(
        project_name="v69_check",
        concept_text="작은 썸네일에서도 읽히는 손그림 공감형 캐릭터",
        selected_style="손그림 공감형 · 굵은 외곽선",
        selected_rules=engine.QUALITY_RULES,
        main_phrase="넵",
        user_feedback="초기 결과는 만족하지만 품질이 계속 진화해야 한다.",
        online_abstract_notes="짧은 답장형, 미니 리액션, 손그림 질감, 썸네일 가독성, 자연스러운 루프 모션",
        out_dir=out_dir,
    )
    data = report.to_dict()
    required_paths = [
        "static_png", "darkmode_preview_png", "motion_preview_gif", "motion_contact_sheet",
        "static_32_plan_csv", "static_32_plan_json", "animated_24_plan_csv", "animated_24_plan_json",
        "style_memory_json", "quality_metrics_json", "learning_db", "html_report_path", "prompt_pack_path", "package_zip_path",
    ]
    missing = [k for k in required_paths if not Path(data[k]).exists()]
    if missing:
        raise AssertionError(f"Missing output paths: {missing}")
    if len(data["motion_variants"]) < 6:
        raise AssertionError("Motion variants must be >= 6")
    if min(data["quality_scores"].values()) < 20:
        raise AssertionError("Quality score too low")
    with zipfile.ZipFile(data["package_zip_path"], "r") as zf:
        bad = zf.testzip()
        if bad:
            raise AssertionError(f"Bad zip entry: {bad}")
        names = zf.namelist()
        if not any(n.endswith(".gif") for n in names):
            raise AssertionError("Package must contain gif")
        if not any(n.endswith(".html") for n in names):
            raise AssertionError("Package must contain html report")
    # Ensure no sample or real API key-like values were serialized.
    serialized = json.dumps(data, ensure_ascii=False)
    if "sk-proj-" in serialized or "OPENAI_API_KEY=" in serialized:
        raise AssertionError("API key-like string leaked")
    print(json.dumps({"status": "PASS", "report": data}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
