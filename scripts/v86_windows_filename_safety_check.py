from __future__ import annotations
from pathlib import Path
import json, re, tempfile, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.set_completeness_engine import V70SetCompletenessEngine

INVALID = set('<>:"/\\|?*')

def has_invalid_windows_name(path: Path) -> bool:
    return any(ch in INVALID or ord(ch) < 32 for ch in path.name)

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "outputs" / "v86_filename_safety_check"
    eng = V70SetCompletenessEngine()
    report = eng.build_bundle(
        project_name="v86_filename_safety_check",
        concept_text="Windows 파일명 안전성 점검: 진짜? 좋아요/확인 같은 문구 포함",
        selected_style="손그림 공감형 · 굵은 외곽선",
        selected_rules=["문구 원문은 유지하되 파일명은 안전하게 정리"],
        main_phrase="진짜?",
        user_feedback="세트 생성 중 물음표가 파일명에 들어가면 Windows에서 오류가 난다.",
        online_abstract_notes="짧은 답장형, 하찮은 공감형, 미니 리액션성",
        out_dir=out,
    )
    run_dir = Path(report.output_dir)
    bad = [str(p.relative_to(run_dir)) for p in run_dir.rglob('*') if p.is_file() and has_invalid_windows_name(p)]
    summary = {
        "status": "PASS" if not bad else "FAIL",
        "output_dir": str(run_dir),
        "invalid_windows_filenames": bad,
        "static_count": len(list((run_dir / 'static_32_png').glob('*.png'))),
        "animated_files": len(list((run_dir / 'animated_24_candidate').glob('*'))),
        "candidate_zip_exists": Path(report.candidate_submission_zip).exists(),
    }
    check_report = root / "v86_windows_filename_safety_check_report.json"
    check_report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
