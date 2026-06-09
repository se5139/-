from __future__ import annotations

import html
import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .manual_trend_analyzer import ManualTrendAnalyzer
from .youtube_collector import YoutubeCollector, YoutubeVideoItem
from .naver_datalab_collector import NaverDatalabCollector, NaverKeywordGroupResult
from .kipris_trademark_checker import KiprisTrademarkChecker, TrademarkCheckResult


@dataclass
class ThirtyDayTrendReport:
    days: int
    keywords: list[str]
    manual_summary: dict | None
    youtube_items: list[dict]
    naver_groups: list[dict]
    trademark_results: list[dict]
    top_keywords: list[tuple[str, int]]
    recommended_phrases: list[str]
    recommended_formats: list[str]
    recommended_characters: list[str]
    caution_notes: list[str]
    quota_estimate: dict
    html_path: str = ""
    json_path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ThirtyDayTrendEngine:
    DEFAULT_KEYWORDS = ["직장인 공감", "퇴근", "월요병", "넵", "확인했습니다", "이모티콘", "카톡 이모티콘"]

    def run(
        self,
        keywords: list[str] | None = None,
        manual_text: str = "",
        days: int = 30,
        youtube_api_key: str = "",
        youtube_max_per_keyword: int = 3,
        include_youtube_comments: bool = False,
        comments_per_video: int = 2,
        naver_client_id: str = "",
        naver_client_secret: str = "",
        kipris_service_key: str = "",
        kipris_endpoint_url: str = "",
        trademark_keywords: list[str] | None = None,
        output_dir: str | Path = "outputs/trend_reports",
    ) -> ThirtyDayTrendReport:
        clean_keywords = _clean_keywords(keywords or self.DEFAULT_KEYWORDS)[:20]
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        manual_blob = manual_text or " ".join(clean_keywords)
        manual_result = ManualTrendAnalyzer().analyze(manual_blob).to_dict()

        youtube_items: list[YoutubeVideoItem] = []
        yt_errors: list[str] = []
        quota = YoutubeCollector.estimate_quota(len(clean_keywords), youtube_max_per_keyword, include_youtube_comments)
        if youtube_api_key:
            try:
                youtube_items = YoutubeCollector(youtube_api_key).search_recent_multi(
                    clean_keywords,
                    max_results_per_keyword=youtube_max_per_keyword,
                    days=days,
                    include_comments=include_youtube_comments,
                    comments_per_video=comments_per_video,
                )
            except Exception as exc:
                yt_errors.append(f"YouTube 수집 실패: {exc}")

        naver_groups: list[NaverKeywordGroupResult] = []
        naver_errors: list[str] = []
        if naver_client_id and naver_client_secret:
            try:
                groups = self._make_naver_groups(clean_keywords)
                naver_groups = NaverDatalabCollector(naver_client_id, naver_client_secret).fetch_multiple_keyword_groups(groups, days=days)
            except Exception as exc:
                naver_errors.append(f"네이버 데이터랩 수집 실패: {exc}")

        trademark_targets = _clean_keywords(trademark_keywords or clean_keywords)[:20]
        trademark_results: list[TrademarkCheckResult] = KiprisTrademarkChecker(kipris_service_key, kipris_endpoint_url).check_keywords(
            trademark_targets,
            use_http_if_configured=bool(kipris_service_key and kipris_endpoint_url),
        )

        combined_text = manual_blob + " " + " ".join(_youtube_text(v) for v in youtube_items)
        combined_text += " " + " ".join(" ".join(g.keywords) for g in naver_groups)
        top = self._top_keywords(combined_text)
        phrases = self._phrases(combined_text, manual_result)
        formats = self._formats(combined_text, manual_result, naver_groups, youtube_items)
        characters = self._characters(top, formats)
        notes = self._notes(yt_errors, naver_errors, trademark_results)

        report = ThirtyDayTrendReport(
            days=days,
            keywords=clean_keywords,
            manual_summary=manual_result,
            youtube_items=[v.to_dict() for v in youtube_items],
            naver_groups=[g.to_dict() for g in naver_groups],
            trademark_results=[r.to_dict() for r in trademark_results],
            top_keywords=top,
            recommended_phrases=phrases,
            recommended_formats=formats,
            recommended_characters=characters,
            caution_notes=notes,
            quota_estimate=quota,
        )
        json_path = output / "trend_30day_report.json"
        html_path = output / "trend_30day_report.html"
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(self._html(report), encoding="utf-8")
        report.json_path = str(json_path)
        report.html_path = str(html_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(self._html(report), encoding="utf-8")
        return report

    def _make_naver_groups(self, keywords: list[str]) -> dict[str, list[str]]:
        groups = {
            "업무/직장": [k for k in keywords if any(x in k for x in ["직장", "퇴근", "출근", "업무", "넵", "확인", "월요", "회사"])],
            "감정/리액션": [k for k in keywords if any(x in k for x in ["피곤", "번아웃", "화남", "당황", "감사", "죄송", "축하", "대박"])],
            "이모티콘/캐릭터": [k for k in keywords if any(x in k for x in ["이모티콘", "캐릭터", "카톡", "귀여운", "하찮"])]
        }
        fallback = {"전체 키워드": keywords[:5]}
        return {k: v[:5] for k, v in groups.items() if v} or fallback

    def _top_keywords(self, text: str) -> list[tuple[str, int]]:
        tokens = re.findall(r"[가-힣A-Za-z0-9]+", text or "")
        stop = {"그리고", "하지만", "이모티콘", "캐릭터", "영상", "댓글", "입니다", "합니다", "있는", "없는", "최근", "분석"}
        counts = Counter(t for t in tokens if len(t) >= 2 and t not in stop)
        return counts.most_common(30)

    def _phrases(self, text: str, manual_result: dict) -> list[str]:
        base = list(manual_result.get("suggested_phrases", []))
        phrase_pool = ["넵", "확인했습니다", "감사합니다", "죄송합니다", "퇴근하고 싶습니다", "살려주세요", "괜찮아요", "잘자요", "축하해요", "파이팅", "잠시만요", "오늘도 버팁니다"]
        scored = []
        for p in phrase_pool:
            scored.append((p, text.count(p[:2]) + (3 if p in base else 0)))
        ordered = [p for p, _ in sorted(scored, key=lambda x: x[1], reverse=True)]
        return list(dict.fromkeys(ordered))[:12]

    def _formats(self, text: str, manual_result: dict, naver_groups: list[NaverKeywordGroupResult], youtube_items: list[YoutubeVideoItem]) -> list[str]:
        score = Counter()
        for f in manual_result.get("suggested_formats", []):
            score[f] += 3
        if any(k in text for k in ["넵", "확인", "죄송", "퇴근", "살려", "월요", "번아웃"]):
            score["animated_text"] += 5
            score["static_text"] += 4
        if any(k in text for k in ["대박", "축하", "폭발", "리액션"]):
            score["big"] += 2
            score["animated"] += 2
        if naver_groups:
            for group in naver_groups:
                if group.growth_ratio > 10:
                    score["static_text"] += 1
                    score["animated_text"] += 1
        if youtube_items:
            avg_comment = sum((v.comment_count or 0) for v in youtube_items) / max(1, len(youtube_items))
            if avg_comment > 20:
                score["animated_text"] += 1
        if not score:
            return ["static_text", "animated_text", "static"]
        label_map = {
            "static": "멈춰있는 이모티콘",
            "static_text": "문구 결합형 멈춰있는 이모티콘",
            "animated": "움직이는 이모티콘",
            "animated_text": "움직이는 문구 결합형 이모티콘",
            "big": "큰 이모티콘",
        }
        return [label_map.get(k, k) for k, _ in score.most_common(5)]

    def _characters(self, top: list[tuple[str, int]], formats: list[str]) -> list[str]:
        words = [k for k, _ in top[:10]]
        base = " ".join(words)
        ideas = []
        if any(k in base for k in ["퇴근", "직장", "업무", "회사", "확인", "넵"]):
            ideas.extend(["업무에 눌려 접히는 메모지 사원", "칭찬받으면 싹이 나는 감자 사원", "답장은 빠르지만 영혼 없는 돌멩이"])
        if any(k in base for k in ["피곤", "번아웃", "월요"]):
            ideas.extend(["월요일마다 녹아내리는 얼음 캐릭터", "퇴근 시간에만 펴지는 종이 캐릭터"])
        if any(k in base for k in ["보리", "쌀", "곡물"]):
            ideas.extend(["보리와 쌀알 콤비형", "작은 쌀알들이 같이 움직이는 무리형 캐릭터"])
        return list(dict.fromkeys(ideas or ["짧은 답장에 특화된 하찮은 사물 캐릭터", "문구와 같이 움직이는 표정형 캐릭터"]))[:8]

    def _notes(self, yt_errors: list[str], naver_errors: list[str], trademark_results: list[TrademarkCheckResult]) -> list[str]:
        notes = []
        notes.extend(yt_errors)
        notes.extend(naver_errors)
        if any(r.risk_score >= 70 for r in trademark_results):
            notes.append("상표/기존 캐릭터명 고위험 신호가 있습니다. 캐릭터명과 외형 방향을 바꾸세요.")
        notes.append("분석 자료는 공개 메타데이터와 입력 자료 기반입니다. 승인/수익 보장이 아니라 제작 방향 검토용입니다.")
        return notes

    def _html(self, report: ThirtyDayTrendReport) -> str:
        def table_rows(rows: list[dict[str, Any]], keys: list[str]) -> str:
            out = []
            for row in rows[:100]:
                out.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(k, '')))}</td>" for k in keys) + "</tr>")
            return "\n".join(out)

        yt_rows = table_rows(report.youtube_items, ["title", "channel_title", "published_at", "view_count", "like_count", "comment_count", "engagement_score"])
        tm_rows = table_rows(report.trademark_results, ["keyword", "risk_level", "risk_score", "source", "raw_count"])
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>30일 무료 API 트렌드 분석 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55}}table{{border-collapse:collapse;width:100%;margin:12px 0}}td,th{{border:1px solid #ddd;padding:8px;vertical-align:top}}th{{background:#f5f5f5}}.note{{background:#fff8dc;padding:12px;border:1px solid #eed}}</style></head><body>
<h1>30일 무료 API 트렌드 분석 리포트</h1>
<p><b>분석 기간:</b> 최근 {report.days}일 기준</p>
<p><b>분석 키워드:</b> {html.escape(', '.join(report.keywords))}</p>
<h2>핵심 키워드</h2><p>{html.escape(', '.join(k for k, _ in report.top_keywords[:15]))}</p>
<h2>추천 문구</h2><p>{html.escape(', '.join(report.recommended_phrases))}</p>
<h2>추천 포맷</h2><p>{html.escape(' → '.join(report.recommended_formats))}</p>
<h2>추천 캐릭터 방향</h2><ul>{''.join('<li>'+html.escape(x)+'</li>' for x in report.recommended_characters)}</ul>
<h2>YouTube 수집 결과</h2><table><tr><th>제목</th><th>채널</th><th>게시일</th><th>조회</th><th>좋아요</th><th>댓글</th><th>반응점수</th></tr>{yt_rows}</table>
<h2>네이버 데이터랩 결과</h2><pre>{html.escape(json.dumps(report.naver_groups, ensure_ascii=False, indent=2)[:5000])}</pre>
<h2>상표/명칭 위험 체크</h2><table><tr><th>키워드</th><th>위험도</th><th>점수</th><th>출처</th><th>API 후보수</th></tr>{tm_rows}</table>
<h2>주의 사항</h2><div class='note'>{'<br>'.join(html.escape(x) for x in report.caution_notes)}</div>
<h2>Quota 추정</h2><pre>{html.escape(json.dumps(report.quota_estimate, ensure_ascii=False, indent=2))}</pre>
</body></html>"""


def _clean_keywords(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        for part in re.split(r"[,/\n;+]+|\s{2,}", item or ""):
            p = part.strip()
            if p:
                result.append(p)
    return list(dict.fromkeys(result))


def _youtube_text(item: YoutubeVideoItem) -> str:
    comments = " ".join(item.top_comments or [])
    tags = " ".join(item.tags or [])
    return f"{item.title} {item.description} {tags} {comments}"
