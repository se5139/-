from __future__ import annotations
import json
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.final_user_approval_workflow import V73FinalUserApprovalWorkflow


def main() -> int:
    out = ROOT / "outputs" / "v73_check"
    engine = V73FinalUserApprovalWorkflow()
    confirmations = {k: True for k, _ in engine.REQUIRED_CONFIRMATIONS + engine.OPTIONAL_CONFIRMATIONS}
    report = engine.build_bundle(
        project_name="v73_final_user_approval_check",
        concept_text="사용자 최종 승인 후 제출 후보 ZIP을 열어주는 카카오형 손그림 공감 이모티콘 세트",
        selected_style=engine.STYLE_PRESETS[0],
        main_phrase="넵",
        user_feedback="최종 제출 전에는 반드시 사용자가 직접 32개/24개/GIF/저작권/공식 기준을 확인해야 한다.",
        online_abstract_notes="온라인 자료는 추상 신호로만 반영하고 기존 캐릭터 복제 금지.",
        user_confirmations=confirmations,
        out_dir=out,
    )
    d = report.to_dict()
    required_paths = [
        "approval_checklist_csv", "approval_manifest_json", "html_report_path",
        "final_approved_zip", "manual_review_zip", "learning_db",
    ]
    errors = []
    for key in required_paths:
        p = Path(d[key])
        if not p.exists() or p.stat().st_size == 0:
            errors.append(f"missing_or_empty:{key}:{p}")
    if not d["final_submission_allowed"]:
        errors.append("final_submission_allowed_false")
    if d["approval_status"] != "USER_APPROVED_FINAL_CANDIDATE":
        errors.append("approval_status_not_approved")
    with zipfile.ZipFile(d["final_approved_zip"], "r") as zf:
        bad = zf.testzip()
        if bad:
            errors.append(f"bad_zip_member:{bad}")
        names = zf.namelist()
        if not any("v73_user_approval_manifest.json" in n for n in names):
            errors.append("manifest_not_in_final_zip")
    # Security check: no raw key-like strings in generated text/archives names.
    for text_path in [Path(d["approval_manifest_json"]), Path(d["html_report_path"]), Path(d["approval_checklist_csv"])]:
        txt = text_path.read_text(encoding="utf-8", errors="ignore")
        if "sk-proj-" in txt or "OPENAI_API_KEY=" in txt:
            errors.append(f"api_key_pattern_in:{text_path.name}")
    print(json.dumps({"ok": not errors, "errors": errors, "report": d}, ensure_ascii=False, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
