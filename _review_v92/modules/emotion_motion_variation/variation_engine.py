from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import csv
import hashlib
import html
import json
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class VariationReport:
    project_name: str
    output_dir: str
    html_path: str
    json_path: str
    csv_path: str
    zip_path: str
    plan_count: int
    preview_count: int
    sample_static_path: str
    sample_gif_path: str
    checksum_sha256: str
    plans: List[Dict[str, Any]]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmotionMotionVariationEngine:
    """v26 감정 하위표현 + 행동모션/제스처 확장 엔진.

    목적:
    - '슬픔' 하나도 조용한 눈물/눈물 한 방울/훌쩍임/엉엉/오열 등으로 분화
    - '따봉' 하나도 한손/양손/큰손 강조/튀어나오는 손/흔들리는 따봉 등으로 분화
    - 캐릭터 성격, 문구 상황, 감정 강도, 모션 강도, 포맷에 따라 자동 배정
    - 같은 24/32개 세트 안에서 같은 표정/포즈 반복을 줄이기 위한 계획표와 미리보기 생성
    """

    CANVAS_SIZE = 360

    SADNESS_VARIATIONS: List[Dict[str, Any]] = [
        {"key":"tear_drop", "label":"눈물 한 방울", "eye":"down", "mouth":"sad_small", "tear":"single_drop", "body":"가만히 있음", "text_motion":"천천히 나타남", "effects":["tear"], "min_intensity":1, "max_intensity":2},
        {"key":"quiet_cry", "label":"조용히 눈물", "eye":"looking_down", "mouth":"tiny_sad", "tear":"one_line", "body":"고개 숙임", "text_motion":"작게 흔들림", "effects":["tear_line"], "min_intensity":1, "max_intensity":3},
        {"key":"sniffle", "label":"훌쩍임", "eye":"watery", "mouth":"pout", "tear":"small_drops", "body":"어깨 움츠림", "text_motion":"점 세 개 순차 등장", "effects":["tear","sweat"], "min_intensity":2, "max_intensity":3},
        {"key":"holding_back", "label":"참다가 터짐", "eye":"watery_hold", "mouth":"pressed", "tear":"delayed_drop", "body":"작아졌다가 터짐", "text_motion":"작게 떨림", "effects":["tear","burst"], "min_intensity":3, "max_intensity":4},
        {"key":"loud_cry", "label":"엉엉 울음", "eye":"closed_cry", "mouth":"wide_cry", "tear":"two_streams", "body":"몸 흔들림", "text_motion":"부들부들 흔들림", "effects":["tear_stream"], "min_intensity":4, "max_intensity":5},
        {"key":"wailing", "label":"오열/눈물 폭발", "eye":"squeezed", "mouth":"huge_cry", "tear":"waterfall", "body":"위아래 흔들림", "text_motion":"크게 떨림", "effects":["tear_burst","shock"], "min_intensity":5, "max_intensity":5},
        {"key":"awkward_tear", "label":"민망한 눈물", "eye":"side_watery", "mouth":"awkward", "tear":"tear_plus_sweat", "body":"살짝 움찔", "text_motion":"작게 등장", "effects":["tear","sweat"], "min_intensity":2, "max_intensity":4},
        {"key":"touched_tear", "label":"감동 눈물", "eye":"happy_watery", "mouth":"warm_smile", "tear":"sparkle_tear", "body":"작게 꾸벅", "text_motion":"반짝이며 등장", "effects":["tear","heart","sparkle"], "min_intensity":2, "max_intensity":4},
    ]

    GESTURE_VARIATIONS: Dict[str, List[Dict[str, Any]]] = {
        "따봉": [
            {"key":"one_hand_thumb", "label":"한손 따봉", "hand":"one", "body":"손만 살짝 올림", "text_motion":"톡 튀어나오기", "effects":["small_sparkle"], "min_motion":1, "max_motion":2},
            {"key":"casual_thumb", "label":"무표정/대충 따봉", "hand":"one_side", "body":"고개 돌리고 손만 따봉", "text_motion":"짧게 툭 등장", "effects":["tiny_sparkle"], "min_motion":1, "max_motion":3},
            {"key":"two_hand_thumb", "label":"양손 따봉", "hand":"both", "body":"양손을 들어 따봉", "text_motion":"통통 튀어나오기", "effects":["sparkle"], "min_motion":2, "max_motion":4},
            {"key":"big_hand_thumb", "label":"큰손 강조 따봉", "hand":"big_front", "body":"손이 앞으로 크게 강조", "text_motion":"커졌다 작아짐", "effects":["sparkle","focus_lines"], "min_motion":3, "max_motion":5},
            {"key":"bouncy_thumb", "label":"흔들리는/통통 따봉", "hand":"both_bounce", "body":"양손 따봉이 통통 튐", "text_motion":"문구도 같이 통통", "effects":["sparkle","bounce"], "min_motion":3, "max_motion":5},
            {"key":"thumb_pop", "label":"앞으로 튀어나오는 따봉", "hand":"pop_forward", "body":"손이 앞으로 튀어나옴", "text_motion":"도장처럼 강조", "effects":["impact","sparkle"], "min_motion":4, "max_motion":5},
        ],
        "꾸벅": [
            {"key":"small_bow", "label":"살짝 꾸벅", "body":"고개만 살짝 숙임", "text_motion":"천천히 나타남", "effects":[], "min_motion":1, "max_motion":2},
            {"key":"deep_bow", "label":"깊게 꾸벅", "body":"몸 전체 깊게 숙임", "text_motion":"작게 떨림", "effects":["sweat"], "min_motion":3, "max_motion":4},
            {"key":"repeated_bow", "label":"연속 꾸벅", "body":"작게 두 번 연속 꾸벅", "text_motion":"점점 작아짐", "effects":["sweat"], "min_motion":4, "max_motion":5},
        ],
        "박수": [
            {"key":"small_clap", "label":"작은 박수", "body":"손을 작게 마주침", "text_motion":"톡 등장", "effects":["small_sparkle"], "min_motion":1, "max_motion":2},
            {"key":"big_clap", "label":"큰 박수", "body":"양손을 크게 흔들며 박수", "text_motion":"반짝이며 등장", "effects":["sparkle","confetti"], "min_motion":3, "max_motion":5},
        ],
        "손흔들기": [
            {"key":"small_wave", "label":"작게 손흔들기", "body":"한손 작게 흔들기", "text_motion":"천천히 나타남", "effects":["wave"], "min_motion":1, "max_motion":2},
            {"key":"big_wave", "label":"양손 크게 흔들기", "body":"양손 크게 흔들기", "text_motion":"통통 튐", "effects":["wave","sparkle"], "min_motion":3, "max_motion":5},
        ],
        "화남": [
            {"key":"silent_angry", "label":"조용한 정색", "body":"팔짱/정지", "text_motion":"고정", "effects":["anger_small"], "min_motion":1, "max_motion":2},
            {"key":"shake_angry", "label":"부들부들 화남", "body":"좌우로 떨림", "text_motion":"부들부들 흔들림", "effects":["anger"], "min_motion":3, "max_motion":4},
            {"key":"explode_angry", "label":"분노 폭발", "body":"위로 튀며 폭발", "text_motion":"크게 흔들림", "effects":["anger","burst"], "min_motion":5, "max_motion":5},
        ],
        "피곤": [
            {"key":"half_tired", "label":"반눈 피곤", "body":"가만히 축 처짐", "text_motion":"축 처짐", "effects":["zzz"], "min_motion":1, "max_motion":2},
            {"key":"melt_tired", "label":"녹아내림", "body":"아래로 흐물흐물", "text_motion":"아래로 처짐", "effects":["zzz","shadow"], "min_motion":3, "max_motion":4},
            {"key":"collapse_tired", "label":"기절/바닥에 누움", "body":"바닥에 쓰러짐", "text_motion":"느리게 사라짐", "effects":["zzz","impact"], "min_motion":5, "max_motion":5},
        ],
        "확인": [
            {"key":"nod_check", "label":"고개 끄덕 확인", "body":"작게 끄덕임", "text_motion":"도장처럼 찍힘", "effects":["check"], "min_motion":1, "max_motion":3},
            {"key":"stamp_check", "label":"확인 도장 찍기", "body":"도장 찍는 손동작", "text_motion":"쿵 하고 찍힘", "effects":["check","stamp"], "min_motion":3, "max_motion":5},
        ],
    }

    EMOTION_HINTS = [
        (["슬프", "울", "눈물", "훌쩍", "엉엉", "오열", "울컥"], "슬픔"),
        (["좋아", "최고", "대박", "굿", "따봉"], "따봉"),
        (["감사", "고마", "땡큐"], "꾸벅"),
        (["죄송", "미안", "사과"], "꾸벅"),
        (["확인", "접수", "완료", "봤"], "확인"),
        (["축하", "박수"], "박수"),
        (["안녕", "바이", "왔"], "손흔들기"),
        (["화", "부들", "건드리지", "짜증"], "화남"),
        (["피곤", "졸", "눕", "살려", "기절"], "피곤"),
    ]

    PERSONALITY_HINTS = {
        "까칠": {"prefer":"casual_thumb", "sadness":"holding_back", "note":"까칠/투덜 성격이라 감정은 숨기거나 고개 돌리는 표현을 우선"},
        "투덜": {"prefer":"casual_thumb", "sadness":"awkward_tear", "note":"투덜 말투라 대충/무표정 제스처를 우선"},
        "온순": {"prefer":"two_hand_thumb", "sadness":"quiet_cry", "note":"온순 성격이라 부드러운 눈물과 작은 움직임을 우선"},
        "다정": {"prefer":"two_hand_thumb", "sadness":"touched_tear", "note":"다정 성격이라 하트/반짝임이 섞인 감정 표현을 우선"},
        "피곤": {"prefer":"half_tired", "sadness":"tear_drop", "note":"피곤 성격이라 축 처지는 모션을 우선"},
        "무표정": {"prefer":"casual_thumb", "sadness":"quiet_cry", "note":"무표정 캐릭터라 큰 리액션보다 절제된 표현을 우선"},
    }

    def _safe_name(self, value: str) -> str:
        return "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "emotion_motion"))[:80] or "emotion_motion"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def classify_phrase(self, phrase: str) -> str:
        text = str(phrase or "")
        for hints, category in self.EMOTION_HINTS:
            if any(h in text for h in hints):
                return category
        return "따봉" if "좋" in text else "확인"

    def _pick_personality_hint(self, personality: str) -> Dict[str, str]:
        for key, value in self.PERSONALITY_HINTS.items():
            if key in personality:
                return value
        return {"prefer":"", "sadness":"", "note":"기본 성격 기준"}

    def _pick_sadness(self, intensity: int, personality: str, used: set[str]) -> Dict[str, Any]:
        hint = self._pick_personality_hint(personality).get("sadness", "")
        candidates = [v for v in self.SADNESS_VARIATIONS if v["min_intensity"] <= intensity <= v["max_intensity"]]
        if hint:
            for c in candidates:
                if c["key"] == hint and c["key"] not in used:
                    return c
        for c in candidates:
            if c["key"] not in used:
                return c
        return candidates[0] if candidates else self.SADNESS_VARIATIONS[0]

    def _pick_gesture(self, gesture: str, motion_intensity: int, personality: str, used: set[str]) -> Dict[str, Any]:
        variants = self.GESTURE_VARIATIONS.get(gesture) or self.GESTURE_VARIATIONS.get("확인") or []
        hint = self._pick_personality_hint(personality).get("prefer", "")
        candidates = [v for v in variants if v.get("min_motion", 1) <= motion_intensity <= v.get("max_motion", 5)] or variants
        if hint:
            for c in candidates:
                if c["key"] == hint and c["key"] not in used:
                    return c
        for c in candidates:
            if c["key"] not in used:
                return c
        return candidates[0] if candidates else {"key":"basic", "label":"기본 동작", "body":"기본 자세", "text_motion":"고정", "effects":[]}

    def build_plans(
        self,
        expressions: List[Dict[str, Any]],
        character_name: str = "캐릭터",
        personality: str = "",
        tone: str = "",
        format_key: str = "static_text",
        emotion_intensity: int = 3,
        motion_intensity: int = 3,
    ) -> List[Dict[str, Any]]:
        plans: List[Dict[str, Any]] = []
        used_sadness: set[str] = set()
        used_gesture: set[str] = set()
        ptext = f"{personality} {tone}"
        for idx, expr in enumerate(expressions, start=1):
            phrase = str(expr.get("phrase") or expr.get("text") or expr.get("문구") or f"표현 {idx}")
            category = self.classify_phrase(phrase)
            plan: Dict[str, Any] = {
                "index": idx,
                "phrase": phrase,
                "character_name": character_name,
                "source_category": str(expr.get("category", category)),
                "detected_category": category,
                "format_key": format_key,
                "emotion_intensity": emotion_intensity,
                "motion_intensity": motion_intensity,
                "personality_note": self._pick_personality_hint(ptext).get("note", "기본 성격 기준"),
            }
            if category == "슬픔":
                sub = self._pick_sadness(emotion_intensity, ptext, used_sadness)
                used_sadness.add(sub["key"])
                plan.update({
                    "variation_type": "emotion_subexpression",
                    "family": "슬픔",
                    "variation_key": sub["key"],
                    "variation_label": sub["label"],
                    "eye_style": sub["eye"],
                    "mouth_style": sub["mouth"],
                    "tear_style": sub["tear"],
                    "body_motion": sub["body"],
                    "text_motion": sub["text_motion"],
                    "effects": sub["effects"],
                    "reason": f"문구 '{phrase}'가 슬픔/눈물 계열이라 강도 {emotion_intensity}단계 기준 '{sub['label']}'로 배정",
                })
            else:
                sub = self._pick_gesture(category, motion_intensity, ptext, used_gesture)
                used_gesture.add(sub["key"])
                plan.update({
                    "variation_type": "gesture_motion",
                    "family": category,
                    "variation_key": sub["key"],
                    "variation_label": sub["label"],
                    "eye_style": "personality" if category in ["따봉", "확인"] else category,
                    "mouth_style": "personality",
                    "hand_pose": sub.get("hand", "auto"),
                    "body_motion": sub.get("body", "기본 자세"),
                    "text_motion": sub.get("text_motion", "고정"),
                    "effects": sub.get("effects", []),
                    "reason": f"문구 '{phrase}'가 {category} 계열이라 모션 강도 {motion_intensity}단계 기준 '{sub['label']}'로 배정",
                })
            if "animated" in format_key:
                plan["timeline"] = self._timeline_for_plan(plan)
            else:
                plan["timeline"] = ["정지형: 한 장면 안에서 표정/포즈/문구를 명확히 표시"]
            plans.append(plan)
        return plans

    def default_expression_seed(self, count: int = 32) -> List[Dict[str, Any]]:
        phrases = [
            "좋아요", "최고예요", "확인했습니다", "봤다", "감사합니다", "고마워요", "죄송합니다", "미안해요",
            "눈물 납니다", "엉엉", "안 운다...", "괜찮아요...", "축하해요", "박수", "안녕하세요", "잘가요",
            "화났습니다", "부들부들", "피곤합니다", "기절", "살려주세요", "잘자요", "응원합니다", "파이팅",
            "완료했습니다", "접수했습니다", "대박", "굿", "마음이 아파요", "훌쩍...", "뭐... 괜찮네", "천천히 해도 돼요",
        ]
        return [{"id": i + 1, "phrase": phrases[i % len(phrases)], "category": "자동"} for i in range(count)]

    def _timeline_for_plan(self, plan: Dict[str, Any]) -> List[str]:
        return [
            "프레임 1: 기본 자세 / 문구 대기",
            f"프레임 2: {plan.get('body_motion','동작 시작')} 시작",
            f"프레임 3: {plan.get('variation_label','강조 동작')} 강조",
            f"프레임 4: 문구 '{plan.get('phrase','')}'가 {plan.get('text_motion','등장')}",
            f"프레임 5: 효과 {', '.join(plan.get('effects', []) or ['없음'])} 표시",
            "프레임 6: 최종 자세 유지 후 자연스럽게 반복",
        ]

    def _draw_character_base(self, draw: ImageDraw.ImageDraw, personality: str = "") -> None:
        body = (222, 184, 120, 255)
        if "쌀" in personality or "온순" in personality:
            body = (246, 237, 211, 255)
        elif "감자" in personality:
            body = (206, 158, 92, 255)
        draw.ellipse((105, 76, 255, 226), fill=body, outline=(44, 38, 32), width=5)
        draw.ellipse((122, 190, 238, 300), fill=body, outline=(44, 38, 32), width=5)

    def render_preview(self, plan: Dict[str, Any], out_path: Path, scale_small: bool = False) -> Path:
        img = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        self._draw_character_base(draw, str(plan.get("character_name", "")))
        family = plan.get("family", "")
        label = plan.get("variation_label", "")
        # eyes/mouth
        eye_color = (38, 34, 30, 255)
        if family == "슬픔":
            draw.arc((135, 126, 165, 150), 20, 160, fill=eye_color, width=4)
            draw.arc((195, 126, 225, 150), 20, 160, fill=eye_color, width=4)
            draw.arc((160, 166, 200, 198), 200, 340, fill=eye_color, width=4)
            self._draw_tear(draw, str(plan.get("tear_style", "single_drop")))
        elif family == "화남":
            draw.line((135, 128, 165, 138), fill=eye_color, width=5)
            draw.line((225, 128, 195, 138), fill=eye_color, width=5)
            draw.line((165, 178, 178, 168, 191, 178, 204, 168), fill=eye_color, width=4)
        elif family == "피곤":
            draw.line((135, 140, 165, 140), fill=eye_color, width=4)
            draw.line((195, 140, 225, 140), fill=eye_color, width=4)
            draw.line((165, 178, 205, 178), fill=eye_color, width=4)
            draw.text((230, 82), "Zzz", fill=(70,70,80,255), font=load_korean_font(22))
        else:
            draw.ellipse((140, 130, 154, 144), fill=eye_color)
            draw.ellipse((206, 130, 220, 144), fill=eye_color)
            draw.arc((158, 164, 204, 196), 0, 180, fill=eye_color, width=4)
        # gesture overlays
        if "따봉" in label or family == "따봉":
            self._draw_thumb(draw, str(plan.get("variation_key", "one_hand_thumb")))
        elif "꾸벅" in label or family == "꾸벅":
            draw.line((125, 245, 95, 270), fill=(44,38,32,255), width=8)
            draw.line((235, 245, 265, 270), fill=(44,38,32,255), width=8)
            draw.text((118, 36), "꾸벅", fill=(44,38,32,255), font=load_korean_font(22))
        elif family == "박수":
            draw.ellipse((73, 205, 120, 248), fill=(246,237,211,255), outline=(44,38,32), width=4)
            draw.ellipse((240, 205, 287, 248), fill=(246,237,211,255), outline=(44,38,32), width=4)
            draw.text((136, 40), "짝짝", fill=(44,38,32,255), font=load_korean_font(22))
        # effects
        if any("sparkle" in e for e in plan.get("effects", [])):
            for x, y in [(88,84),(270,88),(268,205)]:
                draw.line((x-8,y,x+8,y), fill=(255,203,80,255), width=3)
                draw.line((x,y-8,x,y+8), fill=(255,203,80,255), width=3)
        if any("heart" in e for e in plan.get("effects", [])):
            draw.text((252, 116), "♥", fill=(235,80,110,255), font=load_korean_font(28))
        if any("check" in e for e in plan.get("effects", [])):
            draw.line((250, 120, 264, 138, 295, 98), fill=(50,150,80,255), width=7)
        if any("anger" in e for e in plan.get("effects", [])):
            draw.text((250, 92), "#", fill=(220,65,45,255), font=load_korean_font(32))
        # text label
        phrase = str(plan.get("phrase", ""))[:12]
        font = load_korean_font(22 if len(phrase) <= 7 else 18)
        bubble = (66, 302, 294, 348)
        draw.rounded_rectangle(bubble, radius=18, fill=(255,255,255,235), outline=(55,55,55,255), width=3)
        draw.text((84, 314), phrase, fill=(35,35,35,255), font=font)
        if scale_small:
            img = img.resize((180, 180), Image.LANCZOS)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
        return out_path

    def _draw_tear(self, draw: ImageDraw.ImageDraw, style: str) -> None:
        blue = (90, 170, 240, 220)
        if style in ["single_drop", "sparkle_tear"]:
            draw.ellipse((220, 150, 235, 174), fill=blue, outline=(40,120,200,255), width=2)
        elif style in ["one_line", "small_drops", "tear_plus_sweat"]:
            draw.line((155, 150, 148, 198), fill=blue, width=5)
            draw.ellipse((215, 154, 228, 174), fill=blue)
        elif style in ["two_streams", "waterfall"]:
            draw.line((150, 150, 135, 230), fill=blue, width=8)
            draw.line((215, 150, 230, 230), fill=blue, width=8)
            if style == "waterfall":
                draw.line((175, 150, 175, 246), fill=blue, width=7)
                draw.line((195, 150, 195, 246), fill=blue, width=7)
        else:
            draw.ellipse((220, 150, 235, 174), fill=blue)

    def _draw_thumb(self, draw: ImageDraw.ImageDraw, key: str) -> None:
        skin = (246, 237, 211, 255)
        outline = (44, 38, 32, 255)
        if key in ["two_hand_thumb", "bouncy_thumb", "big_hand_thumb", "thumb_pop"]:
            draw.rounded_rectangle((54, 168, 114, 236), radius=20, fill=skin, outline=outline, width=5)
            draw.rounded_rectangle((246, 168, 306, 236), radius=20, fill=skin, outline=outline, width=5)
            draw.text((70, 147), "👍", font=load_korean_font(24), fill=(44,38,32,255))
            draw.text((262, 147), "👍", font=load_korean_font(24), fill=(44,38,32,255))
        else:
            draw.rounded_rectangle((246, 176, 306, 244), radius=20, fill=skin, outline=outline, width=5)
            draw.text((262, 154), "👍", font=load_korean_font(24), fill=(44,38,32,255))
        if key in ["big_hand_thumb", "thumb_pop"]:
            draw.rounded_rectangle((35, 138, 130, 250), radius=32, outline=(255, 191, 56, 255), width=8)
            draw.rounded_rectangle((230, 138, 325, 250), radius=32, outline=(255, 191, 56, 255), width=8)

    def render_gif(self, plan: Dict[str, Any], out_path: Path) -> Path:
        frames = []
        for i in range(6):
            tmp = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), (255,255,255,0))
            base_path = out_path.parent / f"__tmp_frame_{i}.png"
            self.render_preview(plan, base_path)
            frame = Image.open(base_path).convert("RGBA")
            if i in [1,3]:
                frame = frame.transform(frame.size, Image.AFFINE, (1,0,0,0,1,-4), resample=Image.BICUBIC)
            elif i in [2,4]:
                frame = frame.transform(frame.size, Image.AFFINE, (1,0,0,0,1,3), resample=Image.BICUBIC)
            tmp.alpha_composite(frame)
            frames.append(tmp)
            try:
                base_path.unlink()
            except Exception:
                pass
        out_path.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=110, loop=0, disposal=2)
        return out_path

    def write_report(self, report: VariationReport) -> None:
        html_rows = []
        for p in report.plans:
            html_rows.append(
                "<tr>" +
                f"<td>{p.get('index')}</td><td>{html.escape(str(p.get('phrase','')))}</td>" +
                f"<td>{html.escape(str(p.get('family','')))}</td><td>{html.escape(str(p.get('variation_label','')))}</td>" +
                f"<td>{html.escape(str(p.get('body_motion','')))}</td><td>{html.escape(str(p.get('text_motion','')))}</td>" +
                f"<td>{html.escape(', '.join(p.get('effects', [])))}</td><td>{html.escape(str(p.get('reason','')))}</td>" +
                "</tr>"
            )
        html_doc = f"""<!doctype html><html><head><meta charset='utf-8'><title>v26 감정/모션 확장 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;}}table{{border-collapse:collapse;width:100%;}}td,th{{border:1px solid #ddd;padding:8px;vertical-align:top;}}th{{background:#f6f6f6;}}.warn{{background:#fff7e6;padding:12px;border:1px solid #f0c36d;}}</style></head><body>
<h1>v26 감정 하위표현 + 행동모션 확장 리포트</h1>
<p><b>프로젝트:</b> {html.escape(report.project_name)}</p>
<p><b>계획 수:</b> {report.plan_count} / <b>미리보기 수:</b> {report.preview_count}</p>
<div class='warn'>같은 감정·동작을 반복하지 않도록 하위표현을 분화한 제작 계획입니다. 최종 제출 전 공식 가이드와 저작권/품질 검사를 다시 확인하세요.</div>
<h2>계획표</h2><table><tr><th>#</th><th>문구</th><th>계열</th><th>하위표현/모션</th><th>몸동작</th><th>문구움직임</th><th>효과</th><th>배정 이유</th></tr>{''.join(html_rows)}</table>
</body></html>"""
        Path(report.html_path).write_text(html_doc, encoding="utf-8")
        Path(report.json_path).write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        with Path(report.csv_path).open("w", newline="", encoding="utf-8-sig") as f:
            fieldnames = ["index","phrase","family","variation_label","body_motion","text_motion","effects","reason"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in report.plans:
                writer.writerow({k: (", ".join(p.get(k, [])) if k == "effects" else p.get(k, "")) for k in fieldnames})

    def build_project(
        self,
        output_dir: Path,
        project_name: str = "emotion_motion_variations",
        expressions: Optional[List[Dict[str, Any]]] = None,
        character_name: str = "보리와 쌀",
        personality: str = "보리는 까칠하고 투덜, 쌀은 온순하고 다정",
        tone: str = "보리는 짧게 투덜, 쌀은 부드럽게 위로",
        format_key: str = "animated_text",
        emotion_intensity: int = 3,
        motion_intensity: int = 3,
        preview_count: int = 12,
    ) -> VariationReport:
        safe = self._safe_name(project_name)
        root = Path(output_dir) / f"{safe}_{int(time.time())}"
        previews = root / "previews"
        previews.mkdir(parents=True, exist_ok=True)
        exprs = expressions or self.default_expression_seed(32)
        plans = self.build_plans(exprs, character_name, personality, tone, format_key, emotion_intensity, motion_intensity)
        preview_items = []
        for p in plans[:preview_count]:
            png_path = previews / f"{int(p['index']):02d}_{self._safe_name(p['variation_key'])}.png"
            self.render_preview(p, png_path)
            preview_items.append(str(png_path))
        sample_static = previews / "sample_static_preview.png"
        self.render_preview(plans[0], sample_static)
        sample_gif = previews / "sample_animated_motion.gif"
        self.render_gif(plans[0], sample_gif)
        html_path = root / "emotion_motion_variation_report.html"
        json_path = root / "emotion_motion_variation_report.json"
        csv_path = root / "emotion_motion_variation_plans.csv"
        zip_path = root / f"{safe}_v26_emotion_motion_pack.zip"
        report = VariationReport(
            project_name=project_name,
            output_dir=str(root),
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
            plan_count=len(plans),
            preview_count=len(preview_items),
            sample_static_path=str(sample_static),
            sample_gif_path=str(sample_gif),
            checksum_sha256="",
            plans=plans,
            warnings=[],
        )
        self.write_report(report)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in [html_path, json_path, csv_path, sample_static, sample_gif]:
                if Path(fp).exists():
                    zf.write(fp, Path(fp).relative_to(root))
            for fp in preview_items:
                if Path(fp).exists():
                    zf.write(fp, Path(fp).relative_to(root))
        checksum = self._checksum(zip_path)
        report.checksum_sha256 = checksum
        self.write_report(report)
        return report
