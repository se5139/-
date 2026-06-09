from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Iterable
import csv
import hashlib
import json
import re
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

from modules.final_user_approval_workflow import V73FinalUserApprovalWorkflow


@dataclass
class V74RejectionResubmissionReport:
    project_name: str
    output_dir: str
    base_v73_html_report: str
    base_v73_manual_review_zip: str
    rejection_status: str
    revision_lock_required: bool
    overall_revision_score: int
    rejection_count: int
    high_priority_count: int
    detected_categories: List[str]
    action_plan_csv: str
    action_plan_json: str
    rejection_input_csv: str
    revised_static_32_plan_csv: str
    revised_animated_24_plan_csv: str
    prompt_pack_md: str
    trend_signal_memory_json: str
    resubmission_checklist_csv: str
    manifest_json: str
    html_report_path: str
    resubmission_work_package_zip: str
    locked_review_zip: str
    learning_db: str
    checksum_sha256: str
    safety_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class V74RejectionResubmissionLoop(V73FinalUserApprovalWorkflow):
    """v74 반려 대비/재제출 개선 루프.

    카카오 심사 반려 사유, 사용자의 수동 메모, CSV/TXT로 입력된 피드백을
    원본 복제 없이 추상 개선 신호로 분해하고, 다음 재생성/재제출을 위한
    수정 계획과 잠금 체크리스트를 만든다.
    """

    VERSION = "74.0.0"

    CATEGORY_RULES: Dict[str, Dict[str, Any]] = {
        "character_identity": {
            "label": "캐릭터성/콘셉트 약함",
            "keywords": ["캐릭터성", "개성", "콘셉트", "컨셉", "정체성", "매력", "독창"],
            "action": "시그니처 실루엣, 고정 포즈, 반복되는 말투, 대표 감정을 3개 이상 명확히 만든다.",
            "target": "정지형 32개 중 8개 이상에서 캐릭터 고유 포즈/성격이 보이게 재구성",
        },
        "chat_usability": {
            "label": "대화 활용성 낮음",
            "keywords": ["활용", "대화", "사용", "상황", "실생활", "공감", "쓸 곳"],
            "action": "아침/점심/퇴근/감사/확인/사과/거절/응원 등 실제 답장 상황을 우선 배치한다.",
            "target": "짧은 답장형 문구 비율을 70% 이상으로 조정",
        },
        "phrase_readability": {
            "label": "문구/가독성 문제",
            "keywords": ["문구", "오탈자", "맞춤법", "길", "가독", "읽", "텍스트", "글자"],
            "action": "2~7자 중심으로 줄이고, 말풍선 대비와 흰색/검은색 외곽선을 강화한다.",
            "target": "작은 썸네일/다크모드에서 문구가 먼저 읽히게 보정",
        },
        "motion_quality": {
            "label": "모션 어색함/움직임 약함",
            "keywords": ["모션", "움직", "어색", "프레임", "흔들", "느림", "빠름", "반복"],
            "action": "시작-중간-끝 리듬을 분리하고, 통통 튐/꾸벅/손흔들기/말풍선 동기화를 재설계한다.",
            "target": "필수 GIF 3개 이상을 서로 다른 모션 패턴으로 재생성",
        },
        "spec_file_issue": {
            "label": "규격/용량/파일 문제",
            "keywords": ["규격", "용량", "크기", "파일명", "투명", "배경", "프레임 수", "해상도"],
            "action": "360×360, 투명 배경, 파일명, 용량, 프레임 수를 재검사하고 자동보정 대상에 넣는다.",
            "target": "v71/v72 QC를 다시 통과한 보정본만 최종 후보로 이동",
        },
        "similarity_copyright": {
            "label": "유사성/저작권 위험",
            "keywords": ["유사", "저작권", "모방", "비슷", "기존", "판매 중", "캐릭터 침해", "상표"],
            "action": "외형, 문구, 애니메이션 순서, 컬러 조합을 원본 창작 방향으로 크게 바꾼다.",
            "target": "유사 위험 항목이 남으면 최종 제출 ZIP을 잠금 유지",
        },
        "set_repetition": {
            "label": "세트 반복감/다양성 부족",
            "keywords": ["중복", "반복", "다양", "비슷한", "겹침", "구성"],
            "action": "감정군, 포즈군, 문구군을 다시 분산해 32개/24개가 같은 장면처럼 보이지 않게 한다.",
            "target": "동일 감정·포즈·문구 반복을 줄이고 세트 다양성 점수를 올림",
        },
        "finish_quality": {
            "label": "완성도/선/색 품질 부족",
            "keywords": ["완성도", "퀄리티", "품질", "선", "외곽선", "색", "흐림", "깨짐"],
            "action": "외곽선 굵기, 얼굴 크기, 색 대비, 말풍선 배치, 그림자/하이라이트를 보정한다.",
            "target": "작은 화면에서도 얼굴·문구·동작이 분리되어 보이게 보정",
        },
        "ai_policy_origin": {
            "label": "AI/원본성 소명 필요",
            "keywords": ["AI", "ai", "자동생성", "원본", "창작", "스케치", "증빙", "소명"],
            "action": "스케치, 도형, 수정 이력, 창작 manifest, 작업 로그를 함께 보존한다.",
            "target": "직접 창작 증거 폴더와 manifest를 제출 전 검토 패키지에 포함",
        },
    }

    DEFAULT_REJECTION_TEXT = """캐릭터성이 약하고 대화 활용성이 낮아 보입니다.
문구가 길고 작은 화면에서 가독성이 부족합니다.
움직임이 단순하고 일부 표현이 반복적으로 보입니다.
기존 인기 캐릭터와 유사해 보이지 않도록 독창성을 더 강화해야 합니다."""

    STATIC_EMOTIONS = [
        "인사", "확인", "감사", "사과", "축하", "응원", "퇴근", "피곤",
        "놀람", "민망", "하트", "거절", "기다림", "웃음", "울먹", "분노",
        "부탁", "좋아", "싫어", "배고파", "잠옴", "출근", "회의", "집중",
        "OK", "천천히", "잘자", "주말", "월요일", "멘붕", "기쁨", "마무리",
    ]
    ANIMATED_MOTIONS = [
        "통통 튐", "꾸벅", "손 흔들기", "부들부들", "말풍선 흔들림", "하트 팡",
        "눈물 또르르", "피곤 흔들", "깜짝 점프", "고개 끄덕", "손 번쩍", "뒤로 숨기",
        "박수", "불꽃 축하", "쭈글", "녹아내림", "반짝", "좌우 흔들", "작게 점프",
        "숨 고르기", "쿵 떨어짐", "두근", "말풍선 팝", "마무리 웨이브",
    ]

    def _sha256_v74(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _safe_text_rows(self, text: str) -> List[str]:
        chunks = []
        for line in re.split(r"[\n\r]+|(?<=[.!?。])\s+", text or ""):
            s = line.strip(" -•\t")
            if s:
                chunks.append(s[:400])
        return chunks or ["반려 사유가 비어 있어 기본 개선 루프로 분석합니다."]

    def _classify_rows(self, rows: Iterable[str]) -> List[Dict[str, Any]]:
        action_rows: List[Dict[str, Any]] = []
        seen = set()
        idx = 0
        for raw in rows:
            reason = str(raw).strip()
            if not reason:
                continue
            matched = []
            for cat, rule in self.CATEGORY_RULES.items():
                if any(k.lower() in reason.lower() for k in rule["keywords"]):
                    matched.append(cat)
            if not matched:
                matched = ["finish_quality"]
            for cat in matched:
                key = (cat, reason)
                if key in seen:
                    continue
                seen.add(key)
                idx += 1
                priority = "HIGH" if cat in {"similarity_copyright", "spec_file_issue", "ai_policy_origin"} else ("MID" if cat in {"character_identity", "chat_usability", "motion_quality"} else "NORMAL")
                rule = self.CATEGORY_RULES[cat]
                action_rows.append({
                    "no": idx,
                    "priority": priority,
                    "category": cat,
                    "category_label": rule["label"],
                    "rejection_reason": reason,
                    "improvement_action": rule["action"],
                    "target_output": rule["target"],
                    "status": "planned",
                })
        return action_rows

    def _write_csv(self, path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in fieldnames})

    def _write_json(self, path: Path, obj: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def _zip_paths_v74(self, zip_path: Path, paths: List[Path], root: Path | None = None) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                if not p.exists():
                    continue
                if p.is_dir():
                    for child in p.rglob("*"):
                        if child.is_file():
                            try:
                                arc = str(child.relative_to(root or p.parent))
                            except Exception:
                                arc = child.name
                            zf.write(child, arc)
                else:
                    try:
                        arc = str(p.relative_to(root)) if root else p.name
                    except Exception:
                        arc = p.name
                    zf.write(p, arc)

    def _revised_static_plan(self, categories: List[str], main_phrase: str) -> List[Dict[str, Any]]:
        rows = []
        for i, emotion in enumerate(self.STATIC_EMOTIONS, start=1):
            focus = "문구 짧게" if "phrase_readability" in categories else "표정 차별화"
            if "character_identity" in categories and i % 4 == 1:
                focus = "시그니처 포즈 강화"
            if "chat_usability" in categories and i % 3 == 0:
                focus = "실제 답장 상황 강화"
            if "set_repetition" in categories and i % 5 == 0:
                focus = "중복 포즈 교체"
            rows.append({
                "slot": f"static_{i:02d}",
                "emotion": emotion,
                "phrase_hint": main_phrase if i == 1 else self._short_phrase_for_emotion(emotion),
                "revision_focus": focus,
                "quality_target": "작은 썸네일 가독성 + 고유 표정 + 복제 위험 없음",
            })
        return rows

    def _revised_animated_plan(self, categories: List[str], main_phrase: str) -> List[Dict[str, Any]]:
        rows = []
        for i, motion in enumerate(self.ANIMATED_MOTIONS, start=1):
            required_gif = i in {1, 2, 3, 6, 9}
            focus = "시작-중간-끝 리듬 강화" if "motion_quality" in categories else "identity 유지"
            if "phrase_readability" in categories and i % 4 == 0:
                focus = "말풍선 움직임과 문구 가독성 동시 보정"
            rows.append({
                "slot": f"animated_{i:02d}",
                "motion": motion,
                "phrase_hint": main_phrase if i == 1 else self._short_phrase_for_emotion(self.STATIC_EMOTIONS[(i-1) % len(self.STATIC_EMOTIONS)]),
                "required_gif_candidate": "YES" if required_gif else "NO",
                "revision_focus": focus,
                "quality_target": "정지형 identity 유지 + 모션 차별화 + 24프레임/용량 검사",
            })
        return rows

    def _short_phrase_for_emotion(self, emotion: str) -> str:
        mapping = {
            "인사": "안녕", "확인": "넵", "감사": "고마워", "사과": "미안", "축하": "축하해",
            "응원": "할수있어", "퇴근": "퇴근!", "피곤": "힘들어", "놀람": "헉", "민망": "머쓱",
            "하트": "좋아", "거절": "안돼", "기다림": "기다려", "웃음": "ㅋㅋ", "울먹": "힝",
            "분노": "으악", "부탁": "제발", "배고파": "배고파", "잠옴": "졸려", "잘자": "잘자",
        }
        return mapping.get(emotion, emotion[:6])

    def _prompt_pack_text(self, project_name: str, action_rows: List[Dict[str, Any]], categories: List[str]) -> str:
        bullets = "\n".join(f"- [{r['priority']}] {r['category_label']}: {r['improvement_action']}" for r in action_rows[:20])
        return f"""# v74 재제출 개선 프롬프트 팩\n\n프로젝트: {project_name}\n\n## 감지된 반려/개선 카테고리\n{', '.join(categories) if categories else 'none'}\n\n## 수정 원칙\n- 기존 인기 캐릭터·문구·애니메이션을 복제하지 않는다.\n- 온라인 자료는 추상 품질 신호로만 사용한다.\n- 정지형 identity를 움직이는형에서도 유지한다.\n- 작은 썸네일에서 얼굴과 문구가 먼저 읽히게 한다.\n- 32개/24개 전체가 같은 표정·포즈처럼 보이지 않게 한다.\n\n## 개선 액션\n{bullets}\n\n## 다음 재생성 지시문\n캐릭터의 외형·색상·말투는 유지하되, 위 개선 액션을 반영해 정지형 32개와 움직이는형 24개를 다시 설계한다. GIF 후보는 최소 3개 이상 만들고, 시작-중간-끝 움직임이 분명하게 보이도록 한다.\n"""

    def _store_v74_learning(self, db: Path, project_name: str, status: str, score: int, rows: List[Dict[str, Any]]) -> None:
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v74_rejection_runs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    rejection_status TEXT,
                    overall_revision_score INTEGER,
                    rejection_count INTEGER,
                    high_priority_count INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v74_rejection_items(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    priority TEXT,
                    category TEXT,
                    category_label TEXT,
                    rejection_reason TEXT,
                    improvement_action TEXT,
                    target_output TEXT
                )
            """)
            high_count = sum(1 for r in rows if r.get("priority") == "HIGH")
            cur.execute(
                "INSERT INTO v74_rejection_runs(created_at, project_name, rejection_status, overall_revision_score, rejection_count, high_priority_count) VALUES(?,?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), project_name, status, int(score), len(rows), high_count),
            )
            run_id = cur.lastrowid
            for r in rows:
                cur.execute(
                    "INSERT INTO v74_rejection_items(run_id, priority, category, category_label, rejection_reason, improvement_action, target_output) VALUES(?,?,?,?,?,?,?)",
                    (run_id, r.get("priority"), r.get("category"), r.get("category_label"), r.get("rejection_reason"), r.get("improvement_action"), r.get("target_output")),
                )
            con.commit()

    def _render_v74_report(self, template_dir: Path, out_path: Path, context: Dict[str, Any]) -> None:
        template_dir.mkdir(parents=True, exist_ok=True)
        template = template_dir / "v74_rejection_resubmission_report.html.j2"
        if not template.exists():
            template.write_text("""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>v74 반려 대비/재제출 개선 리포트</title>
<style>
body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;color:#172033;margin:0;padding:28px}.wrap{max-width:1160px;margin:auto}.hero{background:linear-gradient(135deg,#111827,#dc2626,#f59e0b);color:white;border-radius:28px;padding:28px 32px;box-shadow:0 18px 42px rgba(15,23,42,.20)}.card{background:white;border:1px solid #e5e7eb;border-radius:22px;padding:20px;margin-top:18px;box-shadow:0 10px 28px rgba(15,23,42,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.score{font-size:34px;font-weight:900;color:#dc2626}.badge{display:inline-block;border-radius:999px;padding:5px 10px;margin:3px;font-weight:800}.high{background:#fee2e2;color:#991b1b}.mid{background:#fef3c7;color:#92400e}.normal{background:#dcfce7;color:#166534}.mono{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:16px;padding:14px;overflow:auto}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left;font-size:14px}
</style></head><body><div class="wrap"><div class="hero"><h1>v74 반려 대비/재제출 개선 리포트</h1><p>반려 사유를 분류하고, 다음 재생성·재제출을 위한 수정 액션으로 변환합니다.</p></div>
<div class="card"><h2>상태</h2><div class="grid"><div><div class="score">{{ overall_revision_score }}</div><b>개선 준비 점수</b></div><div><div class="score">{{ rejection_count }}</div><b>분석 항목</b></div><div><div class="score">{{ high_priority_count }}</div><b>고우선순위</b></div></div><p>{% for c in detected_categories %}<span class="badge mid">{{ c }}</span>{% endfor %}</p></div>
<div class="card"><h2>수정 액션 플랜</h2><table><thead><tr><th>우선순위</th><th>분류</th><th>사유</th><th>개선 액션</th></tr></thead><tbody>{% for r in action_rows %}<tr><td><span class="badge {{ 'high' if r.priority == 'HIGH' else ('mid' if r.priority == 'MID' else 'normal') }}">{{ r.priority }}</span></td><td>{{ r.category_label }}</td><td>{{ r.rejection_reason }}</td><td>{{ r.improvement_action }}</td></tr>{% endfor %}</tbody></table></div>
<div class="card"><h2>재제출 잠금 기준</h2><div class="mono">{{ lock_note }}</div></div>
<div class="card"><h2>안전 메모</h2><div class="mono">{{ safety_note }}</div></div>
</div></body></html>""", encoding="utf-8")
        if Environment is None:
            raise RuntimeError("Jinja2 is required for v74 report rendering")
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"]))
        out_path.write_text(env.get_template(template.name).render(**context), encoding="utf-8")

    def build_bundle(
        self,
        project_name: str,
        concept_text: str,
        selected_style: str,
        main_phrase: str,
        user_feedback: str,
        online_abstract_notes: str,
        rejection_text: str,
        out_dir: Path,
    ) -> V74RejectionResubmissionReport:
        safe_project = self._safe_name_v70(project_name or "v74_rejection_resubmission")
        run_dir = out_dir / f"{safe_project}_{int(time.time())}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Keep the chain connected to v73, but do not auto-submit anything.
        confirmations = {k: True for k, _ in self.REQUIRED_CONFIRMATIONS + self.OPTIONAL_CONFIRMATIONS}
        base_v73 = super().build_bundle(
            project_name=project_name,
            concept_text=concept_text,
            selected_style=selected_style,
            main_phrase=main_phrase,
            user_feedback=user_feedback,
            online_abstract_notes=online_abstract_notes,
            user_confirmations=confirmations,
            out_dir=run_dir / "base_v73_user_approval",
        )
        v73 = base_v73.to_dict()

        rejection_rows = self._safe_text_rows(rejection_text or self.DEFAULT_REJECTION_TEXT)
        action_rows = self._classify_rows(rejection_rows)
        categories = sorted({r["category"] for r in action_rows})
        high_count = sum(1 for r in action_rows if r.get("priority") == "HIGH")
        revision_lock_required = any(c in categories for c in ["similarity_copyright", "spec_file_issue", "ai_policy_origin"])
        overall_score = max(0, min(100, 100 - high_count * 12 - max(0, len(action_rows) - 5) * 2))
        status = "REVISION_LOCK_REQUIRED" if revision_lock_required else "REVISION_PLAN_READY"

        rejection_input_csv = run_dir / "v74_rejection_input.csv"
        self._write_csv(rejection_input_csv, [{"no": i+1, "rejection_reason": r} for i, r in enumerate(rejection_rows)], ["no", "rejection_reason"])
        action_plan_csv = run_dir / "v74_action_plan.csv"
        action_plan_json = run_dir / "v74_action_plan.json"
        self._write_csv(action_plan_csv, action_rows, ["no", "priority", "category", "category_label", "rejection_reason", "improvement_action", "target_output", "status"])
        self._write_json(action_plan_json, action_rows)

        static_plan = self._revised_static_plan(categories, main_phrase)
        animated_plan = self._revised_animated_plan(categories, main_phrase)
        static_csv = run_dir / "v74_revised_static_32_plan.csv"
        animated_csv = run_dir / "v74_revised_animated_24_plan.csv"
        self._write_csv(static_csv, static_plan, ["slot", "emotion", "phrase_hint", "revision_focus", "quality_target"])
        self._write_csv(animated_csv, animated_plan, ["slot", "motion", "phrase_hint", "required_gif_candidate", "revision_focus", "quality_target"])

        prompt_pack = run_dir / "v74_resubmission_prompt_pack.md"
        prompt_pack.write_text(self._prompt_pack_text(project_name, action_rows, categories), encoding="utf-8")
        trend_memory = {
            "version": self.VERSION,
            "project_name": project_name,
            "stored_as_abstract_signals_only": True,
            "detected_categories": categories,
            "preferred_next_generation_bias": {
                "phrase_length": "2~7 Korean characters first" if "phrase_readability" in categories else "short reply type",
                "motion": "clear start-middle-end rhythm" if "motion_quality" in categories else "identity preserving motion",
                "character": "stronger signature silhouette" if "character_identity" in categories else "preserve identity lock",
                "safety": "similarity/copyright lock required" if "similarity_copyright" in categories else "no copying of existing items",
            },
            "source_policy": "Online and rejection feedback are stored as abstract quality signals, not copied characters or protected expressions.",
        }
        trend_memory_json = run_dir / "v74_abstract_signal_memory.json"
        self._write_json(trend_memory_json, trend_memory)

        checklist_rows = [
            {"type": "required", "item": "반려 사유 원문/CSV/캡처 메모 보존", "status": "planned"},
            {"type": "required", "item": "유사성/저작권 HIGH 항목 해결 전 제출 잠금", "status": "locked" if revision_lock_required else "planned"},
            {"type": "required", "item": "v71 규격 QC 재실행", "status": "planned"},
            {"type": "required", "item": "v72 자동보정 재실행", "status": "planned"},
            {"type": "required", "item": "v73 사용자 최종 승인 재확인", "status": "planned"},
        ]
        checklist_csv = run_dir / "v74_resubmission_checklist.csv"
        self._write_csv(checklist_csv, checklist_rows, ["type", "item", "status"])

        db = run_dir / "v74_rejection_resubmission_learning.sqlite3"
        self._store_v74_learning(db, project_name, status, overall_score, action_rows)

        manifest = {
            "version": self.VERSION,
            "project_name": project_name,
            "status": status,
            "revision_lock_required": revision_lock_required,
            "overall_revision_score": overall_score,
            "detected_categories": categories,
            "rejection_count": len(action_rows),
            "high_priority_count": high_count,
            "base_v73_status": v73.get("approval_status"),
            "next_required_steps": [
                "Apply v74 action plan to regenerate character/set",
                "Run v71 QC again",
                "Run v72 autofix/lock again",
                "Run v73 final user approval again",
            ],
            "safety": {
                "no_auto_submission": True,
                "no_existing_character_copy": True,
                "abstract_signals_only": True,
                "api_key_plaintext_included": False,
            },
        }
        manifest_json = run_dir / "v74_rejection_resubmission_manifest.json"
        self._write_json(manifest_json, manifest)

        html_report = run_dir / "v74_rejection_resubmission_report.html"
        self._render_v74_report(
            Path("templates") / "v74_rejection_resubmission",
            html_report,
            {
                "project_name": project_name,
                "overall_revision_score": overall_score,
                "rejection_count": len(action_rows),
                "high_priority_count": high_count,
                "detected_categories": [self.CATEGORY_RULES[c]["label"] for c in categories if c in self.CATEGORY_RULES],
                "action_rows": action_rows,
                "lock_note": "HIGH 항목 또는 규격/유사성/원본성 항목이 남아 있으면 최종 제출 ZIP을 잠금 유지합니다." if revision_lock_required else "현재 입력 기준으로 고위험 잠금 사유는 없지만, 재생성 후 QC/사용자 승인을 다시 통과해야 합니다.",
                "safety_note": "이 루프는 반려 사유를 개선 액션으로 바꾸는 도구입니다. 카카오 승인이나 수익을 보장하지 않으며, 기존 캐릭터/문구/애니메이션 복제를 금지합니다.",
            },
        )

        work_zip = run_dir / "v74_resubmission_work_package.zip"
        locked_zip = run_dir / "v74_locked_review_package.zip"
        work_paths = [
            rejection_input_csv, action_plan_csv, action_plan_json, static_csv, animated_csv,
            prompt_pack, trend_memory_json, checklist_csv, manifest_json, html_report, db,
        ]
        self._zip_paths_v74(work_zip, work_paths, root=run_dir)
        locked_paths = work_paths + [Path(v73.get("manual_review_zip", "")), Path(v73.get("html_report_path", ""))]
        self._zip_paths_v74(locked_zip, locked_paths, root=run_dir)
        checksum = self._sha256_v74(work_zip)

        return V74RejectionResubmissionReport(
            project_name=project_name,
            output_dir=str(run_dir),
            base_v73_html_report=str(v73.get("html_report_path", "")),
            base_v73_manual_review_zip=str(v73.get("manual_review_zip", "")),
            rejection_status=status,
            revision_lock_required=revision_lock_required,
            overall_revision_score=overall_score,
            rejection_count=len(action_rows),
            high_priority_count=high_count,
            detected_categories=categories,
            action_plan_csv=str(action_plan_csv),
            action_plan_json=str(action_plan_json),
            rejection_input_csv=str(rejection_input_csv),
            revised_static_32_plan_csv=str(static_csv),
            revised_animated_24_plan_csv=str(animated_csv),
            prompt_pack_md=str(prompt_pack),
            trend_signal_memory_json=str(trend_memory_json),
            resubmission_checklist_csv=str(checklist_csv),
            manifest_json=str(manifest_json),
            html_report_path=str(html_report),
            resubmission_work_package_zip=str(work_zip),
            locked_review_zip=str(locked_zip),
            learning_db=str(db),
            checksum_sha256=checksum,
            safety_notes=[
                "반려 사유는 추상 개선 신호로만 저장합니다.",
                "기존 캐릭터·문구·애니메이션 복제 기능은 포함하지 않습니다.",
                "HIGH 항목이 있으면 재제출 전 v71/v72/v73 재검사를 요구합니다.",
                "API 키·비밀번호·개인정보 원문을 산출물에 포함하지 않습니다.",
            ],
        )
