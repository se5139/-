from __future__ import annotations
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.pre_submission_qc_engine import V71PreSubmissionQCEngine


def main() -> int:
    out_dir = ROOT / "outputs" / "v71_pre_submission_qc_check"
    engine = V71PreSubmissionQCEngine()
    result = engine.build_bundle(
        project_name="v71_check_pre_submission_qc",
        concept_text="작은 썸네일에서 잘 보이는 손그림 공감형 캐릭터. 정지형 32개와 움직이는형 24개 제출 전 QC를 점검한다.",
        selected_style=engine.STYLE_PRESETS[0],
        selected_rules=engine.QC_RULES,
        main_phrase="넵",
        user_feedback="초기 품질은 만족하지만 제출 전 규격, 용량, 프레임, 투명 배경, 파일명 검사를 강화한다.",
        online_abstract_notes="온라인 자료는 복제하지 않고 문구 길이, 모션 리듬, 썸네일 가독성, 다크모드 대비만 추상 신호로 반영한다.",
        out_dir=out_dir,
    )
    data = result.to_dict()
    required = [
        "qc_matrix_csv", "qc_matrix_json", "pre_submission_manifest_json", "normalized_export_plan_csv",
        "html_report_path", "learning_db", "pre_submission_qc_zip", "checklist_json",
        "static_gallery_png", "animated_gallery_png", "representative_gif",
    ]
    errors = []
    for key in required:
        p = Path(data.get(key, ""))
        if not p.exists() or p.stat().st_size <= 0:
            errors.append(f"missing_or_empty:{key}:{p}")
    if data.get("total_checks", 0) < 100:
        errors.append("too_few_qc_checks")
    if data.get("pass_count", 0) <= 0:
        errors.append("no_pass_checks")
    if not data.get("qc_scores"):
        errors.append("missing_qc_scores")
    zip_path = Path(data["pre_submission_qc_zip"])
    if zip_path.exists():
        try:
            with zipfile.ZipFile(zip_path) as zf:
                bad = zf.testzip()
                if bad:
                    errors.append(f"bad_zip_member:{bad}")
        except Exception as exc:
            errors.append(f"zip_error:{exc}")
    report = {"ok": not errors, "errors": errors, "result": data}
    (ROOT / "v71_pre_submission_qc_check_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
