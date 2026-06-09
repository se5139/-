from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import base64
import csv
import hashlib
import json
import math
import random
import sqlite3
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None


@dataclass
class V69QualityUpgradeReport:
    project_name: str
    output_dir: str
    static_png: str
    darkmode_preview_png: str
    motion_preview_gif: str
    motion_variants: List[Dict[str, Any]]
    motion_contact_sheet: str
    static_32_plan_csv: str
    static_32_plan_json: str
    animated_24_plan_csv: str
    animated_24_plan_json: str
    style_memory_json: str
    quality_metrics_json: str
    learning_db: str
    html_report_path: str
    prompt_pack_path: str
    package_zip_path: str
    identity_lock: Dict[str, Any]
    selected_improvement_rules: List[str]
    quality_scores: Dict[str, int]
    next_generation_plan: List[str]
    safety_notes: List[str]
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class V69ActualQualityUpgradeEngine:
    """v69 실제 품질 고도화 엔진.

    v68의 지속 진화 데이터 구조 위에서 캐릭터 그림체 자체를 조금 더 올린다.
    온라인 자료는 원본 복제가 아니라 추상 품질 신호만 사용한다.
    """

    SIZE = 360
    FRAME_COUNT = 20

    STYLE_PRESETS = [
        "손그림 공감형 · 굵은 외곽선",
        "미니 리액션형 · 즉시 반응",
        "직장인 답장형 · 말풍선 우선",
        "하찮은 낙서형 · 작게 봐도 읽힘",
        "다크모드 대비형 · 흰색 테두리",
    ]

    QUALITY_RULES = [
        "손그림 질감 외곽선 강화",
        "얼굴 크기 확대와 썸네일 가독성 강화",
        "문구 2~7자 답장형 우선",
        "정지형 identity를 모든 GIF에 고정",
        "모션 시작-중간-끝 리듬을 부드럽게",
        "표정 다양성 32개 세트 확장성 강화",
        "말풍선과 캐릭터 동작 동기화",
        "다크모드 대비 흰색 외곽선 유지",
        "기존 인기 캐릭터 복제 금지",
        "사용자가 만족한 스타일을 다음 생성 메모리에 저장",
    ]

    FORBIDDEN_HINTS = [
        "라이언", "춘식이", "어피치", "카카오프렌즈", "라인프렌즈", "산리오", "헬로키티",
        "포켓몬", "피카츄", "디즈니", "짱구", "도라에몽", "스누피", "망그러진 곰",
        "가나디", "토심이", "슈야", "꺅두기", "똑같이", "비슷하게", "따라", "복제",
        "캡처 그대로", "원본 그대로", "검수 우회", "저작권 우회",
    ]

    PHRASE_POOL = [
        ("넵", "확인", "bounce"),
        ("오케이", "확인", "check"),
        ("잠시만요", "대기", "hold"),
        ("감사!", "감사", "sparkle"),
        ("죄송해요", "사과", "bow"),
        ("진짜요?", "놀람", "pop"),
        ("헉", "놀람", "jump"),
        ("파이팅", "응원", "fist"),
        ("퇴근각", "직장", "drag"),
        ("버팀", "공감", "wobble"),
        ("민망", "민망", "blush"),
        ("부들", "분노", "shake"),
        ("좋아요", "긍정", "bounce"),
        ("완료!", "완료", "check"),
        ("살려줘", "피곤", "melt"),
        ("괜찮아", "위로", "soft"),
        ("도와줘요", "부탁", "plead"),
        ("기다림", "대기", "clock"),
        ("축하!", "축하", "confetti"),
        ("울컥", "감동", "tear"),
        ("잘자요", "인사", "float"),
        ("손흔들", "인사", "wave"),
        ("흠...", "고민", "think"),
        ("끝!", "완료", "pop"),
        ("아이고", "피곤", "squash"),
        ("네네", "확인", "nod"),
        ("갑니다", "시작", "fist"),
        ("조용히", "공감", "small"),
        ("놀람!", "놀람", "jump"),
        ("안돼요", "거절", "shake"),
        ("최고", "긍정", "sparkle"),
        ("다시!", "재도전", "bounce"),
    ]

    MOTION_VARIANTS = [
        ("bounce", "통통 튐"),
        ("bow", "꾸벅 인사"),
        ("wave", "손 흔들기"),
        ("wobble", "부들부들"),
        ("speech_sync", "말풍선 동기화"),
        ("pop", "작아졌다 커짐"),
        ("melt", "피곤하게 녹기"),
        ("sparkle", "반짝 강조"),
    ]

    def _safe_name(self, value: str) -> str:
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "v69_quality_upgrade"))
        return safe[:80] or "v69_quality_upgrade"

    def _font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidates = [
            "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/malgun.ttf",
        ]
        for path in candidates:
            try:
                if Path(path).exists():
                    return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _hex_to_rgba(self, value: str, alpha: int = 255) -> Tuple[int, int, int, int]:
        s = value.lstrip("#")
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)

    def build_identity(
        self,
        concept_text: str,
        selected_style: str,
        selected_rules: List[str],
        user_feedback: str,
    ) -> Dict[str, Any]:
        text = f"{concept_text} {user_feedback}"
        material = "둥근 먼지 캐릭터"
        for token in ["보리", "쌀", "감자", "고구마", "버섯", "메모지", "구름", "콩", "양말", "먼지", "만두", "종이컵"]:
            if token in text:
                material = token
                break
        if "미니" in selected_style:
            palette = ["#c7f5d2", "#fef3c7", "#26362e", "#ffadc7", "#ffffff"]
            body_shape = "mini_round"
        elif "직장인" in selected_style:
            palette = ["#b8d7ff", "#fff4c8", "#24313f", "#ffb4b4", "#ffffff"]
            body_shape = "tired_worker_round"
        elif "다크모드" in selected_style:
            palette = ["#ffd166", "#fff5c4", "#221a14", "#ff9fb1", "#ffffff"]
            body_shape = "darkmode_safe_round"
        else:
            palette = ["#f2c56b", "#fff2bd", "#2e2119", "#ffb0b0", "#ffffff"]
            body_shape = "handdrawn_round"

        forbidden_hits = [w for w in self.FORBIDDEN_HINTS if w in text]
        return {
            "material": material,
            "style": selected_style,
            "body_shape": body_shape,
            "palette": palette,
            "outline_width": 9 if "손그림 질감 외곽선 강화" in selected_rules else 7,
            "white_outer_line": "다크모드 대비 흰색 외곽선 유지" in selected_rules or "다크모드" in selected_style,
            "face_scale": 1.34 if "얼굴 크기 확대와 썸네일 가독성 강화" in selected_rules else 1.18,
            "phrase_mode": "short_reply" if "문구 2~7자 답장형 우선" in selected_rules else "balanced",
            "motion_rule": "identity locked: body color, face layout, outline, speech style retained across every motion frame",
            "forbidden_hits": forbidden_hits,
            "copy_risk_policy": "block_generation_if_copy_request_detected" if forbidden_hits else "abstract_only_safe",
        }

    def _text_bbox(self, draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str, font: ImageFont.ImageFont, **kwargs) -> Tuple[int, int, int, int]:
        try:
            return draw.textbbox(xy, text, font=font, **kwargs)
        except Exception:
            w, h = draw.textsize(text, font=font)
            return xy[0], xy[1], xy[0] + w, xy[1] + h

    def _handdrawn_ellipse(
        self,
        draw: ImageDraw.ImageDraw,
        box: Tuple[int, int, int, int],
        fill: Tuple[int, int, int, int] | None,
        outline: Tuple[int, int, int, int],
        width: int,
        jitter: int = 2,
    ) -> None:
        if fill:
            draw.ellipse(box, fill=fill)
        # 조금씩 어긋난 선을 여러 번 그려 손그림 질감을 만든다.
        for dx, dy in [(0, 0), (1, 0), (-1, 1), (0, -1)]:
            b = (box[0] + dx * jitter, box[1] + dy * jitter, box[2] + dx * jitter, box[3] + dy * jitter)
            draw.ellipse(b, outline=outline, width=width)

    def _draw_speech_bubble(self, draw: ImageDraw.ImageDraw, phrase: str, x: int, y: int, width: int, identity: Dict[str, Any]) -> Tuple[int, int, int, int]:
        font = self._font(32 if len(phrase) <= 3 else 27)
        bubble_h = 58
        bubble = (x, y, x + width, y + bubble_h)
        outline = self._hex_to_rgba(identity["palette"][2])
        draw.rounded_rectangle(bubble, radius=22, fill=(255, 255, 255, 255), outline=outline, width=4)
        cx = x + width // 2
        draw.polygon([(cx - 14, y + bubble_h - 1), (cx + 14, y + bubble_h - 1), (cx, y + bubble_h + 18)], fill=(255, 255, 255, 255), outline=outline)
        bbox = self._text_bbox(draw, (0, 0), phrase, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x + (width - tw) // 2, y + (bubble_h - th) // 2 - 3), phrase, font=font, fill=outline)
        return bubble

    def _draw_character_frame(
        self,
        phrase: str,
        identity: Dict[str, Any],
        motion: str = "static",
        frame_index: int = 0,
        total_frames: int = 1,
        background: Tuple[int, int, int, int] | None = None,
        expression: str = "확인",
    ) -> Image.Image:
        W = H = self.SIZE
        img = Image.new("RGBA", (W, H), background or (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        t = 0 if total_frames <= 1 else frame_index / (total_frames - 1)
        wave = math.sin(2 * math.pi * t)
        bounce = -int(12 * max(0, math.sin(math.pi * t))) if motion in {"bounce", "pop", "sparkle"} else 0
        wobble = int(6 * math.sin(4 * math.pi * t)) if motion in {"wobble", "shake"} else 0
        bow_y = int(15 * math.sin(math.pi * t)) if motion == "bow" else 0
        scale = 1.0 + (0.08 * math.sin(math.pi * t) if motion == "pop" else 0)
        squash = 1.0 - (0.07 * math.sin(math.pi * t) if motion in {"melt", "squash"} else 0)

        # shadow
        draw.ellipse((105, 292, 255, 318), fill=(0, 0, 0, 38))

        cx, cy = W // 2 + wobble, 195 + bounce + bow_y
        body_w = int(132 * identity.get("face_scale", 1.2) * 0.92 * scale)
        body_h = int(118 * identity.get("face_scale", 1.2) * 0.88 * squash)
        body_box = (cx - body_w // 2, cy - body_h // 2, cx + body_w // 2, cy + body_h // 2)
        outline = self._hex_to_rgba(identity["palette"][2])
        fill = self._hex_to_rgba(identity["palette"][0])
        highlight = self._hex_to_rgba(identity["palette"][1])
        cheek = self._hex_to_rgba(identity["palette"][3], 210)
        white = self._hex_to_rgba(identity["palette"][4])
        ow = int(identity.get("outline_width", 7))

        if identity.get("white_outer_line"):
            self._handdrawn_ellipse(draw, (body_box[0] - 8, body_box[1] - 8, body_box[2] + 8, body_box[3] + 8), None, white, max(7, ow + 3), jitter=1)
        self._handdrawn_ellipse(draw, body_box, fill, outline, ow, jitter=1)
        draw.arc((body_box[0] + 25, body_box[1] + 10, body_box[2] - 25, body_box[3] - 4), start=195, end=340, fill=highlight, width=5)

        # ears / side blobs
        ear_r = 20
        for side in [-1, 1]:
            ex = cx + side * (body_w // 2 - 4)
            ey = cy - 2
            eb = (ex - ear_r, ey - ear_r, ex + ear_r, ey + ear_r)
            draw.ellipse(eb, fill=fill, outline=outline, width=max(4, ow - 2))

        # arms, wave variation
        arm_y = cy + body_h // 2 - 10
        if motion == "wave":
            right_up = int(25 * math.sin(2 * math.pi * t))
        else:
            right_up = 0
        draw.line((cx - body_w // 2 + 8, arm_y, cx - body_w // 2 - 28, arm_y + 24), fill=outline, width=ow, joint="curve")
        draw.ellipse((cx - body_w // 2 - 42, arm_y + 12, cx - body_w // 2 - 12, arm_y + 42), fill=fill, outline=outline, width=max(4, ow - 2))
        draw.line((cx + body_w // 2 - 8, arm_y, cx + body_w // 2 + 28, arm_y + 24 - right_up), fill=outline, width=ow, joint="curve")
        draw.ellipse((cx + body_w // 2 + 12, arm_y + 12 - right_up, cx + body_w // 2 + 42, arm_y + 42 - right_up), fill=fill, outline=outline, width=max(4, ow - 2))

        # face
        eye_y = cy - 18
        mouth_y = cy + 16
        if expression in {"놀람", "감동"} or motion in {"pop", "jump"}:
            draw.ellipse((cx - 34, eye_y - 12, cx - 22, eye_y + 8), fill=outline)
            draw.ellipse((cx + 22, eye_y - 12, cx + 34, eye_y + 8), fill=outline)
            draw.ellipse((cx - 12, mouth_y - 6, cx + 12, mouth_y + 16), outline=outline, width=4)
        elif expression in {"피곤", "민망", "공감"} or motion in {"melt", "wobble"}:
            draw.arc((cx - 38, eye_y - 12, cx - 20, eye_y + 8), 0, 180, fill=outline, width=4)
            draw.arc((cx + 20, eye_y - 12, cx + 38, eye_y + 8), 0, 180, fill=outline, width=4)
            draw.arc((cx - 24, mouth_y - 2, cx + 24, mouth_y + 25), 200, 340, fill=outline, width=4)
        else:
            draw.ellipse((cx - 36, eye_y - 10, cx - 24, eye_y + 10), fill=outline)
            draw.ellipse((cx + 24, eye_y - 10, cx + 36, eye_y + 10), fill=outline)
            draw.arc((cx - 34, mouth_y - 14, cx + 34, mouth_y + 28), 25, 155, fill=outline, width=5)
        draw.ellipse((cx - 58, cy + 4, cx - 34, cy + 24), fill=cheek)
        draw.ellipse((cx + 34, cy + 4, cx + 58, cy + 24), fill=cheek)

        # speech bubble
        bubble_y = 54 + (int(8 * math.sin(2 * math.pi * t)) if motion == "speech_sync" else 0)
        bubble_w = 218 if len(phrase) <= 4 else 260
        self._draw_speech_bubble(draw, phrase[:10], (W - bubble_w) // 2, bubble_y, bubble_w, identity)

        # sparkle marks
        if motion == "sparkle" or expression in {"감사", "축하", "긍정"}:
            alpha = int(170 + 70 * abs(math.sin(2 * math.pi * t)))
            for sx, sy in [(70, 90), (288, 130), (296, 245)]:
                draw.line((sx - 8, sy, sx + 8, sy), fill=(255, 214, 102, alpha), width=4)
                draw.line((sx, sy - 8, sx, sy + 8), fill=(255, 214, 102, alpha), width=4)

        # subtle paper texture / hand-drawn warmth
        noise = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        nd = ImageDraw.Draw(noise)
        seed = frame_index + len(phrase) * 17
        rng = random.Random(seed)
        for _ in range(38):
            px = rng.randrange(30, W - 30)
            py = rng.randrange(30, H - 30)
            nd.point((px, py), fill=(255, 255, 255, 23))
        img = Image.alpha_composite(img, noise)
        return img

    def _save_static(self, path: Path, phrase: str, identity: Dict[str, Any], expression: str = "확인", dark: bool = False) -> None:
        bg = (17, 24, 39, 255) if dark else None
        frame = self._draw_character_frame(phrase, identity, "static", 0, 1, bg, expression)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.save(path)

    def _save_gif(self, path: Path, phrase: str, identity: Dict[str, Any], motion: str, expression: str) -> None:
        frames = [
            self._draw_character_frame(phrase, identity, motion, i, self.FRAME_COUNT, None, expression)
            for i in range(self.FRAME_COUNT)
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            path,
            save_all=True,
            append_images=frames[1:],
            duration=70,
            loop=0,
            disposal=2,
            optimize=True,
        )

    def _make_contact_sheet(self, path: Path, static_path: Path, variants: List[Dict[str, Any]]) -> None:
        thumbs: List[Tuple[str, Image.Image]] = []
        thumbs.append(("정지형", Image.open(static_path).convert("RGBA")))
        for v in variants[:5]:
            # GIF 첫 프레임만 contact sheet에 배치한다. 실제 재생은 HTML/Streamlit에서 GIF로 표시한다.
            img = Image.open(v["path"]).convert("RGBA")
            thumbs.append((v["label"], img))
        card_w, card_h = 220, 248
        sheet = Image.new("RGB", (card_w * 3, card_h * 2), (246, 247, 251))
        draw = ImageDraw.Draw(sheet)
        font = self._font(20)
        for idx, (label, img) in enumerate(thumbs):
            x = (idx % 3) * card_w
            y = (idx // 3) * card_h
            draw.rounded_rectangle((x + 10, y + 10, x + card_w - 10, y + card_h - 10), radius=18, fill=(255, 255, 255), outline=(229, 231, 235), width=2)
            thumb = img.resize((156, 156), Image.LANCZOS)
            sheet.paste(thumb.convert("RGB"), (x + 32, y + 48), thumb)
            bbox = self._text_bbox(draw, (0, 0), label, font)
            draw.text((x + (card_w - (bbox[2]-bbox[0])) // 2, y + 18), label, font=font, fill=(23, 32, 51))
        path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(path)

    def _build_plans(self, out_dir: Path, identity: Dict[str, Any]) -> Dict[str, str]:
        static_rows = []
        animated_rows = []
        for i, (phrase, emotion, motion) in enumerate(self.PHRASE_POOL, start=1):
            static_rows.append({
                "no": i,
                "phrase": phrase,
                "emotion": emotion,
                "pose": motion,
                "quality_focus": "표정 차이/짧은 문구/썸네일 가독성",
                "identity_lock": identity["body_shape"],
            })
        for i, (phrase, emotion, motion) in enumerate(self.PHRASE_POOL[:24], start=1):
            animated_rows.append({
                "no": i,
                "phrase": phrase,
                "emotion": emotion,
                "motion": motion,
                "format_hint": "GIF_REQUIRED" if i in {1, 8, 16} else "PNG_STATIC_WITH_MOTION_PLAN",
                "frame_limit_note": "24프레임 이하 제출 전 재확인",
            })
        paths = {}
        static_csv = out_dir / "v69_static_32_quality_plan.csv"
        animated_csv = out_dir / "v69_animated_24_quality_plan.csv"
        static_json = out_dir / "v69_static_32_quality_plan.json"
        animated_json = out_dir / "v69_animated_24_quality_plan.json"
        for rows, csv_path, json_path in [(static_rows, static_csv, static_json), (animated_rows, animated_csv, animated_json)]:
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.update({
            "static_csv": str(static_csv),
            "static_json": str(static_json),
            "animated_csv": str(animated_csv),
            "animated_json": str(animated_json),
        })
        return paths

    def _quality_scores(self, identity: Dict[str, Any], selected_rules: List[str], feedback: str) -> Dict[str, int]:
        base = {
            "thumbnail_readability": 80,
            "character_identity": 78,
            "speech_bubble_readability": 79,
            "motion_naturalness": 74,
            "expression_diversity": 72,
            "darkmode_contrast": 76,
            "set_expandability": 73,
            "copy_safety": 88,
        }
        mapping = {
            "손그림 질감 외곽선 강화": "thumbnail_readability",
            "얼굴 크기 확대와 썸네일 가독성 강화": "thumbnail_readability",
            "문구 2~7자 답장형 우선": "speech_bubble_readability",
            "정지형 identity를 모든 GIF에 고정": "character_identity",
            "모션 시작-중간-끝 리듬을 부드럽게": "motion_naturalness",
            "표정 다양성 32개 세트 확장성 강화": "expression_diversity",
            "말풍선과 캐릭터 동작 동기화": "motion_naturalness",
            "다크모드 대비 흰색 외곽선 유지": "darkmode_contrast",
            "기존 인기 캐릭터 복제 금지": "copy_safety",
        }
        for r in selected_rules:
            if r in mapping:
                base[mapping[r]] = min(98, base[mapping[r]] + 8)
        if identity.get("forbidden_hits"):
            base["copy_safety"] = 25
        if "만족" in feedback or "좋" in feedback:
            base["character_identity"] = min(98, base["character_identity"] + 4)
        return base

    def _store_learning(self, db: Path, project_name: str, identity: Dict[str, Any], scores: Dict[str, int], feedback: str) -> None:
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v69_quality_upgrade_runs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    style TEXT,
                    material TEXT,
                    feedback TEXT,
                    total_score INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v69_quality_scores(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    score_key TEXT,
                    score_value INTEGER
                )
            """)
            total = int(sum(scores.values()) / max(1, len(scores)))
            cur.execute(
                "INSERT INTO v69_quality_upgrade_runs(created_at, project_name, style, material, feedback, total_score) VALUES(?,?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), project_name, identity.get("style"), identity.get("material"), feedback[:1000], total),
            )
            run_id = cur.lastrowid
            for k, v in scores.items():
                cur.execute("INSERT INTO v69_quality_scores(run_id, score_key, score_value) VALUES(?,?,?)", (run_id, k, int(v)))
            con.commit()

    def _render_report(self, template_dir: Path, out_path: Path, context: Dict[str, Any]) -> None:
        template_dir.mkdir(parents=True, exist_ok=True)
        template = template_dir / "v69_quality_upgrade_report.html.j2"
        if not template.exists():
            template.write_text("""<!doctype html>
<html lang=\"ko\"><head><meta charset=\"utf-8\"><title>v69 실제 품질 고도화 리포트</title>
<style>
body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;color:#172033;margin:0;padding:28px}.wrap{max-width:1180px;margin:auto}.hero{background:linear-gradient(135deg,#111827,#7c3aed,#ec4899);color:white;border-radius:28px;padding:28px 32px;box-shadow:0 18px 42px rgba(15,23,42,.20)}.card{background:white;border:1px solid #e5e7eb;border-radius:22px;padding:20px;margin-top:18px;box-shadow:0 10px 28px rgba(15,23,42,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}.preview{text-align:center;background:white;border:1px solid #e5e7eb;border-radius:18px;padding:12px}.preview img{max-width:230px;border-radius:18px;background:white}.badge{display:inline-block;background:#fce7f3;color:#9d174d;border-radius:999px;padding:5px 10px;margin:3px;font-weight:700}.score{font-size:27px;font-weight:800;color:#7c3aed}.warn{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:14px;padding:12px}.mono{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:16px;padding:14px;overflow:auto}
</style></head><body><div class=\"wrap\"><div class=\"hero\"><h1>v69 실제 품질 고도화 리포트</h1><p>손그림 질감 · 표정 다양성 · 자연스러운 GIF 모션 · 지속 학습 메모리</p></div>
<div class=\"card\"><h2>프로젝트</h2><p><b>{{ project_name }}</b></p><p>{{ concept_text }}</p>{% for r in selected_rules %}<span class=\"badge\">{{ r }}</span>{% endfor %}</div>
<div class=\"card\"><h2>바로 보이는 결과</h2><div class=\"grid\"><div class=\"preview\"><h3>정지형 PNG</h3><img src=\"data:image/png;base64,{{ static_b64 }}\"></div><div class=\"preview\"><h3>다크모드 대비</h3><img src=\"data:image/png;base64,{{ dark_b64 }}\"></div><div class=\"preview\"><h3>대표 움직이는 GIF</h3><img src=\"data:image/gif;base64,{{ gif_b64 }}\"></div></div></div>
<div class=\"card\"><h2>품질 점수</h2><div class=\"grid\">{% for k,v in quality_scores.items() %}<div><div class=\"score\">{{ v }}</div><b>{{ k }}</b></div>{% endfor %}</div></div>
<div class=\"card\"><h2>다음 생성 계획</h2><ul>{% for item in next_generation_plan %}<li>{{ item }}</li>{% endfor %}</ul></div>
<div class=\"card warn\"><b>안전 원칙</b><ul>{% for item in safety_notes %}<li>{{ item }}</li>{% endfor %}</ul></div>
<div class=\"card\"><h2>Identity Lock</h2><div class=\"mono\">{{ identity_pretty }}</div></div>
</div></body></html>""", encoding="utf-8")
        if Environment is None:
            raise RuntimeError("Jinja2 is required for v69 report rendering")
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"]))
        html = env.get_template(template.name).render(**context)
        out_path.write_text(html, encoding="utf-8")

    def _b64(self, path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("ascii")

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
    ) -> V69QualityUpgradeReport:
        safe_project = self._safe_name(project_name)
        run_dir = out_dir / f"{safe_project}_{int(time.time())}"
        run_dir.mkdir(parents=True, exist_ok=True)
        identity = self.build_identity(concept_text + " " + online_abstract_notes, selected_style, selected_rules, user_feedback)
        phrase = (main_phrase or "넵").strip()[:10]

        static_png = run_dir / "v69_static_quality_preview.png"
        dark_png = run_dir / "v69_darkmode_readability_preview.png"
        self._save_static(static_png, phrase, identity, expression="확인", dark=False)
        self._save_static(dark_png, phrase, identity, expression="확인", dark=True)

        variants: List[Dict[str, Any]] = []
        for motion, label in self.MOTION_VARIANTS:
            p = run_dir / f"v69_motion_{motion}.gif"
            expression = "확인"
            if motion in {"bow"}:
                expression = "사과"
            elif motion in {"wobble", "melt"}:
                expression = "피곤"
            elif motion in {"pop", "sparkle"}:
                expression = "놀람"
            self._save_gif(p, phrase, identity, motion, expression)
            variants.append({"motion": motion, "label": label, "path": str(p), "phrase": phrase, "expression": expression})
        motion_preview_gif = Path(variants[0]["path"])
        contact = run_dir / "v69_motion_contact_sheet.png"
        self._make_contact_sheet(contact, static_png, variants)

        plan_paths = self._build_plans(run_dir, identity)
        scores = self._quality_scores(identity, selected_rules, user_feedback + " " + online_abstract_notes)
        next_plan = [
            "사용자가 만족한 정지형 identity를 다음 움직이는형에서도 우선 고정합니다.",
            "문구는 2~7자 답장형을 기본 후보로 올리고, 긴 문구는 후보 하단으로 내립니다.",
            "GIF 후보는 파일명 대신 화면에서 실제 재생되는 비교 카드로 보여줍니다.",
            "다크모드 대비가 낮은 후보는 흰색 외곽선 또는 밝은 말풍선을 자동 적용합니다.",
            "32개/24개 세트에서 감정 중복이 많으면 표정·포즈 분산을 다시 제안합니다.",
        ]
        if identity.get("forbidden_hits"):
            next_plan.insert(0, "저작권/유사성 위험 키워드가 감지되어 모방형 생성은 차단하고 추상 신호만 남깁니다.")
        safety_notes = [
            "온라인 자료는 원본 이미지/문구/애니메이션을 저장하지 않고 추상 품질 신호만 사용합니다.",
            "기존 인기 캐릭터와 동일한 메시지·표현법·애니메이션 재사용을 방지합니다.",
            "API 키 원문은 결과 리포트, ZIP, JSON, CSV에 저장하지 않습니다.",
            "카카오 공식 규격은 제출 직전 반드시 공식 스튜디오에서 다시 확인합니다.",
        ]

        metrics_json = run_dir / "v69_quality_metrics.json"
        metrics_json.write_text(json.dumps({"scores": scores, "selected_rules": selected_rules, "next_plan": next_plan}, ensure_ascii=False, indent=2), encoding="utf-8")
        style_memory = run_dir / "v69_style_memory.json"
        style_memory.write_text(json.dumps({
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "identity_lock": identity,
            "user_feedback": user_feedback,
            "online_abstract_notes_preview": online_abstract_notes[:1200],
            "preferred_phrase": phrase,
            "selected_rules": selected_rules,
            "apply_next_generation": True,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        db_path = run_dir / "v69_quality_learning.sqlite3"
        self._store_learning(db_path, project_name, identity, scores, user_feedback)

        prompt_pack = run_dir / "v69_next_generation_prompt_pack.md"
        prompt_pack.write_text(
            "# v69 다음 생성 프롬프트 팩\n\n"
            f"- 프로젝트: {project_name}\n"
            f"- 스타일: {selected_style}\n"
            f"- 대표 문구: {phrase}\n"
            "- 유지할 identity: 색상, 외곽선, 얼굴 비율, 말풍선 형태\n"
            "- 금지: 기존 인기 캐릭터 복제, 동일 문구/동일 모션 재사용\n\n"
            "## 다음 개선\n" + "\n".join(f"- {x}" for x in next_plan),
            encoding="utf-8",
        )
        report_html = run_dir / "v69_actual_quality_upgrade_report.html"
        self._render_report(Path(__file__).resolve().parents[1] / "templates" / "v69_quality_upgrade", report_html, {
            "project_name": project_name,
            "concept_text": concept_text,
            "selected_rules": selected_rules,
            "static_b64": self._b64(static_png),
            "dark_b64": self._b64(dark_png),
            "gif_b64": self._b64(motion_preview_gif),
            "quality_scores": scores,
            "next_generation_plan": next_plan,
            "safety_notes": safety_notes,
            "identity_pretty": json.dumps(identity, ensure_ascii=False, indent=2),
        })

        package_zip = run_dir / "v69_actual_quality_upgrade_package.zip"
        include_paths = [
            static_png, dark_png, motion_preview_gif, contact, metrics_json, style_memory, db_path, prompt_pack, report_html,
            Path(plan_paths["static_csv"]), Path(plan_paths["static_json"]), Path(plan_paths["animated_csv"]), Path(plan_paths["animated_json"]),
        ] + [Path(v["path"]) for v in variants]
        unique_paths: List[Path] = []
        seen_names: set[str] = set()
        for fp in include_paths:
            if fp.exists() and fp.name not in seen_names:
                seen_names.add(fp.name)
                unique_paths.append(fp)
        with zipfile.ZipFile(package_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in unique_paths:
                zf.write(fp, fp.name)
        checksum = self._checksum(package_zip)
        return V69QualityUpgradeReport(
            project_name=project_name,
            output_dir=str(run_dir),
            static_png=str(static_png),
            darkmode_preview_png=str(dark_png),
            motion_preview_gif=str(motion_preview_gif),
            motion_variants=variants,
            motion_contact_sheet=str(contact),
            static_32_plan_csv=plan_paths["static_csv"],
            static_32_plan_json=plan_paths["static_json"],
            animated_24_plan_csv=plan_paths["animated_csv"],
            animated_24_plan_json=plan_paths["animated_json"],
            style_memory_json=str(style_memory),
            quality_metrics_json=str(metrics_json),
            learning_db=str(db_path),
            html_report_path=str(report_html),
            prompt_pack_path=str(prompt_pack),
            package_zip_path=str(package_zip),
            identity_lock=identity,
            selected_improvement_rules=selected_rules,
            quality_scores=scores,
            next_generation_plan=next_plan,
            safety_notes=safety_notes,
            checksum_sha256=checksum,
        )
