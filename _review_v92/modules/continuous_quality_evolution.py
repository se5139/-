from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import hashlib
import json
import re
import sqlite3
import time
import zipfile

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from modules.video_reference_quality_engine import VideoReferenceQualityEngine


@dataclass
class V68EvolutionReport:
    project_name: str
    output_dir: str
    source_v67_package: str
    trend_signal_json: str
    quality_history_db: str
    quality_score_csv: str
    feedback_memory_json: str
    evolution_plan_json: str
    html_report_path: str
    prompt_template_path: str
    package_zip_path: str
    static_png: str
    animated_preview_gif: str
    motion_variants: List[Dict[str, Any]]
    quality_scores: Dict[str, int]
    evolution_scores: Dict[str, int]
    abstract_trend_signals: Dict[str, Any]
    safety_notes: List[str]
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContinuousQualityEvolutionEngine:
    """v68 지속 진화형 품질개선/온라인 트렌드 분석 엔진.

    설계 기준
    - 온라인 자료를 직접 복제하거나 기존 인기 캐릭터 외형을 따라 하지 않는다.
    - 최근 30일/무료 수집/쿼터 카운터/유료 호출 차단 구조를 우선한다.
    - 사용자가 만족한 선택값, 문구, 모션, 품질 점수를 SQLite/JSON에 누적한다.
    - 다음 생성 때 추상 트렌드 신호와 사용자 선호를 반영해 품질 점수를 끌어올린다.
    """

    DEFAULT_SAFETY_NOTES = [
        "온라인 정보는 감정 유형, 문구 길이, 모션 리듬, 가독성 같은 추상 신호만 저장합니다.",
        "기존 판매 중인 이모티콘의 동일 메시지, 동일 표현법, 동일 애니메이션은 재사용하지 않습니다.",
        "API 키 원문은 리포트, JSON, CSV, ZIP에 저장하지 않습니다.",
        "YouTube/Google/OpenAI 등 유료 호출은 기본 OFF이며 사용자가 승인해야만 실행합니다.",
        "카카오 공식 규격은 제출 직전 공식 스튜디오/가이드에서 다시 확인해야 합니다.",
    ]

    STYLE_WEIGHTS = {
        "굵은 외곽선": ("thumbnail_readability", 9),
        "짧은 문구": ("phrase_readability", 10),
        "미니": ("mini_reaction_fit", 9),
        "리액션": ("mini_reaction_fit", 9),
        "손그림": ("handdrawn_identity", 8),
        "하찮": ("relatable_concept", 9),
        "공감": ("relatable_concept", 9),
        "다크모드": ("dark_mode_contrast", 8),
        "말풍선": ("speech_bubble_clarity", 8),
        "움직": ("motion_clarity", 8),
        "GIF": ("motion_preview", 10),
        "WebP": ("submission_readiness", 6),
        "24개": ("set_expandability", 7),
        "32개": ("set_expandability", 7),
        "직장": ("relatable_concept", 7),
        "답장": ("phrase_readability", 8),
    }

    FORBIDDEN_HINTS = [
        "라이언", "춘식이", "어피치", "카카오프렌즈", "라인프렌즈", "산리오", "헬로키티",
        "포켓몬", "피카츄", "디즈니", "짱구", "도라에몽", "스누피", "망그러진 곰",
        "가나디", "토심이", "슈야", "꺅두기", "똑같이", "비슷하게", "따라", "복제",
        "캡처 그대로", "원본 그대로", "저작권 우회", "검수 우회",
    ]

    def __init__(self) -> None:
        self.v67 = VideoReferenceQualityEngine()

    def _safe_name(self, value: str) -> str:
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "v68_evolution"))
        return safe[:80] or "v68_evolution"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def extract_abstract_trend_signals(
        self,
        youtube_notes: str,
        kakao_notes: str,
        user_feedback: str,
        local_uploaded_notes: str,
    ) -> Dict[str, Any]:
        text = "\n".join([youtube_notes or "", kakao_notes or "", user_feedback or "", local_uploaded_notes or ""])
        normalized = re.sub(r"\s+", " ", text).strip()
        risk_hits = [w for w in self.FORBIDDEN_HINTS if w in normalized]
        scores = {
            "thumbnail_readability": 60,
            "phrase_readability": 60,
            "mini_reaction_fit": 55,
            "handdrawn_identity": 55,
            "relatable_concept": 60,
            "dark_mode_contrast": 55,
            "speech_bubble_clarity": 60,
            "motion_clarity": 55,
            "motion_preview": 60,
            "set_expandability": 55,
            "submission_readiness": 50,
        }
        hits: List[Dict[str, Any]] = []
        for key, (score_key, weight) in self.STYLE_WEIGHTS.items():
            count = normalized.count(key)
            if count:
                scores[score_key] = min(100, scores[score_key] + min(20, count * weight))
                hits.append({"keyword": key, "mapped_to": score_key, "count": count, "weight": weight})

        # 실제 온라인 원본 복제 대신 추상 신호 문장만 저장한다.
        recommendations: List[str] = []
        if scores["phrase_readability"] >= 75:
            recommendations.append("문구는 2~7자 중심의 즉답형을 우선합니다.")
        if scores["thumbnail_readability"] >= 75:
            recommendations.append("작은 썸네일 기준으로 얼굴·문구·외곽선을 크게 배치합니다.")
        if scores["mini_reaction_fit"] >= 70:
            recommendations.append("미니 리액션처럼 한눈에 의미가 읽히는 포즈를 우선합니다.")
        if scores["motion_clarity"] >= 70 or scores["motion_preview"] >= 70:
            recommendations.append("GIF는 파일명 표시가 아니라 화면에서 실제 재생되는 비교 패널을 기본으로 둡니다.")
        if scores["relatable_concept"] >= 75:
            recommendations.append("하찮은 공감·직장/일상 답장형 표현을 우선 추천합니다.")
        if not recommendations:
            recommendations.append("입력 자료가 부족하므로 로컬 ZIP/TXT/CSV/자막 파일을 먼저 추가해 추상 신호를 보강합니다.")

        return {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "collection_mode": {
                "window_days": 30,
                "local_file_zip_first": True,
                "youtube_api_optional": True,
                "google_search_api_default_off": True,
                "openai_api_default_off": True,
                "paid_calls_blocked_by_default": True,
                "quota_counter_required": True,
            },
            "abstract_only_policy": True,
            "raw_source_storage": "disabled",
            "detected_signal_hits": hits,
            "risk_hits": risk_hits,
            "scores": scores,
            "recommendations": recommendations,
            "source_notes_preview": normalized[:1500],
        }

    def _init_db(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS quality_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    style TEXT,
                    concept TEXT,
                    satisfaction INTEGER,
                    total_score INTEGER,
                    package_path TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS abstract_trend_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    signal_key TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    source_window_days INTEGER NOT NULL,
                    policy TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_feedback_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    feedback_text TEXT,
                    selected_style TEXT,
                    selected_motion TEXT,
                    next_action TEXT
                )
                """
            )
            con.commit()

    def _store_learning_data(
        self,
        db_path: Path,
        project_name: str,
        style: str,
        concept: str,
        satisfaction: int,
        scores: Dict[str, int],
        package_path: str,
        feedback_text: str,
        selected_motion: str,
    ) -> None:
        self._init_db(db_path)
        total_score = int(sum(scores.values()) / max(1, len(scores)))
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO quality_runs(created_at, project_name, style, concept, satisfaction, total_score, package_path) VALUES(?,?,?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), project_name, style, concept, satisfaction, total_score, package_path),
            )
            for k, v in scores.items():
                cur.execute(
                    "INSERT INTO abstract_trend_signals(created_at, signal_key, score, source_window_days, policy) VALUES(?,?,?,?,?)",
                    (time.strftime("%Y-%m-%d %H:%M:%S"), k, int(v), 30, "abstract_only_no_character_copy"),
                )
            cur.execute(
                "INSERT INTO user_feedback_memory(created_at, feedback_text, selected_style, selected_motion, next_action) VALUES(?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), feedback_text[:2000], style, selected_motion, "next_generation_apply_preferred_style_and_motion"),
            )
            con.commit()

    def _render_template(self, out_path: Path, context: Dict[str, Any]) -> None:
        template_dir = Path(__file__).resolve().parents[1] / "templates" / "v68_evolution"
        template_dir.mkdir(parents=True, exist_ok=True)
        template_file = template_dir / "evolution_report.html.j2"
        if not template_file.exists():
            template_file.write_text(
                """<!doctype html>
