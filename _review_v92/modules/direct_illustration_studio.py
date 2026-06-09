from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class IllustrationStudioReport:
    project_name: str
    status: str
    score: int
    project_dir: str
    base_png_path: str
    clean_png_path: str
    contact_sheet_path: str
    static_zip_path: str
    animated_zip_path: str
    creator_ledger_path: str
    manifest_path: str
    html_path: str
    zip_path: str
    checksum_sha256: str
    static_count: int
    animated_count: int
    warnings: list[str]
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DirectIllustrationStudio:
    """Rough sketch to completed emoticon generator.

    Main role:
    - User draws a rough circle/body/arms/legs or uploads a loose sketch.
    - The program interprets that human input as a creation seed.
    - The program generates completed 360x360 PNG candidates and simple GIFs.
    - The package stores the user's rough input, settings, checksums, and
      generation log so the creative process remains traceable.

    It does not copy famous characters, internet images, brands, or a named
    artist style. The output is generated from user-provided structure and local
    rule-based rendering.
    """

    CANVAS_SIZE = 360

    STATIC_SET = [
        ("hello", "안녕", "smile", "wave"),
        ("thanks", "고마워", "soft", "heart"),
        ("sorry", "미안해", "sad", "sweat"),
        ("ok", "오케이", "focused", "check"),
        ("wow", "진짜?", "wide", "sparkle"),
        ("tired", "기절", "half", "zzz"),
        ("cheer", "파이팅", "happy", "sparkle"),
        ("wait", "잠시만", "flat", "pause"),
        ("love", "좋아", "happy", "heart"),
        ("angry", "그만!", "sharp", "anger"),
        ("awkward", "음...", "side", "sweat"),
        ("done", "완료", "focused", "check"),
        ("yes", "넵", "focused", "check"),
        ("no", "어려워", "sad", "sweat"),
        ("sleep", "잘게", "closed", "zzz"),
        ("run", "갑니다", "smile", "motion"),
        ("eat", "냠", "happy", "sparkle"),
        ("work", "작업중", "focused", "pause"),
        ("call", "불러줘", "soft", "wave"),
        ("busy", "바빠요", "half", "sweat"),
        ("good", "최고", "happy", "sparkle"),
        ("bad", "흠", "flat", "pause"),
        ("question", "왜요?", "wide", "question"),
        ("idea", "생각남", "wide", "sparkle"),
        ("late", "늦었어", "sad", "sweat"),
        ("start", "시작", "focused", "check"),
        ("finish", "끝", "smile", "check"),
        ("coffee", "커피?", "half", "sparkle"),
        ("holiday", "쉬자", "closed", "zzz"),
        ("meeting", "회의중", "focused", "pause"),
        ("cute", "헤헤", "happy", "heart"),
        ("bye", "또 봐", "smile", "wave"),
    ]

    def _safe_name(self, value: str) -> str:
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "auto_character"))
        return safe[:64] or "auto_character"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _rgba(self, value: str, fallback: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        try:
            value = value.strip()
            if value.startswith("#") and len(value) == 7:
                return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16), 255)
        except Exception:
            pass
        return fallback

    def _fit_user_sketch(self, sketch_path: Path | None) -> Image.Image | None:
        if not sketch_path or not Path(sketch_path).exists():
            return None
        img = Image.open(sketch_path).convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        background.alpha_composite(img)
        gray = ImageOps.grayscale(background)
        alpha = gray.point(lambda p: 255 if p < 245 else 0)
        line = Image.new("RGBA", img.size, (42, 38, 32, 0))
        line.putalpha(alpha)
        line.thumbnail((310, 310), Image.LANCZOS)
        canvas = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (255, 255, 255, 0))
        canvas.alpha_composite(line, ((self.CANVAS_SIZE - line.width) // 2, (self.CANVAS_SIZE - line.height) // 2))
        bbox = canvas.getchannel("A").getbbox()
        if not bbox:
            return None
        return canvas

    def _sketch_features(self, sketch: Image.Image | None) -> dict[str, Any]:
        if sketch is None:
            return {
                "has_sketch": False,
                "bbox": (74, 64, 286, 306),
                "center": (180, 185),
                "width": 212,
                "height": 242,
                "density": 0.0,
            }
        alpha = sketch.getchannel("A")
        bbox = alpha.getbbox() or (74, 64, 286, 306)
        x0, y0, x1, y1 = bbox
        area = max(1, (x1 - x0) * (y1 - y0))
        density = sum(1 for p in alpha.crop(bbox).getdata() if p > 0) / area
        return {
            "has_sketch": True,
            "bbox": bbox,
            "center": ((x0 + x1) // 2, (y0 + y1) // 2),
            "width": max(80, x1 - x0),
            "height": max(100, y1 - y0),
            "density": round(density, 4),
        }

    def _clean_trace(self, sketch: Image.Image | None) -> Image.Image:
        if sketch is None:
            return Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (255, 255, 255, 0))
        alpha = ImageEnhance.Contrast(sketch.getchannel("A")).enhance(1.6)
        trace = Image.new("RGBA", sketch.size, (44, 39, 33, 0))
        trace.putalpha(alpha.point(lambda p: min(150, p)))
        return trace

    def _draw_completed_character(
        self,
        feature: dict[str, Any],
        concept_note: str,
        base_color: str,
        accent_color: str,
        body_shape: str,
        face_style: str,
        effect: str,
        phrase: str,
        pose_shift: int = 0,
        trace: Image.Image | None = None,
    ) -> Image.Image:
        img = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        ink = (42, 38, 32, 255)
        base = self._rgba(base_color, (242, 192, 120, 255))
        accent = self._rgba(accent_color, (244, 155, 171, 255))

        cx, cy = feature["center"]
        bw = min(220, max(135, int(feature["width"] * 0.88)))
        bh = min(250, max(155, int(feature["height"] * 0.88)))
        cx = max(112, min(248, cx))
        cy = max(128, min(224, cy + pose_shift))
        body_box = (cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)

        shadow = (cx - bw // 2 + 16, cy + bh // 2 - 2, cx + bw // 2 - 10, cy + bh // 2 + 18)
        draw.ellipse(shadow, fill=(0, 0, 0, 28))
        if body_shape == "square":
            draw.rounded_rectangle(body_box, radius=42, fill=base, outline=ink, width=7)
        elif body_shape == "capsule":
            draw.rounded_rectangle(body_box, radius=min(bw, bh) // 2, fill=base, outline=ink, width=7)
        else:
            draw.ellipse(body_box, fill=base, outline=ink, width=7)

        # Arms and legs are generated from the rough body's bounding box.
        arm_y = cy + int(bh * 0.12)
        draw.line((cx - bw // 2 + 8, arm_y, cx - bw // 2 - 42, arm_y - 18), fill=ink, width=8)
        draw.line((cx + bw // 2 - 8, arm_y, cx + bw // 2 + 42, arm_y - 26), fill=ink, width=8)
        draw.ellipse((cx - bw // 2 - 56, arm_y - 30, cx - bw // 2 - 32, arm_y - 6), fill=accent, outline=ink, width=3)
        draw.ellipse((cx + bw // 2 + 30, arm_y - 38, cx + bw // 2 + 54, arm_y - 14), fill=accent, outline=ink, width=3)
        foot_y = cy + bh // 2 - 6
        draw.ellipse((cx - 58, foot_y, cx - 18, foot_y + 22), fill=accent, outline=ink, width=3)
        draw.ellipse((cx + 18, foot_y, cx + 58, foot_y + 22), fill=accent, outline=ink, width=3)

        # Faint rough input trace remains inside the generated asset as a creation seed guide.
        if trace is not None:
            faint = trace.copy()
            img.alpha_composite(faint)

        eye_y = cy - int(bh * 0.18)
        left_eye = (cx - int(bw * 0.20), eye_y)
        right_eye = (cx + int(bw * 0.20), eye_y)
        mouth = (cx, cy + int(bh * 0.02))
        self._draw_face(draw, left_eye, right_eye, mouth, face_style)
        self._draw_effect(draw, effect, (cx, cy, bw, bh))

        if phrase:
            font = load_korean_font(24 if len(phrase) <= 4 else 19)
            bubble_y = min(330, cy + bh // 2 + 34)
            draw.rounded_rectangle((58, bubble_y - 24, 302, bubble_y + 24), radius=18, fill=(255, 255, 255, 238), outline=ink, width=3)
            draw.text((180, bubble_y), phrase[:11], anchor="mm", fill=ink, font=font)
        return img

    def _draw_face(
        self,
        draw: ImageDraw.ImageDraw,
        left_eye: tuple[int, int],
        right_eye: tuple[int, int],
        mouth: tuple[int, int],
        face_style: str,
    ) -> None:
        ink = (42, 38, 32, 255)

        def eye(cx: int, cy: int) -> None:
            if face_style == "happy":
                draw.arc((cx - 16, cy - 3, cx + 16, cy + 18), 180, 360, fill=ink, width=5)
            elif face_style == "soft":
                draw.arc((cx - 13, cy, cx + 13, cy + 16), 190, 350, fill=ink, width=4)
            elif face_style == "sad":
                draw.line((cx - 13, cy + 9, cx + 13, cy - 2), fill=ink, width=5)
            elif face_style == "wide":
                draw.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), outline=ink, width=4)
                draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=ink)
            elif face_style == "half":
                draw.line((cx - 15, cy + 2, cx + 15, cy + 2), fill=ink, width=5)
            elif face_style == "focused":
                draw.ellipse((cx - 7, cy - 10, cx + 7, cy + 10), fill=ink)
            elif face_style == "sharp":
                draw.line((cx - 14, cy + 8, cx + 14, cy - 5), fill=ink, width=5)
            elif face_style == "side":
                draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), outline=ink, width=3)
                draw.ellipse((cx + 1, cy - 3, cx + 7, cy + 3), fill=ink)
            elif face_style == "closed":
                draw.arc((cx - 14, cy - 5, cx + 14, cy + 9), 0, 180, fill=ink, width=4)
            else:
                draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=ink)

        eye(*left_eye)
        eye(*right_eye)
        mx, my = mouth
        if face_style in {"sad", "half", "flat"}:
            draw.line((mx - 30, my, mx + 30, my), fill=ink, width=5)
        elif face_style == "wide":
            draw.ellipse((mx - 12, my - 12, mx + 12, my + 18), outline=ink, width=5)
        elif face_style == "sharp":
            draw.line((mx - 25, my + 8, mx + 22, my - 4), fill=ink, width=5)
        else:
            draw.arc((mx - 35, my - 18, mx + 35, my + 28), 0, 180, fill=ink, width=5)

    def _draw_effect(self, draw: ImageDraw.ImageDraw, effect: str, body: tuple[int, int, int, int]) -> None:
        cx, cy, bw, bh = body
        x = min(312, cx + bw // 2 + 10)
        y = max(38, cy - bh // 2 + 22)
        if effect == "heart":
            draw.polygon([(x, y + 22), (x - 20, y), (x - 10, y - 18), (x, y - 8), (x + 10, y - 18), (x + 20, y)], fill=(240, 92, 126, 230))
        elif effect == "sweat":
            draw.ellipse((x - 11, y - 10, x + 11, y + 24), fill=(92, 176, 235, 230), outline=(42, 38, 32, 255), width=2)
        elif effect == "check":
            draw.line((x - 26, y + 12, x - 8, y + 32, x + 30, y - 12), fill=(48, 160, 80, 255), width=8)
        elif effect == "sparkle":
            for px, py in ((cx - bw // 2 - 12, y), (x, y + 44), (cx + 22, cy + bh // 2 - 30)):
                draw.line((px, py - 12, px, py + 12), fill=(245, 190, 50, 240), width=4)
                draw.line((px - 12, py, px + 12, py), fill=(245, 190, 50, 240), width=4)
        elif effect == "zzz":
            font = load_korean_font(24)
            draw.text((x - 16, y), "Zzz", fill=(100, 100, 100, 230), font=font)
        elif effect == "anger":
            draw.line((x - 24, y, x + 22, y), fill=(220, 60, 50, 255), width=5)
            draw.line((x, y - 22, x, y + 22), fill=(220, 60, 50, 255), width=5)
        elif effect == "pause":
            draw.rounded_rectangle((x - 16, y - 15, x - 5, y + 22), radius=5, fill=(70, 70, 70, 230))
            draw.rounded_rectangle((x + 6, y - 15, x + 17, y + 22), radius=5, fill=(70, 70, 70, 230))
        elif effect == "wave":
            draw.arc((cx - bw // 2 - 66, cy - 70, cx - bw // 2 - 8, cy - 10), 200, 330, fill=(42, 38, 32, 255), width=5)
        elif effect == "question":
            font = load_korean_font(36)
            draw.text((x - 8, y - 20), "?", fill=(70, 120, 220, 255), font=font)
        elif effect == "motion":
            for i in range(3):
                draw.line((cx - bw // 2 - 64, cy + 42 + i * 12, cx - bw // 2 - 20, cy + 42 + i * 12), fill=(42, 38, 32, 120), width=3)

    def _contact_sheet(self, files: list[Path], out: Path) -> None:
        thumb = 132
        cols = 8
        rows = math.ceil(len(files) / cols)
        sheet = Image.new("RGB", (cols * thumb, rows * thumb), (246, 242, 232))
        for idx, fp in enumerate(files):
            img = Image.open(fp).convert("RGBA")
            img.thumbnail((thumb - 10, thumb - 10), Image.LANCZOS)
            cell = Image.new("RGBA", (thumb, thumb), (255, 255, 255, 0))
            cell.alpha_composite(img, ((thumb - img.width) // 2, (thumb - img.height) // 2))
            sheet.paste(cell.convert("RGB"), (idx % cols * thumb, idx // cols * thumb))
        sheet.save(out)

    def _make_gif(self, base_args: dict[str, Any], out: Path, motion: str) -> None:
        frames: list[Image.Image] = []
        shifts = [0, -8, 0, 6, 0]
        if motion in {"wave", "check", "motion"}:
            shifts = [0, -5, -10, -5, 0]
        elif motion in {"zzz", "pause"}:
            shifts = [0, 0, 2, 0, 0]
        for shift in shifts:
            frame = self._draw_completed_character(**base_args, pose_shift=shift)
            frames.append(frame.convert("P", palette=Image.ADAPTIVE))
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=110, loop=0, disposal=2)

    def _zip_files(self, files: list[Path], zip_path: Path, base_dir: Path) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in files:
                if fp.exists():
                    zf.write(fp, fp.relative_to(base_dir))

    def build_project(
        self,
        output_dir: Path,
        project_name: str,
        concept_note: str,
        creator_note: str,
        sketch_path: Path | None = None,
        base_color: str = "#F2C078",
        accent_color: str = "#F49BAB",
        body_shape: str = "round",
        rights_confirmed: bool = False,
        no_ai_completed_image: bool = False,
        learning_summary: str = "",
        generation_mode: str = "main_shape_to_completed_set",
    ) -> IllustrationStudioReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        safe = self._safe_name(project_name)
        project_dir = output_dir / f"{safe}_{int(time.time())}"
        assets = project_dir / "assets"
        static_dir = project_dir / "static_32_png"
        animated_dir = project_dir / "animated_24_gif"
        for folder in (assets, static_dir, animated_dir):
            folder.mkdir(parents=True, exist_ok=True)

        warnings: list[str] = []
        sketch = self._fit_user_sketch(sketch_path)
        feature = self._sketch_features(sketch)
        trace = self._clean_trace(sketch)
        if sketch is None:
            warnings.append("러프 스케치 파일이 없어 사용자가 고른 도형/색상/문구를 생성 입력값으로 사용했습니다.")
        if not rights_confirmed:
            warnings.append("제출 전 저작권/상표권/유사성 확인 체크가 필요합니다.")

        if sketch is not None:
            raw_copy = assets / "user_rough_sketch_original.png"
            sketch.save(raw_copy)
        trace_path = assets / "user_rough_trace_cleaned.png"
        trace.save(trace_path)

        common = {
            "feature": feature,
            "concept_note": concept_note,
            "base_color": base_color,
            "accent_color": accent_color,
            "body_shape": body_shape,
            "trace": trace if sketch is not None else None,
        }
        base_img = self._draw_completed_character(
            **common,
            face_style="smile",
            effect="wave",
            phrase=(concept_note.strip()[:6] or "내 캐릭터"),
        )
        base_path = assets / f"{safe}_generated_base.png"
        clean_path = assets / f"{safe}_completed_360.png"
        base_img.save(base_path)
        base_img.save(clean_path)
        checksum = self._checksum(clean_path)

        static_files: list[Path] = []
        rows: list[dict[str, Any]] = []
        for idx, (key, phrase, face_style, effect) in enumerate(self.STATIC_SET, start=1):
            img = self._draw_completed_character(**common, face_style=face_style, effect=effect, phrase=phrase)
            fp = static_dir / f"{idx:02d}_{key}.png"
            img.save(fp)
            static_files.append(fp)
            rows.append({
                "no": idx,
                "file_name": fp.name,
                "phrase": phrase,
                "face_style": face_style,
                "effect": effect,
                "source": "user rough sketch" if sketch is not None else "user shape/color recipe",
            })

        animated_files: list[Path] = []
        for idx, (key, phrase, face_style, effect) in enumerate(self.STATIC_SET[:24], start=1):
            fp = animated_dir / f"{idx:02d}_{key}.gif"
            self._make_gif({**common, "face_style": face_style, "effect": effect, "phrase": phrase}, fp, effect)
            animated_files.append(fp)

        contact_sheet = project_dir / "generated_32_contact_sheet.jpg"
        self._contact_sheet(static_files, contact_sheet)
        static_zip = project_dir / "static_32_png_submit.zip"
        animated_zip = project_dir / "animated_24_gif_submit.zip"
        self._zip_files(static_files, static_zip, project_dir)
        self._zip_files(animated_files, animated_zip, project_dir)

        score = 35
        if feature["has_sketch"]:
            score += 25
        else:
            score += 10
        if concept_note.strip():
            score += 10
        if creator_note.strip():
            score += 10
        if rights_confirmed:
            score += 15
        if static_files and animated_files:
            score += 5
        score = min(100, score)
        status = "완성 세트 생성 완료" if score >= 85 else "완성 세트 생성 완료 · 증빙 보완 권장"

        ledger = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "project_name": project_name,
            "generation_mode": generation_mode,
            "main_goal": "rough circle/body/arms/legs to completed emoticon set",
            "creator_note": creator_note,
            "concept_note": concept_note,
            "sketch_features": feature,
            "base_color": base_color,
            "accent_color": accent_color,
            "body_shape": body_shape,
            "rights_confirmed": rights_confirmed,
            "ai_completed_generator_enabled": True,
            "rough_input_is_creation_evidence": True,
            "learning_summary_used_as_abstract_reference_only": learning_summary,
            "program_role": [
                "사용자가 대충 그린 원/몸통/팔다리 구조를 완성형 캐릭터로 자동 정리",
                "사용자가 자유롭게 그린 형태를 기반으로 완성형 PNG/GIF 후보 생성",
                "직접 일러스트 작업을 함께 보관하고 창작 증빙 로그 생성",
            ],
            "safety_boundary": [
                "유명 캐릭터, 브랜드, 타 작가 그림체, 인터넷 이미지 복제 금지",
                "러프 입력과 설정값, 해시, 생성 시간을 기록해 창작 과정을 추적",
                "최종 제출 전 공식 심사 기준과 권리 확인은 사용자가 재확인",
            ],
        }
        ledger_path = project_dir / "creator_generation_ledger.json"
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

        csv_path = project_dir / "generated_expression_board.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        manifest = {
            "project_name": project_name,
            "status": status,
            "score": score,
            "checksum_sha256": checksum,
            "base_png_path": str(base_path),
            "clean_png_path": str(clean_path),
            "static_files": [str(fp) for fp in static_files],
            "animated_files": [str(fp) for fp in animated_files],
            "static_zip_path": str(static_zip),
            "animated_zip_path": str(animated_zip),
            "warnings": warnings,
            "evidence": ledger,
        }
        manifest_path = project_dir / "direct_illustration_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        html_path = project_dir / "direct_illustration_report.html"
        self._write_html(manifest, rows, html_path)

        zip_path = project_dir / f"{safe}_auto_completed_emoticon_pack.zip"
        all_files = [
            base_path,
            clean_path,
            trace_path,
            contact_sheet,
            static_zip,
            animated_zip,
            ledger_path,
            csv_path,
            manifest_path,
            html_path,
            *static_files,
            *animated_files,
        ]
        if sketch is not None:
            all_files.append(assets / "user_rough_sketch_original.png")
        self._zip_files(all_files, zip_path, project_dir)

        return IllustrationStudioReport(
            project_name=project_name,
            status=status,
            score=score,
            project_dir=str(project_dir),
            base_png_path=str(base_path),
            clean_png_path=str(clean_path),
            contact_sheet_path=str(contact_sheet),
            static_zip_path=str(static_zip),
            animated_zip_path=str(animated_zip),
            creator_ledger_path=str(ledger_path),
            manifest_path=str(manifest_path),
            html_path=str(html_path),
            zip_path=str(zip_path),
            checksum_sha256=checksum,
            static_count=len(static_files),
            animated_count=len(animated_files),
            warnings=warnings,
            evidence=ledger,
        )

    def _write_html(self, manifest: dict[str, Any], rows: list[dict[str, Any]], out: Path) -> None:
        warning_html = "".join(f"<li>{html.escape(w)}</li>" for w in manifest.get("warnings", [])) or "<li>현재 입력 기준 고위험 경고 없음</li>"
        row_html = "".join(
            "<tr>"
            f"<td>{row['no']}</td><td>{html.escape(row['file_name'])}</td><td>{html.escape(row['phrase'])}</td>"
            f"<td>{html.escape(row['face_style'])}</td><td>{html.escape(row['effect'])}</td><td>{html.escape(row['source'])}</td>"
            "</tr>"
            for row in rows
        )
        out.write_text(
            f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>러프 입력 기반 자동 완성 이모티콘 리포트</title>
  <style>
    body {{ font-family:"Malgun Gothic", Arial, sans-serif; background:#f4efe7; color:#26221d; margin:0; padding:32px; }}
    main {{ max-width:1120px; margin:auto; background:#fffdf8; border:1px solid #dfd3c1; border-radius:24px; padding:28px; }}
    .hero {{ background:linear-gradient(135deg,#1f332c,#7a6a3d); color:white; border-radius:22px; padding:24px; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:18px 0; }}
    .card {{ background:#fbf4e8; border:1px solid #e3d4bd; border-radius:16px; padding:14px; }}
    .card b {{ display:block; font-size:24px; margin-top:4px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:18px; }}
    th,td {{ border-bottom:1px solid #e3d4bd; padding:9px; text-align:left; vertical-align:top; }}
    th {{ background:#e9f0e3; }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <h1>러프 입력 기반 자동 완성 이모티콘 리포트</h1>
    <p>사용자가 대충 그린 원, 몸통, 팔다리 또는 자유 러프를 입력값으로 삼아 프로그램이 완성형 PNG/GIF 세트를 생성했습니다.</p>
  </section>
  <div class="grid">
    <div class="card"><span>상태</span><b>{html.escape(str(manifest.get("status", "")))}</b></div>
    <div class="card"><span>창작/생성 점수</span><b>{html.escape(str(manifest.get("score", 0)))}</b></div>
    <div class="card"><span>정지형 PNG</span><b>{len(rows)}</b></div>
    <div class="card"><span>SHA-256</span><small>{html.escape(str(manifest.get("checksum_sha256", "")))}</small></div>
  </div>
  <h2>경고/확인</h2>
  <ul>{warning_html}</ul>
  <h2>생성 목록</h2>
  <table><thead><tr><th>No</th><th>파일</th><th>문구</th><th>표정</th><th>효과</th><th>입력 근거</th></tr></thead><tbody>{row_html}</tbody></table>
  <p>이 패키지는 자동 완성 생성 결과와 창작 증빙을 함께 보관합니다. 제출 전 최신 공식 기준, 권리 확인, 유사성 확인은 별도로 재확인해야 합니다.</p>
</main>
</body>
</html>""",
            encoding="utf-8",
        )
