from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib
import math
import re
import zipfile

from PIL import Image, ImageDraw

from modules.animated_text_emoticon.font_utils import load_font
from modules.character_search_center.multi_source_mixer import MaterialToken, MultiImageBlendProfile, BlendConcept
from modules.expression_bank.expression_generator import ExpressionItem


@dataclass
class PrototypeSpec:
    name: str
    materials: list[str]
    body_shape: str
    palette: list[str]
    face_style: str
    accessory: str
    motion_hint: str
    originality_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PrototypeResult:
    spec: dict[str, Any]
    file_path: str
    preview_label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CharacterPrototypeBuilder:
    """직접 합성/복제 없이 소재 힌트만 기반으로 360x360 절차형 캐릭터 시안을 만듭니다.

    이 모듈은 기존 캐릭터나 첨부 사진의 구체적 표현을 옮기는 기능이 아닙니다.
    색상, 물성, 분위기 같은 추상 힌트만 받아 단순 도형 기반 새 시안을 생성합니다.
    """

    CANVAS = (360, 360)
    DEFAULT_PALETTE = ["#D8B36A", "#F4E6B5", "#7C5E3C", "#2A2A2A", "#FFFFFF"]
    SHAPES = ["둥근형", "길쭉형", "납작형", "네모형", "알갱이형", "듀오형"]
    FACE_STYLES = ["무표정", "공손한 미소", "피곤한 눈", "당황한 점눈", "뿌듯한 표정"]
    ACCESSORIES = ["싹", "작은 메모", "체크 도장", "땀방울", "말풍선 꼬리", "작은 잎", "없음"]

    MATERIAL_COLORS = {
        "보리": ["#C99A4A", "#E8D28A", "#7B5B2D"],
        "쌀": ["#F8F4E6", "#E0D4B8", "#BFB19A"],
        "쌀알": ["#F8F4E6", "#E7DDC9", "#9D8F78"],
        "감자": ["#C79A60", "#E3C28B", "#7A5A38"],
        "고구마": ["#8E5572", "#E0B05D", "#5A3148"],
        "메모지": ["#FFF4A3", "#F1DF70", "#655F38"],
        "돌멩이": ["#8B8F92", "#C1C5C8", "#4E5154"],
        "무": ["#F7F7EE", "#6BAA53", "#5D6A50"],
        "콩": ["#79A85B", "#B4D28B", "#3D5F30"],
        "양말": ["#D8E7F0", "#FFFFFF", "#4F6D7A"],
    }

    def build_specs(
        self,
        materials: list[MaterialToken] | None,
        image_blend: MultiImageBlendProfile | None,
        blend_concepts: list[BlendConcept] | list[dict[str, Any]] | None,
        count: int = 6,
    ) -> list[PrototypeSpec]:
        material_names = [m.name for m in (materials or [])] or self._materials_from_concepts(blend_concepts) or ["메모지", "감자"]
        seed_text = "|".join(material_names) + "|" + (image_blend.blend_direction if image_blend else "")
        seed = self._stable_int(seed_text)
        base_palette = self._palette_from_materials(material_names)
        if image_blend and image_blend.dominant_color_palette:
            base_palette = self._merge_palette(base_palette, image_blend.dominant_color_palette)
        specs: list[PrototypeSpec] = []
        for i in range(count):
            shape = self._pick_shape(material_names, image_blend, seed + i)
            face = self.FACE_STYLES[(seed + i * 2) % len(self.FACE_STYLES)]
            accessory = self._pick_accessory(material_names, seed + i)
            motion = self._motion_hint(material_names, shape, i)
            name = self._prototype_name(material_names, i)
            specs.append(
                PrototypeSpec(
                    name=name,
                    materials=material_names,
                    body_shape=shape,
                    palette=self._rotate_palette(base_palette, i),
                    face_style=face,
                    accessory=accessory,
                    motion_hint=motion,
                    originality_note="첨부 이미지/단어의 구체적 외형을 복제하지 않고, 색감·물성·상징만 단순 도형 캐릭터로 재해석한 시안입니다.",
                )
            )
        return specs

    def render_prototypes(self, specs: list[PrototypeSpec], output_dir: str | Path) -> list[PrototypeResult]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        results: list[PrototypeResult] = []
        for idx, spec in enumerate(specs, start=1):
            img = self.render_single(spec, expression="기본")
            safe_name = self._safe_filename(f"prototype_{idx:02d}_{spec.name}.png")
            path = output_dir / safe_name
            img.save(path)
            results.append(PrototypeResult(spec.to_dict(), str(path), f"{idx:02d}. {spec.name}"))
        return results

    def render_expression_pack(
        self,
        spec: PrototypeSpec,
        expressions: list[ExpressionItem] | list[dict[str, Any]] | None,
        output_dir: str | Path,
        count: int = 12,
    ) -> list[str]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        expr_dicts = []
        for item in expressions or []:
            if hasattr(item, "to_dict"):
                expr_dicts.append(item.to_dict())
            elif isinstance(item, dict):
                expr_dicts.append(item)
        if not expr_dicts:
            expr_dicts = [
                {"phrase": "넵", "emotion": "확인"},
                {"phrase": "확인했습니다", "emotion": "확인"},
                {"phrase": "감사합니다", "emotion": "감사"},
                {"phrase": "죄송합니다", "emotion": "사과"},
                {"phrase": "퇴근하고 싶습니다", "emotion": "피곤"},
                {"phrase": "잠시만요", "emotion": "기다림"},
                {"phrase": "좋아요", "emotion": "기쁨"},
                {"phrase": "살려주세요", "emotion": "당황"},
            ]
        files: list[str] = []
        for idx, expr in enumerate(expr_dicts[:count], start=1):
            phrase = str(expr.get("phrase") or expr.get("text") or "확인했습니다")
            emotion = str(expr.get("emotion") or expr.get("category") or "기본")
            img = self.render_single(spec, expression=emotion, phrase=phrase)
            path = output_dir / self._safe_filename(f"expr_{idx:02d}_{phrase[:12]}.png")
            img.save(path)
            files.append(str(path))
        return files

    def zip_files(self, file_paths: list[str], output_zip: str | Path) -> Path:
        output_zip = Path(output_zip)
        output_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in file_paths:
                path = Path(fp)
                if path.exists():
                    zf.write(path, arcname=path.name)
        return output_zip

    def render_single(self, spec: PrototypeSpec, expression: str = "기본", phrase: str | None = None) -> Image.Image:
        canvas = Image.new("RGBA", self.CANVAS, (255, 255, 255, 0))
        draw = ImageDraw.Draw(canvas)
        palette = self._normalize_palette(spec.palette)
        fill = palette[0]
        fill2 = palette[1] if len(palette) > 1 else self.DEFAULT_PALETTE[1]
        outline = palette[2] if len(palette) > 2 else "#2A2A2A"
        shadow = Image.new("RGBA", self.CANVAS, (255, 255, 255, 0))
        sd = ImageDraw.Draw(shadow)
        sd.ellipse((106, 252, 254, 278), fill=(0, 0, 0, 26))
        canvas.alpha_composite(shadow)

        bbox = self._body_bbox(spec.body_shape)
        if spec.body_shape == "듀오형":
            self._draw_duo(draw, fill, fill2, outline)
            face_centers = [(142, 172), (218, 172)]
        else:
            self._draw_body(draw, bbox, spec.body_shape, fill, fill2, outline)
            face_centers = [(180, 168)]

        self._draw_texture(draw, spec, bbox, outline)
        for cx, cy in face_centers:
            self._draw_face(draw, cx, cy, spec.face_style, expression)
        self._draw_accessory(draw, spec.accessory, bbox, palette, outline)
        self._draw_limbs(draw, bbox, outline, expression)
        if phrase:
            self._draw_phrase(canvas, phrase)
        return canvas

    def _draw_body(self, draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], shape: str, fill: str, fill2: str, outline: str) -> None:
        if shape == "네모형":
            draw.rounded_rectangle(bbox, radius=28, fill=fill, outline=outline, width=4)
            draw.line((bbox[0] + 20, bbox[1] + 28, bbox[2] - 20, bbox[1] + 28), fill=fill2, width=3)
        elif shape == "길쭉형":
            draw.rounded_rectangle(bbox, radius=55, fill=fill, outline=outline, width=4)
            draw.arc((bbox[0] + 28, bbox[1] + 28, bbox[2] - 28, bbox[3] - 28), 110, 240, fill=fill2, width=5)
        elif shape == "납작형":
            draw.rounded_rectangle(bbox, radius=40, fill=fill, outline=outline, width=4)
            draw.ellipse((bbox[0] + 25, bbox[1] + 30, bbox[2] - 25, bbox[3] - 30), outline=fill2, width=5)
        elif shape == "알갱이형":
            for dx, dy, s in [(-45, -16, 78), (26, -20, 72), (-10, 42, 70), (54, 36, 58)]:
                draw.ellipse((180+dx-s//2, 170+dy-s//2, 180+dx+s//2, 170+dy+s//2), fill=fill, outline=outline, width=3)
        else:
            draw.ellipse(bbox, fill=fill, outline=outline, width=4)
            draw.arc((bbox[0] + 22, bbox[1] + 28, bbox[2] - 24, bbox[3] - 26), 210, 330, fill=fill2, width=5)

    def _draw_duo(self, draw: ImageDraw.ImageDraw, fill: str, fill2: str, outline: str) -> None:
        draw.ellipse((72, 82, 190, 238), fill=fill, outline=outline, width=4)
        draw.rounded_rectangle((176, 96, 286, 242), radius=48, fill=fill2, outline=outline, width=4)
        draw.arc((100, 230, 260, 300), 200, 340, fill=outline, width=3)

    def _draw_face(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, face_style: str, expression: str) -> None:
        eye_y = cy - 18
        if "피곤" in face_style or "피곤" in expression:
            draw.line((cx - 38, eye_y, cx - 22, eye_y + 4), fill=(25, 25, 25), width=4)
            draw.line((cx + 22, eye_y + 4, cx + 38, eye_y), fill=(25, 25, 25), width=4)
            draw.arc((cx - 22, cy + 10, cx + 22, cy + 32), 180, 360, fill=(25, 25, 25), width=3)
        elif "당황" in expression:
            draw.ellipse((cx - 42, eye_y - 7, cx - 26, eye_y + 9), fill=(25, 25, 25))
            draw.ellipse((cx + 26, eye_y - 7, cx + 42, eye_y + 9), fill=(25, 25, 25))
            draw.ellipse((cx - 10, cy + 9, cx + 10, cy + 27), outline=(25, 25, 25), width=3)
        elif "기쁨" in expression or "미소" in face_style or "감사" in expression:
            draw.arc((cx - 45, eye_y - 10, cx - 20, eye_y + 12), 10, 170, fill=(25, 25, 25), width=3)
            draw.arc((cx + 20, eye_y - 10, cx + 45, eye_y + 12), 10, 170, fill=(25, 25, 25), width=3)
            draw.arc((cx - 24, cy - 2, cx + 24, cy + 35), 0, 180, fill=(25, 25, 25), width=3)
        else:
            draw.ellipse((cx - 42, eye_y - 6, cx - 28, eye_y + 8), fill=(25, 25, 25))
            draw.ellipse((cx + 28, eye_y - 6, cx + 42, eye_y + 8), fill=(25, 25, 25))
            if "사과" in expression:
                draw.arc((cx - 24, cy + 14, cx + 24, cy + 36), 180, 360, fill=(25, 25, 25), width=3)
            else:
                draw.line((cx - 22, cy + 20, cx + 22, cy + 20), fill=(25, 25, 25), width=3)

    def _draw_accessory(self, draw: ImageDraw.ImageDraw, accessory: str, bbox: tuple[int, int, int, int], palette: list[str], outline: str) -> None:
        x1, y1, x2, y2 = bbox
        if accessory in ["싹", "작은 잎"]:
            draw.line((180, y1 + 4, 180, y1 - 30), fill=outline, width=4)
            draw.ellipse((180, y1 - 44, 224, y1 - 18), fill="#7AB45A", outline=outline, width=3)
            draw.ellipse((136, y1 - 42, 180, y1 - 18), fill="#90C96B", outline=outline, width=3)
        elif accessory == "작은 메모":
            draw.rounded_rectangle((222, 78, 284, 126), radius=8, fill="#FFF8B8", outline=outline, width=3)
            draw.line((232, 94, 274, 94), fill=outline, width=2)
            draw.line((232, 108, 264, 108), fill=outline, width=2)
        elif accessory == "체크 도장":
            draw.rounded_rectangle((225, 76, 288, 126), radius=10, fill="#FFFFFF", outline=outline, width=3)
            draw.line((240, 102, 254, 115), fill="#29884A", width=5)
            draw.line((254, 115, 276, 86), fill="#29884A", width=5)
        elif accessory == "땀방울":
            draw.ellipse((244, 106, 266, 136), fill="#84C8E8", outline=outline, width=2)
        elif accessory == "말풍선 꼬리":
            draw.polygon([(232, 248), (282, 262), (246, 284)], fill="#FFFFFF", outline=outline)

    def _draw_texture(self, draw: ImageDraw.ImageDraw, spec: PrototypeSpec, bbox: tuple[int, int, int, int], outline: str) -> None:
        x1, y1, x2, y2 = bbox
        mats = " ".join(spec.materials)
        if any(m in mats for m in ["보리", "쌀", "쌀알", "콩"]):
            for i in range(8):
                px = x1 + 32 + (i * 23) % max(1, (x2 - x1 - 64))
                py = y1 + 34 + (i * 29) % max(1, (y2 - y1 - 70))
                draw.ellipse((px, py, px + 8, py + 12), fill=(255, 255, 255, 90), outline=None)
        if any(m in mats for m in ["메모지", "종이"]):
            draw.line((x1 + 34, y1 + 46, x2 - 34, y1 + 46), fill=outline, width=2)
            draw.line((x1 + 34, y1 + 76, x2 - 50, y1 + 76), fill=outline, width=2)
        if "돌" in mats:
            for i in range(3):
                draw.arc((x1 + 40 + i * 28, y1 + 54 + i * 18, x1 + 90 + i * 30, y1 + 90 + i * 22), 200, 330, fill=(80, 80, 80), width=2)

    def _draw_limbs(self, draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], outline: str, expression: str) -> None:
        x1, y1, x2, y2 = bbox
        if "감사" in expression or "사과" in expression:
            draw.arc((x1 - 24, y1 + 100, x1 + 44, y1 + 166), 290, 70, fill=outline, width=5)
            draw.arc((x2 - 44, y1 + 100, x2 + 24, y1 + 166), 110, 250, fill=outline, width=5)
        else:
            draw.line((x1 + 8, y1 + 112, x1 - 30, y1 + 130), fill=outline, width=5)
            draw.line((x2 - 8, y1 + 112, x2 + 30, y1 + 130), fill=outline, width=5)
        draw.line((160, y2 - 4, 150, y2 + 22), fill=outline, width=5)
        draw.line((200, y2 - 4, 210, y2 + 22), fill=outline, width=5)

    def _draw_phrase(self, canvas: Image.Image, phrase: str) -> None:
        draw = ImageDraw.Draw(canvas)
        font_size = 34 if len(phrase) <= 4 else 28 if len(phrase) <= 8 else 22 if len(phrase) <= 13 else 18
        font = load_font(font_size)
        bbox = draw.textbbox((0, 0), phrase, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        bubble_w = min(336, tw + 32)
        bubble_h = th + 22
        bx = (360 - bubble_w) // 2
        by = 284
        draw.rounded_rectangle((bx, by, bx + bubble_w, by + bubble_h), radius=18, fill=(255, 255, 255, 244), outline=(30, 30, 30, 230), width=2)
        draw.text((bx + (bubble_w - tw) // 2, by + (bubble_h - th) // 2 - 2), phrase, font=font, fill=(20, 20, 20, 255))

    def _body_bbox(self, shape: str) -> tuple[int, int, int, int]:
        if shape == "길쭉형":
            return (116, 62, 244, 256)
        if shape == "납작형":
            return (76, 118, 284, 242)
        if shape == "네모형":
            return (88, 72, 272, 250)
        return (88, 70, 272, 254)

    def _palette_from_materials(self, material_names: list[str]) -> list[str]:
        palette: list[str] = []
        for name in material_names:
            for color in self.MATERIAL_COLORS.get(name, []):
                if color not in palette:
                    palette.append(color)
        return palette or self.DEFAULT_PALETTE[:]

    def _merge_palette(self, a: list[str], b: list[str]) -> list[str]:
        out: list[str] = []
        for color in a + b:
            if self._is_hex(color) and color not in out:
                out.append(color)
        return out[:6] or self.DEFAULT_PALETTE[:]

    def _rotate_palette(self, palette: list[str], i: int) -> list[str]:
        if not palette:
            return self.DEFAULT_PALETTE[:]
        rot = i % len(palette)
        return (palette[rot:] + palette[:rot])[:6]

    def _normalize_palette(self, palette: list[str]) -> list[str]:
        valid = [p for p in palette if self._is_hex(p)]
        return valid or self.DEFAULT_PALETTE[:]

    def _pick_shape(self, material_names: list[str], image_blend: MultiImageBlendProfile | None, seed: int) -> str:
        joined = " ".join(material_names)
        if "고구마" in joined or "양말" in joined:
            return "길쭉형"
        if "메모" in joined or "종이" in joined:
            return "네모형"
        if "쌀" in joined or "보리" in joined or "콩" in joined:
            return "알갱이형"
        if len(material_names) >= 2 and seed % 3 == 0:
            return "듀오형"
        return self.SHAPES[seed % len(self.SHAPES)]

    def _pick_accessory(self, material_names: list[str], seed: int) -> str:
        joined = " ".join(material_names)
        if "감자" in joined or "무" in joined:
            return "싹"
        if "메모" in joined:
            return "체크 도장"
        if "보리" in joined:
            return "작은 잎"
        return self.ACCESSORIES[seed % len(self.ACCESSORIES)]

    def _motion_hint(self, material_names: list[str], shape: str, i: int) -> str:
        joined = " ".join(material_names)
        if "메모" in joined:
            return "구겨졌다 펴지며 문구가 도장처럼 찍힘"
        if "감자" in joined:
            return "칭찬/감사 표현에서 싹이 작게 자람"
        if "고구마" in joined:
            return "답답한 감정에서 김이 모락 올라옴"
        if "쌀" in joined or "보리" in joined:
            return "낟알이 톡톡 모였다 흩어짐"
        if shape == "듀오형":
            return "한쪽은 말하고 한쪽은 반응하는 콤비 움직임"
        return ["작게 꾸벅", "부들부들 흔들림", "통통 튐", "축 처짐"][i % 4]

    def _prototype_name(self, material_names: list[str], i: int) -> str:
        if len(material_names) == 1:
            base = material_names[0]
        elif len(material_names) == 2:
            base = f"{material_names[0]}와 {material_names[1]}"
        else:
            base = f"{material_names[0]}·{material_names[1]} 외 {len(material_names)-2}종"
        suffixes = ["기본형", "콤비형", "말풍선형", "알갱이형", "직장인형", "시그니처형"]
        return f"{base} {suffixes[i % len(suffixes)]}"

    def _materials_from_concepts(self, concepts: list[BlendConcept] | list[dict[str, Any]] | None) -> list[str]:
        if not concepts:
            return []
        first = concepts[0]
        if isinstance(first, dict):
            return list(first.get("materials", []))
        return list(first.materials)

    def _stable_int(self, text: str) -> int:
        return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)

    def _safe_filename(self, name: str) -> str:
        cleaned = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", name)
        return cleaned[:96]

    def _is_hex(self, color: str) -> bool:
        return isinstance(color, str) and bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", color))
