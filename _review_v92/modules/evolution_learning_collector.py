from __future__ import annotations

import csv
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from modules.copyright_guard.keyword_guard import KeywordGuard
from modules.trend_intelligence.youtube_collector import YoutubeCollector


@dataclass
class LearningSourceItem:
    source_type: str
    title: str
    url: str
    source_name: str
    published_at: str
    keywords: list[dict[str, Any]]
    safe_signals: list[str]
    risk_flags: list[dict[str, str]]
    learning_use: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvolutionLearningCollector:
    """Collects safe, abstract learning signals for emoticon production.

    It does not download videos, images, thumbnails, or creator artwork. The saved
    database keeps links, titles, metadata, risk flags, and abstract production
    signals only.
    """

    DEFAULT_QUERIES = [
        "카카오 이모티콘 만들기",
        "카카오톡 이모티콘 제작 방법",
        "이모티콘 스튜디오 제안 가이드",
        "이모티콘 반려 사유 개선",
        "움직이는 이모티콘 제작",
    ]

    OFFICIAL_REFERENCE_URLS = [
        "https://emoticonstudio.kakao.com/guideline",
        "https://emoticonstudio.kakao.com/pages/faq?from=with_faq",
        "https://emoticonstudio.kakao.com/terms",
    ]

    SAFE_SIGNAL_RULES = {
        "직접 창작 증거": ["직접", "스케치", "창작", "원본", "레이어", "과정", "수정"],
        "제출 규격 확인": ["가이드", "규격", "사이즈", "용량", "프레임", "업로드", "제안"],
        "문구/상황 기획": ["문구", "표현", "상황", "감정", "대화", "공감"],
        "가독성/미리보기": ["가독성", "미리보기", "채팅", "작게", "썸네일", "대비"],
        "반려 대응": ["반려", "심사", "거절", "재제안", "개선"],
        "데이터 기반 개선": ["조회수", "댓글", "트렌드", "분석", "성과", "통계"],
        "저작권/상표 방어": ["저작권", "상표", "권리", "침해", "라이선스", "유사"],
    }

    BLOCKED_LEARNING_PATTERNS = [
        "따라 그리",
        "똑같이",
        "비슷하게",
        "스타일로",
        "다운로드해서",
        "캡처해서 사용",
        "무단",
        "검수 우회",
        "AI 아닌 척",
        "들키지",
    ]

    def __init__(self) -> None:
        self.guard = KeywordGuard()

    def collect(
        self,
        out_dir: str | Path,
        queries: list[str] | None = None,
        youtube_api_key: str = "",
        max_results_per_query: int = 5,
        days: int = 30,
        reference_urls: list[str] | None = None,
        youtube_channel_ids: list[str] | None = None,
        schedule_days: int = 7,
    ) -> dict[str, Any]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        queries = [q.strip() for q in (queries or self.DEFAULT_QUERIES) if q.strip()]
        reference_urls = [u.strip() for u in (reference_urls or self.OFFICIAL_REFERENCE_URLS) if u.strip()]
        youtube_channel_ids = [c.strip() for c in (youtube_channel_ids or []) if c.strip()]

        items: list[LearningSourceItem] = []
        warnings: list[str] = []

        if youtube_api_key:
            try:
                items.extend(self._collect_youtube_api(youtube_api_key, queries, max_results_per_query, days))
            except Exception as exc:
                warnings.append(f"YouTube API 수집 실패: {exc}")
        else:
            warnings.append("YouTube API 키가 없어 검색 수집은 건너뜁니다. 채널 RSS 또는 참고 URL 수집은 계속 가능합니다.")

        for channel_id in youtube_channel_ids:
            try:
                items.extend(self._collect_youtube_channel_rss(channel_id))
            except Exception as exc:
                warnings.append(f"YouTube RSS 수집 실패({channel_id}): {exc}")

        for url in reference_urls:
            try:
                items.append(self._collect_reference_url(url))
            except Exception as exc:
                warnings.append(f"참고 URL 수집 실패({url}): {exc}")

        deduped = self._dedupe(items)
        report = self._build_report(deduped, warnings, queries, schedule_days)
        files = self._write_outputs(out, report)
        report["files"] = files
        return report

    def due_status(self, schedule_path: str | Path) -> dict[str, Any]:
        path = Path(schedule_path)
        if not path.exists():
            return {"exists": False, "due": True, "message": "수집 주기 파일이 아직 없습니다."}
        data = json.loads(path.read_text(encoding="utf-8"))
        last = data.get("last_collected_at")
        interval = max(1, int(data.get("schedule_days", 7)))
        if not last:
            return {"exists": True, "due": True, "message": "아직 마지막 수집 시간이 없습니다.", "config": data}
        last_dt = datetime.fromisoformat(last)
        next_dt = last_dt + timedelta(days=interval)
        due = datetime.now() >= next_dt
        return {
            "exists": True,
            "due": due,
            "last_collected_at": last,
            "next_collect_after": next_dt.isoformat(timespec="seconds"),
            "message": "수집 주기가 도래했습니다." if due else "아직 다음 수집 전입니다.",
            "config": data,
        }

    def _collect_youtube_api(self, api_key: str, queries: list[str], max_results: int, days: int) -> list[LearningSourceItem]:
        collector = YoutubeCollector(api_key=api_key)
        videos = collector.search_recent_multi(
            queries,
            max_results_per_keyword=max_results,
            days=days,
            include_comments=False,
        )
        items = []
        for video in videos:
            text = " ".join([video.title, video.description or "", " ".join(video.tags or [])])
            items.append(self._make_item(
                source_type="youtube_api",
                title=video.title,
                url=f"https://www.youtube.com/watch?v={video.video_id}",
                source_name=video.channel_title,
                published_at=video.published_at,
                text=text,
                extra_keywords=[
                    {"keyword": "views", "count": video.view_count or 0},
                    {"keyword": "likes", "count": video.like_count or 0},
                    {"keyword": "comments", "count": video.comment_count or 0},
                ],
            ))
        return items

    def _collect_youtube_channel_rss(self, channel_id: str) -> list[LearningSourceItem]:
        url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + urllib.parse.quote(channel_id)
        req = urllib.request.Request(url, headers={"User-Agent": "KakaoEmoticonLearningCollector/1.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            root = ET.fromstring(response.read())
        ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
        source_name = root.findtext("atom:title", default="", namespaces=ns)
        items = []
        for entry in root.findall("atom:entry", ns)[:20]:
            title = entry.findtext("atom:title", default="", namespaces=ns)
            video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
            published = entry.findtext("atom:published", default="", namespaces=ns)
            link = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
            items.append(self._make_item(
                source_type="youtube_rss",
                title=title,
                url=link,
                source_name=source_name,
                published_at=published,
                text=title,
            ))
        return items

    def _collect_reference_url(self, url: str) -> LearningSourceItem:
        req = urllib.request.Request(url, headers={"User-Agent": "KakaoEmoticonLearningCollector/1.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read(512_000).decode("utf-8", errors="ignore")
        title = self._extract_title(raw) or url
        text = self._visible_text(raw)
        return self._make_item(
            source_type="reference_url",
            title=title,
            url=url,
            source_name=urllib.parse.urlparse(url).netloc,
            published_at="",
            text=text,
        )

    def _make_item(self, source_type: str, title: str, url: str, source_name: str, published_at: str, text: str, extra_keywords: list[dict[str, Any]] | None = None) -> LearningSourceItem:
        risk_flags = [finding.to_dict() for finding in self.guard.scan(text)]
        lower = text.lower()
        for pattern in self.BLOCKED_LEARNING_PATTERNS:
            if pattern.lower() in lower:
                risk_flags.append({
                    "level": "위험",
                    "keyword": pattern,
                    "message": "복제·모방·우회로 해석될 수 있는 표현입니다.",
                    "suggestion": "구체 콘텐츠를 따라 하지 말고 추상 제작 원칙만 참고하세요.",
                })
        safe_signals = []
        for label, keywords in self.SAFE_SIGNAL_RULES.items():
            if any(keyword.lower() in lower for keyword in keywords):
                safe_signals.append(label)
        if not safe_signals:
            safe_signals.append("수동 검토")

        keywords = self._keywords(text)[:24]
        if extra_keywords:
            keywords.extend(extra_keywords)
        return LearningSourceItem(
            source_type=source_type,
            title=title.strip()[:240],
            url=url,
            source_name=source_name.strip()[:120],
            published_at=published_at,
            keywords=keywords[:30],
            safe_signals=safe_signals,
            risk_flags=risk_flags,
            learning_use=self._learning_use(risk_flags),
        )

    def _learning_use(self, risk_flags: list[dict[str, str]]) -> str:
        if any(flag.get("level") == "위험" for flag in risk_flags):
            return "차단/경고 데이터로만 사용"
        if risk_flags:
            return "추상 신호만 제한적으로 사용"
        return "안전한 추상 제작 신호로 사용"

    def _build_report(self, items: list[LearningSourceItem], warnings: list[str], queries: list[str], schedule_days: int) -> dict[str, Any]:
        all_signals: dict[str, int] = {}
        blocked_count = 0
        for item in items:
            for signal in item.safe_signals:
                all_signals[signal] = all_signals.get(signal, 0) + 1
            if item.learning_use == "차단/경고 데이터로만 사용":
                blocked_count += 1
        recommendations = [
            "수집 자료는 링크/제목/메타데이터와 추상 신호만 저장하고, 영상·이미지·캐릭터·자막 원문 대량 저장은 피하세요.",
            "위험 플래그가 있는 항목은 창작 참고가 아니라 차단/경고 데이터로만 사용하세요.",
            "반복적으로 등장하는 안전 신호는 문구 은행, QC, 반려 대응, 최종 리포트 개선에만 반영하세요.",
        ]
        return {
            "collected_at": datetime.now().isoformat(timespec="seconds"),
            "queries": queries,
            "schedule_days": schedule_days,
            "source_count": len(items),
            "blocked_or_warning_only_count": blocked_count,
            "safe_signal_counts": dict(sorted(all_signals.items(), key=lambda x: (-x[1], x[0]))),
            "items": [item.to_dict() for item in items],
            "warnings": warnings,
            "recommendations": recommendations,
        }

    def _write_outputs(self, out: Path, report: dict[str, Any]) -> dict[str, str]:
        json_path = out / "evolution_learning_db.json"
        csv_path = out / "evolution_learning_sources.csv"
        html_path = out / "evolution_learning_report.html"
        schedule_path = out / "collection_schedule.json"

        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["source_type", "title", "url", "source_name", "published_at", "safe_signals", "risk_count", "learning_use"])
            writer.writeheader()
            for item in report["items"]:
                writer.writerow({
                    "source_type": item.get("source_type"),
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "source_name": item.get("source_name"),
                    "published_at": item.get("published_at"),
                    "safe_signals": ", ".join(item.get("safe_signals", [])),
                    "risk_count": len(item.get("risk_flags", [])),
                    "learning_use": item.get("learning_use"),
                })
        self._write_html(html_path, report)
        schedule = {
            "schedule_days": report.get("schedule_days", 7),
            "last_collected_at": report.get("collected_at"),
            "queries": report.get("queries", []),
            "official_reference_urls": self.OFFICIAL_REFERENCE_URLS,
            "policy": "Do not store or reproduce video files, images, creator artwork, or large transcript text. Store metadata and abstract signals only.",
        }
        schedule_path.write_text(json.dumps(schedule, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "json_path": str(json_path),
            "csv_path": str(csv_path),
            "html_path": str(html_path),
            "schedule_path": str(schedule_path),
        }

    def _write_html(self, path: Path, report: dict[str, Any]) -> None:
        item_rows = []
        for item in report.get("items", [])[:120]:
            risks = item.get("risk_flags", [])
            risk_text = "<br>".join(html.escape(str(r.get("keyword", ""))) for r in risks) or "없음"
            item_rows.append(
                "<tr>"
                f"<td>{html.escape(str(item.get('source_type', '')))}</td>"
                f"<td><a href=\"{html.escape(str(item.get('url', '')))}\">{html.escape(str(item.get('title', '')))}</a></td>"
                f"<td>{html.escape(', '.join(item.get('safe_signals', [])))}</td>"
                f"<td>{risk_text}</td>"
                f"<td>{html.escape(str(item.get('learning_use', '')))}</td>"
                "</tr>"
            )
        signal_rows = "".join(
            f"<li>{html.escape(str(k))}: {html.escape(str(v))}</li>"
            for k, v in report.get("safe_signal_counts", {}).items()
        )
        doc = f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><title>학습형 수집/진화 리포트</title>
<style>
body{{font-family:"Malgun Gothic",Arial,sans-serif;margin:32px;background:#f7f4ed;color:#25221d}}
main{{max-width:1120px;margin:auto;background:#fffdf8;border:1px solid #ded5c7;padding:28px}}
table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #ded5c7;padding:9px;text-align:left;vertical-align:top}}th{{background:#e6f3ee}}
.note{{background:#fbf6eb;border:1px solid #ded5c7;padding:14px;margin:16px 0}}
</style></head>
<body><main>
<h1>학습형 수집/진화 리포트</h1>
<p>생성 시각: {html.escape(str(report.get("collected_at", "")))} · 수집 항목: {html.escape(str(report.get("source_count", 0)))}</p>
<div class="note">영상/이미지/캐릭터를 저장하거나 복제하지 않고, 링크·제목·메타데이터·추상 제작 신호만 저장합니다.</div>
<h2>누적 안전 신호</h2><ul>{signal_rows}</ul>
<h2>자료 목록</h2>
<table><thead><tr><th>유형</th><th>자료</th><th>안전 신호</th><th>위험 키워드</th><th>사용 방식</th></tr></thead><tbody>{''.join(item_rows)}</tbody></table>
<h2>권장 반영 방향</h2><ul>{''.join(f"<li>{html.escape(str(x))}</li>" for x in report.get("recommendations", []))}</ul>
</main></body></html>"""
        path.write_text(doc, encoding="utf-8")

    def _dedupe(self, items: list[LearningSourceItem]) -> list[LearningSourceItem]:
        seen = set()
        result = []
        for item in items:
            key = item.url or item.title
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _keywords(self, text: str) -> list[dict[str, Any]]:
        tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", (text or "").lower())
        stop = {"https", "youtube", "www", "com", "the", "and", "with", "for", "this", "that"}
        counts: dict[str, int] = {}
        for token in tokens:
            if token in stop:
                continue
            counts[token] = counts.get(token, 0) + 1
        return [{"keyword": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]

    def _extract_title(self, raw_html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.I | re.S)
        if not match:
            return ""
        return html.unescape(re.sub(r"\s+", " ", match.group(1)).strip())

    def _visible_text(self, raw_html: str) -> str:
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()[:20_000]
