
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover - optional in some environments
    Image = None
    ImageDraw = None


TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".srt", ".vtt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
ZIP_EXTENSIONS = {".zip"}
SAFE_EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS | ZIP_EXTENSIONS

FORBIDDEN_COPY_TERMS = [
    "춘식이", "라이언", "어피치", "카카오프렌즈", "라인프렌즈", "브라운", "코니",
    "산리오", "헬로키티", "포켓몬", "피카츄", "디즈니", "미키", "짱구", "스누피",
    "비슷하게", "똑같이", "따라그", "모방", "복제", "스타일로", "느낌으로",
]

EMOTION_KEYWORDS = {
    "인사": ["안녕", "하이", "굿모닝", "출근"],
    "감사": ["감사", "고마", "땡큐"],
    "사과": ["죄송", "미안", "쏘리"],
    "확인": ["확인", "넵", "네", "알겠", "접수"],
    "피곤": ["피곤", "졸려", "월요", "번아웃", "퇴근", "야근"],
    "응원": ["파이팅", "화이팅", "응원", "힘내"],
    "축하": ["축하", "생일", "합격", "대박"],
    "당황": ["헉", "어쩌", "당황", "멘붕"],
    "분노": ["화남", "부들", "열받", "짜증"],
    "애정": ["하트", "좋아", "보고", "사랑"],
}

MOTION_KEYWORDS = {
    "눈깜빡임": ["깜빡", "눈", "blink"],
    "통통 점프": ["통통", "점프", "bounce"],
    "말풍선 팝업": ["말풍선", "팝업", "톡", "카톡"],
    "손 흔들기": ["흔들", "인사", "wave"],
    "눈물 흐름": ["눈물", "울", "훌쩍"],
    "하트 등장": ["하트", "애정", "heart"],
    "화면 흔들림": ["분노", "부들", "흔들"],
}

@dataclass
class FreeApiSafetyConfig:
    project_name: str = "v50_free_api_safety"
    days: int = 30
    youtube_enabled: bool = False
    google_search_enabled: bool = False
    openai_enabled: bool = False
    paid_calls_allowed: bool = False
    daily_youtube_search_limit: int = 20
    daily_youtube_video_limit: int = 200
    daily_youtube_comment_limit: int = 100
    daily_openai_call_limit: int = 0
    monthly_budget_limit_krw: int = 0
    local_first: bool = True
    store_raw_api_keys: bool = False

@dataclass
class QuotaSnapshot:
    service: str
    enabled: bool
    hard_limit: int
    used_today: int
    remaining_today: int
    paid_calls_allowed: bool
    estimated_cost_krw: int
    status: str

@dataclass
class LocalSourceSummary:
    file_name: str
    source_type: str
    size_bytes: int
    sha256_prefix: str
    extracted_text_chars: int
    extracted_image_hint: str
    warning: str

