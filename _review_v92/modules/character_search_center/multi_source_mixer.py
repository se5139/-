from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from pathlib import Path
from typing import Any

from modules.character_search_center.keyword_analyzer import KeywordProfile
from modules.character_search_center.image_feature_analyzer import ImageFeatureProfile


@dataclass
class MaterialToken:
    name: str
    category: str
    role_hint: str
    motion_hint: str
    phrase_hint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BlendConcept:
    name: str
    materials: list[str]
    body_direction: str
    color_direction: str
    personality: str
    signature_motion: str
    signature_phrase: str
    format_hint: str
    originality_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MultiImageBlendProfile:
    image_count: int
    accepted_count: int
    warnings: list[str]
    dominant_color_palette: list[str]
    shape_mix: list[str]
    motion_mix: list[str]
    blend_direction: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MultiSourceMixer:
    """여러 이미지/단어 소재를 복제하지 않고 독창 콘셉트로 재조합합니다."""

    KNOWN_MATERIALS = {
        "보리": ("곡물", "까슬한 수염/낟알 질감", "흔들리는 이삭", "보리보리 버팁니다"),
        "쌀": ("곡물", "작고 둥근 낟알/하얀 색감", "톡톡 튀는 낟알", "한 톨씩 확인했습니다"),
        "감자": ("음식/사물", "둥근 몸통/흙빛 색감", "싹이 남/납작해짐", "칭찬받으면 싹납니다"),
        "고구마": ("음식/사물", "길쭉한 몸통/보라·노랑 색감", "김이 모락/말랑해짐", "답답해서 고구마입니다"),
        "메모지": ("사물", "네모난 종이/접힌 모서리", "구겨졌다 펴짐", "확인했습니다... 접수"),
        "돌멩이": ("사물", "무표정한 단단함/회색 질감", "작게 끄덕임/금이 감", "넵... 아주 작게"),
        "무": ("음식/사물", "하얀 몸통/초록 잎", "땅속으로 숨음/잎 흔들림", "잠시 땅속입니다"),
        "쌀알": ("곡물", "작고 단순한 알갱이", "떼굴떼굴/톡톡 튐", "한 톨 남았습니다"),
        "콩": ("음식/사물", "작고 둥근 점 캐릭터", "통통 튐", "콩닥콩닥 확인"),
        "양말": ("사물", "길쭉하고 접히는 형태", "축 처짐/뒤집힘", "오늘도 늘어졌습니다"),
    }

    SPLIT_PATTERN = re.compile(r"\s*(?:,|\+|/|&|와|과|랑|하고|및|그리고|\n)\s*")

    def parse_materials(self, raw_text: str) -> list[MaterialToken]:
        text = raw_text or ""
        parts = [p.strip() for p in self.SPLIT_PATTERN.split(text) if p.strip()]
        # 긴 문장에서는 알려진 소재만 추가로 추출
        for material in self.KNOWN_MATERIALS:
            if material in text and material not in parts:
                parts.append(material)
        seen: set[str] = set()
        tokens: list[MaterialToken] = []
        for part in parts:
            cleaned = re.sub(r"[^0-9A-Za-z가-힣 ]", "", part).strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            if cleaned not in self.KNOWN_MATERIALS and len(cleaned) > 10 and " " in cleaned:
                # 긴 설명문은 소재가 아니라 콘셉트/성격 맥락일 가능성이 높으므로
                # 복합 소재 토큰에서는 제외하고 KeywordAnalyzer 쪽에서 활용합니다.
                continue
            category, role, motion, phrase = self.KNOWN_MATERIALS.get(
                cleaned,
                ("사용자 소재", "사용자가 지정한 핵심 소재", "작게 튐/흔들림/꾸벅", f"{cleaned}답게 갑니다"),
            )
            tokens.append(MaterialToken(cleaned, category, role, motion, phrase))
        return tokens

    def blend_images(self, image_profiles: list[ImageFeatureProfile]) -> MultiImageBlendProfile:
        warnings: list[str] = []
        count = len(image_profiles)
        if count == 0:
            warnings.append("이미지가 없어서 단어 기반 결합만 사용합니다.")
        if count < 3 and count > 0:
            warnings.append("이미지 결합형은 3~5장 첨부가 가장 좋습니다. 현재는 참고 분석으로만 처리합니다.")
        if count > 5:
            warnings.append("이미지는 최대 5장까지 핵심 결합 대상으로 사용하고, 나머지는 참고에서 제외하는 것이 좋습니다.")
        accepted = min(max(count, 0), 5)
        selected = image_profiles[:accepted]
        palette: list[str] = []
        shape_mix: list[str] = []
        motion_mix: list[str] = []
        for profile in selected:
            for color in profile.dominant_colors:
                if color not in palette and len(palette) < 8:
                    palette.append(color)
            if profile.shape_hint not in shape_mix:
                shape_mix.append(profile.shape_hint)
            if profile.motion_hint not in motion_mix:
                motion_mix.append(profile.motion_hint)
        blend_direction = self._image_blend_direction(shape_mix, motion_mix)
        return MultiImageBlendProfile(count, accepted, warnings, palette, shape_mix, motion_mix, blend_direction)

    def build_blend_concepts(
        self,
        materials: list[MaterialToken],
        keyword_profile: KeywordProfile | None = None,
        image_blend: MultiImageBlendProfile | None = None,
        count: int = 8,
    ) -> list[BlendConcept]:
        material_names = [m.name for m in materials]
        if not material_names and keyword_profile:
            material_names = keyword_profile.bases[:]
            materials = [MaterialToken(name, "기본 후보", "단순한 캐릭터 본체", "꾸벅/통통 튐", f"{name}답게 갑니다") for name in material_names]
        if not material_names:
            material_names = ["메모지", "감자"]
            materials = [MaterialToken("메모지", "사물", "구겨지는 종이", "구겨졌다 펴짐", "확인했습니다"), MaterialToken("감자", "음식/사물", "둥근 몸통", "싹이 남", "칭찬받으면 싹납니다")]

        target = (keyword_profile.targets[0] if keyword_profile and keyword_profile.targets else "일상 대화")
        tone = (keyword_profile.tone[0] if keyword_profile and keyword_profile.tone else "짧은")
        emotions = keyword_profile.emotions if keyword_profile else ["확인", "감사", "피곤"]
        color_direction = self._color_direction(image_blend)
        body_direction = self._body_direction(materials, image_blend)

        patterns = [
            ("반반 조합형", "두 소재가 한 몸에 섞인 캐릭터", "좌우로 갈라진 성격이 표정으로 바뀜"),
            ("짝꿍 듀오형", "두 소재가 작은 콤비처럼 같이 움직임", "하나는 말하고 하나는 반응함"),
            ("변신형", "감정에 따라 A소재에서 B소재 느낌으로 바뀜", "문구 등장과 동시에 질감/색감이 변함"),
            ("가족/무리형", "여러 소재가 작은 알갱이 무리처럼 움직임", "여러 개체가 모였다 흩어짐"),
            ("도구+본체형", "하나는 캐릭터 본체, 하나는 말풍선/효과가 됨", "문구가 소재 효과처럼 찍히거나 피어남"),
        ]

        concepts: list[BlendConcept] = []
        base_label = self._name_join(material_names)
        for idx in range(count):
            pattern_name, pattern_body, motion_extra = patterns[idx % len(patterns)]
            emotion = emotions[idx % len(emotions)] if emotions else "확인"
            motion = self._motion_for(materials, idx, motion_extra)
            phrase = self._phrase_for(materials, emotion, target, idx)
            concepts.append(
                BlendConcept(
                    name=f"{base_label} {pattern_name}",
                    materials=material_names,
                    body_direction=f"{body_direction} / {pattern_body}",
                    color_direction=color_direction,
                    personality=f"{target}에서 쓰기 좋은 {tone} 말투, {emotion} 감정을 중심으로 표현",
                    signature_motion=motion,
                    signature_phrase=phrase,
                    format_hint=self._format_hint(idx, motion, phrase),
                    originality_note="첨부 이미지나 단어를 그대로 합성·복제하지 않고, 색감·물성·상징만 추출해 새 캐릭터로 재조합하는 방향입니다.",
                )
            )
        return concepts

    def _image_blend_direction(self, shape_mix: list[str], motion_mix: list[str]) -> str:
        if not shape_mix:
            return "단어 소재 중심으로 본체를 설계합니다."
        return " / ".join(shape_mix[:3]) + " 형태감을 섞되, 기존 이미지의 구체적 외형은 복제하지 않습니다."

    def _color_direction(self, image_blend: MultiImageBlendProfile | None) -> str:
        if not image_blend or not image_blend.dominant_color_palette:
            return "소재 고유색 2~3개만 사용해 작은 화면 가독성을 우선합니다."
        return f"대표 팔레트 {', '.join(image_blend.dominant_color_palette[:5])} 중 2~3개만 선택해 단순화합니다."

    def _body_direction(self, materials: list[MaterialToken], image_blend: MultiImageBlendProfile | None) -> str:
        roles = [m.role_hint for m in materials[:3]]
        if image_blend and image_blend.shape_mix:
            return f"이미지 형태 힌트({', '.join(image_blend.shape_mix[:2])})와 소재 물성({', '.join(roles)})을 결합"
        return f"소재 물성({', '.join(roles)})을 단순 실루엣으로 재해석"

    def _motion_for(self, materials: list[MaterialToken], idx: int, extra: str) -> str:
        if materials:
            base_motion = materials[idx % len(materials)].motion_hint
        else:
            base_motion = "작게 튐"
        return f"{base_motion} + {extra}"

    def _phrase_for(self, materials: list[MaterialToken], emotion: str, target: str, idx: int) -> str:
        if materials:
            hint = materials[idx % len(materials)].phrase_hint
        else:
            hint = "확인했습니다"
        if "직장" in target or target == "직장인":
            suffixes = ["확인했습니다", "넵... 진행하겠습니다", "죄송합니다", "퇴근하면 펴질게요"]
        else:
            suffixes = ["괜찮아요", "고마워요", "잠시만요", "오늘도 버팁니다"]
        return f"{hint} / {suffixes[idx % len(suffixes)]}"

    def _format_hint(self, idx: int, motion: str, phrase: str) -> str:
        if any(word in motion for word in ["변함", "찍", "흩어", "흔들", "튐", "펴짐"]):
            return "움직이는 문구 결합형 이모티콘 우선"
        if len(phrase) <= 12:
            return "문구 결합형 멈춰있는 이모티콘 우선"
        return "정지형+시리즈 확장 후보"

    def _name_join(self, names: list[str]) -> str:
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]}와 {names[1]}"
        return f"{names[0]}·{names[1]} 외 {len(names)-2}종"
