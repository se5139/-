from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from modules.animated_text_emoticon.font_utils import load_font
from modules.animated_text_emoticon.text_motion_templates import TEXT_MOTION_PRESETS


class AnimatedTextFrameBuilder:
    CANVAS = (360, 360)

    def build_gif(
        self,
        base_image_path: str | Path,
        phrase: str,
        output_path: str | Path,
        text_motion: str = "도장처럼 등장",
        character_motion: str = "통통 튐",
        duration_ms: int = 110,
        frames: int = 8,
    ) -> Path:
        base = Image.open(base_image_path).convert("RGBA")
        base.thumbnail((250, 230), Image.LANCZOS)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        preset = TEXT_MOTION_PRESETS.get(text_motion, TEXT_MOTION_PRESETS["도장처럼 등장"])
        rendered_frames = []
        for i in range(frames):
            canvas = Image.new("RGBA", self.CANVAS, (255, 255, 255, 0))
            char = self._apply_character_motion(base, i, frames, character_motion)
            char_x = (self.CANVAS[0] - char.width) // 2
            char_y = 36 + self._char_y_offset(i, frames, character_motion)
            canvas.alpha_composite(char, (char_x, char_y))
            self._draw_bubble_and_text(canvas, phrase, i, frames, preset)
            rendered_frames.append(canvas)
        rendered_frames[0].save(
            output_path,
            save_all=True,
            append_images=rendered_frames[1:],
            duration=duration_ms,
            loop=0,
            disposal=2,
            optimize=True,
        )
        return output_path

    def _apply_character_motion(self, base: Image.Image, i: int, frames: int, motion: str) -> Image.Image:
        if "부들" in motion or "흔들" in motion:
            return base.rotate([-2, 2, -2, 2, -1, 1, 0, 0][i % 8], resample=Image.BICUBIC, expand=True)
        if "작아" in motion:
            scale = [1.0, 0.96, 0.92, 0.88, 0.86, 0.88, 0.92, 1.0][i % 8]
            return base.resize((int(base.width * scale), int(base.height * scale)), Image.LANCZOS)
        if "꾸벅" in motion:
            return base.rotate([0, 3, 6, 8, 6, 3, 0, 0][i % 8], resample=Image.BICUBIC, expand=True)
        return base

    def _char_y_offset(self, i: int, frames: int, motion: str) -> int:
        if "통통" in motion or "튐" in motion:
            return int(math.sin(i / frames * math.pi * 2) * -8)
        if "축" in motion or "피곤" in motion:
            return [0, 2, 5, 8, 11, 8, 5, 0][i % 8]
        return 0

    def _draw_bubble_and_text(self, canvas: Image.Image, phrase: str, i: int, frames: int, preset: dict) -> None:
        draw = ImageDraw.Draw(canvas)
        scale_seq = preset.get("scale_sequence", [1.0] * frames)
        alpha_seq = preset.get("alpha_sequence", [255] * frames)
        x_seq = preset.get("x_offset_sequence", [0] * frames)
        y_seq = preset.get("y_offset_sequence", [0] * frames)
        scale = scale_seq[i % len(scale_seq)]
        alpha = alpha_seq[i % len(alpha_seq)]
        x_off = x_seq[i % len(x_seq)]
        y_off = y_seq[i % len(y_seq)]

        font_size = self._fit_font_size(phrase)
        font = load_font(max(12, int(font_size * scale)))
        text_bbox = draw.textbbox((0, 0), phrase, font=font)
        tw = text_bbox[2] - text_bbox[0]
        th = text_bbox[3] - text_bbox[1]
        padding_x, padding_y = 16, 10
        bubble_w = min(330, tw + padding_x * 2)
        bubble_h = th + padding_y * 2
        bx = (360 - bubble_w) // 2 + x_off
        by = 285 + y_off
        bubble = Image.new("RGBA", (bubble_w, bubble_h), (255, 255, 255, min(245, alpha)))
        bd = ImageDraw.Draw(bubble)
        bd.rounded_rectangle((0, 0, bubble_w - 1, bubble_h - 1), radius=18, fill=(255, 255, 255, min(245, alpha)), outline=(30, 30, 30, min(210, alpha)), width=2)
        canvas.alpha_composite(bubble, (bx, by))
        draw = ImageDraw.Draw(canvas)
        tx = bx + (bubble_w - tw) // 2
        ty = by + (bubble_h - th) // 2 - 2
        draw.text((tx, ty), phrase, font=font, fill=(20, 20, 20, alpha))

    def _fit_font_size(self, phrase: str) -> int:
        if len(phrase) <= 4:
            return 34
        if len(phrase) <= 8:
            return 28
        if len(phrase) <= 12:
            return 24
        return 20
