from __future__ import annotations

from modules.copyright_guard.keyword_guard import KeywordGuard


class OriginalityScorer:
    def __init__(self) -> None:
        self.guard = KeywordGuard()

    def score(self, concept_text: str, base_count: int, has_worldview: bool = True) -> dict:
        risk = self.guard.risk_score(concept_text)
        score = 65
        if base_count >= 2:
            score += 8
        if has_worldview:
            score += 12
        if any(w in concept_text for w in ["말투", "세계관", "시그니처", "움직임", "문구"]):
            score += 8
        score -= int(risk * 0.45)
        score = max(0, min(100, score))
        return {
            "originality_score": score,
            "risk_score": risk,
            "summary": self._summary(score, risk),
        }

    def _summary(self, score: int, risk: int) -> str:
        if risk >= 50:
            return "유명 캐릭터/스타일 연상 위험이 큽니다. 콘셉트 변환이 필요합니다."
        if score >= 80:
            return "독창성 후보가 강합니다. 문구와 움직임까지 고유화하면 좋습니다."
        if score >= 60:
            return "기본 방향은 가능하지만 외형·말투·시그니처 동작 차별화가 필요합니다."
        return "차별성이 약합니다. 본체, 세계관, 대표 움직임을 다시 조합하세요."
