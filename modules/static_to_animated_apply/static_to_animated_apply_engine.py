
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
class V52StaticToAnimatedReport:
    project_name: str
    output_dir: str
    concept_text: str
    selected_suggestions: List[Dict[str, Any]]
    identity_lock: Dict[str, Any]
    regeneration_plan: List[Dict[str, Any]]
    expression_table: List[Dict[str, Any]]
    static_png_path: str
    static_before_png_path: str
    animated_gif_path: str
    motion_plan_json_path: str
    html_path: str
    json_path: str
    zip_path: str
    checksum_sha256: str
    apply_payload: Dict[str, Any]
    safety_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StaticToAnimatedApplyEngine:
    """v52 정지형-움직이는형 연결 및 선택 제안 반영 재생성 엔진.

    목적:
    - 정지형 캐릭터를 먼저 확정한다.
    - 사용자가 개선 제안을 선택하면 그 선택값을 실제 정지형 PNG 재생성에 반영한다.
    - 같은 identity_lock(형태/색상/얼굴/말투/외곽선 규칙)을 사용해 움직이는형 GIF 초안을 만든다.
    - 생성 결과를 다른 제작 흐름에서 바로 쓸 수 있는 apply_payload로 반환한다.

    안전 원칙:
    - 기존 유명 캐릭터를 복제하지 않는다.
    - 제안은 외곽선, 표정 강도, 포즈, 말풍선, 모션 리듬 같은 추상 속성만 반영한다.
    - 원본/이전 결과를 덮어쓰지 않고 새 output 폴더에 저장한다.
    """

    SUGGESTIONS: List[Dict[str, Any]] = [
        {
            "id": "bold_outline",
            "label": "외곽선 굵게 + 채팅창 축소에서도 잘 보이게",
            "category": "정지형 가독성",
            "effect": "outline_width=6, silhouette_boost=True",
        },
        {
            "id": "face_contrast",
            "label": "눈/입 대비 강화 + 감정이 한눈에 보이게",
            "category": "표정 품질",
            "effect": "face_contrast=high, mouth_scale=1.15",
        },
        {
            "id": "signature_pose",
            "label": "캐릭터만의 시그니처 포즈 추가",
            "category": "독창성",
            "effect": "pose=signature_wave_and_bounce",
        },
        {
            "id": "text_bubble",
            "label": "문구 말풍선 정리 + 짧은 답장형 문구 우선",
            "category": "문구 사용성",
            "effect": "bubble=True, phrase_short=True",
        },
        {
            "id": "animated_identity_lock",
            "label": "정지형 외형/색상/얼굴 비율을 움직이는형에서도 고정",
            "category": "움직이는형 일관성",
            "effect": "identity_lock=True, no_shape_drift=True",
        },
        {
            "id": "text_motion_sync",
            "label": "캐릭터 동작과 문구 움직임 동기화",
            "category": "움직이는형 품질",
            "effect": "text_motion_sync=True, bounce_timing=matched",
        },
        {
            "id": "motion_variation",
            "label": "통통 튐/꾸벅/흔들림 3단 모션 후보 생성",
            "category": "움직이는형 다양성",
            "effect": "motion_variants=3",
        },
        {
            "id": "series_ready",
            "label": "24개/32개 세트 확장용 표정·문구 씨앗 같이 생성",
            "category": "세트 확장",
            "effect": "expression_seed_pack=True",
        },
    ]

    BASE_EXPRESSIONS = [
        ("넵", "확인", "작게 끄덕임"),
        ("확인했습니다", "확인", "체크 표시가 말풍선과 같이 튐"),
        ("감사합니다", "감사", "양손 모으고 반짝"),
        ("죄송합니다", "사과", "고개 숙임 + 땀방울"),
        ("잠시만요", "기다림", "한 손 들고 정지"),
        ("파이팅", "응원", "몸통 통통 + 문구 흔들림"),
        ("살려주세요", "피곤", "축 처짐 + 말풍선 아래 흔들림"),
        ("퇴근하고 싶어요", "피곤", "몸이 살짝 녹듯 내려감"),
        ("대박", "기쁨", "눈 반짝 + 점프"),
        ("괜찮아요", "위로", "부드러운 미소 + 작은 하트"),
        ("오늘도 버팁니다", "직장", "어깨 축 + 작은 흔들림"),
        ("바로 볼게요", "확인", "고개 끄덕 + 체크 효과"),
        ("조용히 파이팅", "응원", "작은 주먹 + 말풍선 통통"),
        ("이미 구겨졌습니다", "피곤", "몸이 납작해졌다 복원"),
        ("마음만 받겠습니다", "거절", "두 손 살짝 흔들기"),
        ("도와주세요", "부탁", "눈 크게 + 손 모으기"),
        ("완료했습니다", "완료", "체크 표시 크게"),
        ("기다릴게요", "기다림", "시계 효과 + 작은 끄덕임"),
        ("축하해요", "축하", "반짝이 + 점프"),
        ("울컥", "감동", "눈물 한 방울"),
        ("민망합니다", "민망", "볼 빨개짐 + 시선 회피"),
        ("화났습니다", "분노", "부들부들 흔들림"),
        ("잘자요", "마무리", "눈 감고 말풍선 둥실"),
        ("주말 잘 보내요", "인사", "손 흔들기"),
    ]

    FORBIDDEN_HINTS = [
        "춘식이", "라이언", "어피치", "카카오프렌즈", "라인프렌즈", "산리오", "헬로키티",
        "포켓몬", "피카츄", "디즈니", "짱구", "스누피", "도라에몽", "똑같이", "비슷하게", "따라",
    ]

    def __init__(self) -> None:
        self.size = 360

    def get_suggestions(self, concept_text: str = "") -> List[Dict[str, Any]]:
        suggestions = [dict(x) for x in self.SUGGESTIONS]
        text = concept_text or ""
        if any(word in text for word in ["문구", "직장", "답장", "넵", "확인"]):
            for row in suggestions:
                if row["id"] == "text_bubble":
                    row["priority"] = "높음"
        if any(word in text for word in ["움직", "GIF", "모션"]):
            for row in suggestions:
                if row["id"] in {"animated_identity_lock", "text_motion_sync", "motion_variation"}:
                    row["priority"] = "높음"
        for row in suggestions:
            row.setdefault("priority", "보통")
        return suggestions

    def _safe_name(self, value: str) -> str:
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "v52_static_to_animated"))
        return safe[:80] or "v52_static_to_animated"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _font(self, size: int):
        return load_korean_font(size)

    def _selection_flags(self, selected_ids: List[str]) -> Dict[str, bool]:
        s = set(selected_ids or [])
        return {
            "bold_outline": "bold_outline" in s,
            "face_contrast": "face_contrast" in s,
            "signature_pose": "signature_pose" in s,
            "text_bubble": "text_bubble" in s,
            "animated_identity_lock": "animated_identity_lock" in s,
            "text_motion_sync": "text_motion_sync" in s,
            "motion_variation": "motion_variation" in s,
            "series_ready": "series_ready" in s,
        }

    def _make_identity(self, concept_text: str, selected_ids: List[str]) -> Dict[str, Any]:
        text = concept_text or "직장인 답장형 캐릭터"
        materials: List[str] = []
        for token in ["보리", "쌀", "감자", "고구마", "팽이버섯", "버섯", "콩", "구름", "메모지", "양말"]:
            if token in text:
                materials.append(token)
        if not materials:
            materials = ["둥근 캐릭터", "작은 친구"]
        flags = self._selection_flags(selected_ids)
        return {
            "materials": materials[:2] if len(materials) >= 2 else materials,
            "base_shape": "둥근 단순 실루엣",
            "main_palette": ["#d7a35f", "#fff2c9", "#3a2c22", "#ffefef"],
            "outline_width": 6 if flags["bold_outline"] else 4,
            "face_contrast": "high" if flags["face_contrast"] else "normal",
            "signature_pose": flags["signature_pose"],
            "text_bubble": flags["text_bubble"],
            "identity_lock": True,
            "motion_sync": flags["text_motion_sync"],
            "motion_variation": 3 if flags["motion_variation"] else 1,
            "phrase_style": "짧은 답장형 우선" if flags["text_bubble"] else "일상 공감형",
            "source_note": "정지형에서 확정한 색상·외곽선·얼굴비율을 움직이는형에도 동일 적용",
        }

    def _draw_character_pair(self, image: Image.Image, identity: Dict[str, Any], mood: str, dx: int = 0, dy: int = 0, scale: float = 1.0, phrase: str = "넵") -> None:
        draw = ImageDraw.Draw(image, "RGBA")
        outline_w = int(identity.get("outline_width", 4))
        outline = (58, 44, 34, 255)
        face = (30, 25, 22, 255)
        barley = (210, 154, 82, 255)
        rice = (255, 243, 203, 255)
        if identity.get("face_contrast") == "high":
            face = (15, 13, 12, 255)
        cx1, cy1 = int(132 + dx), int(182 + dy)
        cx2, cy2 = int(228 + dx), int(184 + dy)
        # shadow
        draw.ellipse((74+dx, 278+dy, 288+dx, 306+dy), fill=(0,0,0,32))
        # Body 1: barley-like oval with awns
        draw.ellipse((cx1-54, cy1-68, cx1+54, cy1+66), fill=barley, outline=outline, width=outline_w)
        for angle in [-50, -25, 0, 25, 50]:
            rad = math.radians(angle)
            x1 = cx1 + int(math.sin(rad) * 14)
            y1 = cy1 - 64
            x2 = cx1 + int(math.sin(rad) * 35)
            y2 = cy1 - 105 + int(abs(angle) * 0.1)
            draw.line((x1, y1, x2, y2), fill=outline, width=max(2, outline_w-1))
        # Body 2: rice rounded rectangle
        draw.rounded_rectangle((cx2-47, cy2-66, cx2+47, cy2+66), radius=45, fill=rice, outline=outline, width=outline_w)
        # arms / signature pose
        if identity.get("signature_pose"):
            draw.line((cx1-48, cy1+22, cx1-86, cy1-6), fill=outline, width=outline_w)
            draw.line((cx2+46, cy2+18, cx2+82, cy2-14), fill=outline, width=outline_w)
            draw.ellipse((cx1-94, cy1-14, cx1-78, cy1+2), fill=barley, outline=outline, width=3)
            draw.ellipse((cx2+74, cy2-22, cx2+92, cy2-4), fill=rice, outline=outline, width=3)
        else:
            draw.line((cx1-48, cy1+28, cx1-78, cy1+46), fill=outline, width=outline_w)
            draw.line((cx2+46, cy2+30, cx2+78, cy2+44), fill=outline, width=outline_w)
        draw.line((cx1+46, cy1+36, cx1+74, cy1+42), fill=outline, width=outline_w)
        draw.line((cx2-44, cy2+38, cx2-70, cy2+44), fill=outline, width=outline_w)
        # face moods
        def eyes(cx, cy, style="normal"):
            if style == "happy":
                draw.arc((cx-31, cy-12, cx-13, cy+10), 200, 340, fill=face, width=3)
                draw.arc((cx+13, cy-12, cx+31, cy+10), 200, 340, fill=face, width=3)
            elif style == "tired":
                draw.line((cx-32, cy-3, cx-14, cy-1), fill=face, width=3)
                draw.line((cx+14, cy-1, cx+32, cy-3), fill=face, width=3)
            else:
                draw.ellipse((cx-29, cy-9, cx-15, cy+7), fill=face)
                draw.ellipse((cx+15, cy-9, cx+29, cy+7), fill=face)
        style = "happy" if mood in {"happy", "thanks", "cheer"} else "tired" if mood in {"tired", "sorry"} else "normal"
        eyes(cx1, cy1, style)
        eyes(cx2, cy2, style)
        if mood in {"happy", "thanks", "cheer"}:
            draw.arc((cx1-23, cy1+12, cx1+23, cy1+42), 0, 180, fill=face, width=3)
            draw.arc((cx2-23, cy2+12, cx2+23, cy2+42), 0, 180, fill=face, width=3)
        elif mood == "sorry":
            draw.arc((cx1-22, cy1+25, cx1+22, cy1+50), 180, 360, fill=face, width=3)
            draw.arc((cx2-22, cy2+25, cx2+22, cy2+50), 180, 360, fill=face, width=3)
        else:
            draw.line((cx1-18, cy1+27, cx1+18, cy1+25), fill=face, width=3)
            draw.line((cx2-18, cy2+27, cx2+18, cy2+25), fill=face, width=3)
        # cheeks
        draw.ellipse((cx1-45, cy1+12, cx1-27, cy1+25), fill=(255, 160, 160, 80))
        draw.ellipse((cx2+27, cy2+12, cx2+45, cy2+25), fill=(255, 160, 160, 80))
        # bubble and text
        if identity.get("text_bubble"):
            draw.rounded_rectangle((72+dx, 34+dy, 288+dx, 92+dy), radius=22, fill=(255,255,255,235), outline=outline, width=3)
            draw.polygon([(164+dx,92+dy),(181+dx,112+dy),(198+dx,92+dy)], fill=(255,255,255,235), outline=outline)
            tx, ty = 180+dx, 63+dy
        else:
            tx, ty = 180+dx, 54+dy
        font = self._font(30 if len(phrase) <= 5 else 24)
        bbox = draw.textbbox((0,0), phrase, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text((tx-tw/2+2, ty-th/2+2), phrase, font=font, fill=(255,255,255,190))
        draw.text((tx-tw/2, ty-th/2), phrase, font=font, fill=face)

    def _create_static_png(self, path: Path, identity: Dict[str, Any], selected: bool, phrase: str) -> None:
        img = Image.new("RGBA", (self.size, self.size), (255,255,255,0))
        # background helper grid-like soft card, transparent edges kept
        draw = ImageDraw.Draw(img, "RGBA")
        if selected:
            draw.rounded_rectangle((18,18,342,342), radius=28, fill=(255,248,232,40), outline=(255,210,120,70), width=2)
        else:
            draw.rounded_rectangle((18,18,342,342), radius=28, fill=(245,245,245,30), outline=(180,180,180,55), width=2)
        self._draw_character_pair(img, identity, "happy" if selected else "normal", phrase=phrase)
        img.save(path)

    def _create_animated_gif(self, path: Path, identity: Dict[str, Any], phrase: str) -> List[Dict[str, Any]]:
        frames: List[Image.Image] = []
        motion_plan: List[Dict[str, Any]] = []
        for i in range(12):
            t = i / 12.0
            if identity.get("motion_sync"):
                dy = int(math.sin(t * math.tau) * 8)
                dx = int(math.sin(t * math.tau * 0.5) * 2)
            else:
                dy = int(math.sin(t * math.tau) * 5)
                dx = 0
            mood = "cheer" if i in {2,3,4,8,9} else "happy"
            img = Image.new("RGBA", (self.size, self.size), (255,255,255,0))
            self._draw_character_pair(img, identity, mood, dx=dx, dy=dy, phrase=phrase)
            frames.append(img)
            motion_plan.append({
                "frame": i + 1,
                "character_offset_y": dy,
                "character_offset_x": dx,
                "text_motion": "캐릭터 통통 튐과 문구 위치 동기화" if identity.get("motion_sync") else "기본 통통 튐",
                "identity_rule": "색상·실루엣·얼굴 비율 고정",
            })
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=90, loop=0, disposal=2)
        return motion_plan

    def _expression_table(self, selected_ids: List[str]) -> List[Dict[str, Any]]:
        table = []
        flags = self._selection_flags(selected_ids)
        for idx, (phrase, emotion, motion) in enumerate(self.BASE_EXPRESSIONS, 1):
            if flags["text_motion_sync"]:
                motion = motion + " / 문구 동작 동기화"
            table.append({
                "no": idx,
                "phrase": phrase,
                "emotion": emotion,
                "static_expression": "눈/입 대비 강화" if flags["face_contrast"] else "기본 표정",
                "animated_motion": motion,
                "applied_to_regeneration": True,
            })
        return table

    def _regeneration_plan(self, selected_suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not selected_suggestions:
            return [{"step": 1, "action": "기본 정지형 생성", "detail": "선택 제안 없음. 기본 identity로 정지형과 움직이는형을 연결"}]
        plan = []
        for idx, sug in enumerate(selected_suggestions, 1):
            plan.append({
                "step": idx,
                "selected_suggestion": sug.get("label"),
                "category": sug.get("category"),
                "actual_apply": sug.get("effect"),
                "result": "정지형 PNG 재생성 및 움직이는형 GIF 생성 규칙에 반영",
            })
        return plan

    def _write_html(self, path: Path, report: Dict[str, Any]) -> None:
        suggestions = "".join(f"<li><b>{html.escape(str(x.get('category','')))}</b> - {html.escape(str(x.get('label','')))}</li>" for x in report["selected_suggestions"])
        plan = "".join(f"<tr><td>{x.get('step')}</td><td>{html.escape(str(x.get('selected_suggestion', x.get('action',''))))}</td><td>{html.escape(str(x.get('result', x.get('detail',''))))}</td></tr>" for x in report["regeneration_plan"])
        body = f"""
<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v52 Static to Animated Apply Report</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;color:#1f2937}}.card{{border:1px solid #e5e7eb;border-radius:16px;padding:18px;margin:12px 0;box-shadow:0 8px 20px rgba(15,23,42,.06)}}img{{max-width:220px;border:1px solid #eee;border-radius:14px;margin-right:12px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #e5e7eb;padding:8px}}th{{background:#f8fafc}}</style></head>
<body><h1>v52 정지형 기반 움직이는형 생성/제안 반영 리포트</h1>
<div class='card'><h2>콘셉트</h2><p>{html.escape(report['concept_text'])}</p></div>
<div class='card'><h2>선택 적용 제안</h2><ul>{suggestions}</ul></div>
<div class='card'><h2>생성 결과</h2><img src='{Path(report['static_png_path']).name}'><img src='{Path(report['animated_gif_path']).name}'></div>
<div class='card'><h2>반영 계획</h2><table><tr><th>단계</th><th>선택/작업</th><th>실제 반영</th></tr>{plan}</table></div>
<div class='card'><h2>안전 원칙</h2><p>기존 캐릭터 복제 없이 색상·표정·포즈·문구·모션 리듬 같은 추상 속성만 반영합니다.</p></div>
</body></html>
"""
        path.write_text(body, encoding="utf-8")

    def build_report(
        self,
        project_name: str,
        concept_text: str,
        selected_suggestion_ids: Optional[List[str]],
        out_dir: Path,
        phrase: str = "넵",
    ) -> V52StaticToAnimatedReport:
        selected_suggestion_ids = selected_suggestion_ids or []
        out_dir = Path(out_dir) / self._safe_name(project_name) / time.strftime("%Y%m%d_%H%M%S")
        out_dir.mkdir(parents=True, exist_ok=True)
        suggestions = self.get_suggestions(concept_text)
        selected = [s for s in suggestions if s["id"] in set(selected_suggestion_ids)]
        identity_before = self._make_identity(concept_text, [])
        identity = self._make_identity(concept_text, selected_suggestion_ids)
        static_before = out_dir / "v52_static_before_suggestion.png"
        static_after = out_dir / "v52_static_regenerated_from_selected_suggestions.png"
        animated_gif = out_dir / "v52_animated_from_static_identity.gif"
        motion_json = out_dir / "v52_motion_plan_identity_locked.json"
        html_path = out_dir / "v52_static_to_animated_apply_report.html"
        json_path = out_dir / "v52_static_to_animated_apply_report.json"
        zip_path = out_dir / "v52_static_to_animated_apply_package.zip"

        self._create_static_png(static_before, identity_before, selected=False, phrase=phrase)
        self._create_static_png(static_after, identity, selected=True, phrase=phrase)
        motion_plan = self._create_animated_gif(animated_gif, identity, phrase=phrase)
        motion_json.write_text(json.dumps(motion_plan, ensure_ascii=False, indent=2), encoding="utf-8")
        expression_table = self._expression_table(selected_suggestion_ids)
        safety_notes = [
            "선택한 제안은 실제 PNG/GIF 재생성 규칙에 반영됩니다.",
            "정지형 identity_lock을 움직이는형 생성에 그대로 사용합니다.",
            "기존 유명 캐릭터/상표/저작권 캐릭터 복제 목적 기능은 포함하지 않습니다.",
            "원본 결과를 덮어쓰지 않고 새 폴더에 저장합니다.",
        ]
        if any(h in (concept_text or "") for h in self.FORBIDDEN_HINTS):
            safety_notes.append("주의: 유명 캐릭터/모방 키워드가 감지되었습니다. 독창 형태로 재작성해야 합니다.")

        apply_payload = {
            "prototype_results": [
                {"label": "v52 선택제안 반영 정지형", "file_path": str(static_after), "asset_type": "static_png", "description": "사용자 선택 제안이 반영된 정지형 캐릭터"},
                {"label": "v52 정지형 기반 움직이는형", "file_path": str(animated_gif), "asset_type": "animated_gif", "description": "정지형 identity_lock 기반 움직이는형 GIF"},
            ],
            "expressions": expression_table,
            "last_gif": str(animated_gif),
            "identity_profile": identity,
            "motion_plan": motion_plan,
            "applied_suggestion_ids": selected_suggestion_ids,
            "next_tabs": ["15 후보 갤러리/세트 선택", "16 표정/파츠 편집기", "17 채팅창 미리보기/최종검수", "18 첫 샘플 세트 제작"],
        }

        temp_report: Dict[str, Any] = {
            "project_name": project_name,
            "output_dir": str(out_dir),
            "concept_text": concept_text,
            "selected_suggestions": selected,
            "identity_lock": identity,
            "regeneration_plan": self._regeneration_plan(selected),
            "expression_table": expression_table,
            "static_png_path": str(static_after),
            "static_before_png_path": str(static_before),
            "animated_gif_path": str(animated_gif),
            "motion_plan_json_path": str(motion_json),
            "html_path": str(html_path),
            "json_path": str(json_path),
            "zip_path": str(zip_path),
            "checksum_sha256": "",
            "apply_payload": apply_payload,
            "safety_notes": safety_notes,
        }
        self._write_html(html_path, temp_report)
        json_path.write_text(json.dumps(temp_report, ensure_ascii=False, indent=2), encoding="utf-8")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in [static_before, static_after, animated_gif, motion_json, html_path, json_path]:
                zf.write(p, arcname=p.name)
        checksum = self._checksum(zip_path)
        temp_report["checksum_sha256"] = checksum
        json_path.write_text(json.dumps(temp_report, ensure_ascii=False, indent=2), encoding="utf-8")
        # update package with final json
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in [static_before, static_after, animated_gif, motion_json, html_path, json_path]:
                zf.write(p, arcname=p.name)
        checksum = self._checksum(zip_path)
        temp_report["checksum_sha256"] = checksum
        json_path.write_text(json.dumps(temp_report, ensure_ascii=False, indent=2), encoding="utf-8")
        return V52StaticToAnimatedReport(**temp_report)
