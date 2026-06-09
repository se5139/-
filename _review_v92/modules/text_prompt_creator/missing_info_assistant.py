
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import hashlib
import html
import json
import re
import time
import zipfile

from modules.text_prompt_creator.text_prompt_engine import TextPromptEmoticonEngine


@dataclass
class CandidateOption:
    field: str
    label: str
    value: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MissingInfoAnalysis:
    raw_prompt: str
    detected: Dict[str, Any]
    missing_fields: List[str]
    candidates: Dict[str, List[Dict[str, Any]]]
    warnings: List[str]
    keep_as_is_prompt: str
    recommended_prompt: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MissingInfoReport:
    project_name: str
    output_dir: str
    html_path: str
    json_path: str
    csv_path: str
    zip_path: str
    analysis: Dict[str, Any]
    selected_values: Dict[str, str]
    final_prompt: str
    mode: str
    preview_report: Optional[Dict[str, Any]]
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MissingInfoAssistant:
    """v28 텍스트 설명 누락 정보 후보 제안/재구성 엔진.

    목적:
    - 사용자가 자연어로 간단히 설명했을 때 빠진 항목을 감지한다.
    - 다리/팔/색상/성격/말투/표정/행동/문구/포맷 후보를 보여준다.
    - 사용자가 후보를 선택해 재구성하거나, 입력한 그대로 초안을 만들 수 있게 한다.
    """

    FIELD_LABELS = {
        "material": "소재/본체",
        "color": "기본 색상",
        "personality": "성격",
        "tone": "말투",
        "phrase": "대표 문구",
        "action": "행동/제스처",
        "face": "표정 방향",
        "arms": "팔/손 구성",
        "legs": "다리/발 구성",
        "motion": "움직임 방식",
        "format": "포맷",
    }

    FORBIDDEN_HINTS = [
        "춘식이", "라이언", "카카오프렌즈", "라인프렌즈", "산리오", "포켓몬", "디즈니",
        "짱구", "스누피", "비슷하게", "똑같이", "스타일로", "느낌으로", "AI 티", "모르게",
    ]

    def _safe_name(self, value: str) -> str:
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "missing_info_project"))
        return safe[:80] or "missing_info_project"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _detect_phrase(self, text: str) -> str:
        q = re.search(r"[\"'“”‘’]([^\"'“”‘’]{1,30})[\"'“”‘’]", text)
        if q:
            return q.group(1).strip()
        m = re.search(r"([가-힣A-Za-z0-9 .!?~]{1,20})\s*(?:라고|이라며|말하며)", text)
        return m.group(1).strip() if m else ""

    def _detect_material(self, text: str) -> str:
        m = re.search(r"(.{1,26}?)(?:을|를)\s*(?:얼굴|캐릭터|이모티콘|형상화|만들)", text)
        if m:
            return m.group(1).strip(" ,.\n")
        known = ["팽이버섯", "보리", "쌀", "감자", "고구마", "메모지", "돌멩이", "무", "콩", "버섯", "양말", "먼지"]
        for k in known:
            if k in text:
                return k
        parts = [p for p in re.split(r"\s+", text.strip()) if p]
        return parts[0][:18] if parts else ""

    def _has_any(self, text: str, words: List[str]) -> bool:
        return any(w in text for w in words)

    def analyze_prompt(self, prompt: str) -> MissingInfoAnalysis:
        text = (prompt or "").strip()
        if not text:
            text = "팽이버섯 한 묶음을 얼굴로 형상화하고 예의 바르게 인사하며 안녕하세요라고 한다"

        detected: Dict[str, Any] = {}
        material = self._detect_material(text)
        if material:
            detected["material"] = material
        phrase = self._detect_phrase(text)
        if phrase:
            detected["phrase"] = phrase
        if self._has_any(text, ["다정", "까칠", "온순", "시크", "피곤", "예민", "밝", "소심", "무표정"]):
            detected["personality"] = self._extract_keyword_phrase(text, ["성격은", "성격:"]) or self._personality_from_text(text)
        if self._has_any(text, ["말투", "예의", "부드럽", "투덜", "단답", "정중", "귀엽"]):
            detected["tone"] = self._extract_keyword_phrase(text, ["말투는", "말투:"]) or self._tone_from_text(text)
        if self._has_any(text, ["빨강", "파랑", "초록", "노랑", "갈색", "아이보리", "검정", "하얀", "색상", "톤"]):
            detected["color"] = self._color_from_text(text)
        if self._has_any(text, ["인사", "따봉", "울", "눈물", "박수", "꾸벅", "확인", "점프", "화내", "도망"]):
            detected["action"] = self._action_from_text(text)
        if self._has_any(text, ["웃", "슬픔", "울", "화난", "피곤", "당황", "무표정", "눈물"]):
            detected["face"] = self._face_from_text(text)
        if self._has_any(text, ["팔", "손", "따봉", "박수", "손흔", "양손", "한손"]):
            detected["arms"] = self._arms_from_text(text)
        if self._has_any(text, ["다리", "발", "걷", "뛰", "점프", "없다", "없음"]):
            detected["legs"] = self._legs_from_text(text)
        if self._has_any(text, ["움직", "흔들", "통통", "튀", "페이드", "도장", "천천히"]):
            detected["motion"] = self._motion_from_text(text)
        if self._has_any(text, ["움직이는", "정지", "문구형", "큰 이모티콘", "GIF"]):
            detected["format"] = self._format_from_text(text)

        required = ["material", "color", "personality", "tone", "phrase", "action", "face", "arms", "legs", "motion", "format"]
        missing = [f for f in required if not detected.get(f)]
        candidates = {f: [c.to_dict() for c in self.candidates_for(f, material, detected)] for f in missing}
        warnings = [f"'{k}' 표현은 기존 캐릭터 모방/AI 은폐/정책 위험 가능성이 있어 독창 방향으로 수정하세요." for k in self.FORBIDDEN_HINTS if k in text]
        recommended = self.reconstruct_prompt(text, detected, {f: (opts[0]["value"] if opts else "") for f, opts in candidates.items()}, mode="candidate")
        return MissingInfoAnalysis(
            raw_prompt=text,
            detected=detected,
            missing_fields=missing,
            candidates=candidates,
            warnings=warnings,
            keep_as_is_prompt=text,
            recommended_prompt=recommended,
        )

    def _extract_keyword_phrase(self, text: str, starts: List[str]) -> str:
        for s0 in starts:
            idx = text.find(s0)
            if idx >= 0:
                s = idx + len(s0)
                end_candidates = [e for e in [text.find(x, s) for x in [",", ".", "\n", "말투", "문구", "라고", "하며"]] if e >= 0]
                e = min(end_candidates) if end_candidates else min(len(text), s + 26)
                return text[s:e].strip(" 은는이가을를하고며,.")
        return ""

    def _personality_from_text(self, text: str) -> str:
        for key, val in [("다정", "다정함"), ("까칠", "까칠하지만 은근히 챙김"), ("온순", "온순하고 다정함"), ("시크", "시크하고 말수가 적음"), ("피곤", "피곤하지만 성실함"), ("소심", "소심하지만 반응이 큼"), ("무표정", "무표정하지만 속정 있음")]:
            if key in text:
                return val
        return ""

    def _tone_from_text(self, text: str) -> str:
        if "예의" in text or "정중" in text:
            return "예의 바르고 정중한 말투"
        if "부드" in text:
            return "부드럽고 위로하는 말투"
        if "투덜" in text:
            return "짧게 투덜거리는 말투"
        if "단답" in text:
            return "짧은 단답 말투"
        return ""

    def _color_from_text(self, text: str) -> str:
        pairs = [("갈색", "따뜻한 곡물톤"), ("아이보리", "아이보리/쌀알톤"), ("노랑", "부드러운 노랑톤"), ("초록", "채소/새싹톤"), ("검정", "흑백 낙서톤"), ("하얀", "밝은 화이트톤")]
        for key, val in pairs:
            if key in text:
                return val
        return "직접 입력 색상"

    def _action_from_text(self, text: str) -> str:
        for key, val in [("따봉", "따봉"), ("인사", "인사"), ("안녕", "인사"), ("울", "울기"), ("눈물", "울기"), ("박수", "박수"), ("꾸벅", "꾸벅"), ("확인", "확인"), ("점프", "점프")]:
            if key in text:
                return val
        return ""

    def _face_from_text(self, text: str) -> str:
        for key, val in [("웃", "웃는 눈 + 미소"), ("울", "촉촉한 눈 + 눈물"), ("눈물", "촉촉한 눈 + 눈물"), ("화난", "날카로운 눈 + 찡그린 입"), ("피곤", "반눈 + 일자 입"), ("당황", "큰 눈 + 열린 입"), ("무표정", "점눈 + 일자 입")]:
            if key in text:
                return val
        return ""

    def _arms_from_text(self, text: str) -> str:
        if "양손" in text:
            return "양손 사용"
        if "한손" in text:
            return "한손 사용"
        if "따봉" in text:
            return "따봉용 손 파츠"
        if "박수" in text:
            return "박수용 양손 파츠"
        return ""

    def _legs_from_text(self, text: str) -> str:
        if "다리 없음" in text or "다리없" in text:
            return "다리 없음"
        if "짧" in text and ("다리" in text or "발" in text):
            return "짧은 다리/콩알 발"
        if "점프" in text or "뛰" in text:
            return "점프 가능한 짧은 다리"
        return ""

    def _motion_from_text(self, text: str) -> str:
        if "통통" in text or "튀" in text:
            return "통통 튀는 움직임"
        if "흔들" in text:
            return "좌우 흔들림"
        if "도장" in text:
            return "도장처럼 문구 등장"
        if "천천히" in text:
            return "천천히 나타남"
        if "움직" in text:
            return "자연스러운 작은 움직임"
        return ""

    def _format_from_text(self, text: str) -> str:
        if "움직이는" in text and "문구" in text:
            return "animated_text"
        if "움직이는" in text or "GIF" in text:
            return "animated"
        if "문구형" in text:
            return "static_text"
        if "큰 이모티콘" in text:
            return "big"
        return ""

    def candidates_for(self, field: str, material: str, detected: Dict[str, Any]) -> List[CandidateOption]:
        material = material or detected.get("material", "캐릭터") or "캐릭터"
        if field == "color":
            return [
                CandidateOption(field, "소재 자연색", f"{material}의 자연색을 단순화", "소재에서 바로 연상되는 색상이라 초보자용으로 안전합니다."),
                CandidateOption(field, "부드러운 파스텔톤", "부드러운 파스텔톤", "다정/위로형 캐릭터에 어울립니다."),
                CandidateOption(field, "선명한 캐릭터톤", "선명한 캐릭터톤", "작은 화면에서 눈에 잘 띕니다."),
                CandidateOption(field, "흑백 낙서톤", "흑백 낙서톤", "대충 그린 듯한 하찮은 콘셉트에 적합합니다."),
            ]
        if field == "personality":
            return [
                CandidateOption(field, "다정함", "다정하고 예의 바름", "인사/감사/위로 문구와 잘 맞습니다."),
                CandidateOption(field, "까칠하지만 챙김", "까칠하지만 은근히 챙김", "투덜거리지만 정이 있는 캐릭터성이 생깁니다."),
                CandidateOption(field, "무표정 속정", "무표정하지만 속정 있음", "짧은 답장형 이모티콘에 좋습니다."),
                CandidateOption(field, "피곤한 직장인", "피곤하지만 성실함", "넵/확인/퇴근 계열 문구와 잘 맞습니다."),
            ]
        if field == "tone":
            return [
                CandidateOption(field, "정중한 말투", "예의 바르고 정중한 말투", "카톡 실사용 문구에 범용성이 높습니다."),
                CandidateOption(field, "부드러운 말투", "부드럽고 위로하는 말투", "다정한 캐릭터와 잘 맞습니다."),
                CandidateOption(field, "투덜 말투", "짧게 투덜거리는 말투", "까칠/하찮은 캐릭터에 개성이 생깁니다."),
                CandidateOption(field, "무표정 단답", "짧은 단답 말투", "직장인 답장형에 적합합니다."),
            ]
        if field == "phrase":
            return [
                CandidateOption(field, "안녕하세요", "안녕하세요", "대표 인사 문구로 가장 안전합니다."),
                CandidateOption(field, "확인했습니다", "확인했습니다", "업무/답장형 사용성이 높습니다."),
                CandidateOption(field, "감사합니다", "감사합니다", "범용성이 높은 감정 문구입니다."),
                CandidateOption(field, "좋아요", "좋아요", "따봉/긍정 모션과 연결하기 쉽습니다."),
            ]
        if field == "action":
            return [
                CandidateOption(field, "인사", "인사", "첫 대표 컷으로 적합합니다."),
                CandidateOption(field, "꾸벅", "꾸벅", "감사/사과/예의 문구와 잘 맞습니다."),
                CandidateOption(field, "따봉", "따봉", "좋아요/응원 계열에 좋습니다."),
                CandidateOption(field, "작게 통통", "작게 통통 튐", "움직이는 문구형에서 생동감이 생깁니다."),
            ]
        if field == "face":
            return [
                CandidateOption(field, "기본 미소", "점눈 + 작은 미소", "대부분의 초안에 무난합니다."),
                CandidateOption(field, "다정한 미소", "부드러운 눈 + 따뜻한 미소", "다정/예의 콘셉트와 맞습니다."),
                CandidateOption(field, "무표정", "점눈 + 일자 입", "하찮은 단답형에 좋습니다."),
                CandidateOption(field, "수줍은 표정", "옆눈 + 어색한 입", "민망/감사 표현에 좋습니다."),
            ]
        if field == "arms":
            return [
                CandidateOption(field, "팔 없음", "팔 없음", "소재 자체를 단순하게 보여줄 때 좋습니다."),
                CandidateOption(field, "짧은 팔", "짧은 콩알 팔", "가장 범용적인 초보자용 파츠입니다."),
                CandidateOption(field, "한손 제스처", "한손 제스처 팔", "인사/따봉을 작게 표현하기 좋습니다."),
                CandidateOption(field, "양손 리액션", "양손 리액션 팔", "좋아요/축하/응원 같은 강한 표현에 좋습니다."),
            ]
        if field == "legs":
            return [
                CandidateOption(field, "다리 없음", "다리 없음", "버섯/곡물/돌멩이처럼 본체만으로도 충분할 때 적합합니다."),
                CandidateOption(field, "짧은 다리", "짧은 다리 2개", "귀엽고 안정적인 기본형입니다."),
                CandidateOption(field, "콩알 발", "작은 콩알 발", "하찮고 둥근 캐릭터에 잘 맞습니다."),
                CandidateOption(field, "뿌리/줄기 다리", "소재 특성을 살린 뿌리형 다리", "팽이버섯/식물형 소재에 어울립니다."),
            ]
        if field == "motion":
            return [
                CandidateOption(field, "작은 꾸벅", "작은 꾸벅", "예의/인사/감사에 적합합니다."),
                CandidateOption(field, "통통 튐", "통통 튀는 움직임", "밝고 귀여운 움직이는 문구형에 좋습니다."),
                CandidateOption(field, "말풍선 등장", "문구가 천천히 나타남", "문구 가독성을 해치지 않습니다."),
                CandidateOption(field, "손 제스처 강조", "손동작과 문구가 함께 강조됨", "따봉/박수/인사에 적합합니다."),
            ]
        if field == "format":
            return [
                CandidateOption(field, "문구형 정지", "static_text", "처음 제작 난이도가 낮고 답장형에 좋습니다."),
                CandidateOption(field, "움직이는 문구형", "animated_text", "문구와 캐릭터 행동을 같이 보여줄 수 있습니다."),
                CandidateOption(field, "멈춰있는 이모티콘", "static", "표정 중심 캐릭터에 적합합니다."),
                CandidateOption(field, "움직이는 이모티콘", "animated", "동작 자체가 재미있을 때 적합합니다."),
            ]
        return []

    def reconstruct_prompt(self, raw_prompt: str, detected: Dict[str, Any], selected: Dict[str, str], mode: str = "candidate") -> str:
        if mode == "keep_as_is":
            return raw_prompt
        merged = dict(detected)
        merged.update({k: v for k, v in selected.items() if v})
        material = merged.get("material", "독창 캐릭터")
        phrase = merged.get("phrase", "안녕하세요")
        parts = [
            f"{material}을/를 독창적인 이모티콘 캐릭터로 만든다",
            f"기본 색상은 {merged.get('color', '소재 자연색')}",
            f"성격은 {merged.get('personality', '다정하고 예의 바름')}",
            f"말투는 {merged.get('tone', '예의 바르고 정중한 말투')}",
            f"표정은 {merged.get('face', '점눈 + 작은 미소')}",
            f"팔/손은 {merged.get('arms', '짧은 콩알 팔')}",
            f"다리/발은 {merged.get('legs', '다리 없음')}",
            f"행동은 {merged.get('action', '인사')}",
            f"움직임은 {merged.get('motion', '작은 꾸벅')}",
            f"대표 문구는 \"{phrase}\"",
        ]
        return ", ".join(parts) + "처럼 구성한다."

    def build_project(
        self,
        output_dir: Path,
        prompt: str,
        project_name: str = "missing_info_assist",
        selected_values: Optional[Dict[str, str]] = None,
        mode: str = "candidate",
        expression_count: int = 32,
    ) -> MissingInfoReport:
        analysis = self.analyze_prompt(prompt)
        selected_values = selected_values or {}
        final_prompt = self.reconstruct_prompt(prompt, analysis.detected, selected_values, mode=mode)
        safe = self._safe_name(project_name)
        out_dir = output_dir / f"{safe}_{int(time.time())}"
        out_dir.mkdir(parents=True, exist_ok=True)

        preview_report = None
        try:
            engine = TextPromptEmoticonEngine()
            preview = engine.build_project(out_dir / "generated_from_prompt", final_prompt, project_name=safe + "_generated", format_key=selected_values.get("format", analysis.detected.get("format", "animated_text")) or "animated_text", expression_count=expression_count)
            preview_report = preview.to_dict()
        except Exception as exc:  # keep report generation alive
            preview_report = {"error": str(exc)}

        csv_path = out_dir / "missing_info_candidates.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["field", "field_label", "option_label", "value", "reason", "selected"])
            writer.writeheader()
            for field, opts in analysis.candidates.items():
                for opt in opts:
                    writer.writerow({
                        "field": field,
                        "field_label": self.FIELD_LABELS.get(field, field),
                        "option_label": opt.get("label"),
                        "value": opt.get("value"),
                        "reason": opt.get("reason"),
                        "selected": selected_values.get(field, "") == opt.get("value"),
                    })

        json_path = out_dir / "missing_info_rebuild_report.json"
        html_path = out_dir / "missing_info_rebuild_report.html"
        report_dict = {
            "project_name": project_name,
            "analysis": analysis.to_dict(),
            "selected_values": selected_values,
            "final_prompt": final_prompt,
            "mode": mode,
            "preview_report": preview_report,
        }
        json_path.write_text(json.dumps(report_dict, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(self._build_html(report_dict), encoding="utf-8")

        zip_path = out_dir / f"{safe}_v28_missing_info_pack.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in [csv_path, json_path, html_path]:
                zf.write(p, p.name)
            if isinstance(preview_report, dict):
                for key in ["preview_png_path", "preview_gif_path", "html_path", "json_path", "csv_path", "zip_path"]:
                    value = preview_report.get(key)
                    if value and Path(value).exists() and Path(value).is_file():
                        zf.write(value, "generated/" + Path(value).name)
        checksum = self._checksum(zip_path)
        return MissingInfoReport(
            project_name=project_name,
            output_dir=str(out_dir),
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
            analysis=analysis.to_dict(),
            selected_values=selected_values,
            final_prompt=final_prompt,
            mode=mode,
            preview_report=preview_report,
            checksum_sha256=checksum,
        )

    def _build_html(self, data: Dict[str, Any]) -> str:
        analysis = data.get("analysis", {})
        detected = analysis.get("detected", {})
        missing = analysis.get("missing_fields", [])
        cands = analysis.get("candidates", {})
        rows = []
        for field, opts in cands.items():
            for opt in opts:
                rows.append(f"<tr><td>{html.escape(self.FIELD_LABELS.get(field, field))}</td><td>{html.escape(opt.get('label',''))}</td><td>{html.escape(opt.get('value',''))}</td><td>{html.escape(opt.get('reason',''))}</td></tr>")
        return f"""<!doctype html><html><head><meta charset='utf-8'><title>v28 누락 정보 후보 제안 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#f5f5f5}}.box{{background:#fafafa;border:1px solid #ddd;padding:12px;border-radius:8px;margin:12px 0}}</style></head><body>
<h1>v28 누락 정보 후보 제안/재구성 리포트</h1>
<div class='box'><b>원문</b><br>{html.escape(analysis.get('raw_prompt',''))}</div>
<div class='box'><b>생성 모드</b>: {html.escape(data.get('mode',''))}<br><b>최종 재구성 프롬프트</b><br>{html.escape(data.get('final_prompt',''))}</div>
<h2>감지된 정보</h2><pre>{html.escape(json.dumps(detected, ensure_ascii=False, indent=2))}</pre>
<h2>누락 필드</h2><p>{html.escape(', '.join([self.FIELD_LABELS.get(x,x) for x in missing]) or '없음')}</p>
<h2>후보 목록</h2><table><tr><th>항목</th><th>후보</th><th>값</th><th>이유</th></tr>{''.join(rows)}</table>
<h2>주의</h2><ul>{''.join(f'<li>{html.escape(w)}</li>' for w in analysis.get('warnings', [])) or '<li>고위험 키워드 없음</li>'}</ul>
</body></html>"""
