
from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class GrowthLearningReport:
    created_at: str
    project_name: str
    total_events: int
    total_outcomes: int
    learning_level: str
    confidence_score: int
    recommended_formats: list[dict]
    recommended_keywords: list[dict]
    improvement_actions: list[str]
    data_health: list[dict]
    html_path: str
    json_path: str
    csv_path: str
    dataset_path: str

    def to_dict(self) -> dict:
        return asdict(self)


class GrowthLearningEngine:
    """누적 데이터 기반 성장형 추천 엔진.

    목표:
    - 트렌드/제작/품질/채팅 미리보기/저작권/심사/판매 기록을 JSONL로 계속 누적합니다.
    - 다음 캐릭터, 포맷, 표현 세트, 수정 우선순위를 추천합니다.
    - 기존 데이터는 삭제하지 않고 append-only 방식으로 기록합니다.
    """

    FORMAT_KEYS = {
        "static": "멈춰있는 이모티콘",
        "static_text": "문구 결합형 멈춰있는 이모티콘",
        "animated": "움직이는 이모티콘",
        "animated_text": "움직이는 문구 결합형 이모티콘",
        "big": "큰 이모티콘",
    }

    def default_data_dir(self, app_folder: str = "KakaoEmoticonProfitSystem") -> Path:
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            return base / app_folder / "UserData" / "growth_learning"
        return Path.home() / ".kakao_emoticon_profit_system" / "UserData" / "growth_learning"

    def ensure_store(self, root: str | Path | None = None) -> dict[str, Path]:
        base = Path(root) if root else self.default_data_dir()
        base.mkdir(parents=True, exist_ok=True)
        paths = {
            "base": base,
            "events": base / "learning_events.jsonl",
            "outcomes": base / "outcome_events.jsonl",
            "snapshots": base / "snapshots",
            "reports": base / "reports",
        }
        paths["snapshots"].mkdir(parents=True, exist_ok=True)
        paths["reports"].mkdir(parents=True, exist_ok=True)
        for key in ["events", "outcomes"]:
            paths[key].touch(exist_ok=True)
        return paths

    def _append_jsonl(self, path: Path, row: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        rows = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def _safe_dict(self, value: Any) -> dict:
        if value is None:
            return {}
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if isinstance(value, dict):
            return value
        return {}

    def _list_dict(self, value: Any) -> list[dict]:
        if not value:
            return []
        result=[]
        for item in value:
            if hasattr(item, "to_dict"):
                result.append(item.to_dict())
            elif isinstance(item, dict):
                result.append(item)
        return result

    def record_snapshot(
        self,
        project_name: str,
        concept_text: str = "",
        profile: dict | None = None,
        expressions: list[dict] | None = None,
        format_scores: list[dict] | None = None,
        trend_result: dict | None = None,
        api_trend_report: dict | None = None,
        candidate_gallery_report: dict | None = None,
        quality_review: dict | None = None,
        chat_preview_report: dict | None = None,
        copyright_report: dict | None = None,
        sample_set_report: dict | None = None,
        output_root: str | Path | None = None,
    ) -> dict:
        paths = self.ensure_store(output_root)
        created_at = datetime.now().isoformat(timespec="seconds")
        expressions = expressions or []
        format_scores = format_scores or []
        keywords = self._extract_keywords(concept_text, profile, trend_result, api_trend_report, expressions)
        row = {
            "event_type": "snapshot",
            "created_at": created_at,
            "project_name": project_name,
            "concept_text": concept_text,
            "profile": profile or {},
            "expression_count": len(expressions),
            "top_expressions": expressions[:20],
            "format_scores": format_scores,
            "trend_summary": trend_result or {},
            "api_trend_summary": api_trend_report or {},
            "candidate_gallery_summary": self._compact_report(candidate_gallery_report),
            "quality_review_summary": self._compact_report(quality_review),
            "chat_preview_summary": self._compact_report(chat_preview_report),
            "copyright_summary": self._compact_report(copyright_report),
            "sample_set_summary": self._compact_report(sample_set_report),
            "keywords": keywords,
        }
        self._append_jsonl(paths["events"], row)
        snapshot_path = paths["snapshots"] / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        snapshot_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"saved": True, "dataset_path": str(paths["events"]), "snapshot_path": str(snapshot_path), "event": row}

    def record_outcome(
        self,
        project_name: str,
        character_name: str,
        format_key: str,
        status: str,
        submitted_at: str = "",
        result_at: str = "",
        rejection_reason: str = "",
        sales_note: str = "",
        revenue_amount: float = 0.0,
        downloads_or_sales_count: int = 0,
        output_root: str | Path | None = None,
    ) -> dict:
        paths = self.ensure_store(output_root)
        row = {
            "event_type": "outcome",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "character_name": character_name,
            "format_key": format_key,
            "format_label": self.FORMAT_KEYS.get(format_key, format_key),
            "status": status,
            "submitted_at": submitted_at,
            "result_at": result_at,
            "rejection_reason": rejection_reason,
            "sales_note": sales_note,
            "revenue_amount": float(revenue_amount or 0),
            "downloads_or_sales_count": int(downloads_or_sales_count or 0),
        }
        self._append_jsonl(paths["outcomes"], row)
        return {"saved": True, "dataset_path": str(paths["outcomes"]), "event": row}

    def build_growth_report(
        self,
        project_name: str = "growth_learning_report",
        output_dir: str | Path | None = None,
        store_root: str | Path | None = None,
    ) -> GrowthLearningReport:
        paths = self.ensure_store(store_root)
        out = Path(output_dir) if output_dir else paths["reports"]
        out.mkdir(parents=True, exist_ok=True)
        events = self._read_jsonl(paths["events"])
        outcomes = self._read_jsonl(paths["outcomes"])

        format_scores = self._score_formats(events, outcomes)
        keywords = self._score_keywords(events)
        actions = self._build_actions(events, outcomes, format_scores, keywords)
        data_health = self._data_health(events, outcomes)
        confidence = self._confidence_score(events, outcomes)
        learning_level = self._learning_level(confidence, len(events), len(outcomes))

        created = datetime.now().isoformat(timespec="seconds")
        csv_path = out / "growth_learning_scores.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["type", "name", "score", "count", "note"])
            writer.writeheader()
            for row in format_scores:
                writer.writerow({"type":"format", "name":row["format_label"], "score":row["score"], "count":row["count"], "note":row.get("note","")})
            for row in keywords[:30]:
                writer.writerow({"type":"keyword", "name":row["keyword"], "score":row["score"], "count":row["count"], "note":row.get("note","")})

        html_path = out / "growth_learning_report.html"
        json_path = out / "growth_learning_report.json"
        report = GrowthLearningReport(
            created_at=created,
            project_name=project_name,
            total_events=len(events),
            total_outcomes=len(outcomes),
            learning_level=learning_level,
            confidence_score=confidence,
            recommended_formats=format_scores,
            recommended_keywords=keywords[:30],
            improvement_actions=actions,
            data_health=data_health,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            dataset_path=str(paths["base"]),
        )
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(self._render_html(report), encoding="utf-8")
        return report

    def _compact_report(self, report: dict | None) -> dict:
        if not report:
            return {}
        keys = [
            "overall_score", "final_status", "actual_count", "selected_count", "sample_score", "sample_status",
            "chat_usability_score", "preview_count", "overall_risk_score", "compliance_score", "quality_score"
        ]
        compact = {k: report.get(k) for k in keys if k in report}
        for path_key in ["html_path", "json_path", "csv_path", "zip_path"]:
            if path_key in report:
                compact[path_key] = report.get(path_key)
        return compact

    def _extract_keywords(self, concept_text: str, profile: dict | None, trend: dict | None, api: dict | None, expressions: list[dict]) -> list[str]:
        words=[]
        for text in [concept_text, (profile or {}).get("raw_text", "")]:
            words += self._tokenize(text)
        for k in ["top_keywords", "recommended_keywords"]:
            vals = (trend or {}).get(k, []) or (api or {}).get(k, [])
            for item in vals:
                if isinstance(item, dict):
                    words.append(str(item.get("keyword") or item.get("word") or ""))
                else:
                    words.append(str(item))
        for e in expressions[:80]:
            words += self._tokenize(str(e.get("phrase", e.get("text", ""))))
        return [w for w in words if w]

    def _tokenize(self, text: str) -> list[str]:
        if not text:
            return []
        separators = [",", "/", "+", "·", "|", "\n", "\t", "와", "과", "및"]
        tmp = text
        for sep in separators:
            tmp = tmp.replace(sep, " ")
        stop = {"그리고", "이모티콘", "캐릭터", "문구", "같이", "있는", "기반", "자동", "생성", "추천", "분석"}
        return [w.strip() for w in tmp.split() if len(w.strip()) >= 2 and w.strip() not in stop]

    def _score_formats(self, events: list[dict], outcomes: list[dict]) -> list[dict]:
        score = defaultdict(lambda: {"base":50, "count":0, "label":"", "outcomes":0, "success":0})
        for ev in events:
            for fs in ev.get("format_scores", []) or []:
                key = str(fs.get("format_key") or fs.get("key") or fs.get("label") or "unknown")
                label = str(fs.get("label") or self.FORMAT_KEYS.get(key, key))
                val = int(fs.get("score", fs.get("format_score", 50)) or 50)
                score[key]["base"] += val
                score[key]["count"] += 1
                score[key]["label"] = label
        for oc in outcomes:
            key = oc.get("format_key", "unknown")
            score[key]["label"] = oc.get("format_label") or self.FORMAT_KEYS.get(key, key)
            score[key]["outcomes"] += 1
            status = str(oc.get("status", ""))
            revenue = float(oc.get("revenue_amount", 0) or 0)
            sales = int(oc.get("downloads_or_sales_count", 0) or 0)
            if any(x in status for x in ["승인", "출시", "판매"]):
                score[key]["success"] += 1
            score[key]["base"] += min(25, revenue / 10000) + min(15, sales / 10)
        rows=[]
        for key, val in score.items():
            cnt=max(1,val["count"])
            base=int(val["base"] / cnt)
            outcome_bonus=0
            if val["outcomes"]:
                outcome_bonus = int((val["success"] / val["outcomes"]) * 15)
            final=max(0, min(100, base + outcome_bonus))
            rows.append({
                "format_key": key,
                "format_label": val["label"] or self.FORMAT_KEYS.get(key, key),
                "score": final,
                "count": val["count"] + val["outcomes"],
                "note": "누적 추천/품질/심사·판매 기록 기반 점수",
            })
        if not rows:
            rows=[{"format_key":"static_text", "format_label":"문구 결합형 멈춰있는 이모티콘", "score":65, "count":0, "note":"데이터 부족: 기본 추천"}]
        return sorted(rows, key=lambda r: r["score"], reverse=True)

    def _score_keywords(self, events: list[dict]) -> list[dict]:
        counter=Counter()
        for ev in events:
            counter.update([k for k in ev.get("keywords", []) if k])
        rows=[]
        for word, count in counter.most_common(100):
            rows.append({"keyword":word, "score":min(100, 50 + count*5), "count":count, "note":"누적 프로젝트/트렌드/표현 후보에서 반복 등장"})
        return rows

    def _data_health(self, events: list[dict], outcomes: list[dict]) -> list[dict]:
        checks=[]
        checks.append({"item":"제작/분석 스냅샷", "count":len(events), "status":"양호" if len(events)>=10 else "축적 필요"})
        checks.append({"item":"심사/판매 결과", "count":len(outcomes), "status":"양호" if len(outcomes)>=5 else "축적 필요"})
        checks.append({"item":"최소 30일 데이터", "count":len(events), "status":"30일 이상 누적 권장"})
        checks.append({"item":"데이터 삭제 방지", "count":1, "status":"append-only 저장 구조"})
        return checks

    def _confidence_score(self, events: list[dict], outcomes: list[dict]) -> int:
        score = min(55, len(events)*5) + min(35, len(outcomes)*7)
        if len(events) >= 30:
            score += 10
        return max(5, min(100, score))

    def _learning_level(self, confidence: int, events_count: int, outcomes_count: int) -> str:
        if confidence >= 80 and outcomes_count >= 10:
            return "강화 학습 단계"
        if confidence >= 55:
            return "추천 보정 단계"
        if events_count >= 10:
            return "초기 패턴 축적 단계"
        return "데이터 축적 시작 단계"

    def _build_actions(self, events: list[dict], outcomes: list[dict], format_scores: list[dict], keywords: list[dict]) -> list[str]:
        actions=[]
        if len(events) < 10:
            actions.append("최소 10개 이상의 캐릭터/표현/품질검사 스냅샷을 저장해 초기 패턴을 확보하세요.")
        if len(outcomes) < 5:
            actions.append("카카오 제출 결과, 반려 사유, 출시 후 반응을 최소 5건 이상 기록하면 추천 정확도가 올라갑니다.")
        if format_scores:
            actions.append(f"현재 누적 데이터 기준 1순위 포맷은 '{format_scores[0]['format_label']}'입니다.")
        if keywords:
            top = ', '.join([k['keyword'] for k in keywords[:5]])
            actions.append(f"반복 등장 키워드: {top}. 다음 캐릭터/문구 후보에 우선 반영하세요.")
        actions.append("새 버전 업데이트 전에는 v19 데이터 보호/백업 기능으로 UserData와 outputs를 먼저 백업하세요.")
        actions.append("학습 데이터는 삭제하지 말고 누적 저장하세요. 잘못된 데이터만 사용자가 승인 후 제외 처리하는 방식이 안전합니다.")
        return actions

    def _render_html(self, report: GrowthLearningReport) -> str:
        def table(rows, cols):
            if not rows:
                return "<p>데이터 없음</p>"
            head=''.join(f"<th>{c}</th>" for c in cols)
            body=''.join('<tr>'+''.join(f"<td>{row.get(c,'')}</td>" for c in cols)+'</tr>' for row in rows)
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>성장형 학습 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;line-height:1.55}}table{{border-collapse:collapse;width:100%;margin:12px 0}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#f5f5f5}}.card{{padding:14px;border:1px solid #ddd;border-radius:10px;margin:10px 0}}</style></head><body>
<h1>카카오 이모티콘 성장형 학습 리포트</h1>
<div class='card'><b>프로젝트:</b> {report.project_name}<br><b>생성:</b> {report.created_at}<br><b>학습 단계:</b> {report.learning_level}<br><b>신뢰도:</b> {report.confidence_score}/100<br><b>스냅샷:</b> {report.total_events}건 · <b>결과 기록:</b> {report.total_outcomes}건</div>
<h2>추천 포맷</h2>{table(report.recommended_formats, ['format_label','score','count','note'])}
<h2>추천 키워드</h2>{table(report.recommended_keywords, ['keyword','score','count','note'])}
<h2>데이터 상태</h2>{table(report.data_health, ['item','count','status'])}
<h2>다음 개선 액션</h2><ol>{''.join(f'<li>{a}</li>' for a in report.improvement_actions)}</ol>
<p>주의: 이 리포트는 누적 데이터 기반 추천 보조 자료이며 카카오 승인 또는 수익을 보장하지 않습니다.</p>
</body></html>"""
