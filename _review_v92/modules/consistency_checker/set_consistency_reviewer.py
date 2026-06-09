from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import csv
import hashlib
import html
import json
import math
import statistics
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont, ImageStat

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class ConsistencyReport:
    project_name: str
    format_key: str
    source_count: int
    preview_count: int
    consistency_score: int
    final_status: str
    summary: Dict[str, Any]
    review_table: List[Dict[str, Any]]
    correction_table: List[Dict[str, Any]]
    generated_files: List[Dict[str, Any]]
    html_path: str
    json_path: str
    csv_path: str
    zip_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SetConsistencyReviewer:
    """v23 캐릭터 일관성 검사/자동 보정 모듈.

    표현 24개/32개가 같은 캐릭터 세트처럼 보이는지 검사합니다.
    색상, 표시 영역, 캐릭터 중심, 문구 길이, 표정/파츠 계획의 일관성을 점수화하고,
    자동 보정 미리보기 PNG를 생성합니다. 법적 판단 또는 카카오 승인 보장을 의미하지 않습니다.
    """

    def __init__(self) -> None:
        self.size = 360
        self.preview_limit_default = 16

    def _safe_name(self, value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in str(value))[:42] or "consistency"

    def _font(self, size: int):
        return load_korean_font(size)

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _open_first_frame(self, file_path: str | None) -> Optional[Image.Image]:
        if not file_path:
            return None
        p = Path(file_path)
        if not p.exists():
            return None
        try:
            img = Image.open(p)
            if getattr(img, "is_animated", False):
                img.seek(0)
            return img.convert("RGBA")
        except Exception:
            return None

    def _render_fallback(self, expr: Dict[str, Any]) -> Image.Image:
        phrase = str(expr.get("phrase") or expr.get("text") or "확인했습니다")
        plan = expr.get("expression_plan") or {}
        category = str(expr.get("category") or "")
        img = Image.new("RGBA", (self.size, self.size), (255, 255, 255, 0))
        d = ImageDraw.Draw(img)
        outline = (38, 34, 30, 255)
        fill = (244, 228, 172, 255)
        if any(k in category for k in ["사과", "민망"]):
            fill = (236, 214, 178, 255)
        if any(k in category for k in ["피곤", "퇴근"]):
            fill = (214, 207, 190, 255)
        if any(k in category for k in ["분노", "거절"]):
            fill = (237, 184, 150, 255)
        d.ellipse((96, 54, 264, 230), fill=fill, outline=outline, width=5)
        eye = plan.get("eye_style", "normal")
        mouth = plan.get("mouth_style", "small_smile")
        if eye in ["closed", "soft_closed", "down"]:
            d.arc((132, 116, 160, 140), 0, 180, fill=outline, width=4)
            d.arc((200, 116, 228, 140), 0, 180, fill=outline, width=4)
        elif eye in ["half", "patient"]:
            d.line((132, 130, 160, 130), fill=outline, width=4)
            d.line((200, 130, 228, 130), fill=outline, width=4)
        else:
            d.ellipse((136, 121, 153, 139), fill=outline)
            d.ellipse((207, 121, 224, 139), fill=outline)
        if mouth in ["sad", "awkward"]:
            d.arc((150, 165, 210, 202), 180, 360, fill=outline, width=4)
        elif mouth == "open":
            d.ellipse((169, 164, 195, 194), fill=outline)
        elif mouth in ["flat", "zigzag"]:
            d.line((154, 179, 206, 179), fill=outline, width=4)
        else:
            d.arc((150, 154, 210, 198), 0, 180, fill=outline, width=4)
        font = self._font(26 if len(phrase) <= 8 else 22)
        lines = self._wrap(phrase, 11)
        y = 252
        for line in lines[:2]:
            tw, th = self._text_size(d, line, font)
            d.rounded_rectangle((180-tw//2-14, y-8, 180+tw//2+14, y+th+8), radius=12, fill=(255,255,255,230), outline=outline, width=2)
            d.text((180-tw//2, y), line, font=font, fill=outline)
            y += th + 12
        return img

    def _wrap(self, phrase: str, max_chars: int = 12) -> List[str]:
        phrase = str(phrase or "").strip()
        if len(phrase) <= max_chars:
            return [phrase]
        out: List[str] = []
        while phrase and len(out) < 3:
            out.append(phrase[:max_chars])
            phrase = phrase[max_chars:]
        return out or [""]

    def _text_size(self, draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
        try:
            box = draw.textbbox((0, 0), text, font=font)
            return box[2]-box[0], box[3]-box[1]
        except Exception:
            return draw.textsize(text, font=font)

    def _alpha_bbox(self, img: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return img.getchannel("A").getbbox()

    def _dominant_color(self, img: Image.Image, bbox: Optional[Tuple[int,int,int,int]]) -> Tuple[int, int, int]:
        if not bbox:
            return (0, 0, 0)
        crop = img.crop(bbox).convert("RGBA")
        # Only non-transparent pixels.
        pixels = [(r,g,b) for r,g,b,a in crop.getdata() if a > 30]
        if not pixels:
            return (0, 0, 0)
        # Median-like average reduces outlier text/outline noise.
        sample = pixels[::max(1, len(pixels)//3000)]
        return tuple(int(sum(c[i] for c in sample)/len(sample)) for i in range(3))

    def _color_distance(self, c1: Tuple[int,int,int], c2: Tuple[int,int,int]) -> float:
        return math.sqrt(sum((a-b)**2 for a,b in zip(c1,c2)))

    def _analyze_image(self, img: Image.Image) -> Dict[str, Any]:
        img = img.convert("RGBA")
        bbox = self._alpha_bbox(img)
        if bbox:
            x1,y1,x2,y2 = bbox
            w = x2-x1; h = y2-y1
            center_x = (x1+x2)/2; center_y = (y1+y2)/2
            area_ratio = (w*h)/(self.size*self.size)
            margin_min = min(x1, y1, self.size-x2, self.size-y2)
        else:
            x1=y1=x2=y2=w=h=0; center_x=center_y=180; area_ratio=0; margin_min=0
        color = self._dominant_color(img, bbox)
        return {
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
            "width": int(w),
            "height": int(h),
            "center_x": round(center_x, 2),
            "center_y": round(center_y, 2),
            "area_ratio": round(area_ratio, 4),
            "margin_min": int(margin_min),
            "dominant_color": color,
        }

    def _score_item(self, stats: Dict[str, Any], ref: Dict[str, Any], expr: Dict[str, Any]) -> Tuple[int, List[str], Dict[str, Any]]:
        warnings: List[str] = []
        score = 100
        center_dx = abs(float(stats["center_x"]) - float(ref["center_x"]))
        center_dy = abs(float(stats["center_y"]) - float(ref["center_y"]))
        size_diff = abs(float(stats["area_ratio"]) - float(ref["area_ratio"]))
        color_diff = self._color_distance(tuple(stats["dominant_color"]), tuple(ref["dominant_color"]))
        phrase = str(expr.get("phrase") or expr.get("text") or "")
        plan = expr.get("expression_plan") or {}
        if center_dx > 24 or center_dy > 24:
            score -= 14
            warnings.append(f"캐릭터 중심 위치 편차 큼(dx={center_dx:.1f}, dy={center_dy:.1f})")
        elif center_dx > 14 or center_dy > 14:
            score -= 7
            warnings.append("캐릭터 중심 위치가 약간 흔들림")
        if size_diff > 0.12:
            score -= 14
            warnings.append("표현별 캐릭터 표시 크기 편차 큼")
        elif size_diff > 0.06:
            score -= 7
            warnings.append("표현별 캐릭터 표시 크기 편차 있음")
        if color_diff > 70:
            score -= 14
            warnings.append("대표 색상 차이가 커서 같은 캐릭터처럼 덜 보일 수 있음")
        elif color_diff > 42:
            score -= 7
            warnings.append("대표 색상 차이가 약간 있음")
        if int(stats["margin_min"]) < 8:
            score -= 12
            warnings.append("가장자리 여백이 부족해 잘림 위험")
        if len(phrase) > 13:
            score -= 7
            warnings.append("문구가 길어 세트 톤/가독성 흔들림 가능")
        if not plan:
            score -= 7
            warnings.append("표정 계획이 없어 자동 구성 일관성 확인 필요")
        metrics = {
            "center_dx": round(center_dx, 1),
            "center_dy": round(center_dy, 1),
            "area_diff": round(size_diff, 3),
            "color_diff": round(color_diff, 1),
            "phrase_length": len(phrase),
        }
        return max(0, min(100, score)), warnings, metrics

    def _normalize_preview(self, img: Image.Image, ref_bbox: Dict[str, Any], ref_color: Tuple[int,int,int]) -> Image.Image:
        """Preview-only correction: center/scale candidate on 360 canvas and soften dominant color variance."""
        img = img.convert("RGBA")
        bbox = self._alpha_bbox(img)
        if not bbox:
            return img
        crop = img.crop(bbox)
        ref_w = max(40, int(ref_bbox.get("width", crop.width) or crop.width))
        ref_h = max(40, int(ref_bbox.get("height", crop.height) or crop.height))
        scale = min(ref_w / max(1, crop.width), ref_h / max(1, crop.height), 1.25)
        if scale <= 0: scale = 1.0
        nw, nh = max(1, int(crop.width*scale)), max(1, int(crop.height*scale))
        crop = crop.resize((nw, nh), Image.LANCZOS)
        # Soft color consistency overlay. This is conservative; not a legal/source alteration guarantee.
        overlay = Image.new("RGBA", crop.size, (*ref_color, 32))
        crop = Image.alpha_composite(crop, overlay)
        canvas = Image.new("RGBA", (self.size, self.size), (255,255,255,0))
        cx = float(ref_bbox.get("center_x", 180)); cy = float(ref_bbox.get("center_y", 170))
        x = int(cx - nw/2); y = int(cy - nh/2)
        canvas.alpha_composite(crop, (max(0,min(self.size-nw,x)), max(0,min(self.size-nh,y))))
        return canvas

    def _write_html(self, report: ConsistencyReport, path: Path) -> None:
        rows = []
        for r in report.review_table:
            warn = "<br>".join(html.escape(w) for w in r.get("warnings", [])) or "-"
            rows.append(
                f"<tr><td>{r.get('index')}</td><td>{html.escape(str(r.get('phrase','')))}</td>"
                f"<td>{r.get('score')}</td><td>{html.escape(str(r.get('status','')))}</td>"
                f"<td>{warn}</td></tr>"
            )
        corr = []
        for c in report.correction_table[:30]:
            corr.append(
                f"<tr><td>{c.get('index')}</td><td>{html.escape(str(c.get('action','')))}</td>"
                f"<td>{html.escape(str(c.get('reason','')))}</td></tr>"
            )
        css = """
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:28px;line-height:1.55;color:#202124}
        .card{border:1px solid #ddd;border-radius:14px;padding:18px;margin:14px 0;background:#fff}
        .score{font-size:36px;font-weight:800}.good{color:#16833a}.warn{color:#b7791f}.bad{color:#c53030}
        table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #e5e7eb;padding:8px;text-align:left;vertical-align:top}th{background:#f8fafc}
        """
        cls = "good" if report.consistency_score >= 82 else "warn" if report.consistency_score >= 65 else "bad"
        body = f"""<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>
        <h1>v23 캐릭터 일관성 검사/자동 보정 리포트</h1>
        <div class='card'><div class='score {cls}'>{report.consistency_score}/100</div>
        <p><b>판정:</b> {html.escape(report.final_status)}</p>
        <p><b>검사 수:</b> {report.source_count} · <b>미리보기 수:</b> {report.preview_count}</p></div>
        <div class='card'><h2>요약</h2><pre>{html.escape(json.dumps(report.summary, ensure_ascii=False, indent=2))}</pre></div>
        <div class='card'><h2>파일별 검사표</h2><table><thead><tr><th>#</th><th>문구</th><th>점수</th><th>상태</th><th>경고</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
        <div class='card'><h2>자동 보정 제안</h2><table><thead><tr><th>#</th><th>보정</th><th>이유</th></tr></thead><tbody>{''.join(corr)}</tbody></table></div>
        <p>이 리포트는 제작 보조 자료이며 카카오 승인·법적 안전성을 보장하지 않습니다.</p>
        </body></html>"""
        path.write_text(body, encoding="utf-8")

    def build_consistency_pack(
        self,
        expressions: List[Dict[str, Any]],
        preview_files: Optional[List[Dict[str, Any]]],
        output_dir: Path,
        project_name: str,
        format_key: str = "static_text",
        auto_correct: bool = True,
        preview_limit: int = 16,
    ) -> ConsistencyReport:
        output_dir = Path(output_dir)
        safe = self._safe_name(project_name)
        root = output_dir / f"{safe}_v23_consistency"
        preview_dir = root / "previews"
        corrected_dir = root / "corrected_preview"
        root.mkdir(parents=True, exist_ok=True)
        preview_dir.mkdir(parents=True, exist_ok=True)
        corrected_dir.mkdir(parents=True, exist_ok=True)
        preview_files = preview_files or []
        path_map: Dict[int, str] = {}
        for idx, item in enumerate(preview_files):
            try:
                if "expression_index" in item:
                    path_map[int(item["expression_index"])] = item.get("file_path") or item.get("path") or ""
                else:
                    path_map[idx] = item.get("file_path") or item.get("path") or ""
            except Exception:
                path_map[idx] = item.get("file_path") or item.get("path") or ""
        source_count = len(expressions)
        analyzed: List[Dict[str, Any]] = []
        images: List[Image.Image] = []
        for idx, expr in enumerate(expressions):
            path = path_map.get(idx) or path_map.get(int(expr.get("index", idx))-1, "")
            img = self._open_first_frame(path) or self._render_fallback(expr)
            # ensure canonical 360 for stats
            if img.size != (self.size, self.size):
                canvas = Image.new("RGBA", (self.size, self.size), (255,255,255,0))
                img.thumbnail((self.size, self.size), Image.LANCZOS)
                canvas.alpha_composite(img, ((self.size-img.width)//2, (self.size-img.height)//2))
                img = canvas
            stats = self._analyze_image(img)
            images.append(img)
            analyzed.append({"expr": expr, "stats": stats, "source_path": path})
        if analyzed:
            ref = {
                "center_x": statistics.median([a["stats"]["center_x"] for a in analyzed]),
                "center_y": statistics.median([a["stats"]["center_y"] for a in analyzed]),
                "area_ratio": statistics.median([a["stats"]["area_ratio"] for a in analyzed]),
                "width": int(statistics.median([a["stats"]["width"] for a in analyzed])),
                "height": int(statistics.median([a["stats"]["height"] for a in analyzed])),
                "dominant_color": tuple(int(statistics.median([a["stats"]["dominant_color"][i] for a in analyzed])) for i in range(3)),
            }
        else:
            ref = {"center_x":180,"center_y":170,"area_ratio":0.4,"width":180,"height":180,"dominant_color":(230,210,160)}
        review_table: List[Dict[str, Any]] = []
        correction_table: List[Dict[str, Any]] = []
        generated_files: List[Dict[str, Any]] = []
        scores: List[int] = []
        preview_count = min(preview_limit, source_count)
        for idx, (a, img) in enumerate(zip(analyzed, images), start=1):
            score, warnings, metrics = self._score_item(a["stats"], ref, a["expr"])
            scores.append(score)
            status = "양호" if score >= 82 else "보완 권장" if score >= 65 else "수정 필요"
            phrase = str(a["expr"].get("phrase") or a["expr"].get("text") or "")
            review_table.append({
                "index": idx,
                "phrase": phrase,
                "category": a["expr"].get("category", ""),
                "score": score,
                "status": status,
                "warnings": warnings,
                "metrics": metrics,
                "stats": a["stats"],
                "source_path": a["source_path"],
            })
            if warnings:
                correction_table.append({
                    "index": idx,
                    "action": "중심/크기/대표색 기준에 맞춘 자동 보정 미리보기 생성" if auto_correct else "편집기에서 위치/크기/색상 수동 점검",
                    "reason": "; ".join(warnings[:3]),
                })
            if idx <= preview_count:
                raw_path = preview_dir / f"{idx:02d}_{self._safe_name(phrase)}_raw.png"
                img.save(raw_path)
                generated_files.append({"kind":"raw_preview", "index":idx, "file_path":str(raw_path), "sha256":self._checksum(raw_path)})
                if auto_correct:
                    corr = self._normalize_preview(img, ref, tuple(ref["dominant_color"]))
                    corr_path = corrected_dir / f"{idx:02d}_{self._safe_name(phrase)}_corrected.png"
                    corr.save(corr_path)
                    generated_files.append({"kind":"corrected_preview", "index":idx, "file_path":str(corr_path), "sha256":self._checksum(corr_path)})
        avg_score = int(round(sum(scores)/len(scores))) if scores else 0
        status = "세트 일관성 양호" if avg_score >= 82 else "보완 후 제출 권장" if avg_score >= 65 else "제출 전 일관성 수정 필요"
        # Distribution summaries
        plan_keys = ["eye_style","mouth_style","body_motion","text_motion"]
        plan_summary: Dict[str, Dict[str,int]] = {}
        for key in plan_keys:
            counts: Dict[str,int] = {}
            for a in analyzed:
                val = str((a["expr"].get("expression_plan") or {}).get(key, "미지정"))
                counts[val] = counts.get(val, 0) + 1
            plan_summary[key] = counts
        summary = {
            "reference": ref,
            "average_score": avg_score,
            "warning_count": sum(1 for r in review_table if r["warnings"]),
            "needs_fix_count": sum(1 for r in review_table if r["status"] == "수정 필요"),
            "auto_correct": auto_correct,
            "plan_summary": plan_summary,
            "rules": [
                "캐릭터 중심 좌표가 표현마다 크게 흔들리지 않는지 검사",
                "표시 영역/크기 비율이 일정한지 검사",
                "대표 색상 차이가 커서 다른 캐릭터처럼 보이는지 검사",
                "가장자리 잘림 위험과 긴 문구로 인한 세트 톤 흔들림 검사",
                "자동 보정은 미리보기용이며 최종 제출 전 사용자가 확인해야 함",
            ],
        }
        csv_path = root / "set_consistency_review_table.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["index","phrase","category","score","status","warnings","metrics","source_path"])
            writer.writeheader()
            for r in review_table:
                row = dict(r)
                row["warnings"] = " | ".join(r.get("warnings", []))
                row["metrics"] = json.dumps(r.get("metrics", {}), ensure_ascii=False)
                row.pop("stats", None)
                writer.writerow(row)
        json_path = root / "set_consistency_report.json"
        html_path = root / "set_consistency_report.html"
        zip_path = output_dir / f"{safe}_v23_consistency_pack.zip"
        report = ConsistencyReport(
            project_name=project_name,
            format_key=format_key,
            source_count=source_count,
            preview_count=preview_count,
            consistency_score=avg_score,
            final_status=status,
            summary=summary,
            review_table=review_table,
            correction_table=correction_table,
            generated_files=generated_files,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
        )
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_html(report, html_path)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in [html_path, json_path, csv_path]:
                z.write(p, p.name)
            for gf in generated_files:
                fp = Path(gf["file_path"])
                if fp.exists():
                    z.write(fp, f"previews/{fp.name}")
        return report
