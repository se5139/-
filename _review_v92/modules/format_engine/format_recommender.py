from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import Counter

from modules.constants import FORMAT_LABELS, PLANNING_COUNTS
from modules.expression_bank.expression_generator import ExpressionItem


@dataclass
class FormatScore:
    key: str
    label: str
    score: int
    planning_count: int
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


class FormatRecommender:
    def score(self, concept_text: str, expressions: list[ExpressionItem]) -> list[FormatScore]:
        text = concept_text or ""
        fmt_counts = Counter(e.recommended_format for e in expressions)
        avg_usage = sum(e.usage_score for e in expressions) / max(len(expressions), 1)
        long_phrase_ratio = sum(1 for e in expressions if len(e.phrase) >= 9) / max(len(expressions), 1)
        motion_words = ["구겨", "녹", "튀", "흔들", "점프", "움직", "도장", "작아", "커짐", "싹"]
        motion_fit = 1 if any(w in text for w in motion_words) else 0
        text_fit = 1 if any(w in text for w in ["문구", "넵", "확인", "직장", "답장", "말투", "공손"]) else 0
        series_fit = 1 if any(w in text for w in ["세계관", "직장인", "커플", "시리즈", "캐릭터"]) else 0

        scores = {
            "static": int(55 + avg_usage * 0.25 + (1 - long_phrase_ratio) * 10),
            "static_text": int(60 + avg_usage * 0.30 + text_fit * 10 + long_phrase_ratio * 10),
            "animated": int(50 + fmt_counts.get("animated", 0) * 1.2 + motion_fit * 15),
            "animated_text": int(60 + fmt_counts.get("animated_text", 0) * 1.1 + text_fit * 8 + motion_fit * 10),
            "big": int(45 + fmt_counts.get("animated", 0) * 0.5 + (1 if "리액션" in text else 0) * 15),
            "series": int(50 + series_fit * 25 + avg_usage * 0.15),
        }
        result = []
        for key, value in scores.items():
            result.append(
                FormatScore(
                    key=key,
                    label=FORMAT_LABELS[key],
                    score=min(100, max(0, value)),
                    planning_count=PLANNING_COUNTS[key],
                    reason=self._reason(key, text_fit, motion_fit, avg_usage),
                )
            )
        return sorted(result, key=lambda x: x.score, reverse=True)

    def _reason(self, key: str, text_fit: int, motion_fit: int, avg_usage: float) -> str:
        if key == "animated_text":
            return "문구 사용성과 움직임 표현을 동시에 살릴 수 있는 포맷입니다."
        if key == "static_text":
            return "짧은 답장 문구와 캐릭터 표정이 핵심일 때 제작 효율이 높습니다."
        if key == "animated":
            return "문구보다 동작 자체가 웃기거나 감정 전달력이 강할 때 적합합니다."
        if key == "static":
            return "기본 표현 세트를 빠르게 만들고 심사 반응을 보기 좋은 포맷입니다."
        if key == "big":
            return "표정·몸짓 리액션이 큰 캐릭터일 때 후보로 검토합니다."
        return "세계관과 말투가 확장 가능하면 후속 세트로 수익화를 넓힐 수 있습니다."