<html lang=\"ko\"><head><meta charset=\"utf-8\"><title>v68 지속 진화형 품질개선 리포트</title>
<style>
body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;color:#172033;margin:0;padding:28px}.wrap{max-width:1180px;margin:auto}.hero{background:linear-gradient(135deg,#0f172a,#16a34a,#06b6d4);color:white;border-radius:28px;padding:28px 32px;box-shadow:0 18px 42px rgba(15,23,42,.2)}.card{background:white;border:1px solid #e5e7eb;border-radius:22px;padding:20px;margin-top:18px;box-shadow:0 10px 28px rgba(15,23,42,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}.preview{text-align:center;background:#fff;border:1px solid #e5e7eb;border-radius:18px;padding:12px}.preview img{max-width:230px;border-radius:18px;background:white}.badge{display:inline-block;background:#dcfce7;color:#166534;border-radius:999px;padding:5px 10px;margin:3px;font-weight:700}.warn{background:#fff7ed;color:#9a3412;border:1px solid #fed7aa;border-radius:14px;padding:12px}.score{font-size:28px;font-weight:800;color:#16a34a}.mono{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:16px;padding:14px;overflow:auto}
</style></head><body><div class=\"wrap\"><div class=\"hero\"><h1>v68 지속 진화형 품질개선 리포트</h1><p>온라인 추상 트렌드 신호 · 사용자 만족도 · 정지형→움직이는형 품질 진화</p></div>
<div class=\"card\"><h2>프로젝트</h2><p><b>{{ project_name }}</b></p><p>{{ concept_text }}</p><p>스타일: <b>{{ selected_style }}</b> / 만족도 기록: <b>{{ satisfaction_score }}</b></p>{% for r in recommendations %}<span class=\"badge\">{{ r }}</span>{% endfor %}</div>
<div class=\"card\"><h2>바로 보이는 결과</h2><div class=\"grid\"><div class=\"preview\"><h3>정지형 PNG</h3><img src=\"data:image/png;base64,{{ static_png_b64 }}\"></div><div class=\"preview\"><h3>대표 움직이는 GIF</h3><img src=\"data:image/gif;base64,{{ animated_gif_b64 }}\"></div></div></div>
<div class=\"card\"><h2>품질 점수</h2><div class=\"grid\">{% for k,v in evolution_scores.items() %}<div><div class=\"score\">{{ v }}</div><b>{{ k }}</b></div>{% endfor %}</div></div>
<div class=\"card\"><h2>추상 트렌드 신호</h2><pre class=\"mono\">{{ abstract_trend_json }}</pre></div>
<div class=\"card warn\"><b>안전 원칙</b><ul>{% for n in safety_notes %}<li>{{ n }}</li>{% endfor %}</ul></div>
</div></body></html>""",
                encoding="utf-8",
            )
        if Environment:
            env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"]))
            rendered = env.get_template("evolution_report.html.j2").render(**context)
        else:
            rendered = json.dumps(context, ensure_ascii=False, indent=2)
        out_path.write_text(rendered, encoding="utf-8")

    def _b64(self, path: Path) -> str:
        import base64
        return base64.b64encode(path.read_bytes()).decode("ascii") if path.exists() else ""

    def build_bundle(
        self,
        project_name: str,
        concept_text: str,
        selected_style: str,
        selected_suggestions: List[str],
        main_phrase: str,
        youtube_notes: str,
        kakao_notes: str,
        user_feedback: str,
        local_uploaded_notes: str,
        satisfaction_score: int,
        preferred_motion: str,
        out_dir: Optional[Path] = None,
    ) -> V68EvolutionReport:
        out_base = Path(out_dir or "outputs/v68_continuous_quality_evolution")
        root = out_base / f"{self._safe_name(project_name)}_{int(time.time())}"
        root.mkdir(parents=True, exist_ok=True)

        trend = self.extract_abstract_trend_signals(youtube_notes, kakao_notes, user_feedback, local_uploaded_notes)
        scores = dict(trend["scores"])
        # 사용자가 만족한 결과라면 선호 스타일 유지/강화, 불만족이면 탐색 다양성 강화.
        if satisfaction_score >= 80:
            scores["user_preference_alignment"] = 92
            feedback_action = "현재 스타일을 다음 생성 기본값으로 고정"
        elif satisfaction_score >= 60:
            scores["user_preference_alignment"] = 78
            feedback_action = "현재 스타일 유지 + 모션/표정 다양성 보강"
        else:
            scores["user_preference_alignment"] = 55
            feedback_action = "스타일 후보를 다시 넓히고 문구/표정/모션을 재탐색"

        suggestion_map = list(selected_suggestions or [])
        for rec in trend.get("recommendations", []):
            if "문구" in rec and "캐릭터보다 문구가 먼저 읽히는 짧은 말풍선" not in suggestion_map:
                suggestion_map.append("캐릭터보다 문구가 먼저 읽히는 짧은 말풍선")
            if "썸네일" in rec and "작은 썸네일에서도 보이는 굵은 외곽선" not in suggestion_map:
                suggestion_map.append("작은 썸네일에서도 보이는 굵은 외곽선")
            if "GIF" in rec and "GIF가 화면에서 바로 움직이게 표시" not in suggestion_map:
                suggestion_map.append("GIF가 화면에서 바로 움직이게 표시")
            if "미니" in rec and "미니 리액션처럼 즉시 이해되는 실루엣" not in suggestion_map:
                suggestion_map.append("미니 리액션처럼 즉시 이해되는 실루엣")
        if "기존 인기 캐릭터 복제 금지" not in suggestion_map:
            suggestion_map.append("기존 인기 캐릭터 복제 금지")

        # v67 생성 엔진을 실제 제작 엔진으로 재사용하되, v68 신호를 입력에 반영.
        v67_result = self.v67.build_bundle(
            project_name=f"{project_name}_v68_base",
            concept_text=concept_text + "\n" + " / ".join(trend.get("recommendations", [])),
            selected_style=selected_style,
            selected_suggestions=suggestion_map,
            main_phrase=main_phrase,
            video_notes="v68 연속 품질개선: " + user_feedback[:500],
            online_notes=" / ".join([youtube_notes[:400], kakao_notes[:400], local_uploaded_notes[:400]]),
            out_dir=root / "generated_emoticon",
        )

        trend_signal_json = root / "v68_abstract_trend_signals.json"
        trend_signal_json.write_text(json.dumps(trend, ensure_ascii=False, indent=2), encoding="utf-8")

        feedback_memory = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "satisfaction_score": satisfaction_score,
            "preferred_motion": preferred_motion,
            "selected_style": selected_style,
            "selected_suggestions": suggestion_map,
            "feedback_action": feedback_action,
            "user_feedback": user_feedback[:2000],
        }
        feedback_memory_json = root / "v68_feedback_memory.json"
        feedback_memory_json.write_text(json.dumps(feedback_memory, ensure_ascii=False, indent=2), encoding="utf-8")

        evolution_plan = {
            "version": "68.0.0",
            "next_generation_policy": {
                "apply_user_preference": True,
                "preserve_identity_lock": True,
                "generate_static_32_plan": True,
                "generate_animated_24_plan": True,
                "show_gif_inline": True,
                "compare_motion_variants": True,
                "online_signals": "abstract_only",
                "paid_api_calls": "blocked_by_default",
            },
            "next_actions": [
                feedback_action,
                "다음 생성 시 짧은 문구/굵은 외곽선/미니 리액션성을 우선 적용",
                "반려/판매/발신 엑셀 데이터가 있으면 품질 가중치에 추가 반영",
                "제출 전 공식 카카오 스튜디오 규격을 다시 확인",
            ],
            "risk_control": {
                "forbidden_hits": trend.get("risk_hits", []),
                "allow_generation": len(trend.get("risk_hits", [])) == 0,
                "if_risk_found": "특정 캐릭터명/복제 의도 제거 후 재생성 필요",
            },
        }
        evolution_plan_json = root / "v68_evolution_plan.json"
        evolution_plan_json.write_text(json.dumps(evolution_plan, ensure_ascii=False, indent=2), encoding="utf-8")

        quality_score_csv = root / "v68_quality_scores.csv"
        with quality_score_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["score_key", "score", "meaning"])
            writer.writeheader()
            for k, v in scores.items():
                writer.writerow({"score_key": k, "score": int(v), "meaning": "0-100 internal quality evolution score"})

        db_path = root / "v68_quality_history.sqlite3"
        self._store_learning_data(
            db_path=db_path,
            project_name=project_name,
            style=selected_style,
            concept=concept_text,
            satisfaction=satisfaction_score,
            scores=scores,
            package_path=v67_result.package_zip_path,
            feedback_text=user_feedback,
            selected_motion=preferred_motion,
        )

        prompt_template_path = root / "v68_next_generation_prompt.md"
        prompt_template_path.write_text(
            "\n".join([
                "# v68 다음 생성 프롬프트 템플릿",
                "",
                f"프로젝트: {project_name}",
                f"기본 콘셉트: {concept_text}",
                f"선호 스타일: {selected_style}",
                f"대표 문구: {main_phrase}",
                f"선호 모션: {preferred_motion}",
                "",
                "## 반영할 추상 신호",
                *[f"- {r}" for r in trend.get("recommendations", [])],
                "",
                "## 금지",
                "- 기존 인기 캐릭터 외형/문구/애니메이션 복제 금지",
                "- API 키 원문 저장 금지",
                "- 유료 API 자동 호출 금지",
            ]),
            encoding="utf-8",
        )

        context = {
            "project_name": project_name,
            "concept_text": concept_text,
            "selected_style": selected_style,
            "satisfaction_score": satisfaction_score,
            "recommendations": trend.get("recommendations", []),
            "static_png_b64": self._b64(Path(v67_result.static_png)),
            "animated_gif_b64": self._b64(Path(v67_result.animated_preview_gif)),
            "evolution_scores": scores,
            "abstract_trend_json": json.dumps(trend, ensure_ascii=False, indent=2),
            "safety_notes": self.DEFAULT_SAFETY_NOTES,
        }
        html_report = root / "v68_continuous_quality_evolution_report.html"
        self._render_template(html_report, context)

        package_zip = root / "v68_continuous_quality_evolution_package.zip"
        written: set[str] = set()
        def add_to_zip(zf: zipfile.ZipFile, item: Path) -> None:
            if not item.exists():
                return
            arcname = item.name
            if arcname in written:
                return
            zf.write(item, arcname)
            written.add(arcname)

        with zipfile.ZipFile(package_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in [
                trend_signal_json,
                feedback_memory_json,
                evolution_plan_json,
                quality_score_csv,
                db_path,
                prompt_template_path,
                html_report,
                Path(v67_result.static_png),
                Path(v67_result.animated_preview_gif),
                Path(v67_result.contact_sheet_png),
                Path(v67_result.static_32_plan_csv),
                Path(v67_result.animated_24_plan_csv),
            ]:
                add_to_zip(z, p)
            for variant in v67_result.motion_variants[:6]:
                add_to_zip(z, Path(variant.get("path", "")))
            v67_zip = Path(v67_result.package_zip_path)
            add_to_zip(z, v67_zip)

        checksum = self._checksum(package_zip)
        return V68EvolutionReport(
            project_name=project_name,
            output_dir=str(root),
            source_v67_package=v67_result.package_zip_path,
            trend_signal_json=str(trend_signal_json),
            quality_history_db=str(db_path),
            quality_score_csv=str(quality_score_csv),
            feedback_memory_json=str(feedback_memory_json),
            evolution_plan_json=str(evolution_plan_json),
            html_report_path=str(html_report),
            prompt_template_path=str(prompt_template_path),
            package_zip_path=str(package_zip),
            static_png=v67_result.static_png,
            animated_preview_gif=v67_result.animated_preview_gif,
            motion_variants=v67_result.motion_variants,
            quality_scores=v67_result.quality_scores,
            evolution_scores=scores,
            abstract_trend_signals=trend,
            safety_notes=self.DEFAULT_SAFETY_NOTES,
            checksum_sha256=checksum,
        )
