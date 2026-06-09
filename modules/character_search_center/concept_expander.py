from __future__ import annotations

from dataclasses import dataclass, asdict

from modules.character_search_center.keyword_analyzer import KeywordProfile


@dataclass
class ConceptCandidate:
    name: str
    base: str
    world: str
    tone: str
    target: str
    signature_motion: str
    signature_phrase: str
    originality_note: str

    def to_dict(self) -> dict:
        return asdict(self)


class ConceptExpander:
    """입력 키워드를 기존 캐릭터 모방이 아닌 새 세계관 조합으로 확장합니다."""

    MOTION_BY_BASE = {
        "감자": ["칭찬받으면 싹이 남", "죄송할수록 작아짐", "업무에 눌려 납작해짐"],
        "메모지": ["구겨졌다 펴짐", "도장처럼 체크가 찍힘", "바람에 살짝 날림"],
        "돌멩이": ["거의 안 움직이다가 작게 끄덕임", "화나면 미세하게 금이 감", "칭찬받으면 반짝임"],
        "무": ["당황하면 잎이 흔들림", "민망하면 땅속으로 숨음", "응원하면 잎이 커짐"],
        "얼음": ["피곤하면 녹아내림", "화나면 다시 얼어붙음", "감동하면 물방울이 됨"],
        "먼지": ["말풍선에 밀려 굴러감", "칭찬받으면 보송해짐", "놀라면 흩어짐"],
    }

    def expand(self, profile: KeywordProfile, count: int = 10) -> list[ConceptCandidate]:
        candidates: list[ConceptCandidate] = []
        tones = profile.tone or ["짧은", "공손"]
        target = profile.targets[0] if profile.targets else "일상 대화"
        for base in profile.bases:
            motions = self.MOTION_BY_BASE.get(base, ["작게 튐", "부들부들 떨림", "꾸벅 숙임"])
            for i, motion in enumerate(motions):
                tone = tones[i % len(tones)]
                name = self._build_name(base, tone, target, i)
                candidates.append(
                    ConceptCandidate(
                        name=name,
                        base=base,
                        world=f"{target} 대화에서 자주 쓰는 말을 {base}의 물성/성격으로 표현하는 세계관",
                        tone=f"{tone} 말투, 짧고 바로 읽히는 문구 중심",
                        target=target,
                        signature_motion=motion,
                        signature_phrase=self._signature_phrase(base, motion),
                        originality_note="유명 캐릭터 외형을 빌리지 않고 본체·말투·움직임을 새로 조합한 후보입니다.",
                    )
                )
                if len(candidates) >= count:
                    return candidates
        return candidates

    def _build_name(self, base: str, tone: str, target: str, idx: int) -> str:
        prefixes = ["업무에 눌린", "예의 바른", "영혼 없는", "칭찬받으면 살아나는", "조용히 버티는"]
        return f"{prefixes[idx % len(prefixes)]} {base}"

    def _signature_phrase(self, base: str, motion: str) -> str:
        if "구겨" in motion:
            return "확인했습니다... 구겨졌지만요"
        if "싹" in motion:
            return "칭찬받으면 싹납니다"
        if "작아" in motion:
            return "죄송합니다... 작아지는 중"
        if "녹" in motion:
            return "잠시 녹는 중입니다"
        if "끄덕" in motion:
            return "넵... 아주 작게"
        return "조용히 파이팅입니다"
