from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass
class ExpressionFacePlan:
    category: str
    focus_character: str
    face_label: str
    eye_style: str
    brow_style: str
    mouth_style: str
    body_motion: str
    text_motion: str
    effects: List[str]
    intensity: int
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExpressionFaceEngine:
    """표현 문구/분류/캐릭터 성격을 기반으로 눈·입·효과·동작 계획을 자동 배정합니다.

    목표는 최종 세트 선별 단계에서 표현만 고르는 것이 아니라,
    각 표현에 맞는 캐릭터 표정과 문구 움직임까지 함께 묶어 제작 초안을 만드는 것입니다.
    """

    CATEGORY_MAP: Dict[str, Dict[str, Any]] = {
        "인사": {"face":"밝은 인사", "eye":"normal", "brow":"soft", "mouth":"smile", "body":"손 흔들기/살짝 튐", "text":"톡 튀어나오기", "effects":["wave"], "intensity":55},
        "확인": {"face":"집중 확인", "eye":"focused", "brow":"straight", "mouth":"small_smile", "body":"작게 끄덕임", "text":"도장처럼 찍힘", "effects":["check"], "intensity":62},
        "감사": {"face":"고마운 미소", "eye":"soft_closed", "brow":"soft", "mouth":"warm_smile", "body":"작게 꾸벅", "text":"천천히 나타남", "effects":["heart","sparkle"], "intensity":70},
        "사과": {"face":"미안한 표정", "eye":"down", "brow":"worried", "mouth":"sad", "body":"몸이 작아지며 꾸벅", "text":"작게 떨림", "effects":["sweat"], "intensity":74},
        "응원": {"face":"힘내는 표정", "eye":"bright", "brow":"up", "mouth":"big_smile", "body":"통통 튐", "text":"위로 올라오며 등장", "effects":["sparkle"], "intensity":72},
        "피곤": {"face":"피곤한 반눈", "eye":"half", "brow":"flat", "mouth":"flat", "body":"아래로 처짐", "text":"축 처짐", "effects":["zzz"], "intensity":68},
        "분노": {"face":"부들부들 화남", "eye":"sharp", "brow":"angry", "mouth":"zigzag", "body":"좌우로 떨림", "text":"부들부들 흔들림", "effects":["anger"], "intensity":82},
        "당황": {"face":"놀람/당황", "eye":"wide", "brow":"raised", "mouth":"open", "body":"짧게 움찔", "text":"툭 튀어나옴", "effects":["sweat","question"], "intensity":76},
        "축하": {"face":"활짝 축하", "eye":"happy", "brow":"up", "mouth":"big_smile", "body":"점프", "text":"반짝이며 등장", "effects":["confetti","sparkle"], "intensity":80},
        "부탁": {"face":"조심스러운 부탁", "eye":"puppy", "brow":"worried", "mouth":"small_smile", "body":"두 손 모으기", "text":"부드럽게 등장", "effects":["small_heart"], "intensity":66},
        "퇴근": {"face":"영혼 퇴근", "eye":"half", "brow":"flat", "mouth":"relieved", "body":"화면 밖으로 이동", "text":"따라가듯 이동", "effects":["speed"], "intensity":77},
        "잘자": {"face":"잠든 표정", "eye":"closed", "brow":"soft", "mouth":"tiny_smile", "body":"살짝 흔들리며 잠듦", "text":"천천히 페이드인", "effects":["zzz","moon"], "intensity":58},
        "거절": {"face":"곤란한 거절", "eye":"side", "brow":"worried", "mouth":"awkward", "body":"살짝 뒤로 물러남", "text":"작게 등장", "effects":["sweat"], "intensity":64},
        "기다림": {"face":"기다리는 표정", "eye":"patient", "brow":"soft", "mouth":"small_smile", "body":"좌우로 작게 흔들림", "text":"점 세 개 순차 등장", "effects":["dots"], "intensity":55},
        "민망": {"face":"민망한 홍조", "eye":"side", "brow":"soft", "mouth":"awkward", "body":"몸이 작아짐", "text":"작게 떨림", "effects":["blush","sweat"], "intensity":66},
        "시그니처": {"face":"캐릭터 대표 표정", "eye":"personality", "brow":"personality", "mouth":"personality", "body":"대표 동작", "text":"시그니처 등장", "effects":["signature"], "intensity":73},
    }

    PHRASE_HINTS = [
        (["고마", "감사", "땡큐"], "감사"),
        (["미안", "죄송", "사과"], "사과"),
        (["확인", "봤", "접수", "완료"], "확인"),
        (["축하", "최고", "대박"], "축하"),
        (["피곤", "졸", "쉬", "눕", "살려"], "피곤"),
        (["화", "부들", "건드리지"], "분노"),
        (["어...", "당황", "괜찮을까요", "뭐냐"], "당황"),
        (["부탁", "도와"], "부탁"),
        (["퇴근", "수고"], "퇴근"),
        (["잘자", "꿈"], "잘자"),
    ]

    def build_plan(self, row: Dict[str, Any], specs: List[Any], format_key: str = "static_text") -> Dict[str, Any]:
        phrase = str(row.get("phrase", ""))
        category = str(row.get("category", "시그니처")) or "시그니처"
        for hints, cat in self.PHRASE_HINTS:
            if any(h in phrase for h in hints):
                category = cat
                break
        base = dict(self.CATEGORY_MAP.get(category, self.CATEGORY_MAP["시그니처"]))
        focus = str(row.get("character_focus", ""))
        if not focus and specs:
            focus = str(getattr(specs[0], "name", "캐릭터"))
        personality = " ".join([str(getattr(s, "personality", "")) + " " + str(getattr(s, "tone", "")) for s in specs if str(getattr(s, "name", "")) == focus])
        if category == "시그니처":
            if any(k in personality for k in ["까칠", "투덜", "시크"]):
                base.update({"face":"까칠한 시그니처", "eye":"sharp", "brow":"angry", "mouth":"smirk", "body":"팔짱/고개 돌림", "text":"짧게 툭 등장", "effects":["signature","small_anger"], "intensity":76})
            elif any(k in personality for k in ["온순", "다정", "부드", "위로"]):
                base.update({"face":"다정한 시그니처", "eye":"soft_closed", "brow":"soft", "mouth":"warm_smile", "body":"작게 다가옴", "text":"부드럽게 나타남", "effects":["heart","sparkle"], "intensity":70})
            elif any(k in personality for k in ["피곤", "무기력", "업무"]):
                base.update({"face":"피곤한 시그니처", "eye":"half", "brow":"flat", "mouth":"flat", "body":"구겨짐/처짐", "text":"아래로 처짐", "effects":["zzz"], "intensity":68})
        if "animated" in format_key:
            base["intensity"] = min(95, int(base.get("intensity", 60)) + 8)
        plan = ExpressionFacePlan(
            category=category,
            focus_character=focus,
            face_label=base["face"],
            eye_style=base["eye"],
            brow_style=base["brow"],
            mouth_style=base["mouth"],
            body_motion=base["body"],
            text_motion=base["text"],
            effects=list(base.get("effects", [])),
            intensity=int(base.get("intensity", 60)),
            reason=f"분류 '{category}'와 문구 '{phrase[:18]}' 기준으로 표정·동작·문구 움직임 자동 배정",
        )
        return plan.to_dict()

    def summary(self, plan: Dict[str, Any]) -> str:
        effects = ",".join(plan.get("effects", [])) or "효과 없음"
        return f"{plan.get('face_label')} · 눈:{plan.get('eye_style')} · 입:{plan.get('mouth_style')} · 효과:{effects}"
