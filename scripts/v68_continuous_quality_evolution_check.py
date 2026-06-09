from __future__ import annotations
import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.continuous_quality_evolution import ContinuousQualityEvolutionEngine


def fail(msg: str):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)


def main():
    checks = []
    engine = ContinuousQualityEvolutionEngine()
    out_dir = ROOT / "outputs" / "v68_check_output"
    result = engine.build_bundle(
        project_name="v68_check",
        concept_text="작은 썸네일에서도 보이는 하찮은 손그림 공감형 캐릭터",
        selected_style="영상 참고형 · 손그림 하찮은 공감",
        selected_suggestions=[
            "작은 썸네일에서도 보이는 굵은 외곽선",
            "캐릭터보다 문구가 먼저 읽히는 짧은 말풍선",
            "정지형 identity를 움직이는형에서도 고정",
            "GIF가 화면에서 바로 움직이게 표시",
            "기존 인기 캐릭터 복제 금지",
        ],
        main_phrase="넵",
        youtube_notes="짧은 문구 공감 하찮 손그림 움직이는 GIF",
        kakao_notes="미니 리액션 작은 썸네일 다크모드 말풍선 24개 32개",
        user_feedback="초기 결과는 만족. 계속 진화하는 품질개선 필요.",
        local_uploaded_notes="정지형 identity 유지 및 모션 후보 비교",
        satisfaction_score=82,
        preferred_motion="통통 튐",
        out_dir=out_dir,
    )
    data = result.to_dict()
    required = [
        "static_png", "animated_preview_gif", "trend_signal_json", "quality_history_db",
        "quality_score_csv", "feedback_memory_json", "evolution_plan_json",
        "html_report_path", "prompt_template_path", "package_zip_path",
    ]
    for key in required:
        p = Path(data[key])
        if not p.exists():
            fail(f"missing output: {key} -> {p}")
        checks.append({"name": f"exists_{key}", "status": "PASS", "path": str(p)})
    if len(data.get("motion_variants", [])) < 3:
        fail("motion variants fewer than 3")
    checks.append({"name": "motion_variants_count", "status": "PASS", "count": len(data.get("motion_variants", []))})
    trend = json.loads(Path(data["trend_signal_json"]).read_text(encoding="utf-8"))
    if not trend.get("collection_mode", {}).get("paid_calls_blocked_by_default"):
        fail("paid call guard missing")
    if not trend.get("abstract_only_policy"):
        fail("abstract only policy missing")
    checks.append({"name": "abstract_trend_guardrails", "status": "PASS"})
    with zipfile.ZipFile(data["package_zip_path"]) as z:
        names = z.namelist()
        if not any(n.endswith("v68_quality_history.sqlite3") for n in names):
            fail("sqlite DB not packaged")
    checks.append({"name": "zip_contains_learning_db", "status": "PASS"})
    # API key raw string leak guard.
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".py", ".txt", ".md", ".json", ".csv", ".html", ".iss", ".bat"}:
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            import re
            if re.search(r"sk-proj-[A-Za-z0-9_\-]{30,}", txt):
                fail(f"possible API key leak in {p}")
            if re.search(r"OPENAI_API_KEY\s*=\s*sk-[A-Za-z0-9_\-]{20,}", txt):
                fail(f"possible API key env leak in {p}")
    checks.append({"name": "api_key_raw_leak_guard", "status": "PASS"})
    report = {"version": "68.0.0", "status": "PASS", "checks": checks, "sample_output": data}
    out = ROOT / "v68_continuous_quality_evolution_check_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[PASS] v68 continuous quality evolution check")
    print(str(out))


if __name__ == "__main__":
    main()
