from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import math
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat
from modules.policy_compliance.direct_creation_gate import DirectCreationGate

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class MaterialSpec:
    name: str
    color: str = "아이보리"
    personality: str = "온순함"
    tone: str = "부드러운 말투"
    base_shape: str = "둥근형"
    role: str = "대화 보조"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceFileSummary:
    label: str
    original_filename: str
    saved_path: str
    source_type: str
    width: Optional[int]
    height: Optional[int]
    dominant_color: str
    shape_hint: str
    use_policy: str
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MultiMaterialReport:
    project_name: str
    material_specs: List[Dict[str, Any]]
    source_files: List[SourceFileSummary]
    generated_assets: List[Dict[str, Any]]
    expression_table: List[Dict[str, Any]]
    motion_scene_table: List[Dict[str, Any]]
    originality_notes: List[str]
    direct_creation_gate: Dict[str, Any]
    human_origin_timeline: List[Dict[str, Any]]
    html_path: str
    json_path: str
    zip_path: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["source_files"] = [x.to_dict() if hasattr(x, "to_dict") else x for x in self.source_files]
        return d


class MultiMaterialCharacterCreator:
    """1~5개 소재 + 도형/스케치/첨부파일 기반 초보자용 캐릭터 제작 보조 엔진.

    주의: 첨부 이미지를 그대로 복제하거나 합성하지 않습니다.
    색감, 비율, 형태 힌트, 사용자가 직접 입력한 성격/말투만 기록하고,
    새 도형 캐릭터 시안과 표현 후보를 만듭니다.
    """

    def __init__(self) -> None:
        self.canvas_size = 360

    def _font(self, size: int):
        return load_korean_font(size)

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _parse_color(self, value: str, fallback: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        value = (value or "").strip()
        named = {
            "연갈색": (202, 154, 92, 255), "갈색": (150, 100, 55, 255),
            "아이보리": (244, 235, 205, 255), "흰색": (255, 250, 240, 255),
            "노랑": (245, 210, 80, 255), "연노랑": (250, 230, 130, 255),
            "초록": (120, 180, 90, 255), "회색": (160, 160, 160, 255),
            "분홍": (240, 160, 180, 255), "보라": (170, 140, 210, 255),
            "주황": (236, 145, 70, 255), "빨강": (220, 85, 85, 255),
            "파랑": (95, 150, 220, 255), "검정": (45, 45, 45, 255),
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

    def _rgb_hex(self, rgb: Tuple[int, int, int]) -> str:
        return "#%02X%02X%02X" % rgb

    def _shape_hint_from_size(self, w: int, h: int) -> str:
        ratio = w / max(1, h)
        if ratio > 1.25:
            return "가로로 넓은 형태 힌트"
        if ratio < 0.8:
            return "세로로 긴 형태 힌트"
        return "정방형/둥근 형태 힌트"

    def analyze_and_store_source_files(self, files: List[Any], out_dir: Path) -> List[SourceFileSummary]:
        out_dir.mkdir(parents=True, exist_ok=True)
        summaries: List[SourceFileSummary] = []
        for idx, f in enumerate(files[:5], start=1):
            name = getattr(f, "name", f"source_{idx}")
            suffix = Path(name).suffix.lower() or ".bin"
            saved = out_dir / f"source_{idx:02d}{suffix}"
            data = f.getvalue() if hasattr(f, "getvalue") else Path(f).read_bytes()
            saved.write_bytes(data)
            width = height = None
            dominant = "분석 불가"
            shape_hint = "파일형 힌트"
            source_type = "첨부파일"
            if suffix in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                try:
                    img = Image.open(saved).convert("RGBA")
                    width, height = img.size
                    thumb = img.copy()
                    thumb.thumbnail((80, 80))
                    # ignore near-transparent pixels
                    pixels = [p[:3] for p in thumb.getdata() if len(p) < 4 or p[3] > 30]
                    if pixels:
                        avg = tuple(int(sum(c[i] for c in pixels) / len(pixels)) for i in range(3))
                        dominant = self._rgb_hex(avg)
                    shape_hint = self._shape_hint_from_size(width, height)
                    source_type = "이미지/스케치 사진"
                    # save a small normalized reference thumbnail for evidence only
                    ref = ImageOps.contain(img, (260, 260))
                    canvas = Image.new("RGBA", (360, 360), (255, 255, 255, 0))
                    canvas.alpha_composite(ref, ((360 - ref.width)//2, (360 - ref.height)//2))
                    canvas.save(out_dir / f"source_{idx:02d}_reference_thumbnail.png")
                except Exception:
                    pass
            summaries.append(SourceFileSummary(
                label=f"첨부자료 {idx}",
                original_filename=name,
                saved_path=str(saved),
                source_type=source_type,
                width=width,
                height=height,
                dominant_color=dominant,
                shape_hint=shape_hint,
                use_policy="직접 합성/복제 금지. 색감·비율·형태 힌트와 창작 증거로만 사용.",
                checksum_sha256=self._checksum(saved),
            ))
        return summaries

    def _draw_material(self, draw: ImageDraw.ImageDraw, x: int, y: int, spec: MaterialSpec, idx: int, total: int, scale: float = 1.0) -> None:
        fill = self._parse_color(spec.color, [(202,154,92,255),(244,235,205,255),(224,164,95,255),(160,160,160,255),(120,180,90,255)][idx % 5])
        outline = (45, 38, 32, 255)
        w = int(64 * scale); h = int(76 * scale)
        shape = spec.base_shape
        if shape == "길쭉형":
            box = (x-w//2, y-h, x+w//2, y+h)
            draw.rounded_rectangle(box, radius=int(28*scale), fill=fill, outline=outline, width=max(2, int(4*scale)))
        elif shape == "납작형":
            box = (x-int(70*scale), y-int(38*scale), x+int(70*scale), y+int(38*scale))
            draw.ellipse(box, fill=fill, outline=outline, width=max(2, int(4*scale)))
        elif shape == "네모형":
            box = (x-w, y-h//2, x+w, y+h//2)
            draw.rounded_rectangle(box, radius=int(18*scale), fill=fill, outline=outline, width=max(2, int(4*scale)))
        elif shape == "알갱이형":
            box = (x-int(42*scale), y-int(60*scale), x+int(42*scale), y+int(60*scale))
            draw.rounded_rectangle(box, radius=int(42*scale), fill=fill, outline=outline, width=max(2, int(4*scale)))
        else:
            box = (x-w, y-h, x+w, y+h)
            draw.ellipse(box, fill=fill, outline=outline, width=max(2, int(4*scale)))
        # identity marker by material type/name
        if any(k in spec.name for k in ["보리", "밀", "쌀"]):
            for a in [-35, 0, 35]:
                rad = math.radians(a)
                draw.line((x, y-int(70*scale), x+int(math.sin(rad)*28*scale), y-int(102*scale)), fill=outline, width=max(2, int(3*scale)))
        if any(k in spec.name for k in ["감자", "고구마", "무", "당근"]):
            draw.arc((x-int(30*scale), y-int(76*scale), x+int(30*scale), y-int(42*scale)), 200, 340, fill=(80, 150, 80, 255), width=max(2, int(3*scale)))
        # personality based eyes/mouth
        angry = any(k in spec.personality + spec.tone for k in ["까칠", "투덜", "화", "시크"])
        gentle = any(k in spec.personality + spec.tone for k in ["온순", "부드", "다정", "위로"])
        tired = any(k in spec.personality + spec.tone for k in ["피곤", "무기력", "귀찮"])
        if angry:
            draw.line((x-int(26*scale), y-int(18*scale), x-int(8*scale), y-int(9*scale)), fill=outline, width=max(2, int(4*scale)))
            draw.line((x+int(8*scale), y-int(9*scale), x+int(26*scale), y-int(18*scale)), fill=outline, width=max(2, int(4*scale)))
        draw.ellipse((x-int(25*scale), y-int(4*scale), x-int(13*scale), y+int(8*scale)), fill=outline)
        draw.ellipse((x+int(13*scale), y-int(4*scale), x+int(25*scale), y+int(8*scale)), fill=outline)
        if gentle:
            draw.arc((x-int(20*scale), y+int(12*scale), x+int(20*scale), y+int(36*scale)), 0, 180, fill=outline, width=max(2, int(3*scale)))
        elif tired:
            draw.line((x-int(18*scale), y+int(26*scale), x+int(18*scale), y+int(24*scale)), fill=outline, width=max(2, int(3*scale)))
        elif angry:
            draw.line((x-int(18*scale), y+int(26*scale), x+int(15*scale), y+int(20*scale)), fill=outline, width=max(2, int(3*scale)))
        else:
            draw.arc((x-int(18*scale), y+int(12*scale), x+int(18*scale), y+int(34*scale)), 0, 180, fill=outline, width=max(2, int(3*scale)))
        # arms
        draw.line((x-int(50*scale), y+int(26*scale), x-int(74*scale), y+int(42*scale)), fill=outline, width=max(2, int(4*scale)))
        draw.line((x+int(50*scale), y+int(26*scale), x+int(74*scale), y+int(18*scale)), fill=outline, width=max(2, int(4*scale)))
        # label
        font = self._font(max(13, int(17*scale)))
        draw.text((x, y+int(86*scale)), spec.name[:6], anchor="mm", fill=(35,35,35,255), font=font)

    def render_multi_group(self, specs: List[MaterialSpec], out_dir: Path, project_name: str) -> List[Dict[str, Any]]:
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_project = self._safe_name(project_name)
        assets: List[Dict[str, Any]] = []
        total = max(1, len(specs))
        img = Image.new("RGBA", (360, 360), (255,255,255,0))
        d = ImageDraw.Draw(img)
        if total == 1:
            positions = [(180, 175, 1.15)]
        elif total == 2:
            positions = [(125, 175, .95), (245, 175, .95)]
        elif total == 3:
            positions = [(90, 180, .78), (180, 145, .78), (270, 180, .78)]
        elif total == 4:
            positions = [(95, 140, .70), (265, 140, .70), (95, 245, .70), (265, 245, .70)]
        else:
            positions = [(180, 115, .62), (80, 190, .62), (180, 200, .62), (280, 190, .62), (180, 280, .62)]
        for i, spec in enumerate(specs):
            x,y,s = positions[i]
            self._draw_material(d, x, y, spec, i, total, s)
        font = self._font(20)
        d.rounded_rectangle((20, 18, 340, 56), radius=16, fill=(255,255,255,220), outline=(90,90,90,255), width=2)
        title = " + ".join([s.name for s in specs])[:22]
        d.text((180, 37), title, anchor="mm", fill=(35,35,35,255), font=font)
        fp = out_dir / f"{safe_project}_group.png"
        fp.parent.mkdir(parents=True, exist_ok=True)
        img.save(fp)
        assets.append({"label":"멀티 소재 기본형", "file_path":str(fp), "asset_type":"prototype", "description":f"{total}개 소재를 구분 배치한 360×360 기본 시안", "checksum_sha256":self._checksum(fp)})
        # single candidates
        for i, spec in enumerate(specs, start=1):
            one = Image.new("RGBA", (360, 360), (255,255,255,0))
            od = ImageDraw.Draw(one)
            self._draw_material(od, 180, 175, spec, i-1, total, 1.1)
            ofp = out_dir / f"material_{i:02d}_{self._safe_name(spec.name)}.png"
            ofp.parent.mkdir(parents=True, exist_ok=True)
            one.save(ofp)
            assets.append({"label":spec.name, "file_path":str(ofp), "asset_type":"material_candidate", "description":"개별 소재 캐릭터 후보", "checksum_sha256":self._checksum(ofp)})
        return assets

    def _safe_name(self, value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in value)[:20] or "material"

    def build_expression_table(self, specs: List[MaterialSpec], count: int = 80) -> List[Dict[str, Any]]:
        situations = [
            ("인사", "안녕"), ("확인", "확인했어요"), ("감사", "고마워요"), ("사과", "미안해요"),
            ("응원", "천천히 해도 괜찮아"), ("피곤", "잠시 쉬어도 돼"), ("분노", "진정해요"),
            ("당황", "어... 괜찮을까요?"), ("축하", "축하해요"), ("부탁", "부탁드려도 될까요?"),
            ("퇴근", "오늘도 수고했어요"), ("잘자", "좋은 꿈 꿔요"), ("거절", "이번엔 어려울 것 같아요"),
            ("기다림", "천천히 와요"), ("민망", "살짝 민망해요"), ("시그니처", "우리 방식대로 가자"),
        ]
        rows: List[Dict[str, Any]] = []
        for i in range(count):
            cat, base = situations[i % len(situations)]
            focus = specs[i % len(specs)]
            # tone conversion: not pretending to be perfect AI, but useful first draft
            if any(k in focus.tone + focus.personality for k in ["까칠", "투덜", "시크"]):
                line = f"{focus.name}: {base.replace('요','다')}... 뭐"
            elif any(k in focus.tone + focus.personality for k in ["부드", "다정", "온순", "위로"]):
                line = f"{focus.name}: {base}"
            elif any(k in focus.tone + focus.personality for k in ["피곤", "무기력", "귀찮"]):
                line = f"{focus.name}: {base}... 잠깐만"
            else:
                line = f"{focus.name}: {base}"
            if len(specs) >= 2 and i % 3 == 0:
                partner = specs[(i+1) % len(specs)]
                line += f" / {partner.name}: 같이 할게요"
            if i >= len(situations):
                line += f" · 변형{i//len(situations)+1}"
            rows.append({
                "no": i+1,
                "category": cat,
                "phrase": line,
                "character_focus": focus.name,
                "format_recommendation": ["문구형 정지", "움직이는 문구형", "정지형", "큰 이모티콘"][i % 4],
                "motion_hint": self._motion_hint(cat, focus, len(specs)),
                "originality_note": "소재별 색·형태·성격·말투 차이를 분리해 독창성 확보",
            })
        return rows

    def _motion_hint(self, cat: str, focus: MaterialSpec, total: int) -> str:
        base = {
            "확인": "문구가 도장처럼 찍히고 캐릭터가 끄덕임",
            "감사": "중심 캐릭터가 작게 숙이고 주변 캐릭터가 반짝임",
            "사과": "몸이 작아지고 문구가 살짝 떨림",
            "피곤": "캐릭터와 문구가 아래로 천천히 처짐",
            "분노": "외곽선이 부들부들 흔들림",
            "퇴근": "캐릭터가 화면 밖으로 이동하고 문구가 따라감",
        }.get(cat, "문구와 캐릭터가 같은 방향으로 부드럽게 움직임")
        if total >= 3:
            return f"{focus.name} 중심 → 나머지 소재가 순차 반응 · {base}"
        return f"{focus.name} 중심 · {base}"

    def render_expression_previews(self, specs: List[MaterialSpec], expressions: List[Dict[str, Any]], out_dir: Path, project_name: str, count: int = 12) -> List[Dict[str, Any]]:
        out_dir.mkdir(parents=True, exist_ok=True)
        assets: List[Dict[str, Any]] = []
        font = self._font(21)
        small = self._font(17)
        for idx, row in enumerate(expressions[:count], start=1):
            img = Image.new("RGBA", (360, 360), (255,255,255,0))
            d = ImageDraw.Draw(img)
            # draw first up to 5 smaller materials
            n = len(specs)
            if n == 1:
                positions = [(180, 145, .95)]
            elif n == 2:
                positions = [(120, 145, .75), (240, 145, .75)]
            elif n == 3:
                positions = [(90, 150, .62), (180, 120, .62), (270, 150, .62)]
            elif n == 4:
                positions = [(95, 112, .55), (265, 112, .55), (95, 192, .55), (265, 192, .55)]
            else:
                positions = [(180, 95, .48), (85, 150, .48), (180, 170, .48), (275, 150, .48), (180, 225, .48)]
            for i, spec in enumerate(specs[:5]):
                x,y,s=positions[i]
                self._draw_material(d, x, y, spec, i, n, s)
            d.rounded_rectangle((22, 257, 338, 342), radius=18, fill=(255,255,255,238), outline=(50,50,50,255), width=2)
            phrase = row["phrase"]
            parts = phrase.split(" / ")
            if len(parts) > 1:
                d.text((180, 284), parts[0][:22], anchor="mm", fill=(25,25,25,255), font=small)
                d.text((180, 316), parts[1][:22], anchor="mm", fill=(25,25,25,255), font=small)
            else:
                d.text((180, 300), phrase[:26], anchor="mm", fill=(25,25,25,255), font=font if len(phrase) <= 16 else small)
            fp = out_dir / f"expr_{idx:02d}.png"
            fp.parent.mkdir(parents=True, exist_ok=True)
            img.save(fp)
            assets.append({"label":f"표현 {idx:02d}", "file_path":str(fp), "asset_type":"expression_preview", "description":row["category"], "checksum_sha256":self._checksum(fp)})
        return assets

    def build_motion_scenes(self, specs: List[MaterialSpec]) -> List[Dict[str, Any]]:
        names = [s.name for s in specs]
        lead = names[0] if names else "캐릭터"
        second = names[1] if len(names) > 1 else "문구"
        group = ", ".join(names[:5])
        return [
            {"scene":"확인", "frames":f"{lead}가 먼저 등장 → {second}가 끄덕임 → 문구가 도장처럼 찍힘", "sync_point":"문구는 첫 캐릭터 동작 후 0.2~0.4초 뒤", "format":"움직이는 문구형"},
            {"scene":"감사", "frames":f"부드러운 소재가 앞으로 이동 → 까칠한 소재가 작게 반응 → 하트/반짝임", "sync_point":"하트와 감사 문구를 같은 프레임에 배치", "format":"움직이는 문구형"},
            {"scene":"사과", "frames":f"전체가 작아짐 → 중심 캐릭터가 꾸벅 → 문구가 작게 떨림", "sync_point":"모든 소재가 숙인 뒤 문구 표시", "format":"움직이는 문구형"},
            {"scene":"단체 리액션", "frames":f"{group} 순서대로 튀어나옴 → 마지막에 전체 말풍선", "sync_point":"소재 등장 순서와 말풍선 글자 등장 순서를 맞춤", "format":"큰 이모티콘/움직이는 문구형"},
            {"scene":"시그니처", "frames":"각 소재의 성격이 1프레임씩 드러난 뒤 하나의 문구로 합쳐짐", "sync_point":"마지막 2프레임은 캐릭터와 문구 모두 정지해 가독성 확보", "format":"시리즈형 확장"},
        ]

    def _timeline(self, project_name: str, source_count: int) -> List[Dict[str, Any]]:
        now = int(time.time())
        return [
            {"step":1, "time_marker":now, "action":"사용자 직접 소재/색/성격/말투 입력", "evidence":"material_specs.json"},
            {"step":2, "time_marker":now+1, "action":f"사용자 첨부자료 {source_count}개 저장 및 체크섬 기록", "evidence":"source_files/"},
            {"step":3, "time_marker":now+2, "action":"첨부 이미지는 복제하지 않고 색감·형태 힌트만 기록", "evidence":"source_file_summary.json"},
            {"step":4, "time_marker":now+3, "action":"도형 기반 멀티 소재 캐릭터 시안 생성", "evidence":"assets/"},
            {"step":5, "time_marker":now+4, "action":"표현 후보/움직이는 문구 장면 확장", "evidence":"expression_table.json, motion_scene_table.json"},
            {"step":6, "time_marker":now+5, "action":"창작 증거 리포트/체크섬 기록", "evidence":"multi_material_creator_report.html/json"},
        ]

    def build_project(
        self,
        specs: List[MaterialSpec],
        uploaded_files: List[Any],
        output_dir: Path,
        project_name: str,
        expression_count: int = 80,
        preview_count: int = 12,
        creator_note: str = "",
        has_layer_or_revision_plan: bool = False,
        rights_confirmed: bool = False,
        uses_ai_completed_image: bool = False,
    ) -> MultiMaterialReport:
        specs = specs[:5]
        if not specs:
            raise ValueError("최소 1개 소재가 필요합니다.")
        safe_project = self._safe_name(project_name)
        root = output_dir / safe_project
        root.mkdir(parents=True, exist_ok=True)
        (root / "material_specs.json").write_text(json.dumps([s.to_dict() for s in specs], ensure_ascii=False, indent=2), encoding="utf-8")
        sources = self.analyze_and_store_source_files(uploaded_files or [], root / "source_files")
        (root / "source_file_summary.json").write_text(json.dumps([s.to_dict() for s in sources], ensure_ascii=False, indent=2), encoding="utf-8")
        assets = self.render_multi_group(specs, root / "assets", safe_project)
        expressions = self.build_expression_table(specs, expression_count)
        assets.extend(self.render_expression_previews(specs, expressions, root / "expression_previews", safe_project, preview_count))
        motion = self.build_motion_scenes(specs)
        timeline = self._timeline(project_name, len(sources))
        notes = [
            "1~5개 소재를 모두 같은 얼굴로 복제하지 않고 색·형태·성격·말투·역할로 분리합니다.",
            "사진/스케치/파일 첨부자료는 직접 합성하지 않고 창작 힌트와 증거 기록으로만 사용합니다.",
            "보리와 쌀처럼 익숙한 소재도 관계성, 말투 대비, 움직임 동기화로 독창성을 확보합니다.",
            "직접 창작 게이트가 통과되지 않으면 결과물은 제출 후보가 아니라 보완용 초안입니다.",
        ]
        gate = DirectCreationGate().evaluate(
            has_user_shape_input=bool(specs),
            has_sketch_or_reference=bool(sources),
            has_creator_note=bool(creator_note.strip()),
            has_layer_or_revision_plan=has_layer_or_revision_plan,
            has_rights_confirmation=rights_confirmed,
            uses_ai_completed_image=uses_ai_completed_image,
        ).to_dict()
        (root / "expression_table.json").write_text(json.dumps(expressions, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "motion_scene_table.json").write_text(json.dumps(motion, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "human_origin_timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
        report = MultiMaterialReport(project_name, [s.to_dict() for s in specs], sources, assets, expressions, motion, notes, gate, timeline, "", "", "")
        json_path = root / "multi_material_creator_report.json"
        html_path = root / "multi_material_creator_report.html"
        zip_path = output_dir / f"{safe_project}_multi_material_creator_pack.zip"
        report.json_path = str(json_path); report.html_path = str(html_path); report.zip_path = str(zip_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(self._html(report), encoding="utf-8")
        self._zip_dir(root, zip_path)
        return report

    def _zip_dir(self, src: Path, zip_path: Path) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in src.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(src.parent))

    def _html(self, report: MultiMaterialReport) -> str:
        def table(items: List[Dict[str, Any]], keys: List[str]) -> str:
            return "\n".join("<tr>" + "".join(f"<td>{str(it.get(k,''))}</td>" for k in keys) + "</tr>" for it in items)
        assets = table(report.generated_assets, ["label","asset_type","description","file_path","checksum_sha256"])
        sources = table([s.to_dict() for s in report.source_files], ["label","original_filename","source_type","width","height","dominant_color","shape_hint","checksum_sha256","use_policy"])
        exprs = table(report.expression_table[:35], ["no","category","phrase","character_focus","format_recommendation","motion_hint"])
        motion = table(report.motion_scene_table, ["scene","frames","sync_point","format"])
        notes = "".join(f"<li>{x}</li>" for x in report.originality_notes)
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>{report.project_name} multi material creator</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55}}table{{border-collapse:collapse;width:100%;margin:14px 0}}th,td{{border:1px solid #ddd;padding:8px;font-size:13px;vertical-align:top}}th{{background:#f5f5f5}}.box{{background:#eef8ff;border:1px solid #b7d7ef;padding:14px;border-radius:10px}}</style></head><body>
<h1>v18 멀티 소재 직접 캐릭터 만들기 리포트</h1>
<div class='box'><b>프로젝트:</b> {report.project_name}<br><b>목적:</b> 도형·사진/스케치·첨부파일·최대 5개 소재 입력을 바탕으로 독창 캐릭터 시안과 표현 후보를 생성합니다. 첨부 이미지를 그대로 복제/합성하지 않습니다.</div>
<h2>소재 입력</h2><pre>{json.dumps(report.material_specs, ensure_ascii=False, indent=2)}</pre>
<h2>독창성 메모</h2><ul>{notes}</ul>
<h2>직접 창작 게이트</h2><pre>{json.dumps(report.direct_creation_gate, ensure_ascii=False, indent=2)}</pre>
<h2>첨부자료 분석/증거</h2><table><tr><th>라벨</th><th>원본 파일명</th><th>유형</th><th>가로</th><th>세로</th><th>대표색</th><th>형태 힌트</th><th>SHA-256</th><th>사용 정책</th></tr>{sources}</table>
<h2>생성 자산</h2><table><tr><th>라벨</th><th>유형</th><th>설명</th><th>파일</th><th>SHA-256</th></tr>{assets}</table>
<h2>표현 후보 일부</h2><table><tr><th>번호</th><th>분류</th><th>문구</th><th>초점</th><th>추천 포맷</th><th>움직임 힌트</th></tr>{exprs}</table>
<h2>움직이는 문구 장면</h2><table><tr><th>장면</th><th>프레임 흐름</th><th>동기화 포인트</th><th>포맷</th></tr>{motion}</table>
<h2>창작 타임라인</h2><pre>{json.dumps(report.human_origin_timeline, ensure_ascii=False, indent=2)}</pre>
</body></html>"""
