from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import zipfile
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.set_completeness_engine import V70SetCompletenessEngine
from scripts.cleanup_old_versions_v90 import run as cleanup_run

INVALID_WINDOWS_CHARS = set('<>:"/\\|?*')
ROOT_BAT_LIMIT = 8

SPECIAL_STATIC = [
    ("진짜?", "놀람", "jump"),
    ("확인/완료", "완료", "check"),
    ("다시!", "재도전", "bounce"),
    ("흠...", "고민", "think"),
    ("좋아요~!", "긍정", "bounce"),
    ("왜요?", "당황", "wobble"),
    ("안녕:)", "인사", "wave"),
    ("고마워요♡", "감사", "sparkle"),
    ("한글 파일명 테스트", "확인", "check"),
    ("띄어쓰기 파일명 테스트", "확인", "check"),
    ("긴 파일명 테스트 " + "가" * 70, "확인", "check"),
    ("<위험>", "주의", "hold"),
    ('따옴표"테스트', "주의", "hold"),
    ("역슬래시\\테스트", "주의", "hold"),
    ("파이프|테스트", "주의", "hold"),
    ("별표*테스트", "주의", "hold"),
    ("CON", "예약어", "hold"),
    ("AUX", "예약어", "hold"),
    ("NUL", "예약어", "hold"),
    ("COM1", "예약어", "hold"),
    ("LPT1", "예약어", "hold"),
]


def has_invalid_windows_name(name: str) -> bool:
    # Check every path segment, because zip arc names may contain subfolders.
    for part in re.split(r"[\\/]", str(name)):
        if not part or part in {".", ".."}:
            continue
        if any(ch in INVALID_WINDOWS_CHARS or ord(ch) < 32 for ch in part):
            return True
        stem = Path(part).stem.upper()
        if stem in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
            return True
    return False


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check_zip_names(zip_path: Path) -> list[str]:
    bad: list[str] = []
    if not zip_path.exists():
        return [f"MISSING_ZIP::{zip_path}"]
    with zipfile.ZipFile(zip_path) as zf:
        if zf.testzip() is not None:
            bad.append(f"CORRUPT_ZIP::{zip_path}")
        for name in zf.namelist():
            if has_invalid_windows_name(name):
                bad.append(name)
    return bad


