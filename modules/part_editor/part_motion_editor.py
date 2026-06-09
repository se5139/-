from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import hashlib
import json
import math
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()

try:
    from modules.animated_text_emoticon.frame_builder import AnimatedTextFrameBuilder
except Exception:  # pragma: no cover
    AnimatedTextFrameBuilder = None  # type: ignore


@dataclass
class PartEditReport:
    project_name: str
    source_count: int
    edited_count: int
    format_key: str
    edit_options: Dict[str, List[str]]
    edited_expressions: List[Dict[str, Any]]
    preview_files: List[Dict[str, Any]]
    final_check_table: List[Dict[str, Any]]
    timeline_table: List[Dict[str, Any]]
    html_path: str
    json_path: str
    csv_path: str
    zip_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PartMotionEditor:
    """v18 표정·파츠·문구·움직임 편집기.

    v18에서 자동 배정된 expression_plan을 사람이 확인/수정할 수 있도록
    눈/입/눈썹/효과/문구 움직임/몸동작 후보를 제공하고, 수정값을 반영한
    미리보기 PNG/GIF와 최종 확인표를 생성합니다.
    """

    EYE_OPTIONS = ["normal", "happy", "soft_closed", "closed", "half", "wide", "focused", "sharp", "puppy", "side", "down", "patient"]
    BROW_OPTIONS = ["soft", "straight", "worried", "angry", "raised", "up", "flat"]
    MOUTH_OPTIONS = ["smile", "small_smile", "warm_smile", "big_smile", "tiny_smile", "flat", "sad", "awkward", "open", "zigzag", "smirk", "relieved"]
    BODY_MOTION_OPTIONS = ["기본 자세", "작게 끄덕임", "작게 꾸벅", "몸이 작아지며 꾸벅", "통통 튐", "좌우로 떨림", "짧게 움찔", "점프", "두 손 모으기", "화면 밖으로 이동", "아래로 처짐", "살짝 흔들리며 잠듦", "구겨짐/처짐", "팔짱/고개 돌림"]
    TEXT_MOTION_OPTIONS = ["고정", "톡 튀어나오기", "도장처럼 찍힘", "천천히 나타남", "작게 떨림", "부들부들 흔들림", "축 처짐", "점 세 개 순차 등장", "반짝이며 등장", "부드럽게 등장", "따라가듯 이동", "짧게 툭 등장"]
    EFFECT_OPTIONS = ["none", "sweat", "heart", "sparkle", "anger", "check", "zzz", "question", "confetti", "small_heart", "speed", "dots", "blush", "moon", "wave", "signature"]

    def __init__(self) -> None:
        self.size = 360

    def edit_options(self) -> Dict[str, List[str]]:
        return {
            "eye_style": self.EYE_OPTIONS,
            "brow_style": self.BROW_OPTIONS,
            "mouth_style": self.MOUTH_OPTIONS,
            "body_motion": self.BODY_MOTION_OPTIONS,
            "text_motion": self.TEXT_MOTION_OPTIONS,
            "effects": self.EFFECT_OPTIONS,
        }

    def _font(self, size: int):
        return load_korean_font(size)

    def _safe_name(self, value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in str(value))[:40] or "part_editor"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _parse_color(self, value: str, fallback=(244, 235, 205, 255)):
        value = str(value or "").strip()
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

    def _text_size(self, draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
        try:
            box = draw.textbbox((0, 0), text, font=font)
            return (box[2] - box[0], box[3] - box[1])
        except Exception:
            return draw.textsize(text, font=font)

    def _wrap(self, phrase: str, max_chars: int = 12) -> List[str]:
        phrase = str(phrase or "").strip()
        if len(phrase) <= max_chars:
            return [phrase]
        lines: List[str] = []
        while phrase:
            lines.append(phrase[:max_chars])
            phrase = phrase[max_chars:]
        return lines[:3]

    def _draw_effects(self, draw: ImageDraw.ImageDraw, effects: List[str], x: int, y: int, intensity: int) -> None:
        outline = (45, 38, 32, 255)
        if "sweat" in effects:
            draw.ellipse((x+58, y-54, x+76, y-31), fill=(100, 180, 245, 230), outline=outline, width=2)
        if "heart" in effects or "small_heart" in effects:
            draw.polygon([(x+65,y-55),(x+78,y-70),(x+93,y-55),(x+79,y-35)], fill=(235,90,120,230), outline=outline)
        if "sparkle" in effects:
            for dx,dy in [(70,-10),(-72,-22),(45,-80)]:
                draw.line((x+dx, y+dy-10, x+dx, y+dy+10), fill=(240,190,50,255), width=3)
                draw.line((x+dx-10, y+dy, x+dx+10, y+dy), fill=(240,190,50,255), width=3)
        if "anger" in effects:
            draw.line((x+58,y-74,x+86,y-62), fill=(220,70,70,255), width=5)
            draw.line((x+64,y-44,x+92,y-38), fill=(220,70,70,255), width=5)
        if "check" in effects:
            draw.line((x+52,y-68,x+66,y-52,x+95,y-86), fill=(60,160,80,255), width=7)
        if "zzz" in effects:
            font = self._font(22)
            draw.text((x+52,y-82), "Zzz", font=font, fill=(80,80,120,220))
        if "question" in effects:
            font = self._font(34)
            draw.text((x+58,y-84), "?", font=font, fill=(80,90,160,235))
        if "confetti" in effects:
            colors = [(250,80,80,255),(80,160,230,255),(250,200,60,255),(100,200,120,255)]
            for i in range(8):
                draw.rectangle((x-105+i*28,y-95+(i%3)*12,x-96+i*28,y-86+(i%3)*12), fill=colors[i%4])
        if "dots" in effects:
            for i in range(3):
                draw.ellipse((x+45+i*15,y-63,x+54+i*15,y-54), fill=outline)
        if "blush" in effects:
            draw.ellipse((x-54,y+8,x-26,y+22), fill=(235,120,135,120))
            draw.ellipse((x+26,y+8,x+54,y+22), fill=(235,120,135,120))
        if "moon" in effects:
            draw.ellipse((x+60,y-88,x+90,y-58), fill=(245,220,110,230), outline=outline, width=2)
            draw.ellipse((x+70,y-92,x+98,y-58), fill=(255,255,255,0))
        if "wave" in effects:
            draw.arc((x-120,y-62,x-84,y-24), -30, 80, fill=outline, width=3)
            draw.arc((x-132,y-74,x-82,y-18), -30, 80, fill=outline, width=3)

    def _draw_face(self, draw: ImageDraw.ImageDraw, x: int, y: int, plan: Dict[str, Any], color: str = "아이보리", scale: float = 1.0) -> None:
        fill = self._parse_color(color)
        outline = (45, 38, 32, 255)
        eye = plan.get("eye_style", "normal")
        brow = plan.get("brow_style", "soft")
        mouth = plan.get("mouth_style", "smile")
        # body offset hints
        body = str(plan.get("body_motion", ""))
        if "처짐" in body or "축" in body:
            y += 12
        if "점프" in body or "통통" in body:
            y -= 8
        if "작아" in body:
            scale *= .88
        rx, ry = int(82*scale), int(92*scale)
        draw.ellipse((x-rx, y-ry, x+rx, y+ry), fill=fill, outline=outline, width=max(3, int(5*scale)))
        # arms/body accent
        draw.line((x-int(70*scale), y+int(30*scale), x-int(104*scale), y+int(48*scale)), fill=outline, width=max(2, int(4*scale)))
        draw.line((x+int(70*scale), y+int(30*scale), x+int(104*scale), y+int(20*scale)), fill=outline, width=max(2, int(4*scale)))
        if brow in ["angry", "worried", "raised", "up", "straight", "flat"]:
            if brow == "angry":
                draw.line((x-int(42*scale), y-int(33*scale), x-int(14*scale), y-int(20*scale)), fill=outline, width=max(2, int(4*scale)))
                draw.line((x+int(14*scale), y-int(20*scale), x+int(42*scale), y-int(33*scale)), fill=outline, width=max(2, int(4*scale)))
            elif brow == "worried":
                draw.line((x-int(42*scale), y-int(23*scale), x-int(14*scale), y-int(34*scale)), fill=outline, width=max(2, int(4*scale)))
                draw.line((x+int(14*scale), y-int(34*scale), x+int(42*scale), y-int(23*scale)), fill=outline, width=max(2, int(4*scale)))
            elif brow in ["raised", "up"]:
                draw.arc((x-int(47*scale), y-int(45*scale), x-int(10*scale), y-int(20*scale)), 200, 340, fill=outline, width=max(2, int(3*scale)))
                draw.arc((x+int(10*scale), y-int(45*scale), x+int(47*scale), y-int(20*scale)), 200, 340, fill=outline, width=max(2, int(3*scale)))
            else:
                draw.line((x-int(43*scale), y-int(28*scale), x-int(12*scale), y-int(28*scale)), fill=outline, width=max(2, int(3*scale)))
                draw.line((x+int(12*scale), y-int(28*scale), x+int(43*scale), y-int(28*scale)), fill=outline, width=max(2, int(3*scale)))
        # eyes
        if eye in ["closed", "soft_closed", "down"]:
            draw.arc((x-int(43*scale), y-int(17*scale), x-int(14*scale), y+int(10*scale)), 0, 180, fill=outline, width=max(2, int(4*scale)))
            draw.arc((x+int(14*scale), y-int(17*scale), x+int(43*scale), y+int(10*scale)), 0, 180, fill=outline, width=max(2, int(4*scale)))
        elif eye in ["half", "patient", "side"]:
            draw.line((x-int(43*scale), y-int(1*scale), x-int(14*scale), y-int(1*scale)), fill=outline, width=max(2, int(4*scale)))
            draw.line((x+int(14*scale), y-int(1*scale), x+int(43*scale), y-int(1*scale)), fill=outline, width=max(2, int(4*scale)))
        elif eye in ["wide", "puppy", "bright", "happy"]:
            draw.ellipse((x-int(46*scale), y-int(17*scale), x-int(15*scale), y+int(15*scale)), fill=(255,255,255,240), outline=outline, width=max(2, int(3*scale)))
            draw.ellipse((x+int(15*scale), y-int(17*scale), x+int(46*scale), y+int(15*scale)), fill=(255,255,255,240), outline=outline, width=max(2, int(3*scale)))
            draw.ellipse((x-int(34*scale), y-int(6*scale), x-int(23*scale), y+int(7*scale)), fill=outline)
            draw.ellipse((x+int(23*scale), y-int(6*scale), x+int(34*scale), y+int(7*scale)), fill=outline)
        elif eye in ["sharp", "focused"]:
            draw.line((x-int(46*scale), y-int(9*scale), x-int(16*scale), y+int(5*scale)), fill=outline, width=max(2, int(5*scale)))
            draw.line((x+int(16*scale), y+int(5*scale), x+int(46*scale), y-int(9*scale)), fill=outline, width=max(2, int(5*scale)))
        else:
            draw.ellipse((x-int(38*scale), y-int(8*scale), x-int(21*scale), y+int(8*scale)), fill=outline)
            draw.ellipse((x+int(21*scale), y-int(8*scale), x+int(38*scale), y+int(8*scale)), fill=outline)
        # mouth
        if mouth in ["big_smile", "warm_smile", "smile", "small_smile", "tiny_smile", "relieved"]:
            draw.arc((x-int(32*scale), y+int(12*scale), x+int(32*scale), y+int(48*scale)), 0, 180, fill=outline, width=max(2, int(5*scale)))
        elif mouth in ["sad", "awkward"]:
            draw.arc((x-int(32*scale), y+int(28*scale), x+int(32*scale), y+int(64*scale)), 180, 360, fill=outline, width=max(2, int(5*scale)))
        elif mouth == "open":
            draw.ellipse((x-int(18*scale), y+int(16*scale), x+int(18*scale), y+int(50*scale)), fill=outline)
        elif mouth == "zigzag":
            pts = [(x-int(35*scale),y+int(35*scale)),(x-int(16*scale),y+int(24*scale)),(x,y+int(38*scale)),(x+int(16*scale),y+int(24*scale)),(x+int(35*scale),y+int(35*scale))]
            draw.line(pts, fill=outline, width=max(2, int(4*scale)))
        elif mouth == "smirk":
            draw.arc((x-int(22*scale), y+int(16*scale), x+int(38*scale), y+int(47*scale)), 10, 150, fill=outline, width=max(2, int(4*scale)))
        else:
            draw.line((x-int(26*scale), y+int(33*scale), x+int(26*scale), y+int(33*scale)), fill=outline, width=max(2, int(4*scale)))
        self._draw_effects(draw, list(plan.get("effects", [])), x, y, int(plan.get("intensity", 60)))

    def _phrase_box(self, draw: ImageDraw.ImageDraw, phrase: str, text_motion: str, text_x: int, text_y: int, font_size: int) -> Dict[str, Any]:
        font = self._font(font_size)
        lines = self._wrap(phrase, 12)
        widths = [self._text_size(draw, line, font)[0] for line in lines]
        line_h = font_size + 4
        bw = min(300, max(widths or [80]) + 34)
        bh = len(lines) * line_h + 26
        if "축 처짐" in text_motion:
            text_y += 10
        if "도장" in text_motion:
            box_fill = (255, 245, 230, 235); border = (205, 80, 70, 255)
        elif "부들" in text_motion or "떨림" in text_motion:
            box_fill = (255, 245, 245, 235); border = (210, 70, 70, 255)
        else:
            box_fill = (255, 255, 255, 235); border = (55, 55, 55, 255)
        left = max(14, min(346-bw, text_x - bw//2)); top = max(12, min(346-bh, text_y))
        draw.rounded_rectangle((left, top, left+bw, top+bh), radius=18, fill=box_fill, outline=border, width=3)
        for idx, line in enumerate(lines):
            tw, th = self._text_size(draw, line, font)
            draw.text((left + (bw-tw)//2, top + 12 + idx*line_h), line, font=font, fill=(35, 35, 35, 255))
        return {"box": [left, top, left+bw, top+bh], "lines": lines, "font_size": font_size}

    def render_preview(self, row: Dict[str, Any], output_path: Path, format_key: str = "static_text") -> Dict[str, Any]:
        phrase = str(row.get("phrase", "표현"))
        plan = dict(row.get("expression_plan", {}) or {})
        if not plan:
            plan = {"eye_style":"normal", "brow_style":"soft", "mouth_style":"smile", "body_motion":"기본 자세", "text_motion":"고정", "effects":[], "intensity":60}
        img = Image.new("RGBA", (self.size, self.size), (255,255,255,0))
        draw = ImageDraw.Draw(img)
        # 캐릭터 위치/문구 위치 조정값
        char_x = int(row.get("char_x", 178)); char_y = int(row.get("char_y", 142))
        text_x = int(row.get("text_x", 180)); text_y = int(row.get("text_y", 250))
        font_size = int(row.get("font_size", 28))
        color = str(row.get("preview_color", "아이보리"))
        if "animated" in format_key:
            # 정적 대표 컷은 중간 프레임 느낌으로 조금 더 강조
            plan["intensity"] = min(95, int(plan.get("intensity", 60)) + 5)
        self._draw_face(draw, char_x, char_y, plan, color=color, scale=float(row.get("scale", 1.0)))
        text_info = self._phrase_box(draw, phrase, str(plan.get("text_motion", "고정")), text_x, text_y, font_size)
        # 편집 상태 배지
        if row.get("manual_edited"):
            badge_font = self._font(13)
            draw.rounded_rectangle((12,12,72,34), radius=8, fill=(255, 245, 160, 240), outline=(80,80,50,255), width=2)
            draw.text((22,15), "수정", font=badge_font, fill=(40,40,20,255))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        return {
            "file_path": str(output_path),
            "file_name": output_path.name,
            "kind": "png_preview",
            "phrase": phrase,
            "checksum_sha256": self._checksum(output_path),
            "text_box": text_info.get("box"),
        }

    def render_gif_preview(self, row: Dict[str, Any], output_path: Path) -> Optional[Dict[str, Any]]:
        if AnimatedTextFrameBuilder is None:
            return None
        # 정적 대표 캐릭터 PNG를 먼저 만든 후 기존 GIF 빌더에 전달
        temp_png = output_path.with_suffix(".base.png")
        static_info = self.render_preview(row, temp_png, format_key="static_text")
        phrase = str(row.get("phrase", "표현"))
        plan = dict(row.get("expression_plan", {}) or {})
        text_motion = str(plan.get("text_motion", "천천히 나타남"))
        body_motion = str(plan.get("body_motion", "통통 튐"))
        # 기존 빌더가 지원하는 대표 동작명에 매핑
        char_motion = "통통 튐"
        if "꾸벅" in body_motion:
            char_motion = "꾸벅"
        elif "작아" in body_motion:
            char_motion = "작아짐"
        elif "떨" in body_motion or "부들" in body_motion:
            char_motion = "부들부들 흔들림"
        elif "처짐" in body_motion or "잠" in body_motion:
            char_motion = "축 처짐"
        try:
            AnimatedTextFrameBuilder().build_gif(temp_png, phrase, output_path, text_motion=text_motion, character_motion=char_motion)
            return {
                "file_path": str(output_path),
                "file_name": output_path.name,
                "kind": "gif_preview",
                "phrase": phrase,
                "checksum_sha256": self._checksum(output_path),
            }
        except Exception:
            return None

    def build_timeline(self, row: Dict[str, Any]) -> List[Dict[str, Any]]:
        plan = dict(row.get("expression_plan", {}) or {})
        phrase = str(row.get("phrase", ""))
        body = plan.get("body_motion", "기본 자세")
        text_motion = plan.get("text_motion", "고정")
        effects = ", ".join(plan.get("effects", [])) or "없음"
        return [
            {"frame": 1, "캐릭터": "기본 자세", "문구": "숨김/대기", "효과": "없음"},
            {"frame": 2, "캐릭터": body, "문구": "문구 등장 준비", "효과": "없음"},
            {"frame": 3, "캐릭터": body, "문구": text_motion, "효과": effects},
            {"frame": 4, "캐릭터": "최종 자세 유지", "문구": phrase, "효과": effects},
            {"frame": 5, "캐릭터": "반복 재생 연결", "문구": "가독성 유지", "효과": "정리"},
        ]

    def apply_overrides(
        self,
        expressions: List[Dict[str, Any]],
        global_overrides: Optional[Dict[str, Any]] = None,
        per_expression_overrides: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        edited: List[Dict[str, Any]] = []
        global_overrides = global_overrides or {}
        per_expression_overrides = per_expression_overrides or {}
        for idx, row in enumerate(expressions, start=1):
            new = dict(row)
            plan = dict(new.get("expression_plan", {}) or {})
            # 기본 expression_plan이 없을 때 최소값을 채움
            plan.setdefault("eye_style", "normal")
            plan.setdefault("brow_style", "soft")
            plan.setdefault("mouth_style", "smile")
            plan.setdefault("body_motion", "기본 자세")
            plan.setdefault("text_motion", "고정")
            plan.setdefault("effects", [])
            plan.setdefault("intensity", 60)
            for key in ["eye_style", "brow_style", "mouth_style", "body_motion", "text_motion"]:
                if global_overrides.get(key) not in [None, "자동 유지", ""]:
                    plan[key] = global_overrides[key]
            if global_overrides.get("effects") not in [None, "자동 유지", ""]:
                eff = global_overrides["effects"]
                plan["effects"] = [] if eff == "none" else [eff]
            if global_overrides.get("font_size"):
                new["font_size"] = int(global_overrides["font_size"])
            if global_overrides.get("char_x") is not None:
                new["char_x"] = int(global_overrides["char_x"])
            if global_overrides.get("char_y") is not None:
                new["char_y"] = int(global_overrides["char_y"])
            if global_overrides.get("text_x") is not None:
                new["text_x"] = int(global_overrides["text_x"])
            if global_overrides.get("text_y") is not None:
                new["text_y"] = int(global_overrides["text_y"])
            specific = per_expression_overrides.get(idx) or per_expression_overrides.get(int(new.get("selected_no", idx))) or {}
            for key, value in specific.items():
                if key in ["eye_style", "brow_style", "mouth_style", "body_motion", "text_motion"] and value:
                    plan[key] = value
                elif key == "effects" and value:
                    plan["effects"] = [] if value == "none" else [value]
                elif key in ["font_size", "char_x", "char_y", "text_x", "text_y", "scale"]:
                    new[key] = value
            new["expression_plan"] = plan
            new["face_summary"] = self.summarize_plan(plan)
            new["manual_edited"] = bool(global_overrides or specific)
            edited.append(new)
        return edited

    def summarize_plan(self, plan: Dict[str, Any]) -> str:
        effects = ",".join(plan.get("effects", [])) or "효과 없음"
        return f"눈:{plan.get('eye_style')} · 입:{plan.get('mouth_style')} · 몸:{plan.get('body_motion')} · 문구:{plan.get('text_motion')} · 효과:{effects}"

    def final_check(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for idx, row in enumerate(rows, start=1):
            phrase = str(row.get("phrase", ""))
            plan = row.get("expression_plan", {}) or {}
            warnings = []
            if len(phrase) > 18 and int(row.get("font_size", 28)) > 26:
                warnings.append("문구가 길어 글자 크기 축소 권장")
            if not plan.get("eye_style") or not plan.get("mouth_style"):
                warnings.append("표정 파츠 누락")
            if "animated" in str(row.get("format_key", "")) and plan.get("text_motion") in ["고정", ""]:
                warnings.append("움직이는 포맷은 문구 움직임 보완 권장")
            status = "완료" if not warnings else "수정 필요"
            result.append({
                "번호": row.get("selected_no", idx),
                "문구": phrase,
                "감정": row.get("category", ""),
                "눈": plan.get("eye_style", ""),
                "입": plan.get("mouth_style", ""),
                "몸동작": plan.get("body_motion", ""),
                "문구움직임": plan.get("text_motion", ""),
                "상태": status,
                "보완메모": "; ".join(warnings),
            })
        return result

    def build_edit_pack(
        self,
        expressions: List[Dict[str, Any]],
        output_dir: Path,
        project_name: str = "part_motion_editor",
        format_key: str = "static_text",
        global_overrides: Optional[Dict[str, Any]] = None,
        per_expression_overrides: Optional[Dict[int, Dict[str, Any]]] = None,
        preview_limit: int = 32,
    ) -> PartEditReport:
        safe_project = self._safe_name(project_name)
        root = output_dir / safe_project
        preview_dir = root / "previews"
        root.mkdir(parents=True, exist_ok=True)
        edited = self.apply_overrides(expressions, global_overrides, per_expression_overrides)
        for row in edited:
            row["format_key"] = format_key
        preview_files: List[Dict[str, Any]] = []
        for idx, row in enumerate(edited[:preview_limit], start=1):
            suffix = "gif" if "animated" in format_key else "png"
            fp = preview_dir / f"{idx:02d}_{self._safe_name(row.get('phrase','item'))}.{suffix}"
            if suffix == "gif":
                gif_info = self.render_gif_preview(row, fp)
                if gif_info:
                    preview_files.append(gif_info)
                else:
                    preview_files.append(self.render_preview(row, fp.with_suffix(".png"), format_key="static_text"))
            else:
                preview_files.append(self.render_preview(row, fp, format_key=format_key))
        final_table = self.final_check(edited)
        timeline_table: List[Dict[str, Any]] = []
        for idx, row in enumerate(edited[:min(8, len(edited))], start=1):
            for frame in self.build_timeline(row):
                timeline_table.append({"표현번호": row.get("selected_no", idx), "문구": row.get("phrase", ""), **frame})
        # save csv/json/html/zip
        csv_path = root / "part_motion_edit_table.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            fieldnames = ["selected_no", "category", "phrase", "face_summary", "manual_edited"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in edited:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        data = {
            "project_name": project_name,
            "format_key": format_key,
            "source_count": len(expressions),
            "edited_count": len(edited),
            "edit_options": self.edit_options(),
            "edited_expressions": edited,
            "preview_files": preview_files,
            "final_check_table": final_table,
            "timeline_table": timeline_table,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        json_path = root / "part_motion_edit_report.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path = root / "part_motion_edit_report.html"
        html_path.write_text(self._html(data), encoding="utf-8")
        zip_path = root / "part_motion_edit_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in [csv_path, json_path, html_path]:
                zf.write(p, p.relative_to(root))
            for item in preview_files:
                fp = Path(item.get("file_path", ""))
                if fp.exists():
                    zf.write(fp, fp.relative_to(root))
        return PartEditReport(
            project_name=project_name,
            source_count=len(expressions),
            edited_count=len(edited),
            format_key=format_key,
            edit_options=self.edit_options(),
            edited_expressions=edited,
            preview_files=preview_files,
            final_check_table=final_table,
            timeline_table=timeline_table,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
        )

    def _html(self, data: Dict[str, Any]) -> str:
        def esc(x: Any) -> str:
            return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows = "".join(
            f"<tr><td>{esc(r.get('selected_no',''))}</td><td>{esc(r.get('category',''))}</td><td>{esc(r.get('phrase',''))}</td><td>{esc(r.get('face_summary',''))}</td></tr>"
            for r in data.get("edited_expressions", [])
        )
        checks = "".join(
            f"<tr><td>{esc(r.get('번호',''))}</td><td>{esc(r.get('문구',''))}</td><td>{esc(r.get('눈',''))}</td><td>{esc(r.get('입',''))}</td><td>{esc(r.get('몸동작',''))}</td><td>{esc(r.get('상태',''))}</td><td>{esc(r.get('보완메모',''))}</td></tr>"
            for r in data.get("final_check_table", [])
        )
        previews = "".join(
            f"<div class='card'><img src='{esc(Path(p.get('file_path','')).name if Path(p.get('file_path','')).suffix.lower()!='.gif' else p.get('file_path',''))}'><p>{esc(p.get('phrase',''))}</p></div>"
            for p in data.get("preview_files", [])[:12]
        )
        # html lives at root, preview image is in previews/; fix relative path
        previews = "".join(
            f"<div class='card'><img src='previews/{esc(Path(p.get('file_path','')).name)}'><p>{esc(p.get('phrase',''))}</p></div>"
            for p in data.get("preview_files", [])[:12]
        )
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v18 표정·파츠 편집 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;background:#fafafa;color:#222}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{border:1px solid #ddd;padding:8px;font-size:13px}}th{{background:#f0f0f0}}.grid{{display:flex;flex-wrap:wrap;gap:12px}}.card{{background:white;border:1px solid #ddd;border-radius:10px;padding:8px;width:150px;text-align:center}}.card img{{width:128px;height:128px;object-fit:contain}}</style></head><body>
<h1>v18 표정·파츠·문구·움직임 편집 리포트</h1>
<p><b>프로젝트:</b> {esc(data.get('project_name'))} / <b>포맷:</b> {esc(data.get('format_key'))} / <b>편집 표현:</b> {esc(data.get('edited_count'))}</p>
<h2>미리보기</h2><div class='grid'>{previews}</div>
<h2>편집 표현표</h2><table><tr><th>번호</th><th>감정</th><th>문구</th><th>표정 요약</th></tr>{rows}</table>
<h2>최종 확인표</h2><table><tr><th>번호</th><th>문구</th><th>눈</th><th>입</th><th>몸동작</th><th>상태</th><th>보완메모</th></tr>{checks}</table>
</body></html>"""
