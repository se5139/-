
from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".srt", ".vtt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
ZIP_EXTENSIONS = {".zip"}
SAFE_EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS | ZIP_EXTENSIONS

COPY_RISK_WORDS = [
    "춘식이", "라이언", "어피치", "카카오프렌즈", "라인프렌즈", "브라운", "코니",
    "산리오", "헬로키티", "포켓몬", "피카츄", "디즈니", "미키", "짱구", "스누피",
    "똑같이", "비슷하게", "따라그", "모방", "복제", "표절", "스타일로", "느낌으로",
]

EMOTION_WORDS = {
    "확인/답장": ["넵", "네", "확인", "알겠", "접수", "완료"],
    "직장/피곤": ["퇴근", "출근", "야근", "월요", "피곤", "번아웃", "회의"],
    "감사/사과": ["감사", "고마", "미안", "죄송", "부탁"],
    "응원/축하": ["파이팅", "화이팅", "힘내", "축하", "대박"],
    "감정폭": ["헉", "멘붕", "눈물", "부들", "행복", "하트", "좋아"],
}

@dataclass
class V51ApiGuardrailConfig:
    project_name: str = "v51_api_guardrail_ledger"
    days: int = 30
    free_mode: bool = True
    youtube_enabled: bool = False
    google_search_enabled: bool = False
    openai_enabled: bool = False
    paid_calls_allowed: bool = False
    local_first: bool = True
    reserve_quota_plan: bool = False
    daily_youtube_search_limit: int = 20
    daily_youtube_video_limit: int = 200
    daily_youtube_comment_limit: int = 100
    daily_google_search_limit: int = 0
    daily_openai_analysis_limit: int = 0
    monthly_budget_limit_krw: int = 0
    max_local_files: int = 80
    max_zip_members: int = 120

