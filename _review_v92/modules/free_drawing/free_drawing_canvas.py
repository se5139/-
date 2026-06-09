
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import csv
import hashlib
import html
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


@dataclass
class FreeStroke:
    stroke_id: str
    points: List[Tuple[int, int]]
    color: str = "#2E2924"
    width: int = 8
    tool: str = "pen"  # pen | eraser
    opacity: int = 255
    layer_name: str = "freehand"
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["points"] = [[int(x), int(y)] for x, y in self.points]
        return d


@dataclass
class FreeDrawingReport:
    project_name: str
    stroke_count: int
    point_count: int
    canvas_png_path: str
    preview_png_path: str
    auto_clean_png_path: str
    line_art_png_path: str
    layer_manifest_path: str
    csv_path: str
    html_path: str
    zip_path: str
    checksum_sha256: str
    creation_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FreeDrawingCanvas:
    """마우스/태블릿 펜/터치 기반 자유 드로잉 원본 저장 엔진.

    Streamlit UI에서는 drawable-canvas가 설치된 경우 브라우저에서 직접 그린 결과를 받고,
    설치되지 않은 경우에는 좌표 입력/업로드/샘플 스트로크 방식으로 동작합니다.
    핵심 목적은 '대충 원, 눈, 입, 몸통'처럼 사용자가 직접 만든 원본을 360×360 투명 PNG와
    창작 증거 리포트로 저장하고, 이후 표현 확장/품질검사/제출 패키지로 연결하는 것입니다.
    """

    CANVAS_SIZE = 360

    def _rgba(self, value: str, opacity: int = 255, fallback=(46, 41, 36, 255)) -> Tuple[int, int, int, int]:
        named = {
            "검정": "#2E2924", "흰색": "#FFFFFF", "연갈색": "#D1A164", "아이보리": "#F7EFD1",
            "갈색": "#966437", "노랑": "#F5D250", "연노랑": "#FAE682", "주황": "#EC9146",
            "초록": "#78B45A", "분홍": "#F0A0B4", "보라": "#AA8CD2", "파랑": "#5F96DC", "회색": "#A0A0A0",
        }
        value = named.get((value or "").strip(), (value or "").strip())
        if value.startswith("#") and len(value) in (7, 9):
            try:
                r = int(value[1:3], 16); g = int(value[3:5], 16); b = int(value[5:7], 16)
                a = int(value[7:9], 16) if len(value) == 9 else opacity
                return (r, g, b, max(0, min(255, a)))
            except Exception:
                return fallback
        return fallback

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def sample_strokes(self, character_label: str = "보리쌀", color: str = "#2E2924") -> List[FreeStroke]:
        """quick_check와 fallback UI를 위한 대충 원/눈/입/몸통 샘플 스트로크."""
        strokes: List[FreeStroke] = []
        # 얼굴 원
        pts = []
        cx, cy, r = 180, 125, 72
        for i in range(72):
            a = 2 * math.pi * i / 72
            pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
        strokes.append(FreeStroke("S01_face_circle", pts, color=color, width=8, layer_name="face", note="사용자가 대충 그린 얼굴 원 예시"))
        # 몸통 원/타원
        pts = []
        cx, cy, rx, ry = 180, 230, 72, 58
        for i in range(72):
            a = 2 * math.pi * i / 72
            pts.append((int(cx + rx * math.cos(a)), int(cy + ry * math.sin(a))))
        strokes.append(FreeStroke("S02_body", pts, color=color, width=8, layer_name="body", note="사용자가 대충 그린 몸통 예시"))
        # 눈
        strokes.append(FreeStroke("S03_left_eye", [(151, 118), (152, 118), (153, 118)], color=color, width=12, layer_name="eyes"))
        strokes.append(FreeStroke("S04_right_eye", [(207, 118), (208, 118), (209, 118)], color=color, width=12, layer_name="eyes"))
        # 웃는 입
        mouth = []
        for i in range(28):
            a = math.pi * i / 27
            mouth.append((int(180 - 34 * math.cos(a)), int(146 + 18 * math.sin(a))))
        strokes.append(FreeStroke("S05_smile", mouth, color=color, width=6, layer_name="mouth"))
        # 팔
        strokes.append(FreeStroke("S06_left_arm", [(116, 214), (95, 232), (82, 250)], color=color, width=8, layer_name="arms"))
        strokes.append(FreeStroke("S07_right_arm", [(244, 214), (265, 232), (278, 250)], color=color, width=8, layer_name="arms"))
        return strokes

    def parse_strokes_from_text(self, text: str, color: str = "#2E2924", width: int = 8) -> List[FreeStroke]:
        """간단 좌표 입력 파서.

        형식 예:
        face: 120,120 180,70 240,120 180,190 120,120
        eye: 150,120 151,120
        """
        strokes: List[FreeStroke] = []
        for idx, raw in enumerate((text or "").splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name = f"stroke_{idx:02d}"
            coords = line
            if ":" in line:
                name, coords = [x.strip() for x in line.split(":", 1)]
            pts: List[Tuple[int, int]] = []
            for token in coords.replace(";", " ").split():
                if "," not in token:
                    continue
                try:
                    x, y = token.split(",", 1)
                    pts.append((max(0, min(self.CANVAS_SIZE, int(float(x)))), max(0, min(self.CANVAS_SIZE, int(float(y))))))
                except Exception:
                    continue
            if pts:
                strokes.append(FreeStroke(f"S{idx:02d}_{name}", pts, color=color, width=width, layer_name=name, note="좌표 입력 자유 드로잉"))
        return strokes

    def strokes_from_canvas_json(self, canvas_json: Dict[str, Any], fallback_color: str = "#2E2924", fallback_width: int = 8) -> List[FreeStroke]:
        """streamlit-drawable-canvas Fabric JSON에서 path/line 객체를 최대한 안전하게 변환."""
        strokes: List[FreeStroke] = []
        objects = (canvas_json or {}).get("objects") or []
        for idx, obj in enumerate(objects, start=1):
            color = obj.get("stroke") or obj.get("fill") or fallback_color
            width = int(obj.get("strokeWidth") or fallback_width)
            left = float(obj.get("left") or 0)
            top = float(obj.get("top") or 0)
            pts: List[Tuple[int, int]] = []
            if obj.get("type") == "path" and obj.get("path"):
                for item in obj.get("path") or []:
                    # Fabric path item: ['M', x, y] / ['Q', ...] / ['L', x, y]
                    nums = [v for v in item[1:] if isinstance(v, (int, float))]
                    if len(nums) >= 2:
                        x, y = nums[-2], nums[-1]
                        pts.append((int(max(0, min(self.CANVAS_SIZE, left + x))), int(max(0, min(self.CANVAS_SIZE, top + y)))))
            elif obj.get("type") in {"line", "polyline"}:
                if obj.get("points"):
                    for p in obj.get("points"):
                        pts.append((int(left + p.get("x", 0)), int(top + p.get("y", 0))))
                else:
                    pts = [(int(obj.get("x1", 0)), int(obj.get("y1", 0))), (int(obj.get("x2", 0)), int(obj.get("y2", 0)))]
            if pts:
                strokes.append(FreeStroke(f"S{idx:02d}_canvas_{obj.get('type','path')}", pts, color=color, width=width, layer_name="browser_canvas", note="마우스/펜/터치 브라우저 캔버스 입력"))
        return strokes

    def render_strokes(self, strokes: List[FreeStroke], background: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        img = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), background or (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for s in strokes:
            if not s.points:
                continue
            color = (255, 255, 255, 0) if s.tool == "eraser" else self._rgba(s.color, s.opacity)
            if len(s.points) == 1:
                x, y = s.points[0]
                r = max(1, int(s.width)//2)
                draw.ellipse((x-r, y-r, x+r, y+r), fill=color)
            else:
                draw.line(s.points, fill=color, width=max(1, int(s.width)), joint="curve")
        return img

    def auto_clean_line_art(self, img: Image.Image, stroke_smooth: bool = True) -> Image.Image:
        """초보자 손그림을 360×360 투명 PNG로 정리. 복잡한 AI 보정 없이 알파/여백/선명도만 정돈."""
        im = img.convert("RGBA")
        # crop to non-transparent bbox and center it with safe padding
        alpha = im.split()[-1]
        bbox = alpha.getbbox()
        if bbox:
            cropped = im.crop(bbox)
            max_side = max(cropped.size)
            scale = min(1.0, 300 / max_side) if max_side else 1.0
            if scale != 1.0:
                cropped = cropped.resize((int(cropped.width*scale), int(cropped.height*scale)), Image.LANCZOS)
            out = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (255, 255, 255, 0))
            out.alpha_composite(cropped, ((self.CANVAS_SIZE-cropped.width)//2, (self.CANVAS_SIZE-cropped.height)//2))
            im = out
        return im

    def _write_html(self, report: Dict[str, Any], out: Path) -> None:
        rows = "".join(
            f"<tr><td>{html.escape(str(x.get('stroke_id','')))}</td><td>{html.escape(str(x.get('layer_name','')))}</td><td>{len(x.get('points',[]))}</td><td>{html.escape(str(x.get('color','')))}</td><td>{x.get('width')}</td><td>{html.escape(str(x.get('note','')))}</td></tr>"
            for x in report.get("strokes", [])
        )
        notes = "".join(f"<li>{html.escape(n)}</li>" for n in report.get("creation_notes", []))
        body = f"""
        <html><head><meta charset='utf-8'><title>자유 드로잉 캔버스 리포트</title>
        <style>body{{font-family:Arial,'Malgun Gothic',sans-serif;line-height:1.55;padding:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#f5f5f5}}.box{{background:#eef8ff;padding:14px;border-radius:10px}}</style></head><body>
        <h1>v24 자유 드로잉 캔버스 리포트</h1>
        <div class='box'><b>프로젝트:</b> {html.escape(report.get('project_name',''))}<br><b>스트로크 수:</b> {report.get('stroke_count',0)}<br><b>포인트 수:</b> {report.get('point_count',0)}<br><b>SHA-256:</b> {html.escape(report.get('checksum_sha256',''))}</div>
        <h2>창작 기록 메모</h2><ul>{notes}</ul>
        <h2>스트로크 목록</h2><table><tr><th>ID</th><th>레이어</th><th>포인트</th><th>색상</th><th>굵기</th><th>메모</th></tr>{rows}</table>
        <p>마우스·태블릿 펜·터치 입력은 사용자의 직접 창작 출발점으로 기록됩니다. 이 리포트는 승인/법적 판단을 보장하지 않습니다.</p>
        </body></html>
        """
        out.write_text(body, encoding="utf-8")

    def build_project(self, strokes: List[FreeStroke], output_dir: Path, project_name: str = "free_drawing_project") -> FreeDrawingReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in project_name)[:80] or "free_drawing_project"
        project_dir = output_dir / f"{safe_name}_{int(time.time())}"
        project_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = project_dir / "assets"; assets_dir.mkdir(exist_ok=True)

        transparent = self.render_strokes(strokes)
        canvas_path = assets_dir / f"{safe_name}_freehand_360_transparent.png"
        transparent.save(canvas_path)
        preview = self.render_strokes(strokes, background=(250, 250, 250, 255))
        preview_path = assets_dir / f"{safe_name}_freehand_preview_bg.png"
        preview.save(preview_path)
        clean = self.auto_clean_line_art(transparent)
        clean_path = assets_dir / f"{safe_name}_auto_clean_360.png"
        clean.save(clean_path)
        line_art = self.render_strokes([s for s in strokes if s.tool != "eraser"])
        line_path = assets_dir / f"{safe_name}_line_art_original.png"
        line_art.save(line_path)

        checksum = self._checksum(clean_path)
        stroke_rows = [s.to_dict() for s in strokes]
        creation_notes = [
            "사용자가 마우스/태블릿 펜/터치/좌표 입력으로 직접 만든 자유 드로잉 원본입니다.",
            "대충 원, 눈, 입, 몸통만 그려도 360×360 투명 PNG로 정리하고 후속 표현 확장에 연결할 수 있습니다.",
            "자동 정리는 여백/중앙/투명 배경 보정 중심이며, 제출용 AI 완성본 은폐 목적이 아닙니다.",
            "스트로크 좌표, 색상, 굵기, SHA-256을 저장해 직접 창작 과정 증거로 활용할 수 있습니다.",
        ]
        manifest = {
            "project_name": project_name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "canvas_size": [self.CANVAS_SIZE, self.CANVAS_SIZE],
            "stroke_count": len(strokes),
            "point_count": sum(len(s.points) for s in strokes),
            "strokes": stroke_rows,
            "canvas_png_path": str(canvas_path),
            "preview_png_path": str(preview_path),
            "auto_clean_png_path": str(clean_path),
            "line_art_png_path": str(line_path),
            "checksum_sha256": checksum,
            "creation_notes": creation_notes,
        }
        manifest_path = project_dir / "free_drawing_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        csv_path = project_dir / "free_drawing_strokes.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["stroke_id", "layer_name", "tool", "color", "width", "opacity", "point_count", "points", "note"])
            writer.writeheader()
            for s in strokes:
                writer.writerow({
                    "stroke_id": s.stroke_id,
                    "layer_name": s.layer_name,
                    "tool": s.tool,
                    "color": s.color,
                    "width": s.width,
                    "opacity": s.opacity,
                    "point_count": len(s.points),
                    "points": json.dumps([[int(x), int(y)] for x, y in s.points], ensure_ascii=False),
                    "note": s.note,
                })
        html_path = project_dir / "free_drawing_report.html"
        self._write_html(manifest, html_path)
        zip_path = project_dir / f"{safe_name}_free_drawing_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in [canvas_path, preview_path, clean_path, line_path, manifest_path, csv_path, html_path]:
                zf.write(fp, fp.relative_to(project_dir))
        return FreeDrawingReport(
            project_name=project_name,
            stroke_count=len(strokes),
            point_count=sum(len(s.points) for s in strokes),
            canvas_png_path=str(canvas_path),
            preview_png_path=str(preview_path),
            auto_clean_png_path=str(clean_path),
            line_art_png_path=str(line_path),
            layer_manifest_path=str(manifest_path),
            csv_path=str(csv_path),
            html_path=str(html_path),
            zip_path=str(zip_path),
            checksum_sha256=checksum,
            creation_notes=creation_notes,
        )
