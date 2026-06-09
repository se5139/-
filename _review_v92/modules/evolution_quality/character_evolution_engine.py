from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List
import csv
import hashlib
import html
import json
import re
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class EvolutionReport:
    project_name: str
    output_dir: str
    source_count: int
    static_quality_score: int
    originality_guard_score: int
    extracted_signals: List[Dict[str, Any]]
    quality_actions: List[Dict[str, Any]]
    applied_profile: Dict[str, Any]
    expression_seed_phrases: List[Dict[str, Any]]
    html_path: str
    json_path: str
    csv_path: str
    board_png_path: str
    zip_path: str
    checksum_sha256: str
    safety_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CharacterTrendEvolutionEngine:
    """v48 진화형 캐릭터 품질 분석 엔진.

    목적:
    - YouTube/인터넷에서 얻은 제목, 설명, 댓글 메모, URL, 사용자가 직접 모은 캡처/CSV를
      '복제용'이 아니라 추상 신호로 분석한다.
    - 정지형 캐릭터가 밋밋해 보일 때 선굵기, 실루엣, 표정 대비, 포즈 다양성,
      문구 가독성, 360x360 채팅창 인식성을 개선하는 제작 프로필을 만든다.
    - 선택한 개선 프로필은 이후 텍스트 초안/표현 은행/후보 갤러리 흐름에 적용할 수 있게 한다.
    """

    EMOTION_WORDS = {
        "인사": ["안녕", "반갑", "출근", "왔"],
        "감사": ["감사", "고마"],
        "사과": ["죄송", "미안"],
        "확인": ["확인", "넵", "알겠", "접수"],
        "피곤": ["피곤", "번아웃", "월요", "야근", "퇴근", "살려"],
        "응원": ["파이팅", "응원", "힘내"],
        "당황": ["당황", "헉", "어쩐"],
        "기쁨": ["좋아", "대박", "축하", "최고"],
    }

    QUALITY_KEYWORDS = {
        "silhouette": ["심플", "단순", "한눈", "큰", "둥근", "실루엣", "굵은"],
        "face": ["표정", "눈", "입", "감정", "리액션", "눈물", "웃"],
        "text": ["문구", "멘트", "짧은", "가독", "키워드", "답장"],
        "pose": ["포즈", "손", "따봉", "꾸벅", "점프", "흔들", "움직"],
        "series": ["시리즈", "2탄", "직장", "일상", "공감", "상황"],
    }

    FORBIDDEN_STYLE_HINTS = [
        "춘식이", "라이언", "어피치", "카카오프렌즈", "라인프렌즈", "산리오", "헬로키티",
        "포켓몬", "피카츄", "디즈니", "짱구", "스누피", "도라에몽", "똑같이", "비슷하게", "스타일로", "따라",
    ]

    def _safe_name(self, value: str) -> str:
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "v48_character_evolution"))
        return safe[:90] or "v48_character_evolution"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", text or "")
        stop = {"그리고", "하지만", "영상", "댓글", "제목", "캐릭터", "이모티콘", "정도", "때문", "사용", "후보"}
        return [t for t in tokens if t not in stop]

    def _count_matches(self, text: str, words: List[str]) -> int:
        return sum(1 for w in words if w and w in text)

    def extract_signals(self, source_text: str, source_urls: str) -> List[Dict[str, Any]]:
        combined = f"{source_text}\n{source_urls}".strip()
        tokens = self._tokenize(combined)
        freq: Dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        top = sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:30]
        rows: List[Dict[str, Any]] = []
        for k, v in top:
            kind = "trend_keyword"
            for family, words in self.EMOTION_WORDS.items():
                if any(w in k for w in words):
                    kind = f"emotion:{family}"
                    break
            rows.append({"signal": k, "count": v, "type": kind, "use": "문구/표정/상황 후보로만 추상화"})
        for category, words in self.QUALITY_KEYWORDS.items():
            count = self._count_matches(combined, words)
            if count:
                rows.append({"signal": category, "count": count, "type": "quality_dimension", "use": "정지형 품질 보정 우선순위"})
        return rows

    def build_quality_actions(self, issue_text: str, target_format: str, priority: str, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        issue = issue_text or "정지형 캐릭터가 밋밋하고 후보가 실제 제작 흐름에 충분히 적용되지 않음"
        static_bias = "static" in target_format or "정지" in target_format or "멈춰" in target_format
        actions = [
            {
                "area": "선택 후보 적용",
                "problem": "후보가 표로만 남으면 제작 흐름이 끊김",
                "action": "선택한 후보를 active_text_prompt, expression_bank, candidate_gallery 입력값으로 저장",
                "result": "다음 탭에서 바로 시안/표현 세트 생성 가능",
            },
            {
                "area": "정지형 실루엣",
                "problem": issue,
                "action": "외곽선을 4~6px로 유지하고 머리/몸통 중심 덩어리를 한눈에 보이게 크게 배치",
                "result": "채팅창 작은 크기에서도 캐릭터가 흐려 보이지 않음",
            },
            {
                "area": "표정 대비",
                "problem": "정지형은 움직임이 없어서 눈/입/눈썹 정보가 약하면 밋밋함",
                "action": "표정마다 눈 모양, 입 각도, 눈썹 방향, 땀/반짝/눈물 효과를 명확히 분리",
                "result": "같은 캐릭터라도 24/32개 세트 반복감 감소",
            },
            {
                "area": "포즈 하위표현",
                "problem": "같은 감정이 같은 자세로 반복됨",
                "action": "인사=손흔듦/꾸벅/몸기울임, 확인=체크/도장/고개끄덕임, 감사=양손모음/작은하트 등으로 분화",
                "result": "움직이지 않는 포맷에서도 장면성이 생김",
            },
            {
                "area": "문구 가독성",
                "problem": "문구가 길거나 캐릭터와 겹치면 카톡 사용성이 낮아짐",
                "action": "핵심 키워드는 2~8자 중심, 긴 문구는 2줄 말풍선으로 분리, 여백 14px 이상 유지",
                "result": "이모티콘 플러스 검색/카톡 답장 사용성 강화",
            },
            {
                "area": "수집 데이터 학습",
                "problem": "인터넷/유튜브 참고가 모방으로 흐를 위험",
                "action": "제목·댓글·캡처에서 캐릭터를 베끼지 않고 감정 빈도, 문구 길이, 포즈 유형, 색 대비 같은 추상 신호만 저장",
                "result": "누적 데이터가 많아질수록 품질 추천이 개선되면서 저작권 위험을 낮춤",
            },
        ]
        if priority == "문구/사용성 우선":
            actions.insert(1, {"area": "문구 우선 설계", "problem": "그림보다 사용 상황이 먼저 보여야 함", "action": "32문구를 먼저 확정한 뒤 각 문구마다 포즈/표정 1개씩 연결", "result": "사용자가 카톡에서 고르기 쉬운 세트"})
        if static_bias:
            actions.append({"area": "정지형 전용 보정", "problem": "정지형은 모션으로 약점을 숨길 수 없음", "action": "표정 차이·몸기울기·손 파츠·효과선·말풍선 위치를 이미지마다 다르게 배정", "result": "멈춰있어도 생동감 있는 세트"})
        return actions

    def _derive_material(self, concept: str, signals: List[Dict[str, Any]]) -> str:
        known = ["팽이버섯", "버섯", "보리", "쌀", "감자", "고구마", "메모지", "돌멩이", "먼지", "양말", "콩", "무"]
        for k in known:
            if k in concept:
                return k
        for row in signals:
            s = row.get("signal", "")
            if s in known:
                return s
        return "작은 둥근 캐릭터"

    def build_applied_profile(self, concept: str, issue_text: str, target_format: str, priority: str, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        material = self._derive_material(concept, signals)
        top_words = [r["signal"] for r in signals if r.get("type", "").startswith("emotion")][:6]
        if not top_words:
            top_words = [r["signal"] for r in signals[:6]]
        phrase_hint = ", ".join(top_words[:5]) if top_words else "넵, 확인했습니다, 감사합니다"
        personality = "피곤하지만 예의 바르고 짧은 답장이 편한 성격" if any("피곤" in str(r) for r in signals) else "단순하지만 표정 반응이 분명한 성격"
        tone = "짧고 검색 가능한 카톡 답장 말투"
        recommended_prompt = (
            f"{material}를 독창 캐릭터로 만들고, {personality}이며, {tone}를 사용한다. "
            f"정지형에서도 밋밋하지 않도록 굵은 외곽선, 큰 실루엣, 선명한 눈/입 표정, 손동작 하위표현, "
            f"짧은 문구 말풍선을 적용한다. 대표 문구는 \"확인했습니다\"이고 참고 키워드는 {phrase_hint}이다."
        )
        return {
            "material": material,
            "base_shape": "둥근형" if material == "작은 둥근 캐릭터" else "소재형 단순 실루엣",
            "personality": personality,
            "tone": tone,
            "target_format": target_format,
            "priority": priority,
            "line_weight": "4~6px 굵은 외곽선",
            "silhouette": "360x360 중앙에 크게 보이는 단순 덩어리",
            "face_rule": "눈/입/눈썹 차이를 표현마다 명확히 분리",
            "pose_rule": "손동작·몸기울기·효과선을 표현마다 다르게 적용",
            "text_rule": "2~8자 핵심 문구 우선, 긴 문구는 2줄 말풍선",
            "recommended_prompt": recommended_prompt,
            "apply_targets": ["v27 텍스트 설명 초안", "v28 누락 후보 적용", "표현 은행", "후보 갤러리", "채팅창 미리보기"],
        }

    def build_expression_seed(self, signals: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        base = [
            ("넵", "확인", "체크 표시 + 작은 고개 끄덕임"),
            ("확인했습니다", "확인", "도장처럼 체크"),
            ("감사합니다", "감사", "양손 모으고 작은 미소"),
            ("죄송합니다", "사과", "고개 숙임 + 땀 한 방울"),
            ("파이팅", "응원", "두 손 응원 + 반짝"),
            ("살려주세요", "피곤", "축 처진 몸 + 반눈"),
            ("퇴근하고 싶어요", "피곤", "녹아내리는 자세"),
            ("잠시만요", "기다림", "한 손 들고 멈춤"),
        ]
        signal_words = [r.get("signal", "") for r in signals if r.get("signal")]
        for w in signal_words[:16]:
            if len(w) <= 10:
                base.append((w, "트렌드", "키워드 말풍선 + 표정 대비"))
        rows = []
        for i in range(32):
            phrase, category, pose = base[i % len(base)]
            rows.append({
                "no": i + 1,
                "category": category,
                "phrase": phrase,
                "usage_score": max(60, 92 - (i % 10) * 3),
                "emotion": category,
                "format_hint": profile.get("target_format", "static_text"),
                "motion_hint": pose,
                "static_quality_note": "정지형에서도 포즈/표정/효과가 다르게 보이도록 적용",
            })
        return rows

    def render_board(self, profile: Dict[str, Any], actions: List[Dict[str, Any]], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1200, 760), (250, 250, 247))
        draw = ImageDraw.Draw(img)
        title_font = load_korean_font(36)
        h_font = load_korean_font(24)
        body_font = load_korean_font(18)
        small_font = load_korean_font(15)
        draw.text((36, 26), "v48 정지형 캐릭터 품질 진화 보드", fill=(35, 35, 35), font=title_font)
        draw.text((38, 82), f"적용 소재: {profile.get('material')} · 목표: {profile.get('target_format')} · 우선순위: {profile.get('priority')}", fill=(70, 70, 70), font=body_font)
        # three character variants
        centers = [(185, 270), (380, 270), (575, 270)]
        captions = ["큰 실루엣", "표정 대비", "포즈 하위표현"]
        for idx, (cx, cy) in enumerate(centers):
            fill = [(226, 181, 105), (244, 235, 205), (198, 166, 118)][idx]
            outline = (40, 36, 31)
            draw.ellipse((cx-75, cy-85, cx+75, cy+70), fill=fill, outline=outline, width=7)
            draw.ellipse((cx-52, cy-8, cx-35, cy+8), fill=outline)
            draw.ellipse((cx+35, cy-8, cx+52, cy+8), fill=outline)
            if idx == 0:
                draw.arc((cx-34, cy+24, cx+34, cy+58), 0, 180, fill=outline, width=5)
            elif idx == 1:
                draw.line((cx-35, cy+38, cx+35, cy+38), fill=outline, width=5)
                draw.arc((cx+55, cy-2, cx+78, cy+35), 60, 160, fill=(70, 155, 220), width=4)
            else:
                draw.arc((cx-38, cy+18, cx+38, cy+58), 0, 180, fill=outline, width=5)
                draw.line((cx+72, cy+28, cx+122, cy-10), fill=outline, width=7)
                draw.line((cx+116, cy-14, cx+136, cy-32), fill=outline, width=5)
            draw.rounded_rectangle((cx-85, cy+102, cx+85, cy+150), radius=17, fill=(255,255,255), outline=outline, width=3)
            draw.text((cx-58, cy+115), captions[idx], fill=(30,30,30), font=small_font)
        # action table
        draw.rounded_rectangle((730, 142, 1145, 616), radius=22, fill=(255,255,255), outline=(210,210,210), width=2)
        draw.text((760, 170), "적용 규칙", fill=(35,35,35), font=h_font)
        y = 214
        for action in actions[:7]:
            area = str(action.get("area", ""))[:18]
            result = str(action.get("result", ""))[:34]
            draw.text((760, y), f"• {area}", fill=(35,35,35), font=body_font)
            draw.text((782, y+28), result, fill=(80,80,80), font=small_font)
            y += 58
        draw.rounded_rectangle((42, 606, 1145, 718), radius=20, fill=(255,255,255), outline=(215,215,215), width=2)
        prompt = str(profile.get("recommended_prompt", ""))
        lines = [prompt[i:i+74] for i in range(0, min(len(prompt), 220), 74)]
        draw.text((66, 628), "다음 생성에 적용될 추천 프롬프트", fill=(35,35,35), font=h_font)
        yy = 662
        for line in lines[:3]:
            draw.text((66, yy), line, fill=(75,75,75), font=small_font)
            yy += 23
        img.save(out_path)
        return out_path

    def build_report(
        self,
        output_dir: Path,
        project_name: str,
        character_concept: str,
        issue_text: str,
        source_text: str,
        source_urls: str,
        target_format: str = "static_text",
        priority: str = "정지형 품질 우선",
    ) -> EvolutionReport:
        safe = self._safe_name(project_name)
        root = output_dir / safe
        root.mkdir(parents=True, exist_ok=True)
        combined_sources = f"{source_text}\n{source_urls}\n{character_concept}\n{issue_text}"
        signals = self.extract_signals(source_text + "\n" + character_concept + "\n" + issue_text, source_urls)
        actions = self.build_quality_actions(issue_text, target_format, priority, signals)
        profile = self.build_applied_profile(character_concept, issue_text, target_format, priority, signals)
        seeds = self.build_expression_seed(signals, profile)
        danger = [w for w in self.FORBIDDEN_STYLE_HINTS if w in combined_sources]
        originality_guard = 100 - min(50, len(danger) * 10)
        static_quality_score = min(98, 62 + len([s for s in signals if s.get("type") == "quality_dimension"]) * 6 + len([s for s in signals if str(s.get("type", "")).startswith("emotion")]) * 2)
        safety_notes = [
            "유튜브/인터넷 자료는 캐릭터 모방용이 아니라 감정 빈도·문구 길이·포즈 유형 같은 추상 신호로만 사용합니다.",
            "기존 캐릭터명·상표·저작물과 비슷하게 만들라는 입력은 위험 신호로 기록하고 독창 방향으로 전환합니다.",
            "자동 웹 수집은 각 사이트 약관/API 정책 확인 후 사용해야 하며, 기본값은 사용자 입력/CSV/공식 API 기반입니다.",
        ]
        if danger:
            safety_notes.append("위험 키워드 감지: " + ", ".join(danger))
        board_path = self.render_board(profile, actions, root / "v48_static_quality_evolution_board.png")
        csv_path = root / "v48_expression_seed_phrases.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(seeds[0].keys()))
            writer.writeheader()
            writer.writerows(seeds)
        json_path = root / "v48_character_evolution_report.json"
        html_path = root / "v48_character_evolution_report.html"
        zip_path = root / "v48_character_evolution_package.zip"
        payload = {
            "project_name": project_name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source_count": len([x for x in [source_text.strip(), source_urls.strip()] if x]),
            "static_quality_score": static_quality_score,
            "originality_guard_score": originality_guard,
            "extracted_signals": signals,
            "quality_actions": actions,
            "applied_profile": profile,
            "expression_seed_phrases": seeds,
            "safety_notes": safety_notes,
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        html_rows = "".join(f"<tr><td>{html.escape(str(a.get('area','')))}</td><td>{html.escape(str(a.get('action','')))}</td><td>{html.escape(str(a.get('result','')))}</td></tr>" for a in actions)
        signal_rows = "".join(f"<tr><td>{html.escape(str(s.get('signal','')))}</td><td>{s.get('count','')}</td><td>{html.escape(str(s.get('type','')))}</td></tr>" for s in signals[:30])
        html_path.write_text(f"""
<!doctype html><html><head><meta charset='utf-8'><title>v48 Character Evolution</title>
<style>body{{font-family:Arial,sans-serif;line-height:1.55;padding:28px}} table{{border-collapse:collapse;width:100%;margin:12px 0}} td,th{{border:1px solid #ddd;padding:8px}} th{{background:#f4f4f4}} code{{background:#f7f7f7;padding:2px 4px}}</style></head>
<body><h1>v48 진화형 캐릭터 품질 분석 리포트</h1>
<p><b>정지형 품질 점수:</b> {static_quality_score} / <b>독창성 방어 점수:</b> {originality_guard}</p>
<h2>적용 프로필</h2><pre>{html.escape(json.dumps(profile, ensure_ascii=False, indent=2))}</pre>
<h2>품질 개선 액션</h2><table><tr><th>영역</th><th>적용</th><th>결과</th></tr>{html_rows}</table>
<h2>추출 신호</h2><table><tr><th>신호</th><th>빈도</th><th>유형</th></tr>{signal_rows}</table>
<h2>안전 노트</h2><ul>{''.join('<li>'+html.escape(n)+'</li>' for n in safety_notes)}</ul>
</body></html>
""", encoding="utf-8")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in [json_path, html_path, csv_path, board_path]:
                z.write(p, p.name)
        return EvolutionReport(
            project_name=project_name,
            output_dir=str(root),
            source_count=payload["source_count"],
            static_quality_score=static_quality_score,
            originality_guard_score=originality_guard,
            extracted_signals=signals,
            quality_actions=actions,
            applied_profile=profile,
            expression_seed_phrases=seeds,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            board_png_path=str(board_path),
            zip_path=str(zip_path),
            checksum_sha256=self._checksum(zip_path),
            safety_notes=safety_notes,
        )