@dataclass
class V51Report:
    project_name: str
    created_at: str
    mode: str
    days: int
    collection_window: dict[str, str]
    api_key_status: dict[str, Any]
    cost_guard: dict[str, Any]
    quota_ledger: list[dict[str, Any]]
    planned_jobs: list[dict[str, Any]]
    local_source_summary: list[dict[str, Any]]
    extracted_signals: dict[str, Any]
    safety_warnings: list[str]
    workflow_application: dict[str, Any]
    ledger_path: str
    html_path: str
    json_path: str
    csv_path: str
    board_png_path: str
    zip_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class V51ApiGuardrailLedgerEngine:
    """API-key, quota-ledger, and paid-call guardrail engine.

    v51 is intentionally a preflight/planning layer. It does not call external
    APIs by itself. It validates keys as session inputs, masks them, builds a
    30-day collection plan, checks daily counters, and blocks paid calls unless
    the user explicitly enables them.
    """

    def build_report(
        self,
        output_dir: str | Path,
        config: V51ApiGuardrailConfig | None = None,
        local_input_paths: Iterable[str | Path] | None = None,
        manual_notes: str = "",
        search_keywords: str = "직장인 공감 이모티콘, 짧은 답장, 퇴근, 피곤",
        youtube_api_key: str = "",
        google_api_key: str = "",
        openai_api_key: str = "",
    ) -> V51Report:
        config = config or V51ApiGuardrailConfig()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = output_dir / "v51_usage_ledger.json"

        days = max(1, min(int(config.days), 30))
        now = datetime.now(timezone.utc)
        collection_window = {
            "start_utc": (now - timedelta(days=days)).date().isoformat(),
            "end_utc": now.date().isoformat(),
            "rule": "최근 30일을 넘지 않도록 내부 제한",
        }

        key_status = self._key_status({
            "youtube": youtube_api_key,
            "google_search": google_api_key,
            "openai": openai_api_key,
        })
        local_rows, extracted_text = self._analyze_local_sources(local_input_paths or [], output_dir, config)
        combined_text = "\n".join([manual_notes or "", search_keywords or "", extracted_text])
        signals = self._extract_signals(combined_text, local_rows)
        cost_guard = self._cost_guard(config)
        planned_jobs = self._planned_jobs(config, search_keywords, days, signals)
        quota_ledger = self._quota_ledger_rows(config, planned_jobs, ledger_path)
        warnings = self._safety_warnings(config, key_status, signals, quota_ledger)
        workflow = self._workflow_application(signals, warnings)

        if config.reserve_quota_plan:
            self._reserve_plan(ledger_path, planned_jobs)
            quota_ledger = self._quota_ledger_rows(config, planned_jobs, ledger_path)

        core = {
            "project_name": config.project_name,
            "created_at": now.isoformat(),
            "mode": "FREE_ZERO_COST_PREFLIGHT" if config.free_mode else "USER_CONFIGURED_PREFLIGHT",
            "days": days,
            "collection_window": collection_window,
            "api_key_status": key_status,
            "cost_guard": cost_guard,
            "quota_ledger": quota_ledger,
            "planned_jobs": planned_jobs,
            "local_source_summary": local_rows,
            "extracted_signals": signals,
            "safety_warnings": warnings,
            "workflow_application": workflow,
        }

        json_path = output_dir / "v51_api_guardrail_ledger_report.json"
        csv_path = output_dir / "v51_planned_jobs.csv"
        html_path = output_dir / "v51_api_guardrail_ledger_report.html"
        board_png = output_dir / "v51_api_guardrail_board.png"
        package_zip = output_dir / "v51_api_guardrail_package.zip"

        json_path.write_text(json.dumps(core, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_jobs_csv(csv_path, planned_jobs)
        self._write_html(html_path, core)
        self._write_board_png(board_png, core)
        self._write_zip(package_zip, [json_path, csv_path, html_path, board_png, ledger_path])

        return V51Report(
            **core,
            ledger_path=str(ledger_path),
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            board_png_path=str(board_png),
            zip_path=str(package_zip),
        )

    def _key_status(self, keys: dict[str, str]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for service, raw in keys.items():
            cleaned = (raw or "").strip()
            result[service] = {
                "present": bool(cleaned),
                "masked_preview": self._mask_key(cleaned),
                "fingerprint_sha256_12": hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12] if cleaned else "",
                "raw_key_saved": False,
                "storage_rule": "원문 키는 리포트/CSV/ZIP에 저장하지 않음. 기본은 세션 입력값만 사용.",
            }
        return result

    def _mask_key(self, key: str) -> str:
        if not key:
            return ""
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"

    def _cost_guard(self, config: V51ApiGuardrailConfig) -> dict[str, Any]:
        blocked_services = []
        if config.free_mode and not config.paid_calls_allowed:
            if config.openai_enabled:
                blocked_services.append("openai_analysis")
            if config.google_search_enabled and config.daily_google_search_limit <= 0:
                blocked_services.append("google_search")
        return {
            "free_mode": bool(config.free_mode),
            "paid_calls_allowed": bool(config.paid_calls_allowed),
            "monthly_budget_limit_krw": int(config.monthly_budget_limit_krw),
            "blocked_services": blocked_services,
            "rule": "무료 모드에서는 유료 가능성이 있는 호출을 실행하지 않고 계획/로컬 분석만 수행합니다.",
            "external_api_called_by_v51": False,
        }

    def _planned_jobs(self, config: V51ApiGuardrailConfig, keywords: str, days: int, signals: dict[str, Any]) -> list[dict[str, Any]]:
        keyword_list = [k.strip() for k in re.split(r"[,\n]", keywords or "") if k.strip()]
        if not keyword_list:
            keyword_list = ["직장인 공감 이모티콘"]
        keyword_list = keyword_list[:10]
        jobs: list[dict[str, Any]] = []
        jobs.append({
            "job_id": "local_first_analysis",
            "service": "local_files_zip",
            "enabled": True,
            "quota_units_planned": 0,
            "cost_krw_planned": 0,
            "status": "READY",
            "description": "사용자가 올린 파일/ZIP/메모를 먼저 분석합니다.",
        })
        if config.youtube_enabled:
            jobs.append({
                "job_id": "youtube_search_30d",
                "service": "youtube_search",
                "enabled": True,
                "quota_units_planned": min(len(keyword_list), int(config.daily_youtube_search_limit)),
                "cost_krw_planned": 0,
                "status": "READY" if config.daily_youtube_search_limit > 0 else "LIMIT_ZERO",
                "description": f"최근 {days}일 기준 키워드 {len(keyword_list)}개 검색 계획",
            })
            jobs.append({
                "job_id": "youtube_video_details",
                "service": "youtube_videos",
                "enabled": True,
                "quota_units_planned": min(max(10, len(keyword_list) * 10), int(config.daily_youtube_video_limit)),
                "cost_krw_planned": 0,
                "status": "READY" if config.daily_youtube_video_limit > 0 else "LIMIT_ZERO",
                "description": "제목/설명/조회수/게시일 등 공개 영상 메타데이터 확인 계획",
            })
            jobs.append({
                "job_id": "youtube_comment_sample",
                "service": "youtube_comments",
                "enabled": True,
                "quota_units_planned": min(max(5, len(keyword_list) * 5), int(config.daily_youtube_comment_limit)),
                "cost_krw_planned": 0,
                "status": "READY" if config.daily_youtube_comment_limit > 0 else "LIMIT_ZERO",
                "description": "댓글 전체 복제가 아니라 키워드/반응 신호 추출용 샘플 계획",
            })
        else:
            jobs.append({"job_id": "youtube_off", "service": "youtube_search", "enabled": False, "quota_units_planned": 0, "cost_krw_planned": 0, "status": "OFF", "description": "YouTube API OFF"})

        if config.google_search_enabled:
            status = "READY" if config.daily_google_search_limit > 0 and (config.paid_calls_allowed or not config.free_mode) else "BLOCKED_FREE_MODE"
            jobs.append({
                "job_id": "google_search_guarded",
                "service": "google_search",
                "enabled": True,
                "quota_units_planned": min(len(keyword_list), max(0, int(config.daily_google_search_limit))),
                "cost_krw_planned": 0 if status == "READY" else 0,
                "status": status,
                "description": "Google 검색 API는 기본 OFF. 무료 한도/프로젝트 정책 확인 전에는 차단.",
            })
        else:
            jobs.append({"job_id": "google_search_off", "service": "google_search", "enabled": False, "quota_units_planned": 0, "cost_krw_planned": 0, "status": "OFF", "description": "Google 검색 API OFF"})

        if config.openai_enabled:
            status = "READY" if config.paid_calls_allowed and config.daily_openai_analysis_limit > 0 else "BLOCKED_FREE_MODE"
            jobs.append({
                "job_id": "openai_advanced_analysis",
                "service": "openai_analysis",
                "enabled": True,
                "quota_units_planned": min(3, max(0, int(config.daily_openai_analysis_limit))),
                "cost_krw_planned": 0,
                "status": status,
                "description": "로컬/YouTube 요약을 바탕으로 선택형 고급 분석. 기본 무료모드에서는 차단.",
            })
        else:
            jobs.append({"job_id": "openai_off", "service": "openai_analysis", "enabled": False, "quota_units_planned": 0, "cost_krw_planned": 0, "status": "OFF", "description": "OpenAI 고급 분석 OFF"})

        for idx, emotion in enumerate(signals.get("top_emotions", [])[:5], start=1):
            jobs.append({
                "job_id": f"quality_signal_{idx}",
                "service": "local_quality_engine",
                "enabled": True,
                "quota_units_planned": 0,
                "cost_krw_planned": 0,
                "status": "READY",
                "description": f"{emotion} 감정/문구/모션 신호를 정지형·움직이는형 품질 진화에 반영",
            })
        return jobs

    def _quota_ledger_rows(self, config: V51ApiGuardrailConfig, jobs: list[dict[str, Any]], ledger_path: Path) -> list[dict[str, Any]]:
        today = datetime.now().strftime("%Y-%m-%d")
        ledger = self._read_ledger(ledger_path)
        today_used = ledger.get(today, {}) if isinstance(ledger, dict) else {}
        limits = {
            "youtube_search": int(config.daily_youtube_search_limit),
            "youtube_videos": int(config.daily_youtube_video_limit),
            "youtube_comments": int(config.daily_youtube_comment_limit),
            "google_search": int(config.daily_google_search_limit),
            "openai_analysis": int(config.daily_openai_analysis_limit),
        }
        planned: dict[str, int] = {}
        for job in jobs:
            service = job.get("service", "")
            planned[service] = planned.get(service, 0) + int(job.get("quota_units_planned", 0) or 0)
        rows: list[dict[str, Any]] = []
        for service, limit in limits.items():
            used = int(today_used.get(service, 0) or 0)
            plan = int(planned.get(service, 0) or 0)
            remaining_before = max(0, limit - used)
            remaining_after = max(0, limit - used - plan)
            if limit <= 0:
                status = "OFF_OR_ZERO_LIMIT"
            elif plan > remaining_before:
                status = "PLAN_EXCEEDS_LIMIT"
            else:
                status = "OK"
            rows.append({
                "date": today,
                "service": service,
                "daily_limit": limit,
                "used_today": used,
                "planned_now": plan,
                "remaining_before_plan": remaining_before,
                "remaining_after_plan": remaining_after,
                "status": status,
            })
        if not ledger_path.exists():
            ledger_path.write_text(json.dumps({today: {}}, ensure_ascii=False, indent=2), encoding="utf-8")
        return rows

    def _read_ledger(self, ledger_path: Path) -> dict[str, Any]:
        if not ledger_path.exists():
            return {}
        try:
            data = json.loads(ledger_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _reserve_plan(self, ledger_path: Path, jobs: list[dict[str, Any]]) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        ledger = self._read_ledger(ledger_path)
        ledger.setdefault(today, {})
        for job in jobs:
            service = str(job.get("service", ""))
            units = int(job.get("quota_units_planned", 0) or 0)
            if service in {"youtube_search", "youtube_videos", "youtube_comments", "google_search", "openai_analysis"} and units > 0:
                ledger[today][service] = int(ledger[today].get(service, 0) or 0) + units
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    def _analyze_local_sources(self, paths: Iterable[str | Path], output_dir: Path, config: V51ApiGuardrailConfig) -> tuple[list[dict[str, Any]], str]:
        rows: list[dict[str, Any]] = []
        texts: list[str] = []
        extract_dir = output_dir / "v51_local_extracts"
        extract_dir.mkdir(parents=True, exist_ok=True)
        for raw_path in list(paths)[:max(1, int(config.max_local_files))]:
            path = Path(raw_path)
            if not path.exists() or not path.is_file():
                continue
            suffix = path.suffix.lower()
            sha = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            warning = ""
            source_type = suffix.lstrip(".") or "unknown"
            extracted_chars = 0
            image_hint = ""
            if suffix in TEXT_EXTENSIONS:
                text = self._read_text(path)
                texts.append(text[:15000])
                extracted_chars = len(text)
            elif suffix in IMAGE_EXTENSIONS:
                image_hint = self._image_hint(path)
            elif suffix in ZIP_EXTENSIONS:
                z_rows, z_text = self._analyze_zip(path, extract_dir, config)
                rows.extend(z_rows)
                texts.append(z_text)
                warning = f"ZIP 내부 {len(z_rows)}개 파일 분석"
            else:
                warning = "지원하지 않는 확장자라 내용 분석 제외"
            rows.append({
                "file_name": path.name,
                "source_type": source_type,
                "size_bytes": path.stat().st_size,
                "sha256_prefix": sha,
                "extracted_text_chars": extracted_chars,
                "extracted_image_hint": image_hint,
                "warning": warning,
            })
        return rows, "\n".join(texts)

    def _analyze_zip(self, zip_path: Path, extract_dir: Path, config: V51ApiGuardrailConfig) -> tuple[list[dict[str, Any]], str]:
        rows: list[dict[str, Any]] = []
        texts: list[str] = []
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                members = [m for m in zf.infolist() if not m.is_dir()][:max(1, int(config.max_zip_members))]
                for member in members:
                    name = Path(member.filename).name
                    suffix = Path(name).suffix.lower()
                    if suffix not in SAFE_EXTENSIONS - ZIP_EXTENSIONS:
                        rows.append({"file_name": f"{zip_path.name}/{name}", "source_type": suffix.lstrip(".") or "unknown", "size_bytes": member.file_size, "sha256_prefix": "", "extracted_text_chars": 0, "extracted_image_hint": "", "warning": "ZIP 내부 지원 제외 확장자"})
                        continue
                    data = zf.read(member)
                    sha = hashlib.sha256(data).hexdigest()[:16]
                    extracted_chars = 0
                    image_hint = ""
                    if suffix in TEXT_EXTENSIONS:
                        text = data.decode("utf-8", errors="ignore")
                        texts.append(text[:8000])
                        extracted_chars = len(text)
                    elif suffix in IMAGE_EXTENSIONS:
                        image_hint = "ZIP 이미지 파일 감지 - 실제 픽셀 분석은 추출 후 개별 검토 권장"
                    rows.append({"file_name": f"{zip_path.name}/{name}", "source_type": suffix.lstrip("."), "size_bytes": member.file_size, "sha256_prefix": sha, "extracted_text_chars": extracted_chars, "extracted_image_hint": image_hint, "warning": "ZIP 안전 분석"})
        except Exception as exc:
            rows.append({"file_name": zip_path.name, "source_type": "zip", "size_bytes": zip_path.stat().st_size if zip_path.exists() else 0, "sha256_prefix": "", "extracted_text_chars": 0, "extracted_image_hint": "", "warning": f"ZIP 분석 실패: {exc}"})
        return rows, "\n".join(texts)

    def _read_text(self, path: Path) -> str:
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                return path.read_text(encoding=enc, errors="ignore")
            except Exception:
                continue
        return ""

    def _image_hint(self, path: Path) -> str:
        if Image is None:
            return "Pillow 미설치 - 이미지 크기 분석 생략"
        try:
            with Image.open(path) as img:
                return f"{img.width}x{img.height}, mode={img.mode}"
        except Exception as exc:
            return f"이미지 분석 실패: {exc}"

    def _extract_signals(self, text: str, local_rows: list[dict[str, Any]]) -> dict[str, Any]:
        lowered = text.lower()
        emotion_scores = []
        for label, words in EMOTION_WORDS.items():
            score = sum(lowered.count(w.lower()) for w in words)
            if score > 0:
                emotion_scores.append((label, score))
        emotion_scores.sort(key=lambda x: x[1], reverse=True)
        copy_risks = [w for w in COPY_RISK_WORDS if w.lower() in lowered]
        phrase_candidates = re.findall(r"[가-힣A-Za-z0-9!?~ㅋㅎㅠㅜ]{2,14}", text or "")
        phrase_counts: dict[str, int] = {}
        for p in phrase_candidates:
            if len(p) <= 1:
                continue
            phrase_counts[p] = phrase_counts.get(p, 0) + 1
        top_phrases = [p for p, _ in sorted(phrase_counts.items(), key=lambda x: (-x[1], len(x[0])))[:24]]
        if not top_phrases:
            top_phrases = ["넵", "확인했습니다", "감사합니다", "잠시만요", "퇴근하고싶다", "오늘도버팀"]
        return {
            "top_emotions": [x[0] for x in emotion_scores[:5]] or ["확인/답장", "직장/피곤", "감사/사과"],
            "emotion_scores": [{"emotion": k, "score": v} for k, v in emotion_scores[:10]],
            "top_phrases": top_phrases[:24],
            "copy_risk_terms": copy_risks,
            "local_file_count": len(local_rows),
            "text_source_count": sum(1 for r in local_rows if int(r.get("extracted_text_chars", 0) or 0) > 0),
            "image_source_count": sum(1 for r in local_rows if r.get("extracted_image_hint")),
        }

    def _safety_warnings(self, config: V51ApiGuardrailConfig, key_status: dict[str, Any], signals: dict[str, Any], quota_rows: list[dict[str, Any]]) -> list[str]:
        warnings: list[str] = []
        if signals.get("copy_risk_terms"):
            warnings.append("유사성/모방 위험 단어가 감지되었습니다. 기존 캐릭터 복제 방향은 기능화하지 말고 추상 신호만 사용하세요.")
        for row in quota_rows:
            if row.get("status") == "PLAN_EXCEEDS_LIMIT":
                warnings.append(f"{row.get('service')} 계획량이 일일 제한을 초과합니다. 수집량을 줄여야 합니다.")
        if config.openai_enabled and not config.paid_calls_allowed:
            warnings.append("OpenAI 고급 분석이 켜졌지만 무료모드/유료차단 상태라 실제 호출은 차단됩니다.")
        if config.google_search_enabled and config.daily_google_search_limit <= 0:
            warnings.append("Google 검색 API가 켜졌지만 일일 한도가 0이라 차단됩니다.")
        for service, status in key_status.items():
            if status.get("present") and status.get("raw_key_saved"):
                warnings.append(f"{service} 키 원문 저장 위험이 있습니다.")
        return warnings or ["현재 설정에서는 치명적 안전 경고가 없습니다."]

    def _workflow_application(self, signals: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
        phrases = signals.get("top_phrases", [])[:32]
        rows = []
        for idx, phrase in enumerate(phrases, start=1):
            rows.append({
                "no": idx,
                "category": "v51_수집신호",
                "phrase": phrase,
                "usage_score": max(50, 95 - idx),
                "emotion": signals.get("top_emotions", ["확인/답장"])[0],
                "format_hint": "static_text",
                "motion_hint": "정지형 기준 프레임 유지 + 눈깜빡임/통통점프/말풍선 팝업 중 1개 적용",
            })
        if not rows:
            rows = [{"no": 1, "category": "v51_기본", "phrase": "넵", "usage_score": 90, "emotion": "확인/답장", "format_hint": "static_text", "motion_hint": "눈깜빡임"}]
        return {
            "active_generation_profile": {
                "source": "v51_api_guardrail_ledger",
                "local_first": True,
                "paid_call_guard": "enabled",
                "top_emotions": signals.get("top_emotions", []),
                "copy_risk_terms": signals.get("copy_risk_terms", []),
            },
            "recommended_prompt": "정지형 캐릭터의 외곽선/색상/얼굴 비율을 고정하고, 문구 가독성과 표정 차이를 크게 만든 뒤 움직이는형은 동일 기준 프레임에 작은 모션만 추가합니다.",
            "expression_seed_phrases": rows,
            "motion_seed_plan": [
                {"motion": "눈깜빡임", "use_when": "확인/감사/기본 답장"},
                {"motion": "통통 점프", "use_when": "응원/축하/좋아요"},
                {"motion": "말풍선 팝업", "use_when": "문구형 정지·움직이는형 공통"},
                {"motion": "흔들림", "use_when": "분노/당황/멘붕"},
            ],
            "warnings_to_show_before_generation": warnings,
        }

    def _write_jobs_csv(self, path: Path, jobs: list[dict[str, Any]]) -> None:
        fields = ["job_id", "service", "enabled", "quota_units_planned", "cost_krw_planned", "status", "description"]
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for job in jobs:
                writer.writerow({k: job.get(k, "") for k in fields})

    def _write_html(self, path: Path, data: dict[str, Any]) -> None:
        rows = "".join(
            f"<tr><td>{j.get('job_id')}</td><td>{j.get('service')}</td><td>{j.get('status')}</td><td>{j.get('quota_units_planned')}</td><td>{j.get('description')}</td></tr>"
            for j in data.get("planned_jobs", [])
        )
        warnings = "".join(f"<li>{w}</li>" for w in data.get("safety_warnings", []))
        html = f"""<!doctype html><html lang='ko'><meta charset='utf-8'>
<title>v51 API Guardrail Ledger</title>
<style>body{{font-family:Arial,sans-serif;margin:28px;background:#f7f8fb;color:#111827}}.card{{background:#fff;border:1px solid #e5e7eb;border-radius:18px;padding:18px;margin:14px 0;box-shadow:0 8px 20px rgba(15,23,42,.06)}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left}}</style>
<h1>v51 API 키/쿼터/유료차단 사전검증 리포트</h1>
<div class='card'><b>모드:</b> {data.get('mode')}<br><b>수집기간:</b> {data.get('collection_window', {}).get('start_utc')} ~ {data.get('collection_window', {}).get('end_utc')}</div>
<div class='card'><h2>안전 경고</h2><ul>{warnings}</ul></div>
<div class='card'><h2>수집 계획</h2><table><tr><th>작업</th><th>서비스</th><th>상태</th><th>계획량</th><th>설명</th></tr>{rows}</table></div>
</html>"""
        path.write_text(html, encoding="utf-8")

    def _write_board_png(self, path: Path, data: dict[str, Any]) -> None:
        if Image is None or ImageDraw is None:
            path.write_bytes(b"")
            return
        img = Image.new("RGB", (1200, 720), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 1200, 160], fill=(31, 41, 55))
        draw.text((40, 42), "v51 API Guardrail Ledger", fill=(255, 255, 255))
        draw.text((40, 86), "API key input / 30-day limit / quota counter / paid-call block / local-first", fill=(229, 231, 235))
        y = 210
        for row in data.get("quota_ledger", [])[:5]:
            draw.rounded_rectangle([40, y, 1160, y+68], radius=16, outline=(229,231,235), width=2)
            draw.text((65, y+20), f"{row.get('service')} | limit {row.get('daily_limit')} | used {row.get('used_today')} | planned {row.get('planned_now')} | {row.get('status')}", fill=(17,24,39))
            y += 86
        img.save(path)

    def _write_zip(self, path: Path, files: list[Path]) -> None:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                if f.exists():
                    zf.write(f, f.name)
