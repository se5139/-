from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Any


FORMAT_LABELS = {
    "static": "멈춰있는 이모티콘",
    "static_text": "문구 결합형 멈춰있는 이모티콘",
    "animated": "움직이는 이모티콘",
    "animated_text": "움직이는 문구 결합형 이모티콘",
    "big": "큰 이모티콘",
    "series": "시리즈형 캐릭터 확장",
}


@dataclass
class PipelineStep:
    order: int
    phase: str
    recommended_format: str
    goal: str
    deliverable: str
    expression_count: int
    risk_check: str
    success_signal: str
    next_action: str
    target_window: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelinePlan:
    character_name: str
    primary_format: str
    secondary_format: str
    top_keywords: list[str]
    priority_phrases: list[str]
    positioning: str
    steps: list[PipelineStep]
    series_candidates: list[dict]
    kpi_template: dict
    summary: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["steps"] = [s.to_dict() for s in self.steps]
        return data


class ProfitPipelinePlanner:
    """캐릭터 1종을 여러 포맷으로 확장하는 수익 파이프라인 설계기.

    카카오 승인/수익을 예측하거나 보장하지 않고, 사용자가 만든 프로젝트 데이터를 바탕으로
    어떤 포맷을 먼저 만들고 어떤 후속 세트를 준비할지 정리합니다.
    """

    def build(
        self,
        character_name: str,
        profile: dict | None,
        trend_result: dict | None,
        format_scores: list[dict] | None,
        expressions: list[dict] | None,
        desired_monthly_submissions: int = 1,
    ) -> PipelinePlan:
        character_name = character_name.strip() or self._fallback_character_name(profile)
        scores = sorted(format_scores or [], key=lambda x: x.get("score", 0), reverse=True)
        primary_key = scores[0].get("format_key", scores[0].get("key", "static_text")) if scores else "static_text"
        secondary_key = scores[1].get("format_key", scores[1].get("key", "animated_text")) if len(scores) > 1 else "animated_text"
        primary_label = scores[0].get("label", FORMAT_LABELS.get(primary_key, primary_key)) if scores else FORMAT_LABELS[primary_key]
        secondary_label = scores[1].get("label", FORMAT_LABELS.get(secondary_key, secondary_key)) if len(scores) > 1 else FORMAT_LABELS[secondary_key]

        top_keywords = self._top_keywords(trend_result, profile)
        priority_phrases = self._priority_phrases(trend_result, expressions)
        expression_count = len(expressions or [])
        start = date.today()
        monthly = max(1, min(int(desired_monthly_submissions or 1), 4))
        cadence = max(7, 30 // monthly)

        steps = [
            PipelineStep(
                order=1,
                phase="1차 테스트 상품",
                recommended_format=primary_label,
                goal="제작 난이도와 실사용성을 균형 있게 맞춘 첫 제출 후보를 만든다.",
                deliverable=f"{primary_label} 제출 준비 ZIP + 체크리스트 + 저작권 방어 리포트",
                expression_count=self._target_count(primary_key, expression_count),
                risk_check="기존 캐릭터명/유명 IP/AI 완성본/폰트 라이선스/문구 복제 위험을 먼저 제거",
                success_signal="심사 통과 또는 반려 사유가 구체적으로 확보되는 것",
                next_action="반려 시 문구·표정·포맷 중 어떤 문제가 큰지 기록하고 예비 표현으로 교체",
                target_window=f"{start.isoformat()} ~ {(start + timedelta(days=cadence)).isoformat()}",
            ),
            PipelineStep(
                order=2,
                phase="2차 확장 상품",
                recommended_format=secondary_label,
                goal="1차 캐릭터의 강점을 유지하면서 더 강한 리액션 또는 문구 움직임을 붙인다.",
                deliverable=f"{secondary_label} 패키지 + 움직임/문구 동기화 샘플",
                expression_count=self._target_count(secondary_key, expression_count),
                risk_check="움직임이 문구와 따로 놀지 않는지, 작은 화면에서 글자가 읽히는지 검사",
                success_signal="1차 대비 캐릭터성이 더 분명해지고 재사용 문구가 늘어나는 것",
                next_action="가장 반응 좋은 문구군을 후속 시리즈의 중심 문구로 고정",
                target_window=f"{(start + timedelta(days=cadence + 1)).isoformat()} ~ {(start + timedelta(days=cadence * 2)).isoformat()}",
            ),
            PipelineStep(
                order=3,
                phase="3차 시리즈 후보",
                recommended_format="시리즈형 캐릭터 확장",
                goal="같은 캐릭터를 주제별 2탄/3탄으로 확장할 수 있는지 판단한다.",
                deliverable="시리즈 후보 5개 + 각 후보별 표현 24~32개 초안",
                expression_count=min(max(expression_count // 2, 24), 40),
                risk_check="1탄과 너무 중복되지 않으면서도 캐릭터 정체성이 유지되는지 검사",
                success_signal="세계관·말투·대표 동작이 반복 가능한 구조로 정리되는 것",
                next_action="심사/판매/사용자 반응 기록이 가장 좋은 테마부터 제작",
                target_window=f"{(start + timedelta(days=cadence * 2 + 1)).isoformat()} ~ {(start + timedelta(days=cadence * 3)).isoformat()}",
            ),
        ]

        series_candidates = self._series_candidates(character_name, top_keywords, priority_phrases)
        positioning = self._positioning(character_name, primary_label, top_keywords)
        summary = (
            f"'{character_name}'는 1차로 '{primary_label}' 포맷을 우선 제작하고, "
            f"2차로 '{secondary_label}' 확장을 준비하는 흐름이 적합합니다. "
            "이 계획은 승인/수익 보장이 아니라 제작 우선순위와 반복 개선용 로드맵입니다."
        )

        return PipelinePlan(
            character_name=character_name,
            primary_format=primary_label,
            secondary_format=secondary_label,
            top_keywords=top_keywords,
            priority_phrases=priority_phrases,
            positioning=positioning,
            steps=steps,
            series_candidates=series_candidates,
            kpi_template=self._kpi_template(),
            summary=summary,
        )

    def _fallback_character_name(self, profile: dict | None) -> str:
        if profile:
            bases = profile.get("bases") or []
            if bases:
                return f"{bases[0]} 캐릭터"
        return "새 캐릭터"

    def _top_keywords(self, trend_result: dict | None, profile: dict | None) -> list[str]:
        keywords: list[str] = []
        if trend_result:
            for item in trend_result.get("top_keywords", [])[:8]:
                if isinstance(item, (list, tuple)) and item:
                    keywords.append(str(item[0]))
                elif isinstance(item, dict):
                    keywords.append(str(item.get("keyword", "")))
        if profile:
            keywords += [str(x) for x in profile.get("targets", [])[:3]]
            keywords += [str(x) for x in profile.get("emotions", [])[:3]]
        cleaned = []
        for k in keywords:
            k = k.strip()
            if k and k not in cleaned:
                cleaned.append(k)
        return cleaned[:10] or ["일상", "답장", "공감", "감정표현"]

    def _priority_phrases(self, trend_result: dict | None, expressions: list[dict] | None) -> list[str]:
        phrases = []
        if trend_result:
            phrases += [str(x) for x in trend_result.get("suggested_phrases", [])]
        for item in expressions or []:
            phrase = str(item.get("phrase", "")).strip()
            category = str(item.get("category", ""))
            if phrase and ("기본" in category or "직장" in category or len(phrases) < 8):
                phrases.append(phrase)
        cleaned = []
        for p in phrases:
            if p and p not in cleaned:
                cleaned.append(p)
        return cleaned[:12] or ["넵", "확인했습니다", "감사합니다", "죄송합니다"]

    def _target_count(self, format_key: str, expression_count: int) -> int:
        defaults = {
            "static": 32,
            "static_text": 32,
            "animated": 24,
            "animated_text": 24,
            "big": 16,
            "series": 24,
        }
        return min(defaults.get(format_key, 24), max(expression_count, defaults.get(format_key, 24)))

    def _series_candidates(self, character_name: str, keywords: list[str], phrases: list[str]) -> list[dict]:
        themes = [
            ("직장/업무편", ["넵", "확인", "퇴근", "죄송", "회의"]),
            ("피곤/무기력편", ["기절", "살려", "월요일", "번아웃", "잠시만"]),
            ("감사/사과편", ["감사", "죄송", "부탁", "고맙", "미안"]),
            ("친구 리액션편", ["대박", "인정", "가자", "뭐해", "웃김"]),
            ("시즌/특별편", ["주말", "명절", "생일", "연말", "새해"]),
        ]
        joined = " ".join(keywords + phrases)
        result = []
        for idx, (theme, keys) in enumerate(themes, start=1):
            score = 60 + min(30, sum(6 for k in keys if k in joined))
            result.append({
                "순위": idx,
                "시리즈 후보": f"{character_name} {theme}",
                "추천 점수": score,
                "핵심 문구 방향": ", ".join(keys[:4]),
                "제작 메모": "1탄과 겹치는 문구는 줄이고 캐릭터 고유 말투를 유지",
            })
        return sorted(result, key=lambda x: x["추천 점수"], reverse=True)

    def _positioning(self, character_name: str, primary_format: str, keywords: list[str]) -> str:
        return (
            f"{character_name}는 '{', '.join(keywords[:4])}' 흐름을 바탕으로, "
            f"첫 상품에서는 {primary_format} 중심의 짧고 반복 사용 가능한 대화형 포지션을 잡는 것이 좋습니다."
        )

    def _kpi_template(self) -> dict[str, Any]:
        return {
            "심사 상태": ["준비", "제출", "승인", "반려", "수정 후 재제출", "출시"],
            "기록할 수치": ["제출일", "심사 결과일", "반려 사유", "수정 항목", "판매/정산 메모", "사용자 반응 메모"],
            "다음 판단 기준": [
                "반려 사유가 규격이면 패키지/용량/크기 수정",
                "반려 사유가 상품성이면 문구/표정/콘셉트 차별화 강화",
                "승인되면 같은 캐릭터의 2차 포맷과 시리즈 후보를 준비",
            ],
        }
