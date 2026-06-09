from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict


@dataclass
class TrademarkCheckResult:
    keyword: str
    risk_level: str
    risk_score: int
    findings: list[str]
    source: str = "offline_keyword_check"
    raw_count: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class KiprisTrademarkChecker:
    """캐릭터명/이모티콘명 상표 위험 체크.

    KIPRIS Plus API는 사용자가 발급받은 서비스키와 세부 API URL/권한에 따라 호출 방식이 달라질 수 있습니다.
    v7에서는 안전하게 쓸 수 있는 오프라인 위험 키워드 검사와, URL이 확인된 경우에만 호출하는 선택형 HTTP 테스트를 제공합니다.
    """

    RISK_KEYWORDS = {
        "춘식이", "라이언", "어피치", "카카오프렌즈", "라인프렌즈", "산리오", "헬로키티", "포켓몬",
        "피카츄", "디즈니", "미키", "짱구", "스누피", "도라에몽", "마블", "아이언맨", "스파이더맨",
    }

    GENERIC_HIGH_COMPETITION = {"고양이", "강아지", "토끼", "곰", "감자", "직장인", "커플", "친구"}

    def __init__(self, service_key: str = "", endpoint_url: str = "") -> None:
        self.service_key = (service_key or "").strip()
        self.endpoint_url = (endpoint_url or "").strip()

    def check_keywords(self, keywords: list[str], use_http_if_configured: bool = False) -> list[TrademarkCheckResult]:
        results = []
        for keyword in keywords:
            kw = (keyword or "").strip()
            if not kw:
                continue
            result = self.offline_check(kw)
            if use_http_if_configured and self.service_key and self.endpoint_url:
                try:
                    api_count = self._try_http_count(kw)
                    result.raw_count = api_count
                    result.source = "kipris_http_test"
                    if api_count and api_count > 0:
                        result.risk_score = min(100, max(result.risk_score, 45 + min(api_count, 20)))
                        result.risk_level = _level(result.risk_score)
                        result.findings.append(f"KIPRIS API 테스트 결과 유사/동일 후보 {api_count}건 감지 · 상세 분류 확인 필요")
                except Exception as exc:
                    result.findings.append(f"KIPRIS HTTP 테스트 실패: {exc}")
            results.append(result)
        return sorted(results, key=lambda x: x.risk_score, reverse=True)

    def offline_check(self, keyword: str) -> TrademarkCheckResult:
        findings: list[str] = []
        score = 0
        lowered = keyword.lower()
        for risk in self.RISK_KEYWORDS:
            if risk.lower() in lowered:
                score += 80
                findings.append(f"기존 유명 캐릭터/브랜드 연상 키워드 포함: {risk}")
        for generic in self.GENERIC_HIGH_COMPETITION:
            if generic in keyword:
                score += 12
                findings.append(f"경쟁 과밀 가능 소재: {generic}")
        if len(keyword) <= 2:
            score += 15
            findings.append("너무 짧은 명칭은 동일/유사 명칭 충돌 가능성이 높습니다.")
        if not findings:
            findings.append("오프라인 키워드 검사에서 즉시 고위험 신호는 낮습니다. 실제 제출 전 KIPRIS 정식 검색을 권장합니다.")
        score = min(100, score)
        return TrademarkCheckResult(keyword=keyword, risk_level=_level(score), risk_score=score, findings=findings)

    def _try_http_count(self, keyword: str) -> int:
        params = {"word": keyword, "ServiceKey": self.service_key}
        url = self.endpoint_url + ("&" if "?" in self.endpoint_url else "?") + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": "KakaoEmoticonProfitSystem/7.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            text = response.read().decode("utf-8", errors="ignore")
        try:
            raw = json.loads(text)
            blob = json.dumps(raw, ensure_ascii=False)
        except Exception:
            blob = text
        # 포맷이 API별로 다를 수 있으므로 보수적 카운트만 수행합니다.
        return max(blob.count("title"), blob.count("trademark"), blob.count("상표"), blob.count(keyword))


def _level(score: int) -> str:
    if score >= 70:
        return "높음"
    if score >= 35:
        return "주의"
    return "낮음"
