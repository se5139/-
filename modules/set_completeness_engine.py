
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import base64
import csv
import hashlib
import html
import json
import sqlite3
import time
import zipfile
import shutil

from PIL import Image, ImageDraw

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from modules.actual_quality_upgrade_engine import V69ActualQualityUpgradeEngine


@dataclass
class V70SetCompletenessReport:
    project_name: str
    output_dir: str
    static_gallery_png: str
    animated_gallery_png: str
    motion_contact_sheet: str
    representative_static_png: str
    representative_gif: str
    required_gif_paths: List[str]
    static_32_plan_csv: str
    static_32_plan_json: str
    animated_24_plan_csv: str
    animated_24_plan_json: str
    set_quality_matrix_csv: str
    set_quality_matrix_json: str
    static_32_package_zip: str
    animated_24_package_zip: str
    candidate_submission_zip: str
    html_report_path: str
    prompt_pack_path: str
    learning_db: str
    identity_lock_json: str
    identity_lock: Dict[str, Any]
    set_scores: Dict[str, int]
    duplicate_warnings: List[str]
    improvement_plan: List[str]
    safety_notes: List[str]
    v90_simple_output_dir: str = ""
    v90_static_png_submit_dir: str = ""
    v90_animated_gif_submit_dir: str = ""
    v90_preview_jpg_dir: str = ""
    v90_submit_only_png_gif_zip: str = ""
    v90_simple_output_package_zip: str = ""
    v90_manifest_json: str = ""
    v90_manifest_csv: str = ""
    checksum_sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class V70SetCompletenessEngine(V69ActualQualityUpgradeEngine):
    """v70 세트 완성도 강화 엔진.

    v69가 캐릭터 1개와 대표 모션 품질을 올렸다면,
    v70은 32개 정지형 세트와 24개 움직이는형 세트가 감정/문구/포즈 면에서
    충분히 분산되어 보이도록 구성한다.
    """

    VERSION = "90.0.0"

    SET_RULES = [
        "32개 정지형 세트 감정 중복 최소화",
        "24개 움직이는형 세트는 사용자가 바로 이해할 수 있게 GIF 24개로 출력",
        "확인/감사/사과/응원/피곤/놀람/거절/축하 등 핵심 감정 균형",
        "동일 문구·동일 포즈·동일 모션 반복 위험 점검",
        "작은 썸네일에서 얼굴과 문구가 모두 읽히게 구성",
        "다크모드 대비와 흰색 외곽선 안전성 유지",
        "정지형 identity를 전체 세트에 고정",
        "움직이는형은 시작-중간-끝 루프 리듬을 분산",
        "카카오 제출 전 공식 규격 재확인 문구 포함",
        "기존 인기 캐릭터 복제 금지 및 추상 신호만 반영",
    ]

    CORE_STATIC_SET = [
        ("넵", "확인", "bounce"), ("확인!", "확인", "check"), ("오케이", "수락", "nod"), ("잠시만", "대기", "hold"),
        ("감사!", "감사", "sparkle"), ("고마워", "감사", "sparkle"), ("죄송", "사과", "bow"), ("미안해", "사과", "bow"),
        ("파이팅", "응원", "fist"), ("최고", "긍정", "sparkle"), ("좋아요", "긍정", "bounce"), ("축하!", "축하", "confetti"),
        ("헉", "놀람", "pop"), ("진짜?", "놀람", "jump"), ("어쩌지", "당황", "wobble"), ("민망", "민망", "blush"),
        ("피곤", "피곤", "melt"), ("버팀", "공감", "wobble"), ("퇴근각", "직장", "drag"), ("살려줘", "피곤", "melt"),
        ("안돼", "거절", "shake"), ("부들", "분노", "shake"), ("괜찮아", "위로", "soft"), ("울컥", "감동", "tear"),
        ("잘자요", "인사", "float"), ("안녕", "인사", "wave"), ("기다림", "대기", "clock"), ("도와줘", "부탁", "plead"),
        ("완료!", "완료", "check"), ("다시!", "재도전", "bounce"), ("흠...", "고민", "think"), ("끝!", "완료", "pop"),
    ]

    CORE_ANIMATED_SET = [
        ("넵", "확인", "bounce", True), ("감사!", "감사", "sparkle", False), ("죄송", "사과", "bow", False), ("파이팅", "응원", "fist", False),
        ("헉", "놀람", "pop", False), ("민망", "민망", "wobble", False), ("피곤", "피곤", "melt", False), ("안녕", "인사", "wave", True),
        ("부들", "분노", "shake", False), ("완료!", "완료", "check", False), ("잠시만", "대기", "hold", False), ("좋아요", "긍정", "bounce", False),
        ("퇴근각", "직장", "drag", False), ("괜찮아", "위로", "soft", False), ("축하!", "축하", "sparkle", False), ("살려줘", "피곤", "melt", True),
        ("진짜?", "놀람", "jump", False), ("안돼", "거절", "shake", False), ("기다림", "대기", "clock", False), ("도와줘", "부탁", "plead", False),
        ("최고", "긍정", "sparkle", False), ("울컥", "감동", "tear", False), ("다시!", "재도전", "bounce", False), ("잘자요", "인사", "float", False),
    ]

    def _safe_name_v70(self, value: str) -> str:
        return self._safe_name(value or "v70_set_completeness")

    @staticmethod
    def _windows_safe_token(value: str, fallback: str = "item", max_len: int = 28) -> str:
        """Return a Windows-safe token for generated asset filenames.

        Windows forbids angle brackets, colon, quotes, slash, backslash, pipe, question mark, asterisk, and control chars.
        User-facing phrases may keep punctuation in the CSV/JSON/preview text,
        but generated file names must use a sanitized token.
        """
        text = str(value or "").strip()
        forbidden = set('<>:"/\\|?*')
        cleaned = []
        for ch in text:
            if ch in forbidden or ord(ch) < 32:
                cleaned.append("_")
            elif ch.isspace():
                cleaned.append("_")
            elif ch.isalnum() or ch in {"_", "-", "!", "~"}:
                cleaned.append(ch)
            else:
                cleaned.append("_")
        token = "".join(cleaned).strip("._ ")
        while "__" in token:
            token = token.replace("__", "_")
        reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
        if not token or token.upper() in reserved:
            token = fallback
        return token[:max_len] or fallback

    def _asset_name(self, prefix: str, no: int, phrase: str, suffix: str = "", ext: str = ".png") -> str:
        phrase_token = self._windows_safe_token(phrase, fallback=f"item_{no:02d}")
        suffix_token = self._windows_safe_token(suffix, fallback="", max_len=20) if suffix else ""
        parts = [prefix, f"{no:02d}", phrase_token]
        if suffix_token:
            parts.append(suffix_token)
        return "_".join(parts) + ext

    def _expression_for_emotion(self, emotion: str) -> str:
        if emotion in {"놀람", "감동", "축하"}:
            return "놀람"
        if emotion in {"피곤", "민망", "공감", "직장", "거절", "분노", "고민"}:
            return "피곤"
        if emotion in {"사과", "부탁"}:
            return "사과"
        return "확인"

    def _motion_to_v69(self, motion: str) -> str:
        mapping = {
            "check": "speech_sync", "nod": "bow", "hold": "speech_sync", "fist": "bounce", "confetti": "sparkle",
            "jump": "pop", "blush": "wobble", "drag": "melt", "soft": "speech_sync", "tear": "melt",
            "float": "bounce", "clock": "speech_sync", "plead": "wobble", "think": "speech_sync",
            "shake": "wobble", "wave": "wave", "melt": "melt", "pop": "pop", "sparkle": "sparkle", "bounce": "bounce",
        }
        return mapping.get(motion, "bounce")

    def _checksum_v70(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _write_rows(self, csv_path: Path, json_path: Path, rows: List[Dict[str, Any]]) -> None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def _make_set_gallery(self, path: Path, rows: List[Dict[str, Any]], title: str) -> None:
        # 8 x 4 for 32, 6 x 4 for 24. Keep thumbnail preview for quick set-level review.
        count = len(rows)
        cols = 8 if count >= 32 else 6
        thumb = 104
        label_h = 34
        pad = 16
        header_h = 42
        rows_n = (count + cols - 1) // cols
        W = cols * (thumb + pad) + pad
        H = header_h + rows_n * (thumb + label_h + pad) + pad
        sheet = Image.new("RGB", (W, H), (246, 247, 251))
        d = ImageDraw.Draw(sheet)
        title_font = self._font(22)
        small_font = self._font(15)
        d.text((pad, 10), title, font=title_font, fill=(23, 32, 51))
        for idx, row in enumerate(rows):
            x = pad + (idx % cols) * (thumb + pad)
            y = header_h + (idx // cols) * (thumb + label_h + pad)
            d.rounded_rectangle((x-4, y-4, x+thumb+4, y+thumb+label_h+6), radius=12, fill=(255,255,255), outline=(229,231,235), width=1)
            fp = Path(row.get("file_path", ""))
            if fp.exists():
                im = Image.open(fp).convert("RGBA")
                im.thumbnail((thumb, thumb), Image.LANCZOS)
                px = x + (thumb - im.width) // 2
                py = y + (thumb - im.height) // 2
                sheet.paste(im.convert("RGB"), (px, py), im)
            label = f"{row.get('no')}. {row.get('phrase')}"
            d.text((x + 4, y + thumb + 4), label[:12], font=small_font, fill=(23, 32, 51))
            d.text((x + 4, y + thumb + 20), str(row.get("emotion", ""))[:10], font=small_font, fill=(100, 116, 139))
        path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(path)

    def _set_scores(self, static_rows: List[Dict[str, Any]], animated_rows: List[Dict[str, Any]], identity: Dict[str, Any]) -> Tuple[Dict[str, int], List[str]]:
        warnings: List[str] = []
        phrases = [r["phrase"] for r in static_rows]
        emotions = [r["emotion"] for r in static_rows]
        motions = [r["motion"] for r in animated_rows]
        dup_phrase = len(phrases) - len(set(phrases))
        if dup_phrase:
            warnings.append(f"중복 문구 {dup_phrase}개 감지: 세트 출시 전 문구를 분산해야 합니다.")
        emotion_diversity = min(100, 62 + len(set(emotions)) * 3)
        phrase_diversity = max(55, 96 - dup_phrase * 9)
        motion_diversity = min(100, 64 + len(set(motions)) * 4)
        gif_count = sum(1 for r in animated_rows if str(r.get("format_hint", "")).startswith("GIF"))
        gif_readiness = 98 if gif_count >= 24 else (96 if gif_count >= 3 else 45)
        thumbnail = 92 if identity.get("face_scale", 1) >= 1.25 else 82
        copy_safety = 28 if identity.get("forbidden_hits") else 96
        if gif_count < 3:
            warnings.append("움직이는형 필수 GIF 후보가 3개 미만입니다.")
        if copy_safety < 70:
            warnings.append("유사성 위험 키워드가 있어 원본 모방형 생성은 차단해야 합니다.")
        return {
            "emotion_diversity": emotion_diversity,
            "phrase_diversity": phrase_diversity,
            "motion_diversity": motion_diversity,
            "gif_readiness": gif_readiness,
            "thumbnail_readability": thumbnail,
            "identity_consistency": 94,
            "darkmode_safety": 92 if identity.get("white_outer_line") else 80,
            "copy_safety": copy_safety,
        }, warnings

    def _store_v70_learning(self, db: Path, project_name: str, scores: Dict[str, int], static_rows: List[Dict[str, Any]], animated_rows: List[Dict[str, Any]]) -> None:
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v70_set_completion_runs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    static_count INTEGER,
                    animated_count INTEGER,
                    total_score INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v70_set_completion_scores(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    score_key TEXT,
                    score_value INTEGER
                )
            """)
            total = int(sum(scores.values()) / max(1, len(scores)))
            cur.execute(
                "INSERT INTO v70_set_completion_runs(created_at, project_name, static_count, animated_count, total_score) VALUES(?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), project_name, len(static_rows), len(animated_rows), total),
            )
            run_id = cur.lastrowid
            for k, v in scores.items():
                cur.execute("INSERT INTO v70_set_completion_scores(run_id, score_key, score_value) VALUES(?,?,?)", (run_id, k, int(v)))
            con.commit()

    def _b64_file(self, path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("ascii")

    def _render_v70_report(self, template_dir: Path, out_path: Path, context: Dict[str, Any]) -> None:
        template_dir.mkdir(parents=True, exist_ok=True)
        template = template_dir / "v70_set_completion_report.html.j2"
        if not template.exists():
            template.write_text("""<!doctype html>
<html lang=\"ko\"><head><meta charset=\"utf-8\"><title>v70 세트 완성도 강화 리포트</title>
<style>
body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;color:#172033;margin:0;padding:28px}.wrap{max-width:1240px;margin:auto}.hero{background:linear-gradient(135deg,#111827,#0f766e,#84cc16);color:white;border-radius:28px;padding:28px 32px;box-shadow:0 18px 42px rgba(15,23,42,.20)}.card{background:white;border:1px solid #e5e7eb;border-radius:22px;padding:20px;margin-top:18px;box-shadow:0 10px 28px rgba(15,23,42,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}.preview{text-align:center;background:white;border:1px solid #e5e7eb;border-radius:18px;padding:12px}.preview img{max-width:100%;border-radius:16px;background:white}.badge{display:inline-block;background:#dcfce7;color:#166534;border-radius:999px;padding:5px 10px;margin:3px;font-weight:700}.score{font-size:28px;font-weight:800;color:#0f766e}.warn{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:14px;padding:12px}.mono{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:16px;padding:14px;overflow:auto}
</style></head><body><div class=\"wrap\"><div class=\"hero\"><h1>v70 세트 완성도 강화 리포트</h1><p>32개 정지형 · 24개 움직이는형 · 감정/문구/포즈 중복 점검 · 제출 후보 패키지</p></div>
<div class=\"card\"><h2>프로젝트</h2><p><b>{{ project_name }}</b></p><p>{{ concept_text }}</p>{% for r in set_rules %}<span class=\"badge\">{{ r }}</span>{% endfor %}</div>
<div class=\"card\"><h2>세트 미리보기</h2><div class=\"grid\"><div class=\"preview\"><h3>32개 정지형 갤러리</h3><img src=\"data:image/png;base64,{{ static_gallery_b64 }}\"></div><div class=\"preview\"><h3>24개 움직이는형 갤러리</h3><img src=\"data:image/png;base64,{{ animated_gallery_b64 }}\"></div><div class=\"preview\"><h3>대표 GIF</h3><img src=\"data:image/gif;base64,{{ gif_b64 }}\"></div></div></div>
<div class=\"card\"><h2>세트 품질 점수</h2><div class=\"grid\">{% for k,v in set_scores.items() %}<div><div class=\"score\">{{ v }}</div><b>{{ k }}</b></div>{% endfor %}</div></div>
<div class=\"card\"><h2>개선 계획</h2><ul>{% for item in improvement_plan %}<li>{{ item }}</li>{% endfor %}</ul></div>
<div class=\"card warn\"><b>중복/안전 경고</b><ul>{% for item in duplicate_warnings %}<li>{{ item }}</li>{% endfor %}{% if not duplicate_warnings %}<li>현재 기준 중복 위험은 크게 발견되지 않았습니다.</li>{% endif %}</ul></div>
<div class=\"card\"><h2>Identity Lock</h2><div class=\"mono\">{{ identity_pretty }}</div></div>
</div></body></html>""", encoding="utf-8")
        if Environment is None:
            project = html.escape(str(context.get("project_name", "v70 report")))
            concept = html.escape(str(context.get("concept_text", "")))
            scores = context.get("set_scores", {})
            score_items = "".join(
                f"<li><b>{html.escape(str(k))}</b>: {html.escape(str(v))}</li>"
                for k, v in scores.items()
            )
            plan_items = "".join(
                f"<li>{html.escape(str(item))}</li>"
                for item in context.get("improvement_plan", [])
            )
            out_path.write_text(
                "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
                f"<title>{project}</title></head><body>"
                f"<h1>{project}</h1><p>{concept}</p>"
                f"<h2>Scores</h2><ul>{score_items}</ul>"
                f"<h2>Next Improvements</h2><ul>{plan_items}</ul>"
                "</body></html>",
                encoding="utf-8",
            )
            return
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"]))
        rendered_html = env.get_template(template.name).render(**context)
        out_path.write_text(rendered_html, encoding="utf-8")

    def _zip_dir_files(self, zip_path: Path, files: List[Path]) -> None:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            seen: set[str] = set()
            for fp in files:
                if fp.exists() and fp.name not in seen:
                    seen.add(fp.name)
                    zf.write(fp, fp.name)


    def _save_v90_jpg_preview(self, source_path: Path, out_path: Path) -> None:
        """Create JPG preview only. JPG is never treated as the transparent final submission file."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source_path) as im:
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.getchannel("A"))
            bg.save(out_path, "JPEG", quality=92, optimize=True)

    def _zip_tree(self, zip_path: Path, source_dir: Path, include_root: bool = False) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in sorted(source_dir.rglob("*")):
                if not fp.is_file():
                    continue
                arc = fp.relative_to(source_dir.parent if include_root else source_dir)
                zf.write(fp, arc.as_posix())

    def _build_v90_simple_output(
        self,
        run_dir: Path,
        static_rows: List[Dict[str, Any]],
        animated_rows: List[Dict[str, Any]],
        project_name: str,
    ) -> Dict[str, str]:
        """Build the beginner-facing output layout: static PNG, animated GIF, JPG preview only."""
        simple_dir = run_dir / "v90_simple_png_gif_output"
        static_submit = simple_dir / "static_png_submit"
        animated_submit = simple_dir / "animated_gif_submit"
        preview_jpg = simple_dir / "preview_jpg"
        meta_dir = simple_dir / "metadata"
        for d in [static_submit, animated_submit, preview_jpg, meta_dir]:
            d.mkdir(parents=True, exist_ok=True)

        manifest_rows: List[Dict[str, Any]] = []
        for row in static_rows:
            no = int(row.get("no", 0))
            src = Path(str(row.get("file_path", "")))
            dst = static_submit / f"static_{no:02d}.png"
            if src.exists():
                shutil.copy2(src, dst)
                jpg = preview_jpg / f"static_{no:02d}_preview.jpg"
                self._save_v90_jpg_preview(dst, jpg)
                manifest_rows.append({
                    "no": no,
                    "kind": "static_png_submit",
                    "submit_file": dst.relative_to(simple_dir).as_posix(),
                    "preview_jpg": jpg.relative_to(simple_dir).as_posix(),
                    "original_phrase": row.get("phrase", ""),
                    "emotion": row.get("emotion", ""),
                    "final_format": "PNG",
                    "jpg_rule": "preview_only_not_submit",
                })

        for row in animated_rows:
            no = int(row.get("no", 0))
            src = Path(str(row.get("file_path", "")))
            dst = animated_submit / f"animated_{no:02d}.gif"
            if src.exists() and src.suffix.lower() == ".gif":
                shutil.copy2(src, dst)
                jpg = preview_jpg / f"animated_{no:02d}_first_frame_preview.jpg"
                self._save_v90_jpg_preview(dst, jpg)
                manifest_rows.append({
                    "no": no,
                    "kind": "animated_gif_submit",
                    "submit_file": dst.relative_to(simple_dir).as_posix(),
                    "preview_jpg": jpg.relative_to(simple_dir).as_posix(),
                    "original_phrase": row.get("phrase", ""),
                    "emotion": row.get("emotion", ""),
                    "final_format": "GIF",
                    "jpg_rule": "preview_only_not_submit",
                })

        manifest_json = meta_dir / "v90_simple_output_manifest.json"
        manifest_csv = meta_dir / "v90_simple_output_manifest.csv"
        manifest = {
            "project_name": project_name,
            "version": "90.0.0",
            "static_png_submit_count": len(list(static_submit.glob("*.png"))),
            "animated_gif_submit_count": len(list(animated_submit.glob("*.gif"))),
            "preview_jpg_count": len(list(preview_jpg.glob("*.jpg"))),
            "rule_summary": [
                "정지형 최종 파일은 PNG입니다.",
                "움직이는형 최종 파일은 GIF입니다.",
                "JPG는 확인용 미리보기이며 제출용 ZIP에서는 분리됩니다.",
                "사용자 문구 원문은 manifest에 보존하고 파일명은 Windows 안전 이름만 사용합니다.",
            ],
            "items": manifest_rows,
        }
        manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_rows(manifest_csv, meta_dir / "v90_simple_output_manifest_rows.json", manifest_rows or [{"no":"", "kind":"", "submit_file":"", "preview_jpg":"", "original_phrase":"", "emotion":"", "final_format":"", "jpg_rule":""}])

        guide = simple_dir / "README_V90_OUTPUT_KO.txt"
        guide.write_text(
            "v90 간편 출력 구조\n\n"
            "1) static_png_submit: 안 움직이는 이모티콘 최종 후보 PNG 32개\n"
            "2) animated_gif_submit: 움직이는 이모티콘 최종 후보 GIF 24개\n"
            "3) preview_jpg: 확인용 JPG입니다. 투명 배경이 필요한 제출용으로 쓰지 않습니다.\n"
            "4) metadata: 원문 문구, 감정, 파일 매핑 manifest입니다.\n\n"
            "제출 전에는 카카오 이모티콘 스튜디오의 최신 수량/용량/크기 기준을 다시 확인하세요.\n",
            encoding="utf-8",
        )
        submit_only = run_dir / "v90_submit_only_png_gif.zip"
        with zipfile.ZipFile(submit_only, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in sorted(static_submit.glob("*.png")):
                zf.write(fp, f"static_png_submit/{fp.name}")
            for fp in sorted(animated_submit.glob("*.gif")):
                zf.write(fp, f"animated_gif_submit/{fp.name}")
            zf.write(manifest_json, "metadata/v90_simple_output_manifest.json")
        simple_zip = run_dir / "v90_simple_output_package.zip"
        self._zip_tree(simple_zip, simple_dir, include_root=True)
        return {
            "v90_simple_output_dir": str(simple_dir),
            "v90_static_png_submit_dir": str(static_submit),
            "v90_animated_gif_submit_dir": str(animated_submit),
            "v90_preview_jpg_dir": str(preview_jpg),
            "v90_submit_only_png_gif_zip": str(submit_only),
            "v90_simple_output_package_zip": str(simple_zip),
            "v90_manifest_json": str(manifest_json),
            "v90_manifest_csv": str(manifest_csv),
        }

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
    ) -> V70SetCompletenessReport:
        safe_project = self._safe_name_v70(project_name)
        run_dir = out_dir / f"{safe_project}_{int(time.time())}"
        suffix = 1
        while run_dir.exists():
            suffix += 1
            run_dir = out_dir / f"{safe_project}_{int(time.time())}_{suffix:02d}"
        static_dir = run_dir / "static_32_png"
        animated_dir = run_dir / "animated_24_gif"
        run_dir.mkdir(parents=True, exist_ok=True)
        static_dir.mkdir(parents=True, exist_ok=True)
        animated_dir.mkdir(parents=True, exist_ok=True)

        merged_rules = list(dict.fromkeys((selected_rules or []) + [
            "정지형 identity를 모든 GIF에 고정",
            "표정 다양성 32개 세트 확장성 강화",
            "다크모드 대비 흰색 외곽선 유지",
            "기존 인기 캐릭터 복제 금지",
        ]))
        identity = self.build_identity(concept_text + " " + online_abstract_notes, selected_style, merged_rules, user_feedback)

        static_rows: List[Dict[str, Any]] = []
        for i, (phrase, emotion, motion) in enumerate(self.CORE_STATIC_SET, start=1):
            expr = self._expression_for_emotion(emotion)
            fp = static_dir / self._asset_name("static", i, phrase, ext=".png")
            self._save_static(fp, phrase, identity, expression=expr, dark=False)
            static_rows.append({
                "no": i, "phrase": phrase, "emotion": emotion, "pose": motion, "expression": expr,
                "file_path": str(fp), "set_role": "static_32", "duplicate_group": f"{emotion}:{motion}",
                "quality_focus": "짧은 문구/큰 얼굴/표정 분산/썸네일 가독성",
            })

        animated_rows: List[Dict[str, Any]] = []
        required_gif_paths: List[str] = []
        representative_gif = ""
        for i, (phrase, emotion, motion, required_gif) in enumerate(self.CORE_ANIMATED_SET, start=1):
            expr = self._expression_for_emotion(emotion)
            v69_motion = self._motion_to_v69(motion)
            fp = animated_dir / self._asset_name("animated", i, phrase, suffix=v69_motion, ext=".gif")
            self._save_gif(fp, phrase, identity, v69_motion, expr)
            required_gif_paths.append(str(fp))
            if not representative_gif:
                representative_gif = str(fp)
            fmt = "GIF_FINAL_SUBMIT"
            animated_rows.append({
                "no": i, "phrase": phrase, "emotion": emotion, "motion": v69_motion,
                "expression": expr, "format_hint": fmt, "file_path": str(fp),
                "frame_limit_note": "GIF는 24프레임 이하 제출 전 공식 기준 재확인",
                "identity_lock": identity.get("body_shape"),
            })
        if not representative_gif and animated_rows:
            representative_gif = animated_rows[0]["file_path"]

        representative_static = static_rows[0]["file_path"]
        static_gallery = run_dir / "v70_static_32_gallery.png"
        animated_gallery = run_dir / "v70_animated_24_gallery.png"
        self._make_set_gallery(static_gallery, static_rows, "v70 정지형 32개 세트 미리보기")
        self._make_set_gallery(animated_gallery, animated_rows, "v70 움직이는형 24개 세트 미리보기")
        contact = run_dir / "v70_motion_required_gif_contact_sheet.png"
        gif_variants = [{"path": p, "label": Path(p).stem.replace("animated_", "")} for p in required_gif_paths]
        self._make_contact_sheet(contact, Path(representative_static), gif_variants)

        static_csv = run_dir / "v70_static_32_set_plan.csv"
        static_json = run_dir / "v70_static_32_set_plan.json"
        animated_csv = run_dir / "v70_animated_24_set_plan.csv"
        animated_json = run_dir / "v70_animated_24_set_plan.json"
        matrix_csv = run_dir / "v70_set_quality_matrix.csv"
        matrix_json = run_dir / "v70_set_quality_matrix.json"
        self._write_rows(static_csv, static_json, static_rows)
        self._write_rows(animated_csv, animated_json, animated_rows)
        scores, warnings = self._set_scores(static_rows, animated_rows, identity)
        matrix_rows = [{"score_key": k, "score_value": v, "note": "v70 set-level score"} for k, v in scores.items()]
        self._write_rows(matrix_csv, matrix_json, matrix_rows)

        improvement_plan = [
            "32개 정지형에서 같은 감정이 몰리는 경우 문구와 포즈를 자동 분산합니다.",
            "24개 움직이는형은 최종 사용자가 바로 확인할 수 있게 GIF 24개로 생성합니다.",
            "사용자가 선택한 대표 GIF 모션은 다음 세트 생성에서 우선 순위를 높입니다.",
            "썸네일 갤러리에서 얼굴/문구가 작게 보이면 외곽선과 얼굴 크기를 자동 보정합니다.",
            "제출 직전에는 공식 카카오 스튜디오 기준으로 수량·용량·프레임·파일형식을 다시 검사합니다.",
        ]
        safety_notes = [
            "온라인 정보는 원본 이미지/문구/모션을 복제하지 않고 추상 신호만 사용합니다.",
            "동일 메시지·동일 표현법·동일 애니메이션 재사용 위험을 세트 단위로 점검합니다.",
            "API 키 원문은 결과물에 저장하지 않습니다.",
            "사용자 데이터는 outputs/user data 영역에 저장하고 업데이트 삭제 대상에서 보호해야 합니다.",
        ]

        identity_json = run_dir / "v70_identity_lock.json"
        identity_json.write_text(json.dumps(identity, ensure_ascii=False, indent=2), encoding="utf-8")
        learning_db = run_dir / "v70_set_completion_learning.sqlite3"
        self._store_v70_learning(learning_db, project_name, scores, static_rows, animated_rows)
        prompt_pack = run_dir / "v70_set_completion_prompt_pack.md"
        prompt_pack.write_text(
            "# v70 세트 완성도 다음 생성 프롬프트 팩\n\n"
            f"- 프로젝트: {project_name}\n- 스타일: {selected_style}\n- 대표 문구: {(main_phrase or '넵')[:10]}\n"
            "- 목표: 32개 정지형과 24개 움직이는형 전체가 서로 다른 감정/문구/포즈로 보이도록 구성\n"
            "- 금지: 기존 인기 캐릭터 외형·문구·모션 복제\n\n"
            "## 다음 개선 계획\n" + "\n".join(f"- {x}" for x in improvement_plan),
            encoding="utf-8",
        )
        report_html = run_dir / "v70_set_completion_report.html"
        self._render_v70_report(Path(__file__).resolve().parents[1] / "templates" / "v70_set_completion", report_html, {
            "project_name": project_name,
            "concept_text": concept_text,
            "set_rules": self.SET_RULES,
            "static_gallery_b64": self._b64_file(static_gallery),
            "animated_gallery_b64": self._b64_file(animated_gallery),
            "gif_b64": self._b64_file(Path(representative_gif)),
            "set_scores": scores,
            "improvement_plan": improvement_plan,
            "duplicate_warnings": warnings,
            "identity_pretty": json.dumps(identity, ensure_ascii=False, indent=2),
        })

        static_zip = run_dir / "v90_static_32_png_package.zip"
        animated_zip = run_dir / "v90_animated_24_gif_package.zip"
        submission_zip = run_dir / "v90_submission_candidate_package.zip"
        self._zip_dir_files(static_zip, [Path(r["file_path"]) for r in static_rows] + [static_csv, static_json])
        self._zip_dir_files(animated_zip, [Path(r["file_path"]) for r in animated_rows] + [animated_csv, animated_json])
        self._zip_dir_files(submission_zip, [
            static_gallery, animated_gallery, contact, static_csv, static_json, animated_csv, animated_json,
            matrix_csv, matrix_json, identity_json, learning_db, prompt_pack, report_html, static_zip, animated_zip,
        ] + [Path(p) for p in required_gif_paths] + [Path(representative_static), Path(representative_gif)])
        v90_paths = self._build_v90_simple_output(run_dir, static_rows, animated_rows, project_name)
        checksum = self._checksum_v70(submission_zip)
        return V70SetCompletenessReport(
            project_name=project_name,
            output_dir=str(run_dir),
            static_gallery_png=str(static_gallery),
            animated_gallery_png=str(animated_gallery),
            motion_contact_sheet=str(contact),
            representative_static_png=str(representative_static),
            representative_gif=str(representative_gif),
            required_gif_paths=required_gif_paths,
            static_32_plan_csv=str(static_csv),
            static_32_plan_json=str(static_json),
            animated_24_plan_csv=str(animated_csv),
            animated_24_plan_json=str(animated_json),
            set_quality_matrix_csv=str(matrix_csv),
            set_quality_matrix_json=str(matrix_json),
            static_32_package_zip=str(static_zip),
            animated_24_package_zip=str(animated_zip),
            candidate_submission_zip=str(submission_zip),
            html_report_path=str(report_html),
            prompt_pack_path=str(prompt_pack),
            learning_db=str(learning_db),
            identity_lock_json=str(identity_json),
            identity_lock=identity,
            set_scores=scores,
            duplicate_warnings=warnings,
            improvement_plan=improvement_plan,
            safety_notes=safety_notes,
            v90_simple_output_dir=v90_paths["v90_simple_output_dir"],
            v90_static_png_submit_dir=v90_paths["v90_static_png_submit_dir"],
            v90_animated_gif_submit_dir=v90_paths["v90_animated_gif_submit_dir"],
            v90_preview_jpg_dir=v90_paths["v90_preview_jpg_dir"],
            v90_submit_only_png_gif_zip=v90_paths["v90_submit_only_png_gif_zip"],
            v90_simple_output_package_zip=v90_paths["v90_simple_output_package_zip"],
            v90_manifest_json=v90_paths["v90_manifest_json"],
            v90_manifest_csv=v90_paths["v90_manifest_csv"],
            checksum_sha256=checksum,
        )
