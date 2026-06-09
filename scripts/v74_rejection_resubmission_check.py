from __future__ import annotations
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.rejection_resubmission_loop import V74RejectionResubmissionLoop


def main() -> int:
    out_dir = ROOT / "outputs" / "v74_check"
    engine = V74RejectionResubmissionLoop()
    report = engine.build_bundle(
        project_name="v74_check_rejection_loop",
        concept_text="작은 썸네일에서도 보이는 손그림 공감형 캐릭터 세트를 반려 사유 기준으로 개선한다.",
        selected_style=engine.STYLE_PRESETS[0],
        main_phrase="넵",
        user_feedback="초기 방향은 만족하지만 품질은 계속 진화해야 한다.",
        online_abstract_notes="온라인 자료는 추상 신호만 저장하고 복제하지 않는다.",
        rejection_text=engine.DEFAULT_REJECTION_TEXT,
        out_dir=out_dir,
    ).to_dict()
    checks = []
    def check(name: str, cond: bool):
        checks.append({"name": name, "pass": bool(cond)})
    check("status present", bool(report.get("rejection_status")))
    check("action plan csv exists", Path(report["action_plan_csv"]).exists())
    check("action plan json exists", Path(report["action_plan_json"]).exists())
    check("static 32 plan exists", Path(report["revised_static_32_plan_csv"]).exists())
    check("animated 24 plan exists", Path(report["revised_animated_24_plan_csv"]).exists())
    check("prompt pack exists", Path(report["prompt_pack_md"]).exists())
    check("trend memory exists", Path(report["trend_signal_memory_json"]).exists())
    check("html report exists", Path(report["html_report_path"]).exists())
    zip_path = Path(report["resubmission_work_package_zip"])
    check("work zip exists", zip_path.exists())
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            bad = zf.testzip()
            names = zf.namelist()
        check("work zip integrity", bad is None)
        check("work zip includes prompt pack", any("prompt_pack" in n for n in names))
        check("work zip includes manifest", any("manifest" in n for n in names))
    check("learning db exists", Path(report["learning_db"]).exists())
    check("detected categories", len(report.get("detected_categories", [])) >= 3)
    passed = all(c["pass"] for c in checks)
    result = {"pass": passed, "checks": checks, "report": report}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
