
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import csv
import hashlib
import html
import json
import re
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class TextPromptSpec:
    raw_prompt: str
    material: str
    shape_hint: str
    personality: str
    tone: str
    action: str
    phrase: str
    format_key: str
    concept_name: str
    concept_summary: str
    safety_notes: List[str]
    parsed_fields: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TextPromptReport:
    project_name: str
    output_dir: str
    html_path: str
    json_path: str
    csv_path: str
    zip_path: str
    spec: Dict[str, Any]
    expression_count: int
    preview_png_path: str
    preview_gif_path: str
    expression_sheet_path: str
    checksum_sha256: str
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TextPromptEmoticonEngine:
    """v27 텍스트 설명 기반 이모티콘 초안 생성 엔진.

    사용 예:
    "팽이버섯 한묶음을 얼굴로 형상화해주고 성격은 다정하고 예의바르게 인사하며 '안녕하세요' 라고 한다"

    이 엔진의 역할:
    - 자연어 설명에서 소재/형태/성격/말투/문구/행동을 추출
    - 기존 캐릭터를 모방하지 않고 새 캐릭터 콘셉트로 정리
    - 360x360 정지형 PNG 및 움직이는 문구형 GIF 초안 생성
    - 표현 후보와 제작 계획 리포트 생성
    """

    CANVAS = 360
    STOP_CHARS = ",.\n/|"

    FORMAT_NAMES = {
        "static": "멈춰있는 이모티콘",
        "static_text": "문구 결합형 멈춰있는 이모티콘",
        "animated": "움직이는 이모티콘",
        "animated_text": "움직이는 문구 결합형 이모티콘",
        "big": "큰 이모티콘",
    }

    FORBIDDEN_HINTS = [
        "춘식이", "라이언", "카카오프렌즈", "라인프렌즈", "산리오", "헬로키티",
        "포켓몬", "피카츄", "디즈니", "짱구", "스누피", "도라에몽", "비슷하게",
        "똑같이", "따라", "스타일로", "느낌으로", "AI 티 안나게", "모르게",
    ]

    MATERIAL_DEFAULT_COLORS = {
        "팽이버섯": ((246, 238, 211, 255), (216, 194, 153, 255)),
        "버섯": ((238, 218, 190, 255), (178, 119, 82, 255)),
        "보리": ((213, 168, 93, 255), (160, 111, 52, 255)),
        "쌀": ((247, 241, 218, 255), (224, 211, 180, 255)),
        "감자": ((208, 161, 96, 255), (130, 85, 47, 255)),
        "고구마": ((170, 105, 143, 255), (228, 186, 116, 255)),
        "메모지": ((255, 244, 148, 255), (70, 70, 70, 255)),
        "돌멩이": ((174, 174, 166, 255), (88, 88, 84, 255)),
        "무": ((239, 246, 226, 255), (111, 174, 86, 255)),
    }

    def _safe_name(self, value: str) -> str:
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "text_prompt_emoticon"))
        return safe[:80] or "text_prompt_emoticon"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _extract_between(self, text: str, start_keywords: List[str], end_keywords: Optional[List[str]] = None) -> str:
        best = ""
        for start in start_keywords:
            idx = text.find(start)
            if idx >= 0:
                s = idx + len(start)
                candidates = []
                if end_keywords:
                    for end in end_keywords:
                        e = text.find(end, s)
                        if e >= 0:
                            candidates.append(e)
                for ch in self.STOP_CHARS:
                    e = text.find(ch, s)
                    if e >= 0:
                        candidates.append(e)
                e = min(candidates) if candidates else min(len(text), s + 30)
                cand = text[s:e].strip(" 은는이가을를하고며,.")
                if len(cand) > len(best):
                    best = cand
        return best

    def parse_prompt(self, prompt: str, format_key: str = "animated_text") -> TextPromptSpec:
        text = (prompt or "").strip()
        warnings: List[str] = []
        if not text:
            text = "팽이버섯 한 묶음을 얼굴로 형상화하고 성격은 다정하고 예의 바르게 인사하며 안녕하세요라고 한다"

        for k in self.FORBIDDEN_HINTS:
            if k in text:
                warnings.append(f"'{k}' 표현은 기존 캐릭터 모방/AI 은폐/정책 위험 가능성이 있어 독창 방향으로 바꾸는 것이 필요합니다.")

        quote_match = re.search(r"[\"'“”‘’]([^\"'“”‘’]{1,30})[\"'“”‘’]", text)
        if quote_match:
            phrase = quote_match.group(1).strip()
        else:
            m = re.search(r"([가-힣A-Za-z0-9 .!?~]{1,18})\s*(?:라고|이라며|말하며|한다)", text)
            phrase = m.group(1).strip() if m else "안녕하세요"
            phrase = re.sub(r".*\s", "", phrase) if len(phrase) > 10 and " " in phrase else phrase
        if not phrase:
            phrase = "안녕하세요"

        personality = self._extract_between(text, ["성격은", "성격:", "성격은 ", "캐릭터 성격은"], ["말투", "문구", "라고", "하며", "하고"])
        if not personality:
            if "다정" in text:
                personality = "다정함"
            elif "까칠" in text:
                personality = "까칠함"
            elif "피곤" in text:
                personality = "피곤하지만 성실함"
            else:
                personality = "성격을 직접 보완할 수 있음"

        tone = self._extract_between(text, ["말투는", "말투:", "말투는 "], ["문구", "라고", "한다", "하며"])
        if not tone:
            if "예의" in text or "예이" in text:
                tone = "예의 바르고 부드러운 말투"
            elif "투덜" in text:
                tone = "짧게 투덜거리는 말투"
            else:
                tone = personality + "에 맞춘 말투"

        action = "인사"
        for key, label in [("따봉", "따봉"), ("좋아요", "따봉"), ("울", "울기"), ("눈물", "울기"), ("감사", "꾸벅"), ("사과", "꾸벅"), ("인사", "인사"), ("안녕", "인사"), ("확인", "확인")]:
            if key in text:
                action = label
                break

        # material extraction: before '을/를 ... 얼굴/형상화' or first noun-like chunk.
        material = ""
        m = re.search(r"(.{1,24}?)(?:을|를)\s*(?:얼굴|캐릭터|이모티콘|형상화)", text)
        if m:
            material = m.group(1).strip(" ,.")
        if not material:
            known = [k for k in self.MATERIAL_DEFAULT_COLORS.keys() if k in text]
            material = known[0] if known else text.split()[0][:16]
        material = material.replace("한묵음", "한 묶음").replace("한묶음", "한 묶음")

        shape_hint = ""
        for k in ["한 묶음", "묶음", "얼굴", "둥근", "길쭉", "알갱이", "납작", "네모", "큰손", "작은"]:
            if k in text or k in material:
                shape_hint += (", " if shape_hint else "") + k
        if not shape_hint:
            shape_hint = "소재 특징을 단순화한 얼굴형"

        clean_material = material.replace("해주고", "").replace("형상화", "").strip()
        concept_name = f"{clean_material} {action} 캐릭터"
        concept_summary = f"{clean_material}을/를 {shape_hint} 기반으로 단순화하고, 성격은 {personality}, 말투는 {tone}, 대표 문구는 '{phrase}'인 독창 이모티콘 초안입니다."
        parsed = {
            "material": clean_material,
            "shape_hint": shape_hint,
            "personality": personality,
            "tone": tone,
            "action": action,
            "phrase": phrase,
            "format_label": self.FORMAT_NAMES.get(format_key, format_key),
        }
        return TextPromptSpec(
            raw_prompt=text,
            material=clean_material,
            shape_hint=shape_hint,
            personality=personality,
            tone=tone,
            action=action,
            phrase=phrase,
            format_key=format_key,
            concept_name=concept_name,
            concept_summary=concept_summary,
            safety_notes=warnings,
            parsed_fields=parsed,
        )

    def build_expression_plan(self, spec: TextPromptSpec, count: int = 32) -> List[Dict[str, Any]]:
        base_phrase = spec.phrase or "안녕하세요"
        action = spec.action
        personality = spec.personality
        tone = spec.tone
        material = spec.material
        starters = [
            (base_phrase, action, "대표 문구"),
            ("안녕하세요", "인사", "기본 인사"),
            ("감사합니다", "꾸벅", "감사"),
            ("죄송합니다", "꾸벅", "사과"),
            ("확인했습니다", "확인", "확인"),
            ("좋아요", "따봉", "긍정"),
            ("괜찮아요", "위로", "위로"),
            ("천천히 해도 돼요", "위로", "다정"),
            ("파이팅", "응원", "응원"),
            ("잘자요", "휴식", "휴식"),
            ("눈물나요", "울기", "슬픔"),
            ("기분 좋아요", "기쁨", "기쁨"),
        ]
        if "예의" in tone or "다정" in personality:
            starters += [("반갑습니다", "인사", "예의"), ("마음이 따뜻해요", "감동", "다정")]
        if "팽이버섯" in material or "버섯" in material:
            starters += [("송송 모였습니다", "인사", "시그니처"), ("한 묶음으로 응원해요", "응원", "소재 시그니처")]
        if "보리" in material or "쌀" in material:
            starters += [("든든하게 왔어요", "인사", "곡물 시그니처"), ("밥심으로 갑니다", "응원", "시그니처")]
        rows: List[Dict[str, Any]] = []
        for i in range(count):
            phrase, motion, category = starters[i % len(starters)]
            phrase = phrase if i == 0 else phrase
            rows.append({
                "index": i + 1,
                "phrase": phrase,
                "category": category,
                "motion_family": motion,
                "face_direction": self._face_direction(category, spec),
                "motion_direction": self._motion_direction(motion, spec),
                "text_motion": self._text_motion(motion),
                "note": f"{spec.material}의 {spec.personality} 성격과 '{spec.tone}' 말투를 반영",
            })
        return rows

    def _face_direction(self, category: str, spec: TextPromptSpec) -> str:
        if category in ["감사", "예의", "대표 문구"]:
            return "부드러운 눈 + 작은 미소"
        if category == "사과":
            return "처진 눈 + 미안한 입 + 작은 땀"
        if category == "슬픔":
            return "촉촉한 눈 + 눈물 한 방울"
        if category in ["기쁨", "긍정", "응원"]:
            return "웃는 눈 + 큰 미소 + 반짝임"
        if "다정" in spec.personality:
            return "둥근 눈 + 따뜻한 미소"
        return "기본 점눈 + 단순 미소"

    def _motion_direction(self, motion: str, spec: TextPromptSpec) -> str:
        if motion == "인사":
            return "살짝 손흔들기 또는 작은 꾸벅"
        if motion == "따봉":
            return "한손/양손 따봉 중 성격에 맞춰 선택"
        if motion == "꾸벅":
            return "고개를 작게 숙임"
        if motion == "울기":
            return "눈물 한 방울 또는 조용한 눈물"
        if motion == "응원":
            return "몸이 작게 통통 튐"
        if motion == "확인":
            return "체크 표시가 도장처럼 등장"
        return "문구와 맞춰 작게 움직임"

    def _text_motion(self, motion: str) -> str:
        return {
            "인사": "문구가 천천히 나타남",
            "따봉": "문구가 통통 튀어나옴",
            "꾸벅": "문구가 부드럽게 등장",
            "울기": "문구가 작게 떨림",
            "응원": "문구가 반짝이며 등장",
            "확인": "문구가 도장처럼 찍힘",
        }.get(motion, "문구 고정")

    def _colors_for_material(self, material: str) -> Tuple[Tuple[int,int,int,int], Tuple[int,int,int,int]]:
        for key, colors in self.MATERIAL_DEFAULT_COLORS.items():
            if key in material:
                return colors
        return ((230, 210, 160, 255), (72, 60, 45, 255))

    def render_preview_png(self, spec: TextPromptSpec, out_path: Path) -> Path:
        img = Image.new("RGBA", (self.CANVAS, self.CANVAS), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        fill, outline = self._colors_for_material(spec.material)
        if "팽이버섯" in spec.material or "버섯" in spec.material:
            self._draw_enoki_bunch(draw, fill, outline)
        elif "쌀" in spec.material and "보리" not in spec.material:
            self._draw_rice_character(draw, fill, outline)
        elif "보리" in spec.material or "곡물" in spec.material:
            self._draw_grain_character(draw, fill, outline)
        else:
            self._draw_generic_character(draw, fill, outline, spec.shape_hint)
        self._draw_face_and_action(draw, spec)
        self._draw_text_label(draw, spec.phrase)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
        return out_path

    def _draw_enoki_bunch(self, draw: ImageDraw.ImageDraw, fill, outline) -> None:
        xs = [118, 137, 156, 176, 196, 215, 235]
        heights = [210, 196, 220, 205, 216, 198, 212]
        for x, h in zip(xs, heights):
            draw.rounded_rectangle((x-7, 112, x+7, h), radius=6, fill=fill, outline=outline, width=3)
            draw.ellipse((x-16, 82, x+16, 116), fill=(248, 241, 221, 255), outline=outline, width=3)
        draw.rounded_rectangle((100, 198, 255, 273), radius=42, fill=(246, 238, 211, 245), outline=outline, width=5)

    def _draw_rice_character(self, draw: ImageDraw.ImageDraw, fill, outline) -> None:
        draw.ellipse((110, 78, 250, 245), fill=fill, outline=outline, width=5)
        draw.ellipse((130, 218, 230, 300), fill=fill, outline=outline, width=5)

    def _draw_grain_character(self, draw: ImageDraw.ImageDraw, fill, outline) -> None:
        draw.ellipse((105, 82, 255, 230), fill=fill, outline=outline, width=5)
        for x, y in [(128, 68), (180, 58), (232, 70)]:
            draw.line((180, 94, x, y), fill=outline, width=5)
            draw.ellipse((x-10, y-16, x+10, y+16), fill=(226, 185, 98,255), outline=outline, width=3)
        draw.ellipse((120, 205, 240, 300), fill=fill, outline=outline, width=5)

    def _draw_generic_character(self, draw: ImageDraw.ImageDraw, fill, outline, shape_hint: str) -> None:
        if "길쭉" in shape_hint:
            draw.rounded_rectangle((125, 62, 235, 250), radius=50, fill=fill, outline=outline, width=5)
        elif "네모" in shape_hint:
            draw.rounded_rectangle((105, 90, 255, 238), radius=28, fill=fill, outline=outline, width=5)
        else:
            draw.ellipse((100, 80, 260, 240), fill=fill, outline=outline, width=5)
        draw.ellipse((118, 214, 242, 302), fill=fill, outline=outline, width=5)

    def _draw_face_and_action(self, draw: ImageDraw.ImageDraw, spec: TextPromptSpec) -> None:
        ink = (40, 35, 30, 255)
        # Face
        if "다정" in spec.personality or "예의" in spec.tone:
            draw.arc((135, 132, 163, 154), 0, 180, fill=ink, width=4)
            draw.arc((198, 132, 226, 154), 0, 180, fill=ink, width=4)
            draw.arc((158, 163, 204, 194), 0, 180, fill=ink, width=4)
        else:
            draw.ellipse((142, 135, 155, 148), fill=ink)
            draw.ellipse((205, 135, 218, 148), fill=ink)
            draw.arc((160, 164, 202, 194), 0, 180, fill=ink, width=4)
        # Action
        if spec.action == "인사":
            draw.line((248, 210, 288, 178), fill=ink, width=7)
            draw.line((285, 178, 300, 164), fill=ink, width=5)
            draw.arc((290, 136, 328, 178), 200, 320, fill=(90,90,90,255), width=3)
        elif spec.action == "따봉":
            draw.rounded_rectangle((246, 176, 306, 244), radius=20, fill=(246,237,211,255), outline=ink, width=5)
            draw.text((262, 152), "👍", font=load_korean_font(24), fill=ink)
        elif spec.action == "꾸벅":
            draw.text((136, 52), "꾸벅", fill=ink, font=load_korean_font(22))
        elif spec.action == "울기":
            draw.ellipse((218, 152, 234, 178), fill=(90,170,240,220), outline=(40,120,200,255), width=2)
        elif spec.action == "확인":
            draw.line((250, 124, 264, 142, 296, 102), fill=(50,150,80,255), width=7)

    def _draw_text_label(self, draw: ImageDraw.ImageDraw, phrase: str) -> None:
        phrase = str(phrase or "안녕하세요")[:14]
        font_size = 24 if len(phrase) <= 7 else 19
        font = load_korean_font(font_size)
        bubble = (52, 304, 308, 350)
        draw.rounded_rectangle(bubble, radius=18, fill=(255,255,255,235), outline=(55,55,55,255), width=3)
        draw.text((74, 316), phrase, fill=(35,35,35,255), font=font)

    def render_preview_gif(self, spec: TextPromptSpec, out_path: Path) -> Path:
        frames: List[Image.Image] = []
        for i in range(6):
            tmp = out_path.parent / f"__text_prompt_frame_{i}.png"
            self.render_preview_png(spec, tmp)
            frame = Image.open(tmp).convert("RGBA")
            if i in [1, 3]:
                frame = frame.transform(frame.size, Image.AFFINE, (1,0,0,0,1,-5), resample=Image.BICUBIC)
            elif i in [2, 4]:
                frame = frame.transform(frame.size, Image.AFFINE, (1,0,0,0,1,4), resample=Image.BICUBIC)
            if i >= 3:
                overlay = Image.new("RGBA", frame.size, (255,255,255,0))
                od = ImageDraw.Draw(overlay)
                od.text((72, 287), "•", fill=(255,190,70,255), font=load_korean_font(32))
                frame.alpha_composite(overlay)
            frames.append(frame)
            try:
                tmp.unlink()
            except Exception:
                pass
        out_path.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=115, loop=0, disposal=2)
        return out_path

    def write_outputs(self, report: TextPromptReport, expressions: List[Dict[str, Any]]) -> None:
        spec = report.spec
        html_rows = "".join(
            f"<tr><td>{e['index']}</td><td>{html.escape(str(e['phrase']))}</td><td>{html.escape(str(e['category']))}</td><td>{html.escape(str(e['face_direction']))}</td><td>{html.escape(str(e['motion_direction']))}</td><td>{html.escape(str(e['text_motion']))}</td></tr>"
            for e in expressions
        )
        warnings_html = "".join(f"<li>{html.escape(w)}</li>" for w in report.warnings) or "<li>고위험 문구 없음. 단, 제출 전 저작권/상표/AI 정책 검사는 별도 확인 필요.</li>"
        html_doc = f"""<!doctype html><html><head><meta charset='utf-8'><title>v27 텍스트 설명 기반 이모티콘 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;}}table{{border-collapse:collapse;width:100%;}}td,th{{border:1px solid #ddd;padding:8px;vertical-align:top;}}th{{background:#f6f6f6;}}.box{{background:#f8fbff;border:1px solid #b8d7ff;padding:12px;border-radius:10px;}}.warn{{background:#fff7e6;border:1px solid #f0c36d;padding:12px;border-radius:10px;}}</style></head><body>
<h1>v27 텍스트 설명 기반 이모티콘 초안 리포트</h1>
<div class='box'><p><b>콘셉트명:</b> {html.escape(str(spec.get('concept_name','')))}</p><p><b>요약:</b> {html.escape(str(spec.get('concept_summary','')))}</p><p><b>원문:</b> {html.escape(str(spec.get('raw_prompt','')))}</p></div>
<h2>파싱 결과</h2><table><tr><th>항목</th><th>값</th></tr>{''.join(f'<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>' for k,v in spec.get('parsed_fields',{}).items())}</table>
<h2>안전 메모</h2><div class='warn'><ul>{warnings_html}</ul></div>
<h2>표현 계획</h2><table><tr><th>#</th><th>문구</th><th>분류</th><th>표정 방향</th><th>행동/모션 방향</th><th>문구 움직임</th></tr>{html_rows}</table>
</body></html>"""
        Path(report.html_path).write_text(html_doc, encoding="utf-8")
        Path(report.json_path).write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        with Path(report.csv_path).open("w", newline="", encoding="utf-8-sig") as f:
            fieldnames = ["index", "phrase", "category", "motion_family", "face_direction", "motion_direction", "text_motion", "note"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in expressions:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

    def build_project(
        self,
        output_dir: Path,
        prompt: str,
        project_name: str = "text_prompt_emoticon",
        format_key: str = "animated_text",
        expression_count: int = 32,
    ) -> TextPromptReport:
        safe = self._safe_name(project_name)
        root = Path(output_dir) / f"{safe}_{int(time.time())}"
        root.mkdir(parents=True, exist_ok=True)
        previews = root / "previews"
        previews.mkdir(exist_ok=True)
        spec = self.parse_prompt(prompt, format_key=format_key)
        expressions = self.build_expression_plan(spec, count=expression_count)
        png_path = previews / "text_prompt_preview_360.png"
        gif_path = previews / "text_prompt_preview_motion.gif"
        self.render_preview_png(spec, png_path)
        self.render_preview_gif(spec, gif_path)
        html_path = root / "text_prompt_emoticon_report.html"
        json_path = root / "text_prompt_emoticon_report.json"
        csv_path = root / "text_prompt_expression_plan.csv"
        zip_path = root / f"{safe}_v27_text_prompt_pack.zip"
        report = TextPromptReport(
            project_name=project_name,
            output_dir=str(root),
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
            spec=spec.to_dict(),
            expression_count=len(expressions),
            preview_png_path=str(png_path),
            preview_gif_path=str(gif_path),
            expression_sheet_path=str(csv_path),
            checksum_sha256="",
            warnings=spec.safety_notes,
        )
        self.write_outputs(report, expressions)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in [html_path, json_path, csv_path, png_path, gif_path]:
                zf.write(fp, Path(fp).relative_to(root))
        report.checksum_sha256 = self._checksum(zip_path)
        self.write_outputs(report, expressions)
        return report
