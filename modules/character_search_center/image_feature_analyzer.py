from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass
class ImageFeatureProfile:
    width: int
    height: int
    has_alpha: bool
    aspect_ratio: float
    dominant_colors: list[str]
    small_screen_warning: str
    shape_hint: str
    motion_hint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ImageFeatureAnalyzer:
    def analyze(self, image_path: str | Path) -> ImageFeatureProfile:
        image = Image.open(image_path).convert("RGBA")
        width, height = image.size
        has_alpha = image.getchannel("A").getextrema()[0] < 255
        colors = self._dominant_colors(image)
        ratio = round(width / height, 3) if height else 0
        warning = "적합" if min(width, height) >= 256 else "원본 해상도가 낮아 360×360 작업 시 품질 저하 가능"
        shape_hint = self._shape_hint(width, height)
        motion_hint = self._motion_hint(shape_hint)
        return ImageFeatureProfile(width, height, has_alpha, ratio, colors, warning, shape_hint, motion_hint)

    def _dominant_colors(self, image: Image.Image, max_colors: int = 5) -> list[str]:
        small = image.resize((80, 80))
        # 투명 픽셀은 제외
        pixels = [p for p in small.getdata() if p[3] > 20]
        if not pixels:
            return []
        rgb = Image.new("RGB", (len(pixels), 1))
        rgb.putdata([(r, g, b) for r, g, b, _ in pixels])
        pal = rgb.quantize(colors=max_colors)
        palette = pal.getpalette() or []
        counts = sorted(pal.getcolors(), reverse=True)
        result = []
        for _, idx in counts[:max_colors]:
            base = idx * 3
            result.append("#%02x%02x%02x" % tuple(palette[base:base+3]))
        return result

    def _shape_hint(self, width: int, height: int) -> str:
        ratio = width / height if height else 1
        if 0.85 <= ratio <= 1.15:
            return "정방형/둥근형 후보"
        if ratio > 1.15:
            return "가로형/납작한 캐릭터 후보"
        return "세로형/길쭉한 캐릭터 후보"

    def _motion_hint(self, shape_hint: str) -> str:
        if "납작" in shape_hint:
            return "구겨짐, 펴짐, 좌우 흔들림, 도장 찍힘 동작 추천"
        if "길쭉" in shape_hint:
            return "꾸벅, 흔들림, 접힘, 점프 동작 추천"
        return "통통 튐, 작아짐, 커짐, 눈/입 표정 변화 추천"
