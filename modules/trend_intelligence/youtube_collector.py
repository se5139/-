from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class YoutubeVideoItem:
    video_id: str
    title: str
    published_at: str
    channel_title: str
    description: str = ""
    tags: list[str] | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    engagement_score: float | None = None
    top_comments: list[str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class YoutubeCollector:
    """YouTube Data API v3 수집기.

    원칙:
    - 영상 파일을 다운로드하거나 재사용하지 않습니다.
    - 최근 30일 기준 제목/설명/태그/조회·좋아요·댓글 수/상위 댓글 텍스트만 분석합니다.
    - API 키가 없거나 네트워크가 막힌 환경에서는 수동 입력 분석을 사용합니다.
    """

    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
    VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
    COMMENT_THREADS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"

    def __init__(self, api_key: str, sleep_seconds: float = 0.0) -> None:
        self.api_key = (api_key or "").strip()
        self.sleep_seconds = max(0.0, sleep_seconds)

    @staticmethod
    def estimate_quota(keyword_count: int, max_results_per_keyword: int, include_comments: bool) -> dict:
        """대략적인 quota 사용량 추정. 실제 과금/할당량은 Google 콘솔 기준을 따릅니다."""
        keyword_count = max(0, keyword_count)
        search_units = keyword_count * 100
        video_batches = keyword_count  # 검색 키워드당 video.list 1회 기준
        video_units = video_batches
        comment_units = keyword_count * max_results_per_keyword if include_comments else 0
        return {
            "search_units_estimate": search_units,
            "videos_units_estimate": video_units,
            "comments_units_estimate": comment_units,
            "total_units_estimate": search_units + video_units + comment_units,
            "note": "search.list 중심 추정값입니다. 실제 quota 정책은 Google Cloud Console/YouTube Data API 설정을 확인하세요.",
        }

    def search_recent(self, query: str, max_results: int = 10, days: int = 30, include_comments: bool = False, comments_per_video: int = 3) -> list[YoutubeVideoItem]:
        if not self.api_key:
            raise ValueError("YouTube API 키가 비어 있습니다.")
        published_after = (datetime.now(timezone.utc) - timedelta(days=max(1, days))).isoformat().replace("+00:00", "Z")
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "viewCount",
            "maxResults": max(1, min(max_results, 50)),
            "publishedAfter": published_after,
            "key": self.api_key,
        }
        raw = self._get_json(self.SEARCH_URL, params)
        items: list[YoutubeVideoItem] = []
        ids: list[str] = []
        for item in raw.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue
            ids.append(video_id)
            snip = item.get("snippet", {})
            items.append(
                YoutubeVideoItem(
                    video_id=video_id,
                    title=snip.get("title", ""),
                    published_at=snip.get("publishedAt", ""),
                    channel_title=snip.get("channelTitle", ""),
                    description=snip.get("description", ""),
                    tags=[],
                    top_comments=[],
                )
            )
        details = self.fetch_details(ids) if ids else {}
        for item in items:
            detail = details.get(item.video_id, {})
            stats = detail.get("statistics", {})
            snippet = detail.get("snippet", {})
            item.view_count = _safe_int(stats.get("viewCount"))
            item.like_count = _safe_int(stats.get("likeCount"))
            item.comment_count = _safe_int(stats.get("commentCount"))
            item.tags = snippet.get("tags", [])[:20]
            item.engagement_score = self._engagement_score(item)
            if include_comments:
                try:
                    item.top_comments = self.fetch_top_comments(item.video_id, max_results=comments_per_video)
                except Exception:
                    item.top_comments = []
                if self.sleep_seconds:
                    time.sleep(self.sleep_seconds)
        return items

    def search_recent_multi(self, queries: list[str], max_results_per_keyword: int = 5, days: int = 30, include_comments: bool = False, comments_per_video: int = 3) -> list[YoutubeVideoItem]:
        seen: set[str] = set()
        merged: list[YoutubeVideoItem] = []
        for query in queries:
            query = (query or "").strip()
            if not query:
                continue
            for item in self.search_recent(query, max_results=max_results_per_keyword, days=days, include_comments=include_comments, comments_per_video=comments_per_video):
                if item.video_id in seen:
                    continue
                seen.add(item.video_id)
                merged.append(item)
            if self.sleep_seconds:
                time.sleep(self.sleep_seconds)
        return sorted(merged, key=lambda x: (x.view_count or 0, x.comment_count or 0), reverse=True)

    def fetch_details(self, video_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not video_ids:
            return {}
        params = {
            "part": "snippet,statistics",
            "id": ",".join(video_ids[:50]),
            "key": self.api_key,
        }
        raw = self._get_json(self.VIDEOS_URL, params)
        return {item.get("id", ""): item for item in raw.get("items", [])}

    def fetch_stats(self, video_ids: list[str]) -> dict[str, dict[str, int | None]]:
        details = self.fetch_details(video_ids)
        result: dict[str, dict[str, int | None]] = {}
        for vid, detail in details.items():
            stats = detail.get("statistics", {})
            result[vid] = {
                "viewCount": _safe_int(stats.get("viewCount")),
                "likeCount": _safe_int(stats.get("likeCount")),
                "commentCount": _safe_int(stats.get("commentCount")),
            }
        return result

    def fetch_top_comments(self, video_id: str, max_results: int = 5) -> list[str]:
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": max(1, min(max_results, 20)),
            "order": "relevance",
            "textFormat": "plainText",
            "key": self.api_key,
        }
        raw = self._get_json(self.COMMENT_THREADS_URL, params)
        comments: list[str] = []
        for item in raw.get("items", []):
            text = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {}).get("textDisplay", "")
            if text:
                comments.append(text)
        return comments

    def _engagement_score(self, item: YoutubeVideoItem) -> float:
        views = max(1, item.view_count or 0)
        likes = item.like_count or 0
        comments = item.comment_count or 0
        # 댓글은 이모티콘 반응 분석에서 가치가 커서 가중치를 줍니다.
        return round(((likes / views) * 100.0) + ((comments / views) * 300.0), 4)

    def _get_json(self, url: str, params: dict) -> dict:
        full_url = url + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(full_url, headers={"User-Agent": "KakaoEmoticonProfitSystem/7.0"})
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None
