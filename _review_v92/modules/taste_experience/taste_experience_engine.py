from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZipFile, ZIP_DEFLATED


@dataclass
class TasteExperienceReport:
    source_inputs: dict[str, Any]
    personal_concept_questions: list[dict[str, Any]]
    concept_candidates: list[dict[str, Any]]
    story_seeds: list[dict[str, Any]]
    phrase_plan: list[dict[str, Any]]
    motion_template_plan: list[dict[str, Any]]
    platform_reuse_plan: list[dict[str, Any]]
    content_calendar: list[dict[str, Any]]
    safety_notes: list[str]
    next_actions: list[str]
    files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TasteExperienceMotionEngine:
    """취향·경험 기반 아이디어 발굴 + 모션 템플릿 고도화 엔진.

    설계 반영점:
    - 내가 좋아하는 것/취미/일상/지역 경험에서 독창 콘셉트 후보를 뽑습니다.
    - 24개/32개 멘트를 먼저 정리하고, 각 문구를 표정/모션/플랫폼 재활용 계획으로 연결합니다.
    - 모션은 2컷/4컷/6컷/10컷 난이도로 나눠 초보자도 단계적으로 만들 수 있게 합니다.
    - 카카오 이모티콘 1차 파이프라인 이후 인스타툰/릴스/OGQ/라인/굿즈 재활용을 함께 제안합니다.
    - 기존 캐릭터/저작물 모방이 아니라 개인 경험과 취향을 독창화하는 방향만 제안합니다.
    """

    CORE_SITUATIONS = [
        ("인사", ["안녕하세요", "왔어요", "좋은 하루예요"]),
        ("확인/답장", ["확인했어요", "봤어요", "잠시만요", "알겠습니다", "넵"]),
        ("감사", ["고마워요", "감사합니다", "마음이 따뜻해요"]),
        ("사과", ["미안해요", "죄송해요", "제가 조심할게요"]),
        ("응원/칭찬", ["좋아요", "잘했어요", "파이팅", "최고예요"]),
        ("피곤/일상", ["힘드네요", "쉬고 싶어요", "오늘도 버텼어요", "퇴근하고 싶어요"]),
        ("감정 리액션", ["헐", "대박", "감동이에요", "눈물나요", "부들부들"]),
        ("시그니처", []),
        ("마무리", ["잘자요", "또 만나요"]),
    ]

    MOTION_BY_DIFFICULTY = {
        "2컷 간단 모션": [
            ("깜빡", "기본 자세 → 눈/효과만 바뀜", 2),
            ("살짝 끄덕", "기본 자세 → 머리만 4~8px 이동", 2),
            ("문구 톡", "문구 없음 → 문구 등장", 2),
        ],
        "4컷 기본 모션": [
            ("손흔들기", "팔 좌 → 중앙 → 우 → 중앙", 4),
            ("꾸벅", "기본 → 숙임 → 유지 → 복귀", 4),
            ("따봉", "손 대기 → 손 올림 → 따봉 강조 → 반짝", 4),
        ],
        "6컷 자연스러운 모션": [
            ("통통 점프", "압축 → 점프 → 최고점 → 착지 → 반동 → 정지", 6),
            ("눈물 한 방울", "고임 → 떨어짐 → 흔들림 → 닦음 → 안정 → 문구", 6),
            ("박수", "손 벌림 → 접근 → 짝 → 벌림 → 반짝 → 정지", 6),
        ],
        "10컷 템플릿 모션": [
            ("자동차/이동", "좌측 진입부터 우측 이동까지 10프레임", 10),
            ("큰 리액션", "작아짐→확대→효과→문구→정지 연결", 10),
            ("복합 제스처", "표정 변화+손동작+문구 동기화 10프레임", 10),
        ],
    }

    PLATFORM_RULES = [
        ("카카오 이모티콘", "1차 수익 파이프라인", "문구 사용성·채팅창 가독성·직접 창작 기록 우선"),
        ("미니 이모티콘", "단순 소재/이어붙이기 확장", "작은 파츠·반복 배치·짧은 리액션 중심"),
        ("네이버 OGQ/블로그 스티커", "카카오 반려 시 재활용 후보", "블로그/댓글용 정지 이미지 세트로 재패키징"),
        ("라인 스티커", "해외/다중 플랫폼 확장", "언어 변환 가능 문구와 보편 리액션 분리"),
        ("인스타툰/릴스", "캐릭터 IP 확장", "4컷 스토리·짧은 장면·경험담 콘텐츠로 변환"),
        ("굿즈/SNS PNG", "부가 활용", "대표 포즈·시그니처 문구를 큰 이미지로 재활용"),
    ]

    RISK_WORDS = ["세일러문", "디즈니", "포켓몬", "산리오", "춘식이", "라이언", "무한도전", "X맨", "따라", "비슷하게", "똑같이", "캐릭터 복제"]

    def build_report(
        self,
        output_dir: str | Path,
        favorites: str,
        hobbies: str,
        life_experience: str,
        daily_observation: str,
        persona: str,
        target_count: int = 32,
        motion_difficulty: str = "4컷 기본 모션",
        include_platform_reuse: bool = True,
    ) -> TasteExperienceReport:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        source_inputs = {
            "favorites": favorites.strip(),
            "hobbies": hobbies.strip(),
            "life_experience": life_experience.strip(),
            "daily_observation": daily_observation.strip(),
            "persona": persona.strip(),
            "target_count": int(target_count),
            "motion_difficulty": motion_difficulty,
            "include_platform_reuse": bool(include_platform_reuse),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        questions = self._build_questions(source_inputs)
        concepts = self._concept_candidates(source_inputs)
        story_seeds = self._story_seeds(source_inputs, concepts)
        phrases = self._phrase_plan(concepts, source_inputs, int(target_count))
        motion_plan = self._motion_templates(phrases, motion_difficulty)
        platform_plan = self._platform_reuse_plan(concepts, phrases) if include_platform_reuse else []
        calendar = self._content_calendar(concepts, phrases, platform_plan)
        safety_notes = self._safety_notes(source_inputs)
        next_actions = self._next_actions(concepts, phrases, motion_difficulty)
        data = {
            "source_inputs": source_inputs,
            "personal_concept_questions": questions,
            "concept_candidates": concepts,
            "story_seeds": story_seeds,
            "phrase_plan": phrases,
            "motion_template_plan": motion_plan,
            "platform_reuse_plan": platform_plan,
            "content_calendar": calendar,
            "safety_notes": safety_notes,
            "next_actions": next_actions,
        }
        files = self._write_files(out / "taste_experience_v35", data)
        return TasteExperienceReport(files=files, **data)

    def _tokens(self, text: str) -> list[str]:
        raw = re.split(r"[,/\n·+]+|하고|그리고|또|\s{2,}", text or "")
        return [x.strip() for x in raw if x.strip()]

    def _build_questions(self, src: dict[str, Any]) -> list[dict[str, Any]]:
        prompts = [
            ("취향", "어릴 때부터 좋아한 장르·소품·캐릭터 감성은 무엇인가요?", src.get("favorites", "")),
            ("취미", "내가 직접 해봤거나 계속 관심 있는 취미/활동은 무엇인가요?", src.get("hobbies", "")),
            ("경험", "직장·가족·지역·반려동물·건강·자취 등 자주 겪는 상황은 무엇인가요?", src.get("life_experience", "")),
            ("관찰", "오늘 본 웃긴 장면, 릴스/쇼츠에서 메모한 장면, 주변 사람 말투는 무엇인가요?", src.get("daily_observation", "")),
            ("캐릭터화", "이 경험을 어떤 소재로 바꾸면 가장 자연스러운가요?", src.get("persona", "")),
        ]
        rows = []
        for idx, (cat, q, value) in enumerate(prompts, 1):
            rows.append({"번호": idx, "분류": cat, "질문": q, "현재 입력": value or "미입력", "보완 필요": "예" if not value else "아니오"})
        return rows

    def _concept_candidates(self, src: dict[str, Any]) -> list[dict[str, Any]]:
        favs = self._tokens(src.get("favorites", "")) or ["좋아하는 감성"]
        hobbies = self._tokens(src.get("hobbies", "")) or ["일상 취미"]
        exp = self._tokens(src.get("life_experience", "")) or ["생활 경험"]
        obs = self._tokens(src.get("daily_observation", "")) or ["관찰 메모"]
        persona = src.get("persona", "").strip() or "짧고 쓰기 쉬운 리액션형 캐릭터"
        candidates = []
        mixes = [
            (favs[0], hobbies[0], "취향+취미"),
            (exp[0], obs[0], "경험+관찰"),
            (favs[-1], exp[-1], "좋아하는 것+생활 경험"),
            (hobbies[-1], obs[-1], "취미+짧은 장면"),
        ]
        for i, (a, b, basis) in enumerate(mixes, 1):
            concept = f"{a} 감성과 {b} 상황을 섞은 {persona}"
            candidates.append({
                "번호": i,
                "콘셉트 후보": concept,
                "근거": basis,
                "외형 힌트": self._shape_hint(a, b),
                "말투 힌트": self._tone_hint(src.get("persona", "") + " " + a + " " + b),
                "차별화 포인트": "개인 취향/경험 기반이라 기존 인기 캐릭터 모방보다 독창성 확보에 유리",
                "추천 포맷": "문구형 정지 + 미니/인스타툰 확장",
            })
        return candidates

    def _shape_hint(self, a: str, b: str) -> str:
        text = a + b
        if any(w in text for w in ["수영", "물", "바다", "파도"]):
            return "물방울/파도형 몸통, 둥근 손, 흔들리는 물결 효과"
        if any(w in text for w in ["강아지", "고양이", "반려"]):
            return "동물 귀/꼬리보다 표정과 말투를 먼저 살린 단순 낙서형"
        if any(w in text for w in ["직장", "회사", "업무"]):
            return "메모지/서류/감자형 몸통, 피곤한 눈, 큰 문구 영역"
        if any(w in text for w in ["음식", "밥", "햄버거", "감자", "버섯"]):
            return "음식 소재의 기본 실루엣을 단순화하고 얼굴을 크게 배치"
        return "동그라미·알갱이·말풍선형 기본 실루엣에서 시작"

    def _tone_hint(self, text: str) -> str:
        if any(w in text for w in ["예의", "정중", "부드"]):
            return "짧고 예의 바른 존댓말"
        if any(w in text for w in ["까칠", "투덜", "시크"]):
            return "짧은 투덜/반전 말투"
        if any(w in text for w in ["피곤", "직장", "업무"]):
            return "영혼은 없지만 예의는 있는 직장인 답장 말투"
        if any(w in text for w in ["사투리", "충청", "강원", "경상", "전라", "제주"]):
            return "과장 없이 생활형 지역 말투"
        return "짧고 상황이 바로 보이는 리액션 말투"

    def _story_seeds(self, src: dict[str, Any], concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        base = concepts[0]["콘셉트 후보"] if concepts else "캐릭터"
        obs = self._tokens(src.get("daily_observation", "")) or ["평범한 하루"]
        seeds = []
        for i, ob in enumerate(obs[:6], 1):
            seeds.append({
                "번호": i,
                "스토리 씨앗": ob,
                "4컷 구조": f"1컷: {base} 등장 / 2컷: {ob} 상황 발생 / 3컷: 캐릭터식 반응 / 4컷: 짧은 문구로 마무리",
                "이모티콘 연결": "대표 리액션 1개와 시그니처 문구 1개로 변환",
                "SNS 확장": "인스타툰 4컷 또는 릴스 6초 장면으로 재활용 가능",
            })
        return seeds

    def _phrase_plan(self, concepts: list[dict[str, Any]], src: dict[str, Any], target_count: int) -> list[dict[str, Any]]:
        tone = self._tone_hint(src.get("persona", "") + " " + src.get("life_experience", ""))
        signature = self._signature_phrases(concepts, src)
        rows = []
        idx = 1
        for category, examples in self.CORE_SITUATIONS:
            items = examples[:] if category != "시그니처" else signature
            for phrase in items:
                if idx > target_count:
                    return rows
                final = self._apply_tone(phrase, tone)
                rows.append({
                    "번호": idx,
                    "분류": category,
                    "기본 문구": phrase,
                    "최종 문구": final,
                    "말투 기준": tone,
                    "상황": self._usage_scene(category),
                    "표정 힌트": self._face_hint(category),
                    "모션 힌트": self._motion_hint(category),
                    "검색 키워드": self._keyword_for_phrase(final),
                    "길이 점검": "양호" if len(final) <= 12 else "짧게 수정 권장",
                })
                idx += 1
        # Fill to target count with context-specific phrases
        while idx <= target_count:
            final = signature[(idx - 1) % len(signature)] if signature else f"시그니처 {idx}"
            final = self._apply_tone(final, tone)
            rows.append({
                "번호": idx,
                "분류": "시그니처",
                "기본 문구": final,
                "최종 문구": final,
                "말투 기준": tone,
                "상황": "캐릭터 고유 말버릇",
                "표정 힌트": "캐릭터 대표 표정",
                "모션 힌트": "작은 끄덕임/문구 톡",
                "검색 키워드": self._keyword_for_phrase(final),
                "길이 점검": "양호" if len(final) <= 12 else "짧게 수정 권장",
            })
            idx += 1
        return rows

    def _signature_phrases(self, concepts: list[dict[str, Any]], src: dict[str, Any]) -> list[str]:
        text = " ".join([src.get("favorites", ""), src.get("hobbies", ""), src.get("life_experience", ""), src.get("persona", "")])
        if "수영" in text:
            return ["한 바퀴만 더", "물 먹었어요", "숨 찼어요", "입수합니다", "오늘 자유형 가능?"]
        if any(w in text for w in ["직장", "회사", "업무"]):
            return ["영혼은 퇴근", "회의 중입니다", "커피가 필요해요", "업무에 눌림", "그래도 합니다"]
        if any(w in text for w in ["강아지", "고양이", "반려"]):
            return ["산책 갈래요", "간식 주세요", "기다렸어요", "꼬리 흔드는 중", "말은 못 해도 알아요"]
        if any(w in text for w in ["사투리", "충청"]):
            return ["그려유", "괜찮아유", "천천히 해유", "고맙슈", "어쩐대유"]
        return ["오늘도 왔어요", "작게 파이팅", "괜찮은 척", "잠깐 쉬어요", "그래도 좋아요"]

    def _apply_tone(self, phrase: str, tone: str) -> str:
        if "직장" in tone and phrase in ["넵", "봤어요"]:
            return "확인했습니다"
        if "투덜" in tone:
            mapping = {"고마워요": "뭐... 고맙다", "미안해요": "미안하다 됐냐", "좋아요": "뭐... 괜찮네", "잘했어요": "나쁘진 않네"}
            return mapping.get(phrase, phrase)
        if "사투리" in tone or "지역" in tone:
            mapping = {"안녕하세요": "안녕하세유", "괜찮아요": "괜찮아유", "고마워요": "고맙슈", "봤어요": "봤어유"}
            return mapping.get(phrase, phrase)
        return phrase

    def _usage_scene(self, category: str) -> str:
        scenes = {
            "인사": "대화 시작", "확인/답장": "업무/일상 빠른 답장", "감사": "호의에 대한 반응",
            "사과": "실수/늦은 답장", "응원/칭찬": "성과/축하/기운 주기", "피곤/일상": "월요일/퇴근/번아웃",
            "감정 리액션": "놀람/웃김/공감", "시그니처": "캐릭터 고유성 강화", "마무리": "대화 종료",
        }
        return scenes.get(category, "일상 대화")

    def _face_hint(self, category: str) -> str:
        return {
            "인사": "웃는 눈+작은 미소", "확인/답장": "집중 눈+체크 효과", "감사": "부드러운 눈+하트/반짝임",
            "사과": "처진 눈+땀", "응원/칭찬": "활짝 웃음+반짝임", "피곤/일상": "반눈+축 처짐",
            "감정 리액션": "큰 눈/눈물/분노선 중 문구별 선택", "시그니처": "대표 표정 유지", "마무리": "감은 눈/손흔들기",
        }.get(category, "기본 표정")

    def _motion_hint(self, category: str) -> str:
        return {
            "인사": "손흔들기", "확인/답장": "체크/도장", "감사": "꾸벅/하트", "사과": "작게 꾸벅/땀",
            "응원/칭찬": "따봉/박수", "피곤/일상": "녹아내림/축 처짐", "감정 리액션": "부들부들/눈물/점프",
            "시그니처": "문구 톡", "마무리": "손흔들기/페이드",
        }.get(category, "작은 끄덕임")

    def _keyword_for_phrase(self, phrase: str) -> str:
        for key in ["안녕", "확인", "감사", "고마", "죄송", "미안", "좋아", "최고", "축하", "파이팅", "잘자", "퇴근", "밥", "헐", "대박"]:
            if key in phrase:
                return key
        return re.sub(r"[^가-힣A-Za-z0-9]", "", phrase)[:6] or "리액션"

    def _motion_templates(self, phrases: list[dict[str, Any]], difficulty: str) -> list[dict[str, Any]]:
        candidates = self.MOTION_BY_DIFFICULTY.get(difficulty, self.MOTION_BY_DIFFICULTY["4컷 기본 모션"])
        rows = []
        for idx, (name, desc, frames) in enumerate(candidates, 1):
            matched = [p["최종 문구"] for p in phrases if name[:2] in p.get("모션 힌트", "") or p.get("모션 힌트") in name or name in p.get("모션 힌트", "")]
            if not matched:
                matched = [p["최종 문구"] for p in phrases[(idx-1)*2:idx*2]]
            rows.append({
                "번호": idx,
                "난이도": difficulty,
                "템플릿명": name,
                "프레임 수": frames,
                "프레임 구조": desc,
                "추천 문구": ", ".join(matched[:4]),
                "캐릭터 비율 조정": "머리/몸통/팔 길이에 맞춰 위치와 크기를 먼저 맞춘 뒤 눈·입·색·문구를 입힘",
                "초보자 메모": "처음에는 2~4컷부터 시작하고, 자연스러움이 필요할 때 6~10컷으로 확장",
            })
        return rows

    def _platform_reuse_plan(self, concepts: list[dict[str, Any]], phrases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        top = concepts[0]["콘셉트 후보"] if concepts else "캐릭터"
        rows = []
        for idx, (platform, purpose, note) in enumerate(self.PLATFORM_RULES, 1):
            rows.append({
                "번호": idx,
                "플랫폼/용도": platform,
                "목적": purpose,
                "재활용 방식": note,
                "적용 콘셉트": top,
                "추천 자산": self._assets_for_platform(platform),
                "주의": "각 플랫폼 최신 규격/정책 확인 필요",
            })
        return rows

    def _assets_for_platform(self, platform: str) -> str:
        if "카카오" in platform:
            return "24/32개 PNG/GIF, 채팅창 미리보기, 저작권 방어 리포트"
        if "미니" in platform:
            return "작은 파츠형 PNG, 이어붙이기 가능한 짧은 리액션"
        if "인스타" in platform:
            return "4컷 스토리, 정사각 카드, 릴스용 6~10초 장면"
        if "굿즈" in platform:
            return "대표 포즈 3종, 큰 해상도 PNG, 시그니처 문구"
        return "정지 PNG 세트와 짧은 문구 CSV"

    def _content_calendar(self, concepts: list[dict[str, Any]], phrases: list[dict[str, Any]], platforms: list[dict[str, Any]]) -> list[dict[str, Any]]:
        concept = concepts[0]["콘셉트 후보"] if concepts else "캐릭터"
        return [
            {"주차": "1주차", "작업": "취향/경험 메모 20개 수집", "산출물": "콘셉트 후보 5개", "메모": "릴스/쇼츠/일상 관찰을 복제하지 말고 상황만 메모"},
            {"주차": "2주차", "작업": "24/32문구 선기획", "산출물": "문구 CSV", "메모": "짧고 검색 가능한 문구 우선"},
            {"주차": "3주차", "작업": "대표 시안+모션 템플릿 적용", "산출물": "PNG/GIF 초안", "메모": f"{concept}의 성격이 외형과 문구에 계속 유지되는지 확인"},
            {"주차": "4주차", "작업": "채팅 미리보기/품질검사/다중 플랫폼 재활용 검토", "산출물": "제출 패키지+SNS 확장안", "메모": "카카오 우선, 반려 시 OGQ/라인/SNS 재활용"},
        ]

    def _safety_notes(self, src: dict[str, Any]) -> list[str]:
        text = " ".join(str(v) for v in src.values())
        notes = [
            "좋아하는 작품/장르에서 영감을 얻더라도 기존 캐릭터명·외형·포즈를 모방하지 말고 감성/상황만 독창적으로 변환하세요.",
            "수익 사례는 개인 사례이므로 승인/수익 보장으로 표시하지 말고, 프로그램은 제작·검수·재활용 보조로 유지합니다.",
            "카카오 외 플랫폼 재활용 시 각 플랫폼의 최신 규격과 약관을 별도로 확인해야 합니다.",
        ]
        hits = [w for w in self.RISK_WORDS if w.lower() in text.lower()]
        if hits:
            notes.insert(0, "위험 키워드 감지: " + ", ".join(hits) + " → 직접 모방/유사 스타일 사용 금지, 독창 콘셉트로 재구성 필요")
        return notes

    def _next_actions(self, concepts: list[dict[str, Any]], phrases: list[dict[str, Any]], difficulty: str) -> list[str]:
        return [
            "가장 마음에 드는 콘셉트 후보 1개를 선택하고 제목 후보를 v34 엔진에서 다시 점수화하세요.",
            "문구 24/32개 중 길이가 긴 문구를 1초 안에 읽히는 표현으로 줄이세요.",
            f"모션은 현재 '{difficulty}' 기준으로 시작하되, 초안은 2~4컷부터 만든 뒤 자연스러움이 필요한 표현만 확장하세요.",
            "대표 캐릭터 원본을 v24/v25 자유 드로잉·파츠 추정 흐름에 연결하세요.",
            "카카오 제출 전 v30 잠금 체크리스트와 v31 최종 제출 패키지 마법사를 실행하세요.",
        ]

    def _write_files(self, base: Path, data: dict[str, Any]) -> dict[str, str]:
        base.parent.mkdir(parents=True, exist_ok=True)
        html_path = base.with_suffix(".html")
        json_path = base.with_suffix(".json")
        concept_csv = base.with_name(base.name + "_concepts.csv")
        phrase_csv = base.with_name(base.name + "_phrases.csv")
        motion_csv = base.with_name(base.name + "_motions.csv")
        platform_csv = base.with_name(base.name + "_platforms.csv")
        calendar_csv = base.with_name(base.name + "_calendar.csv")
        notes_txt = base.with_name(base.name + "_notes.txt")
        zip_path = base.with_suffix(".zip")
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_csv(concept_csv, data["concept_candidates"])
        self._write_csv(phrase_csv, data["phrase_plan"])
        self._write_csv(motion_csv, data["motion_template_plan"])
        self._write_csv(platform_csv, data["platform_reuse_plan"])
        self._write_csv(calendar_csv, data["content_calendar"])
        notes_txt.write_text("\n".join(data["safety_notes"] + ["", "다음 액션:"] + data["next_actions"]), encoding="utf-8")
        html_path.write_text(self._html(data), encoding="utf-8")
        with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
            for p in [html_path, json_path, concept_csv, phrase_csv, motion_csv, platform_csv, calendar_csv, notes_txt]:
                if p.exists():
                    zf.write(p, p.name)
        return {
            "html_path": str(html_path),
            "json_path": str(json_path),
            "concept_csv_path": str(concept_csv),
            "phrase_csv_path": str(phrase_csv),
            "motion_csv_path": str(motion_csv),
            "platform_csv_path": str(platform_csv),
            "calendar_csv_path": str(calendar_csv),
            "notes_txt_path": str(notes_txt),
            "zip_path": str(zip_path),
        }

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        keys: list[str] = []
        for row in rows:
            for k in row.keys():
                if k not in keys:
                    keys.append(k)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in keys})

    def _html(self, data: dict[str, Any]) -> str:
        def table(rows: list[dict[str, Any]]) -> str:
            if not rows:
                return "<p>없음</p>"
            keys = list(rows[0].keys())
            head = "".join(f"<th>{html.escape(str(k))}</th>" for k in keys)
            body = "".join("<tr>" + "".join(f"<td>{html.escape(str(row.get(k,'')))}</td>" for k in keys) + "</tr>" for row in rows)
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v35 취향·경험 기반 아이디어/모션 전략</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.55;margin:32px;color:#222}} table{{border-collapse:collapse;width:100%;margin:12px 0}} th,td{{border:1px solid #ddd;padding:8px;vertical-align:top}} th{{background:#f3f5f7}} .box{{background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:14px 0}} code{{background:#f3f4f6;padding:2px 5px;border-radius:5px}}</style></head><body>
<h1>v35 취향·경험 기반 아이디어 발굴 + 모션 템플릿 고도화</h1>
<div class='box'><h2>입력 요약</h2><pre>{html.escape(json.dumps(data['source_inputs'], ensure_ascii=False, indent=2))}</pre></div>
<h2>개인 콘셉트 질문</h2>{table(data['personal_concept_questions'])}
<h2>콘셉트 후보</h2>{table(data['concept_candidates'])}
<h2>스토리 씨앗</h2>{table(data['story_seeds'])}
<h2>24/32문구 계획</h2>{table(data['phrase_plan'])}
<h2>모션 템플릿 계획</h2>{table(data['motion_template_plan'])}
<h2>플랫폼 재활용 계획</h2>{table(data['platform_reuse_plan'])}
<h2>4주 제작 캘린더</h2>{table(data['content_calendar'])}
<h2>안전 노트</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in data['safety_notes'])}</ul>
<h2>다음 액션</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in data['next_actions'])}</ul>
</body></html>"""
