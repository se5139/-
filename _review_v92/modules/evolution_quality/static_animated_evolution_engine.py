from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Iterable, Optional
import csv
import hashlib
import html
import json
import math
import re
import shutil
import tempfile
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont, ImageSequence

try:
    from modules.animated_text_emoticon.font_utils import load_korean_font
except Exception:  # pragma: no cover
    def load_korean_font(size: int):
        return ImageFont.load_default()


@dataclass
class StaticAnimatedEvolutionReport:
    project_name: str
    output_dir: str
    source_count: int
    image_count: int
    text_count: int
    zip_count: int
    static_quality_score: int
    animated_quality_score: int
    originality_guard_score: int
    extracted_signals: List[Dict[str, Any]]
    uploaded_source_summary: List[Dict[str, Any]]
    static_quality_actions: List[Dict[str, Any]]
    animated_quality_actions: List[Dict[str, Any]]
    identity_profile: Dict[str, Any]
    static_to_animated_plan: List[Dict[str, Any]]
    expression_seed_phrases: List[Dict[str, Any]]
    candidate_apply_flow: List[Dict[str, Any]]
    html_path: str
    json_path: str
    csv_path: str
    board_png_path: str
    animated_preview_gif_path: str
    zip_path: str
    checksum_sha256: str
    safety_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StaticAnimatedEvolutionEngine:
    """v49 정지형/움직이는형 통합 품질 진화 엔진.

    핵심 원칙:
    - YouTube/인터넷 자료는 공식 API, 사용자가 직접 입력한 메모, 업로드 파일, ZIP 자료 중심으로 처리한다.
    - 기존 캐릭터의 외형을 복제하지 않고 감정 빈도, 문구 길이, 포즈, 모션 리듬, 색 대비 같은 추상 신호만 학습한다.
    - 정지형에서 확정한 캐릭터 정체성(색상, 실루엣, 말투, 얼굴 규칙)을 움직이는형 제작 계획으로 이어 붙인다.
    """

    IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".srt", ".vtt", ".log"}

    FORBIDDEN_STYLE_HINTS = [
        "춘식이", "라이언", "어피치", "카카오프렌즈", "라인프렌즈", "산리오", "헬로키티",
        "포켓몬", "피카츄", "디즈니", "짱구", "스누피", "도라에몽", "마블", "연예인 얼굴",
        "똑같이", "비슷하게", "스타일로", "따라", "모방", "복제", "트레이싱",
    ]

    EMOTION_GROUPS = {
        "인사": ["안녕", "반갑", "출근", "왔", "하이"],
        "감사": ["감사", "고마", "잘 쓸", "덕분"],
        "사과": ["죄송", "미안", "실수", "늦"],
        "확인": ["확인", "넵", "알겠", "접수", "완료"],
        "피곤": ["피곤", "번아웃", "월요", "야근", "퇴근", "살려", "졸려"],
        "응원": ["파이팅", "응원", "힘내", "할 수"],
        "당황": ["당황", "헉", "어쩐", "망", "뭐지"],
        "기쁨": ["좋아", "대박", "축하", "최고", "행복"],
        "슬픔": ["눈물", "울", "속상", "슬퍼"],
    }

    QUALITY_WORDS = {
        "static_silhouette": ["실루엣", "한눈", "단순", "큼직", "외곽선", "굵은"],
        "static_face": ["표정", "눈", "입", "눈썹", "감정", "리액션"],
        "static_text": ["문구", "멘트", "짧은", "가독", "답장", "검색"],
        "static_pose": ["포즈", "손", "몸", "기울", "따봉", "꾸벅"],
        "animated_motion": ["움직", "모션", "프레임", "흔들", "통통", "깜빡", "튀", "점프"],
        "animated_consistency": ["일관", "같은 캐릭터", "색상 유지", "비율 유지"],
        "series": ["시리즈", "2탄", "세계관", "직장", "일상", "공감"],
    }

    BASE_PHRASES = [
        ("넵", "확인", "고개 끄덕임"),
        ("확인했습니다", "확인", "체크 표시가 톡 튐"),
        ("감사합니다", "감사", "양손 모으고 반짝"),
        ("죄송합니다", "사과", "고개 숙임 + 땀방울"),
        ("잠시만요", "기다림", "한 손 들고 멈춤"),
        ("파이팅", "응원", "두 손 응원 + 통통"),
        ("살려주세요", "피곤", "축 처짐 + 흔들림"),
        ("퇴근하고 싶어요", "피곤", "말풍선이 아래로 녹음"),
        ("대박", "기쁨", "눈 반짝 + 점프"),
        ("괜찮아요", "위로", "부드러운 미소"),
    ]

    def _safe_name(self, value: str) -> str:
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in (value or "v49_static_animated_evolution"))
        return safe[:90] or "v49_static_animated_evolution"

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", text or "")
        stop = {"그리고", "하지만", "영상", "댓글", "제목", "캐릭터", "이모티콘", "사용", "후보", "파일", "업로드"}
        return [t for t in tokens if t not in stop]

    def _count_matches(self, text: str, words: Iterable[str]) -> int:
        return sum(1 for w in words if w and w in text)

    def _safe_extract_zip(self, zip_path: Path, extract_dir: Path, max_files: int = 150) -> List[Path]:
        paths: List[Path] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist()[:max_files]:
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                parts = [p for p in name.split("/") if p and p not in {".", ".."}]
                if not parts:
                    continue
                safe_rel = Path(*[re.sub(r"[^0-9A-Za-z가-힣._ -]", "_", p)[:120] for p in parts])
                target = extract_dir / safe_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                paths.append(target)
        return paths

    def collect_sources(self, input_paths: Optional[List[Path]], out_dir: Path) -> List[Path]:
        copied: List[Path] = []
        source_dir = out_dir / "uploaded_sources"
        source_dir.mkdir(parents=True, exist_ok=True)
        extract_dir = out_dir / "zip_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        for src in input_paths or []:
            if not src or not Path(src).exists() or Path(src).is_dir():
                continue
            src = Path(src)
            safe = self._safe_name(src.stem) + src.suffix.lower()
            dst = source_dir / safe
            counter = 1
            while dst.exists():
                dst = source_dir / f"{self._safe_name(src.stem)}_{counter}{src.suffix.lower()}"
                counter += 1
            shutil.copy2(src, dst)
            copied.append(dst)
            if dst.suffix.lower() == ".zip":
                try:
                    copied.extend(self._safe_extract_zip(dst, extract_dir / self._safe_name(dst.stem)))
                except Exception:
                    pass
        return copied

    def _read_text_file(self, path: Path, max_chars: int = 20000) -> str:
        try:
            if path.suffix.lower() == ".json":
                data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
                return json.dumps(data, ensure_ascii=False)[:max_chars]
            return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
        except Exception:
            try:
                return path.read_text(encoding="cp949", errors="ignore")[:max_chars]
            except Exception:
                return ""

    def _image_summary(self, path: Path) -> Dict[str, Any]:
        with Image.open(path) as img:
            frames = 1
            try:
                frames = sum(1 for _ in ImageSequence.Iterator(img)) if getattr(img, "is_animated", False) else 1
            except Exception:
                frames = 1
            rgb = img.convert("RGB").resize((24, 24))
            colors = rgb.getcolors(24 * 24) or []
            colors = sorted(colors, key=lambda x: x[0], reverse=True)[:5]
            palette = ["#%02x%02x%02x" % c for _, c in colors]
            w, h = img.size
            return {
                "name": path.name,
                "kind": "image",
                "width": w,
                "height": h,
                "frames": frames,
                "palette": palette,
                "transparent_candidate": img.mode in {"RGBA", "LA", "P"},
                "note": "이미지는 직접 복제하지 않고 색 대비/크기/프레임 정보만 품질 분석에 사용",
            }

    def summarize_sources(self, source_paths: List[Path], source_text: str, source_urls: str) -> tuple[List[Dict[str, Any]], str, int, int, int]:
        rows: List[Dict[str, Any]] = []
        text_blobs = [source_text or "", source_urls or ""]
        image_count = text_count = zip_count = 0
        for path in source_paths:
            suffix = path.suffix.lower()
            try:
                if suffix in self.IMAGE_SUFFIXES:
                    rows.append(self._image_summary(path))
                    image_count += 1
                elif suffix in self.TEXT_SUFFIXES:
                    txt = self._read_text_file(path)
                    text_blobs.append(txt)
                    rows.append({"name": path.name, "kind": "text", "chars": len(txt), "note": "문구/감정/품질 키워드만 추상 분석"})
                    text_count += 1
                elif suffix == ".zip":
                    rows.append({"name": path.name, "kind": "zip", "note": "압축 내부 자료를 안전 경로로 추출 후 분석"})
                    zip_count += 1
                else:
                    rows.append({"name": path.name, "kind": "other", "note": "파일명만 기록"})
            except Exception as exc:
                rows.append({"name": path.name, "kind": "error", "error": str(exc)[:160]})
        combined = "\n".join(text_blobs)
        return rows, combined, image_count, text_count, zip_count

    def extract_signals(self, combined_text: str, source_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tokens = self._tokenize(combined_text)
        freq: Dict[str, int] = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1
        rows: List[Dict[str, Any]] = []
        for token, count in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:35]:
            signal_type = "trend_keyword"
            for emotion, words in self.EMOTION_GROUPS.items():
                if any(w in token for w in words):
                    signal_type = f"emotion:{emotion}"
                    break
            rows.append({"signal": token, "count": count, "type": signal_type, "use": "문구/표정/상황 후보로 추상화"})
        for family, words in self.QUALITY_WORDS.items():
            count = self._count_matches(combined_text, words)
            if count:
                rows.append({"signal": family, "count": count, "type": "quality_dimension", "use": "품질 보정 우선순위"})
        # Image-derived abstract signals
        palettes = []
        animated_files = 0
        for row in source_summary:
            if row.get("kind") == "image":
                palettes.extend(row.get("palette") or [])
                if int(row.get("frames") or 1) > 1:
                    animated_files += 1
        if palettes:
            rows.append({"signal": "uploaded_palette_count", "count": len(set(palettes)), "type": "image_abstract", "use": "직접 복제 금지, 색 대비/톤 참고"})
        if animated_files:
            rows.append({"signal": "uploaded_animated_reference", "count": animated_files, "type": "motion_abstract", "use": "프레임 수/리듬 참고"})
        return rows

    def build_identity_profile(self, concept: str, target_style: str, signals: List[Dict[str, Any]], source_summary: List[Dict[str, Any]]) -> Dict[str, Any]:
        known = ["팽이버섯", "버섯", "보리", "쌀", "감자", "고구마", "메모지", "돌멩이", "먼지", "양말", "콩", "무", "종이컵", "구름", "물방울"]
        material = next((k for k in known if k in (concept or "")), "독창 소재 캐릭터")
        palettes = []
        for row in source_summary:
            if row.get("kind") == "image":
                palettes.extend(row.get("palette") or [])
        palette = list(dict.fromkeys(palettes))[:5] or ["#f6d58f", "#3d342b", "#ffffff", "#f7a8a8"]
        is_cute = "귀여" in concept or "동글" in concept or target_style == "귀엽고 세련된 카카오톡형"
        return {
            "material": material,
            "character_identity_rule": "정지형과 움직이는형 모두 같은 외곽선 굵기, 대표 색상, 눈/입 비율, 말투를 유지",
            "base_silhouette": "동글고 큰 머리 + 작은 몸" if is_cute else "단순한 소재 실루엣 + 큰 얼굴 영역",
            "line_weight": "4~6px 굵은 외곽선",
            "main_palette": palette,
            "face_rule": "눈 2개, 입 1개, 눈썹/효과선으로 감정 차이를 크게 구분",
            "pose_rule_static": "정지형은 손동작·몸기울기·효과선·말풍선 위치를 장면별로 다르게 배치",
            "pose_rule_animated": "움직이는형은 정지형 시안을 기준으로 위치/각도/표정만 단계적으로 변화",
            "tone_rule": "2~8자 짧은 답장 + 필요 시 2줄 말풍선",
            "copy_guard": "참고자료의 캐릭터 외형/상표/고유 디자인은 복제하지 않고 추상 품질 신호만 사용",
        }

    def build_static_actions(self, issue_text: str, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {"area": "후보 적용", "problem": "후보가 화면에만 보이면 제작 흐름이 끊김", "action": "선택 후보를 active_generation_profile, expression_bank, candidate_gallery, text_prompt 기본값에 저장", "result": "다음 탭에서 바로 시안/표현/프롬프트 생성"},
            {"area": "실루엣", "problem": issue_text or "정지형이 작고 밋밋함", "action": "캐릭터 본체를 360x360 중앙 70% 영역에 크게 배치하고 외곽선 4~6px 적용", "result": "작은 채팅창에서도 한눈에 보임"},
            {"area": "표정", "problem": "눈/입 변화가 약하면 정지형 생동감이 낮음", "action": "눈 모양, 입 각도, 눈썹 방향, 땀/반짝/눈물 효과를 표현마다 분리", "result": "같은 캐릭터 반복감 감소"},
            {"area": "포즈", "problem": "동일 자세 반복", "action": "인사/감사/확인/사과/피곤/응원마다 손·몸기울기·말풍선 위치를 별도 배정", "result": "멈춰 있어도 장면성이 생김"},
            {"area": "문구", "problem": "문구가 길면 사용성이 낮음", "action": "대표 문구는 2~8자, 업무형 문장은 2줄 말풍선으로 분리", "result": "카톡 답장/검색 사용성 개선"},
        ]

    def build_animated_actions(self) -> List[Dict[str, Any]]:
        return [
            {"area": "정지형→움직이는형 연결", "problem": "움직이는 캐릭터가 정지형과 다른 캐릭터처럼 보일 수 있음", "action": "정지형 대표 PNG를 기준 프레임으로 두고 위치, 각도, 눈깜빡임, 말풍선 크기만 변화", "result": "캐릭터 일관성 유지"},
            {"area": "모션 난이도", "problem": "초보자가 복잡한 프레임을 만들기 어려움", "action": "2컷/4컷/6컷/10컷 템플릿을 선택하고 기본은 4~6컷 반복 모션 사용", "result": "제작 난이도와 품질 균형"},
            {"area": "표정 모션", "problem": "몸만 움직이면 감정 전달이 약함", "action": "눈깜빡임, 입 변화, 땀/반짝/하트 효과를 프레임별로 작게 변화", "result": "짧은 WebP/GIF에서도 감정이 보임"},
            {"area": "문구 모션", "problem": "글자가 흔들리면 가독성 저하", "action": "문구는 1~2프레임 팝업 후 고정, 캐릭터만 통통/꾸벅/흔들림", "result": "가독성과 생동감 동시 확보"},
            {"area": "압축", "problem": "움직이는형은 용량 제한 위험", "action": "프레임 수/색상 수/투명 여백/반복 횟수를 검수 단계에서 자동 점검", "result": "제출 전 용량 리스크 감소"},
        ]

    def build_static_to_animated_plan(self, identity: Dict[str, Any]) -> List[Dict[str, Any]]:
        plan = []
        templates = [
            ("인사", "정지형: 한 손 들기", "움직이는형: 손 2회 흔들기 + 눈깜빡임", 6),
            ("확인", "정지형: 체크 표시", "움직이는형: 체크가 톡 튀고 고개 끄덕임", 6),
            ("감사", "정지형: 양손 모으기", "움직이는형: 몸이 살짝 꾸벅 + 반짝 효과", 8),
            ("사과", "정지형: 고개 숙임", "움직이는형: 고개 숙였다 올라오며 땀방울", 8),
            ("피곤", "정지형: 축 처진 몸", "움직이는형: 몸이 아래로 녹듯 흔들림", 6),
            ("응원", "정지형: 두 손 파이팅", "움직이는형: 통통 점프 + 작은 별", 8),
        ]
        for idx, (emotion, static_scene, animated_scene, frames) in enumerate(templates, 1):
            plan.append({
                "no": idx,
                "emotion": emotion,
                "static_base": static_scene,
                "animated_conversion": animated_scene,
                "frame_count_suggestion": frames,
                "identity_lock": identity.get("character_identity_rule"),
            })
        return plan

    def build_expression_seed(self, signals: List[Dict[str, Any]], target_formats: List[str]) -> List[Dict[str, Any]]:
        dynamic_words = [r.get("signal", "") for r in signals if r.get("type", "").startswith("emotion") and 2 <= len(str(r.get("signal", ""))) <= 10]
        phrases = list(self.BASE_PHRASES)
        for word in dynamic_words[:18]:
            phrases.append((word, "트렌드", "키워드 말풍선 + 표정 대비"))
        rows = []
        for i in range(32):
            phrase, emotion, motion = phrases[i % len(phrases)]
            rows.append({
                "no": i + 1,
                "phrase": phrase,
                "emotion": emotion,
                "static_direction": f"정지형: {motion} 장면을 한 컷으로 명확히 표현",
                "animated_direction": f"움직이는형: {motion}을 4~8프레임으로 변환",
                "format_targets": ", ".join(target_formats),
                "apply_status": "선택 시 제작 흐름에 반영 가능",
            })
        return rows

    def build_candidate_apply_flow(self) -> List[Dict[str, Any]]:
        return [
            {"step": 1, "name": "후보 선택", "effect": "선택 후보를 세션/프로젝트 JSON에 저장"},
            {"step": 2, "name": "정지형 프로필 적용", "effect": "색상·실루엣·표정·문구 규칙을 정지형 시안 기본값으로 반영"},
            {"step": 3, "name": "움직이는형 변환", "effect": "정지형 시안을 기준 프레임으로 삼아 모션 템플릿 자동 배정"},
            {"step": 4, "name": "다중/ZIP 자료 반영", "effect": "업로드 자료의 색 대비·문구 빈도·프레임 수를 추상 신호로 누적"},
            {"step": 5, "name": "갤러리/편집기 연결", "effect": "후보 갤러리, 표정/파츠 편집기, 채팅 미리보기로 이어짐"},
        ]

    def score_quality(self, signals: List[Dict[str, Any]], source_summary: List[Dict[str, Any]], animated: bool = False) -> int:
        base = 62 if not animated else 58
        dims = {r.get("signal") for r in signals if r.get("type") == "quality_dimension"}
        base += min(20, len(dims) * 3)
        if any(r.get("kind") == "image" for r in source_summary):
            base += 6
        if any((r.get("kind") == "image" and int(r.get("frames") or 1) > 1) for r in source_summary) and animated:
            base += 8
        return max(0, min(95, base))

    def originality_score(self, combined_text: str) -> tuple[int, List[str]]:
        found = [w for w in self.FORBIDDEN_STYLE_HINTS if w.lower() in (combined_text or "").lower()]
        score = max(35, 92 - len(found) * 8)
        notes = [
            "참고자료는 캐릭터 복제용이 아니라 추상 품질 신호 분석용으로만 사용합니다.",
            "YouTube/인터넷 자동 수집은 공식 API·약관·저작권 기준을 확인한 뒤 사용해야 합니다.",
            "업로드 ZIP은 안전 경로로만 추출하고 개인 문서 전체 폴더는 자동 수집하지 않습니다.",
        ]
        if found:
            notes.append("유사성 위험 키워드 감지: " + ", ".join(found[:10]))
        return score, notes

    def render_board(self, identity: Dict[str, Any], static_actions: List[Dict[str, Any]], animated_plan: List[Dict[str, Any]], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1280, 820), (247, 249, 252))
        draw = ImageDraw.Draw(img)
        title_font = load_korean_font(36)
        h_font = load_korean_font(24)
        body_font = load_korean_font(17)
        small_font = load_korean_font(14)
        draw.rounded_rectangle((28, 24, 1252, 132), 24, fill=(28, 35, 52))
        draw.text((58, 48), "v49 후보 적용 · 정지형/움직이는형 품질 진화 보드", fill=(255, 255, 255), font=title_font)
        draw.text((60, 96), f"소재: {identity.get('material')} · 규칙: 정지형과 움직이는형의 외형/색상/말투 일관성 유지", fill=(218, 226, 238), font=body_font)

        # Preview character cards
        x0 = 50
        for idx, title in enumerate(["정지형 기본", "표정 차별", "움직이는형 기준"]):
            x = x0 + idx * 275
            draw.rounded_rectangle((x, 168, x + 240, 520), 24, fill=(255, 255, 255), outline=(224, 229, 237), width=2)
            draw.text((x + 26, 190), title, fill=(35, 40, 50), font=h_font)
            cx, cy = x + 120, 335
            palette = identity.get("main_palette") or ["#f6d58f"]
            fill = palette[idx % len(palette)] if str(palette[idx % len(palette)]).startswith("#") else "#f6d58f"
            try:
                fill_rgb = tuple(int(fill.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                fill_rgb = (246, 213, 143)
            offset = 0 if idx < 2 else 12
            draw.ellipse((cx - 72, cy - 80 + offset, cx + 72, cy + 68 + offset), fill=fill_rgb, outline=(40, 36, 31), width=7)
            eye_y = cy - 10 + offset
            if idx == 1:
                draw.arc((cx - 50, eye_y - 12, cx - 26, eye_y + 12), 0, 180, fill=(40, 36, 31), width=4)
                draw.arc((cx + 26, eye_y - 12, cx + 50, eye_y + 12), 0, 180, fill=(40, 36, 31), width=4)
                draw.arc((cx - 32, cy + 22 + offset, cx + 32, cy + 58 + offset), 0, 180, fill=(40, 36, 31), width=5)
            else:
                draw.ellipse((cx - 45, eye_y - 7, cx - 31, eye_y + 7), fill=(40, 36, 31))
                draw.ellipse((cx + 31, eye_y - 7, cx + 45, eye_y + 7), fill=(40, 36, 31))
                draw.line((cx - 28, cy + 36 + offset, cx + 28, cy + 36 + offset), fill=(40, 36, 31), width=5)
            draw.rounded_rectangle((x + 34, 450, x + 206, 492), 14, fill=(255, 244, 214), outline=(225, 207, 160))
            draw.text((x + 64, 462), ["확인!", "감사합니다", "통통!"][idx], fill=(50, 45, 40), font=body_font)

        # Right action summary
        rx = 890
        draw.rounded_rectangle((rx, 168, 1230, 520), 24, fill=(255, 255, 255), outline=(224, 229, 237), width=2)
        draw.text((rx + 24, 192), "적용 흐름", fill=(35, 40, 50), font=h_font)
        bullets = [
            "후보 선택 → 실제 프로필 저장",
            "정지형 시안 → 움직이는형 기준 프레임",
            "다중 파일/ZIP → 추상 신호 분석",
            "표현 은행/갤러리/편집기 연결",
            "저작권 위험 키워드 분리",
        ]
        y = 238
        for b in bullets:
            draw.rounded_rectangle((rx + 26, y - 3, rx + 48, y + 19), 11, fill=(58, 113, 255))
            draw.text((rx + 60, y - 2), b, fill=(52, 59, 72), font=body_font)
            y += 48

        # bottom motion plan
        draw.rounded_rectangle((48, 555, 1232, 782), 24, fill=(255, 255, 255), outline=(224, 229, 237), width=2)
        draw.text((76, 578), "정지형을 그대로 움직이게 하는 모션 계획", fill=(35, 40, 50), font=h_font)
        y = 625
        for row in animated_plan[:4]:
            line = f"{row['emotion']}: {row['static_base']} → {row['animated_conversion']} · {row['frame_count_suggestion']}프레임"
            draw.text((86, y), line, fill=(65, 72, 85), font=body_font)
            y += 36
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
        return out_path

    def render_animated_preview(self, identity: Dict[str, Any], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        frames: List[Image.Image] = []
        palette = identity.get("main_palette") or ["#f6d58f"]
        fill = palette[0] if str(palette[0]).startswith("#") else "#f6d58f"
        try:
            fill_rgb = tuple(int(fill.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            fill_rgb = (246, 213, 143)
        font = load_korean_font(26)
        for i in range(12):
            img = Image.new("RGBA", (360, 360), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            bounce = int(math.sin(i / 12 * math.pi * 2) * 10)
            cx, cy = 180, 155 + bounce
            draw.ellipse((cx - 78, cy - 85, cx + 78, cy + 72), fill=fill_rgb + (255,), outline=(40, 36, 31, 255), width=7)
            # blink at two frames
            if i in {3, 9}:
                draw.line((cx - 50, cy - 8, cx - 30, cy - 8), fill=(40, 36, 31, 255), width=5)
                draw.line((cx + 30, cy - 8, cx + 50, cy - 8), fill=(40, 36, 31, 255), width=5)
            else:
                draw.ellipse((cx - 48, cy - 16, cx - 32, cy), fill=(40, 36, 31, 255))
                draw.ellipse((cx + 32, cy - 16, cx + 48, cy), fill=(40, 36, 31, 255))
            draw.arc((cx - 34, cy + 20, cx + 34, cy + 58), 0, 180, fill=(40, 36, 31, 255), width=5)
            star_y = 70 + (i % 4) * 3
            draw.text((250, star_y), "✦", fill=(255, 191, 0, 255), font=load_korean_font(32))
            bubble_scale = 1 + (0.04 if i in {1, 2, 3} else 0)
            bw, bh = int(190 * bubble_scale), int(54 * bubble_scale)
            bx, by = (360 - bw) // 2, 270
            draw.rounded_rectangle((bx, by, bx + bw, by + bh), 16, fill=(255, 246, 221, 255), outline=(220, 198, 150, 255), width=2)
            draw.text((bx + 50, by + 13), "확인!", fill=(45, 40, 35, 255), font=font)
            frames.append(img)
        frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=90, loop=0, disposal=2)
        return out_path

    def write_reports(self, report: StaticAnimatedEvolutionReport, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = Path(report.json_path)
        csv_path = Path(report.csv_path)
        html_path = Path(report.html_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["no", "phrase", "emotion", "static_direction", "animated_direction", "format_targets", "apply_status"])
            writer.writeheader()
            for row in report.expression_seed_phrases:
                writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
        def table(rows: List[Dict[str, Any]]) -> str:
            if not rows:
                return "<p>없음</p>"
            headers = list(rows[0].keys())
            head = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
            body = "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(h, '')))}</td>" for h in headers) + "</tr>" for r in rows)
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        html_text = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v49 품질 진화 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;background:#f5f7fb;color:#222;margin:32px}}.card{{background:white;border-radius:18px;padding:22px;margin:18px 0;box-shadow:0 8px 24px #0001}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #e5e8ef;padding:8px;text-align:left;font-size:13px}}th{{background:#eef3ff}}code{{background:#eef3ff;padding:2px 5px;border-radius:5px}}</style></head><body>
<h1>v49 후보 적용 · 정지형/움직이는형 품질 진화 리포트</h1>
<div class='card'><b>프로젝트:</b> {html.escape(report.project_name)}<br><b>정지형 점수:</b> {report.static_quality_score}<br><b>움직이는형 점수:</b> {report.animated_quality_score}<br><b>독창성 방어 점수:</b> {report.originality_guard_score}</div>
<div class='card'><h2>캐릭터 정체성 프로필</h2><pre>{html.escape(json.dumps(report.identity_profile, ensure_ascii=False, indent=2))}</pre></div>
<div class='card'><h2>업로드/ZIP 분석 요약</h2>{table(report.uploaded_source_summary)}</div>
<div class='card'><h2>추출 신호</h2>{table(report.extracted_signals)}</div>
<div class='card'><h2>정지형 품질 액션</h2>{table(report.static_quality_actions)}</div>
<div class='card'><h2>움직이는형 품질 액션</h2>{table(report.animated_quality_actions)}</div>
<div class='card'><h2>정지형→움직이는형 계획</h2>{table(report.static_to_animated_plan)}</div>
<div class='card'><h2>표현 씨앗</h2>{table(report.expression_seed_phrases)}</div>
<div class='card'><h2>안전 노트</h2><ul>{''.join(f'<li>{html.escape(n)}</li>' for n in report.safety_notes)}</ul></div>
</body></html>"""
        html_path.write_text(html_text, encoding="utf-8")

    def package_outputs(self, out_dir: Path, zip_path: Path) -> str:
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in out_dir.rglob("*"):
                if file.is_file() and file != zip_path:
                    zf.write(file, file.relative_to(out_dir))
        return self._checksum(zip_path)

    def build_report(
        self,
        base_output: Path,
        project_name: str,
        character_concept: str,
        issue_text: str,
        source_text: str,
        source_urls: str,
        target_formats: Optional[List[str]] = None,
        target_style: str = "귀엽고 세련된 카카오톡형",
        input_paths: Optional[List[Path]] = None,
    ) -> StaticAnimatedEvolutionReport:
        target_formats = target_formats or ["static", "animated"]
        out_dir = base_output / self._safe_name(project_name) / time.strftime("%Y%m%d_%H%M%S")
        out_dir.mkdir(parents=True, exist_ok=True)
        all_sources = self.collect_sources(input_paths, out_dir)
        source_summary, combined_text, image_count, text_count, zip_count = self.summarize_sources(all_sources, source_text, source_urls)
        signals = self.extract_signals(combined_text + "\n" + character_concept + "\n" + issue_text, source_summary)
        identity = self.build_identity_profile(character_concept, target_style, signals, source_summary)
        static_actions = self.build_static_actions(issue_text, signals)
        animated_actions = self.build_animated_actions()
        motion_plan = self.build_static_to_animated_plan(identity)
        expressions = self.build_expression_seed(signals, target_formats)
        flow = self.build_candidate_apply_flow()
        original_score, safety_notes = self.originality_score(combined_text + "\n" + character_concept + "\n" + issue_text)
        board_path = self.render_board(identity, static_actions, motion_plan, out_dir / "v49_static_animated_evolution_board.png")
        gif_path = self.render_animated_preview(identity, out_dir / "v49_static_to_animated_preview.gif")
        html_path = out_dir / "v49_static_animated_evolution_report.html"
        json_path = out_dir / "v49_static_animated_evolution_report.json"
        csv_path = out_dir / "v49_expression_seed.csv"
        zip_path = out_dir / "v49_static_animated_evolution_package.zip"
        report = StaticAnimatedEvolutionReport(
            project_name=project_name,
            output_dir=str(out_dir),
            source_count=len(all_sources),
            image_count=image_count,
            text_count=text_count,
            zip_count=zip_count,
            static_quality_score=self.score_quality(signals, source_summary, animated=False),
            animated_quality_score=self.score_quality(signals, source_summary, animated=True),
            originality_guard_score=original_score,
            extracted_signals=signals,
            uploaded_source_summary=source_summary,
            static_quality_actions=static_actions,
            animated_quality_actions=animated_actions,
            identity_profile=identity,
            static_to_animated_plan=motion_plan,
            expression_seed_phrases=expressions,
            candidate_apply_flow=flow,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            board_png_path=str(board_path),
            animated_preview_gif_path=str(gif_path),
            zip_path=str(zip_path),
            checksum_sha256="",
            safety_notes=safety_notes,
        )
        self.write_reports(report, out_dir)
        checksum = self.package_outputs(out_dir, zip_path)
        report.checksum_sha256 = checksum
        self.write_reports(report, out_dir)
        checksum = self.package_outputs(out_dir, zip_path)
        report.checksum_sha256 = checksum
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return report
