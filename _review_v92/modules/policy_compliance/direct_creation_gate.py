from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class DirectCreationGateResult:
    status: str
    score: int
    passed: bool
    checks: dict[str, bool]
    required_actions: list[str]
    allowed_program_role: list[str]
    blocked_program_role: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DirectCreationGate:
    """Gate a project toward human-authored Kakao emoticon production.

    The goal is not to certify legal compliance. It keeps the workflow away from
    AI-completed submissions and toward user-authored sketches, shapes, edits,
    and evidence records.
    """

    def evaluate(
        self,
        has_user_shape_input: bool,
        has_sketch_or_reference: bool,
        has_creator_note: bool,
        has_layer_or_revision_plan: bool,
        has_rights_confirmation: bool,
        uses_ai_completed_image: bool,
    ) -> DirectCreationGateResult:
        checks = {
            "사용자가 도형/소재/색/성격을 직접 입력": bool(has_user_shape_input),
            "손스케치 또는 직접 만든 참고자료 있음": bool(has_sketch_or_reference),
            "직접 창작 메모 있음": bool(has_creator_note),
            "레이어/수정 이력 계획 있음": bool(has_layer_or_revision_plan),
            "타인 저작권/상표권 미사용 확인": bool(has_rights_confirmation),
            "AI 완성 이미지 미사용": not bool(uses_ai_completed_image),
        }
        weights = {
            "사용자가 도형/소재/색/성격을 직접 입력": 20,
            "손스케치 또는 직접 만든 참고자료 있음": 20,
            "직접 창작 메모 있음": 15,
            "레이어/수정 이력 계획 있음": 15,
            "타인 저작권/상표권 미사용 확인": 15,
            "AI 완성 이미지 미사용": 15,
        }
        score = sum(weights[key] for key, ok in checks.items() if ok)
        required_actions: list[str] = []
        if not checks["손스케치 또는 직접 만든 참고자료 있음"]:
            required_actions.append("제출 전 손스케치, 도형 러프, 직접 만든 참고 이미지를 1개 이상 저장하세요.")
        if not checks["레이어/수정 이력 계획 있음"]:
            required_actions.append("몸통/눈/입/팔/말풍선/효과 레이어 또는 수정 전후 기록을 남기세요.")
        if not checks["타인 저작권/상표권 미사용 확인"]:
            required_actions.append("유명 캐릭터, 브랜드, 작가 스타일, 타인 이미지를 사용하지 않았는지 확인하세요.")
        if not checks["AI 완성 이미지 미사용"]:
            required_actions.append("AI가 만든 완성 이미지는 제출 후보에서 제외하고, 직접 그린 레이어 기반으로 다시 제작하세요.")

        if uses_ai_completed_image:
            status = "제출 후보 차단"
        elif score >= 85:
            status = "직접 창작 흐름 양호"
        elif score >= 65:
            status = "증거 보완 후 사용"
        else:
            status = "제출 전 직접 창작 증거 부족"

        return DirectCreationGateResult(
            status=status,
            score=score,
            passed=(status == "직접 창작 흐름 양호"),
            checks=checks,
            required_actions=required_actions,
            allowed_program_role=[
                "사용자 도형/스케치 입력을 360x360 작업 초안으로 정리",
                "문구 후보, 감정 분류, 모션 계획, 파일명/용량/QC 검사 보조",
                "창작 과정 타임라인, 체크섬, 출처 기록 정리",
            ],
            blocked_program_role=[
                "AI 완성 이미지 생성 후 제출",
                "유명 캐릭터/브랜드/작가 스타일 모방",
                "검수 우회 또는 AI 사용 은폐",
                "타인 이미지·이모티콘·영상 프레임 복제",
            ],
        )
