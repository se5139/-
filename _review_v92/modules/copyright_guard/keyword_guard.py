from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterable, List

from modules.constants import FORBIDDEN_STYLE_KEYWORDS, AI_RISK_KEYWORDS


@dataclass
class GuardFinding:
    level: str
    keyword: str
    message: str
    suggestion: str

    def to_dict(self) -> dict:
        return asdict(self)


class KeywordGuard:
    """저작권/상표권/AI 정책 위험 키워드 1차 방어기.

    법적 판정기가 아니라, 제작 전에 위험한 방향을 피하도록 돕는 로컬 검사기입니다.
    """

    def __init__(self, forbidden_keywords: Iterable[str] | None = None, ai_keywords: Iterable[str] | None = None) -> None:
        self.forbidden_keywords = list(forbidden_keywords or FORBIDDEN_STYLE_KEYWORDS)
        self.ai_keywords = list(ai_keywords or AI_RISK_KEYWORDS)

    def scan(self, text: str) -> list[GuardFinding]:
        normalized = (text or "").lower().strip()
        findings: list[GuardFinding] = []
        if not normalized:
            return findings

        for keyword in self.forbidden_keywords:
            if keyword.lower() in normalized:
                findings.append(
                    GuardFinding(
                        level="위험",
                        keyword=keyword,
                        message="기존 유명 캐릭터/브랜드/스타일을 연상시킬 수 있는 표현입니다.",
                        suggestion="유명 캐릭터명·브랜드명 대신 본체, 성격, 세계관, 말투를 새로 조합하세요.",
                    )
                )

        for keyword in self.ai_keywords:
            if keyword.lower() in normalized:
                findings.append(
                    GuardFinding(
                        level="주의",
                        keyword=keyword,
                        message="생성형 AI 완성 이미지 제출은 플랫폼 정책상 제한될 수 있습니다.",
                        suggestion="AI는 아이디어/문구/분석 보조로만 쓰고, 제출 이미지는 직접 제작 레이어 기반으로 관리하세요.",
                    )
                )

        if re.search(r"(느낌|스타일|비슷|따라|닮게|같이)", normalized):
            findings.append(
                GuardFinding(
                    level="주의",
                    keyword="유사 표현 요청",
                    message="특정 스타일 모방 방향으로 해석될 수 있는 문구가 있습니다.",
                    suggestion="'누구 느낌' 대신 '둥근 실루엣, 무표정, 짧은 극존칭'처럼 추상 특징으로 바꾸세요.",
                )
            )
        return findings

    def risk_score(self, text: str) -> int:
        findings = self.scan(text)
        score = 0
        for finding in findings:
            score += 25 if finding.level == "위험" else 12
        return min(100, score)
