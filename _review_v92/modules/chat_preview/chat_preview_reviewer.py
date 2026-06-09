from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import hashlib
import html
import json
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont, ImageSequence

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class ChatPreviewReport:
    project_name: str
    format_key: str
    source_count: int
    preview_count: int
    chat_usability_score: int
    final_status: str
    review_summary: Dict[str, Any]
    review_table: List[Dict[str, Any]]
    preview_files: List[Dict[str, Any]]
    html_path: str
    json_path: str
    csv_path: str
    zip_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ChatPreviewReviewer:
    """v18 카카오톡 실제 사용 화면 미리보기 + 최종 검수 보강 모듈.

    이 모듈은 제출 승인을 보장하지 않습니다. 제작된 PNG/GIF 후보를 카카오톡 채팅창처럼
    흰 배경/어두운 배경/작은 크기에서 확인하고, 문구 가독성·겹침·반복 표현 위험을
    사람이 더 쉽게 점검할 수 있도록 리포트를 생성합니다.
    """

    LIGHT_BG = (246, 247, 250, 255)
    DARK_BG = (34, 36, 42, 255)
    ME_BUBBLE = (255, 232, 89, 255)
    OTHER_BUBBLE = (255, 255, 255, 255)
    OTHER_BUBBLE_DARK = (58, 62, 72, 255)
    TEXT_DARK = (35, 35, 35, 255)
    TEXT_LIGHT = (244, 244, 244, 255)

    def __init__(self) -> None:
        self.chat_w = 720
        self.chat_h = 960
        self.icon_size = 156

    def _font(self, size: int):
        return load_korean_font(size)

    def _safe_name(self, value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in str(value))[:42] or "chat_preview"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _text_size(self, draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
        try:
            box = draw.textbbox((0, 0), text, font=font)
            return box[2] - box[0], box[3] - box[1]
        except Exception:
            return draw.textsize(text, font=font)

    def _wrap_text(self, text: str, max_chars: int = 16) -> List[str]:
        text = str(text or "").strip()
        if not text:
            return [""]
        # spaces first; Korean short phrases usually have no spaces, so fallback slicing.
        words = text.split()
        lines: List[str] = []
        if len(words) > 1:
            current = ""
            for w in words:
                if len((current + " " + w).strip()) <= max_chars:
                    current = (current + " " + w).strip()
                else:
                    if current:
                        lines.append(current)
                    current = w
            if current:
                lines.append(current)
        else:
            while text:
                lines.append(text[:max_chars])
                text = text[max_chars:]
        return lines[:3]

    def _load_preview_image(self, path: Optional[str], phrase: str, expression: Dict[str, Any]) -> Image.Image:
        if path:
            p = Path(path)
            if p.exists():
                try:
                    img = Image.open(p)
                    if getattr(img, "is_animated", False):
                        img.seek(0)
                    return img.convert("RGBA")
                except Exception:
                    pass
        # Fallback: draw a simple emoticon card from expression plan.
        img = Image.new("RGBA", (360, 360), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        outline = (40, 34, 28, 255)
        fill = (244, 226, 165, 255)
        plan = expression.get("expression_plan") or {}
        category = str(expression.get("category", ""))
        if "사과" in category:
            fill = (238, 215, 170, 255)
        elif "분노" in category:
            fill = (240, 190, 150, 255)
        elif "피곤" in category or "퇴근" in category:
            fill = (210, 205, 190, 255)
        elif "감사" in category or "축하" in category:
            fill = (248, 220, 130, 255)
        draw.ellipse((98, 58, 262, 232), fill=fill, outline=outline, width=5)
        eye = plan.get("eye_style", "normal")
        mouth = plan.get("mouth_style", "smile")
        if eye in ["closed", "soft_closed", "down"]:
            draw.arc((132, 116, 158, 140), 0, 180, fill=outline, width=4)
            draw.arc((202, 116, 228, 140), 0, 180, fill=outline, width=4)
        elif eye in ["half", "patient"]:
            draw.line((132, 130, 158, 130), fill=outline, width=4)
            draw.line((202, 130, 228, 130), fill=outline, width=4)
        else:
            draw.ellipse((136, 122, 153, 139), fill=outline)
            draw.ellipse((207, 122, 224, 139), fill=outline)
        if mouth in ["sad", "awkward"]:
            draw.arc((150, 162, 210, 202), 180, 360, fill=outline, width=4)
        elif mouth == "open":
            draw.ellipse((170, 166, 194, 196), fill=outline)
        elif mouth in ["flat", "zigzag"]:
            draw.line((156, 178, 205, 178), fill=outline, width=4)
        else:
            draw.arc((150, 154, 210, 196), 0, 180, fill=outline, width=4)
        font = self._font(28 if len(phrase) <= 8 else 23)
        lines = self._wrap_text(phrase, 11)
        y = 254
        for line in lines:
            tw, th = self._text_size(draw, line, font)
            draw.rounded_rectangle((180 - tw//2 - 14, y - 8, 180 + tw//2 + 14, y + th + 8), radius=12, fill=(255,255,255,230), outline=outline, width=2)
            draw.text((180 - tw//2, y), line, font=font, fill=outline)
            y += th + 12
        return img

    def _fit_icon(self, img: Image.Image, size: int) -> Image.Image:
        img = img.convert("RGBA")
        img.thumbnail((size, size), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        canvas.alpha_composite(img, ((size - img.width)//2, (size - img.height)//2))
        return canvas

    def _rounded_text_bubble(self, draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, who: str, dark: bool) -> tuple[int, int, int, int]:
        font = self._font(26)
        lines = self._wrap_text(text, 18)
        sizes = [self._text_size(draw, l, font) for l in lines]
        w = max([s[0] for s in sizes] + [10]) + 38
        h = sum(s[1] for s in sizes) + 18 + max(0, len(lines)-1)*7
        x, y = xy
        fill = self.ME_BUBBLE if who == "me" else (self.OTHER_BUBBLE_DARK if dark else self.OTHER_BUBBLE)
        txt = self.TEXT_DARK if (who == "me" or not dark) else self.TEXT_LIGHT
        draw.rounded_rectangle((x, y, x+w, y+h), radius=20, fill=fill)
        ty = y + 9
        for line, (tw, th) in zip(lines, sizes):
            draw.text((x + 19, ty), line, font=font, fill=txt)
            ty += th + 7
        return (x, y, x+w, y+h)

    def _draw_chat_frame(self, icon: Image.Image, expression: Dict[str, Any], theme: str, small_scale: bool) -> Image.Image:
        dark = theme == "dark"
        bg = self.DARK_BG if dark else self.LIGHT_BG
        canvas = Image.new("RGBA", (self.chat_w, self.chat_h), bg)
        draw = ImageDraw.Draw(canvas)
        # top bar
        top_fill = (28,30,35,255) if dark else (235,238,242,255)
        draw.rectangle((0, 0, self.chat_w, 72), fill=top_fill)
        title_font = self._font(25)
        small_font = self._font(18)
        draw.text((28, 22), "카카오톡 미리보기", font=title_font, fill=self.TEXT_LIGHT if dark else self.TEXT_DARK)
        draw.text((500, 27), "실제 제출 전 확인용", font=small_font, fill=(170,170,170,255) if dark else (90,90,90,255))
        # sample chat text
        phrase = str(expression.get("phrase") or expression.get("text") or "확인했습니다")
        category = str(expression.get("category", "표현"))
        draw.text((30, 96), "상대", font=self._font(20), fill=(210,210,210,255) if dark else (80,80,80,255))
        self._rounded_text_bubble(draw, (30, 124), "오늘 가능하세요?", "other", dark)
        # icon bubble area
        icon_size = 110 if small_scale else self.icon_size
        fitted = self._fit_icon(icon, icon_size)
        x_icon = 30
        y_icon = 228
        if not small_scale:
            draw.text((30, 204), "나", font=self._font(20), fill=(210,210,210,255) if dark else (80,80,80,255))
        bubble_fill = (250, 250, 250, 255) if not dark else (48, 52, 60, 255)
        draw.rounded_rectangle((x_icon-10, y_icon-10, x_icon+icon_size+10, y_icon+icon_size+10), radius=24, fill=bubble_fill)
        canvas.alpha_composite(fitted, (x_icon, y_icon))
        self._rounded_text_bubble(draw, (30, y_icon + icon_size + 42), "감사합니다!", "other", dark)
        # right side diagnostic panel
        panel_x = 270
        panel_y = 112
        panel_fill = (42,45,52,255) if dark else (255,255,255,255)
        draw.rounded_rectangle((panel_x, panel_y, self.chat_w-28, self.chat_h-44), radius=24, fill=panel_fill)
        text_color = self.TEXT_LIGHT if dark else self.TEXT_DARK
        draw.text((panel_x+24, panel_y+24), "표현 점검", font=self._font(30), fill=text_color)
        detail_lines = [
            f"문구: {phrase}",
            f"분류: {category}",
            f"배경: {'어두운 채팅창' if dark else '밝은 채팅창'}",
            f"보기: {'작은 크기' if small_scale else '일반 크기'}",
        ]
        y = panel_y + 78
        for line in detail_lines:
            for wrapped in self._wrap_text(line, 17):
                draw.text((panel_x+24, y), wrapped, font=self._font(22), fill=text_color)
                y += 33
        draw.line((panel_x+24, y+6, self.chat_w-54, y+6), fill=(100,100,100,180), width=1)
        y += 28
        tips = self._review_expression(expression, phrase, icon)
        for key in ["readability_note", "small_screen_note", "background_note", "motion_note"]:
            msg = str(tips.get(key, ""))
            for wrapped in self._wrap_text("· " + msg, 18):
                draw.text((panel_x+24, y), wrapped, font=self._font(20), fill=text_color)
                y += 30
        return canvas.convert("RGB")

    def _review_expression(self, expression: Dict[str, Any], phrase: str, icon: Image.Image) -> Dict[str, Any]:
        text_len = len(str(phrase))
        plan = expression.get("expression_plan") or {}
        effects = plan.get("effects") or []
        if isinstance(effects, str):
            effects = [effects]
        score = 92
        warnings: List[str] = []
        if text_len > 14:
            score -= 12
            warnings.append("문구가 길어 작은 채팅창에서 읽기 어려울 수 있음")
        if text_len > 22:
            score -= 10
            warnings.append("문구를 2개 표현으로 나누는 것 검토")
        if icon.width != icon.height:
            score -= 5
            warnings.append("원본 비율이 정사각형이 아니라 여백/잘림 재확인 필요")
        # alpha bounding box for cut/empty margins
        alpha = icon.convert("RGBA").getchannel("A")
        bbox = alpha.getbbox()
        margin_note = "표시 영역 양호"
        if bbox:
            x0, y0, x1, y1 = bbox
            if x0 < 2 or y0 < 2 or icon.width - x1 < 2 or icon.height - y1 < 2:
                score -= 7
                warnings.append("캐릭터/문구가 가장자리에 가까워 잘림 위험")
                margin_note = "가장자리 잘림 위험 확인"
            used_ratio = ((x1-x0)*(y1-y0)) / max(1, icon.width*icon.height)
            if used_ratio < 0.13:
                score -= 8
                warnings.append("작은 화면에서 너무 작게 보일 수 있음")
                margin_note = "표시 영역이 작음"
        else:
            score -= 25
            warnings.append("투명/빈 이미지일 수 있음")
            margin_note = "표시 영역 없음"
        if not plan:
            score -= 6
            warnings.append("표정/움직임 계획이 없어 감정 전달 재확인 필요")
        if expression.get("category") in ["감사", "축하"] and not any(e in effects for e in ["heart", "sparkle", "confetti", "small_heart"]):
            score -= 3
        score = max(0, min(100, score))
        status = "양호" if score >= 85 else ("보완 권장" if score >= 70 else "수정 필요")
        return {
            "score": score,
            "status": status,
            "warnings": warnings,
            "readability_note": "문구 가독성 양호" if text_len <= 14 else "문구가 길어 크기/줄바꿈 확인 필요",
            "small_screen_note": margin_note,
            "background_note": "밝은/어두운 배경 모두 확인 대상",
            "motion_note": "GIF는 첫 프레임/마지막 프레임 연결 확인" if "animated" in str(expression.get("format_key", "")) else "정지형은 표정과 문구 겹침 확인",
        }

    def _match_preview_paths(self, expressions: List[Dict[str, Any]], preview_files: Optional[List[Dict[str, Any]]]) -> List[Optional[str]]:
        paths: List[Optional[str]] = [None] * len(expressions)
        if not preview_files:
            return paths
        by_no: Dict[str, str] = {}
        ordered: List[str] = []
        for item in preview_files:
            p = item.get("file_path") or item.get("path") or item.get("preview_path")
            if not p:
                continue
            ordered.append(str(p))
            for key in ["selected_no", "no", "index"]:
                if key in item:
                    by_no[str(item[key])] = str(p)
        for i, e in enumerate(expressions):
            no = str(e.get("selected_no") or e.get("no") or e.get("index") or "")
            if no in by_no:
                paths[i] = by_no[no]
            elif i < len(ordered):
                paths[i] = ordered[i]
        return paths

    def build_preview_pack(
        self,
        expressions: List[Dict[str, Any]],
        output_dir: Path,
        project_name: str,
        format_key: str,
        preview_files: Optional[List[Dict[str, Any]]] = None,
        preview_limit: int = 12,
        include_dark: bool = True,
        include_small: bool = True,
    ) -> ChatPreviewReport:
        output_dir = Path(output_dir)
        safe_project = self._safe_name(project_name)
        pack_dir = output_dir / safe_project
        img_dir = pack_dir / "chat_previews"
        meta_dir = pack_dir / "meta"
        img_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)

        selected = [dict(e) for e in expressions[:max(1, preview_limit)]]
        matched_paths = self._match_preview_paths(selected, preview_files)
        preview_records: List[Dict[str, Any]] = []
        review_table: List[Dict[str, Any]] = []

        for idx, exp in enumerate(selected, start=1):
            phrase = str(exp.get("phrase") or exp.get("text") or f"표현 {idx}")
            icon = self._load_preview_image(matched_paths[idx-1], phrase, exp)
            exp["format_key"] = format_key
            review = self._review_expression(exp, phrase, icon)
            themes = ["light"] + (["dark"] if include_dark else [])
            scales = [False] + ([True] if include_small else [])
            generated_for_exp: List[str] = []
            for theme in themes:
                for small in scales:
                    name = f"{idx:02d}_{theme}_{'small' if small else 'normal'}.png"
                    path = img_dir / name
                    frame = self._draw_chat_frame(icon, exp, theme=theme, small_scale=small)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    frame.save(path)
                    generated_for_exp.append(str(path))
                    preview_records.append({
                        "selected_no": exp.get("selected_no", idx),
                        "phrase": phrase,
                        "theme": theme,
                        "scale": "small" if small else "normal",
                        "file_path": str(path),
                        "sha256": self._checksum(path),
                    })
            review_table.append({
                "selected_no": exp.get("selected_no", idx),
                "category": exp.get("category", ""),
                "phrase": phrase,
                "score": review["score"],
                "status": review["status"],
                "warnings": " / ".join(review["warnings"]) if review["warnings"] else "",
                "readability_note": review["readability_note"],
                "small_screen_note": review["small_screen_note"],
                "background_note": review["background_note"],
                "motion_note": review["motion_note"],
                "preview_count": len(generated_for_exp),
            })

        avg_score = int(round(sum(r["score"] for r in review_table) / max(1, len(review_table))))
        warn_count = sum(1 for r in review_table if r["status"] != "양호")
        final_status = "채팅 사용성 양호" if avg_score >= 85 and warn_count <= max(1, len(review_table)//5) else ("보완 후 제출 권장" if avg_score >= 72 else "제출 전 수정 필요")
        summary = {
            "average_score": avg_score,
            "warning_count": warn_count,
            "checked_backgrounds": "light/dark" if include_dark else "light",
            "checked_scales": "normal/small" if include_small else "normal",
            "review_rules": [
                "밝은 채팅창과 어두운 채팅창에서 문구 대비 확인",
                "작은 크기에서 캐릭터/문구 인식성 확인",
                "긴 문구·가장자리 잘림·빈 이미지 위험 경고",
                "움직이는 문구형은 첫 프레임/마지막 프레임 자연스러움 별도 확인",
            ],
        }

        csv_path = meta_dir / "chat_preview_review_table.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(review_table[0].keys()) if review_table else ["selected_no", "phrase"])
            writer.writeheader()
            writer.writerows(review_table)

        json_path = meta_dir / "chat_preview_final_review.json"
        data = {
            "project_name": project_name,
            "format_key": format_key,
            "source_count": len(expressions),
            "preview_count": len(preview_records),
            "chat_usability_score": avg_score,
            "final_status": final_status,
            "review_summary": summary,
            "review_table": review_table,
            "preview_files": preview_records,
        }
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        html_path = meta_dir / "chat_preview_final_review.html"
        html_path.write_text(self._build_html(data), encoding="utf-8")

        zip_path = output_dir / f"{safe_project}_chat_preview_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in [html_path, json_path, csv_path]:
                zf.write(p, p.relative_to(pack_dir))
            for item in preview_records:
                p = Path(item["file_path"])
                if p.exists():
                    zf.write(p, p.relative_to(pack_dir))

        return ChatPreviewReport(
            project_name=project_name,
            format_key=format_key,
            source_count=len(expressions),
            preview_count=len(preview_records),
            chat_usability_score=avg_score,
            final_status=final_status,
            review_summary=summary,
            review_table=review_table,
            preview_files=preview_records,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
        )

    def _build_html(self, data: Dict[str, Any]) -> str:
        rows = []
        for r in data.get("review_table", []):
            rows.append("<tr>" + "".join(f"<td>{html.escape(str(r.get(k, '')))}</td>" for k in ["selected_no", "category", "phrase", "score", "status", "warnings", "readability_note", "small_screen_note", "motion_note"]) + "</tr>")
        preview_html = []
        for p in data.get("preview_files", [])[:40]:
            rel = Path(p["file_path"]).name
            src = "../chat_previews/" + html.escape(rel)
            cap = html.escape(f"{p.get('selected_no')} · {p.get('phrase')} · {p.get('theme')} · {p.get('scale')}")
            preview_html.append(f"<figure><img src='{src}'><figcaption>{cap}</figcaption></figure>")
        summary = data.get("review_summary", {})
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<title>v18 채팅창 미리보기 최종 리뷰</title>
<style>
body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;background:#f7f7f7;color:#222}}
h1{{margin-bottom:8px}} .box{{background:white;border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 1px 5px #ddd}}
.badge{{display:inline-block;padding:8px 12px;border-radius:999px;background:#ffe15a;font-weight:bold}}
table{{border-collapse:collapse;width:100%;background:white}} th,td{{border:1px solid #ddd;padding:8px;font-size:13px;vertical-align:top}} th{{background:#f0f0f0}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}} figure{{background:white;border-radius:14px;padding:10px;margin:0;box-shadow:0 1px 4px #ddd}} img{{max-width:100%;border-radius:10px}} figcaption{{font-size:12px;color:#555;margin-top:6px}}
</style></head><body>
<h1>v18 채팅창 미리보기 + 최종 검수 리포트</h1>
<div class='box'><span class='badge'>{html.escape(str(data.get('final_status','')))}</span>
<p>채팅 사용성 점수: <b>{data.get('chat_usability_score')}</b> / 100</p>
<p>검사 표현 수: {data.get('source_count')} · 생성 미리보기 수: {data.get('preview_count')}</p>
<p>배경 검사: {html.escape(str(summary.get('checked_backgrounds','')))} · 크기 검사: {html.escape(str(summary.get('checked_scales','')))}</p></div>
<div class='box'><h2>검사 기준</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in summary.get('review_rules', []))}</ul></div>
<div class='box'><h2>표현별 검수표</h2><table><thead><tr><th>번호</th><th>분류</th><th>문구</th><th>점수</th><th>상태</th><th>경고</th><th>가독성</th><th>작은 화면</th><th>움직임</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class='box'><h2>채팅창 미리보기</h2><div class='gallery'>{''.join(preview_html)}</div></div>
</body></html>"""
