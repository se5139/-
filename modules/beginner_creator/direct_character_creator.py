
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
import json
import math
import time
import hashlib

from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class DuoCharacterInput:
    material_a: str
    material_b: str
    personality_a: str
    personality_b: str
    tone_a: str
    tone_b: str
    color_a: str
    color_b: str
    base_shape: str = "둥근형"
    relationship: str = "투덜이와 다정이 콤비"
    target: str = "직장인/일상 답장"
    creator_note: str = "사용자가 직접 설정한 기본 도형/색/성격/말투를 기반으로 확장"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedCharacterAsset:
    label: str
    file_path: str
    asset_type: str
    description: str
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeginnerCreationReport:
    project_name: str
    input_summary: Dict[str, Any]
    generated_assets: List[GeneratedCharacterAsset]
    expression_table: List[Dict[str, Any]]
    motion_scene_table: List[Dict[str, Any]]
    originality_notes: List[str]
    human_origin_timeline: List[Dict[str, Any]]
    html_path: str
    json_path: str
    zip_path: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["generated_assets"] = [x.to_dict() if hasattr(x, "to_dict") else x for x in self.generated_assets]
        return d


class BeginnerCharacterCreator:
    """초보자용 직접 창작 보조 엔진.

    이 모듈은 AI 완성본을 숨기거나 대체하는 기능이 아니라,
    사용자가 직접 정한 도형·색·성격·말투를 바탕으로 단순 시안을 만들고
    표현/움직임/창작 타임라인을 자동 정리하는 로컬 제작 보조 기능입니다.
    """

    def __init__(self) -> None:
        self.canvas_size = 360

    def _font(self, size: int):
        return load_korean_font(size)

    def _parse_color(self, value: str, fallback: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        value = (value or "").strip()
        named = {
            "연갈색": (202, 154, 92, 255),
            "갈색": (150, 100, 55, 255),
            "아이보리": (244, 235, 205, 255),
            "흰색": (255, 250, 240, 255),
            "노랑": (245, 210, 80, 255),
            "연노랑": (250, 230, 130, 255),
            "초록": (120, 180, 90, 255),
            "회색": (160, 160, 160, 255),
            "분홍": (240, 160, 180, 255),
            "보라": (170, 140, 210, 255),
        }
        if value in named:
            return named[value]
        if value.startswith("#") and len(value) in (7, 9):
            try:
                r = int(value[1:3], 16); g = int(value[3:5], 16); b = int(value[5:7], 16)
                a = int(value[7:9], 16) if len(value) == 9 else 255
                return (r, g, b, a)
            except Exception:
                return fallback
        return fallback

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest()

    def _draw_barley(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, fill, mood: str = "normal") -> None:
        outline = (45, 35, 25, 255)
        # body/face: slightly sharp oval
        draw.ellipse((cx-58, cy-72, cx+58, cy+70), fill=fill, outline=outline, width=4)
        # barley awns
        for angle in [-55, -30, 0, 30, 55]:
            rad = math.radians(angle)
            x1 = cx + int(math.sin(rad) * 18)
            y1 = cy - 68
            x2 = cx + int(math.sin(rad) * 42)
            y2 = cy - 112 + int(abs(angle) * 0.15)
            draw.line((x1, y1, x2, y2), fill=outline, width=3)
        # eyebrows and eyes
        if mood in ("angry", "grumble", "sorry"):
            draw.line((cx-34, cy-22, cx-12, cy-12), fill=outline, width=4)
            draw.line((cx+12, cy-12, cx+34, cy-22), fill=outline, width=4)
            draw.ellipse((cx-28, cy-4, cx-15, cy+9), fill=outline)
            draw.ellipse((cx+15, cy-4, cx+28, cy+9), fill=outline)
        else:
            draw.ellipse((cx-28, cy-6, cx-14, cy+8), fill=outline)
            draw.ellipse((cx+14, cy-6, cx+28, cy+8), fill=outline)
        # mouth
        if mood == "smile":
            draw.arc((cx-24, cy+12, cx+24, cy+40), 0, 180, fill=outline, width=3)
        elif mood == "sorry":
            draw.arc((cx-22, cy+24, cx+22, cy+52), 180, 360, fill=outline, width=3)
        elif mood == "tired":
            draw.line((cx-22, cy+30, cx+22, cy+26), fill=outline, width=3)
        else:
            draw.line((cx-20, cy+28, cx+18, cy+24), fill=outline, width=3)
        # arms
        draw.line((cx-54, cy+32, cx-84, cy+52), fill=outline, width=5)
        draw.line((cx+54, cy+32, cx+86, cy+22), fill=outline, width=5)

    def _draw_rice(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, fill, mood: str = "normal") -> None:
        outline = (55, 45, 35, 255)
        # rounded rice grain
        draw.rounded_rectangle((cx-50, cy-72, cx+50, cy+72), radius=48, fill=fill, outline=outline, width=4)
        # gentle shine
        draw.arc((cx-26, cy-54, cx+16, cy-10), 190, 260, fill=(255,255,255,160), width=3)
        # eyes
        if mood == "cry":
            draw.arc((cx-28, cy-14, cx-12, cy+10), 200, 340, fill=outline, width=3)
            draw.arc((cx+12, cy-14, cx+28, cy+10), 200, 340, fill=outline, width=3)
            draw.ellipse((cx+30, cy+8, cx+40, cy+26), fill=(100, 170, 240, 200))
        else:
            draw.ellipse((cx-26, cy-7, cx-13, cy+7), fill=outline)
            draw.ellipse((cx+13, cy-7, cx+26, cy+7), fill=outline)
        # mouth
        if mood in ("smile", "thanks", "normal"):
            draw.arc((cx-20, cy+12, cx+20, cy+38), 0, 180, fill=outline, width=3)
        elif mood == "surprise":
            draw.ellipse((cx-8, cy+17, cx+8, cy+34), outline=outline, width=3)
        else:
            draw.line((cx-14, cy+28, cx+14, cy+28), fill=outline, width=3)
        # arms
        draw.line((cx-48, cy+36, cx-76, cy+24), fill=outline, width=5)
        draw.line((cx+48, cy+36, cx+78, cy+54), fill=outline, width=5)

    def render_base_duo(self, spec: DuoCharacterInput, out_dir: Path, project_name: str) -> List[GeneratedCharacterAsset]:
        out_dir.mkdir(parents=True, exist_ok=True)
        color_a = self._parse_color(spec.color_a, (198, 150, 86, 255))
        color_b = self._parse_color(spec.color_b, (246, 238, 210, 255))
        assets: List[GeneratedCharacterAsset] = []
        # main duo
        img = Image.new("RGBA", (360, 360), (255,255,255,0))
        draw = ImageDraw.Draw(img)
        self._draw_barley(draw, 125, 190, color_a, mood="grumble")
        self._draw_rice(draw, 245, 190, color_b, mood="smile")
        # relationship tag
        font = self._font(22)
        tag = spec.relationship[:14]
        draw.rounded_rectangle((58, 24, 302, 62), radius=18, fill=(255,255,255,220), outline=(80,80,80,255), width=2)
        draw.text((180, 43), tag, anchor="mm", fill=(40,40,40,255), font=font)
        fp = out_dir / f"{project_name}_duo_base.png"
        img.save(fp)
        assets.append(GeneratedCharacterAsset("듀오 기본형", str(fp), "prototype", "보리/쌀 성격 대비를 반영한 360×360 기본 시안", self._checksum(fp)))
        # separate simple layer-like images
        for label, drawer, cx, color, mood, fname, desc in [
            (spec.material_a, self._draw_barley, 180, color_a, "grumble", "layer_barley_base.png", "보리 단독 기본 레이어 후보"),
            (spec.material_b, self._draw_rice, 180, color_b, "smile", "layer_rice_base.png", "쌀 단독 기본 레이어 후보"),
        ]:
            layer = Image.new("RGBA", (360, 360), (255,255,255,0))
            d = ImageDraw.Draw(layer)
            drawer(d, cx, 190, color, mood=mood)
            lfp = out_dir / fname
            layer.save(lfp)
            assets.append(GeneratedCharacterAsset(label, str(lfp), "layer_candidate", desc, self._checksum(lfp)))
        return assets

    def build_expression_table(self, spec: DuoCharacterInput, count: int = 80) -> List[Dict[str, Any]]:
        base_rows = [
            ("인사", f"{spec.material_a}: 왔냐... / {spec.material_b}: 안녕"),
            ("확인", f"{spec.material_a}: 봤다 / {spec.material_b}: 확인했어요"),
            ("감사", f"{spec.material_a}: 뭐... 고맙다 / {spec.material_b}: 고마워요"),
            ("사과", f"{spec.material_a}: 미안하다 됐냐 / {spec.material_b}: 미안해요"),
            ("응원", f"{spec.material_a}: 해봐, 안 죽어 / {spec.material_b}: 천천히 해도 괜찮아"),
            ("피곤", f"{spec.material_a}: 아 몰라 눕는다 / {spec.material_b}: 쉬어도 돼"),
            ("분노", f"{spec.material_a}: 건드리지 마라 / {spec.material_b}: 우리 진정해요"),
            ("당황", f"{spec.material_a}: 뭐냐 이건 / {spec.material_b}: 어... 괜찮을까요?"),
            ("축하", f"{spec.material_a}: 뭐... 축하한다 / {spec.material_b}: 진심으로 축하해"),
            ("부탁", f"{spec.material_a}: 해주면 안 되냐 / {spec.material_b}: 부탁드려도 될까요?"),
            ("퇴근", f"{spec.material_a}: 나 간다 / {spec.material_b}: 오늘도 수고했어요"),
            ("잘자", f"{spec.material_a}: 자라 / {spec.material_b}: 좋은 꿈 꿔요"),
            ("거절", f"{spec.material_a}: 안 된다 / {spec.material_b}: 이번엔 어려울 것 같아요"),
            ("기다림", f"{spec.material_a}: 기다린다... / {spec.material_b}: 천천히 와요"),
            ("민망", f"{spec.material_a}: 못 본 척해라 / {spec.material_b}: 살짝 민망해요"),
            ("고마움", f"{spec.material_a}: 챙겨주긴 하네 / {spec.material_b}: 마음이 따뜻해요"),
        ]
        format_cycle = ["문구형 정지", "움직이는 문구형", "정지형", "움직이는 문구형"]
        rows = []
        for i in range(count):
            cat, phrase = base_rows[i % len(base_rows)]
            # add small variations without copying external phrases
            if i >= len(base_rows):
                phrase = phrase + f" · {i//len(base_rows)+1}"
            rows.append({
                "no": i + 1,
                "category": cat,
                "phrase": phrase,
                "character_focus": spec.material_a if i % 2 == 0 else spec.material_b,
                "format_recommendation": format_cycle[i % len(format_cycle)],
                "motion_hint": self._motion_for_category(cat, spec),
                "originality_note": "성격 대비·듀오 관계·말투 차이로 차별화",
            })
        return rows

    def _motion_for_category(self, category: str, spec: DuoCharacterInput) -> str:
        mapping = {
            "확인": f"{spec.material_a}가 툭 튀어나오고 {spec.material_b}가 부드럽게 끄덕임",
            "감사": f"{spec.material_b}가 먼저 웃고 {spec.material_a}가 고개를 돌린 채 작게 반응",
            "사과": f"{spec.material_b}가 꾸벅, {spec.material_a}는 늦게 작게 숙임",
            "피곤": "둘 다 아래로 축 처지고 문구가 천천히 내려앉음",
            "분노": f"{spec.material_a} 이삭이 부들부들, {spec.material_b}가 말림",
            "퇴근": f"{spec.material_a}가 먼저 화면 밖으로 가고 {spec.material_b}가 손 흔듦",
        }
        return mapping.get(category, "두 캐릭터가 성격 차이에 맞춰 순차 반응")

    def render_expression_previews(self, spec: DuoCharacterInput, expressions: List[Dict[str, Any]], out_dir: Path, project_name: str, count: int = 12) -> List[GeneratedCharacterAsset]:
        out_dir.mkdir(parents=True, exist_ok=True)
        assets: List[GeneratedCharacterAsset] = []
        color_a = self._parse_color(spec.color_a, (198, 150, 86, 255))
        color_b = self._parse_color(spec.color_b, (246, 238, 210, 255))
        font = self._font(24)
        small = self._font(18)
        for idx, row in enumerate(expressions[:count], start=1):
            img = Image.new("RGBA", (360, 360), (255,255,255,0))
            d = ImageDraw.Draw(img)
            mood_a = "grumble" if row["character_focus"] == spec.material_a else "normal"
            mood_b = "smile" if row["character_focus"] == spec.material_b else "normal"
            self._draw_barley(d, 120, 155, color_a, mood=mood_a)
            self._draw_rice(d, 240, 155, color_b, mood=mood_b)
            # speech bubble
            d.rounded_rectangle((26, 260, 334, 340), radius=18, fill=(255,255,255,235), outline=(50,50,50,255), width=2)
            phrase = row["phrase"]
            if len(phrase) > 28:
                # split around slash if possible
                parts = phrase.split(" / ")
                if len(parts) >= 2:
                    d.text((180, 284), parts[0][:20], anchor="mm", fill=(25,25,25,255), font=small)
                    d.text((180, 316), parts[1][:20], anchor="mm", fill=(25,25,25,255), font=small)
                else:
                    d.text((180, 300), phrase[:24], anchor="mm", fill=(25,25,25,255), font=small)
            else:
                d.text((180, 300), phrase, anchor="mm", fill=(25,25,25,255), font=font)
            fp = out_dir / f"expr_{idx:02d}.png"
            img.save(fp)
            assets.append(GeneratedCharacterAsset(f"표현 {idx:02d}", str(fp), "expression_preview", row["category"], self._checksum(fp)))
        return assets

    def build_motion_scenes(self, spec: DuoCharacterInput) -> List[Dict[str, Any]]:
        return [
            {"scene": "확인했어요", "frames": "보리 툭 등장 → 쌀 끄덕임 → 문구 도장처럼 등장", "sync_point": "문구는 보리 등장 후 0.3초 뒤", "format": "움직이는 문구형"},
            {"scene": "고마워요", "frames": "쌀 하트 미소 → 보리 고개 돌림 → 작은 고맙다", "sync_point": "하트와 문구를 같은 프레임에 배치", "format": "움직이는 문구형"},
            {"scene": "미안해요", "frames": "쌀 꾸벅 → 보리 망설임 → 보리도 작게 숙임", "sync_point": "사과 문구는 두 캐릭터가 모두 숙인 뒤 등장", "format": "움직이는 문구형"},
            {"scene": "퇴근", "frames": "보리 먼저 이탈 → 쌀 손 흔듦 → 문구 아래로 흐름", "sync_point": "캐릭터 이동 방향과 문구 이동 방향을 일치", "format": "움직이는 문구형"},
            {"scene": "파이팅", "frames": "쌀이 먼저 응원 → 보리가 투덜대며 엄지척", "sync_point": "응원 문구는 마지막 포즈와 동시 확대", "format": "문구형 정지/움직이는 문구형"},
        ]

    def build_human_origin_timeline(self, project_name: str, output_dir: Path) -> List[Dict[str, Any]]:
        now = int(time.time())
        return [
            {"step": 1, "time_marker": now, "action": "사용자 직접 소재/성격/말투 입력", "evidence": "input_summary.json"},
            {"step": 2, "time_marker": now + 1, "action": "도형 기반 직접 창작 시안 생성", "evidence": "duo_base.png / layer candidates"},
            {"step": 3, "time_marker": now + 2, "action": "표현 은행과 말투 차이 자동 확장", "evidence": "expression_table.json/csv"},
            {"step": 4, "time_marker": now + 3, "action": "움직이는 문구 장면 설계", "evidence": "motion_scene_table.json"},
            {"step": 5, "time_marker": now + 4, "action": "창작 증거/체크섬 기록", "evidence": "beginner_creator_report.json/html"},
        ]

    def build_project(self, spec: DuoCharacterInput, output_dir: Path, project_name: str, expression_count: int = 80, preview_count: int = 12) -> BeginnerCreationReport:
        root = output_dir / project_name
        root.mkdir(parents=True, exist_ok=True)
        input_path = root / "input_summary.json"
        input_path.write_text(json.dumps(spec.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        assets = self.render_base_duo(spec, root / "assets", project_name)
        expressions = self.build_expression_table(spec, expression_count)
        expression_assets = self.render_expression_previews(spec, expressions, root / "expression_previews", project_name, preview_count)
        assets.extend(expression_assets)
        motion = self.build_motion_scenes(spec)
        timeline = self.build_human_origin_timeline(project_name, root)
        (root / "expression_table.json").write_text(json.dumps(expressions, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "motion_scene_table.json").write_text(json.dumps(motion, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "human_origin_timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
        notes = [
            "보리와 쌀처럼 익숙한 소재라도 성격 대비·말투 차이·듀오 관계성으로 독창성을 확보합니다.",
            "기존 캐릭터의 외형·말투·구도 모방이 아니라 사용자가 정한 기본 도형/색/성격을 기반으로 확장합니다.",
            "완성본 AI 은폐가 아니라 직접 창작 시작점과 수정/확장 기록을 남기는 방식입니다.",
        ]
        report = BeginnerCreationReport(project_name, spec.to_dict(), assets, expressions, motion, notes, timeline, "", "", "")
        json_path = root / "beginner_creator_report.json"
        html_path = root / "beginner_creator_report.html"
        zip_path = output_dir / f"{project_name}_beginner_creator_pack.zip"
        report.json_path = str(json_path)
        report.html_path = str(html_path)
        report.zip_path = str(zip_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(self._html(report), encoding="utf-8")
        self._zip_dir(root, zip_path)
        return report

    def _zip_dir(self, src: Path, zip_path: Path) -> None:
        import zipfile
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in src.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(src.parent))

    def _html(self, report: BeginnerCreationReport) -> str:
        def rows(items: List[Dict[str, Any]], keys: List[str]) -> str:
            out = []
            for it in items:
                out.append("<tr>" + "".join(f"<td>{str(it.get(k,''))}</td>" for k in keys) + "</tr>")
            return "\n".join(out)
        asset_rows = rows([a.to_dict() for a in report.generated_assets], ["label", "asset_type", "description", "file_path", "checksum_sha256"])
        expr_rows = rows(report.expression_table[:30], ["no", "category", "phrase", "character_focus", "format_recommendation", "motion_hint"])
        motion_rows = rows(report.motion_scene_table, ["scene", "frames", "sync_point", "format"])
        notes = "".join(f"<li>{x}</li>" for x in report.originality_notes)
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>{report.project_name} beginner creator report</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55}}table{{border-collapse:collapse;width:100%;margin:14px 0}}th,td{{border:1px solid #ddd;padding:8px;font-size:13px;vertical-align:top}}th{{background:#f5f5f5}}.box{{background:#fff8e8;border:1px solid #edd59a;padding:14px;border-radius:10px}}</style></head><body>
<h1>초보자 직접 캐릭터 만들기 리포트</h1>
<div class='box'><b>프로젝트:</b> {report.project_name}<br><b>목적:</b> 사용자가 직접 정한 도형·색·성격·말투를 기반으로 캐릭터/표현/움직임 방향을 확장합니다. AI 완성본 은폐 기능이 아닙니다.</div>
<h2>입력 요약</h2><pre>{json.dumps(report.input_summary, ensure_ascii=False, indent=2)}</pre>
<h2>독창성 메모</h2><ul>{notes}</ul>
<h2>생성 자산/체크섬</h2><table><tr><th>라벨</th><th>유형</th><th>설명</th><th>파일</th><th>SHA-256</th></tr>{asset_rows}</table>
<h2>표현 후보 일부</h2><table><tr><th>번호</th><th>분류</th><th>문구</th><th>초점</th><th>추천 포맷</th><th>움직임 힌트</th></tr>{expr_rows}</table>
<h2>움직이는 문구 장면</h2><table><tr><th>장면</th><th>프레임 흐름</th><th>동기화 포인트</th><th>포맷</th></tr>{motion_rows}</table>
<h2>창작 과정 타임라인</h2><pre>{json.dumps(report.human_origin_timeline, ensure_ascii=False, indent=2)}</pre>
</body></html>"""
