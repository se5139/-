from __future__ import annotations

import csv
import html
import json
import re
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZipFile, ZIP_DEFLATED

from modules.trend_intelligence.youtube_collector import YoutubeCollector


YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


@dataclass
class YoutubeReferenceReport:
    video_id: str
    source_url: str
    title: str
    channel_title: str
    published_at: str
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    transcript_summary: dict[str, Any]
    core_claims: list[dict[str, str]]
    risky_claims: list[dict[str, str]]
    safe_feature_ideas: list[dict[str, str]]
    extracted_keywords: list[dict[str, Any]]
    comments_summary: dict[str, Any]
    recommendations: list[str]
    warnings: list[str]
    files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class YoutubeReferenceAnalyzer:
    """유튜브 참고영상/자막 분석기.

    원칙:
    - 영상 파일을 다운로드하거나 재사용하지 않습니다.
    - URL/iframe에서 videoId를 추출합니다.
    - YouTube API 키가 있으면 제목/설명/통계/상위 댓글을 조회합니다.
    - 자막은 사용자가 붙여넣거나 TXT/SRT/VTT 파일로 제공한 텍스트를 분석합니다.
    - AI 은폐/검수 우회 주장은 기능화하지 않고 위험 신호로 분리합니다.
    """

    RISK_PATTERNS = [
        ("AI 은폐", ["ai 티 안", "ai가 만든 걸 모르게", "ai 아닌 척", "ai 티가 안", "숨기", "은폐", "모르게 제출", "검수 우회", "탐지 우회", "들키지", "속이"]),
        ("기존 캐릭터 모방", ["춘식이", "라이언", "카카오프렌즈", "산리오", "헬로키티", "포켓몬", "디즈니", "짱구", "스누피", "비슷하게", "똑같이", "따라 그", "스타일로"]),
        ("수익 보장 과장", ["무조건 승인", "무조건 수익", "100% 승인", "돈이 굴러", "자동으로 돈", "월 천", "보장"]),
        ("무단 수집/재사용", ["긁어오", "다운로드해서 쓰", "남의 이미지", "인기 이모티콘 저장", "그대로 사용", "복붙"]),
    ]

    SAFE_IDEAS = [
        ("직접 창작 증거 강화", ["스케치", "손그림", "직접", "원본", "레이어", "과정", "수정 이력"]),
        ("문구/표현 은행", ["문구", "표현", "감정", "상황", "답장", "사용성"]),
        ("시장/트렌드 분석", ["유튜브", "댓글", "검색", "트렌드", "조회수", "좋아요", "키워드"]),
        ("품질/가독성 검사", ["가독성", "작게", "채팅창", "미리보기", "검수", "품질", "배경"]),
        ("저작권/상표 방어", ["저작권", "상표", "라이선스", "유사", "출처"]),
    ]

    CLAIM_KEYWORDS = {
        "승인/반려": ["승인", "반려", "거부", "심사", "검수"],
        "AI 사용": ["ai", "생성형", "자동 생성", "챗gpt", "미드저니", "달리", "스테이블"],
        "수익화": ["수익", "판매", "돈", "정산", "자동수익", "파이프라인"],
        "제작 방법": ["그리", "스케치", "캐릭터", "이모티콘", "표정", "모션", "문구"],
        "데이터 분석": ["분석", "댓글", "조회수", "키워드", "트렌드", "유튜브"],
    }

    def extract_video_id(self, url_or_iframe: str) -> str:
        text = (url_or_iframe or "").strip()
        if not text:
            return ""
        # iframe src 추출
        match = re.search(r"src=[\'\"]([^\'\"]+)[\'\"]", text, flags=re.I)
        if match:
            text = match.group(1)
        if YOUTUBE_ID_RE.match(text):
            return text
        parsed = urllib.parse.urlparse(text)
        host = (parsed.netloc or "").lower()
        path = parsed.path or ""
        query = urllib.parse.parse_qs(parsed.query or "")
        if "youtu.be" in host:
            candidate = path.strip("/").split("/")[0]
            return candidate if YOUTUBE_ID_RE.match(candidate) else ""
        if "youtube.com" in host:
            if "v" in query and query["v"]:
                candidate = query["v"][0]
                return candidate if YOUTUBE_ID_RE.match(candidate) else ""
            parts = [p for p in path.split("/") if p]
            if "embed" in parts:
                idx = parts.index("embed")
                if len(parts) > idx + 1:
                    candidate = parts[idx + 1]
                    return candidate if YOUTUBE_ID_RE.match(candidate) else ""
            if "shorts" in parts:
                idx = parts.index("shorts")
                if len(parts) > idx + 1:
                    candidate = parts[idx + 1]
                    return candidate if YOUTUBE_ID_RE.match(candidate) else ""
        # fallback: 11자 ID 패턴 탐색
        for candidate in re.findall(r"[A-Za-z0-9_-]{11}", text):
            if YOUTUBE_ID_RE.match(candidate):
                return candidate
        return ""

    def strip_caption_format(self, text: str) -> str:
        text = text or ""
        lines = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.upper().startswith("WEBVTT"):
                continue
            if re.match(r"^\d+$", line):
                continue
            if "-->" in line:
                continue
            line = re.sub(r"<[^>]+>", "", line)
            line = re.sub(r"\{[^}]+\}", "", line)
            lines.append(line)
        return "\n".join(lines)

    def analyze(
        self,
        output_dir: str | Path,
        url_or_iframe: str,
        transcript_text: str = "",
        uploaded_transcripts: list[tuple[str, str]] | None = None,
        api_key: str = "",
        include_comments: bool = False,
        comments_per_video: int = 10,
        manual_title: str = "",
        manual_notes: str = "",
    ) -> YoutubeReferenceReport:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        video_id = self.extract_video_id(url_or_iframe)
        warnings: list[str] = []
        if not video_id:
            warnings.append("YouTube videoId를 추출하지 못했습니다. URL 또는 iframe을 다시 확인하세요.")

        combined_transcript = self.strip_caption_format(transcript_text)
        uploaded_transcripts = uploaded_transcripts or []
        for name, content in uploaded_transcripts:
            clean = self.strip_caption_format(content)
            if clean:
                combined_transcript += f"\n\n[{name}]\n{clean}"

        title = manual_title.strip()
        channel_title = ""
        published_at = ""
        view_count = like_count = comment_count = None
        comments: list[str] = []
        description = ""
        tags: list[str] = []
        if api_key and video_id:
            try:
                collector = YoutubeCollector(api_key=api_key)
                details = collector.fetch_details([video_id]).get(video_id, {})
                snippet = details.get("snippet", {})
                stats = details.get("statistics", {})
                title = snippet.get("title", title)
                channel_title = snippet.get("channelTitle", "")
                published_at = snippet.get("publishedAt", "")
                description = snippet.get("description", "") or ""
                tags = snippet.get("tags", [])[:30]
                view_count = _safe_int(stats.get("viewCount"))
                like_count = _safe_int(stats.get("likeCount"))
                comment_count = _safe_int(stats.get("commentCount"))
                if include_comments:
                    try:
                        comments = collector.fetch_top_comments(video_id, max_results=comments_per_video)
                    except Exception as exc:
                        warnings.append(f"댓글 조회 실패: {exc}")
            except Exception as exc:
                warnings.append(f"YouTube API 조회 실패: {exc}")
        elif not api_key:
            warnings.append("YouTube API 키가 없어 제목/통계/댓글 조회는 건너뛰고, URL·자막·수동 메모 중심으로 분석했습니다.")

        combined_text = "\n".join([title, description, " ".join(tags), combined_transcript, "\n".join(comments), manual_notes]).strip()
        if not combined_text:
            combined_text = url_or_iframe or ""

        transcript_summary = self._summarize_transcript(combined_transcript)
        core_claims = self._extract_core_claims(combined_text)
        risky_claims = self._extract_risky_claims(combined_text)
        safe_feature_ideas = self._extract_safe_feature_ideas(combined_text)
        extracted_keywords = self._extract_keywords(combined_text)
        comments_summary = self._summarize_comments(comments)
        recommendations = self._make_recommendations(core_claims, risky_claims, safe_feature_ideas, transcript_summary)
        if risky_claims:
            warnings.append("AI 은폐/검수 우회/기존 캐릭터 모방/무단 재사용 관련 위험 주장이 감지되었습니다. 해당 방향은 기능화하지 않고 차단·경고로 분리했습니다.")

        base = out / f"youtube_reference_{video_id or 'unknown'}"
        report_dict_pre = {
            "video_id": video_id,
            "source_url": url_or_iframe,
            "title": title,
            "channel_title": channel_title,
            "published_at": published_at,
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "transcript_summary": transcript_summary,
            "core_claims": core_claims,
            "risky_claims": risky_claims,
            "safe_feature_ideas": safe_feature_ideas,
            "extracted_keywords": extracted_keywords,
            "comments_summary": comments_summary,
            "recommendations": recommendations,
            "warnings": warnings,
        }
        json_path = base.with_suffix(".json")
        html_path = base.with_suffix(".html")
        csv_path = base.with_name(base.name + "_ideas.csv")
        transcript_path = base.with_name(base.name + "_transcript_clean.txt")
        zip_path = base.with_suffix(".zip")
        json_path.write_text(json.dumps(report_dict_pre, ensure_ascii=False, indent=2), encoding="utf-8")
        transcript_path.write_text(combined_transcript, encoding="utf-8")
        self._write_csv(csv_path, core_claims, risky_claims, safe_feature_ideas, extracted_keywords)
        self._write_html(html_path, report_dict_pre)
        with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
            for fp in [json_path, html_path, csv_path, transcript_path]:
                if fp.exists():
                    zf.write(fp, fp.name)
        files = {
            "html_path": str(html_path),
            "json_path": str(json_path),
            "csv_path": str(csv_path),
            "transcript_path": str(transcript_path),
            "zip_path": str(zip_path),
        }
        return YoutubeReferenceReport(
            video_id=video_id,
            source_url=url_or_iframe,
            title=title,
            channel_title=channel_title,
            published_at=published_at,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            transcript_summary=transcript_summary,
            core_claims=core_claims,
            risky_claims=risky_claims,
            safe_feature_ideas=safe_feature_ideas,
            extracted_keywords=extracted_keywords,
            comments_summary=comments_summary,
            recommendations=recommendations,
            warnings=warnings,
            files=files,
        )

    def _summarize_transcript(self, text: str) -> dict[str, Any]:
        clean = text.strip()
        words = re.findall(r"[가-힣A-Za-z0-9]+", clean.lower())
        sentences = [s.strip() for s in re.split(r"[.!?。！？\n]+", clean) if len(s.strip()) >= 8]
        return {
            "provided": bool(clean),
            "char_count": len(clean),
            "word_count": len(words),
            "sentence_count": len(sentences),
            "sample_sentences": sentences[:8],
        }

    def _extract_core_claims(self, text: str) -> list[dict[str, str]]:
        claims: list[dict[str, str]] = []
        sentences = [s.strip() for s in re.split(r"[.!?。！？\n]+", text) if len(s.strip()) >= 8]
        for category, kws in self.CLAIM_KEYWORDS.items():
            hits = []
            for sentence in sentences:
                low = sentence.lower()
                if any(k.lower() in low for k in kws):
                    hits.append(sentence[:180])
            if hits:
                claims.append({"category": category, "claim_summary": " / ".join(hits[:3]), "action": self._claim_action(category)})
        if not claims:
            claims.append({"category": "일반 참고", "claim_summary": "자막/메모에서 명확한 이모티콘 관련 핵심 주장을 많이 찾지 못했습니다.", "action": "제목·댓글·수동 메모를 보강해 다시 분석하세요."})
        return claims

    def _claim_action(self, category: str) -> str:
        return {
            "승인/반려": "반려 사유 개선 엔진(v29)과 제출 전 잠금 체크리스트(v30)에 반영",
            "AI 사용": "직접 창작 기준/AI 정책 대응(v13/v30)에서 위험 문구로 분리",
            "수익화": "성장형 학습 엔진(v20)과 수익 파이프라인(v8/v18)에 참고 데이터로 저장",
            "제작 방법": "텍스트 설명 생성(v27), 누락 정보 재구성(v28), 감정/모션 확장(v26)에 아이디어로 반영",
            "데이터 분석": "30일 트렌드 분석(v7/v20)과 유튜브 참고영상 분석(v32)에 누적",
        }.get(category, "수동 검토")

    def _extract_risky_claims(self, text: str) -> list[dict[str, str]]:
        results = []
        low = text.lower()
        for risk_type, kws in self.RISK_PATTERNS:
            matched = [k for k in kws if k.lower() in low]
            if matched:
                results.append({
                    "risk_type": risk_type,
                    "matched_keywords": ", ".join(matched[:12]),
                    "program_handling": "기능화 금지 · 경고/차단/직접 창작 증거 보강 방향으로만 반영",
                })
        return results

    def _extract_safe_feature_ideas(self, text: str) -> list[dict[str, str]]:
        ideas = []
        low = text.lower()
        for idea, kws in self.SAFE_IDEAS:
            matched = [k for k in kws if k.lower() in low]
            if matched:
                ideas.append({"feature": idea, "matched_keywords": ", ".join(matched[:10]), "implementation_hint": self._feature_hint(idea)})
        if not ideas:
            ideas.append({"feature": "수동 참고 메모", "matched_keywords": "-", "implementation_hint": "자막/댓글/영상 메모를 붙여넣으면 안전한 기능 후보를 더 구체적으로 추출합니다."})
        return ideas

    def _feature_hint(self, idea: str) -> str:
        hints = {
            "직접 창작 증거 강화": "자유 드로잉/스케치/레이어/수정 이력 SHA-256 기록에 연결",
            "문구/표현 은행": "표현 후보 80~120개 생성과 24/32개 세트 선별에 반영",
            "시장/트렌드 분석": "YouTube 제목/댓글/조회수/좋아요와 네이버 데이터랩 분석에 반영",
            "품질/가독성 검사": "채팅창 미리보기, 작은 화면/어두운 배경 검사에 반영",
            "저작권/상표 방어": "상표/유사 키워드/자료 출처/라이선스 리포트에 반영",
        }
        return hints.get(idea, "수동 검토")

    def _extract_keywords(self, text: str) -> list[dict[str, Any]]:
        tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", text.lower())
        stop = {"the", "and", "this", "that", "with", "you", "for", "are", "was", "https", "youtu", "youtube"}
        counts: dict[str, int] = {}
        for token in tokens:
            if token in stop:
                continue
            counts[token] = counts.get(token, 0) + 1
        ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:30]
        return [{"keyword": k, "count": v} for k, v in ranked]

    def _summarize_comments(self, comments: list[str]) -> dict[str, Any]:
        joined = "\n".join(comments)
        risks = self._extract_risky_claims(joined) if joined else []
        keywords = self._extract_keywords(joined)[:12] if joined else []
        return {
            "comment_count_analyzed": len(comments),
            "top_comment_samples": comments[:5],
            "comment_keywords": keywords,
            "comment_risk_flags": risks,
        }

    def _make_recommendations(self, claims, risks, ideas, summary) -> list[str]:
        recs = [
            "영상 내용은 기존 캐릭터/영상/문구를 따라 만드는 용도가 아니라, 제작 프로세스와 리스크 참고자료로만 사용하세요.",
            "자막에서 발견된 안전한 기능 아이디어는 직접 창작 기반 워크플로우, 품질검사, 데이터 분석, 반려 개선 엔진에만 반영하세요.",
        ]
        if risks:
            recs.append("AI 은폐·검수 우회·기존 캐릭터 모방 관련 표현은 프로그램에서 자동 차단/경고 대상으로 유지하세요.")
        if not summary.get("provided"):
            recs.append("정밀 분석을 위해 자막 텍스트, SRT/VTT/TXT 파일, 또는 핵심 장면 캡처 내용을 추가하세요.")
        if ideas:
            recs.append("추출된 기능 후보는 성장형 학습 엔진(v20)에 스냅샷으로 저장해 다음 제작 추천에 반영하세요.")
        return recs

    def _write_csv(self, path: Path, claims, risks, ideas, keywords) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["type", "name", "detail", "action"])
            writer.writeheader()
            for c in claims:
                writer.writerow({"type": "core_claim", "name": c.get("category"), "detail": c.get("claim_summary"), "action": c.get("action")})
            for r in risks:
                writer.writerow({"type": "risk", "name": r.get("risk_type"), "detail": r.get("matched_keywords"), "action": r.get("program_handling")})
            for i in ideas:
                writer.writerow({"type": "safe_feature", "name": i.get("feature"), "detail": i.get("matched_keywords"), "action": i.get("implementation_hint")})
            for k in keywords:
                writer.writerow({"type": "keyword", "name": k.get("keyword"), "detail": k.get("count"), "action": "키워드 후보"})

    def _write_html(self, path: Path, data: dict[str, Any]) -> None:
        title = "v32 유튜브 참고영상/자막 분석 리포트"
        sections = []
        for key, value in data.items():
            sections.append(f"<h2>{html.escape(str(key))}</h2><pre>{html.escape(json.dumps(value, ensure_ascii=False, indent=2))}</pre>")
        doc = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Malgun Gothic',Arial,sans-serif;margin:32px;line-height:1.55;color:#222}}h1{{font-size:28px}}h2{{margin-top:28px;border-bottom:2px solid #eee;padding-bottom:6px}}pre{{background:#f7f7f8;border-radius:10px;padding:14px;white-space:pre-wrap;overflow-x:auto}}.badge{{display:inline-block;background:#eef2ff;padding:4px 10px;border-radius:999px;margin-right:6px}}</style>
</head><body><h1>{title}</h1><p><span class="badge">생성일 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span><span class="badge">영상 다운로드 없음</span><span class="badge">자막/메타데이터 분석</span></p>{''.join(sections)}<p>이 리포트는 법적 판정서가 아니며, 영상 내용을 복제하거나 우회 기능으로 사용하지 않습니다.</p></body></html>"""
        path.write_text(doc, encoding="utf-8")


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None
