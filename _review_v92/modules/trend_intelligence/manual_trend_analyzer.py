from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
import re


@dataclass
class TrendResult:
    top_keywords: list[tuple[str, int]]
    suggested_targets: list[str]
    suggested_phrases: list[str]
    suggested_formats: list[str]
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


class ManualTrendAnalyzer:
    """무료 API 연동 전에도 쓸 수 있는 30일 키워드/댓글 수동 입력 분석기."""

    STOPWORDS = {"그리고", "그런데", "이모티콘", "캐릭터", "영상", "댓글", "ㅋㅋ", "ㅎㅎ", "입니다", "있어요", "없어요"}
    FORMAT_RULES = {
        "animated_text": ["넵", "확인", "죄송", "퇴근", "살려", "피곤", "월요", "번아웃"],
        "static_text": ["감사", "축하", "잘자", "괜찮", "부탁", "알겠"],
        "animated": ["웃긴", "리액션", "점프", "화남", "눈물", "당황", "놀람"],
        "big": ["대박", "축하", "폭발", "강한", "큰", "리액션"],
    }

    def analyze(self, raw_text: str) -> TrendResult:
        tokens = self._tokenize(raw_text)
        counts = Counter(t for t in tokens if t not in self.STOPWORDS and len(t) >= 2)
        top = counts.most_common(20)
        joined = " ".join(tokens)
        targets = self._targets(joined)
        phrases = self._phrases(joined)
        formats = self._formats(joined)
        summary = self._summary(top, formats)
        return TrendResult(top, targets, phrases, formats, summary)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[가-힣A-Za-z0-9]+", text or "")

    def _targets(self, text: str) -> list[str]:
        mapping = {
            "직장인": ["회사", "퇴근", "출근", "업무", "넵", "확인", "월요", "야근"],
            "커플": ["사랑", "보고", "데이트", "삐짐", "질투", "잘자"],
            "가족": ["엄마", "아빠", "밥", "조심", "집", "가족"],
            "친구": ["대박", "인정", "가자", "뭐해", "웃긴"],
        }
        scored = []
        for target, keys in mapping.items():
            score = sum(1 for k in keys if k in text)
            if score:
                scored.append((target, score))
        return [x for x, _ in sorted(scored, key=lambda p: p[1], reverse=True)] or ["일상 대화"]

    def _phrases(self, text: str) -> list[str]:
        candidates = ["넵", "확인했습니다", "감사합니다", "죄송합니다", "퇴근하고 싶습니다", "살려주세요", "괜찮아요", "잘자요", "축하해요", "파이팅"]
        scored = []
        for phrase in candidates:
            base = phrase[:2]
            scored.append((phrase, text.count(base)))
        return [p for p, _ in sorted(scored, key=lambda x: x[1], reverse=True)[:8]]

    def _formats(self, text: str) -> list[str]:
        scored = []
        for fmt, keys in self.FORMAT_RULES.items():
            score = sum(1 for k in keys if k in text)
            if score:
                scored.append((fmt, score))
        return [f for f, _ in sorted(scored, key=lambda x: x[1], reverse=True)] or ["static_text", "animated_text"]

    def _summary(self, top: list[tuple[str, int]], formats: list[str]) -> str:
        keyword_text = ", ".join(k for k, _ in top[:5]) if top else "입력 데이터 부족"
        return f"최근 30일 입력 데이터에서 '{keyword_text}' 계열 키워드가 두드러집니다. 우선 포맷 후보는 {', '.join(formats[:3])}입니다."
