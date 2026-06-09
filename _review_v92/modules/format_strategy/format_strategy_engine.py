from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass
class FormatStrategyReport:
    project_name: str
    character_concept: str
    data_stage: str
    primary_format: dict[str, Any]
    format_scores: list[dict[str, Any]]
    expansion_roadmap: list[dict[str, Any]]
    decision_rules: list[str]
    data_requirements: list[dict[str, Any]]
    series_candidates: list[dict[str, Any]]
    hold_formats: list[dict[str, Any]]
    next_actions: list[str]
    safety_notes: list[str]
    files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FormatStrategyEngine:
    """1차 포맷 추천 + 단계별 확장 전략 엔진.

    핵심 원칙:
    - 처음부터 모든 포맷을 제작하지 않습니다.
    - 캐릭터 콘셉트, 문구 사용성, 제작 난이도, 심사 리스크, 현재 데이터 수준을 기준으로 1차 포맷 1개만 추천합니다.
    - 미니/큰/움직이는 포맷은 선택형 확장 후보로 보관하고, 심사/품질/판매/반응 데이터가 쌓인 뒤 재판단합니다.
    - 모든 판단은 승인/수익 보장이 아니라 제작 우선순위 추천입니다.
    """

    FORMATS = {
        "static_text": {
            "label": "문구 결합형 멈춰있는 이모티콘",
            "count_hint": "32개 중심",
            "strength": "짧은 답장·말투·사용 상황이 강한 캐릭터에 적합",
            "difficulty": 2,
            "review_risk": 2,
        },
        "static": {
            "label": "멈춰있는 이모티콘",
            "count_hint": "32개 중심",
            "strength": "표정·포즈만으로 감정 전달이 명확할 때 적합",
            "difficulty": 2,
            "review_risk": 2,
        },
        "animated_text": {
            "label": "움직이는 문구 결합형 이모티콘",
            "count_hint": "24개 중심",
            "strength": "문구와 캐릭터 동작이 같이 살아날 때 적합",
            "difficulty": 4,
            "review_risk": 3,
        },
        "animated": {
            "label": "움직이는 이모티콘",
            "count_hint": "24개 중심",
            "strength": "동작 자체가 상품 매력일 때 적합",
            "difficulty": 5,
            "review_risk": 4,
        },
        "mini_static": {
            "label": "멈춰있는 미니 이모티콘",
            "count_hint": "42개 중심, 공식 최신 기준 확인 필요",
            "strength": "작고 단순하며 이어붙이기/조합 사용성이 있을 때 적합",
            "difficulty": 3,
            "review_risk": 3,
        },
        "mini_animated": {
            "label": "움직이는 미니 이모티콘",
            "count_hint": "35개 중심, 공식 최신 기준 확인 필요",
            "strength": "작은 조합형 캐릭터에 짧은 움직임을 붙일 때 적합",
            "difficulty": 4,
            "review_risk": 4,
        },
        "big": {
            "label": "큰 이모티콘",
            "count_hint": "16개 중심",
            "strength": "강한 리액션·큰 표정·확대 임팩트가 있을 때 적합",
            "difficulty": 4,
            "review_risk": 3,
        },
        "series": {
            "label": "시리즈 확장",
            "count_hint": "2탄/3탄 기획",
            "strength": "1차 승인/반응 이후 캐릭터성이 검증되면 적합",
            "difficulty": 3,
            "review_risk": 2,
        },
    }

    HIGH_USE_WORDS = ["확인", "넵", "감사", "죄송", "수고", "잘자", "축하", "파이팅", "괜찮", "잠시", "퇴근", "헐", "대박", "좋아"]
    MOTION_WORDS = ["뛰", "흔들", "움직", "박수", "따봉", "꾸벅", "눈물", "부들", "점프", "도장", "자동차", "이동", "통통"]
    MINI_WORDS = ["미니", "작은", "조합", "이어", "하트", "느낌표", "말풍선", "스티커", "단순", "작게"]
    BIG_WORDS = ["큰", "강한", "과장", "폭발", "오열", "대박", "화남", "리액션", "크게"]
    SERIES_WORDS = ["직장", "퇴근", "사투리", "지역", "가족", "친구", "시리즈", "편", "계절", "명절"]

    def build_report(
        self,
        output_dir: str | Path,
        project_name: str,
        character_concept: str,
        phrase_examples: str = "",
        personality: str = "",
        motion_strength: int = 2,
        expression_variety_score: int = 70,
        chat_readability_score: int = 75,
        quality_score: int = 75,
        review_status: str = "아직 제출 전",
        approval_count: int = 0,
        rejection_count: int = 0,
        sales_signal: str = "아직 데이터 없음",
        user_goal: str = "첫 제출용 1개 포맷 추천",
    ) -> FormatStrategyReport:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        project_name = (project_name or "kakao_emoticon_project").strip()
        concept = (character_concept or "").strip()
        phrase_examples = (phrase_examples or "").strip()
        personality = (personality or "").strip()
        text_blob = " ".join([concept, phrase_examples, personality, sales_signal, user_goal])

        data_stage = self._data_stage(review_status, approval_count, rejection_count, sales_signal)
        scores = self._score_formats(
            text_blob=text_blob,
            motion_strength=motion_strength,
            expression_variety_score=expression_variety_score,
            chat_readability_score=chat_readability_score,
            quality_score=quality_score,
            approval_count=approval_count,
            rejection_count=rejection_count,
            data_stage=data_stage,
        )
        primary = scores[0]
        roadmap = self._expansion_roadmap(primary, scores, data_stage, approval_count, rejection_count, sales_signal, text_blob)
        data_requirements = self._data_requirements(primary, roadmap)
        series_candidates = self._series_candidates(text_blob, primary["format_key"])
        hold_formats = self._hold_formats(scores, primary["format_key"], data_stage)
        decision_rules = self._decision_rules()
        next_actions = self._next_actions(primary, data_stage)
        safety_notes = self._safety_notes()

        data = {
            "project_name": project_name,
            "character_concept": concept,
            "data_stage": data_stage,
            "primary_format": primary,
            "format_scores": scores,
            "expansion_roadmap": roadmap,
            "decision_rules": decision_rules,
            "data_requirements": data_requirements,
            "series_candidates": series_candidates,
            "hold_formats": hold_formats,
            "next_actions": next_actions,
            "safety_notes": safety_notes,
        }
        files = self._write_files(out / self._safe_slug(project_name), data)
        return FormatStrategyReport(files=files, **data)

    def _data_stage(self, review_status: str, approval_count: int, rejection_count: int, sales_signal: str) -> str:
        if approval_count <= 0 and rejection_count <= 0 and "출시" not in review_status and "판매" not in sales_signal:
            return "초기 기획/첫 제출 전"
        if approval_count <= 0 and rejection_count > 0:
            return "반려 데이터 수집 단계"
        if approval_count >= 1 and "판매" not in sales_signal and "반응" not in sales_signal:
            return "승인 후 반응 관찰 단계"
        if approval_count >= 1 and any(x in sales_signal for x in ["좋", "양호", "판매", "사용", "매출", "반응"]):
            return "확장 검토 단계"
        return "데이터 보강 필요 단계"

    def _score_formats(self, text_blob: str, motion_strength: int, expression_variety_score: int, chat_readability_score: int, quality_score: int, approval_count: int, rejection_count: int, data_stage: str) -> list[dict[str, Any]]:
        scores: list[dict[str, Any]] = []
        text = text_blob.lower()
        high_use = sum(1 for w in self.HIGH_USE_WORDS if w in text_blob)
        motion_hits = sum(1 for w in self.MOTION_WORDS if w in text_blob)
        mini_hits = sum(1 for w in self.MINI_WORDS if w in text_blob)
        big_hits = sum(1 for w in self.BIG_WORDS if w in text_blob)
        series_hits = sum(1 for w in self.SERIES_WORDS if w in text_blob)
        first_submission_penalty = 10 if data_stage.startswith("초기") else 0
        rejection_penalty = min(12, rejection_count * 3)
        approval_bonus = min(15, approval_count * 5)

        for key, meta in self.FORMATS.items():
            score = 50
            reasons = []
            cautions = []
            if key == "static_text":
                score += 16 + min(14, high_use * 3) + min(10, chat_readability_score // 10)
                reasons += ["짧은 문구·답장형 사용성이 1차 제출에서 검증하기 쉽습니다.", "문구와 말투가 캐릭터성을 보여주는 포맷입니다."]
                if chat_readability_score < 70: cautions.append("문구 가독성 점수를 먼저 높여야 합니다.")
            elif key == "static":
                score += 10 + min(10, expression_variety_score // 12)
                reasons += ["제작 난이도가 낮고 표정/포즈 일관성을 검증하기 좋습니다."]
                if high_use >= 4: score -= 2
            elif key == "animated_text":
                score += min(18, motion_hits * 4) + min(10, motion_strength * 2) + min(8, chat_readability_score // 12)
                score -= 6 if data_stage.startswith("초기") else 0
                reasons += ["문구와 동작이 같이 살아나는 캐릭터라면 2차 확장에 적합합니다."]
                if motion_strength < 3: cautions.append("모션 강도가 낮으면 1차보다 2차 확장 후보가 안전합니다.")
            elif key == "animated":
                score += min(18, motion_hits * 5) + min(10, motion_strength * 2)
                score -= 12 + first_submission_penalty
                reasons += ["동작 자체가 핵심 매력일 때 적합하지만 제작/검수 부담이 큽니다."]
                cautions.append("첫 제출에서 바로 선택하기보다 모션 템플릿 검증 후 추천합니다.")
            elif key == "mini_static":
                score += min(20, mini_hits * 5) + (8 if "단순" in text_blob or "작" in text_blob else 0)
                score -= 5 if data_stage.startswith("초기") else 0
                reasons += ["단순한 소재·이어붙이기·작은 리액션이 강하면 유리합니다."]
                cautions.append("공식 최신 수량/규격 확인 후 별도 제작해야 합니다.")
            elif key == "mini_animated":
                score += min(18, mini_hits * 4) + min(12, motion_hits * 3)
                score -= 10 + first_submission_penalty
                reasons += ["미니 조합성이 확인된 뒤 움직임을 붙이는 2~3차 후보입니다."]
                cautions.append("처음부터 제작하면 수량/프레임/용량 부담이 커질 수 있습니다.")
            elif key == "big":
                score += min(20, big_hits * 5) + min(8, expression_variety_score // 15)
                score -= 8 + first_submission_penalty
                reasons += ["강한 표정·큰 리액션이 캐릭터 핵심일 때 확장 후보입니다."]
                cautions.append("초기에는 캐릭터 인지도/강한 리액션 데이터가 부족할 수 있습니다.")
            elif key == "series":
                score += min(18, series_hits * 4) + approval_bonus
                score -= 14 if approval_count == 0 else 0
                reasons += ["1차 승인·반응 후 가장 안전하게 확장할 수 있는 방향입니다."]
                if approval_count == 0: cautions.append("첫 세트 결과가 쌓인 뒤 시리즈화를 판단해야 합니다.")
            score += approval_bonus
            score -= rejection_penalty if key in ["animated", "mini_animated", "big"] else rejection_penalty // 2
            score += max(-8, min(8, (quality_score - 75) // 3))
            score = max(0, min(100, score - meta["difficulty"] - meta["review_risk"]))
            scores.append({
                "format_key": key,
                "format_label": meta["label"],
                "score": int(score),
                "count_hint": meta["count_hint"],
                "recommended_role": "1차 제작 후보" if key in ["static_text", "static"] else "확장 후보",
                "why": " / ".join(reasons[:3]),
                "caution": " / ".join(cautions) if cautions else "특이 주의 없음. 단, 공식 최신 기준 재확인 필요.",
                "difficulty": meta["difficulty"],
                "review_risk": meta["review_risk"],
            })
        scores.sort(key=lambda x: x["score"], reverse=True)
        # 초기 단계에서는 모든 포맷 일괄 제작을 막기 위해 고난이도 포맷이 1위여도 보수적으로 재정렬합니다.
        if data_stage.startswith("초기"):
            safe = [s for s in scores if s["format_key"] in ["static_text", "static"]]
            if safe and scores[0]["format_key"] not in ["static_text", "static"]:
                safest = max(safe, key=lambda x: x["score"])
                scores = [safest] + [s for s in scores if s is not safest]
        scores[0]["recommended_role"] = "1차 실제 제작 포맷"
        return scores

    def _expansion_roadmap(self, primary: dict[str, Any], scores: list[dict[str, Any]], data_stage: str, approval_count: int, rejection_count: int, sales_signal: str, text_blob: str) -> list[dict[str, Any]]:
        roadmap = []
        roadmap.append({
            "phase": "1차",
            "timing": "현재",
            "action": f"{primary['format_label']} 1개 포맷만 제작",
            "decision_basis": "초기에는 콘셉트/문구/품질을 먼저 검증하고 나머지 포맷은 보류합니다.",
            "do_not_do": "미니/큰/움직이는 포맷 전체를 동시에 제작하지 않음",
        })
        top_expansions = [s for s in scores if s["format_key"] != primary["format_key"]][:3]
        for idx, candidate in enumerate(top_expansions, start=2):
            condition = self._expansion_condition(candidate["format_key"], approval_count, rejection_count, sales_signal)
            roadmap.append({
                "phase": f"{idx}차",
                "timing": "심사/품질/반응 데이터 축적 후",
                "action": f"{candidate['format_label']} 검토",
                "decision_basis": condition,
                "do_not_do": "근거 없이 자동 제작하지 않고, 누적 데이터 리포트에서 다시 판단",
            })
        return roadmap

    def _expansion_condition(self, key: str, approval_count: int, rejection_count: int, sales_signal: str) -> str:
        base = {
            "animated_text": "문구형 정지 세트의 채팅 사용성·문구 반응이 좋고, 모션 템플릿으로 자연스럽게 확장 가능할 때",
            "animated": "캐릭터의 포즈/행동 자체가 강하고, 프레임/용량 품질검사를 안정적으로 통과할 때",
            "mini_static": "단순 소재·이어붙이기·작은 리액션 문구가 충분히 쌓였을 때",
            "mini_animated": "미니 정지형 조합성이 검증되고, 짧은 2~4컷 모션으로도 의미가 분명할 때",
            "big": "강한 표정/큰 리액션이 반복 사용될 만큼 캐릭터성이 확인될 때",
            "series": "1차 세트 승인 또는 좋은 판매/사용 반응이 기록된 뒤 같은 세계관으로 확장할 때",
            "static_text": "다른 포맷 시도 전 문구 사용성이 더 중요하다고 판단될 때",
            "static": "멘트보다 표정/포즈 중심으로 메시지가 더 잘 전달될 때",
        }.get(key, "누적 데이터가 충분할 때")
        if approval_count == 0:
            return base + " · 현재는 승인 데이터가 없어 보류 권장"
        if rejection_count > approval_count:
            return base + " · 반려 사유 개선 후 재검토"
        if any(x in sales_signal for x in ["좋", "양호", "높", "판매", "매출"]):
            return base + " · 판매/반응 신호가 있으므로 우선 검토 가능"
        return base

    def _data_requirements(self, primary: dict[str, Any], roadmap: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {"data": "심사 결과", "why": "승인/반려 여부에 따라 시리즈·포맷 확장 판단", "required_before_expansion": True},
            {"data": "반려 사유", "why": "문구/캐릭터성/규격/유사성 중 어떤 문제인지 분류", "required_before_expansion": True},
            {"data": "품질검사 점수", "why": "가독성·여백·용량·일관성 문제 확인", "required_before_expansion": True},
            {"data": "채팅창 미리보기 점수", "why": "실사용 화면에서 문구/표정이 읽히는지 확인", "required_before_expansion": True},
            {"data": "사용자 최종 선택 표현", "why": "어떤 문구·감정·포즈가 실제 세트에 남았는지 학습", "required_before_expansion": False},
            {"data": "출시 후 판매/사용 반응 메모", "why": "시리즈/움직이는 버전/미니 전환 근거", "required_before_expansion": False},
        ]

    def _series_candidates(self, text_blob: str, primary_key: str) -> list[dict[str, Any]]:
        candidates = []
        base = [
            ("직장인 답장편", "확인/감사/죄송/수고/퇴근 등 실사용 문구 강화"),
            ("피곤·퇴근편", "반눈·녹아내림·축 처짐 모션으로 공감 리액션 강화"),
            ("사투리 생활편", "지역 말투/생활 표현을 짧은 문구형으로 확장"),
            ("미니 조합편", "하트/느낌표/짧은 리액션을 이어붙이기 구조로 검토"),
            ("움직이는 문구편", "1차 인기 문구에 2~4컷 기본 모션 추가"),
        ]
        if any(w in text_blob for w in ["보리", "쌀", "감자", "고구마", "팽이버섯"]):
            base.insert(0, ("소재 듀오/푸드 캐릭터편", "소재별 성격 차이를 유지하면서 시리즈화"))
        if any(w in text_blob for w in ["충청", "사투리", "유", "슈", "지역"]):
            base.insert(0, ("지역 말투 리액션편", "사용자 경험 사투리를 과장 없이 생활형 문구로 확장"))
        for i, (name, memo) in enumerate(base[:6], 1):
            candidates.append({"rank": i, "series_name": name, "fit_reason": memo, "recommended_after": "1차 승인/품질점수/반응 데이터 확인 후"})
        return candidates

    def _hold_formats(self, scores: list[dict[str, Any]], primary_key: str, data_stage: str) -> list[dict[str, Any]]:
        holds=[]
        for s in scores:
            if s["format_key"] == primary_key: continue
            holds.append({
                "format": s["format_label"],
                "current_score": s["score"],
                "status": "보류/미래 확장 후보",
                "why_hold": "초기에는 포맷을 분산하지 않고 1개 포맷으로 심사·사용성 데이터를 먼저 쌓기 위함" if data_stage.startswith("초기") else s.get("caution", "데이터 재검토 필요"),
            })
        return holds

    def _decision_rules(self) -> list[str]:
        return [
            "처음부터 모든 포맷을 만들지 않고 1차 포맷 1개만 실제 제작합니다.",
            "움직이는 이모티콘이 무조건 유리하다는 전제를 사용하지 않습니다.",
            "문구 사용성이 강하면 문구형 정지를 우선 검토합니다.",
            "단순 조합·작은 리액션이 강할 때만 미니 이모티콘을 확장 후보로 둡니다.",
            "큰 이모티콘은 강한 표정/대형 리액션 데이터가 쌓인 뒤 검토합니다.",
            "시리즈화는 1차 승인 또는 판매/사용 반응이 확인된 뒤 추천합니다.",
            "모든 확장 판단은 성장형 학습 데이터와 심사/판매 기록을 근거로 갱신합니다.",
        ]

    def _next_actions(self, primary: dict[str, Any], data_stage: str) -> list[str]:
        return [
            f"1차 제작은 '{primary['format_label']}' 중심으로 진행합니다.",
            "선택하지 않은 포맷은 제작하지 말고 확장 후보로만 저장합니다.",
            "24개/32개 문구 선기획과 채팅창 미리보기를 먼저 통과시킵니다.",
            "v36 카카오 규격/용량 검수를 선택 포맷 기준으로만 실행합니다.",
            "제출 전 v30 잠금 체크리스트와 데이터 백업을 실행합니다.",
            "심사 결과/반려 사유/품질점수/판매반응을 v20 성장형 학습 엔진에 저장합니다.",
        ]

    def _safety_notes(self) -> list[str]:
        return [
            "이 리포트는 제작 우선순위 추천이며 카카오 승인이나 수익을 보장하지 않습니다.",
            "공식 규격은 변경될 수 있으므로 제출 직전 카카오 이모티콘 스튜디오 최신 안내를 확인해야 합니다.",
            "AI 완성본 은폐, 기존 캐릭터 모방, 유사 스타일 복제는 기능화하지 않습니다.",
            "데이터가 충분하지 않은 초기 단계에서는 보수적으로 1개 포맷만 제작하는 전략이 안전합니다.",
        ]

    def _write_files(self, base: Path, data: dict[str, Any]) -> dict[str, str]:
        base.mkdir(parents=True, exist_ok=True)
        json_path = base / "format_strategy_v37.json"
        html_path = base / "format_strategy_v37.html"
        scores_csv = base / "format_strategy_v37_scores.csv"
        roadmap_csv = base / "format_strategy_v37_roadmap.csv"
        data_csv = base / "format_strategy_v37_data_requirements.csv"
        notes_txt = base / "format_strategy_v37_notes.txt"
        zip_path = base / "format_strategy_v37.zip"

        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_csv(scores_csv, data.get("format_scores", []))
        self._write_csv(roadmap_csv, data.get("expansion_roadmap", []))
        self._write_csv(data_csv, data.get("data_requirements", []))
        notes_txt.write_text("\n".join(data.get("decision_rules", []) + [""] + data.get("next_actions", []) + [""] + data.get("safety_notes", [])), encoding="utf-8")
        html_path.write_text(self._render_html(data), encoding="utf-8")
        with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
            for p in [json_path, html_path, scores_csv, roadmap_csv, data_csv, notes_txt]:
                zf.write(p, p.name)
        return {
            "json_path": str(json_path),
            "html_path": str(html_path),
            "scores_csv_path": str(scores_csv),
            "roadmap_csv_path": str(roadmap_csv),
            "data_requirements_csv_path": str(data_csv),
            "notes_txt_path": str(notes_txt),
            "zip_path": str(zip_path),
        }

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        keys=[]
        for r in rows:
            for k in r.keys():
                if k not in keys: keys.append(k)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w=csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in rows:
                w.writerow(r)

    def _render_html(self, data: dict[str, Any]) -> str:
        def table(rows):
            if not rows: return "<p>없음</p>"
            keys=[]
            for r in rows:
                for k in r.keys():
                    if k not in keys: keys.append(k)
            head="".join(f"<th>{html.escape(str(k))}</th>" for k in keys)
            body=""
            for r in rows:
                body += "<tr>" + "".join(f"<td>{html.escape(str(r.get(k,'')))}</td>" for k in keys) + "</tr>"
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        primary = data.get("primary_format", {})
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v37 1차 포맷 추천 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;line-height:1.55}}table{{border-collapse:collapse;width:100%;margin:12px 0}}th,td{{border:1px solid #ddd;padding:8px;vertical-align:top}}th{{background:#f5f5f5}}.box{{border:1px solid #ddd;border-radius:12px;padding:16px;background:#fafafa}}.primary{{background:#eef8ff;border-left:6px solid #159}}code{{background:#f2f2f2;padding:2px 4px;border-radius:4px}}</style></head><body>
<h1>v37 1차 포맷 추천 + 단계별 확장 전략</h1>
<div class='box primary'><h2>1차 실제 제작 포맷</h2><p><b>{html.escape(str(primary.get('format_label','')))}</b> · 점수 {html.escape(str(primary.get('score','')))}점</p><p>{html.escape(str(primary.get('why','')))}</p><p><b>주의:</b> {html.escape(str(primary.get('caution','')))}</p></div>
<h2>프로젝트</h2><p><b>{html.escape(str(data.get('project_name','')))}</b></p><p>{html.escape(str(data.get('character_concept','')))}</p><p>데이터 단계: <b>{html.escape(str(data.get('data_stage','')))}</b></p>
<h2>포맷별 점수</h2>{table(data.get('format_scores', []))}
<h2>단계별 확장 로드맵</h2>{table(data.get('expansion_roadmap', []))}
<h2>확장 판단에 필요한 데이터</h2>{table(data.get('data_requirements', []))}
<h2>시리즈 후보</h2>{table(data.get('series_candidates', []))}
<h2>보류 포맷</h2>{table(data.get('hold_formats', []))}
<h2>판단 규칙</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in data.get('decision_rules', []))}</ul>
<h2>다음 액션</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in data.get('next_actions', []))}</ul>
<h2>안전 노트</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in data.get('safety_notes', []))}</ul>
</body></html>"""

    def _safe_slug(self, name: str) -> str:
        return re.sub(r"[^가-힣A-Za-z0-9_.-]+", "_", name).strip("_") or "project"
