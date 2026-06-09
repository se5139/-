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
class DialectLifeExpressionReport:
    region: str
    material: str
    concept_summary: str
    title_candidates: list[dict[str, Any]]
    phrase_set: list[dict[str, Any]]
    personal_dialect_phrases: list[str]
    safety_warnings: list[str]
    regional_style_notes: list[str]
    source_reference_notes: list[str]
    recommendations: list[str]
    files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DialectLifeExpressionEngine:
    """지역 특성·사투리 실생활 문구 엔진.

    목적:
    - 공식/공개 지역어 자료를 직접 대량 복제하지 않고, 참고 구조와 출처 메모를 남깁니다.
    - 실제 문구는 사용자가 입력한 생활 말투와 안전한 후보 템플릿을 기반으로 생성합니다.
    - 특정 지역을 희화화하거나 고정관념화하지 않도록 위험 표현을 감지합니다.
    """

    REGION_STYLES: dict[str, dict[str, Any]] = {
        "충청권": {
            "tone": "느긋하고 부드러운 생활형 말투",
            "suffixes": ["유", "슈", "그려유", "해유"],
            "examples": ["안녕하세유", "괜찮아유", "천천히 해유", "고맙슈", "봤어유", "어쩐대유"],
            "avoid": "느리다/답답하다 같은 고정관념으로 밀어붙이지 않기",
        },
        "강원권": {
            "tone": "소박하고 담백한 생활형 말투",
            "suffixes": ["래요", "드래요", "하드래요"],
            "examples": ["왔드래요", "괜찮드래요", "고맙드래요", "천천히 하드래요"],
            "avoid": "지역어 후보는 세부 지역에 따라 차이가 커서 사용자 검수 필요",
        },
        "경상권": {
            "tone": "짧고 힘 있는 리액션형 말투",
            "suffixes": ["데이", "하이소", "아이가", "한다이가"],
            "examples": ["봤데이", "고맙데이", "괜찮다 아이가", "힘내이소"],
            "avoid": "거친 말투로만 고정하지 않기",
        },
        "전라권": {
            "tone": "정감 있고 리듬감 있는 생활형 말투",
            "suffixes": ["잉", "허요", "해불자", "그라제"],
            "examples": ["고맙당께", "괜찮허요", "천천히 해불자", "그라제"],
            "avoid": "과장된 방송식 흉내로 만들지 않기",
        },
        "제주권": {
            "tone": "고유 어휘가 강한 지역어라 사용 전 검수 필요한 말투",
            "suffixes": ["마씸", "수다", "양"],
            "examples": ["고맙수다", "괜찮수다", "혼저 옵서예", "천천히 해도 됨수다"],
            "avoid": "제주어는 고유성이 강해 실제 화자/자료 검수 권장",
        },
        "수도권": {
            "tone": "표준어 기반의 짧은 생활 리액션",
            "suffixes": ["요", "네요", "합니다"],
            "examples": ["안녕하세요", "확인했어요", "괜찮아요", "고마워요"],
            "avoid": "지역성보다 캐릭터 말투와 상황성을 강화",
        },
        "직접 입력": {
            "tone": "사용자 실제 생활 말투 기반",
            "suffixes": [],
            "examples": [],
            "avoid": "사용자가 직접 경험한 표현을 우선하고 과장 표현은 줄이기",
        },
    }

    BASE_SITUATIONS = [
        ("인사", "안녕하세요"), ("확인", "확인했어요"), ("수락", "네"), ("감사", "고마워요"),
        ("사과", "미안해요"), ("위로", "괜찮아요"), ("응원", "천천히 해요"), ("당황", "어쩌죠"),
        ("피곤", "힘드네요"), ("기쁨", "좋아요"), ("축하", "축하해요"), ("부탁", "부탁해요"),
        ("기다림", "잠깐만요"), ("퇴근", "퇴근하고 싶어요"), ("잘자", "잘자요"), ("시그니처", "오늘도 해볼게요"),
        ("관심", "밥 먹었어요"), ("걱정", "괜찮으세요"), ("마무리", "또 만나요"), ("놀람", "진짜요"),
        ("민망", "머쓱하네요"), ("거절", "어려울 것 같아요"), ("칭찬", "잘했어요"), ("리액션", "대박이에요"),
        ("슬픔", "눈물나요"), ("분노", "부들부들"), ("하트", "마음만 받을게요"), ("직장", "접수했어요"),
        ("친구", "뭐해요"), ("가족", "조심히 와요"), ("느긋", "천천히 가요"), ("캐릭터", "여기 있어요"),
    ]

    RISK_WORDS = [
        "촌놈", "촌년", "미개", "무식", "게으름", "느려터", "무식한", "멍청", "바보 지역",
        "사투리충", "지역 비하", "깡촌", "억지로 웃긴", "놀림", "비하",
    ]

    def build_report(
        self,
        output_dir: str | Path,
        region: str,
        material: str,
        personality: str,
        tone: str,
        context: str,
        personal_dialect_text: str = "",
        target_count: int = 32,
        format_key: str = "static_text",
        politeness: str = "부드러운 존댓말",
    ) -> DialectLifeExpressionReport:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        region = region if region in self.REGION_STYLES else "직접 입력"
        style = self.REGION_STYLES[region]
        material = (material or "지역형 캐릭터").strip()
        personality = (personality or "다정하고 생활감 있음").strip()
        tone = (tone or style["tone"]).strip()
        context = (context or "일상 답장용").strip()
        personal = self._parse_personal_phrases(personal_dialect_text)
        warnings = self._safety_warnings("\n".join([region, material, personality, tone, context, personal_dialect_text]))

        concept_summary = f"{region} 생활 말투를 과장 없이 살린 {personality} {material} 캐릭터"
        title_candidates = self._make_titles(region, material, personality, personal)
        phrase_set = self._make_phrases(region, style, material, personality, tone, context, personal, target_count, politeness, format_key)
        regional_notes = [
            f"{region} 말투 방향: {style['tone']}",
            f"주의: {style['avoid']}",
            "사투리 후보는 실제 지역·세대·가족/직장 관계에 따라 달라질 수 있으므로, 사용자가 직접 어색함을 검수해야 합니다.",
            "문구는 이모티콘 검색성과 채팅 사용성을 위해 짧게 유지하는 것을 우선합니다.",
        ]
        source_notes = [
            "국립국어원 '방언 찾기/지역어 종합 정보' 같은 공개 지역어 자료는 후보 검증·참고 출처로 사용합니다.",
            "국립국어원 모두의 말뭉치·일상 대화 말뭉치 계열 자료는 생활 문장 감각을 참고하는 구조로 사용하며, 이용 조건 확인이 필요합니다.",
            "프로그램에는 타 자료 원문을 대량 복제하지 않고, 사용자 직접 입력 말투와 안전한 문구 템플릿을 결합해 후보를 생성합니다.",
        ]
        recommendations = self._recommendations(format_key, region, personal, warnings)
        base = out / "dialect_life_expression"
        files = self._write_files(base, {
            "region": region,
            "material": material,
            "concept_summary": concept_summary,
            "title_candidates": title_candidates,
            "phrase_set": phrase_set,
            "personal_dialect_phrases": personal,
            "safety_warnings": warnings,
            "regional_style_notes": regional_notes,
            "source_reference_notes": source_notes,
            "recommendations": recommendations,
        })
        return DialectLifeExpressionReport(
            region=region,
            material=material,
            concept_summary=concept_summary,
            title_candidates=title_candidates,
            phrase_set=phrase_set,
            personal_dialect_phrases=personal,
            safety_warnings=warnings,
            regional_style_notes=regional_notes,
            source_reference_notes=source_notes,
            recommendations=recommendations,
            files=files,
        )

    def _parse_personal_phrases(self, text: str) -> list[str]:
        if not text:
            return []
        raw = re.split(r"[,\n;/]+", text)
        phrases = []
        for item in raw:
            phrase = item.strip().strip("-• ")
            if phrase and phrase not in phrases:
                phrases.append(phrase[:30])
        return phrases[:40]

    def _safety_warnings(self, text: str) -> list[str]:
        warnings = []
        lower = text.lower()
        for word in self.RISK_WORDS:
            if word.lower() in lower:
                warnings.append(f"지역 비하/희화화 위험 표현 감지: {word}")
        if "웃기게 과장" in text or "과장해서" in text:
            warnings.append("사투리를 웃음거리로 과장하는 방향은 위험합니다. 생활형 짧은 문구로 순화하세요.")
        if not warnings:
            warnings.append("고위험 비하 표현은 감지되지 않았습니다. 단, 실제 지역 사용자 검수는 권장됩니다.")
        return warnings

    def _make_titles(self, region: str, material: str, personality: str, personal: list[str]) -> list[dict[str, Any]]:
        base_word = personal[0] if personal else self.REGION_STYLES[region]["examples"][0] if self.REGION_STYLES[region]["examples"] else "우리말투"
        candidates = [
            f"{base_word} {material}",
            f"{region} {material}의 하루",
            f"{material}, 오늘도 {base_word}",
            f"생활말투 {material}",
            f"{personality.split()[0] if personality else '다정한'} {material}",
            f"우리동네 {material}",
            f"말맛 나는 {material}",
            f"{material}가 말해유",
            f"{material} 리액션 모음",
            f"{material}의 짧은 답장",
        ]
        result = []
        seen = set()
        for idx, title in enumerate(candidates, start=1):
            title = title.strip()
            if title in seen:
                continue
            seen.add(title)
            score = 70 + min(20, len([w for w in [region, material, base_word] if w and w in title]) * 7)
            result.append({"rank": idx, "title": title, "concept_score": min(score, 96), "memo": "콘셉트·지역 말투·소재가 제목에 보이는지 기준으로 점수화"})
        return result[:10]

    def _make_phrases(self, region: str, style: dict[str, Any], material: str, personality: str, tone: str, context: str, personal: list[str], target_count: int, politeness: str, format_key: str) -> list[dict[str, Any]]:
        examples = style.get("examples", [])[:]
        phrases = []
        # Personal phrases first: user experience wins.
        for p in personal:
            phrases.append({
                "no": len(phrases)+1,
                "category": "사용자 경험 사투리",
                "standard": p,
                "dialect_phrase": self._shorten(p),
                "usage_context": "사용자가 실제 생활에서 쓰는 말투",
                "character_note": f"{personality} 성격에 맞춰 과장 없이 사용",
                "motion_hint": self._motion_hint(p, format_key),
                "safety_note": "사용자 직접 경험 표현이므로 우선 후보. 다만 상대/상황별 어색함 검수 필요.",
            })
        for category, standard in self.BASE_SITUATIONS:
            if len(phrases) >= target_count:
                break
            dialect_phrase = self._convert_phrase(region, standard, examples, len(phrases))
            if dialect_phrase in [x["dialect_phrase"] for x in phrases]:
                continue
            phrases.append({
                "no": len(phrases)+1,
                "category": category,
                "standard": standard,
                "dialect_phrase": dialect_phrase,
                "usage_context": self._usage_context(category, context),
                "character_note": self._character_note(material, personality, tone, category),
                "motion_hint": self._motion_hint(dialect_phrase, format_key, category),
                "safety_note": "지역 말투 후보입니다. 특정 지역을 희화화하지 않는지 최종 검수하세요.",
            })
        # ensure count
        while len(phrases) < target_count:
            idx = len(phrases) + 1
            phrase = f"{material} 답장 {idx}"
            phrases.append({
                "no": idx,
                "category": "확장 후보",
                "standard": phrase,
                "dialect_phrase": phrase,
                "usage_context": context,
                "character_note": "추가 검수 필요",
                "motion_hint": "정지형은 문구 크게, 움직이는 문구형은 작게 통통",
                "safety_note": "자동 보충 문구이므로 사용 전 수정 권장",
            })
        return phrases[:target_count]

    def _convert_phrase(self, region: str, standard: str, examples: list[str], index: int) -> str:
        if region == "충청권":
            mapping = {
                "안녕하세요": "안녕하세유", "확인했어요": "봤어유", "네": "그려유", "고마워요": "고맙슈",
                "미안해요": "미안해유", "괜찮아요": "괜찮아유", "천천히 해요": "천천히 해유", "어쩌죠": "어쩐대유",
                "힘드네요": "힘드네유", "좋아요": "좋구먼유", "잠깐만요": "잠깐만유", "진짜요": "진짜유?",
            }
            return mapping.get(standard, standard.replace("요", "유") if standard.endswith("요") else standard + "유")
        if region == "강원권":
            mapping = {"안녕하세요": "왔드래요", "고마워요": "고맙드래요", "괜찮아요": "괜찮드래요", "천천히 해요": "천천히 하드래요"}
            return mapping.get(standard, examples[index % len(examples)] if examples else standard)
        if region == "경상권":
            mapping = {"안녕하세요": "왔나", "확인했어요": "봤데이", "고마워요": "고맙데이", "괜찮아요": "괜찮다 아이가", "천천히 해요": "천천히 하이소", "좋아요": "좋데이"}
            return mapping.get(standard, standard.replace("요", "데이") if standard.endswith("요") else standard)
        if region == "전라권":
            mapping = {"안녕하세요": "왔당께", "확인했어요": "봤당께", "고마워요": "고맙당께", "괜찮아요": "괜찮허요", "천천히 해요": "천천히 해불자", "좋아요": "좋아부러"}
            return mapping.get(standard, standard.replace("요", "허요") if standard.endswith("요") else standard)
        if region == "제주권":
            mapping = {"안녕하세요": "혼저 옵서예", "확인했어요": "봤수다", "고마워요": "고맙수다", "괜찮아요": "괜찮수다", "천천히 해요": "천천히 해도 됨수다"}
            return mapping.get(standard, examples[index % len(examples)] if examples else standard)
        return standard

    def _shorten(self, phrase: str) -> str:
        return phrase[:18] + "…" if len(phrase) > 19 else phrase

    def _usage_context(self, category: str, context: str) -> str:
        if category in ["확인", "수락", "직장", "기다림"]:
            return f"{context} / 직장·단톡 답장"
        if category in ["감사", "사과", "위로", "응원"]:
            return f"{context} / 관계 유지 문구"
        if category in ["피곤", "퇴근", "슬픔", "분노"]:
            return f"{context} / 감정 리액션"
        return context

    def _character_note(self, material: str, personality: str, tone: str, category: str) -> str:
        return f"{material}의 {personality} 성격을 유지하고, {tone} 말투로 {category} 상황을 짧게 표현"

    def _motion_hint(self, phrase: str, format_key: str, category: str = "") -> str:
        if format_key == "animated_text":
            if category in ["감사", "사과"] or any(k in phrase for k in ["고맙", "미안", "죄송"]):
                return "작게 꾸벅 + 문구가 천천히 등장"
            if category in ["확인", "수락"] or any(k in phrase for k in ["봤", "확인", "그려"]):
                return "고개 끄덕 + 체크/도장처럼 문구 등장"
            if category in ["피곤", "퇴근"]:
                return "몸이 아래로 처짐 + 문구도 살짝 내려앉음"
            return "캐릭터 작게 통통 + 문구가 톡 튀어나옴"
        return "정지형은 글자를 크게, 캐릭터 표정을 명확하게"

    def _recommendations(self, format_key: str, region: str, personal: list[str], warnings: list[str]) -> list[str]:
        recs = [
            "사투리 문구는 24개/32개 전체에 과하게 넣기보다, 핵심 시그니처 6~10개와 일반 실사용 문구를 섞는 편이 안전합니다.",
            "제목에는 지역명보다 캐릭터 소재와 말맛이 보이게 구성하고, 지역 비하로 읽힐 수 있는 표현은 제외하세요.",
            "사용자가 직접 경험한 생활 말투를 우선 반영하면 독창성과 실제감이 높아집니다.",
        ]
        if format_key == "animated_text":
            recs.append("움직이는 문구형에서는 사투리 어미가 길어지지 않도록 문구를 짧게 유지하고, 문구 움직임은 작게 적용하세요.")
        if not personal:
            recs.append("개인 경험 사투리 입력이 없으므로, 가족/직장/친구 사이에서 실제로 쓰는 말 5개 이상을 추가하면 결과가 더 자연스러워집니다.")
        if warnings and not warnings[0].startswith("고위험"):
            recs.append("경고가 있는 표현은 순화 후보로 교체한 뒤 채팅창 미리보기에서 다시 확인하세요.")
        return recs

    def _write_files(self, base: Path, data: dict[str, Any]) -> dict[str, str]:
        base.parent.mkdir(parents=True, exist_ok=True)
        json_path = base.with_suffix(".json")
        html_path = base.with_suffix(".html")
        csv_path = base.with_name(base.name + "_phrases.csv")
        txt_path = base.with_name(base.name + "_source_notes.txt")
        zip_path = base.with_suffix(".zip")
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["no", "category", "standard", "dialect_phrase", "usage_context", "character_note", "motion_hint", "safety_note"])
            writer.writeheader()
            writer.writerows(data.get("phrase_set", []))
        txt_path.write_text("\n".join(data.get("source_reference_notes", [])), encoding="utf-8")
        html_path.write_text(self._html(data), encoding="utf-8")
        with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
            for p in [json_path, html_path, csv_path, txt_path]:
                if p.exists():
                    zf.write(p, arcname=p.name)
        return {"json_path": str(json_path), "html_path": str(html_path), "csv_path": str(csv_path), "source_notes_path": str(txt_path), "zip_path": str(zip_path)}

    def _html(self, data: dict[str, Any]) -> str:
        rows = []
        for p in data.get("phrase_set", []):
            rows.append("<tr>" + "".join(f"<td>{html.escape(str(p.get(k,'')))}</td>" for k in ["no", "category", "dialect_phrase", "usage_context", "motion_hint", "safety_note"]) + "</tr>")
        title_rows = "".join(f"<li>{html.escape(t['title'])} · 점수 {t['concept_score']}</li>" for t in data.get("title_candidates", []))
        warn_rows = "".join(f"<li>{html.escape(w)}</li>" for w in data.get("safety_warnings", []))
        rec_rows = "".join(f"<li>{html.escape(r)}</li>" for r in data.get("recommendations", []))
        return f"""<!doctype html>
<html lang='ko'><head><meta charset='utf-8'><title>지역·사투리 실생활 문구 리포트</title>
<style>body{{font-family:'Malgun Gothic',Arial,sans-serif;margin:28px;line-height:1.55;color:#222}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border:1px solid #ddd;padding:7px;vertical-align:top}}th{{background:#f5f5f5}}.badge{{display:inline-block;background:#eee;border-radius:999px;padding:4px 10px;margin-right:6px}}</style></head>
<body><h1>지역·사투리 실생활 문구 리포트</h1>
<p><span class='badge'>생성일 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span><span class='badge'>{html.escape(data.get('region',''))}</span></p>
<h2>콘셉트</h2><p>{html.escape(data.get('concept_summary',''))}</p>
<h2>제목 후보</h2><ol>{title_rows}</ol>
<h2>안전 경고</h2><ul>{warn_rows}</ul>
<h2>문구 세트</h2><table><tr><th>No</th><th>분류</th><th>문구</th><th>사용 상황</th><th>모션 힌트</th><th>안전 메모</th></tr>{''.join(rows)}</table>
<h2>추천</h2><ul>{rec_rows}</ul>
<h2>자료 참고 원칙</h2><pre>{html.escape(json.dumps(data.get('source_reference_notes',[]), ensure_ascii=False, indent=2))}</pre>
<p>이 리포트는 실제 지역어를 법적으로 보증하거나 지역 대표성을 확정하는 자료가 아닙니다. 제출 전 실제 화자/사용자 검수를 권장합니다.</p>
</body></html>"""
