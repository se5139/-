from __future__ import annotations

from dataclasses import dataclass, asdict

from modules.constants import DEFAULT_CHARACTER_BASES, TARGET_GROUPS, CORE_EMOTIONS
from modules.copyright_guard.keyword_guard import KeywordGuard


@dataclass
class KeywordProfile:
    raw_text: str
    bases: list[str]
    targets: list[str]
    emotions: list[str]
    tone: list[str]
    risk_score: int
    risk_findings: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


class KeywordAnalyzer:
    def __init__(self) -> None:
        self.guard = KeywordGuard()
        self.tone_words = ["공손", "하찮", "무표정", "피곤", "귀여", "소심", "뻔뻔", "짧은", "극존칭", "밈", "직설", "따뜻"]

    def analyze(self, text: str) -> KeywordProfile:
        normalized = text or ""
        bases = [b for b in DEFAULT_CHARACTER_BASES if b in normalized]
        targets = [t for t in TARGET_GROUPS if t in normalized]
        emotions = [e for e in CORE_EMOTIONS if e in normalized]
        tone = [w for w in self.tone_words if w in normalized]

        if not bases:
            # 키워드가 명확하지 않으면 독창성 후보가 넓은 사물형을 기본 추천
            bases = ["메모지", "감자", "돌멩이"]
        if not targets:
            targets = ["직장인"] if any(x in normalized for x in ["회사", "업무", "퇴근", "넵", "확인"]) else ["친구"]
        if not emotions:
            emotions = ["확인", "감사", "피곤", "당황"]
        if not tone:
            tone = ["짧은", "공손"]

        findings = self.guard.scan(normalized)
        return KeywordProfile(
            raw_text=normalized,
            bases=bases,
            targets=targets,
            emotions=emotions,
            tone=tone,
            risk_score=self.guard.risk_score(normalized),
            risk_findings=[f.to_dict() for f in findings],
        )
