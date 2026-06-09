from __future__ import annotations
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.submission_autofix_lock_engine import V72SubmissionAutofixLockEngine


def main() -> int:
    out_dir = ROOT / "outputs" / "v72_submission_autofix_lock_check"
    engine = V72SubmissionAutofixLockEngine()
    result = engine.build_bundle(
        project_name="v72_check_submission_autofix_lock",
        concept_text="작은 썸네일에서 잘 보이는 손그림 공감형 캐릭터 세트를 자동 보정하고 제출 후보 ZIP 잠금 상태를 판단한다.",
        selected_style=engine.STYLE_PRESETS[0],
        selected_rules=engine.AUTOFIX_RULES,
        main_phrase="넵",
        user_feedback="v71 QC 이후 용량, 파일명, 프레임, 최종 패키지 잠금/해제를 연결한다.",
        online_abstract_notes="온라인 자료는 복제하지 않고 썸네일 가독성, 짧은 답장형 문구, 모션 리듬만 추상 신호로 반영한다.",
        out_dir=out_dir,
    )
    data = result.to_dict()
    required = [
        "base_qc_zip", "static_export_zip", "animated_export_zip", "final_submission_zip", "locked_review_zip",
        "autofix_log_csv", "autofix_log_json", "final_manifest_json", "lock_manifest_json", "html_report_path", "learning_db",
    ]
    errors: list[str] = []
    for key in required:
        p = Path(data.get(key, ""))
        if not p.exists() or p.stat().st_size <= 0:
            errors.append(f"missing_or_empty:{key}:{p}")
    if data.get("exported_static_count") != 32:
        errors.append(f"static_count_not_32:{data.get('exported_static_count')}")
    if data.get("exported_animated_count") != 24:
        errors.append(f"animated_count_not_24:{data.get('exported_animated_count')}")
    if data.get("exported_gif_count", 0) < 3:
        errors.append(f"gif_count_less_than_3:{data.get('exported_gif_count')}")
    if not data.get("final_scores"):
        errors.append("missing_final_scores")
    for key in ["static_export_zip", "animated_export_zip", "final_submission_zip", "locked_review_zip"]:
        p = Path(data.get(key, ""))
        if p.exists():
            try:
                with zipfile.ZipFile(p) as zf:
                    bad = zf.testzip()
                    if bad:
                        errors.append(f"bad_zip_member:{key}:{bad}")
            except Exception as exc:
                errors.append(f"zip_error:{key}:{exc}")
    package_text = ""
    for key in required:
        p = Path(data.get(key, ""))
        if p.exists() and p.suffix.lower() in {".json", ".csv", ".html", ".txt", ".md"}:
            package_text += p.read_text(encoding="utf-8", errors="ignore")[:5000]
    if "sk-proj-" in package_text or "OPENAI_API_KEY=" in package_text:
        errors.append("possible_api_key_leak")
    report = {"ok": not errors, "errors": errors, "result": data}
    (ROOT / "v72_submission_autofix_lock_check_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
