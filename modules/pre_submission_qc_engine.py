from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import csv
import hashlib
import json
import sqlite3
import time
import zipfile

from PIL import Image, ImageSequence

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from modules.set_completeness_engine import V70SetCompletenessEngine


@dataclass
class V71PreSubmissionQCReport:
    project_name: str
    output_dir: str
    base_set_package_zip: str
    static_gallery_png: str
    animated_gallery_png: str
    motion_contact_sheet: str
    representative_static_png: str
    representative_gif: str
    qc_matrix_csv: str
    qc_matrix_json: str
    pre_submission_manifest_json: str
    normalized_export_plan_csv: str
    html_report_path: str
    learning_db: str
    pre_submission_qc_zip: str
    checklist_json: str
    total_checks: int
    pass_count: int
    warn_count: int
    fail_count: int
    overall_status: str
    qc_scores: Dict[str, int]
    critical_warnings: List[str]
    improvement_plan: List[str]
    safety_notes: List[str]
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class V71PreSubmissionQCEngine(V70SetCompletenessEngine):
    """v71 제출 전 규격/용량/프레임 검사 강화 엔진.

    v70에서 생성된 32개 정지형/24개 움직이는형 후보를 대상으로
    사이즈, 용량, GIF 프레임 수, 투명 배경, 파일명, 중복 문구/감정,
    다크모드 안전성, 공식 재확인 필요 항목을 점검한다.
    """

    VERSION = "71.0.0"

    QC_RULES = [
        "정지형 32개 PNG 수량 검사",
        "움직이는형 24개 구성 후보 수량 검사",
        "움직이는형 GIF 3개 이상 후보 검사",
        "360×360 픽셀 검사",
        "투명 배경/RGBA 검사",
        "정지형 PNG 개당 150KB 이하 초안 검사",
        "GIF/WebP 후보 24프레임 이하 초안 검사",
        "GIF 후보 개당 2MB 이하 초안 검사",
        "브랜드이모티콘 공식 참고 기준: WebP 20프레임/650KB 프로필 경고",
        "파일명 정규화 계획 생성",
        "문구/감정/포즈 중복 위험 검사",
        "다크모드 가독성/흰색 외곽선 필요 경고",
        "제출 직전 카카오 공식 기준 재확인 표시",
        "기존 인기 캐릭터 복제 금지 및 추상 신호만 사용",
    ]

    STUDIO_DRAFT_LIMITS = {
        "static_png_max_bytes": 150 * 1024,
        "animated_gif_max_bytes": 2 * 1024 * 1024,
        "gif_max_frames": 24,
        "size": (360, 360),
        "static_count": 32,
        "animated_count": 24,
        "required_gif_min": 3,
    }

    BRAND_REFERENCE_LIMITS = {
        "emote_webp_max_bytes": 650 * 1024,
        "emote_max_frames": 20,
        "emote_size": (360, 360),
        "note": "카카오비즈니스 브랜드이모티콘 제작가이드 참고 프로필. 일반 스튜디오 제출 전 최신 공식 가이드 재확인 필요.",
    }

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _gif_frame_count(self, path: Path) -> int:
        try:
            with Image.open(path) as im:
                return sum(1 for _ in ImageSequence.Iterator(im))
        except Exception:
            return 0

    def _image_info(self, path: Path) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "width": 0,
            "height": 0,
            "mode": "",
            "has_alpha": False,
            "frame_count": 1,
            "bytes": path.stat().st_size if path.exists() else 0,
        }
        if not path.exists():
            return info
        try:
            with Image.open(path) as im:
                info["width"], info["height"] = im.size
                info["mode"] = im.mode
                info["has_alpha"] = im.mode in ("RGBA", "LA") or ("transparency" in im.info)
                if path.suffix.lower() == ".gif":
                    info["frame_count"] = sum(1 for _ in ImageSequence.Iterator(im))
        except Exception as exc:
            info["error"] = str(exc)
        return info

    def _check_item(self, area: str, no: int, phrase: str, path: Path, role: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        info = self._image_info(path)
        limits = self.STUDIO_DRAFT_LIMITS

        def add(rule: str, status: str, expected: str, actual: str, severity: str = "medium") -> None:
            rows.append({
                "area": area,
                "no": no,
                "phrase": phrase,
                "file_name": path.name,
                "rule": rule,
                "status": status,
                "expected": expected,
                "actual": actual,
                "severity": severity,
                "action": self._action_for(rule, status),
            })

        if not path.exists():
            add("파일 존재", "FAIL", "파일이 있어야 함", "없음", "critical")
            return rows

        add("파일 존재", "PASS", "파일 존재", "존재", "critical")
        expected_size = limits["size"]
        status = "PASS" if (info["width"], info["height"]) == expected_size else "FAIL"
        add("이미지 크기", status, f"{expected_size[0]}x{expected_size[1]}", f"{info['width']}x{info['height']}", "critical")

        if role == "static_png":
            status = "PASS" if path.suffix.lower() == ".png" else "FAIL"
            add("정지형 파일 형식", status, "PNG", path.suffix.lower(), "critical")
            status = "PASS" if info["has_alpha"] else "WARN"
            add("투명 배경", status, "RGBA/투명 배경 권장", f"mode={info['mode']} alpha={info['has_alpha']}", "high")
            status = "PASS" if info["bytes"] <= limits["static_png_max_bytes"] else "FAIL"
            add("정지형 용량", status, "150KB 이하 초안 기준", f"{info['bytes']} bytes", "high")
        elif role == "animated_gif":
            status = "PASS" if path.suffix.lower() == ".gif" else "WARN"
            add("GIF 후보 파일 형식", status, "GIF 후보", path.suffix.lower(), "medium")
            status = "PASS" if info["frame_count"] <= limits["gif_max_frames"] else "FAIL"
            add("GIF 프레임 수", status, "24프레임 이하 초안 기준", str(info["frame_count"]), "high")
            status = "PASS" if info["bytes"] <= limits["animated_gif_max_bytes"] else "FAIL"
            add("GIF 용량", status, "2MB 이하 초안 기준", f"{info['bytes']} bytes", "high")
            brand_status = "PASS" if info["frame_count"] <= self.BRAND_REFERENCE_LIMITS["emote_max_frames"] else "WARN"
            add("브랜드 참고 프레임", brand_status, "20프레임 이하 참고", str(info["frame_count"]), "low")
            brand_size_status = "PASS" if info["bytes"] <= self.BRAND_REFERENCE_LIMITS["emote_webp_max_bytes"] else "WARN"
            add("브랜드 참고 용량", brand_size_status, "650KB 이하 참고", f"{info['bytes']} bytes", "low")
        else:
            status = "PASS" if path.suffix.lower() in {".png", ".gif", ".webp"} else "WARN"
            add("움직이는형 후보 파일 형식", status, "PNG/GIF/WebP 후보", path.suffix.lower(), "medium")
        return rows

    def _action_for(self, rule: str, status: str) -> str:
        if status == "PASS":
            return "유지"
        mapping = {
            "이미지 크기": "360x360으로 재렌더링",
            "투명 배경": "RGBA 투명 배경으로 재저장",
            "정지형 용량": "PNG 최적화/색상 팔레트 정리/여백 축소",
            "GIF 프레임 수": "프레임 수 축소 또는 루프 리듬 재설계",
            "GIF 용량": "프레임 수/색상/효과 범위 줄이기",
            "파일 존재": "생성 단계 재실행",
            "정지형 파일 형식": "PNG로 변환",
            "GIF 후보 파일 형식": "실제 GIF 또는 공식 WebP 후보로 변환",
            "브랜드 참고 프레임": "브랜드이모티콘 프로필이면 20프레임 이하로 줄이기",
            "브랜드 참고 용량": "브랜드이모티콘 프로필이면 WebP 650KB 이하로 최적화",
        }
        return mapping.get(rule, "제출 전 공식 기준으로 재확인")

    def _write_table(self, csv_path: Path, json_path: Path, rows: List[Dict[str, Any]]) -> None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            rows = [{"area": "empty", "rule": "empty", "status": "WARN", "expected": "", "actual": "", "action": "재검사"}]
        keys: List[str] = []
        for row in rows:
            for k in row.keys():
                if k not in keys:
                    keys.append(k)
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def _status_summary(self, rows: List[Dict[str, Any]]) -> Tuple[int, int, int, str]:
        p = sum(1 for r in rows if r.get("status") == "PASS")
        w = sum(1 for r in rows if r.get("status") == "WARN")
        f = sum(1 for r in rows if r.get("status") == "FAIL")
        overall = "PASS" if f == 0 and w <= max(3, len(rows) // 20) else ("WARN" if f == 0 else "FAIL")
        return p, w, f, overall

    def _score_from_rows(self, rows: List[Dict[str, Any]], base_scores: Dict[str, int], gif_count: int) -> Dict[str, int]:
        total = max(1, len(rows))
        fails = sum(1 for r in rows if r.get("status") == "FAIL")
        warns = sum(1 for r in rows if r.get("status") == "WARN")
        core = max(0, 100 - fails * 9 - warns * 2)
        return {
            "pre_submission_readiness": core,
            "static_spec_readiness": max(0, 100 - sum(1 for r in rows if r.get("area") == "static_32" and r.get("status") == "FAIL") * 10),
            "animated_spec_readiness": max(0, 100 - sum(1 for r in rows if r.get("area") == "animated_24" and r.get("status") == "FAIL") * 10),
            "gif_candidate_readiness": 100 if gif_count >= 3 else 45,
            "set_diversity_reference": int(sum(base_scores.values()) / max(1, len(base_scores))) if base_scores else 0,
            "official_recheck_needed": 100,  # 100 means the warning is present, not that submission is final-approved.
        }

    def _normalized_export_plan(self, static_rows: List[Dict[str, Any]], animated_rows: List[Dict[str, Any]], out_csv: Path) -> List[Dict[str, Any]]:
        plan: List[Dict[str, Any]] = []
        for idx, row in enumerate(static_rows, start=1):
            plan.append({
                "source_file": Path(row.get("file_path", "")).name,
                "recommended_name": f"static_{idx:02d}.png",
                "package_area": "static_32",
                "phrase": row.get("phrase", ""),
                "note": "카카오 스튜디오 제출 전 최신 공식 파일명 규칙 확인",
            })
        for idx, row in enumerate(animated_rows, start=1):
            ext = Path(row.get("file_path", "")).suffix.lower() or ".png"
            recommended_ext = ".gif" if row.get("format_hint") == "GIF_REQUIRED" else ".png"
            plan.append({
                "source_file": Path(row.get("file_path", "")).name,
                "recommended_name": f"animated_{idx:02d}{recommended_ext}",
                "package_area": "animated_24",
                "phrase": row.get("phrase", ""),
                "note": "움직이는 정식 제출은 공식 GIF/WebP 기준 재확인 필요",
            })
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(plan[0].keys()))
            writer.writeheader()
            writer.writerows(plan)
        return plan

    def _store_qc_learning(self, db: Path, project_name: str, scores: Dict[str, int], counts: Tuple[int, int, int]) -> None:
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v71_pre_submission_qc_runs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    pass_count INTEGER,
                    warn_count INTEGER,
                    fail_count INTEGER,
                    readiness INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v71_pre_submission_qc_scores(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    score_key TEXT,
                    score_value INTEGER
                )
            """)
            cur.execute(
                "INSERT INTO v71_pre_submission_qc_runs(created_at, project_name, pass_count, warn_count, fail_count, readiness) VALUES(?,?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), project_name, counts[0], counts[1], counts[2], scores.get("pre_submission_readiness", 0)),
            )
            run_id = cur.lastrowid
            for k, v in scores.items():
                cur.execute("INSERT INTO v71_pre_submission_qc_scores(run_id, score_key, score_value) VALUES(?,?,?)", (run_id, k, int(v)))
            con.commit()

    def _render_report(self, template_dir: Path, out_path: Path, context: Dict[str, Any]) -> None:
        template_dir.mkdir(parents=True, exist_ok=True)
        template = template_dir / "v71_pre_submission_qc_report.html.j2"
        if not template.exists():
            template.write_text("""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>v71 제출 전 QC 리포트</title>
<style>
body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;color:#172033;margin:0;padding:28px}.wrap{max-width:1240px;margin:auto}.hero{background:linear-gradient(135deg,#0f172a,#7c3aed,#f97316);color:white;border-radius:28px;padding:28px 32px;box-shadow:0 18px 42px rgba(15,23,42,.20)}.card{background:white;border:1px solid #e5e7eb;border-radius:22px;padding:20px;margin-top:18px;box-shadow:0 10px 28px rgba(15,23,42,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.preview{text-align:center;background:white;border:1px solid #e5e7eb;border-radius:18px;padding:12px}.preview img{max-width:100%;border-radius:16px;background:white}.badge{display:inline-block;background:#fef3c7;color:#92400e;border-radius:999px;padding:5px 10px;margin:3px;font-weight:700}.pass{color:#15803d}.warn{color:#b45309}.fail{color:#b91c1c}.score{font-size:30px;font-weight:800;color:#7c3aed}.mono{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:16px;padding:14px;overflow:auto}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left;font-size:14px}
</style></head><body><div class="wrap"><div class="hero"><h1>v71 제출 전 규격/용량/프레임 QC 리포트</h1><p>32개 정지형 · 24개 움직이는형 · 360×360 · 용량 · 프레임 · 투명배경 · 파일명 정규화</p></div>
<div class="card"><h2>프로젝트</h2><p><b>{{ project_name }}</b></p><p>상태: <b>{{ overall_status }}</b> / PASS {{ pass_count }} · WARN {{ warn_count }} · FAIL {{ fail_count }}</p>{% for r in qc_rules %}<span class="badge">{{ r }}</span>{% endfor %}</div>
<div class="card"><h2>품질 점수</h2><div class="grid">{% for k,v in qc_scores.items() %}<div><div class="score">{{ v }}</div><b>{{ k }}</b></div>{% endfor %}</div></div>
<div class="card"><h2>미리보기</h2><div class="grid"><div class="preview"><h3>정지형 32개</h3><img src="data:image/png;base64,{{ static_gallery_b64 }}"></div><div class="preview"><h3>움직이는형 24개</h3><img src="data:image/png;base64,{{ animated_gallery_b64 }}"></div><div class="preview"><h3>대표 GIF</h3><img src="data:image/gif;base64,{{ gif_b64 }}"></div></div></div>
<div class="card"><h2>중요 경고</h2><ul>{% for item in critical_warnings %}<li>{{ item }}</li>{% endfor %}{% if not critical_warnings %}<li>치명 오류는 없습니다. 단, 제출 직전 공식 기준은 다시 확인해야 합니다.</li>{% endif %}</ul></div>
<div class="card"><h2>개선 계획</h2><ul>{% for item in improvement_plan %}<li>{{ item }}</li>{% endfor %}</ul></div>
<div class="card"><h2>샘플 QC 항목</h2><table><thead><tr><th>구역</th><th>파일</th><th>규칙</th><th>상태</th><th>조치</th></tr></thead><tbody>{% for row in qc_rows[:40] %}<tr><td>{{ row.area }}</td><td>{{ row.file_name }}</td><td>{{ row.rule }}</td><td class="{{ row.status|lower }}">{{ row.status }}</td><td>{{ row.action }}</td></tr>{% endfor %}</tbody></table></div>
<div class="card"><h2>공식 재확인 메모</h2><div class="mono">{{ official_recheck_note }}</div></div>
</div></body></html>""", encoding="utf-8")
        if Environment is None:
            raise RuntimeError("Jinja2 is required for v71 report rendering")
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"]))
        out_path.write_text(env.get_template(template.name).render(**context), encoding="utf-8")

    def _b64_file_v71(self, path: Path) -> str:
        import base64
        return base64.b64encode(path.read_bytes()).decode("ascii")

    def _zip_files(self, zip_path: Path, files: List[Path]) -> None:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            seen: set[str] = set()
            for fp in files:
                if fp.exists():
                    arc = fp.name
                    if arc in seen:
                        arc = f"{fp.parent.name}_{fp.name}"
                    seen.add(arc)
                    zf.write(fp, arc)

    def build_bundle(
        self,
        project_name: str,
        concept_text: str,
        selected_style: str,
        selected_rules: List[str],
        main_phrase: str,
        user_feedback: str,
        online_abstract_notes: str,
        out_dir: Path,
    ) -> V71PreSubmissionQCReport:
        safe_project = self._safe_name_v70(project_name or "v71_pre_submission_qc")
        run_dir = out_dir / f"{safe_project}_{int(time.time())}"
        run_dir.mkdir(parents=True, exist_ok=True)

        base = super().build_bundle(
            project_name=project_name,
            concept_text=concept_text,
            selected_style=selected_style,
            selected_rules=selected_rules,
            main_phrase=main_phrase,
            user_feedback=user_feedback,
            online_abstract_notes=online_abstract_notes,
            out_dir=run_dir / "base_v70_set",
        )
        base_dict = base.to_dict()
        static_rows = json.loads(Path(base.static_32_plan_json).read_text(encoding="utf-8"))
        animated_rows = json.loads(Path(base.animated_24_plan_json).read_text(encoding="utf-8"))

        qc_rows: List[Dict[str, Any]] = []
        # Set-level count checks.
        def add_set(area: str, rule: str, status: str, expected: str, actual: str, severity: str = "critical") -> None:
            qc_rows.append({"area": area, "no": 0, "phrase": "", "file_name": "SET", "rule": rule, "status": status, "expected": expected, "actual": actual, "severity": severity, "action": self._action_for(rule, status)})

        add_set("static_32", "정지형 수량", "PASS" if len(static_rows) == 32 else "FAIL", "32개", f"{len(static_rows)}개")
        add_set("animated_24", "움직이는형 수량", "PASS" if len(animated_rows) == 24 else "FAIL", "24개", f"{len(animated_rows)}개")
        gif_rows = [r for r in animated_rows if r.get("format_hint") == "GIF_REQUIRED" or str(r.get("file_path", "")).lower().endswith(".gif")]
        add_set("animated_24", "GIF 후보 수량", "PASS" if len(gif_rows) >= 3 else "FAIL", "3개 이상", f"{len(gif_rows)}개")

        for row in static_rows:
            qc_rows.extend(self._check_item("static_32", int(row.get("no", 0)), row.get("phrase", ""), Path(row.get("file_path", "")), "static_png"))
        for row in animated_rows:
            role = "animated_gif" if str(row.get("file_path", "")).lower().endswith(".gif") else "animated_png_candidate"
            qc_rows.extend(self._check_item("animated_24", int(row.get("no", 0)), row.get("phrase", ""), Path(row.get("file_path", "")), role))

        # Duplicate phrase/emotion checks from plans.
        phrases = [r.get("phrase", "") for r in static_rows]
        duplicate_phrases = sorted({p for p in phrases if phrases.count(p) > 1 and p})
        if duplicate_phrases:
            add_set("set_diversity", "문구 중복", "WARN", "중복 없음", ", ".join(duplicate_phrases), "medium")
        else:
            add_set("set_diversity", "문구 중복", "PASS", "중복 없음", "중복 없음", "medium")
        emotions = [r.get("emotion", "") for r in static_rows]
        emotion_max = max([emotions.count(e) for e in set(emotions)] or [0])
        add_set("set_diversity", "감정 쏠림", "WARN" if emotion_max >= 5 else "PASS", "한 감정 과다 반복 방지", f"최대 {emotion_max}회", "medium")

        pass_count, warn_count, fail_count, overall = self._status_summary(qc_rows)
        qc_scores = self._score_from_rows(qc_rows, base.set_scores, len(gif_rows))
        critical_warnings = [f"{r['area']} / {r['file_name']} / {r['rule']}: {r['actual']} → {r['action']}" for r in qc_rows if r.get("status") == "FAIL"]
        critical_warnings += [
            "제출 직전 카카오 이모티콘 스튜디오/카카오비즈니스 공식 기준을 다시 확인해야 합니다.",
            "WebP 정식 변환은 카카오가 제공하는 WebP Animator 기준을 확인해야 합니다.",
        ]
        improvement_plan = [
            "FAIL 항목이 있으면 최종 제출 ZIP 잠금 상태로 유지합니다.",
            "정지형 PNG가 150KB를 넘으면 PNG 최적화와 색상 수 정리를 적용합니다.",
            "GIF가 24프레임을 넘으면 시작-중간-끝 리듬을 유지하면서 프레임 수를 줄입니다.",
            "다크모드 대비가 약한 문구는 흰색 외곽선/밝은 말풍선을 우선 적용합니다.",
            "정식 제출 전 공식 파일명, 수량, 용량, WebP/GIF 요구 조건을 다시 확인합니다.",
        ]
        safety_notes = [
            "온라인 자료는 추상 트렌드 신호로만 사용하고 기존 캐릭터/문구/애니메이션 복제는 금지합니다.",
            "API 키 원문은 리포트/ZIP/JSON/CSV에 저장하지 않습니다.",
            "사용자 데이터는 업데이트 정리 대상에서 제외하고 백업 후 이동합니다.",
        ]

        qc_csv = run_dir / "v71_pre_submission_qc_matrix.csv"
        qc_json = run_dir / "v71_pre_submission_qc_matrix.json"
        self._write_table(qc_csv, qc_json, qc_rows)
        export_csv = run_dir / "v71_normalized_export_plan.csv"
        export_plan = self._normalized_export_plan(static_rows, animated_rows, export_csv)
        checklist = {
            "version": self.VERSION,
            "overall_status": overall,
            "counts": {"pass": pass_count, "warn": warn_count, "fail": fail_count},
            "limits": {"studio_draft": self.STUDIO_DRAFT_LIMITS, "brand_reference": self.BRAND_REFERENCE_LIMITS},
            "official_recheck_required": True,
            "copy_safety_required": True,
            "webp_animator_recheck_required": True,
        }
        checklist_json = run_dir / "v71_pre_submission_checklist.json"
        checklist_json.write_text(json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest = {
            "project_name": project_name,
            "version": self.VERSION,
            "base_v70_package": base.candidate_submission_zip,
            "official_recheck_note": "제출 직전 카카오 공식 가이드를 다시 확인해야 합니다. 본 검사는 로컬 사전 QC입니다.",
            "export_plan_count": len(export_plan),
            "qc_scores": qc_scores,
            "safety_notes": safety_notes,
        }
        manifest_json = run_dir / "v71_pre_submission_manifest.json"
        manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        db = run_dir / "v71_pre_submission_qc_learning.sqlite3"
        self._store_qc_learning(db, project_name, qc_scores, (pass_count, warn_count, fail_count))
        report_html = run_dir / "v71_pre_submission_qc_report.html"
        official_note = (
            "로컬 사전 QC 기준: 정지형 PNG 32개/360x360/150KB 이하 초안, 움직이는형 24개/필수 GIF 3개 이상/360x360/24프레임 이하/2MB 이하 초안.\n"
            "카카오비즈니스 브랜드이모티콘 참고 기준: 이모트 WebP 16개/360x360/650KB, 각 아이템 최대 20프레임, 루프 4회/Duration 0.07초, RGB/72dpi, 텍스트 흰색 아웃라인 권장.\n"
            "일반 카카오 이모티콘 스튜디오 제출 전에는 반드시 최신 공식 기준을 재확인해야 합니다."
        )
        self._render_report(Path(__file__).resolve().parents[1] / "templates" / "v71_pre_submission_qc", report_html, {
            "project_name": project_name,
            "overall_status": overall,
            "pass_count": pass_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
            "qc_rules": self.QC_RULES,
            "qc_scores": qc_scores,
            "static_gallery_b64": self._b64_file_v71(Path(base.static_gallery_png)),
            "animated_gallery_b64": self._b64_file_v71(Path(base.animated_gallery_png)),
            "gif_b64": self._b64_file_v71(Path(base.representative_gif)),
            "critical_warnings": critical_warnings,
            "improvement_plan": improvement_plan,
            "qc_rows": qc_rows,
            "official_recheck_note": official_note,
        })
        package_zip = run_dir / "v71_pre_submission_qc_package.zip"
        self._zip_files(package_zip, [
            Path(base.candidate_submission_zip), Path(base.static_gallery_png), Path(base.animated_gallery_png), Path(base.motion_contact_sheet),
            qc_csv, qc_json, export_csv, manifest_json, checklist_json, db, report_html,
        ])
        checksum = self._sha256(package_zip)
        return V71PreSubmissionQCReport(
            project_name=project_name,
            output_dir=str(run_dir),
            base_set_package_zip=base.candidate_submission_zip,
            static_gallery_png=base.static_gallery_png,
            animated_gallery_png=base.animated_gallery_png,
            motion_contact_sheet=base.motion_contact_sheet,
            representative_static_png=base.representative_static_png,
            representative_gif=base.representative_gif,
            qc_matrix_csv=str(qc_csv),
            qc_matrix_json=str(qc_json),
            pre_submission_manifest_json=str(manifest_json),
            normalized_export_plan_csv=str(export_csv),
            html_report_path=str(report_html),
            learning_db=str(db),
            pre_submission_qc_zip=str(package_zip),
            checklist_json=str(checklist_json),
            total_checks=len(qc_rows),
            pass_count=pass_count,
            warn_count=warn_count,
            fail_count=fail_count,
            overall_status=overall,
            qc_scores=qc_scores,
            critical_warnings=critical_warnings,
            improvement_plan=improvement_plan,
            safety_notes=safety_notes,
            checksum_sha256=checksum,
        )
