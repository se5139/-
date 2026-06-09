from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import cycle

from modules.constants import PHRASE_GROUPS, CORE_EMOTIONS


@dataclass
class ExpressionItem:
    no: int
    category: str
    phrase: str
    emotion: str
    recommended_motion: str
    recommended_format: str
    usage_score: int
    originality_hook: str

    def to_dict(self) -> dict:
        return asdict(self)


class ExpressionGenerator:
    MOTIONS = {
        "인사": "손 흔들기/살짝 튀기",
        "감사": "꾸벅 숙이기 + 문구 부드럽게 등장",
        "사과": "작아짐 + 땀방울 + 문구 떨림",
        "확인": "체크 도장 + 문구 쿵 등장",
        "수락": "작게 끄덕임 + 말풍선 팝업",
        "거절": "뒤로 물러남 + 문구 작아짐",
        "부탁": "두 손 모으기 + 말풍선 흔들림",
        "응원": "통통 튀기 + 반짝 효과",
        "축하": "폭죽/하트 효과",
        "피곤": "녹아내림/구겨짐 + 글자 축 처짐",
        "당황": "부들부들 + 땀방울",
        "분노": "미세한 떨림 + 효과선",
        "슬픔": "눈물 방울 + 문구 천천히 등장",
        "기쁨": "점프 + 별 효과",
        "민망": "작아짐 + 볼 빨개짐",
        "기다림": "점 3개 순차 등장",
        "퇴근": "몸이 펴짐/탈출 움직임",
        "출근": "몸이 접힘/느린 등장",
    }

    def generate(self, concept_name: str, target_count: int = 80) -> list[ExpressionItem]:
        items: list[ExpressionItem] = []
        emotions = cycle(CORE_EMOTIONS)
        phrases = []
        for category, group in PHRASE_GROUPS.items():
            for phrase in group:
                phrases.append((category, phrase))
        phrase_cycle = cycle(phrases)

        for idx in range(1, target_count + 1):
            category, phrase = next(phrase_cycle)
            emotion = next(emotions)
            motion = self.MOTIONS.get(emotion, "작게 튀기")
            fmt = self._recommend_format(phrase, motion)
            score = self._usage_score(category, phrase)
            items.append(
                ExpressionItem(
                    no=idx,
                    category=category,
                    phrase=phrase,
                    emotion=emotion,
                    recommended_motion=motion,
                    recommended_format=fmt,
                    usage_score=score,
                    originality_hook=f"{concept_name}의 고유 동작과 말투로 변형 필요",
                )
            )
        return items

    def _usage_score(self, category: str, phrase: str) -> int:
        score = 60
        if category in ["기본 답장", "감사/사과", "직장/일상"]:
            score += 20
        if len(phrase) <= 8:
            score += 10
        if any(k in phrase for k in ["넵", "확인", "감사", "죄송", "퇴근", "괜찮"]):
            score += 10
        return min(score, 100)

    def _recommend_format(self, phrase: str, motion: str) -> str:
        if any(k in phrase for k in ["확인", "죄송", "퇴근", "살려", "접수", "구겨", "넵"]):
            return "animated_text"
        if len(phrase) >= 9:
            return "static_text"
        if any(k in motion for k in ["점프", "폭죽", "부들", "녹아"]):
            return "animated"
        return "static_text"