def scan_api_key_literals(root: Path) -> list[str]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}"),
        re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    ]
    skip_dirs = {".git", ".venv", "__pycache__", "outputs", "installer/Output"}
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(x) for x in skip_dirs):
            continue
        if path.suffix.lower() not in {".py", ".bat", ".ps1", ".txt", ".md", ".json", ".csv", ".iss", ".yml", ".yaml", ".html", ".j2"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat.search(text):
                hits.append(rel)
                break
    return sorted(set(hits))



def run_cleanup_fake_flow_test(root: Path) -> dict[str, Any]:
    fake_root = root / "outputs" / "v90_cleanup_fake_scan_root"
    if fake_root.exists():
        import shutil
        shutil.rmtree(fake_root)
    fake_root.mkdir(parents=True, exist_ok=True)

    old66 = fake_root / "kakao_emoticon_profit_system_v66_manual_extract"
    old80 = fake_root / "kakao_emoticon_profit_system_v80_final"
    old88 = fake_root / "kakao_emoticon_profit_system_v88_previous_install"
    old89 = fake_root / "kakao_emoticon_profit_system_v89_previous_install"
    current90 = fake_root / "kakao_emoticon_profit_system_v90_current"
    for folder in [old66, old80, old88, old89, current90]:
        (folder / "outputs" / "samples").mkdir(parents=True, exist_ok=True)
        (folder / "outputs" / "samples" / "테스트.png").write_bytes(b"fake-png")
        (folder / "settings.json").write_text("{\"ok\": true}", encoding="utf-8")
    out_root = root / "outputs" / "v90_cleanup_test_reports"

    preview = cleanup_run(
        mode="preview",
        scan_roots=[fake_root],
        current_version=90,
        current_path=current90,
        output_root=out_root,
        confirm=None,
        yes=False,
    )
    preview_detected = preview.get("candidate_count") == 4
    current_excluded = all("v90_current" not in c.get("path", "") for c in preview.get("candidates", []))

    quarantine = cleanup_run(
        mode="quarantine",
        scan_roots=[fake_root],
        current_version=90,
        current_path=current90,
        output_root=out_root,
        confirm="MOVE_OLD_KAKAO_VERSIONS",
        yes=True,
    )
    quarantine_moved = quarantine.get("summary", {}).get("acted") == 4 and not old66.exists() and not old80.exists() and not old88.exists() and not old89.exists() and current90.exists()

    # Recreate one old folder to test delete backup behavior.
    old83 = fake_root / "kakao_emoticon_profit_system_v83_delete_test"
    (old83 / "outputs" / "final").mkdir(parents=True, exist_ok=True)
    (old83 / "outputs" / "final" / "old_output.csv").write_text("phrase\n진짜?", encoding="utf-8")
    delete_report = cleanup_run(
        mode="delete",
        scan_roots=[fake_root],
        current_version=90,
        current_path=current90,
        output_root=out_root,
        confirm="DELETE_OLD_KAKAO_VERSIONS",
        yes=True,
    )
    delete_removed = not old83.exists()
    backup_root = Path(delete_report.get("backup_root", ""))
    backup_created = backup_root.exists() and any(backup_root.rglob("old_output.csv"))

    return {
        "preview_detected_four_old_versions_including_v89": preview_detected,
        "current_v90_excluded": current_excluded,
        "quarantine_moved_old_versions_only": quarantine_moved,
        "delete_preserves_user_data_then_removes_old_folder": delete_removed and backup_created,
        "preview_report_path": preview.get("report_path"),
        "quarantine_report_path": quarantine.get("report_path"),
        "delete_report_path": delete_report.get("report_path"),
    }


def main() -> int:
    root = ROOT
    out = root / "outputs" / "v90_simple_png_gif_output_check"
    out.mkdir(parents=True, exist_ok=True)

    eng = V70SetCompletenessEngine()
    # Patch the instance only for the test run. The real program keeps its normal phrase set.
    static = list(SPECIAL_STATIC)
    for phrase, emotion, motion in eng.CORE_STATIC_SET:
        if len(static) >= 32:
            break
        if phrase not in {x[0] for x in static}:
            static.append((phrase, emotion, motion))
    animated = []
    for idx, (phrase, emotion, motion) in enumerate(static[:24], start=1):
        animated.append((phrase, emotion, motion, idx in {1, 2, 3, 8, 16}))
    eng.CORE_STATIC_SET = static[:32]
    eng.CORE_ANIMATED_SET = animated[:24]

    report = eng.build_bundle(
        project_name="v90_초보자_전체흐름_파일명안전_점검",
        concept_text="정지형 PNG 32개, 움직이는 GIF 24개, JPG 확인용 미리보기 분리 출력 흐름 점검",
        selected_style="손그림 공감형 · 굵은 외곽선 · 미니 리액션형",
        selected_rules=["정지형 최종 파일은 PNG", "움직이는형 최종 파일은 GIF", "JPG는 확인용 미리보기만 사용", "5개 큰 메뉴 유지"],
        main_phrase="진짜?",
        user_feedback="초보자는 큰 단계만 누르고 내부 하위 기능은 자동 처리되기를 원한다.",
        online_abstract_notes="짧은 답장형, 하찮은 공감형, 포즈 다양성, 모션 리듬만 추상 신호로 반영",
        out_dir=out,
    )
    run_dir = Path(report.output_dir)

    all_files = [p for p in run_dir.rglob("*") if p.is_file()]
    invalid_runtime_files = [str(p.relative_to(run_dir)) for p in all_files if has_invalid_windows_name(p.name)]
    static_files = sorted((run_dir / "static_32_png").glob("*.png"))
    animated_files = sorted((run_dir / "animated_24_gif").glob("*"))
    gif_files = sorted((run_dir / "animated_24_gif").glob("*.gif"))
    static_submit_files = sorted(Path(report.v90_static_png_submit_dir).glob("*.png"))
    animated_submit_files = sorted(Path(report.v90_animated_gif_submit_dir).glob("*.gif"))
    preview_jpg_files = sorted(Path(report.v90_preview_jpg_dir).glob("*.jpg"))
    simple_manifest = read_json(Path(report.v90_manifest_json))
    simple_manifest_csv_rows = read_csv_rows(Path(report.v90_manifest_csv))

    static_rows = read_json(Path(report.static_32_plan_json))
    animated_rows = read_json(Path(report.animated_24_plan_json))
    static_phrases = [r.get("phrase", "") for r in static_rows]
    phrase_preservation_missing = [p for p, _, _ in SPECIAL_STATIC[:12] if p not in static_phrases]

    zip_invalid = {
        "static_32_package_zip": check_zip_names(Path(report.static_32_package_zip)),
        "animated_24_package_zip": check_zip_names(Path(report.animated_24_package_zip)),
        "candidate_submission_zip": check_zip_names(Path(report.candidate_submission_zip)),
        "v90_submit_only_png_gif_zip": check_zip_names(Path(report.v90_submit_only_png_gif_zip)),
        "v90_simple_output_package_zip": check_zip_names(Path(report.v90_simple_output_package_zip)),
    }
    with zipfile.ZipFile(report.v90_submit_only_png_gif_zip) as zf:
        submit_only_zip_entries = zf.namelist()
    submit_only_jpg_entries = [
        name for name in submit_only_zip_entries
        if Path(name).suffix.lower() in {".jpg", ".jpeg"}
    ]

    root_bats = sorted(p.name for p in root.glob("*.bat"))
    app_text = (root / "app.py").read_text(encoding="utf-8", errors="ignore")
    compact_menu_count = app_text.count('"label": "') if "COMPACT_WORKFLOWS" in app_text else 0
    compact_labels_present = all(label in app_text for label in [
        "1 제작 시작 · 정지형/움직이는형 미리보기",
        "2 세트 구성 · 32개/24개 품질 진화",
        "3 검사 · 자동보정 · 제출 전 승인",
        "4 반려 대응 · 캡처/OCR · 재생성",
        "5 최종 납품 · 백업/리포트/재검사",
        "고급 세부 메뉴 보기",
    ])

    cleanup_flow = run_cleanup_fake_flow_test(root)

    checks = {
        "runtime_windows_filename_safe": not invalid_runtime_files,
        "zip_internal_windows_filename_safe": all(not v for v in zip_invalid.values()),
        "static_32_generated": len(static_files) == 32,
        "animated_24_gif_generated": len(animated_files) == 24 and len(gif_files) == 24,
        "v90_static_png_submit_32": len(static_submit_files) == 32,
        "v90_animated_gif_submit_24": len(animated_submit_files) == 24,
        "v90_preview_jpg_56_created": len(preview_jpg_files) == 56,
        "v90_submit_only_zip_has_no_jpg": not submit_only_jpg_entries,
        "v90_manifest_counts_match": (
            simple_manifest.get("static_png_submit_count") == 32
            and simple_manifest.get("animated_gif_submit_count") == 24
            and simple_manifest.get("preview_jpg_count") == 56
            and len(simple_manifest.get("items", [])) == 56
            and len(simple_manifest_csv_rows) == 56
        ),
        "special_phrases_preserved_in_json": not phrase_preservation_missing,
        "candidate_submission_zip_exists": Path(report.candidate_submission_zip).exists(),
        "candidate_submission_zip_integrity": zipfile.ZipFile(report.candidate_submission_zip).testzip() is None,
        "root_bat_count_beginner_safe": len(root_bats) <= ROOT_BAT_LIMIT,
        "compact_5_menu_labels_present": compact_labels_present,
        "api_key_literal_absent": not scan_api_key_literals(root),
        "cleanup_preview_detects_old_versions_including_v89": cleanup_flow.get("preview_detected_four_old_versions_including_v89", False),
        "cleanup_excludes_current_v90": cleanup_flow.get("current_v90_excluded", False),
        "cleanup_quarantine_moves_old_versions_only": cleanup_flow.get("quarantine_moved_old_versions_only", False),
        "cleanup_delete_backs_up_user_data": cleanup_flow.get("delete_preserves_user_data_then_removes_old_folder", False),
    }
    api_hits = scan_api_key_literals(root)
    checks["api_key_literal_absent"] = not api_hits
    status = "PASS" if all(checks.values()) else "FAIL"

    summary = {
        "status": status,
        "version": "90.0.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "output_dir": str(run_dir),
        "checks": checks,
        "counts": {
            "root_bat_count": len(root_bats),
            "static_png_count": len(static_files),
            "animated_gif_count": len(gif_files),
            "v90_static_png_submit_count": len(static_submit_files),
            "v90_animated_gif_submit_count": len(animated_submit_files),
            "v90_preview_jpg_count": len(preview_jpg_files),
            "v90_manifest_csv_row_count": len(simple_manifest_csv_rows),
            "runtime_file_count": len(all_files),
        },
        "root_bats": root_bats,
        "invalid_runtime_files": invalid_runtime_files,
        "invalid_zip_entries": zip_invalid,
        "submit_only_jpg_entries": submit_only_jpg_entries,
        "phrase_preservation_missing": phrase_preservation_missing,
        "api_key_literal_hits": api_hits,
        "cleanup_fake_flow_test": cleanup_flow,
        "candidate_submission_zip": report.candidate_submission_zip,
        "candidate_submission_zip_sha256": sha256_file(Path(report.candidate_submission_zip)),
        "v90_submit_only_png_gif_zip": report.v90_submit_only_png_gif_zip,
        "v90_submit_only_png_gif_zip_sha256": sha256_file(Path(report.v90_submit_only_png_gif_zip)),
        "v90_simple_output_package_zip": report.v90_simple_output_package_zip,
        "v90_simple_output_package_zip_sha256": sha256_file(Path(report.v90_simple_output_package_zip)),
    }

    report_path = root / "v90_simple_png_gif_output_check_report.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
