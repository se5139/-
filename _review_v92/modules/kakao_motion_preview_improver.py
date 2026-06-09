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

from PIL import Image, ImageDraw, ImageFont, ImageSequence

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class V61KakaoMotionPreviewReport:
    project_name: str
    output_dir: str
    concept_text: str
    style_preset: str
    selected_style_suggestions: List[str]
    reference_basis: Dict[str, Any]
    identity_lock: Dict[str, Any]
    quality_scores: Dict[str, int]
    static_preview_png: str
    animated_preview_gif: str
    animated_variants: List[Dict[str, str]]
    webp_preview_path: str
    contact_sheet_path: str
    kakao_24_plan_csv: str
    kakao_24_plan_json: str
    html_report_path: str
    json_report_path: str
    package_zip_path: str
    checksum_sha256: str
    apply_payload: Dict[str, Any]
    safety_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KakaoMotionPreviewImprover:
    """v61 카카오형 정지형→움직이는형 미리보기/품질 개선 엔진.

    핵심 개선점:
    - 정지형 PNG가 만들어진 뒤 같은 identity_lock으로 움직이는 GIF를 즉시 생성한다.
    - Streamlit 화면에서 GIF가 바로 보이도록 GIF/HTML/contact-sheet를 함께 만든다.
    - 카카오 제출 구조에 맞춘 24개 구성 초안(21 PNG + 3 GIF) 계획을 생성한다.
    - 온라인/유튜브/인터넷 수집 결과는 기존 캐릭터 복제가 아니라 공감 문구, 표정 대비,
      포즈 리듬, 미니 리액션성 같은 추상 신호만 반영한다.
    """

    SIZE = 360
    FORBIDDEN_HINTS = [
        "춘식이", "라이언", "어피치", "카카오프렌즈", "라인프렌즈", "산리오", "헬로키티",
        "포켓몬", "피카츄", "디즈니", "짱구", "스누피", "도라에몽", "똑같이", "비슷하게", "따라",
    ]

    STYLE_SUGGESTIONS = [
        "굵은 외곽선과 큰 실루엣",
        "눈·입 대비 강화",
        "짧은 답장형 문구 우선",
        "정지형 identity를 움직이는형에도 고정",
        "3개 GIF 모션 샘플을 바로 미리보기",
        "미니 리액션처럼 즉시 이해되는 감정",
        "하찮고 공감되는 일상형 포즈",
        "24개 구성: 21 PNG + 3 GIF 계획 생성",
    ]

    BASE_PHRASES = [
        ("넵", "확인", "nod"), ("확인했습니다", "확인", "pop"), ("감사합니다", "감사", "sparkle"),
        ("죄송합니다", "사과", "bow"), ("잠시만요", "대기", "hold"), ("바로 볼게요", "확인", "bounce"),
        ("완료했습니다", "완료", "check"), ("좋아요", "긍정", "bounce"), ("대박", "놀람", "jump"),
        ("파이팅", "응원", "fist"), ("살려주세요", "피곤", "melt"), ("퇴근하고 싶어요", "직장", "drag"),
        ("오늘도 버팁니다", "공감", "wobble"), ("이미 구겨졌습니다", "공감", "squash"),
        ("괜찮아요", "위로", "soft"), ("도와주세요", "부탁", "plead"), ("기다릴게요", "대기", "clock"),
        ("축하해요", "축하", "confetti"), ("울컥", "감동", "tear"), ("민망합니다", "민망", "blush"),
        ("화났습니다", "분노", "shake"), ("잘자요", "인사", "float"), ("주말 잘 보내요", "인사", "wave"),
        ("조용히 파이팅", "응원", "small_fist"),
    ]

    def _font(self, size: int):
        return load_korean_font(size)

    def _safe_name(self, value: str) -> str:
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "v61_kakao_motion_preview"))
        return safe[:80] or "v61_kakao_motion_preview"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def build_reference_basis(self, online_notes: str = "") -> Dict[str, Any]:
        notes = online_notes or ""
        keywords = []
        for word in ["직장인", "공감", "하찮", "미니", "리액션", "짧은문구", "움직이는", "퇴근", "확인", "넵"]:
            if word in notes.replace(" ", ""):
                keywords.append(word)
        return {
            "kakao_static_guideline": "정지형 기획 기준: 32 PNG, 360x360, 투명 배경, 작은 화면 가독성 우선",
            "kakao_animated_guideline": "움직이는형 기획 기준: 24개 중 GIF 3개 미리보기, 24프레임 이하를 목표로 관리",
            "trend_signals": [
                "짧은 답장형 문구",
                "하찮고 공감되는 일상 상황",
                "굵은 외곽선과 단순 실루엣",
                "미니 리액션처럼 바로 이해되는 감정",
                "기존 캐릭터 모방 대신 추상 품질 기준만 반영",
            ],
            "detected_keywords_from_notes": keywords,
            "online_notes_length": len(notes),
            "source_policy": "온라인/유튜브 정보는 원본 캐릭터 복제가 아니라 문구 길이, 포즈 리듬, 감정 분포, 가독성 같은 추상 신호만 사용",
        }

    def make_identity(self, concept_text: str, style_preset: str, selected: List[str], online_notes: str) -> Dict[str, Any]:
        text = concept_text or "직장인 공감 답장 캐릭터"
        lower = text.lower()
        material = "둥근 캐릭터"
        for token in ["보리", "쌀", "감자", "고구마", "버섯", "메모지", "구름", "콩", "양말", "먼지", "만두"]:
            if token in text:
                material = token
                break
        if "하찮" in style_preset or "공감" in style_preset or "하찮" in online_notes:
            mood = "하찮은 공감형"
            palette = ["#f4c66f", "#fff0bd", "#34251f", "#ffb7b7"]
        elif "직장" in style_preset or "업무" in lower:
            mood = "직장인 답장형"
            palette = ["#a7c7e7", "#fff7d6", "#24313f", "#fca5a5"]
        elif "미니" in style_preset or "리액션" in online_notes:
            mood = "미니 리액션형"
            palette = ["#bdecc8", "#fff4c8", "#263528", "#ffb8d1"]
        else:
            mood = "귀여운 단순형"
            palette = ["#ddb07a", "#fff1ce", "#35251c", "#ffb0b0"]
        return {
            "material": material,
            "style_preset": style_preset,
            "mood": mood,
            "palette": palette,
            "outline_width": 7 if "굵은 외곽선과 큰 실루엣" in selected else 5,
            "face_scale": 1.25 if "눈·입 대비 강화" in selected else 1.0,
            "phrase_style": "짧은 답장형" if "짧은 답장형 문구 우선" in selected else "일상 공감형",
            "identity_lock": True,
            "motion_rule": "정지형의 색상·외곽선·얼굴비율·몸통 크기를 움직이는형 전체 프레임에 고정",
            "preview_required": True,
        }

    def _draw_body(self, img: Image.Image, identity: Dict[str, Any], phrase: str, emotion: str, frame: int = 0, motion: str = "bounce") -> None:
        draw = ImageDraw.Draw(img, "RGBA")
        palette = identity["palette"]
        body = tuple(int(palette[0].lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        sub = tuple(int(palette[1].lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        line = tuple(int(palette[2].lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        cheek = tuple(int(palette[3].lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (110,)
        ow = int(identity.get("outline_width", 5))
        fscale = float(identity.get("face_scale", 1.0))

        t = frame / 16.0
        dy = dx = 0
        squash = 0
        if motion in {"bounce", "jump", "pop", "sparkle", "check", "fist", "small_fist"}:
            dy = int(math.sin(t * math.tau) * 10)
        elif motion in {"nod", "bow"}:
            dy = int(abs(math.sin(t * math.tau)) * 9)
        elif motion in {"shake", "wobble"}:
            dx = int(math.sin(t * math.tau * 2) * 8)
        elif motion in {"melt", "drag", "squash"}:
            dy = int(abs(math.sin(t * math.tau)) * 7)
            squash = int(abs(math.sin(t * math.tau)) * 10)
        elif motion in {"wave", "float", "soft"}:
            dy = int(math.sin(t * math.tau) * 5)

        # invisible bounds guide kept transparent; visual shadow only
        draw.ellipse((75 + dx, 284, 285 + dx, 312), fill=(0, 0, 0, 28))
        # speech bubble
        draw.rounded_rectangle((48, 28, 312, 88), radius=23, fill=(255, 255, 255, 238), outline=line, width=3)
        draw.polygon([(165, 87), (182, 109), (199, 87)], fill=(255, 255, 255, 238), outline=line)
        font = self._font(31 if len(phrase) <= 6 else 24)
        bbox = draw.textbbox((0, 0), phrase, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((180 - tw / 2 + 2, 58 - th / 2 + 2), phrase, font=font, fill=(255, 255, 255, 200))
        draw.text((180 - tw / 2, 58 - th / 2), phrase, font=font, fill=line)

        # main body: intentionally simple and original, not a known character replica
        cx, cy = 180 + dx, 198 + dy
        body_box = (cx - 77, cy - 72 + squash, cx + 77, cy + 78)
        draw.rounded_rectangle(body_box, radius=52, fill=body, outline=line, width=ow)
        draw.ellipse((cx - 49, cy - 91 + squash, cx + 49, cy - 20), fill=sub, outline=line, width=ow)
        # small limbs
        draw.line((cx - 72, cy + 10, cx - 107, cy - 6 + (8 if motion == "wave" else 0)), fill=line, width=ow)
        draw.line((cx + 72, cy + 10, cx + 107, cy - 12 - (8 if motion == "wave" else 0)), fill=line, width=ow)
        draw.ellipse((cx - 116, cy - 15, cx - 98, cy + 4), fill=sub, outline=line, width=3)
        draw.ellipse((cx + 98, cy - 21, cx + 118, cy - 2), fill=sub, outline=line, width=3)
        draw.line((cx - 38, cy + 73, cx - 46, cy + 96), fill=line, width=ow)
        draw.line((cx + 38, cy + 73, cx + 46, cy + 96), fill=line, width=ow)

        # face
        eye_r = int(7 * fscale)
        if emotion in {"피곤", "공감", "사과"}:
            draw.line((cx - 33, cy - 19, cx - 16, cy - 17), fill=line, width=4)
            draw.line((cx + 16, cy - 17, cx + 33, cy - 19), fill=line, width=4)
        elif emotion in {"감사", "응원", "축하", "긍정", "완료"}:
            draw.arc((cx - 40, cy - 28, cx - 18, cy - 6), 200, 340, fill=line, width=4)
            draw.arc((cx + 18, cy - 28, cx + 40, cy - 6), 200, 340, fill=line, width=4)
        else:
            draw.ellipse((cx - 34, cy - 24, cx - 34 + eye_r * 2, cy - 24 + eye_r * 2), fill=line)
            draw.ellipse((cx + 20, cy - 24, cx + 20 + eye_r * 2, cy - 24 + eye_r * 2), fill=line)
        if emotion in {"감사", "응원", "축하", "긍정", "완료"}:
            draw.arc((cx - 23, cy + 5, cx + 23, cy + 35), 0, 180, fill=line, width=4)
        elif emotion in {"사과", "피곤", "분노"}:
            draw.arc((cx - 22, cy + 18, cx + 22, cy + 40), 180, 360, fill=line, width=4)
        else:
            draw.line((cx - 17, cy + 18, cx + 17, cy + 18), fill=line, width=4)
        draw.ellipse((cx - 62, cy + 3, cx - 40, cy + 18), fill=cheek)
        draw.ellipse((cx + 40, cy + 3, cx + 62, cy + 18), fill=cheek)

        # motion accents
        if motion in {"sparkle", "confetti", "jump", "pop"}:
            for sx, sy in [(74, 117), (289, 128), (65, 236), (300, 238)]:
                r = 4 + frame % 3
                draw.line((sx - r, sy, sx + r, sy), fill=(255, 202, 40, 190), width=3)
                draw.line((sx, sy - r, sx, sy + r), fill=(255, 202, 40, 190), width=3)
        if motion in {"tear", "melt"}:
            draw.ellipse((cx + 43, cy + 6, cx + 54, cy + 24), fill=(93, 188, 255, 180))

    def _save_png(self, path: Path, identity: Dict[str, Any], phrase: str, emotion: str, motion: str = "bounce") -> None:
        img = Image.new("RGBA", (self.SIZE, self.SIZE), (255, 255, 255, 0))
        self._draw_body(img, identity, phrase, emotion, frame=0, motion=motion)
        img.save(path)

    def _save_gif(self, path: Path, identity: Dict[str, Any], phrase: str, emotion: str, motion: str, frame_count: int = 16) -> List[Dict[str, Any]]:
        frames: List[Image.Image] = []
        plan: List[Dict[str, Any]] = []
        for i in range(frame_count):
            img = Image.new("RGBA", (self.SIZE, self.SIZE), (255, 255, 255, 0))
            self._draw_body(img, identity, phrase, emotion, frame=i, motion=motion)
            frames.append(img)
            plan.append({"frame": i + 1, "motion": motion, "identity_lock": "same color/outline/face/body ratio"})
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=75, loop=0, disposal=2)
        return plan

    def _save_webp(self, gif_path: Path, webp_path: Path) -> bool:
        try:
            im = Image.open(gif_path)
            frames = [frame.copy().convert("RGBA") for frame in ImageSequence.Iterator(im)]
            if not frames:
                return False
            frames[0].save(webp_path, save_all=True, append_images=frames[1:], duration=75, loop=0, lossless=True, method=4)
            return True
        except Exception:
            return False

    def _contact_sheet(self, path: Path, assets: List[Tuple[str, Path]]) -> None:
        thumb = 128
        cols = 4
        rows = math.ceil(len(assets) / cols)
        sheet = Image.new("RGB", (cols * 210, rows * 172 + 34), "white")
        draw = ImageDraw.Draw(sheet)
        font = self._font(18)
        draw.text((14, 8), "v61 GIF 미리보기/24개 구성 초안", fill=(30, 41, 59), font=font)
        for idx, (label, p) in enumerate(assets):
            x = (idx % cols) * 210 + 18
            y = (idx // cols) * 172 + 42
            try:
                im = Image.open(p).convert("RGBA")
                if getattr(im, "is_animated", False):
                    im.seek(0)
                    im = im.convert("RGBA")
                im.thumbnail((thumb, thumb))
                bg = Image.new("RGB", (thumb, thumb), "#f8fafc")
                bg.paste(im, ((thumb - im.width) // 2, (thumb - im.height) // 2), im if im.mode == "RGBA" else None)
                sheet.paste(bg, (x, y))
            except Exception:
                draw.rectangle((x, y, x + thumb, y + thumb), outline=(220, 38, 38), width=2)
            draw.text((x, y + thumb + 6), label[:18], fill=(30, 41, 59), font=font)
        sheet.save(path)

    def _write_plan(self, csv_path: Path, json_path: Path, identity: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = []
        for idx, (phrase, emotion, motion) in enumerate(self.BASE_PHRASES, 1):
            asset_type = "GIF" if idx in {2, 10, 21} else "PNG"
            rows.append({
                "no": idx,
                "asset_type": asset_type,
                "phrase": phrase,
                "emotion": emotion,
                "motion_or_pose": motion,
                "identity_rule": identity["motion_rule"],
                "kakao_note": "움직이는형 24개 구성 초안: 21 PNG + 3 GIF",
            })
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader(); writer.writerows(rows)
        json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return rows

    def _quality_scores(self, selected: List[str], notes: str) -> Dict[str, int]:
        base = 70
        return {
            "gif_preview_visible": 100,
            "identity_consistency": 94 if "정지형 identity를 움직이는형에도 고정" in selected else 82,
            "small_chat_readability": min(100, base + (12 if "굵은 외곽선과 큰 실루엣" in selected else 0) + (8 if "눈·입 대비 강화" in selected else 0)),
            "trend_fit": min(100, base + (10 if "공감" in notes or "하찮" in notes else 0) + (8 if "미니" in notes or "리액션" in notes else 0)),
            "kakao_pack_readiness": 88,
        }

    def _write_html(self, html_path: Path, report: Dict[str, Any]) -> None:
        variants = "".join(
            f"<div class='card'><h3>{html.escape(v['label'])}</h3><img src='{Path(v['path']).name}'></div>"
            for v in report["animated_variants"]
        )
        suggestions = "".join(f"<li>{html.escape(x)}</li>" for x in report["selected_style_suggestions"])
        html_text = f"""
<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v61 Kakao Motion Preview</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;background:#f8fafc;color:#0f172a}}.hero{{background:linear-gradient(135deg,#0f172a,#2563eb);color:white;border-radius:22px;padding:22px;margin-bottom:18px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}}.card{{background:white;border:1px solid #e5e7eb;border-radius:18px;padding:16px;box-shadow:0 8px 20px rgba(15,23,42,.06)}}img{{max-width:220px;border-radius:16px;border:1px solid #e5e7eb;background:#fff}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #e5e7eb;padding:8px}}th{{background:#eff6ff}}</style></head>
<body><div class='hero'><h1>v61 카카오형 GIF 미리보기/품질 개선 리포트</h1><p>정지형 생성 후 움직이는 GIF가 바로 보이도록 생성했습니다.</p></div>
<div class='grid'><div class='card'><h2>정지형</h2><img src='{Path(report['static_preview_png']).name}'></div><div class='card'><h2>대표 GIF</h2><img src='{Path(report['animated_preview_gif']).name}'></div></div>
<h2>GIF 모션 후보</h2><div class='grid'>{variants}</div>
<div class='card'><h2>선택 반영 제안</h2><ul>{suggestions}</ul></div>
<div class='card'><h2>품질 점수</h2><pre>{html.escape(json.dumps(report['quality_scores'], ensure_ascii=False, indent=2))}</pre></div>
<div class='card'><h2>안전 원칙</h2><p>온라인 정보는 캐릭터 복제 목적이 아니라 문구 길이, 포즈 유형, 감정 분포, 모션 리듬 같은 추상 품질 신호만 반영했습니다.</p></div>
</body></html>
"""
        html_path.write_text(html_text, encoding="utf-8")

    def build_report(
        self,
        project_name: str,
        concept_text: str,
        style_preset: str,
        selected_style_suggestions: Optional[List[str]],
        online_notes: str,
        out_dir: Path,
        main_phrase: str = "넵",
    ) -> V61KakaoMotionPreviewReport:
        selected_style_suggestions = selected_style_suggestions or []
        out_dir = Path(out_dir) / self._safe_name(project_name) / time.strftime("%Y%m%d_%H%M%S")
        out_dir.mkdir(parents=True, exist_ok=True)
        reference_basis = self.build_reference_basis(online_notes)
        identity = self.make_identity(concept_text, style_preset, selected_style_suggestions, online_notes)
        static_path = out_dir / "v61_static_preview_identity_locked.png"
        main_gif = out_dir / "v61_animated_preview_visible.gif"
        webp_path = out_dir / "v61_animated_preview_visible.webp"
        contact_sheet = out_dir / "v61_preview_contact_sheet.png"
        plan_csv = out_dir / "v61_kakao_24_item_plan.csv"
        plan_json = out_dir / "v61_kakao_24_item_plan.json"
        html_path = out_dir / "v61_kakao_motion_preview_report.html"
        json_path = out_dir / "v61_kakao_motion_preview_report.json"
        zip_path = out_dir / "v61_kakao_motion_preview_package.zip"

        self._save_png(static_path, identity, main_phrase, "확인", "nod")
        main_motion_plan = self._save_gif(main_gif, identity, main_phrase, "확인", "bounce")
        self._save_webp(main_gif, webp_path)
        variants: List[Dict[str, str]] = []
        variant_specs = [("통통 튐", "bounce", "넵", "확인"), ("꾸벅", "bow", "죄송합니다", "사과"), ("부들부들", "shake", "화났습니다", "분노")]
        for label, motion, phrase, emotion in variant_specs:
            p = out_dir / f"v61_motion_{motion}.gif"
            self._save_gif(p, identity, phrase, emotion, motion)
            variants.append({"label": label, "path": str(p), "motion": motion, "phrase": phrase})
        plan_rows = self._write_plan(plan_csv, plan_json, identity)
        preview_assets = [("정지형", static_path), ("대표 GIF", main_gif)] + [(v["label"], Path(v["path"])) for v in variants]
        self._contact_sheet(contact_sheet, preview_assets)
        quality_scores = self._quality_scores(selected_style_suggestions, online_notes)
        safety_notes = [
            "움직이는 GIF가 화면에서 바로 보이도록 대표 GIF와 3개 모션 후보를 생성했습니다.",
            "정지형 identity_lock을 움직이는형 모든 프레임에 적용합니다.",
            "카카오형 24개 구성 초안은 21 PNG + 3 GIF 계획으로 생성했습니다.",
            "기존 인기 캐릭터를 복제하지 않고 추상 트렌드 신호만 반영합니다.",
        ]
        if any(h in (concept_text or "") for h in self.FORBIDDEN_HINTS):
            safety_notes.append("유명 캐릭터/모방 키워드가 감지되었습니다. 독창 콘셉트로 다시 작성해야 합니다.")
        apply_payload = {
            "prototype_results": [
                {"label": "v61 정지형 미리보기", "file_path": str(static_path), "asset_type": "static_png", "description": "identity_lock 정지형"},
                {"label": "v61 움직이는 미리보기 GIF", "file_path": str(main_gif), "asset_type": "animated_gif", "description": "화면에서 바로 확인 가능한 움직이는 GIF"},
            ],
            "last_gif": str(main_gif),
            "animated_variants": variants,
            "expressions": plan_rows,
            "identity_profile": identity,
            "quality_scores": quality_scores,
            "reference_basis": reference_basis,
            "next_tabs": ["49 정지형 기반 움직이는형/제안 반영", "15 후보 갤러리/세트 선택", "17 채팅창 미리보기/최종검수"],
        }
        report: Dict[str, Any] = {
            "project_name": project_name,
            "output_dir": str(out_dir),
            "concept_text": concept_text,
            "style_preset": style_preset,
            "selected_style_suggestions": selected_style_suggestions,
            "reference_basis": reference_basis,
            "identity_lock": identity,
            "quality_scores": quality_scores,
            "static_preview_png": str(static_path),
            "animated_preview_gif": str(main_gif),
            "animated_variants": variants,
            "webp_preview_path": str(webp_path) if webp_path.exists() else "",
            "contact_sheet_path": str(contact_sheet),
            "kakao_24_plan_csv": str(plan_csv),
            "kakao_24_plan_json": str(plan_json),
            "html_report_path": str(html_path),
            "json_report_path": str(json_path),
            "package_zip_path": str(zip_path),
            "checksum_sha256": "",
            "apply_payload": apply_payload,
            "safety_notes": safety_notes,
        }
        self._write_html(html_path, report)
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        files = [static_path, main_gif, contact_sheet, plan_csv, plan_json, html_path, json_path]
        if webp_path.exists():
            files.append(webp_path)
        files += [Path(v["path"]) for v in variants]
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in files:
                if p.exists():
                    zf.write(p, arcname=p.name)
        checksum = self._checksum(zip_path)
        report["checksum_sha256"] = checksum
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in files:
                if p.exists():
                    zf.write(p, arcname=p.name)
        checksum = self._checksum(zip_path)
        report["checksum_sha256"] = checksum
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return V61KakaoMotionPreviewReport(**report)
