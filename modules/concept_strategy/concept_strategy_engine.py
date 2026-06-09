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
class ConceptStrategyReport:
    raw_input: str
    concrete_concept: str
    specificity_score: int
    weakness_flags: list[str]
    title_candidates: list[dict[str, Any]]
    phrase_plan: list[dict[str, Any]]
    plus_keywords: list[dict[str, Any]]
    motion_templates: list[dict[str, Any]]
    format_recommendation: list[dict[str, Any]]
    revision_notes: list[str]
    safety_notes: list[str]
    files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConceptStrategyEngine:
    """구체 콘셉트·멘트·모션 템플릿 전략 엔진.

    참고자료 반영 방향:
    - 막연한 '귀여운 고양이'보다 '게으르고 나른한 뚱냥이'처럼 구체 콘셉트를 먼저 잡습니다.
    - 콘셉트가 외형·멘트·제목에 드러나는지 점검합니다.
    - 초보자는 멘트가 있어야 상황 사용성이 높으므로 24/32개 문구를 먼저 기획합니다.
    - 모션은 프레임을 매번 새로 그리기보다 템플릿을 캐릭터 비율에 맞춰 변형하는 방향으로 제안합니다.
    - 움직이는 포맷이 무조건 우위가 아니므로, 포맷 추천은 콘셉트/문구/사용성/완성도를 기준으로 합니다.
    """

    VAGUE_WORDS = ["귀여운", "귀엽", "예쁜", "멋진", "좋은", "재밌는", "캐릭터", "동물", "고양이", "강아지"]
    SPECIFIC_TRAITS = [
        "게으른", "나른한", "뚱뚱한", "까칠하지만 챙기는", "무표정하지만 속정 있는", "피곤한 직장인",
        "다정한", "예의 바른", "소심한", "느긋한", "하찮은", "반전 성격", "사투리 말투", "업무에 눌린",
        "말풍선 콘셉트", "순정만화 콘셉트", "낙서형", "미니", "이어붙이는", "직장인 답장형",
    ]
    HIGH_USE_KEYWORDS = [
        "안녕하세요", "넵", "확인했습니다", "알겠습니다", "감사합니다", "고마워요", "죄송합니다", "미안해요",
        "괜찮아요", "잠시만요", "부탁드려요", "수고하셨습니다", "좋아요", "최고예요", "축하해요", "파이팅",
        "잘자요", "밥 먹었어요?", "퇴근하고 싶어요", "살려주세요", "대박", "헐", "진짜요?", "어쩌죠",
    ]
    MOTION_LIBRARY = [
        ("손흔들기", "인사/안녕하세요", "팔이 2~3프레임으로 좌우 흔들림", "문구는 위쪽에서 톡 등장"),
        ("꾸벅", "감사/사과/예의", "몸통이 아래로 살짝 숙여졌다 복귀", "문구는 천천히 페이드인"),
        ("박수", "축하/최고/감동", "양손이 가까워졌다 멀어짐, 반짝임", "문구는 통통 튐"),
        ("따봉", "좋아요/확인/응원", "한손/양손/큰손 강조 선택", "문구는 도장처럼 찍힘 또는 통통"),
        ("부들부들", "분노/당황/참는 감정", "몸통이 좌우로 빠르게 흔들림", "문구도 작게 떨림"),
        ("눈물", "슬픔/감동/민망", "눈물 한 방울~폭발까지 강도별", "문구는 아래로 처지거나 흔들림"),
        ("자동차/이동", "출근/퇴근/이동", "캐릭터가 프레임 밖에서 들어왔다 나감", "문구는 따라붙는 말풍선"),
        ("하트/반짝임", "고마움/호감/칭찬", "하트와 별이 2~4프레임 반짝", "문구는 부드럽게 등장"),
        ("도장/체크", "확인/완료/접수", "체크 또는 도장이 마지막 프레임에 찍힘", "문구는 도장처럼 쿵"),
        ("녹아내림/축 처짐", "피곤/무기력", "몸통이 아래로 눌리거나 작아짐", "문구도 아래로 처짐"),
    ]

    CATEGORY_TARGETS_32 = [
        ("인사", 3), ("확인/답장", 5), ("감사", 3), ("사과", 3), ("응원/축하", 4),
        ("피곤/일상", 4), ("감정 리액션", 5), ("캐릭터 시그니처", 4), ("마무리", 1),
    ]

    def build_report(
        self,
        output_dir: str | Path,
        concept_text: str,
        material: str = "",
        target_user: str = "일상 카톡 사용자",
        personality: str = "",
        tone: str = "",
        format_focus: str = "auto",
        target_count: int = 32,
        include_mini_strategy: bool = True,
    ) -> ConceptStrategyReport:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        raw = (concept_text or "").strip()
        material = (material or self._guess_material(raw) or "캐릭터").strip()
        personality = (personality or self._guess_personality(raw) or "구체 성격 후보 필요").strip()
        tone = (tone or self._guess_tone(raw, personality) or "짧고 상황이 바로 보이는 말투").strip()
        concrete = self._make_concrete_concept(raw, material, personality, target_user)
        score, flags = self._specificity_score(raw, material, personality, tone)
        titles = self._make_titles(material, personality, tone, concrete)
        phrase_plan = self._make_phrase_plan(material, personality, tone, target_count)
        plus_keywords = self._make_plus_keywords(phrase_plan, material)
        motion_templates = self._make_motion_templates(material, personality, format_focus)
        formats = self._recommend_formats(raw, phrase_plan, motion_templates, format_focus, include_mini_strategy)
        revision_notes = self._revision_notes(score, flags, phrase_plan, formats)
        safety_notes = self._safety_notes(raw)
        data = {
            "raw_input": raw,
            "concrete_concept": concrete,
            "specificity_score": score,
            "weakness_flags": flags,
            "title_candidates": titles,
            "phrase_plan": phrase_plan,
            "plus_keywords": plus_keywords,
            "motion_templates": motion_templates,
            "format_recommendation": formats,
            "revision_notes": revision_notes,
            "safety_notes": safety_notes,
        }
        files = self._write_files(out / "concept_strategy_v34", data)
        return ConceptStrategyReport(files=files, **data)

    def _guess_material(self, text: str) -> str:
        candidates = ["고양이", "강아지", "팽이버섯", "감자", "고구마", "보리", "쌀", "돌멩이", "조약돌", "메모지", "토끼", "하트", "당근", "햄버거", "말풍선"]
        for c in candidates:
            if c in text:
                return c
        m = re.search(r"([가-힣A-Za-z0-9]+)(?:을|를|이|가|으로|로)\s*(?:얼굴|캐릭터|이모티콘)", text)
        return m.group(1) if m else ""

    def _guess_personality(self, text: str) -> str:
        hits = []
        for t in ["게으른", "나른", "뚱", "까칠", "다정", "예의", "소심", "시크", "무표정", "피곤", "느긋", "반전", "애교", "업무"]:
            if t in text:
                hits.append(t)
        if not hits:
            return ""
        mapping = {
            "나른": "나른하고 느긋함", "뚱": "둥글고 느긋한 반전 매력", "예의": "예의 바르고 다정함", "업무": "업무에 눌렸지만 성실함",
        }
        return ", ".join(mapping.get(h, h) for h in hits[:4])

    def _guess_tone(self, text: str, personality: str) -> str:
        if "냥" in text or "고양이" in text:
            return "짧은 고양이 말투와 생활 리액션"
        if "사투리" in text or "유" in text or "슈" in text:
            return "생활형 사투리 말투"
        if "예의" in personality or "다정" in personality:
            return "예의 바르고 부드러운 말투"
        if "까칠" in personality:
            return "짧게 투덜거리지만 미워 보이지 않는 말투"
        return "짧고 검색 가능한 일상 리액션 말투"

    def _make_concrete_concept(self, raw: str, material: str, personality: str, target_user: str) -> str:
        if raw:
            base = raw.replace("\n", " ").strip()
        else:
            base = f"{material} 캐릭터"
        return f"{personality} 성격이 외형과 멘트에 드러나는 {material} 이모티콘 · 대상: {target_user} · 원문: {base[:120]}"

    def _specificity_score(self, raw: str, material: str, personality: str, tone: str) -> tuple[int, list[str]]:
        score = 40
        flags = []
        if material and material != "캐릭터": score += 12
        else: flags.append("소재가 막연합니다.")
        if personality and "후보 필요" not in personality: score += 18
        else: flags.append("성격이 약합니다. 게으름/까칠함/다정함/반전 성격처럼 구체화하세요.")
        if tone: score += 10
        if any(t in raw for t in self.SPECIFIC_TRAITS): score += 15
        if any(w in raw for w in self.VAGUE_WORDS) and not any(t in raw for t in self.SPECIFIC_TRAITS):
            flags.append("'귀여운/예쁜'처럼 막연한 표현이 많습니다. 왜 귀여운지 외형과 성격으로 바꾸세요.")
            score -= 8
        if any(x in raw for x in ["멘트", "문구", "안녕하세요", "확인", "고마워", "나른"]): score += 8
        else: flags.append("대표 멘트가 부족합니다. 초보자는 문구가 있어야 사용 상황이 명확합니다.")
        return max(0, min(100, score)), flags

    def _make_titles(self, material: str, personality: str, tone: str, concept: str) -> list[dict[str, Any]]:
        key = personality.split(",")[0].strip() if personality else "생활형"
        candidates = [
            f"{key} {material}", f"{material}의 짧은 답장", f"{material}, 오늘도 한마디",
            f"{tone.split()[0]} {material}", f"{material} 리액션 모음", f"말맛 나는 {material}",
            f"{material}의 나른한 하루", f"{material}가 말합니다", f"{material} 사용설명서", f"작고 확실한 {material}",
        ]
        out=[]; seen=set()
        for i,t in enumerate(candidates,1):
            t=t.replace("구체", "").strip()
            if t in seen: continue
            seen.add(t)
            out.append({"rank": i, "title": t, "concept_fit_score": self._title_score(t, material, personality), "memo": "제목 안에 소재·성격·사용상황 중 2개 이상이 보이면 유리"})
        return out[:10]

    def _title_score(self, title: str, material: str, personality: str) -> int:
        score=55
        if material and material in title: score += 18
        for token in re.split(r"[,\s/]+", personality):
            if token and token[:2] in title:
                score += 8
                break
        if any(w in title for w in ["답장","리액션","하루","말","사용"]): score += 12
        return min(score, 96)

    def _make_phrase_plan(self, material: str, personality: str, tone: str, count: int) -> list[dict[str, Any]]:
        count = 24 if count <= 24 else 32
        templates = {
            "인사": ["안녕하세요", "왔어요", "좋은 하루예요"],
            "확인/답장": ["넵", "확인했습니다", "알겠습니다", "봤어요", "접수했어요"],
            "감사": ["감사합니다", "고마워요", "마음만 받을게요"],
            "사과": ["죄송합니다", "미안해요", "다음엔 더 잘할게요"],
            "응원/축하": ["파이팅", "잘했어요", "축하해요", "최고예요"],
            "피곤/일상": ["졸려요", "퇴근하고 싶어요", "잠시만요", "오늘도 버팁니다"],
            "감정 리액션": ["헐", "대박", "눈물나요", "부들부들", "감동이에요"],
            "캐릭터 시그니처": [f"{material}처럼 서 있을게요", f"{material}도 봤어요", f"{material} 마음입니다", f"{material}는 쉬는 중"],
            "마무리": ["잘자요", "또 만나요"],
        }
        plan=[]
        target_def = self.CATEGORY_TARGETS_32 if count == 32 else [(c, max(1, round(n*24/32))) for c,n in self.CATEGORY_TARGETS_32]
        for category,n in target_def:
            for base in templates.get(category, [])[:n]:
                if len(plan) >= count: break
                phrase = self._apply_tone(base, material, personality, tone)
                plan.append({
                    "no": len(plan)+1, "category": category, "base_phrase": base, "final_phrase": phrase,
                    "length_score": self._length_score(phrase), "usefulness_score": self._usefulness_score(base, category),
                    "expression_hint": self._expression_hint(category), "motion_template": self._motion_for_category(category),
                    "plus_search_keyword": self._keyword_for_phrase(base),
                    "memo": "짧고 검색 가능한 문구를 우선 배정",
                })
        while len(plan) < count:
            base = self.HIGH_USE_KEYWORDS[len(plan) % len(self.HIGH_USE_KEYWORDS)]
            phrase = self._apply_tone(base, material, personality, tone)
            plan.append({"no":len(plan)+1,"category":"보충","base_phrase":base,"final_phrase":phrase,"length_score":self._length_score(phrase),"usefulness_score":70,"expression_hint":"기본 리액션","motion_template":"기본 말풍선","plus_search_keyword":self._keyword_for_phrase(base),"memo":"보충 후보"})
        return plan

    def _apply_tone(self, base: str, material: str, personality: str, tone: str) -> str:
        if "냥" in tone and not base.endswith("냥"):
            if base.endswith("요"): return base[:-1] + "냥"
            return base + "냥"
        if "투덜" in tone or "까칠" in personality:
            return {"고마워요":"뭐... 고맙다", "죄송합니다":"미안하다 됐냐", "좋아요":"뭐... 괜찮네", "파이팅":"해봐, 안 죽어"}.get(base, base)
        if "사투리" in tone or "유" in tone:
            return {"안녕하세요":"안녕하세유", "확인했습니다":"확인했어유", "괜찮아요":"괜찮아유", "고마워요":"고맙슈", "잠시만요":"잠깐만유"}.get(base, base)
        if "예의" in personality or "다정" in personality:
            return base if base.endswith(("요","다")) else base + "요"
        return base

    def _length_score(self, phrase: str) -> int:
        l = len(phrase.replace(" ", ""))
        if l <= 5: return 95
        if l <= 9: return 85
        if l <= 13: return 72
        return 55

    def _usefulness_score(self, base: str, category: str) -> int:
        score = 60
        if base in self.HIGH_USE_KEYWORDS: score += 20
        if category in ["확인/답장","감사","사과","인사","응원/축하"]: score += 12
        return min(score, 98)

    def _expression_hint(self, category: str) -> str:
        return {
            "인사":"밝은 눈+작은 손흔들기", "확인/답장":"집중눈+체크/도장", "감사":"웃는눈+하트/꾸벅", "사과":"처진눈+땀/작아짐",
            "응원/축하":"활짝 웃음+박수/따봉", "피곤/일상":"반눈+축 처짐", "감정 리액션":"큰 눈/눈물/분노선", "캐릭터 시그니처":"소재 특성 강조", "마무리":"감은 눈/손흔들기",
        }.get(category, "기본 표정")

    def _motion_for_category(self, category: str) -> str:
        return {"인사":"손흔들기", "확인/답장":"도장/체크", "감사":"꾸벅", "사과":"꾸벅+땀", "응원/축하":"박수/따봉", "피곤/일상":"축 처짐", "감정 리액션":"감정별 하위모션", "마무리":"손흔들기/페이드"}.get(category, "기본 말풍선")

    def _keyword_for_phrase(self, base: str) -> str:
        for k in ["안녕", "확인", "고마워", "감사", "죄송", "미안", "축하", "파이팅", "잘자", "밥", "퇴근", "헐", "대박", "좋아"]:
            if k in base: return k
        return base[:6]

    def _make_plus_keywords(self, phrase_plan: list[dict[str, Any]], material: str) -> list[dict[str, Any]]:
        seen=[]
        for row in phrase_plan:
            k=row.get("plus_search_keyword") or ""
            if k and k not in seen:
                seen.append(k)
        for k in [material, "귀여워", "답장", "리액션"]:
            if k and k not in seen: seen.append(k)
        return [{"keyword":k,"reason":"카톡 문장/키워드 입력 시 관련 이모티콘 노출 가능성을 고려한 후보","priority":i+1} for i,k in enumerate(seen[:20])]

    def _make_motion_templates(self, material: str, personality: str, format_focus: str) -> list[dict[str, Any]]:
        result=[]
        for i,(name, use, motion, text) in enumerate(self.MOTION_LIBRARY,1):
            result.append({"rank":i,"template_name":name,"use_case":use,"frame_plan":motion,"text_sync":text,"character_ratio_note":f"{material}의 머리/몸통 비율에 맞춰 팔 길이·말풍선 위치 수정","difficulty":"낮음" if i<=4 else "보통","format_fit":"animated_text" if format_focus in ["auto","animated_text"] else format_focus})
        return result

    def _recommend_formats(self, raw: str, phrase_plan: list[dict[str, Any]], motions: list[dict[str, Any]], focus: str, mini: bool) -> list[dict[str, Any]]:
        avg_len = sum(x["length_score"] for x in phrase_plan)/max(1,len(phrase_plan))
        static_text = 80 + (5 if avg_len > 80 else 0)
        animated_text = 72 + (8 if motions else 0)
        mini_score = 68 + (10 if mini and any(w in raw for w in ["미니","단순","하트","느낌표","당근"]) else 0)
        formats = [
            ("static_text", "문구 결합형 멈춰있는 이모티콘", static_text, "짧은 멘트와 상황성이 강하면 초보자에게 가장 안정적"),
            ("animated_text", "움직이는 문구 결합형", animated_text, "모션 템플릿을 쓰면 제작 난이도를 낮출 수 있음"),
            ("static", "멈춰있는 이모티콘", 70, "멘트 없이도 표정/캐릭터성이 강할 때 적합"),
            ("mini", "미니 이모티콘", mini_score, "단순 소재·이어붙이기 구조·작은 리액션에 적합. 공식 최신 규격 확인 필요"),
            ("animated", "움직이는 이모티콘", 64, "움직임 자체가 콘셉트일 때 적합"),
        ]
        if focus != "auto":
            formats = [(k,l,s+(10 if k==focus else 0),m) for k,l,s,m in formats]
        return [{"rank":i+1,"format_key":k,"format_label":l,"score":min(int(s),98),"reason":m} for i,(k,l,s,m) in enumerate(sorted(formats, key=lambda x:x[2], reverse=True))]

    def _revision_notes(self, score: int, flags: list[str], phrases: list[dict[str, Any]], formats: list[dict[str, Any]]) -> list[str]:
        notes=[]
        if score < 70:
            notes.append("콘셉트가 아직 약합니다. 소재+성격+상황+말투가 제목과 문구에 보이도록 보강하세요.")
        notes.extend(flags[:4])
        long_count = sum(1 for p in phrases if p.get("length_score",0) < 70)
        if long_count:
            notes.append(f"긴 문구 후보 {long_count}개가 있습니다. 작은 화면 가독성을 위해 8~12자 안쪽으로 줄이세요.")
        notes.append(f"1차 추천 포맷은 {formats[0]['format_label']}입니다. 움직이는 포맷이 무조건 우위가 아니라 콘셉트/문구 사용성을 우선합니다.")
        notes.append("모션 템플릿은 고정 복사가 아니라 캐릭터 비율에 맞춰 팔 길이·몸통 크기·문구 위치를 수정해야 합니다.")
        return notes

    def _safety_notes(self, raw: str) -> list[str]:
        notes = [
            "기존 캐릭터 스타일 모방, 유명 캐릭터 유사 생성, AI 은폐/검수 우회 방향은 차단해야 합니다.",
            "수익 사례는 개인 사례이며 승인·판매·수익을 보장하지 않습니다.",
            "실제 제출 전 카카오 이모티콘 스튜디오 최신 규격과 운영 원칙을 다시 확인하세요.",
        ]
        if any(w in raw for w in ["춘식이","라이언","산리오","포켓몬","비슷하게","스타일"]):
            notes.insert(0, "유명 캐릭터/브랜드 연상 키워드가 있어 독창화가 필요합니다.")
        return notes

    def _write_files(self, base: Path, data: dict[str, Any]) -> dict[str, str]:
        base.parent.mkdir(parents=True, exist_ok=True)
        html_path = base.with_suffix(".html")
        json_path = base.with_suffix(".json")
        phrases_csv = base.parent / f"{base.name}_32_phrase_plan.csv"
        titles_csv = base.parent / f"{base.name}_title_candidates.csv"
        motions_csv = base.parent / f"{base.name}_motion_templates.csv"
        zip_path = base.with_suffix(".zip")
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_csv(phrases_csv, data.get("phrase_plan", []))
        self._write_csv(titles_csv, data.get("title_candidates", []))
        self._write_csv(motions_csv, data.get("motion_templates", []))
        html_path.write_text(self._html(data), encoding="utf-8")
        with ZipFile(zip_path, "w", ZIP_DEFLATED) as z:
            for p in [html_path, json_path, phrases_csv, titles_csv, motions_csv]:
                if p.exists(): z.write(p, p.name)
        return {"html_path": str(html_path), "json_path": str(json_path), "phrase_csv_path": str(phrases_csv), "title_csv_path": str(titles_csv), "motion_csv_path": str(motions_csv), "zip_path": str(zip_path)}

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        fields=[]
        for r in rows:
            for k in r.keys():
                if k not in fields: fields.append(k)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    def _html(self, data: dict[str, Any]) -> str:
        def table(rows):
            if not rows: return "<p>없음</p>"
            fields=[]
            for r in rows:
                for k in r.keys():
                    if k not in fields: fields.append(k)
            head="".join(f"<th>{html.escape(str(f))}</th>" for f in fields)
            body="".join("<tr>"+"".join(f"<td>{html.escape(str(r.get(f,'')))}</td>" for f in fields)+"</tr>" for r in rows)
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v34 콘셉트 전략 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;line-height:1.55}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #ddd;padding:7px;vertical-align:top}}th{{background:#f3f5f7}}.card{{background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:14px 0}}code{{background:#f1f5f9;padding:2px 4px;border-radius:4px}}</style></head><body>
<h1>v34 구체 콘셉트·멘트·모션 템플릿 전략 리포트</h1>
<div class='card'><b>생성 시각:</b> {datetime.now().isoformat(timespec='seconds')}<br><b>구체 콘셉트:</b> {html.escape(data.get('concrete_concept',''))}<br><b>구체성 점수:</b> {data.get('specificity_score')}</div>
<h2>보완 플래그</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in data.get('weakness_flags',[]))}</ul>
<h2>제목 후보</h2>{table(data.get('title_candidates',[]))}
<h2>32문구 선기획</h2>{table(data.get('phrase_plan',[]))}
<h2>이모티콘 플러스 키워드 후보</h2>{table(data.get('plus_keywords',[]))}
<h2>모션 템플릿 후보</h2>{table(data.get('motion_templates',[]))}
<h2>포맷 추천</h2>{table(data.get('format_recommendation',[]))}
<h2>수정 노트</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in data.get('revision_notes',[]))}</ul>
<h2>안전 노트</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in data.get('safety_notes',[]))}</ul>
</body></html>"""
