
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.set_completeness_engine import V70SetCompletenessEngine


def main() -> int:
    out_dir = ROOT / "outputs" / "v70_check_output"
    engine = V70SetCompletenessEngine()
    report = engine.build_bundle(
        project_name="v70_check",
        concept_text="작은 썸네일에서도 읽히는 손그림 공감형 캐릭터를 32개 정지형과 24개 움직이는형 세트로 완성한다.",
        selected_style="손그림 공감형 · 굵은 외곽선",
        selected_rules=engine.QUALITY_RULES,
        main_phrase="넵",
        user_feedback="초기 결과는 만족하지만 세트 전체 다양성과 움직이는형 구성 완성도가 올라가야 한다.",
        online_abstract_notes="짧은 답장형, 미니 리액션, 손그림 질감, 썸네일 가독성, 세트 감정 분산, 자연스러운 루프 모션",
        out_dir=out_dir,
    )
    data = report.to_dict()
    required = [
        "static_gallery_png", "animated_gallery_png", "motion_contact_sheet", "representative_static_png", "representative_gif",
        "static_32_plan_csv", "static_32_plan_json", "animated_24_plan_csv", "animated_24_plan_json",
        "set_quality_matrix_csv", "set_quality_matrix_json", "static_32_package_zip", "animated_24_package_zip",
        "candidate_submission_zip", "html_report_path", "prompt_pack_path", "learning_db", "identity_lock_json",
    ]
    missing = [k for k in required if not Path(data[k]).exists()]
    if missing:
        raise AssertionError(f"Missing paths: {missing}")
    if len(data["required_gif_paths"]) < 3:
        raise AssertionError("At least 3 GIF paths required")
    if data["set_scores"].get("gif_readiness", 0) < 90:
        raise AssertionError("GIF readiness too low")
    with zipfile.ZipFile(data["candidate_submission_zip"], "r") as zf:
        bad = zf.testzip()
        if bad:
            raise AssertionError(f"Bad zip entry: {bad}")
        names = zf.namelist()
        if not any(n.endswith(".html") for n in names):
            raise AssertionError("HTML report missing in package")
        if sum(1 for n in names if n.endswith(".gif")) < 3:
            raise AssertionError("Required gifs missing in package")
    serialized = json.dumps(data, ensure_ascii=False)
    if "sk-proj-" in serialized or "OPENAI_API_KEY=" in serialized:
        raise AssertionError("API key-like string leaked")
    print(json.dumps({"status": "PASS", "report": data}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
