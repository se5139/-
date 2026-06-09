
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
class CanvasLayer:
    layer_id: str
    layer_type: str
    shape: str
    x: int
    y: int
    w: int
    h: int
    fill_color: str = "#F4EBCD"
    outline_color: str = "#2E2924"
    stroke_width: int = 4
    text: str = ""
    opacity: int = 255
    visible: bool = True
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanvasProjectReport:
    project_name: str
    layer_count: int
    preview_png_path: str
    transparent_png_path: str
    layer_files: List[Dict[str, Any]]
    manifest_path: str
    html_path: str
    csv_path: str
    zip_path: str
    checksum_sha256: str
    creation_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DrawingCanvasLayerEditor:
    """초보자용 도형/파츠 기반 직접 창작 캔버스.

    사용자가 동그라미, 몸통, 눈, 입, 팔, 말풍선 같은 기본 파츠를 선택하면
    360×360 투명 PNG 원본과 레이어 증거 파일을 생성합니다.
    이 모듈은 AI 완성본 생성이 아니라 사용자가 선택한 도형/색상/텍스트를
    기록 가능한 직접 창작 출발점으로 저장하는 목적입니다.
    """

    CANVAS_SIZE = 360

    PART_PRESETS = {
        "둥근 얼굴": {"layer_type": "face", "shape": "ellipse", "x": 180, "y": 120, "w": 150, "h": 130, "fill_color": "#F4EBCD"},
        "알갱이 몸통": {"layer_type": "body", "shape": "roundrect", "x": 180, "y": 215, "w": 145, "h": 135, "fill_color": "#D1A164"},
        "길쭉 몸통": {"layer_type": "body", "shape": "capsule", "x": 180, "y": 210, "w": 115, "h": 165, "fill_color": "#E7B36D"},
        "쌀알 몸통": {"layer_type": "body", "shape": "capsule", "x": 180, "y": 205, "w": 105, "h": 150, "fill_color": "#F7EFD1"},
        "점눈 왼쪽": {"layer_type": "eye", "shape": "dot", "x": 152, "y": 112, "w": 13, "h": 13, "fill_color": "#2E2924"},
        "점눈 오른쪽": {"layer_type": "eye", "shape": "dot", "x": 208, "y": 112, "w": 13, "h": 13, "fill_color": "#2E2924"},
        "반눈 왼쪽": {"layer_type": "eye", "shape": "line", "x": 152, "y": 116, "w": 28, "h": 6, "fill_color": "#2E2924"},
        "반눈 오른쪽": {"layer_type": "eye", "shape": "line", "x": 208, "y": 116, "w": 28, "h": 6, "fill_color": "#2E2924"},
        "웃는 입": {"layer_type": "mouth", "shape": "smile", "x": 180, "y": 145, "w": 46, "h": 28, "fill_color": "#2E2924"},
        "무표정 입": {"layer_type": "mouth", "shape": "line", "x": 180, "y": 150, "w": 42, "h": 6, "fill_color": "#2E2924"},
        "삐죽 입": {"layer_type": "mouth", "shape": "zigzag", "x": 180, "y": 151, "w": 44, "h": 16, "fill_color": "#2E2924"},
        "왼팔": {"layer_type": "arm", "shape": "arm_left", "x": 112, "y": 220, "w": 70, "h": 42, "fill_color": "#2E2924"},
        "오른팔": {"layer_type": "arm", "shape": "arm_right", "x": 248, "y": 220, "w": 70, "h": 42, "fill_color": "#2E2924"},
        "땀 효과": {"layer_type": "effect", "shape": "teardrop", "x": 248, "y": 98, "w": 24, "h": 34, "fill_color": "#77C7EA"},
        "하트 효과": {"layer_type": "effect", "shape": "heart", "x": 252, "y": 82, "w": 34, "h": 34, "fill_color": "#F06C8C"},
        "말풍선": {"layer_type": "bubble", "shape": "speech_bubble", "x": 180, "y": 295, "w": 230, "h": 56, "fill_color": "#FFFFFF"},
    }

    def _font(self, size: int):
        return load_korean_font(size)

    def _rgba(self, value: str, opacity: int = 255, fallback: Tuple[int, int, int, int] = (244, 235, 205, 255)) -> Tuple[int, int, int, int]:
        if not value:
            return fallback
        value = value.strip()
        named = {
            "연갈색": "#D1A164", "아이보리": "#F7EFD1", "갈색": "#966437", "회색": "#A0A0A0",
            "노랑": "#F5D250", "연노랑": "#FAE682", "주황": "#EC9146", "초록": "#78B45A",
            "분홍": "#F0A0B4", "보라": "#AA8CD2", "파랑": "#5F96DC", "검정": "#2E2924", "흰색": "#FFFFFF",
        }
        value = named.get(value, value)
        if value.startswith("#") and len(value) in (7, 9):
            try:
                r = int(value[1:3], 16); g = int(value[3:5], 16); b = int(value[5:7], 16)
                a = int(value[7:9], 16) if len(value) == 9 else opacity
                return (r, g, b, max(0, min(255, a)))
            except Exception:
                return fallback
        return fallback

    def build_layers_from_presets(self, preset_names: List[str], base_color: str = "#D1A164", label_text: str = "") -> List[CanvasLayer]:
        layers: List[CanvasLayer] = []
        for idx, name in enumerate(preset_names, start=1):
            p = dict(self.PART_PRESETS.get(name, {}))
            if not p:
                continue
            if p.get("layer_type") in {"face", "body"}:
                p["fill_color"] = base_color or p.get("fill_color", "#F4EBCD")
            layers.append(CanvasLayer(layer_id=f"L{idx:02d}_{name}", note=f"preset:{name}", **p))
        if label_text:
            layers.append(CanvasLayer(layer_id=f"L{len(layers)+1:02d}_text", layer_type="text", shape="text", x=180, y=295, w=240, h=46, fill_color="#2E2924", outline_color="#2E2924", stroke_width=1, text=label_text[:18], note="직접 입력 문구"))
        return layers

    def _draw_layer(self, draw: ImageDraw.ImageDraw, layer: CanvasLayer) -> None:
        if not layer.visible:
            return
        fill = self._rgba(layer.fill_color, layer.opacity)
        outline = self._rgba(layer.outline_color, 255, (46, 41, 36, 255))
        sw = max(1, int(layer.stroke_width))
        x, y, w, h = int(layer.x), int(layer.y), int(layer.w), int(layer.h)
        box = (x - w//2, y - h//2, x + w//2, y + h//2)
        shape = layer.shape
        if shape == "ellipse" or shape == "dot":
            draw.ellipse(box, fill=fill, outline=outline if shape != "dot" else None, width=sw)
        elif shape == "roundrect":
            draw.rounded_rectangle(box, radius=max(8, min(w, h)//5), fill=fill, outline=outline, width=sw)
        elif shape == "capsule":
            draw.rounded_rectangle(box, radius=max(18, min(w, h)//2), fill=fill, outline=outline, width=sw)
        elif shape == "line":
            draw.line((x - w//2, y, x + w//2, y), fill=fill, width=sw+2)
        elif shape == "smile":
            draw.arc(box, start=0, end=180, fill=fill, width=sw+2)
        elif shape == "zigzag":
            pts = [(x-w//2, y), (x-w//4, y+h//4), (x, y), (x+w//4, y+h//4), (x+w//2, y)]
            draw.line(pts, fill=fill, width=sw+1, joint="curve")
        elif shape == "arm_left":
            draw.line((x + w//3, y - h//3, x - w//3, y + h//3), fill=fill, width=sw+2)
        elif shape == "arm_right":
            draw.line((x - w//3, y - h//3, x + w//3, y + h//3), fill=fill, width=sw+2)
        elif shape == "teardrop":
            draw.ellipse((x-w//3, y-h//2, x+w//3, y+h//4), fill=fill, outline=outline, width=1)
            draw.polygon([(x, y+h//2), (x-w//4, y), (x+w//4, y)], fill=fill)
        elif shape == "heart":
            # simple heart made of circles and polygon
            draw.ellipse((x-w//2, y-h//2, x, y), fill=fill)
            draw.ellipse((x, y-h//2, x+w//2, y), fill=fill)
            draw.polygon([(x-w//2, y-h//5), (x+w//2, y-h//5), (x, y+h//2)], fill=fill)
        elif shape == "speech_bubble":
            draw.rounded_rectangle(box, radius=14, fill=fill, outline=outline, width=max(1, sw//2))
            draw.polygon([(x-w//5, y+h//2-2), (x-w//8, y+h//2+18), (x, y+h//2-2)], fill=fill, outline=outline)
        elif shape == "text":
            font = self._font(max(12, min(38, int(h*0.65))))
            draw.text((x, y), layer.text or "", anchor="mm", fill=fill, font=font)
        else:
            draw.rectangle(box, fill=fill, outline=outline, width=sw)

    def render_canvas(self, layers: List[CanvasLayer], background: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        img = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), background or (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for layer in layers:
            self._draw_layer(draw, layer)
        return img

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _write_html(self, report: Dict[str, Any], out: Path) -> None:
        layer_rows = "".join(
            f"<tr><td>{html.escape(str(x.get('layer_id','')))}</td><td>{html.escape(str(x.get('layer_type','')))}</td><td>{html.escape(str(x.get('shape','')))}</td><td>{x.get('x')},{x.get('y')}</td><td>{x.get('w')}×{x.get('h')}</td><td>{html.escape(str(x.get('fill_color','')))}</td></tr>"
            for x in report.get("layers", [])
        )
        notes = "".join(f"<li>{html.escape(n)}</li>" for n in report.get("creation_notes", []))
        body = f"""
        <html><head><meta charset='utf-8'><title>직접 그리기 캔버스 리포트</title>
        <style>body{{font-family:Arial,'Malgun Gothic',sans-serif;line-height:1.55;padding:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#f5f5f5}}.box{{background:#fff8e8;padding:14px;border-radius:10px}}</style></head><body>
        <h1>v22 직접 그리기 캔버스/레이어 리포트</h1>
        <div class='box'><b>프로젝트:</b> {html.escape(report.get('project_name',''))}<br><b>레이어 수:</b> {report.get('layer_count',0)}<br><b>SHA-256:</b> {report.get('checksum_sha256','')}</div>
        <h2>창작 기록 메모</h2><ul>{notes}</ul>
        <h2>레이어 목록</h2><table><tr><th>ID</th><th>종류</th><th>도형</th><th>위치</th><th>크기</th><th>색상</th></tr>{layer_rows}</table>
        <p>주의: 이 리포트는 직접 창작 출발점과 레이어 기록 보조 자료입니다. 카카오 승인이나 법적 판단을 보장하지 않습니다.</p>
        </body></html>
        """
        out.write_text(body, encoding="utf-8")

    def build_canvas_project(self, layers: List[CanvasLayer], output_dir: Path, project_name: str = "direct_canvas_project") -> CanvasProjectReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in project_name)[:80] or "direct_canvas_project"
        project_dir = output_dir / f"{safe_name}_{int(time.time())}"
        project_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = project_dir / "assets"
        layer_dir = project_dir / "layers"
        assets_dir.mkdir(exist_ok=True)
        layer_dir.mkdir(exist_ok=True)

        transparent = self.render_canvas(layers)
        transparent_path = assets_dir / f"{safe_name}_360_transparent.png"
        transparent.save(transparent_path)
        preview = self.render_canvas(layers, background=(250, 250, 250, 255))
        preview_path = assets_dir / f"{safe_name}_preview_bg.png"
        preview.save(preview_path)

        layer_files: List[Dict[str, Any]] = []
        for idx, layer in enumerate(layers, start=1):
            layer_img = self.render_canvas([layer])
            lp = layer_dir / f"{idx:02d}_{layer.layer_type}_{layer.shape}.png"
            layer_img.save(lp)
            item = layer.to_dict()
            item.update({"file_path": str(lp), "checksum_sha256": self._checksum(lp)})
            layer_files.append(item)

        creation_notes = [
            "사용자가 도형/파츠/색상/문구를 직접 선택한 창작 출발점입니다.",
            "레이어별 PNG와 SHA-256을 저장해 수정 이력·창작 증거로 활용할 수 있습니다.",
            "스케치/사진 첨부 없이도 360×360 투명 PNG 원본을 만들 수 있습니다.",
            "AI 완성본 은폐가 아니라 직접 선택/편집 기반 상품화 보조 흐름입니다.",
        ]
        manifest = {
            "project_name": project_name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "canvas_size": [self.CANVAS_SIZE, self.CANVAS_SIZE],
            "layers": [l.to_dict() for l in layers],
            "layer_files": layer_files,
            "transparent_png_path": str(transparent_path),
            "preview_png_path": str(preview_path),
            "creation_notes": creation_notes,
        }
        checksum = self._checksum(transparent_path)
        manifest["checksum_sha256"] = checksum
        manifest_path = project_dir / "direct_canvas_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        csv_path = project_dir / "direct_canvas_layers.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["layer_id","layer_type","shape","x","y","w","h","fill_color","outline_color","stroke_width","text","opacity","visible","note","file_path","checksum_sha256"])
            writer.writeheader()
            for row in layer_files:
                writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
        html_path = project_dir / "direct_canvas_report.html"
        self._write_html({**manifest, "layer_count": len(layers)}, html_path)
        zip_path = project_dir / f"{safe_name}_direct_canvas_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in [transparent_path, preview_path, manifest_path, csv_path, html_path, *[Path(x["file_path"]) for x in layer_files]]:
                zf.write(fp, fp.relative_to(project_dir))
        return CanvasProjectReport(
            project_name=project_name,
            layer_count=len(layers),
            preview_png_path=str(preview_path),
            transparent_png_path=str(transparent_path),
            layer_files=layer_files,
            manifest_path=str(manifest_path),
            html_path=str(html_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
            checksum_sha256=checksum,
            creation_notes=creation_notes,
        )
