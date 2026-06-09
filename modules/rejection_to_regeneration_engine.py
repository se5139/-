from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import csv
import hashlib
import json
import shutil
import sqlite3
import time
import zipfile

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from modules.capture_rejection_ingestion import V75CaptureRejectionIngestionEngine
from modules.set_completeness_engine import V70SetCompletenessEngine


@dataclass
class V76RejectionToRegenerationReport:
    project_name: str
    output_dir: str
    pipeline_status: str
    capture_v75_report_html: str
    capture_v75_work_package_zip: str
    connected_v74_action_plan_csv: str
    connected_v74_resubmission_zip: str
    regenerated_v70_html_report: str
    regenerated_static_32_gallery: str
    regenerated_animated_24_gallery: str
    regenerated_gif_contact_sheet: str
    regenerated_set_package_zip: str
    regeneration_action_plan_csv: str
    regeneration_prompt_md: str
    regeneration_manifest_json: str
    html_report_path: str
    work_package_zip: str
    learning_db: str
    detected_categories: List[str]
    applied_regeneration_rules: List[str]
    regenerated_static_count: int
    regenerated_animated_count: int
    regenerated_gif_count: int
    next_required_steps: List[str]
    safety_notes: List[str]
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class V76RejectionToRegenerationEngine:
    """v76 캡처/반려 사유 → 실제 재생성 자동 연결 엔진.

    v75는 캡처와 수동 교정 텍스트를 v74 액션 플랜으로 연결했다.
    v76은 그 액션 플랜을 실제 정지형 32개/움직이는형 24개 재생성으로 연결한다.

    안전 원칙:
    - 반려 사유와 온라인 정보는 추상 개선 신호로만 사용한다.
    - 기존 인기 캐릭터/문구/애니메이션을 복제하지 않는다.
    - 원본 산출물을 덮어쓰지 않고 regenerated_set 폴더에 새 결과를 만든다.
    - 재생성 후에는 v71 QC → v72 자동보정/잠금 → v73 사용자 승인 순서를 다시 타야 한다.
    """

    VERSION = "76.0.0"

    DEFAULT_REJECTION_TEXT = """캡처/반려 사유 기반 재생성 테스트입니다.
문구가 길어 작은 썸네일에서 가독성이 낮습니다.
일부 표정과 포즈가 반복적으로 보입니다.
움직임이 단순해서 GIF 후보를 더 분리해야 합니다.
캐릭터 고유성이 더 분명해야 합니다."""

    CATEGORY_RULE_MAP: Dict[str, List[str]] = {
        "character_identity": [
            "시그니처 실루엣 강화",
            "대표 표정 3종 고정",
            "캐릭터 고유 포즈 8개 이상 분산",
        ],
        "chat_usability": [
            "실제 답장형 문구 우선",
            "확인/감사/사과/퇴근/응원 상황 우선 배치",
            "말풍선 문구를 2~7자 중심으로 조정",
        ],
        "phrase_readability": [
            "짧은 문구 우선",
            "말풍선 대비 강화",
            "작은 썸네일 가독성 우선",
        ],
        "motion_quality": [
            "GIF 시작-중간-끝 리듬 분리",
            "통통 튐/꾸벅/손흔들기/말풍선 동기화 분리",
            "필수 GIF 3개 이상 모션 차별화",
        ],
        "spec_file_issue": [
            "360x360 투명 PNG 기준 유지",
            "프레임/용량 QC 재실행 준비",
            "파일명 정규화 대상 표시",
        ],
        "similarity_copyright": [
            "유사 위험 외형/문구/모션을 크게 변경",
            "기존 캐릭터 복제 금지",
            "추상 트렌드 신호만 사용",
        ],
        "set_repetition": [
            "감정/포즈/문구 중복 분산",
            "32개/24개 세트 다양성 강화",
            "비슷한 장면 연속 배치 방지",
        ],
        "finish_quality": [
            "외곽선 굵기 강화",
            "얼굴 크기 확대",
            "색 대비/말풍선 위치 보정",
        ],
        "ai_policy_origin": [
            "창작 원본/스케치/수정 이력 manifest 보존",
            "직접 창작 증거 폴더 유지",
            "AI 완성본 은폐 금지 안내",
        ],
    }

    def __init__(self) -> None:
        self.v75 = V75CaptureRejectionIngestionEngine()
        self.v70 = V70SetCompletenessEngine()

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _safe_name(self, name: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (name or "v76_rejection_to_regeneration"))
        return safe.strip("_") or "v76_rejection_to_regeneration"

    def _read_csv_rows(self, path: Path) -> List[Dict[str, str]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _write_csv(self, path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

    def _write_json(self, path: Path, obj: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def _zip_paths(self, zip_path: Path, paths: Iterable[Path], root: Path | None = None) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                if not p.exists():
                    continue
                if p.is_dir():
                    for child in p.rglob("*"):
                        if child.is_file():
                            arc = str(child.relative_to(root or p.parent))
                            zf.write(child, arc)
                else:
                    try:
                        arc = str(p.relative_to(root)) if root else p.name
                    except Exception:
                        arc = p.name
                    zf.write(p, arc)

    def _extract_categories(self, action_plan_csv: Path) -> List[str]:
        rows = self._read_csv_rows(action_plan_csv)
        categories = sorted({r.get("category", "").strip() for r in rows if r.get("category", "").strip()})
        if not categories:
            categories = ["phrase_readability", "motion_quality", "set_repetition", "finish_quality"]
        return categories

    def _rules_from_categories(self, categories: List[str], user_selected_rules: List[str] | None = None) -> List[str]:
        rules: List[str] = []
        for cat in categories:
            rules.extend(self.CATEGORY_RULE_MAP.get(cat, []))
        rules.extend(user_selected_rules or [])
        rules.extend([
            "정지형 identity를 움직이는형에서도 고정",
            "사용자가 선택한 반려 개선 제안을 실제 재생성에 반영",
            "온라인 자료는 추상 품질 신호만 사용",
            "기존 인기 캐릭터/문구/애니메이션 복제 금지",
            "재생성 후 v71 QC, v72 자동보정, v73 사용자 승인 재실행",
        ])
        # stable unique ordering
        return list(dict.fromkeys([r for r in rules if r]))

    def _build_regeneration_prompt(self, project_name: str, concept_text: str, categories: List[str], action_rows: List[Dict[str, str]], rules: List[str]) -> str:
        lines = [
            f"# v76 재생성 프롬프트 팩 - {project_name}",
            "",
            "## 목표",
            "반려/캡처 사유를 바탕으로 정지형 32개와 움직이는형 24개를 실제 재생성한다.",
            "원본/기존 인기 캐릭터를 복제하지 않고 추상 개선 신호만 적용한다.",
            "",
            "## 콘셉트",
            concept_text or "작은 썸네일에서도 읽히는 손그림 공감형 캐릭터",
            "",
            "## 감지 카테고리",
        ]
        lines.extend([f"- {c}" for c in categories])
        lines.append("")
        lines.append("## 적용 재생성 규칙")
        lines.extend([f"- {r}" for r in rules])
        lines.append("")
        lines.append("## 주요 액션 플랜")
        for row in action_rows[:12]:
            lines.append(f"- [{row.get('priority','')}] {row.get('category_label', row.get('category',''))}: {row.get('improvement_action','')}")
        return "\n".join(lines) + "\n"

    def _store_learning(self, db_path: Path, project_name: str, status: str, categories: List[str], rules: List[str], counts: Dict[str, int]) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v76_regeneration_runs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT,
                    project_name TEXT,
                    status TEXT,
                    categories_json TEXT,
                    rules_json TEXT,
                    static_count INTEGER,
                    animated_count INTEGER,
                    gif_count INTEGER
                )
            """)
            cur.execute(
                "INSERT INTO v76_regeneration_runs (created_at, project_name, status, categories_json, rules_json, static_count, animated_count, gif_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), project_name, status, json.dumps(categories, ensure_ascii=False), json.dumps(rules, ensure_ascii=False), counts.get("static", 0), counts.get("animated", 0), counts.get("gif", 0)),
            )
            con.commit()

    def _render_report(self, template_root: Path, out_path: Path, context: Dict[str, Any]) -> None:
        if Environment is None:
            raise RuntimeError("Jinja2 is required for v76 report rendering")
        template_root.mkdir(parents=True, exist_ok=True)
        template_path = template_root / "v76_rejection_to_regeneration_report.html.j2"
        if not template_path.exists():
            template_path.write_text("""<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><title>v76 반려 → 실제 재생성 리포트</title>
<style>body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f5f7fb;color:#172033;margin:0;padding:28px}.wrap{max-width:1160px;margin:auto}.hero{background:linear-gradient(135deg,#111827,#7c3aed,#06b6d4);color:white;border-radius:26px;padding:28px 32px}.card{background:white;border:1px solid #e5e7eb;border-radius:20px;padding:18px;margin-top:16px;box-shadow:0 8px 22px rgba(15,23,42,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.metric{font-size:28px;font-weight:900;color:#7c3aed}.badge{display:inline-block;background:#ede9fe;color:#5b21b6;border-radius:999px;padding:5px 10px;margin:3px;font-weight:700}li{margin:4px 0}code{background:#f1f5f9;border-radius:8px;padding:2px 5px}</style></head><body><div class=\"wrap\">
<div class=\"hero\"><h1>v76 캡처/반려 사유 → 실제 재생성 자동 연결</h1><p>v75 캡처 입력 · v74 액션 플랜 · v70 실제 32/24 재생성 · 다음 QC 루프 연결</p></div>
<div class=\"card\"><h2>프로젝트</h2><p><b>{{ project_name }}</b></p><p>상태: <b>{{ pipeline_status }}</b></p>{% for c in detected_categories %}<span class=\"badge\">{{ c }}</span>{% endfor %}</div>
<div class=\"grid\"><div class=\"card\"><div class=\"metric\">{{ regenerated_static_count }}</div><b>정지형 재생성</b></div><div class=\"card\"><div class=\"metric\">{{ regenerated_animated_count }}</div><b>움직이는형 재생성</b></div><div class=\"card\"><div class=\"metric\">{{ regenerated_gif_count }}</div><b>GIF 후보</b></div><div class=\"card\"><div class=\"metric\">{{ applied_regeneration_rules|length }}</div><b>적용 규칙</b></div></div>
<div class=\"card\"><h2>실제 적용된 재생성 규칙</h2><ul>{% for r in applied_regeneration_rules %}<li>{{ r }}</li>{% endfor %}</ul></div>
<div class=\"card\"><h2>다음 필수 단계</h2><ol>{% for s in next_required_steps %}<li>{{ s }}</li>{% endfor %}</ol></div>
<div class=\"card\"><h2>생성 파일</h2><ul><li>v75 리포트: <code>{{ capture_v75_report_html }}</code></li><li>v74 액션 플랜: <code>{{ connected_v74_action_plan_csv }}</code></li><li>재생성 v70 리포트: <code>{{ regenerated_v70_html_report }}</code></li><li>재생성 ZIP: <code>{{ regenerated_set_package_zip }}</code></li></ul></div>
<div class=\"card\"><h2>안전 메모</h2><ul>{% for n in safety_notes %}<li>{{ n }}</li>{% endfor %}</ul></div>
</div></body></html>""", encoding="utf-8")
        env = Environment(loader=FileSystemLoader(str(template_root)), autoescape=select_autoescape(["html", "xml"]))
        html = env.get_template(template_path.name).render(**context)
        out_path.write_text(html, encoding="utf-8")

    def build_bundle(
        self,
        project_name: str,
        concept_text: str,
        selected_style: str,
        main_phrase: str,
        user_feedback: str,
        online_abstract_notes: str,
        manual_rejection_text: str,
        image_inputs: Iterable[Tuple[str, bytes]],
        out_dir: Path,
        enable_ocr: bool = False,
        user_selected_rules: List[str] | None = None,
    ) -> V76RejectionToRegenerationReport:
        safe_project = self._safe_name(project_name)
        run_dir = out_dir / f"{safe_project}_{int(time.time())}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # 1) v75 capture/manual text -> connected v74 action plan
        v75_report = self.v75.build_bundle(
            project_name="cap",
            concept_text=concept_text,
            selected_style=selected_style,
            main_phrase=main_phrase,
            user_feedback=user_feedback,
            online_abstract_notes=online_abstract_notes,
            manual_rejection_text=manual_rejection_text or self.DEFAULT_REJECTION_TEXT,
            image_inputs=image_inputs,
            out_dir=run_dir / "cap",
            enable_ocr=enable_ocr,
        ).to_dict()
        v74_action_plan = Path(v75_report.get("v74_action_plan_csv", ""))
        action_rows = self._read_csv_rows(v74_action_plan)
        categories = self._extract_categories(v74_action_plan)
        rules = self._rules_from_categories(categories, user_selected_rules)

        # 2) Action plan -> actual regenerated 32/24 set
        regen_concept = (
            f"{concept_text}\n\n반려/캡처 기반 실제 재생성: "
            + "; ".join([str(r.get("improvement_action", "")) for r in action_rows[:6] if r.get("improvement_action")])
        )
        regen_feedback = (
            f"{user_feedback}\n\n[v76 applied action categories] " + ", ".join(categories)
            + "\n선택한 제안을 결과에 실제 반영하고 정지형 identity를 움직이는형까지 유지한다."
        )
        v70_report = self.v70.build_bundle(
            project_name="regen",
            concept_text=regen_concept,
            selected_style=selected_style,
            selected_rules=rules,
            main_phrase=main_phrase,
            user_feedback=regen_feedback,
            online_abstract_notes=online_abstract_notes + "\n" + "\n".join(rules),
            out_dir=run_dir / "regen",
        ).to_dict()

        regenerated_dir = Path(v70_report.get("output_dir", ""))
        prompt_md = run_dir / "v76_regeneration_prompt_pack.md"
        prompt_md.write_text(self._build_regeneration_prompt(project_name, concept_text, categories, action_rows, rules), encoding="utf-8")
        action_csv = run_dir / "v76_applied_regeneration_action_plan.csv"
        applied_rows = [
            {
                "no": i + 1,
                "category": cat,
                "applied_rule": rule,
                "applied_to": "static_32_and_animated_24",
                "status": "applied_to_regeneration",
            }
            for i, (cat, rule) in enumerate([(cat, rule) for cat in categories for rule in self.CATEGORY_RULE_MAP.get(cat, [])])
        ]
        if not applied_rows:
            applied_rows = [{"no": 1, "category": "general", "applied_rule": "짧은 문구/모션 다양성/가독성 강화", "applied_to": "static_32_and_animated_24", "status": "applied_to_regeneration"}]
        self._write_csv(action_csv, applied_rows, ["no", "category", "applied_rule", "applied_to", "status"])

        regenerated_set_zip = run_dir / "v76_regenerated_actual_set_package.zip"
        self._zip_paths(regenerated_set_zip, [regenerated_dir, prompt_md, action_csv], root=run_dir)
        static_count = len(self._read_csv_rows(Path(v70_report.get("static_32_plan_csv", ""))))
        animated_count = len(self._read_csv_rows(Path(v70_report.get("animated_24_plan_csv", ""))))
        gif_count = len(v70_report.get("required_gif_paths", []) or [])
        pipeline_status = "REGENERATION_DONE_RECHECK_REQUIRED"
        next_steps = [
            "v71 제출 전 규격/용량/프레임 QC 재실행",
            "v72 자동보정/잠금 재실행",
            "v73 사용자 최종 확인/수동 승인 재실행",
            "카카오 공식 기준 제출 직전 재확인",
        ]
        safety_notes = [
            "캡처/반려 사유는 개선 신호로만 사용하고 원본 캐릭터/문구/애니메이션 복제에 사용하지 않습니다.",
            "재생성 산출물은 원본을 덮어쓰지 않고 v76 regenerated 폴더에 새로 생성됩니다.",
            "유사성/저작권/원본성 HIGH 항목이 있었으면 최종 제출 ZIP은 v71/v72/v73 재검사 전까지 잠금 유지가 필요합니다.",
            "API 키 원문은 manifest, CSV, HTML, ZIP에 저장하지 않습니다.",
        ]
        manifest = {
            "version": self.VERSION,
            "project_name": project_name,
            "pipeline_status": pipeline_status,
            "detected_categories": categories,
            "applied_regeneration_rules": rules,
            "generated_counts": {"static": static_count, "animated": animated_count, "gif": gif_count},
            "source_chain": {
                "v75_report": v75_report.get("v75_html_report_path"),
                "v74_action_plan": str(v74_action_plan),
                "v70_regenerated_output": v70_report.get("output_dir"),
            },
            "next_required_steps": next_steps,
            "safety": {
                "abstract_signals_only": True,
                "no_existing_character_copy": True,
                "no_auto_submission": True,
                "api_key_plaintext_included": False,
            },
        }
        manifest_json = run_dir / "v76_rejection_to_regeneration_manifest.json"
        self._write_json(manifest_json, manifest)

        learning_db = run_dir / "v76_rejection_to_regeneration_learning.sqlite3"
        self._store_learning(learning_db, project_name, pipeline_status, categories, rules, {"static": static_count, "animated": animated_count, "gif": gif_count})

        html_report = run_dir / "v76_rejection_to_regeneration_report.html"
        report_context = {
            "project_name": project_name,
            "pipeline_status": pipeline_status,
            "detected_categories": categories,
            "applied_regeneration_rules": rules,
            "regenerated_static_count": static_count,
            "regenerated_animated_count": animated_count,
            "regenerated_gif_count": gif_count,
            "next_required_steps": next_steps,
            "safety_notes": safety_notes,
            "capture_v75_report_html": v75_report.get("v75_html_report_path", ""),
            "connected_v74_action_plan_csv": str(v74_action_plan),
            "regenerated_v70_html_report": v70_report.get("html_report_path", ""),
            "regenerated_set_package_zip": str(regenerated_set_zip),
        }
        template_root = Path(__file__).resolve().parents[1] / "templates" / "v76_rejection_to_regeneration"
        self._render_report(template_root, html_report, report_context)

        work_zip = run_dir / "v76_rejection_to_regeneration_work_package.zip"
        self._zip_paths(work_zip, [html_report, manifest_json, learning_db, prompt_md, action_csv, regenerated_set_zip, Path(v75_report.get("v75_work_package_zip", "")), Path(v75_report.get("v74_resubmission_work_package_zip", ""))], root=run_dir)
        checksum = self._sha256(work_zip)

        return V76RejectionToRegenerationReport(
            project_name=project_name,
            output_dir=str(run_dir),
            pipeline_status=pipeline_status,
            capture_v75_report_html=str(v75_report.get("v75_html_report_path", "")),
            capture_v75_work_package_zip=str(v75_report.get("v75_work_package_zip", "")),
            connected_v74_action_plan_csv=str(v74_action_plan),
            connected_v74_resubmission_zip=str(v75_report.get("v74_resubmission_work_package_zip", "")),
            regenerated_v70_html_report=str(v70_report.get("html_report_path", "")),
            regenerated_static_32_gallery=str(v70_report.get("static_gallery_png", "")),
            regenerated_animated_24_gallery=str(v70_report.get("animated_gallery_png", "")),
            regenerated_gif_contact_sheet=str(v70_report.get("motion_contact_sheet", "")),
            regenerated_set_package_zip=str(regenerated_set_zip),
            regeneration_action_plan_csv=str(action_csv),
            regeneration_prompt_md=str(prompt_md),
            regeneration_manifest_json=str(manifest_json),
            html_report_path=str(html_report),
            work_package_zip=str(work_zip),
            learning_db=str(learning_db),
            detected_categories=categories,
            applied_regeneration_rules=rules,
            regenerated_static_count=static_count,
            regenerated_animated_count=animated_count,
            regenerated_gif_count=gif_count,
            next_required_steps=next_steps,
            safety_notes=safety_notes,
            checksum_sha256=checksum,
        )