@dataclass
class V50Report:
    project_name: str
    created_at: str
    mode: str
    days: int
    api_key_status: dict[str, Any]
    quota_snapshots: list[dict[str, Any]]
    paid_call_guard: dict[str, Any]
    local_source_summary: list[dict[str, Any]]
    extracted_signals: dict[str, Any]
    quality_actions: list[dict[str, Any]]
    collection_plan: list[dict[str, Any]]
    workflow_application: dict[str, Any]
    html_path: str
    json_path: str
    csv_path: str
    board_png_path: str
    zip_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FreeApiSafetyEngine:
    """Free-mode collector/planner for the Kakao emoticon project.

    The engine is intentionally local-first. It never stores raw API keys in
    reports, never enables paid calls by default, and treats external APIs as
    optional inputs behind quota counters.
    """

    def __init__(self, usage_state_path: str | Path | None = None) -> None:
        self.usage_state_path = Path(usage_state_path) if usage_state_path else None

    def build_report(
        self,
        output_dir: str | Path,
        config: FreeApiSafetyConfig | None = None,
        local_input_paths: Iterable[str | Path] | None = None,
        manual_notes: str = "",
        youtube_api_key: str = "",
        google_api_key: str = "",
        openai_api_key: str = "",
        search_keywords: str = "직장인 공감 이모티콘, 짧은 답장, 카카오톡 문구",
    ) -> V50Report:
        config = config or FreeApiSafetyConfig()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_days = max(1, min(int(config.days), 30))
        raw_api_keys = {
            "youtube_api_key": youtube_api_key,
            "google_api_key": google_api_key,
            "openai_api_key": openai_api_key,
        }
        api_key_status = self._api_key_status(raw_api_keys, config)
        paid_call_guard = self._build_paid_call_guard(config)
        quota_snapshots = self._quota_snapshots(config)
        local_summary, extracted_text = self._analyze_local_sources(local_input_paths or [], output_dir)

        combined_text = "\n".join([manual_notes or "", search_keywords or "", extracted_text])
        signals = self._extract_quality_signals(combined_text, local_summary)
        quality_actions = self._build_quality_actions(signals)
        collection_plan = self._build_collection_plan(config, search_keywords, safe_days)
        workflow_application = self._build_workflow_application(signals, quality_actions)

        report_core = {
            "project_name": config.project_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": "FREE_LOCAL_FIRST" if not config.paid_calls_allowed else "USER_APPROVED_PAID_MODE",
            "days": safe_days,
            "api_key_status": api_key_status,
            "quota_snapshots": [asdict(s) for s in quota_snapshots],
            "paid_call_guard": paid_call_guard,
            "local_source_summary": [asdict(x) for x in local_summary],
            "extracted_signals": signals,
            "quality_actions": quality_actions,
            "collection_plan": collection_plan,
            "workflow_application": workflow_application,
        }

        json_path = output_dir / "v50_free_api_safety_report.json"
        csv_path = output_dir / "v50_quality_actions.csv"
        html_path = output_dir / "v50_free_api_safety_report.html"
        board_png_path = output_dir / "v50_free_mode_board.png"
        zip_path = output_dir / "v50_free_api_safety_package.zip"

        json_path.write_text(json.dumps(report_core, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_csv(csv_path, quality_actions)
        self._write_html(html_path, report_core)
        self._write_board_png(board_png_path, report_core)
        self._write_zip(zip_path, [json_path, csv_path, html_path, board_png_path])

        return V50Report(
            **report_core,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            board_png_path=str(board_png_path),
            zip_path=str(zip_path),
        )

    def _api_key_status(self, raw_api_keys: dict[str, str], config: FreeApiSafetyConfig) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, key in raw_api_keys.items():
            cleaned = (key or "").strip()
            result[name.replace("_api_key", "")] = {
                "present": bool(cleaned),
                "stored": bool(config.store_raw_api_keys and cleaned),
                "masked_preview": self._mask_key(cleaned),
                "note": "세션 입력값으로만 사용하고 리포트에는 원문 저장 금지" if cleaned else "미입력 - 로컬 분석 우선",
            }
        return result

    def _mask_key(self, key: str) -> str:
        if not key:
            return ""
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"

    def _build_paid_call_guard(self, config: FreeApiSafetyConfig) -> dict[str, Any]:
        return {
            "paid_calls_allowed": bool(config.paid_calls_allowed),
            "monthly_budget_limit_krw": int(config.monthly_budget_limit_krw),
            "openai_default_enabled": bool(config.openai_enabled),
            "google_search_default_enabled": bool(config.google_search_enabled),
            "block_reason": "무료 모드에서는 유료 호출과 예산 초과 호출을 실행하지 않습니다." if not config.paid_calls_allowed else "사용자가 유료 호출을 명시 승인한 상태입니다.",
            "safety_default": "무료/로컬 우선",
        }

    def _quota_snapshots(self, config: FreeApiSafetyConfig) -> list[QuotaSnapshot]:
        today_usage = self._read_today_usage()
        specs = [
            ("youtube_search", config.youtube_enabled, config.daily_youtube_search_limit),
            ("youtube_videos", config.youtube_enabled, config.daily_youtube_video_limit),
            ("youtube_comments", config.youtube_enabled, config.daily_youtube_comment_limit),
            ("google_search", config.google_search_enabled, 0),
            ("openai_analysis", config.openai_enabled, config.daily_openai_call_limit),
        ]
        rows: list[QuotaSnapshot] = []
        for service, enabled, limit in specs:
            used = int(today_usage.get(service, 0))
            remaining = max(0, limit - used)
            status = "OFF" if not enabled else ("LIMIT_REACHED" if remaining <= 0 else "READY")
            estimated_cost = 0 if not config.paid_calls_allowed else max(0, used) * 1
            rows.append(QuotaSnapshot(service, enabled, limit, used, remaining, config.paid_calls_allowed, estimated_cost, status))
        return rows

    def _read_today_usage(self) -> dict[str, int]:
        if not self.usage_state_path or not self.usage_state_path.exists():
            return {}
        try:
            data = json.loads(self.usage_state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        today = datetime.now().strftime("%Y-%m-%d")
        return data.get(today, {}) if isinstance(data, dict) else {}

    def _analyze_local_sources(self, paths: Iterable[str | Path], output_dir: Path) -> tuple[list[LocalSourceSummary], str]:
        summaries: list[LocalSourceSummary] = []
        collected_text: list[str] = []
        unpack_dir = output_dir / "local_source_extracts"
        unpack_dir.mkdir(parents=True, exist_ok=True)

        for raw_path in list(paths)[:60]:
            path = Path(raw_path)
            if not path.exists() or not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in SAFE_EXTENSIONS:
                summaries.append(self._summary(path, "blocked", 0, "", f"지원하지 않는 확장자: {suffix}"))
                continue
            if suffix in ZIP_EXTENSIONS:
                zip_summaries, zip_text = self._safe_extract_and_analyze_zip(path, unpack_dir)
                summaries.extend(zip_summaries)
                collected_text.append(zip_text)
            elif suffix in TEXT_EXTENSIONS:
                text = self._read_text_file(path)
                collected_text.append(text)
                summaries.append(self._summary(path, "text", len(text), "", ""))
            elif suffix in IMAGE_EXTENSIONS:
                hint = self._analyze_image_hint(path)
                summaries.append(self._summary(path, "image", 0, hint, ""))
        return summaries, "\n".join(collected_text)

    def _safe_extract_and_analyze_zip(self, zip_path: Path, unpack_dir: Path) -> tuple[list[LocalSourceSummary], str]:
        summaries: list[LocalSourceSummary] = []
        text_chunks: list[str] = []
        max_files = 120
        max_total_bytes = 40 * 1024 * 1024
        total_bytes = 0
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()[:max_files]
                for name in names:
                    info = zf.getinfo(name)
                    if info.is_dir():
                        continue
                    total_bytes += int(info.file_size)
                    if total_bytes > max_total_bytes:
                        summaries.append(self._summary(zip_path, "zip", 0, "", "ZIP 분석 한도를 초과해 일부 파일은 건너뜀"))
                        break
                    safe_name = Path(name).name
                    suffix = Path(safe_name).suffix.lower()
                    if suffix not in (TEXT_EXTENSIONS | IMAGE_EXTENSIONS):
                        continue
                    target = unpack_dir / f"zip_{hashlib.sha1(name.encode()).hexdigest()[:10]}_{safe_name}"
                    data = zf.read(name)
                    target.write_bytes(data)
                    if suffix in TEXT_EXTENSIONS:
                        text = self._read_text_file(target)
                        text_chunks.append(text)
                        summaries.append(self._summary(target, "zip_text", len(text), "", f"from {zip_path.name}"))
                    elif suffix in IMAGE_EXTENSIONS:
                        hint = self._analyze_image_hint(target)
                        summaries.append(self._summary(target, "zip_image", 0, hint, f"from {zip_path.name}"))
        except Exception as exc:
            summaries.append(self._summary(zip_path, "zip_error", 0, "", str(exc)))
        return summaries, "\n".join(text_chunks)

    def _summary(self, path: Path, source_type: str, text_chars: int, image_hint: str, warning: str) -> LocalSourceSummary:
        try:
            data = path.read_bytes()
        except Exception:
            data = b""
        return LocalSourceSummary(
            file_name=path.name,
            source_type=source_type,
            size_bytes=len(data),
            sha256_prefix=hashlib.sha256(data).hexdigest()[:16] if data else "",
            extracted_text_chars=int(text_chars),
            extracted_image_hint=image_hint,
            warning=warning,
        )

    def _read_text_file(self, path: Path) -> str:
        data = path.read_bytes()[:800_000]
        for encoding in ["utf-8-sig", "utf-8", "cp949", "euc-kr", "latin-1"]:
            try:
                return data.decode(encoding, errors="ignore")
            except Exception:
                continue
        return data.decode("utf-8", errors="ignore")

    def _analyze_image_hint(self, path: Path) -> str:
        if Image is None:
            return "Pillow 미설치 - 이미지 메타 분석 생략"
        try:
            img = Image.open(path).convert("RGBA")
            w, h = img.size
            px = img.resize((1, 1)).getpixel((0, 0))
            alpha_hint = "투명도 있음" if px[3] < 255 or (img.getextrema()[3][0] < 255) else "불투명 배경"
            ratio = round(w / h, 2) if h else 0
            return f"{w}x{h}, 비율 {ratio}, 평균색 rgba{px}, {alpha_hint}"
        except Exception as exc:
            return f"이미지 분석 실패: {exc}"

    def _extract_quality_signals(self, text: str, local_summary: list[LocalSourceSummary]) -> dict[str, Any]:
        normalized = re.sub(r"\s+", " ", text or "").strip()
        lower = normalized.lower()
        words = re.findall(r"[가-힣A-Za-z0-9]{2,20}", normalized)
        freq: dict[str, int] = {}
        for word in words:
            freq[word] = freq.get(word, 0) + 1
        top_keywords = sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:30]

        emotion_counts = {}
        for emotion, keys in EMOTION_KEYWORDS.items():
            emotion_counts[emotion] = sum(lower.count(k.lower()) for k in keys)
        motion_counts = {}
        for motion, keys in MOTION_KEYWORDS.items():
            motion_counts[motion] = sum(lower.count(k.lower()) for k in keys)

        risk_terms = [term for term in FORBIDDEN_COPY_TERMS if term.lower() in lower]
        image_count = sum(1 for s in local_summary if "image" in s.source_type)
        text_count = sum(1 for s in local_summary if "text" in s.source_type)
        zip_count = sum(1 for s in local_summary if s.source_type.startswith("zip"))
        avg_phrase_len = round(sum(len(w) for w in words[:100]) / max(1, min(100, len(words))), 1)

        return {
            "top_keywords": top_keywords,
            "emotion_counts": emotion_counts,
            "motion_counts": motion_counts,
            "risk_terms": risk_terms,
            "image_count": image_count,
            "text_count": text_count,
            "zip_count": zip_count,
            "avg_phrase_len": avg_phrase_len,
            "raw_text_chars": len(normalized),
        }

    def _build_quality_actions(self, signals: dict[str, Any]) -> list[dict[str, Any]]:
        top_emotions = sorted(signals.get("emotion_counts", {}).items(), key=lambda x: (-x[1], x[0]))[:5]
        top_motions = sorted(signals.get("motion_counts", {}).items(), key=lambda x: (-x[1], x[0]))[:5]
        risk_terms = signals.get("risk_terms", [])
        actions = [
            {
                "area": "정지형 캐릭터",
                "priority": "HIGH",
                "action": "한눈에 보이는 외곽선·실루엣·큰 표정 차이를 먼저 고정",
                "reason": "정지형은 360×360 작은 화면에서 즉시 읽혀야 하므로 형태 대비가 중요",
            },
            {
                "area": "움직이는형 캐릭터",
                "priority": "HIGH",
                "action": "정지형 PNG를 1프레임 기준으로 삼고 눈깜빡임·통통 점프·말풍선 팝업만 추가",
                "reason": "외형 일관성을 유지하면서 움직임 제작 난이도를 낮춤",
            },
            {
                "area": "로컬/ZIP 분석",
                "priority": "MEDIUM",
                "action": f"업로드 이미지 {signals.get('image_count', 0)}개, 텍스트 {signals.get('text_count', 0)}개, ZIP 항목 {signals.get('zip_count', 0)}개를 추상 신호로만 반영",
                "reason": "자료 원본 복제 대신 품질 기준과 말투 경향만 누적",
            },
            {
                "area": "무료 API 안전장치",
                "priority": "HIGH",
                "action": "API 키 입력은 선택값으로 두고 쿼터 카운터·30일 제한·유료 호출 차단을 기본값으로 유지",
                "reason": "초기 운영 비용 0원 목표와 과금 사고 방지",
            },
        ]
        if top_emotions:
            actions.append({"area": "문구/감정", "priority": "MEDIUM", "action": "상위 감정 축: " + ", ".join(k for k, _ in top_emotions), "reason": "30일 메모/자료에서 반복된 감정 신호"})
        if top_motions:
            actions.append({"area": "모션", "priority": "MEDIUM", "action": "우선 모션 축: " + ", ".join(k for k, _ in top_motions), "reason": "움직이는형 변환에 바로 쓰기 쉬운 저난이도 모션"})
        if risk_terms:
            actions.append({"area": "저작권/상표권", "priority": "BLOCK", "action": "모방 위험 키워드 제거: " + ", ".join(risk_terms), "reason": "기존 캐릭터 복제·유사 표현 위험"})
        return actions

    def _build_collection_plan(self, config: FreeApiSafetyConfig, search_keywords: str, days: int) -> list[dict[str, Any]]:
        keywords = [x.strip() for x in re.split(r"[,\n]", search_keywords or "") if x.strip()][:8]
        plan = [
            {"step": 1, "name": "로컬 파일/ZIP 분석", "enabled": True, "cost": "0원", "limit": "파일 60개/ZIP 내부 120개/40MB 안전 한도", "keywords": "사용자 업로드"},
            {"step": 2, "name": "수동 URL/자막/메모 분석", "enabled": True, "cost": "0원", "limit": f"최근 {days}일 기준 메모만 반영", "keywords": keywords},
            {"step": 3, "name": "YouTube API 검색", "enabled": bool(config.youtube_enabled), "cost": "무료 쿼터 안에서만", "limit": f"일 {config.daily_youtube_search_limit}회 이하", "keywords": keywords},
            {"step": 4, "name": "Google 검색 API", "enabled": bool(config.google_search_enabled), "cost": "기본 OFF", "limit": "사용자가 켠 경우만", "keywords": keywords},
            {"step": 5, "name": "OpenAI 고급 분석", "enabled": bool(config.openai_enabled), "cost": "기본 OFF / 사용자 승인 필요", "limit": f"일 {config.daily_openai_call_limit}회", "keywords": "로컬 분석 결과 요약본만 전달"},
        ]
        return plan

    def _build_workflow_application(self, signals: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any]:
        top_words = [k for k, _ in signals.get("top_keywords", [])[:12]]
        emotion_counts = signals.get("emotion_counts", {})
        motion_counts = signals.get("motion_counts", {})
        top_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "확인"
        top_motion = max(motion_counts, key=motion_counts.get) if motion_counts else "눈깜빡임"
        phrases = []
        seed_map = {
            "확인": ["넵", "확인했습니다", "바로 볼게요", "접수했습니다"],
            "피곤": ["오늘도 버팁니다", "퇴근하고 싶어요", "잠시 충전 중", "영혼은 퇴근"],
            "감사": ["감사합니다", "덕분이에요", "고맙습니다", "잘 받았습니다"],
            "사과": ["죄송합니다", "다음엔 더 잘할게요", "미안해요", "잠시만요"],
            "응원": ["파이팅", "할 수 있어요", "조용히 응원", "힘내요"],
        }
        phrases.extend(seed_map.get(top_emotion, seed_map["확인"]))
        phrases.extend([w for w in top_words if 2 <= len(w) <= 12])
        unique_phrases = []
        for p in phrases:
            if p and p not in unique_phrases:
                unique_phrases.append(p)
        return {
            "active_generation_profile": {
                "source": "v50_free_api_safety_mode",
                "top_emotion": top_emotion,
                "top_motion": top_motion,
                "local_first": True,
                "paid_calls_blocked": True,
            },
            "expression_seed_phrases": [
                {"no": i + 1, "category": top_emotion, "phrase": p, "usage_score": max(60, 96 - i * 2), "emotion": top_emotion, "format_hint": "static_and_animated", "motion_hint": top_motion}
                for i, p in enumerate(unique_phrases[:32])
            ],
            "recommended_prompt": f"{top_emotion} 감정과 {top_motion} 모션을 중심으로, 정지형 캐릭터를 먼저 고정한 뒤 같은 외형을 유지해 움직이는형으로 확장한다.",
            "blocked_risk_terms": signals.get("risk_terms", []),
            "quality_action_count": len(actions),
        }

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            fieldnames = ["area", "priority", "action", "reason"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

    def _write_html(self, path: Path, data: dict[str, Any]) -> None:
        esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows = "".join(f"<tr><td>{esc(a.get('area'))}</td><td>{esc(a.get('priority'))}</td><td>{esc(a.get('action'))}</td><td>{esc(a.get('reason'))}</td></tr>" for a in data.get("quality_actions", []))
        html = f"""<!doctype html><html lang='ko'><meta charset='utf-8'><title>v50 Free API Safety Report</title>
        <style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:32px;background:#f6f8fb;color:#111827}}.card{{background:#fff;border:1px solid #e5e7eb;border-radius:18px;padding:18px;margin:14px 0;box-shadow:0 8px 24px rgba(15,23,42,.06)}}table{{border-collapse:collapse;width:100%;background:#fff}}td,th{{border:1px solid #e5e7eb;padding:9px}}th{{background:#eff6ff}}</style>
        <h1>v50 무료 API 수집 안전모드 리포트</h1>
        <div class='card'><b>모드:</b> {esc(data.get('mode'))} · <b>수집 기준:</b> 최근 {esc(data.get('days'))}일 · <b>유료 호출:</b> {esc(data.get('paid_call_guard',{}).get('paid_calls_allowed'))}</div>
        <div class='card'><h2>품질 개선 액션</h2><table><tr><th>영역</th><th>우선순위</th><th>액션</th><th>근거</th></tr>{rows}</table></div>
        <div class='card'><h2>추출 신호</h2><pre>{esc(json.dumps(data.get('extracted_signals', {}), ensure_ascii=False, indent=2))}</pre></div>
        </html>"""
        path.write_text(html, encoding="utf-8")

    def _write_board_png(self, path: Path, data: dict[str, Any]) -> None:
        if Image is None or ImageDraw is None:
            path.write_bytes(b"")
            return
        img = Image.new("RGB", (1200, 760), "#f6f8fb")
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((40, 40, 1160, 180), radius=28, fill="#1f2937")
        draw.text((70, 80), "v50 Free API Safety Mode", fill="white")
        draw.text((70, 115), "Local ZIP/File First · 30-day collection · quota counter · paid-call block", fill="#dbeafe")
        cards = [
            ("API Key", "optional / masked"), ("Paid Calls", "blocked by default"),
            ("Local Analysis", "first priority"), ("Days", str(data.get("days", 30))),
            ("Quality", "static + animated"), ("Risk", "copy terms blocked"),
        ]
        x0, y0 = 60, 220
        for i, (title, value) in enumerate(cards):
            x = x0 + (i % 3) * 370
            y = y0 + (i // 3) * 180
            draw.rounded_rectangle((x, y, x + 320, y + 125), radius=22, fill="white", outline="#dbe4f0")
            draw.text((x + 24, y + 28), title, fill="#1f2937")
            draw.text((x + 24, y + 70), value, fill="#2563eb")
        img.save(path)

    def _write_zip(self, zip_path: Path, paths: list[Path]) -> None:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in paths:
                if path.exists() and path.is_file() and path.stat().st_size > 0:
                    zf.write(path, arcname=path.name)
