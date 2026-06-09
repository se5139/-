from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, asdict
from datetime import date, timedelta


@dataclass
class NaverTrendPoint:
    period: str
    ratio: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NaverKeywordGroupResult:
    group_name: str
    keywords: list[str]
    points: list[NaverTrendPoint]
    average_ratio: float
    latest_ratio: float
    growth_ratio: float

    def to_dict(self) -> dict:
        return {
            "group_name": self.group_name,
            "keywords": self.keywords,
            "points": [p.to_dict() for p in self.points],
            "average_ratio": self.average_ratio,
            "latest_ratio": self.latest_ratio,
            "growth_ratio": self.growth_ratio,
        }


class NaverDatalabCollector:
    URL = "https://openapi.naver.com/v1/datalab/search"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()

    def fetch_keyword_trend(self, keyword_group_name: str, keywords: list[str], days: int = 30) -> list[NaverTrendPoint]:
        return self.fetch_keyword_group(keyword_group_name, keywords, days=days).points

    def fetch_keyword_group(self, keyword_group_name: str, keywords: list[str], days: int = 30) -> NaverKeywordGroupResult:
        if not self.client_id or not self.client_secret:
            raise ValueError("네이버 데이터랩 Client ID/Secret이 비어 있습니다.")
        clean_keywords = [k.strip() for k in keywords if k and k.strip()][:20]
        if not clean_keywords:
            raise ValueError("분석할 네이버 키워드가 비어 있습니다.")
        end = date.today()
        start = end - timedelta(days=max(1, days))
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "timeUnit": "date",
            "keywordGroups": [{"groupName": keyword_group_name, "keywords": clean_keywords}],
        }
        raw = self._post_json(body)
        data = raw.get("results", [{}])[0].get("data", [])
        points = [NaverTrendPoint(period=d.get("period", ""), ratio=float(d.get("ratio", 0))) for d in data]
        return _summarize_group(keyword_group_name, clean_keywords, points)

    def fetch_multiple_keyword_groups(self, groups: dict[str, list[str]], days: int = 30) -> list[NaverKeywordGroupResult]:
        results: list[NaverKeywordGroupResult] = []
        for group_name, keywords in groups.items():
            if not keywords:
                continue
            results.append(self.fetch_keyword_group(group_name, keywords, days=days))
        return sorted(results, key=lambda x: (x.growth_ratio, x.latest_ratio, x.average_ratio), reverse=True)

    def _post_json(self, body: dict) -> dict:
        request = urllib.request.Request(self.URL)
        request.add_header("X-Naver-Client-Id", self.client_id)
        request.add_header("X-Naver-Client-Secret", self.client_secret)
        request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request, data=json.dumps(body).encode("utf-8"), timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))


def _summarize_group(group_name: str, keywords: list[str], points: list[NaverTrendPoint]) -> NaverKeywordGroupResult:
    ratios = [p.ratio for p in points]
    avg = round(sum(ratios) / len(ratios), 2) if ratios else 0.0
    latest = round(ratios[-1], 2) if ratios else 0.0
    if len(ratios) >= 6:
        early = sum(ratios[:5]) / 5
        late = sum(ratios[-5:]) / 5
        growth = round(late - early, 2)
    elif len(ratios) >= 2:
        growth = round(ratios[-1] - ratios[0], 2)
    else:
        growth = 0.0
    return NaverKeywordGroupResult(group_name, keywords, points, avg, latest, growth)
