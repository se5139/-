
from __future__ import annotations
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def fail(msg: str):
    print("[FAIL]", msg)
    raise SystemExit(1)

def ok(msg: str):
    print("[PASS]", msg)

def main():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    constants = (ROOT / "modules" / "constants.py").read_text(encoding="utf-8")
    if 'APP_VERSION = "67.0.0"' not in constants:
        fail("APP_VERSION is not 67.0.0")
    ok("version constant")

    required_markers = [
        "VideoReferenceQualityEngine",
        "54 실제 제작 품질 개선/영상 기준 반영",
        "v67_quality_direction_report",
        "GIF가 화면에서 바로 움직이게 표시",
        "선택한 제안은 정지형 재생성/GIF 모션/24개·32개 구성에 실제 반영됩니다.",
    ]
    for marker in required_markers:
        if marker not in app:
            fail(f"missing app marker: {marker}")
    ok("app routing markers")

    forbidden_visible = [
        "'54 코딩 프로그램/툴체인 관리'",
        "'55 전문 IDE/코딩 프로그램 적용 기준'",
        "'56 멀티툴 개발 실행/검증 파이프라인'",
    ]
    for marker in forbidden_visible:
        if marker in app:
            fail(f"old coding-tool menu still visible in PAGE_LABELS: {marker}")
    ok("old coding tool menus hidden")

    from modules.video_reference_quality_engine import VideoReferenceQualityEngine
    engine = VideoReferenceQualityEngine()
    with tempfile.TemporaryDirectory() as td:
        report = engine.build_bundle(
            project_name="v67_check",
            concept_text="하찮고 공감되는 손그림 답장 캐릭터",
            selected_style="영상 참고형 · 손그림 하찮은 공감",
            selected_suggestions=[
                "작은 썸네일에서도 보이는 굵은 외곽선",
                "캐릭터보다 문구가 먼저 읽히는 짧은 말풍선",
                "정지형 identity를 움직이는형에서도 고정",
                "GIF가 화면에서 바로 움직이게 표시",
                "3개 이상 모션 후보를 동시에 비교",
                "기존 인기 캐릭터 복제 금지",
            ],
            main_phrase="넵",
            video_notes="작은 썸네일, 짧은 문구, 손그림 스타일, GIF 실제 미리보기",
            online_notes="미니 리액션, 다크모드 대비, 짧은 답장",
            out_dir=Path(td),
        )
        data = report.to_dict()
        must_exist = [
            data["static_png"],
            data["animated_preview_gif"],
            data["contact_sheet_png"],
            data["static_32_plan_json"],
            data["animated_24_plan_json"],
            data["html_report_path"],
            data["prompt_pack_path"],
            data["manifest_path"],
            data["package_zip_path"],
        ]
        for p in must_exist:
            if not Path(p).exists():
                fail(f"missing output: {p}")
        if len(data["motion_variants"]) < 6:
            fail("motion variants fewer than 6")
        if len(json.loads(Path(data["static_32_plan_json"]).read_text(encoding="utf-8"))) != 32:
            fail("static 32 plan count mismatch")
        if len(json.loads(Path(data["animated_24_plan_json"]).read_text(encoding="utf-8"))) != 24:
            fail("animated 24 plan count mismatch")
        if data["quality_scores"].get("gif_visible", 0) < 90:
            fail("gif visible score too low")
        ok("engine smoke outputs")

    # API key leakage marker check
    leak_patterns = ["sk-proj-", "OPENAI_API_KEY="]
    for base, _, files in os.walk(ROOT):
        # ignore .venv if present
        if ".venv" in Path(base).parts:
            continue
        for fn in files:
            p = Path(base) / fn
            if p.suffix.lower() in {".pyc", ".png", ".gif", ".jpg", ".jpeg", ".webp", ".zip"}:
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "openai-api-key.txt" in str(p):
                fail("openai-api-key.txt should not be packaged")
            import re
            if re.search(r"sk-proj-[A-Za-z0-9_\\-]{30,}", txt):
                fail(f"possible OpenAI key leaked in {p}")
    ok("api key leakage check")

    print("[PASS] v67 video quality direction check completed")

if __name__ == "__main__":
    main()
