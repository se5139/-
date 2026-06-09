from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import csv
import hashlib
import html
import json
import math
import time
import zipfile

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class PartEstimate:
    name: str
    bbox: Tuple[int, int, int, int]
    confidence: float
    role: str
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["bbox"] = [int(x) for x in self.bbox]
        return d


@dataclass
class DrawingRefineReport:
    project_name: str
    input_image_path: str
    normalized_png_path: str
    parts_overlay_path: str
    parts_manifest_path: str
    expression_manifest_path: str
    expression_csv_path: str
    html_path: str
    zip_path: str
    checksum_sha256: str
    part_count: int
    variant_count: int
    starter_expression_count: int
    part_files: List[Dict[str, Any]]
    variant_files: List[Dict[str, Any]]
    starter_expressions: List[Dict[str, Any]]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DrawingRefineEngine:
    """v25 자유 드로잉 원본 자동 정리·파츠 추정·표정 확장 엔진.

    목적:
    - 사용자가 마우스/태블릿 펜/손가락으로 대충 그린 원본을 360×360 캐릭터 원본으로 정리
    - 얼굴/몸통/눈/입/팔 후보 영역을 초보자용으로 추정
    - 원본 하나에서 표정 변형 PNG를 여러 개 만들고, 24/32개 세트 제작 흐름에 연결할 표정 맵을 저장
    - 기존 파일은 덮어쓰지 않고 새 폴더에 결과/리포트/ZIP을 생성
    """

    CANVAS_SIZE = 360

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _safe_name(self, value: str) -> str:
        return "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "drawing_refine"))[:80] or "drawing_refine"

    def _load_image(self, image_path: Path) -> Image.Image:
        img = Image.open(image_path).convert("RGBA")
        if img.size != (self.CANVAS_SIZE, self.CANVAS_SIZE):
            # Keep aspect, fit into 360×360 transparent canvas
            img.thumbnail((self.CANVAS_SIZE, self.CANVAS_SIZE), Image.LANCZOS)
            out = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (255, 255, 255, 0))
            out.alpha_composite(img, ((self.CANVAS_SIZE - img.width) // 2, (self.CANVAS_SIZE - img.height) // 2))
            img = out
        return img

    def normalize_image(self, img: Image.Image, target_margin: int = 34) -> Image.Image:
        """투명 여백/크기/중심을 정리한다. AI 보정이 아닌 기하학적 정리만 수행."""
        im = img.convert("RGBA")
        alpha = im.split()[-1]
        bbox = alpha.getbbox()
        if not bbox:
            return im
        cropped = im.crop(bbox)
        max_w = self.CANVAS_SIZE - target_margin * 2
        max_h = self.CANVAS_SIZE - target_margin * 2
        scale = min(max_w / max(1, cropped.width), max_h / max(1, cropped.height), 1.35)
        new_size = (max(1, int(cropped.width * scale)), max(1, int(cropped.height * scale)))
        cropped = cropped.resize(new_size, Image.LANCZOS)
        # Slight alpha/contrast cleanup to make faint pen marks more visible but not redraw content.
        r, g, b, a = cropped.split()
        a = ImageEnhance.Contrast(a).enhance(1.25)
        cropped = Image.merge("RGBA", (r, g, b, a))
        out = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (255, 255, 255, 0))
        out.alpha_composite(cropped, ((self.CANVAS_SIZE - cropped.width) // 2, (self.CANVAS_SIZE - cropped.height) // 2))
        return out

    def _nontransparent_bbox(self, img: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        return img.convert("RGBA").split()[-1].getbbox()

    def _dark_components(self, img: Image.Image, bbox: Tuple[int, int, int, int], min_pixels: int = 8) -> List[Dict[str, Any]]:
        """간단한 연결 성분 추출. 외부 의존성 없이 눈/입 후보를 찾기 위한 보조용."""
        im = img.convert("RGBA")
        pix = im.load()
        x0, y0, x1, y1 = bbox
        w, h = im.size
        visited = set()
        comps: List[Dict[str, Any]] = []
        # Dark/opaque pixels; line art typically black/brown.
        def is_mark(x: int, y: int) -> bool:
            r, g, b, a = pix[x, y]
            if a < 40:
                return False
            brightness = (int(r) + int(g) + int(b)) / 3
            return brightness < 150 or a > 180

        for y in range(max(0, y0), min(h, y1), 2):
            for x in range(max(0, x0), min(w, x1), 2):
                if (x, y) in visited or not is_mark(x, y):
                    continue
                stack = [(x, y)]
                visited.add((x, y))
                xs, ys = [], []
                while stack:
                    cx, cy = stack.pop()
                    xs.append(cx); ys.append(cy)
                    for nx, ny in ((cx+2,cy),(cx-2,cy),(cx,cy+2),(cx,cy-2)):
                        if nx < x0 or nx >= x1 or ny < y0 or ny >= y1 or (nx, ny) in visited:
                            continue
                        visited.add((nx, ny))
                        if is_mark(nx, ny):
                            stack.append((nx, ny))
                if len(xs) >= min_pixels:
                    comps.append({
                        "bbox": (min(xs), min(ys), max(xs)+1, max(ys)+1),
                        "pixels": len(xs),
                        "cx": sum(xs) / len(xs),
                        "cy": sum(ys) / len(ys),
                    })
        return sorted(comps, key=lambda c: c["pixels"], reverse=True)

    def estimate_parts(self, img: Image.Image) -> Tuple[List[PartEstimate], List[str]]:
        warnings: List[str] = []
        bbox = self._nontransparent_bbox(img)
        if not bbox:
            warnings.append("그림 영역을 찾지 못했습니다. 자유 드로잉 캔버스에서 원/눈/입/몸통을 한 번 더 그려주세요.")
            return [], warnings
        x0, y0, x1, y1 = bbox
        bw, bh = x1 - x0, y1 - y0
        parts: List[PartEstimate] = [
            PartEstimate("full_character", bbox, 0.95, "전체 캐릭터", "전체 비투명 영역 기준"),
        ]
        # Heuristic split: face top, body bottom. Good enough as a beginner confirmation stage.
        face_y1 = y0 + int(bh * 0.52)
        body_y0 = y0 + int(bh * 0.42)
        face_bbox = (x0, y0, x1, face_y1)
        body_bbox = (x0, body_y0, x1, y1)
        parts.append(PartEstimate("face_candidate", face_bbox, 0.72, "얼굴 후보", "전체 영역의 상단 52%를 얼굴 후보로 추정"))
        parts.append(PartEstimate("body_candidate", body_bbox, 0.68, "몸통 후보", "전체 영역의 하단 58%를 몸통 후보로 추정"))
        comps = self._dark_components(img, face_bbox)
        # Eye candidates: small-ish components in upper/middle face, split left/right
        eye_comps = []
        for c in comps:
            bx0, by0, bx1, by1 = c["bbox"]
            cw, ch = bx1-bx0, by1-by0
            if y0 + bh * 0.08 <= c["cy"] <= y0 + bh * 0.42 and cw <= bw * 0.32 and ch <= bh * 0.22:
                eye_comps.append(c)
        eye_comps = sorted(eye_comps[:6], key=lambda c: c["cx"])
        if len(eye_comps) >= 2:
            parts.append(PartEstimate("left_eye_candidate", eye_comps[0]["bbox"], 0.62, "왼쪽 눈 후보", "상단 작은 선/점 성분 기준"))
            parts.append(PartEstimate("right_eye_candidate", eye_comps[-1]["bbox"], 0.62, "오른쪽 눈 후보", "상단 작은 선/점 성분 기준"))
        else:
            ex1 = x0 + int(bw * 0.35); ex2 = x0 + int(bw * 0.65); ey = y0 + int(bh * 0.28)
            parts.append(PartEstimate("left_eye_candidate", (ex1-10, ey-8, ex1+10, ey+8), 0.36, "왼쪽 눈 후보", "명확한 눈 성분이 부족해 기본 위치로 추정"))
            parts.append(PartEstimate("right_eye_candidate", (ex2-10, ey-8, ex2+10, ey+8), 0.36, "오른쪽 눈 후보", "명확한 눈 성분이 부족해 기본 위치로 추정"))
            warnings.append("눈 후보가 명확하지 않아 기본 위치로 추정했습니다. v16 표정/파츠 편집기에서 확인하세요.")
        # Mouth candidate: component under eyes, near horizontal center
        mouth_candidates = []
        for c in comps:
            bx0, by0, bx1, by1 = c["bbox"]
            cw, ch = bx1-bx0, by1-by0
            if y0 + bh * 0.30 <= c["cy"] <= y0 + bh * 0.58 and abs(c["cx"] - (x0+x1)/2) <= bw * 0.30 and cw >= 8:
                mouth_candidates.append(c)
        if mouth_candidates:
            m = sorted(mouth_candidates, key=lambda c: (-c["pixels"], abs(c["cx"]-(x0+x1)/2)))[0]
            parts.append(PartEstimate("mouth_candidate", m["bbox"], 0.58, "입 후보", "얼굴 중앙 하단 선 성분 기준"))
        else:
            mx = (x0+x1)//2; my = y0 + int(bh * 0.43)
            parts.append(PartEstimate("mouth_candidate", (mx-28, my-8, mx+28, my+12), 0.34, "입 후보", "명확한 입 성분이 부족해 기본 위치로 추정"))
            warnings.append("입 후보가 명확하지 않아 기본 위치로 추정했습니다. 표정 변형 미리보기에서 확인하세요.")
        # Arms/effects rough side candidates
        parts.append(PartEstimate("left_side_arm_candidate", (max(0, x0-8), y0+int(bh*0.42), x0+int(bw*0.25), y0+int(bh*0.86)), 0.38, "왼팔/왼쪽 장식 후보", "좌측 하단 외곽 기준"))
        parts.append(PartEstimate("right_side_arm_candidate", (x1-int(bw*0.25), y0+int(bh*0.42), min(360, x1+8), y0+int(bh*0.86)), 0.38, "오른팔/오른쪽 장식 후보", "우측 하단 외곽 기준"))
        return parts, warnings

    def _draw_overlay(self, img: Image.Image, parts: List[PartEstimate], out: Path) -> None:
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 255))
        overlay.alpha_composite(img)
        draw = ImageDraw.Draw(overlay)
        font = load_korean_font(13)
        colors = ["#FF4D4D", "#3B82F6", "#22C55E", "#F59E0B", "#A855F7", "#14B8A6", "#EF4444", "#64748B"]
        for idx, p in enumerate(parts):
            color = colors[idx % len(colors)]
            draw.rectangle(p.bbox, outline=color, width=3)
            tx, ty = p.bbox[0] + 3, max(0, p.bbox[1] - 18)
            label = p.role
            draw.rectangle((tx-2, ty-1, tx+len(label)*9+4, ty+17), fill=(255,255,255,210))
            draw.text((tx, ty), label, fill=color, font=font)
        overlay.save(out)

    def _crop_part(self, img: Image.Image, bbox: Tuple[int, int, int, int], out: Path) -> None:
        part = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (255,255,255,0))
        crop = img.crop(bbox)
        part.alpha_composite(crop, (bbox[0], bbox[1]))
        part.save(out)

    def _part_center(self, parts: List[PartEstimate], name: str, fallback: Tuple[int, int]) -> Tuple[int, int]:
        p = next((p for p in parts if p.name == name), None)
        if not p:
            return fallback
        x0, y0, x1, y1 = p.bbox
        return ((x0+x1)//2, (y0+y1)//2)

    def expression_variants(self) -> List[Dict[str, Any]]:
        return [
            {"key":"base", "label":"기본", "emotion":"기본", "eye":"dot", "mouth":"smile", "effect":"", "phrase":"안녕하세요"},
            {"key":"happy", "label":"웃음", "emotion":"기쁨", "eye":"happy", "mouth":"big_smile", "effect":"sparkle", "phrase":"좋아요"},
            {"key":"thanks", "label":"감사", "emotion":"감사", "eye":"soft", "mouth":"small_smile", "effect":"heart", "phrase":"고마워요"},
            {"key":"sorry", "label":"사과", "emotion":"사과", "eye":"down", "mouth":"sad", "effect":"sweat", "phrase":"죄송합니다"},
            {"key":"angry", "label":"화남", "emotion":"분노", "eye":"sharp", "mouth":"zigzag", "effect":"anger", "phrase":"건드리지 마"},
            {"key":"surprised", "label":"놀람", "emotion":"당황", "eye":"wide", "mouth":"open", "effect":"question", "phrase":"어...?"},
            {"key":"tired", "label":"피곤", "emotion":"피곤", "eye":"half", "mouth":"flat", "effect":"zzz", "phrase":"기절"},
            {"key":"check", "label":"확인", "emotion":"확인", "eye":"focused", "mouth":"flat", "effect":"check", "phrase":"확인했습니다"},
            {"key":"cheer", "label":"응원", "emotion":"응원", "eye":"happy", "mouth":"big_smile", "effect":"sparkle", "phrase":"파이팅"},
            {"key":"awkward", "label":"민망", "emotion":"당황", "eye":"side", "mouth":"awkward", "effect":"sweat", "phrase":"아...네"},
            {"key":"sleep", "label":"잘자", "emotion":"휴식", "eye":"closed", "mouth":"relieved", "effect":"zzz", "phrase":"잘자요"},
            {"key":"love", "label":"하트", "emotion":"호감", "eye":"happy", "mouth":"small_smile", "effect":"heart", "phrase":"마음만 받을게요"},
        ]

    def _draw_face_variant(self, base: Image.Image, parts: List[PartEstimate], variant: Dict[str, Any]) -> Image.Image:
        img = base.copy().convert("RGBA")
        draw = ImageDraw.Draw(img)
        le = self._part_center(parts, "left_eye_candidate", (150, 120))
        re = self._part_center(parts, "right_eye_candidate", (210, 120))
        mouth = self._part_center(parts, "mouth_candidate", (180, 150))
        # Cover old face marks gently with semi-transparent fill? Avoid destroying original: draw small white/transparent sticker-style patches.
        # Use light cream patches so variants are visible on line-art drawings.
        patch = (255, 248, 230, 210)
        for cx, cy in [le, re]:
            draw.ellipse((cx-18, cy-14, cx+18, cy+14), fill=patch)
        draw.rounded_rectangle((mouth[0]-42, mouth[1]-16, mouth[0]+42, mouth[1]+20), radius=10, fill=patch)
        ink = (42, 38, 32, 255)
        eye = variant.get("eye", "dot")
        for cx, cy in [le, re]:
            if eye == "happy":
                draw.arc((cx-13, cy-6, cx+13, cy+12), 180, 360, fill=ink, width=4)
            elif eye == "soft":
                draw.arc((cx-12, cy-2, cx+12, cy+12), 190, 350, fill=ink, width=3)
            elif eye == "down":
                draw.line((cx-12, cy, cx+12, cy+8), fill=ink, width=4)
            elif eye == "sharp":
                draw.line((cx-14, cy+6, cx+14, cy-5), fill=ink, width=5)
                draw.line((cx-13, cy-10, cx+12, cy-2), fill=(80,40,30,255), width=3)
            elif eye == "wide":
                draw.ellipse((cx-10, cy-10, cx+10, cy+10), outline=ink, width=4)
                draw.ellipse((cx-3, cy-3, cx+3, cy+3), fill=ink)
            elif eye == "half":
                draw.line((cx-13, cy, cx+13, cy), fill=ink, width=5)
            elif eye == "focused":
                draw.ellipse((cx-6, cy-8, cx+6, cy+8), fill=ink)
            elif eye == "side":
                draw.ellipse((cx-7, cy-7, cx+7, cy+7), outline=ink, width=3)
                draw.ellipse((cx+1, cy-3, cx+7, cy+3), fill=ink)
            elif eye == "closed":
                draw.arc((cx-12, cy-3, cx+12, cy+8), 0, 180, fill=ink, width=4)
            else:
                draw.ellipse((cx-5, cy-5, cx+5, cy+5), fill=ink)
        mx, my = mouth
        m = variant.get("mouth", "smile")
        if m == "big_smile":
            draw.arc((mx-34, my-14, mx+34, my+34), 0, 180, fill=ink, width=5)
        elif m == "small_smile":
            draw.arc((mx-22, my-6, mx+22, my+20), 0, 180, fill=ink, width=4)
        elif m == "sad":
            draw.arc((mx-26, my, mx+26, my+30), 180, 360, fill=ink, width=4)
        elif m == "zigzag":
            pts = [(mx-30,my+4),(mx-18,my-4),(mx-6,my+4),(mx+6,my-4),(mx+18,my+4),(mx+30,my-4)]
            draw.line(pts, fill=ink, width=4)
        elif m == "open":
            draw.ellipse((mx-10, my-8, mx+10, my+18), outline=ink, width=4)
        elif m == "flat":
            draw.line((mx-24, my+4, mx+24, my+4), fill=ink, width=4)
        elif m == "awkward":
            draw.line((mx-20, my+2, mx-5, my+8, mx+12, my+2, mx+24, my+8), fill=ink, width=3)
        elif m == "relieved":
            draw.arc((mx-24, my-2, mx+24, my+18), 15, 165, fill=ink, width=3)
        else:
            draw.arc((mx-28, my-10, mx+28, my+24), 0, 180, fill=ink, width=4)
        self._draw_effect(draw, variant.get("effect", ""), parts)
        return img

    def _draw_effect(self, draw: ImageDraw.ImageDraw, effect: str, parts: List[PartEstimate]) -> None:
        bbox_part = next((p for p in parts if p.name == "full_character"), None)
        if bbox_part:
            x0, y0, x1, y1 = bbox_part.bbox
        else:
            x0, y0, x1, y1 = (70, 50, 290, 290)
        if effect == "heart":
            cx, cy = min(320, x1+12), max(30, y0+18)
            draw.polygon([(cx,cy+12),(cx-16,cy-3),(cx-8,cy-18),(cx,cy-8),(cx+8,cy-18),(cx+16,cy-3)], fill=(240,80,120,230))
        elif effect == "sweat":
            cx, cy = min(320, x1+12), y0+40
            draw.ellipse((cx-8,cy-12,cx+8,cy+12), fill=(85,170,235,230))
        elif effect == "anger":
            cx, cy = x1-20, y0+22
            draw.line((cx-16,cy,cx+16,cy), fill=(230,60,50,255), width=5)
            draw.line((cx,cy-16,cx,cy+16), fill=(230,60,50,255), width=5)
        elif effect == "question":
            font = load_korean_font(34)
            draw.text((min(310, x1+5), y0+10), "?", fill=(70,120,220,255), font=font)
        elif effect == "zzz":
            font = load_korean_font(22)
            draw.text((min(300, x1), y0+10), "Zzz", fill=(100,100,100,220), font=font)
        elif effect == "check":
            draw.line((x1-35, y0+35, x1-20, y0+50, x1+12, y0+18), fill=(45,160,80,255), width=6)
        elif effect == "sparkle":
            for dx, dy in [(x0-8,y0+25),(x1+5,y0+65),(x1-20,y1-30)]:
                draw.line((dx,dy-9,dx,dy+9), fill=(245,190,50,230), width=3)
                draw.line((dx-9,dy,dx+9,dy), fill=(245,190,50,230), width=3)

    def _write_html(self, report: Dict[str, Any], out: Path) -> None:
        parts_rows = "".join(
            f"<tr><td>{html.escape(p.get('role',''))}</td><td>{html.escape(p.get('name',''))}</td><td>{p.get('bbox')}</td><td>{p.get('confidence')}</td><td>{html.escape(p.get('note',''))}</td></tr>"
            for p in report.get("parts", [])
        )
        variant_rows = "".join(
            f"<tr><td>{html.escape(v.get('label',''))}</td><td>{html.escape(v.get('emotion',''))}</td><td>{html.escape(v.get('phrase',''))}</td><td>{html.escape(v.get('file_name',''))}</td></tr>"
            for v in report.get("variants", [])
        )
        warning_html = "".join(f"<li>{html.escape(w)}</li>" for w in report.get("warnings", [])) or "<li>치명적 경고 없음</li>"
        body = f"""
        <html><head><meta charset='utf-8'><title>v25 자유 드로잉 정리/파츠추정 리포트</title>
        <style>body{{font-family:Arial,'Malgun Gothic',sans-serif;line-height:1.55;padding:24px}}table{{border-collapse:collapse;width:100%;margin-top:12px}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#f5f5f5}}.box{{background:#f2fbf5;border-radius:10px;padding:14px}}.warn{{background:#fff8e8;padding:12px;border-radius:8px}}</style></head><body>
        <h1>v25 자유 드로잉 자동 정리 + 파츠 추정 + 표정 확장 리포트</h1>
        <div class='box'><b>프로젝트:</b> {html.escape(report.get('project_name',''))}<br><b>파츠 후보 수:</b> {report.get('part_count')}<br><b>표정 변형 수:</b> {report.get('variant_count')}<br><b>스타터 표현 수:</b> {report.get('starter_expression_count')}<br><b>SHA-256:</b> {html.escape(report.get('checksum_sha256',''))}</div>
        <h2>주의/확인 항목</h2><ul class='warn'>{warning_html}</ul>
        <h2>파츠 추정 결과</h2><table><tr><th>역할</th><th>키</th><th>영역</th><th>신뢰도</th><th>메모</th></tr>{parts_rows}</table>
        <h2>표정 변형 결과</h2><table><tr><th>표정</th><th>감정</th><th>기본 문구</th><th>파일</th></tr>{variant_rows}</table>
        <p>파츠 추정은 법적/심사 판단이 아니라 제작 보조용입니다. 결과는 v16 표정/파츠 편집기와 v23 일관성 검사에서 다시 확인하세요.</p>
        </body></html>
        """
        out.write_text(body, encoding="utf-8")

    def _starter_expression_rows(self, variants: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
        base_phrases = [
            ("인사", "안녕하세요"), ("확인", "확인했습니다"), ("답장", "넵"), ("감사", "감사합니다"),
            ("사과", "죄송합니다"), ("응원", "파이팅"), ("피곤", "기절"), ("퇴근", "퇴근하고 싶어요"),
            ("당황", "어...?"), ("축하", "축하해요"), ("부탁", "부탁드려요"), ("잘자", "잘자요"),
            ("분노", "건드리지 마"), ("위로", "괜찮아요"), ("기다림", "잠시만요"), ("완료", "완료했습니다"),
            ("민망", "아...네"), ("호감", "마음만 받을게요"), ("슬픔", "눈물나요"), ("놀람", "진짜요?"),
            ("업무", "접수했습니다"), ("거절", "어려울 것 같아요"), ("휴식", "쉬어도 돼요"), ("리액션", "오오"),
            ("시그니처", "뭐... 고맙긴 하네"), ("시그니처", "같이 할게요"), ("시그니처", "잠시 접혀있겠습니다"), ("시그니처", "말랑하게 갑니다"),
            ("시즌", "월요일입니다"), ("시즌", "주말 주세요"), ("관계", "보고싶어요"), ("마무리", "수고했어요"),
        ]
        rows = []
        for i in range(target_count):
            category, phrase = base_phrases[i % len(base_phrases)]
            v = variants[i % len(variants)]
            rows.append({
                "no": i + 1,
                "category": category,
                "phrase": phrase,
                "variant_key": v["key"],
                "variant_label": v["label"],
                "emotion": v["emotion"],
                "eye_style": v["eye"],
                "mouth_style": v["mouth"],
                "effect": v["effect"],
                "next_step": "후보 갤러리/표정 편집/채팅 미리보기로 연결",
            })
        return rows

    def build_project(
        self,
        input_image_path: Path,
        output_dir: Path,
        project_name: str = "drawing_refine_project",
        starter_expression_count: int = 32,
        variant_count: int = 12,
    ) -> DrawingRefineReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        safe = self._safe_name(project_name)
        project_dir = output_dir / f"{safe}_{int(time.time())}"
        assets = project_dir / "assets"
        parts_dir = project_dir / "parts"
        variants_dir = project_dir / "expression_variants"
        for d in [assets, parts_dir, variants_dir]:
            d.mkdir(parents=True, exist_ok=True)

        source = self._load_image(Path(input_image_path))
        normalized = self.normalize_image(source)
        normalized_path = assets / f"{safe}_normalized_360.png"
        normalized.save(normalized_path)
        checksum = self._checksum(normalized_path)
        parts, warnings = self.estimate_parts(normalized)

        overlay_path = assets / f"{safe}_parts_overlay.png"
        self._draw_overlay(normalized, parts, overlay_path)

        part_files: List[Dict[str, Any]] = []
        for p in parts:
            fp = parts_dir / f"{safe}_{p.name}.png"
            self._crop_part(normalized, p.bbox, fp)
            part_files.append({"part": p.to_dict(), "file_path": str(fp), "file_name": fp.name})

        variants_meta = self.expression_variants()[:max(1, variant_count)]
        variant_files: List[Dict[str, Any]] = []
        for idx, v in enumerate(variants_meta, start=1):
            img = self._draw_face_variant(normalized, parts, v)
            fp = variants_dir / f"{idx:02d}_{v['key']}_{v['label']}.png"
            img.save(fp)
            row = dict(v)
            row.update({"file_path": str(fp), "file_name": fp.name})
            variant_files.append(row)

        starter_rows = self._starter_expression_rows(variants_meta, starter_expression_count)
        expression_manifest_path = project_dir / "starter_expression_bridge.json"
        expression_manifest_path.write_text(json.dumps(starter_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        csv_path = project_dir / "starter_expression_bridge.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            fieldnames = ["no", "category", "phrase", "variant_key", "variant_label", "emotion", "eye_style", "mouth_style", "effect", "next_step"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(starter_rows)

        manifest = {
            "project_name": project_name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "input_image_path": str(input_image_path),
            "normalized_png_path": str(normalized_path),
            "parts_overlay_path": str(overlay_path),
            "checksum_sha256": checksum,
            "parts": [p.to_dict() for p in parts],
            "part_files": part_files,
            "variants": variant_files,
            "starter_expressions": starter_rows,
            "warnings": warnings,
            "notes": [
                "직접 그린 원본을 360×360으로 정리하고 파츠 후보를 추정했습니다.",
                "표정 변형은 원본을 기반으로 제작 보조용 오버레이를 적용한 미리보기입니다.",
                "제출 전에는 v16 표정/파츠 편집기, v17 채팅 미리보기, v23 일관성 검사로 다시 확인하세요.",
            ],
        }
        parts_manifest_path = project_dir / "drawing_refine_parts_manifest.json"
        parts_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path = project_dir / "drawing_refine_report.html"
        self._write_html({**manifest, "part_count": len(parts), "variant_count": len(variant_files), "starter_expression_count": len(starter_rows)}, html_path)
        zip_path = project_dir / f"{safe}_drawing_refine_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in [normalized_path, overlay_path, parts_manifest_path, expression_manifest_path, csv_path, html_path]:
                zf.write(fp, fp.relative_to(project_dir))
            for row in part_files:
                fp = Path(row["file_path"])
                zf.write(fp, fp.relative_to(project_dir))
            for row in variant_files:
                fp = Path(row["file_path"])
                zf.write(fp, fp.relative_to(project_dir))
        return DrawingRefineReport(
            project_name=project_name,
            input_image_path=str(input_image_path),
            normalized_png_path=str(normalized_path),
            parts_overlay_path=str(overlay_path),
            parts_manifest_path=str(parts_manifest_path),
            expression_manifest_path=str(expression_manifest_path),
            expression_csv_path=str(csv_path),
            html_path=str(html_path),
            zip_path=str(zip_path),
            checksum_sha256=checksum,
            part_count=len(parts),
            variant_count=len(variant_files),
            starter_expression_count=len(starter_rows),
            part_files=part_files,
            variant_files=variant_files,
            starter_expressions=starter_rows,
            warnings=warnings,
        )
