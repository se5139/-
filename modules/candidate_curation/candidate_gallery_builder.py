from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
import csv
import hashlib
import json
import math
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont

from .expression_face_engine import ExpressionFaceEngine

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()

try:
    from modules.beginner_creator.multi_material_creator import MaterialSpec
except Exception:  # pragma: no cover
    @dataclass
    class MaterialSpec:  # type: ignore
        name: str
        color: str = "아이보리"
        personality: str = "온순함"
        tone: str = "부드러운 말투"
        base_shape: str = "둥근형"
        role: str = "대화 보조"
        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)


@dataclass
class CurationReport:
    project_name: str
    format_key: str
    target_count: int
    total_candidates: int
    selected_count: int
    category_balance: Dict[str, int]
    selection_rules: List[str]
    selected_expressions: List[Dict[str, Any]]
    skipped_expressions: List[Dict[str, Any]]
    generated_files: List[Dict[str, Any]]
    html_path: str
    json_path: str
    csv_path: str
    zip_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CandidateGalleryBuilder:
    """표현 후보 은행에서 포맷별 최종 후보 24/32개를 고르고 갤러리/ZIP을 생성합니다.

    이 모듈은 심사 승인 보장을 의미하지 않습니다. 표현 후보를 사람이 더 쉽게 고를 수 있도록
    중복·가독성·감정 균형·포맷 적합도를 점수화하고, 선택된 결과를 미리보기 폴더로 정리합니다.
    """

    CATEGORY_WEIGHTS = {
        "확인": 96, "감사": 92, "사과": 90, "인사": 86, "응원": 84,
        "피곤": 86, "퇴근": 88, "당황": 82, "축하": 80, "부탁": 82,
        "잘자": 74, "거절": 76, "기다림": 72, "민망": 74, "분노": 78,
        "시그니처": 88,
    }

    FORMAT_MATCH_BONUS = {
        "static": ["정지형", "문구형 정지"],
        "static_text": ["문구형 정지", "정지형"],
        "animated": ["움직이는 문구형", "큰 이모티콘"],
        "animated_text": ["움직이는 문구형", "문구형 정지"],
        "big": ["큰 이모티콘", "움직이는 문구형"],
    }

    def __init__(self) -> None:
        self.canvas_size = 360
        self.face_engine = ExpressionFaceEngine()

    def _font(self, size: int):
        return load_korean_font(size)

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _safe_name(self, value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in value)[:28] or "project"

    def _parse_color(self, value: str, fallback: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        value = (value or "").strip()
        named = {
            "연갈색": (202, 154, 92, 255), "갈색": (150, 100, 55, 255),
            "아이보리": (244, 235, 205, 255), "흰색": (255, 250, 240, 255),
            "노랑": (245, 210, 80, 255), "연노랑": (250, 230, 130, 255),
            "초록": (120, 180, 90, 255), "회색": (160, 160, 160, 255),
            "분홍": (240, 160, 180, 255), "보라": (170, 140, 210, 255),
            "주황": (236, 145, 70, 255), "빨강": (220, 85, 85, 255),
            "파랑": (95, 150, 220, 255), "검정": (45, 45, 45, 255),
        }
        if value in named:
            return named[value]
        if value.startswith("#") and len(value) in (7, 9):
            try:
                r = int(value[1:3], 16); g = int(value[3:5], 16); b = int(value[5:7], 16)
                a = int(value[7:9], 16) if len(value) == 9 else 255
                return (r, g, b, a)
            except Exception:
                return fallback
        return fallback

    def _draw_material(self, draw: ImageDraw.ImageDraw, x: int, y: int, spec: MaterialSpec, idx: int, total: int, scale: float = 1.0, dx: int = 0, dy: int = 0) -> None:
        x += dx; y += dy
        fill = self._parse_color(getattr(spec, "color", ""), [(202,154,92,255),(244,235,205,255),(224,164,95,255),(160,160,160,255),(120,180,90,255)][idx % 5])
        outline = (45, 38, 32, 255)
        w = int(56 * scale); h = int(66 * scale)
        shape = getattr(spec, "base_shape", "둥근형")
        if shape == "길쭉형":
            draw.rounded_rectangle((x-w//2, y-h, x+w//2, y+h), radius=int(28*scale), fill=fill, outline=outline, width=max(2, int(4*scale)))
        elif shape == "납작형":
            draw.ellipse((x-int(62*scale), y-int(34*scale), x+int(62*scale), y+int(34*scale)), fill=fill, outline=outline, width=max(2, int(4*scale)))
        elif shape == "네모형":
            draw.rounded_rectangle((x-w, y-h//2, x+w, y+h//2), radius=int(16*scale), fill=fill, outline=outline, width=max(2, int(4*scale)))
        elif shape == "알갱이형":
            draw.rounded_rectangle((x-int(38*scale), y-int(54*scale), x+int(38*scale), y+int(54*scale)), radius=int(38*scale), fill=fill, outline=outline, width=max(2, int(4*scale)))
        else:
            draw.ellipse((x-w, y-h, x+w, y+h), fill=fill, outline=outline, width=max(2, int(4*scale)))
        name = getattr(spec, "name", "")
        if any(k in name for k in ["보리", "밀", "쌀"]):
            for a in [-35, 0, 35]:
                rad = math.radians(a)
                draw.line((x, y-int(60*scale), x+int(math.sin(rad)*24*scale), y-int(88*scale)), fill=outline, width=max(2, int(3*scale)))
        if any(k in name for k in ["감자", "고구마", "무", "당근"]):
            draw.arc((x-int(26*scale), y-int(66*scale), x+int(26*scale), y-int(36*scale)), 200, 340, fill=(80, 150, 80, 255), width=max(2, int(3*scale)))
        persona = getattr(spec, "personality", "") + getattr(spec, "tone", "")
        angry = any(k in persona for k in ["까칠", "투덜", "화", "시크"])
        gentle = any(k in persona for k in ["온순", "부드", "다정", "위로"])
        tired = any(k in persona for k in ["피곤", "무기력", "귀찮", "업무"])
        if angry:
            draw.line((x-int(24*scale), y-int(18*scale), x-int(8*scale), y-int(10*scale)), fill=outline, width=max(2, int(4*scale)))
            draw.line((x+int(8*scale), y-int(10*scale), x+int(24*scale), y-int(18*scale)), fill=outline, width=max(2, int(4*scale)))
        draw.ellipse((x-int(22*scale), y-int(3*scale), x-int(12*scale), y+int(7*scale)), fill=outline)
        draw.ellipse((x+int(12*scale), y-int(3*scale), x+int(22*scale), y+int(7*scale)), fill=outline)
        if gentle:
            draw.arc((x-int(18*scale), y+int(12*scale), x+int(18*scale), y+int(32*scale)), 0, 180, fill=outline, width=max(2, int(3*scale)))
        elif tired:
            draw.line((x-int(16*scale), y+int(24*scale), x+int(16*scale), y+int(22*scale)), fill=outline, width=max(2, int(3*scale)))
        elif angry:
            draw.line((x-int(16*scale), y+int(25*scale), x+int(14*scale), y+int(19*scale)), fill=outline, width=max(2, int(3*scale)))
        else:
            draw.arc((x-int(16*scale), y+int(12*scale), x+int(16*scale), y+int(31*scale)), 0, 180, fill=outline, width=max(2, int(3*scale)))
        draw.line((x-int(43*scale), y+int(22*scale), x-int(64*scale), y+int(34*scale)), fill=outline, width=max(2, int(3*scale)))
        draw.line((x+int(43*scale), y+int(22*scale), x+int(64*scale), y+int(14*scale)), fill=outline, width=max(2, int(3*scale)))

    def _positions(self, total: int) -> List[Tuple[int, int, float]]:
        if total <= 1:
            return [(180, 142, 0.92)]
        if total == 2:
            return [(122, 140, 0.74), (238, 140, 0.74)]
        if total == 3:
            return [(88, 148, .56), (180, 116, .56), (272, 148, .56)]
        if total == 4:
            return [(96, 112, .50), (264, 112, .50), (96, 194, .50), (264, 194, .50)]
        return [(180, 86, .43), (86, 142, .43), (180, 162, .43), (274, 142, .43), (180, 220, .43)]

    def _wrap_text(self, text: str, max_chars: int = 18) -> List[str]:
        text = str(text).replace("·", " ").strip()
        if len(text) <= max_chars:
            return [text]
        chunks: List[str] = []
        while text and len(chunks) < 3:
            chunks.append(text[:max_chars])
            text = text[max_chars:]
        return chunks

    def _draw_expression_overlay(self, draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, spec: MaterialSpec, plan: Dict[str, Any], idx: int, dx: int = 0, dy: int = 0) -> None:
        """선택 표현에 맞춘 눈·입·효과를 기본 도형 위에 덧그립니다."""
        if not plan:
            return
        x += dx; y += dy
        outline = (36, 32, 28, 255)
        fill = self._parse_color(getattr(spec, "color", ""), (244, 235, 205, 255))
        eye = str(plan.get("eye_style", "normal"))
        brow = str(plan.get("brow_style", "soft"))
        mouth = str(plan.get("mouth_style", "smile"))
        effects = set(plan.get("effects", []))
        # 얼굴 중앙부를 살짝 덮어 표정 변형이 더 분명하게 보이게 함
        draw.rounded_rectangle((x-int(36*scale), y-int(22*scale), x+int(36*scale), y+int(38*scale)), radius=int(18*scale), fill=(*fill[:3], 210))
        # 눈
        if eye in ["closed", "soft_closed"]:
            draw.arc((x-int(28*scale), y-int(4*scale), x-int(8*scale), y+int(12*scale)), 0, 180, fill=outline, width=max(2, int(3*scale)))
            draw.arc((x+int(8*scale), y-int(4*scale), x+int(28*scale), y+int(12*scale)), 0, 180, fill=outline, width=max(2, int(3*scale)))
        elif eye in ["half", "patient", "side"]:
            draw.line((x-int(29*scale), y+int(2*scale), x-int(9*scale), y+int(2*scale)), fill=outline, width=max(2, int(3*scale)))
            draw.line((x+int(9*scale), y+int(2*scale), x+int(29*scale), y+int(2*scale)), fill=outline, width=max(2, int(3*scale)))
        elif eye in ["wide", "puppy", "bright", "happy"]:
            draw.ellipse((x-int(30*scale), y-int(9*scale), x-int(9*scale), y+int(13*scale)), fill=(255,255,255,235), outline=outline, width=max(2, int(2*scale)))
            draw.ellipse((x+int(9*scale), y-int(9*scale), x+int(30*scale), y+int(13*scale)), fill=(255,255,255,235), outline=outline, width=max(2, int(2*scale)))
            draw.ellipse((x-int(23*scale), y-int(2*scale), x-int(15*scale), y+int(7*scale)), fill=outline)
            draw.ellipse((x+int(15*scale), y-int(2*scale), x+int(23*scale), y+int(7*scale)), fill=outline)
        elif eye in ["sharp", "focused"]:
            draw.line((x-int(29*scale), y-int(2*scale), x-int(9*scale), y+int(7*scale)), fill=outline, width=max(2, int(4*scale)))
            draw.line((x+int(9*scale), y+int(7*scale), x+int(29*scale), y-int(2*scale)), fill=outline, width=max(2, int(4*scale)))
        else:
            draw.ellipse((x-int(24*scale), y-int(4*scale), x-int(13*scale), y+int(7*scale)), fill=outline)
            draw.ellipse((x+int(13*scale), y-int(4*scale), x+int(24*scale), y+int(7*scale)), fill=outline)
        # 눈썹
        if brow in ["angry", "worried", "raised", "up", "straight"]:
            if brow == "angry":
                draw.line((x-int(32*scale), y-int(20*scale), x-int(10*scale), y-int(11*scale)), fill=outline, width=max(2, int(3*scale)))
                draw.line((x+int(10*scale), y-int(11*scale), x+int(32*scale), y-int(20*scale)), fill=outline, width=max(2, int(3*scale)))
            elif brow == "worried":
                draw.line((x-int(32*scale), y-int(13*scale), x-int(10*scale), y-int(20*scale)), fill=outline, width=max(2, int(3*scale)))
                draw.line((x+int(10*scale), y-int(20*scale), x+int(32*scale), y-int(13*scale)), fill=outline, width=max(2, int(3*scale)))
            else:
                draw.line((x-int(32*scale), y-int(18*scale), x-int(10*scale), y-int(18*scale)), fill=outline, width=max(2, int(3*scale)))
                draw.line((x+int(10*scale), y-int(18*scale), x+int(32*scale), y-int(18*scale)), fill=outline, width=max(2, int(3*scale)))
        # 입
        if mouth in ["big_smile", "warm_smile", "smile", "small_smile", "tiny_smile", "relieved"]:
            box = (x-int(22*scale), y+int(12*scale), x+int(22*scale), y+int(36*scale))
            draw.arc(box, 0, 180, fill=outline, width=max(2, int(4*scale)))
        elif mouth in ["sad", "awkward"]:
            box = (x-int(22*scale), y+int(20*scale), x+int(22*scale), y+int(44*scale))
            draw.arc(box, 180, 360, fill=outline, width=max(2, int(4*scale)))
        elif mouth == "open":
            draw.ellipse((x-int(12*scale), y+int(17*scale), x+int(12*scale), y+int(40*scale)), fill=outline)
        elif mouth == "zigzag":
            pts = [(x-int(22*scale),y+int(25*scale)),(x-int(10*scale),y+int(18*scale)),(x,y+int(27*scale)),(x+int(10*scale),y+int(18*scale)),(x+int(22*scale),y+int(25*scale))]
            draw.line(pts, fill=outline, width=max(2, int(3*scale)))
        elif mouth == "smirk":
            draw.arc((x-int(18*scale), y+int(15*scale), x+int(24*scale), y+int(36*scale)), 10, 150, fill=outline, width=max(2, int(3*scale)))
        else:
            draw.line((x-int(16*scale), y+int(25*scale), x+int(16*scale), y+int(25*scale)), fill=outline, width=max(2, int(3*scale)))
        # 감정 효과
        if "sweat" in effects:
            draw.ellipse((x+int(42*scale), y-int(35*scale), x+int(56*scale), y-int(16*scale)), fill=(80,170,230,230), outline=outline, width=max(1, int(2*scale)))
        if "blush" in effects:
            draw.ellipse((x-int(44*scale), y+int(14*scale), x-int(27*scale), y+int(26*scale)), fill=(240,120,135,170))
            draw.ellipse((x+int(27*scale), y+int(14*scale), x+int(44*scale), y+int(26*scale)), fill=(240,120,135,170))
        if "zzz" in effects:
            zfont = self._font(max(12, int(18*scale)))
            draw.text((x+int(44*scale), y-int(56*scale)), "Zzz", fill=(70,70,120,210), font=zfont)
        if "check" in effects:
            draw.line((x+int(42*scale), y-int(48*scale), x+int(52*scale), y-int(36*scale), x+int(74*scale), y-int(58*scale)), fill=(50,160,80,240), width=max(2, int(5*scale)))
        if "heart" in effects or "small_heart" in effects:
            draw.text((x-int(60*scale), y-int(58*scale)), "♥", fill=(230,80,120,230), font=self._font(max(14, int(22*scale))))
        if "sparkle" in effects or "confetti" in effects:
            draw.text((x+int(48*scale), y-int(72*scale)), "✦", fill=(230,175,40,230), font=self._font(max(14, int(22*scale))))
        if "anger" in effects or "small_anger" in effects:
            draw.text((x+int(42*scale), y-int(64*scale)), "#", fill=(210,70,60,230), font=self._font(max(16, int(24*scale))))
        if "question" in effects:
            draw.text((x+int(50*scale), y-int(62*scale)), "?", fill=(80,80,80,230), font=self._font(max(16, int(24*scale))))

    def score_expressions(self, expressions: List[Dict[str, Any]], format_key: str = "static_text") -> List[Dict[str, Any]]:
        seen_phrase: Dict[str, int] = {}
        scored: List[Dict[str, Any]] = []
        allowed = self.FORMAT_MATCH_BONUS.get(format_key, [])
        for idx, row in enumerate(expressions):
            phrase = str(row.get("phrase", "")).strip()
            compact = "".join(ch for ch in phrase if ch.isalnum())[:24]
            cat = str(row.get("category", "기타"))
            fmt = str(row.get("format_recommendation", ""))
            score = self.CATEGORY_WEIGHTS.get(cat, 70)
            if any(a in fmt for a in allowed):
                score += 12
            if 3 <= len(phrase) <= 34:
                score += 10
            elif len(phrase) > 48:
                score -= 15
            if "/" in phrase:
                score += 5
            if str(row.get("motion_hint", "")) and "animated" in format_key:
                score += 8
            duplicate_count = seen_phrase.get(compact, 0)
            if duplicate_count:
                score -= 25 * duplicate_count
            seen_phrase[compact] = duplicate_count + 1
            enriched = dict(row)
            enriched["candidate_score"] = max(0, min(100, int(score)))
            enriched["duplicate_key"] = compact
            enriched["readability_note"] = "양호" if len(phrase) <= 34 else "문구가 길어 축약 권장"
            enriched["selection_reason"] = self._reason(enriched, format_key)
            scored.append(enriched)
        return scored

    def _reason(self, row: Dict[str, Any], format_key: str) -> str:
        reasons = []
        if row.get("category") in ["확인", "감사", "사과", "피곤", "퇴근", "시그니처"]:
            reasons.append("실사용 빈도/캐릭터성 우선")
        if "animated" in format_key and row.get("motion_hint"):
            reasons.append("문구-동작 동기화 가능")
        if row.get("readability_note") == "양호":
            reasons.append("360×360 가독성 양호")
        if not reasons:
            reasons.append("표현 균형 보강용")
        return ", ".join(reasons)

    def curate(self, expressions: List[Dict[str, Any]], target_count: int, format_key: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
        scored = sorted(self.score_expressions(expressions, format_key), key=lambda r: r.get("candidate_score", 0), reverse=True)
        selected: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        category_counts: Dict[str, int] = {}
        duplicate_keys = set()
        per_category_soft_limit = max(3, target_count // 6)
        # First pass: preserve category balance and avoid duplicates.
        for row in scored:
            cat = str(row.get("category", "기타"))
            key = row.get("duplicate_key")
            if len(selected) >= target_count:
                skipped.append({**row, "skip_reason": "목표 수량 초과"})
                continue
            if key in duplicate_keys:
                skipped.append({**row, "skip_reason": "문구 중복 위험"})
                continue
            if category_counts.get(cat, 0) >= per_category_soft_limit and len(selected) < target_count * 0.75:
                skipped.append({**row, "skip_reason": "감정/상황 균형을 위해 예비 보류"})
                continue
            selected.append(row)
            duplicate_keys.add(key)
            category_counts[cat] = category_counts.get(cat, 0) + 1
        # Second pass: fill remaining slots from skipped but still avoid exact duplicate keys.
        if len(selected) < target_count:
            for row in scored:
                if len(selected) >= target_count:
                    break
                key = row.get("duplicate_key")
                if key in duplicate_keys:
                    continue
                selected.append(row)
                duplicate_keys.add(key)
                cat = str(row.get("category", "기타"))
                category_counts[cat] = category_counts.get(cat, 0) + 1
        selected = selected[:target_count]
        selected_ids = {id(x) for x in selected}
        final_skipped = [r for r in scored if id(r) not in selected_ids][: max(0, min(40, len(scored)))]
        for i, row in enumerate(selected, start=1):
            row["selected_no"] = i
        return selected, final_skipped, category_counts

    def _render_static_item(self, specs: List[MaterialSpec], row: Dict[str, Any], out_path: Path, no: int) -> None:
        img = Image.new("RGBA", (360, 360), (255, 255, 255, 0))
        d = ImageDraw.Draw(img)
        total = len(specs)
        plan = row.get("expression_plan") or self.face_engine.build_plan(row, specs, "static_text")
        focus = str(plan.get("focus_character", ""))
        for idx, spec in enumerate(specs[:5]):
            x, y, scale = self._positions(total)[idx]
            self._draw_material(d, x, y, spec, idx, total, scale)
            if getattr(spec, "name", "") == focus or (not focus and idx == 0):
                self._draw_expression_overlay(d, x, y, scale, spec, plan, idx)
        d.rounded_rectangle((18, 248, 342, 344), radius=18, fill=(255, 255, 255, 240), outline=(35,35,35,255), width=2)
        text = str(row.get("phrase", ""))
        lines = self._wrap_text(text, max_chars=18 if len(specs) >= 3 else 20)
        font = self._font(18 if len(lines) <= 2 else 15)
        top = 276 if len(lines) == 1 else 266
        for i, line in enumerate(lines):
            d.text((180, top + i * 25), line, anchor="mm", fill=(25,25,25,255), font=font)
        small = self._font(13)
        d.text((28, 24), f"#{no:02d}", fill=(70,70,70,230), font=small)
        img.save(out_path)

    def _render_animated_item(self, specs: List[MaterialSpec], row: Dict[str, Any], out_path: Path, no: int) -> None:
        frames = []
        offsets = [0, -4, -8, -4, 0, 3, 0, 0]
        plan = row.get("expression_plan") or self.face_engine.build_plan(row, specs, "animated_text")
        focus = str(plan.get("focus_character", ""))
        effects = set(plan.get("effects", []))
        for frame_idx, off in enumerate(offsets):
            img = Image.new("RGBA", (360, 360), (255, 255, 255, 0))
            d = ImageDraw.Draw(img)
            total = len(specs)
            for idx, spec in enumerate(specs[:5]):
                x, y, scale = self._positions(total)[idx]
                is_focus = getattr(spec, "name", "") == focus or (not focus and idx == 0)
                phase = off if (is_focus or idx == (frame_idx % max(1, total))) else 0
                self._draw_material(d, x, y, spec, idx, total, scale, dy=phase)
                if is_focus:
                    self._draw_expression_overlay(d, x, y, scale, spec, plan, idx, dy=phase)
            if "confetti" in effects and frame_idx >= 2:
                d.text((52, 62), "✦", fill=(230,175,40,220), font=self._font(24))
                d.text((302, 74), "✦", fill=(230,120,80,220), font=self._font(22))
            if "anger" in effects and frame_idx % 2 == 1:
                d.line((45,70,72,62), fill=(210,70,60,220), width=4)
                d.line((286,64,316,76), fill=(210,70,60,220), width=4)
            bubble_y = 248 + min(10, max(-6, -off))
            d.rounded_rectangle((18, bubble_y, 342, bubble_y + 96), radius=18, fill=(255, 255, 255, 235), outline=(35,35,35,255), width=2)
            text = str(row.get("phrase", ""))
            visible = text if frame_idx >= 2 else text[: max(1, int(len(text) * (frame_idx + 1) / 3))]
            lines = self._wrap_text(visible, max_chars=18 if len(specs) >= 3 else 20)
            font = self._font(18 if len(lines) <= 2 else 15)
            top = bubble_y + (28 if len(lines) == 1 else 18)
            for i, line in enumerate(lines):
                d.text((180, top + i * 25), line, anchor="mm", fill=(25,25,25,255), font=font)
            small = self._font(13)
            d.text((28, 24), f"#{no:02d}", fill=(70,70,70,230), font=small)
            frames.append(img)
        frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=90, loop=0, disposal=2)

    def _write_html(self, report: Dict[str, Any], path: Path) -> None:
        rows = "".join(
            f"<tr><td>{r.get('selected_no','')}</td><td>{r.get('category','')}</td><td>{r.get('phrase','')}</td><td>{r.get('candidate_score','')}</td><td>{r.get('face_summary','')}</td><td>{r.get('selection_reason','')}</td></tr>"
            for r in report["selected_expressions"]
        )
        balance = "".join(f"<li>{k}: {v}</li>" for k, v in report["category_balance"].items())
        generated = "".join(f"<li>{g.get('file_name')} · {g.get('checksum_sha256','')[:12]}</li>" for g in report["generated_files"][:80])
        html = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v18 후보 갤러리 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#f6f6f6}}.box{{background:#fff8e8;border:1px solid #f0d58a;border-radius:10px;padding:14px;margin:14px 0}}</style></head><body>
<h1>v18 후보 갤러리/세트 선택 리포트</h1>
<div class='box'><b>프로젝트:</b> {report['project_name']}<br><b>포맷:</b> {report['format_key']}<br><b>후보:</b> {report['total_candidates']}개 → <b>선택:</b> {report['selected_count']}개</div>
<h2>선택 기준</h2><ul>{''.join(f'<li>{x}</li>' for x in report['selection_rules'])}</ul>
<h2>표현 균형</h2><ul>{balance}</ul>
<h2>선택 표현 + 표정 자동 구성</h2><table><tr><th>No</th><th>분류</th><th>문구</th><th>점수</th><th>자동 표정/효과</th><th>선택 이유</th></tr>{rows}</table>
<h2>생성 파일</h2><ul>{generated}</ul>
<p>이 리포트는 제작 편의용 검토 자료이며 승인/법적 안전을 보장하지 않습니다.</p>
</body></html>"""
        path.write_text(html, encoding="utf-8")

    def build_gallery_pack(self, specs: List[MaterialSpec], expressions: List[Dict[str, Any]], output_dir: Path, project_name: str, format_key: str = "static_text", target_count: int = 32) -> CurationReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_project = self._safe_name(project_name)
        root = output_dir / safe_project
        items = root / "items"
        meta = root / "meta"
        items.mkdir(parents=True, exist_ok=True)
        meta.mkdir(parents=True, exist_ok=True)
        specs = specs[:5]
        selected, skipped, balance = self.curate(expressions, target_count, format_key)
        for row in selected:
            plan = self.face_engine.build_plan(row, specs, format_key)
            row["expression_plan"] = plan
            row["face_summary"] = self.face_engine.summary(plan)
        generated: List[Dict[str, Any]] = []
        ext = ".gif" if "animated" in format_key else ".png"
        for idx, row in enumerate(selected, start=1):
            fp = items / f"{idx:02d}{ext}"
            if ext == ".gif":
                self._render_animated_item(specs, row, fp, idx)
            else:
                self._render_static_item(specs, row, fp, idx)
            generated.append({
                "no": idx,
                "file_name": fp.name,
                "file_path": str(fp),
                "format": format_key,
                "size_bytes": fp.stat().st_size,
                "checksum_sha256": self._checksum(fp),
            })
        csv_path = meta / "curated_expression_selection.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["selected_no", "category", "phrase", "candidate_score", "format_recommendation", "motion_hint", "face_summary", "expression_plan", "selection_reason", "readability_note"])
            writer.writeheader()
            for row in selected:
                writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
        selection_rules = [
            "중복 문구를 우선 제외하고 카톡 실사용성이 높은 표현을 우선 선별",
            "확인·감사·사과·피곤·퇴근·시그니처 표현을 적절히 섞어 감정 균형 유지",
            "문구 길이와 360×360 가독성을 점수에 반영",
            "움직이는 문구형은 문구와 캐릭터 동작이 연결되는 표현을 우선 선택",
            "선택 표현마다 눈·입·눈썹·감정 효과·문구 움직임 계획을 자동 배정",
            "이 결과는 자동 초안이므로 최종 제출 전 사람 검토가 필요",
        ]
        report_dict = {
            "project_name": project_name,
            "format_key": format_key,
            "target_count": target_count,
            "total_candidates": len(expressions),
            "selected_count": len(selected),
            "category_balance": balance,
            "selection_rules": selection_rules,
            "selected_expressions": selected,
            "skipped_expressions": skipped,
            "generated_files": generated,
            "created_at": int(time.time()),
        }
        json_path = meta / "candidate_gallery_report.json"
        json_path.write_text(json.dumps(report_dict, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path = meta / "candidate_gallery_report.html"
        self._write_html(report_dict, html_path)
        zip_path = output_dir / f"{safe_project}_candidate_gallery_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in root.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(root.parent))
        return CurationReport(
            project_name=project_name,
            format_key=format_key,
            target_count=target_count,
            total_candidates=len(expressions),
            selected_count=len(selected),
            category_balance=balance,
            selection_rules=selection_rules,
            selected_expressions=selected,
            skipped_expressions=skipped,
            generated_files=generated,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
        )
