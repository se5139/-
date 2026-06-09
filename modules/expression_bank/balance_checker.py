from __future__ import annotations

from collections import Counter

from modules.expression_bank.expression_generator import ExpressionItem


class ExpressionBalanceChecker:
    def check(self, items: list[ExpressionItem]) -> dict:
        categories = Counter(item.category for item in items)
        formats = Counter(item.recommended_format for item in items)
        avg_usage = round(sum(item.usage_score for item in items) / max(len(items), 1), 1)
        warnings = []
        if categories.get("기본 답장", 0) < len(items) * 0.15:
            warnings.append("기본 답장형 표현이 부족합니다.")
        if categories.get("감정 리액션", 0) < len(items) * 0.12:
            warnings.append("감정 리액션 표현이 부족합니다.")
        if avg_usage < 70:
            warnings.append("실사용성 평균 점수가 낮습니다. 짧은 답장형 문구를 보강하세요.")
        return {
            "category_counts": dict(categories),
            "format_counts": dict(formats),
            "average_usage_score": avg_usage,
            "warnings": warnings,
        }
