from __future__ import annotations

import csv
import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except Exception:
        import re
        m = re.search(r"-?\d+(?:\.\d+)?", text)
        return float(m.group(0)) if m else 0.0


def _int(value: Any) -> int:
    return int(round(_num(value)))


def _safe(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "미지정"


def _esc(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@dataclass
class PerformanceDashboardReport:
    project_name: str
    generated_at: str
    source_summary: Dict[str, Any]
    portfolio_metrics: Dict[str, Any]
    dashboard_rows: List[Dict[str, Any]]
    top_projects: List[Dict[str, Any]]
    weak_projects: List[Dict[str, Any]]
    strategy_recommendations: List[Dict[str, Any]]
    series_candidates: List[Dict[str, Any]]
    format_expansion_candidates: List[Dict[str, Any]]
    next_production_plan: List[Dict[str, Any]]
    data_needs: List[Dict[str, Any]]
    safety_notes: List[str]
    files: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceDashboardEngine:
    """v40 성과 데이터 대시보드와 다음 제작 방향 추천 엔진.

    v39 카카오 스튜디오 엑셀 성과 학습 리포트의 plus/sales/performance 데이터를 받아,
    작품별 성과·약점·시리즈화·포맷 확장·다음 4주 실행 계획을 생성한다.
    """

    def build_report(
        self,
        output_dir: Path,
        project_name: str = "kakao_performance_dashboard",
        kakao_excel_report: Optional[Dict[str, Any]] = None,
        learning_records: Optional[List[Dict[str, Any]]] = None,
    ) -> PerformanceDashboardReport:
        output_dir = Path(output_dir)
        run_dir = output_dir / f"performance_dashboard_v40_{_now()}"
        report_dir = run_dir / "report"
        data_dir = run_dir / "dashboard_data"
        for d in [report_dir, data_dir]:
            d.mkdir(parents=True, exist_ok=True)

        source = self._merge_sources(kakao_excel_report or {}, learning_records or [])
        rows = self._build_dashboard_rows(source)
        metrics = self._portfolio_metrics(rows)
        top_projects = [r for r in rows if r["performance_band"] in ("확장 검토", "강한 성과")][:10]
        weak_projects = [r for r in rows if r["performance_band"] in ("데이터 부족", "보완 필요")][:10]
        strategy = self._strategy_recommendations(rows, metrics)
        series = self._series_candidates(rows)
        expansions = self._format_expansion_candidates(rows)
        plan = self._next_production_plan(rows, metrics)
        needs = self._data_needs(rows, metrics, source)
        safety = [
            "처음부터 모든 포맷을 동시에 만들지 않고, 1차 포맷 성과를 본 뒤 시리즈/미니/움직이는 버전을 단계적으로 검토합니다.",
            "성과 데이터가 0이거나 부족하면 확장 추천보다 추가 데이터 축적을 우선합니다.",
            "카카오 스튜디오 엑셀 데이터는 실제 운영 참고 자료이며, 승인·수익을 보장하지 않습니다.",
            "제출 전에는 v30 잠금 체크리스트, v36 규격/용량 검수, v19 데이터 백업을 함께 실행해야 합니다.",
        ]

        files: Dict[str, str] = {"run_dir": str(run_dir)}
        files.update(self._write_table(data_dir, "dashboard_rows", rows))
        files.update(self._write_table(data_dir, "strategy_recommendations", strategy))
        files.update(self._write_table(data_dir, "series_candidates", series))
        files.update(self._write_table(data_dir, "format_expansion_candidates", expansions))
        files.update(self._write_table(data_dir, "next_production_plan", plan))
        files.update(self._write_table(data_dir, "data_needs", needs))

        report = PerformanceDashboardReport(
            project_name=project_name,
            generated_at=datetime.now().isoformat(timespec="seconds"),
            source_summary=source["summary"],
            portfolio_metrics=metrics,
            dashboard_rows=rows,
            top_projects=top_projects,
            weak_projects=weak_projects,
            strategy_recommendations=strategy,
            series_candidates=series,
            format_expansion_candidates=expansions,
            next_production_plan=plan,
            data_needs=needs,
            safety_notes=safety,
            files=files,
        )
        html_path = report_dir / "performance_dashboard_v40.html"
        json_path = report_dir / "performance_dashboard_v40.json"
        self._write_html(report, html_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        files["html_path"] = str(html_path)
        files["json_path"] = str(json_path)
        zip_path = run_dir / "performance_dashboard_v40.zip"
        self._zip_run(run_dir, zip_path)
        files["zip_path"] = str(zip_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def load_learning_jsonl(self, jsonl_path: Path, limit: int = 200) -> List[Dict[str, Any]]:
        path = Path(jsonl_path)
        if not path.exists():
            return []
        records: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
        return records[-limit:]

    def _merge_sources(self, report: Dict[str, Any], learning_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        plus_rows: List[Dict[str, Any]] = []
        sales_summary: List[Dict[str, Any]] = []
        sales_details: List[Dict[str, Any]] = []
        performance_scores: List[Dict[str, Any]] = []
        periods: List[Dict[str, Any]] = []

        if report:
            plus_rows.extend(report.get("plus_rows", []) or [])
            sales_summary.extend(report.get("sales_summary", []) or [])
            sales_details.extend(report.get("sales_details", []) or [])
            performance_scores.extend(report.get("performance_scores", []) or [])
            if report.get("period"):
                periods.append(report.get("period", {}))
        for rec in learning_records:
            plus_rows.extend(rec.get("plus_rows", []) or [])
            sales_summary.extend(rec.get("sales_summary", []) or [])
            sales_details.extend(rec.get("sales_details", []) or [])
            performance_scores.extend(rec.get("performance_scores", []) or [])
            if rec.get("period"):
                periods.append(rec.get("period", {}))

        summary = {
            "plus_row_count": len(plus_rows),
            "sales_summary_count": len(sales_summary),
            "sales_detail_count": len(sales_details),
            "performance_score_count": len(performance_scores),
            "learning_record_count": len(learning_records),
            "period_start": min([p.get("start_date") for p in periods if p.get("start_date")] or [""]),
            "period_end": max([p.get("end_date") for p in periods if p.get("end_date")] or [""]),
        }
        return {"plus_rows": plus_rows, "sales_summary": sales_summary, "sales_details": sales_details, "performance_scores": performance_scores, "summary": summary}

    def _build_dashboard_rows(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        bucket: Dict[str, Dict[str, Any]] = {}
        for row in source.get("plus_rows", []):
            name = _safe(row.get("emoticon_name"))
            series = _safe(row.get("series_name")) if row.get("series_name") else ""
            key = name + "||" + series
            rec = bucket.setdefault(key, {"emoticon_name": name, "series_name": series, "sent_count": 0, "user_count": 0, "sales_count": 0, "sales_amount": 0.0, "data_sources": set()})
            rec["sent_count"] += _int(row.get("sent_count", 0))
            rec["user_count"] += _int(row.get("user_count", 0))
            rec["data_sources"].add("plus")
        for row in source.get("sales_details", []):
            name = _safe(row.get("emoticon_title"))
            series = _safe(row.get("series_name")) if row.get("series_name") else ""
            key = name + "||" + series
            rec = bucket.setdefault(key, {"emoticon_name": name, "series_name": series, "sent_count": 0, "user_count": 0, "sales_count": 0, "sales_amount": 0.0, "data_sources": set()})
            rec["sales_count"] += _int(row.get("sales_count", 0))
            rec["sales_amount"] += _num(row.get("amount", 0))
            rec["data_sources"].add("sales")
        # v39 performance_scores만 있고 원천 행이 없는 경우도 수용
        for row in source.get("performance_scores", []):
            name = _safe(row.get("emoticon_name"))
            series = _safe(row.get("series_name")) if row.get("series_name") else ""
            key = name + "||" + series
            rec = bucket.setdefault(key, {"emoticon_name": name, "series_name": series, "sent_count": 0, "user_count": 0, "sales_count": 0, "sales_amount": 0.0, "data_sources": set()})
            rec["sent_count"] = max(_int(rec.get("sent_count")), _int(row.get("sent_count", 0)))
            rec["user_count"] = max(_int(rec.get("user_count")), _int(row.get("user_count", 0)))
            rec["sales_count"] = max(_int(rec.get("sales_count")), _int(row.get("sales_count", 0)))
            rec["sales_amount"] = max(_num(rec.get("sales_amount")), _num(row.get("sales_amount", 0)))
            rec["data_sources"].add("score")

        rows: List[Dict[str, Any]] = []
        for rec in bucket.values():
            sent = _int(rec.get("sent_count"))
            users = _int(rec.get("user_count"))
            sales_count = _int(rec.get("sales_count"))
            sales_amount = _num(rec.get("sales_amount"))
            repeat_rate = round(sent / users, 3) if users else 0
            plus_strength = self._strength(sent, users, repeat_rate)
            sales_strength = self._sales_strength(sales_count, sales_amount)
            total_score = round(min(100, sent * 0.08 + users * 0.25 + repeat_rate * 4 + sales_count * 3 + sales_amount / 15000), 1)
            band = self._performance_band(total_score, sent, users, sales_count, sales_amount)
            next_direction = self._next_direction(sent, users, repeat_rate, sales_count, sales_amount, band)
            rows.append({
                "emoticon_name": rec["emoticon_name"],
                "series_name": rec.get("series_name", ""),
                "sent_count": sent,
                "user_count": users,
                "repeat_rate": repeat_rate,
                "sales_count": sales_count,
                "sales_amount": round(sales_amount, 0),
                "plus_strength": plus_strength,
                "sales_strength": sales_strength,
                "total_score": total_score,
                "performance_band": band,
                "next_direction": next_direction,
                "data_sources": ",".join(sorted(rec.get("data_sources", []))),
            })
        return sorted(rows, key=lambda x: x["total_score"], reverse=True)

    def _portfolio_metrics(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        sent = sum(_int(r.get("sent_count")) for r in rows)
        users = sum(_int(r.get("user_count")) for r in rows)
        sales_count = sum(_int(r.get("sales_count")) for r in rows)
        amount = sum(_num(r.get("sales_amount")) for r in rows)
        strong = sum(1 for r in rows if r.get("performance_band") in ("확장 검토", "강한 성과"))
        weak = sum(1 for r in rows if r.get("performance_band") in ("데이터 부족", "보완 필요"))
        data_stage = "성과 판단 가능" if (sent or users or sales_count or amount) and rows else "데이터 축적 필요"
        return {
            "project_count": len(rows),
            "total_sent": sent,
            "total_users": users,
            "portfolio_repeat_rate": round(sent / users, 3) if users else 0,
            "total_sales_count": sales_count,
            "total_sales_amount": round(amount, 0),
            "strong_project_count": strong,
            "weak_project_count": weak,
            "data_stage": data_stage,
        }

    def _strategy_recommendations(self, rows: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        recs: List[Dict[str, Any]] = []
        if not rows or metrics.get("data_stage") == "데이터 축적 필요":
            recs.append({"priority": 1, "strategy": "데이터 축적 우선", "reason": "발신/판매 데이터가 아직 부족합니다.", "action": "카카오 스튜디오 플러스 발신 통계와 판매내역 엑셀을 2~4주 단위로 누적 업로드합니다."})
            recs.append({"priority": 2, "strategy": "1차 포맷 유지", "reason": "확장 판단 근거가 부족합니다.", "action": "처음에는 문구형 정지 또는 현재 1차 포맷만 완성하고, 미니/큰/움직이는 확장은 보류합니다."})
            return recs
        high_plus = [r for r in rows if r["sent_count"] > 0 and r["user_count"] > 0]
        high_sales = [r for r in rows if r["sales_count"] > 0 or r["sales_amount"] > 0]
        if high_plus:
            recs.append({"priority": 1, "strategy": "반복 사용 문구 강화", "reason": "플러스 발신 데이터가 있는 작품이 있습니다.", "action": "확인/감사/사과/퇴근/잘자 같은 짧은 답장형 문구를 다음 세트에 우선 배치합니다."})
        if high_sales:
            recs.append({"priority": 2, "strategy": "판매형 대표 이미지/제목 유지", "reason": "실제 판매가 발생한 작품이 있습니다.", "action": "판매가 나온 작품의 제목 구조, 공유 이미지 톤, 캐릭터 콘셉트를 다음 시리즈에 반영합니다."})
        strong = [r for r in rows if r["performance_band"] in ("확장 검토", "강한 성과")]
        if strong:
            recs.append({"priority": 3, "strategy": "시리즈 2탄 검토", "reason": "성과 점수가 높은 작품이 있습니다.", "action": "같은 캐릭터로 상황만 바꾼 2탄, 직장인편, 사투리편, 미니 리액션편을 후보로 만듭니다."})
        weak = [r for r in rows if r["performance_band"] == "보완 필요"]
        if weak:
            recs.append({"priority": 4, "strategy": "보완 후 재제작", "reason": "반응이 약한 작품이 있습니다.", "action": "문구 길이, 캐릭터 성격 선명도, 채팅창 가독성, 대표 제목을 v29/v34로 다시 점검합니다."})
        return recs

    def _series_candidates(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for r in rows[:20]:
            if r["performance_band"] not in ("확장 검토", "강한 성과"):
                continue
            base = r["emoticon_name"]
            result.extend([
                {"base_project": base, "series_candidate": f"{base} 2탄 - 짧은 답장편", "reason": "발신/사용성 기반 확장", "priority": "높음"},
                {"base_project": base, "series_candidate": f"{base} - 직장인/퇴근편", "reason": "반복 사용 가능한 생활 문구 확장", "priority": "중간"},
            ])
        if not result:
            result.append({"base_project": "-", "series_candidate": "시리즈 판단 보류", "reason": "성과 데이터가 부족합니다.", "priority": "보류"})
        return result

    def _format_expansion_candidates(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for r in rows[:20]:
            name = r["emoticon_name"]
            if r["performance_band"] in ("확장 검토", "강한 성과"):
                if r["sent_count"] and r["user_count"]:
                    result.append({"project": name, "candidate_format": "문구형 정지 2탄", "reason": "플러스 발신/사용성 데이터가 있어 같은 문구형 확장이 우선입니다.", "status": "우선 검토"})
                    result.append({"project": name, "candidate_format": "움직이는 문구형", "reason": "1차 문구가 검증되면 모션을 붙여 2차 확장할 수 있습니다.", "status": "후순위 검토"})
                if r["repeat_rate"] >= 2:
                    result.append({"project": name, "candidate_format": "미니 이모티콘", "reason": "반복 사용률이 있어 짧은 조합형 리액션으로 검토 가능합니다.", "status": "조건부 검토"})
            elif r["performance_band"] == "데이터 부족":
                result.append({"project": name, "candidate_format": "확장 보류", "reason": "성과 데이터가 부족해 모든 포맷 확장은 보류합니다.", "status": "보류"})
        if not result:
            result.append({"project": "-", "candidate_format": "1차 포맷 유지", "reason": "아직 판단 가능한 작품 데이터가 없습니다.", "status": "데이터 누적"})
        return result

    def _next_production_plan(self, rows: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not rows or metrics.get("data_stage") == "데이터 축적 필요":
            focus = "1차 포맷 완성 및 데이터 수집"
        else:
            top = rows[0]
            focus = f"{top['emoticon_name']} 기반 다음 세트 기획"
        return [
            {"week": "1주차", "goal": "성과 데이터 정리", "tasks": "플러스 발신/판매 엑셀 업로드, 작품별 점수 확인, 약한 문구/강한 문구 메모"},
            {"week": "2주차", "goal": focus, "tasks": "v34 콘셉트·32문구 선기획, v33 사투리/생활 문구 후보, 시리즈 후보 2~3개 작성"},
            {"week": "3주차", "goal": "대표 시안 제작", "tasks": "v24/v25 직접 드로잉·파츠 추정, v26 감정/모션 확장, 후보 갤러리 24/32개 선별"},
            {"week": "4주차", "goal": "제출 전 검수", "tasks": "v17 채팅 미리보기, v23 일관성 검사, v36 규격/용량 검사, v30 잠금 체크리스트, v19 백업"},
        ]

    def _data_needs(self, rows: List[Dict[str, Any]], metrics: Dict[str, Any], source: Dict[str, Any]) -> List[Dict[str, Any]]:
        needs = []
        if not source.get("plus_rows"):
            needs.append({"data": "이모티콘 플러스 발신 통계", "why": "반복 사용성 판단", "how": "카카오 스튜디오에서 plus_report.xlsx 다운로드 후 v39/v40에 업로드"})
        if not source.get("sales_details") and not source.get("sales_summary"):
            needs.append({"data": "판매내역", "why": "구매 전환/국가별 판매 판단", "how": "카카오 스튜디오에서 sales_report.xlsx 다운로드 후 업로드"})
        if metrics.get("project_count", 0) < 3:
            needs.append({"data": "여러 주차 누적 데이터", "why": "일시적 변동과 실제 강점을 구분", "how": "최소 4주 이상 같은 양식으로 누적"})
        if not needs:
            needs.append({"data": "문구별 반응 메모", "why": "다음 시리즈 문구 정확도 개선", "how": "v38 phrase_feedback CSV 또는 캡처 입력"})
        return needs

    def _strength(self, sent: int, users: int, repeat_rate: float) -> str:
        if sent <= 0 and users <= 0:
            return "없음/부족"
        if sent > 0 and users > 0 and repeat_rate >= 2:
            return "반복 사용 강함"
        if users > 0:
            return "사용자 확산 있음"
        return "발신 일부 있음"

    def _sales_strength(self, count: int, amount: float) -> str:
        if count <= 0 and amount <= 0:
            return "판매 없음/부족"
        if count >= 10 or amount >= 25000:
            return "판매 반응 있음"
        return "판매 일부 있음"

    def _performance_band(self, score: float, sent: int, users: int, count: int, amount: float) -> str:
        if sent <= 0 and users <= 0 and count <= 0 and amount <= 0:
            return "데이터 부족"
        if score >= 70:
            return "강한 성과"
        if score >= 35:
            return "확장 검토"
        return "보완 필요"

    def _next_direction(self, sent: int, users: int, repeat_rate: float, count: int, amount: float, band: str) -> str:
        if band == "데이터 부족":
            return "확장 보류 · 데이터 누적"
        if band == "보완 필요":
            return "문구/제목/캐릭터성 보완"
        if sent and users and count:
            return "시리즈 2탄 우선 검토"
        if sent and users:
            return "문구형 정지 2탄 또는 움직이는 문구형 검토"
        if count or amount:
            return "대표 이미지/제목 유지 후 사용성 문구 보강"
        return "1차 포맷 유지"

    def _write_table(self, out: Path, name: str, records: List[Dict[str, Any]]) -> Dict[str, str]:
        out.mkdir(parents=True, exist_ok=True)
        csv_path = out / f"{name}.csv"
        json_path = out / f"{name}.json"
        rows = records if records else [{"note": "데이터 없음"}]
        keys = list(dict.fromkeys(k for r in rows for k in r.keys()))
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return {f"{name}_csv_path": str(csv_path), f"{name}_json_path": str(json_path)}

    def _write_html(self, report: PerformanceDashboardReport, path: Path) -> None:
        def table(records: List[Dict[str, Any]], limit: int = 80) -> str:
            if not records:
                return "<p>데이터 없음</p>"
            keys = list(dict.fromkeys(k for rec in records for k in rec.keys()))
            head = "<tr>" + "".join(f"<th>{_esc(k)}</th>" for k in keys) + "</tr>"
            body = "".join("<tr>" + "".join(f"<td>{_esc(rec.get(k, ''))}</td>" for k in keys) + "</tr>" for rec in records[:limit])
            return f"<table>{head}{body}</table>"

        metrics = report.portfolio_metrics
        html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>v40 성과 대시보드</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;line-height:1.55}}table{{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0 26px}}th,td{{border:1px solid #ddd;padding:6px;vertical-align:top}}th{{background:#f5f5f5}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.card{{background:#f8fbff;border:1px solid #dbeafe;border-radius:10px;padding:14px}}.warn{{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:14px}}</style></head><body>
<h1>v40 성과 데이터 대시보드 + 다음 제작 방향 리포트</h1>
<p><b>프로젝트:</b> {_esc(report.project_name)} · <b>생성:</b> {_esc(report.generated_at)}</p>
<div class="grid">
<div class="card"><b>작품 수</b><br>{_esc(metrics.get('project_count', 0))}</div>
<div class="card"><b>총 발신수</b><br>{_esc(metrics.get('total_sent', 0))}</div>
<div class="card"><b>총 이용자수</b><br>{_esc(metrics.get('total_users', 0))}</div>
<div class="card"><b>총 판매금액</b><br>{_esc(metrics.get('total_sales_amount', 0))}</div>
</div>
<div class="warn"><b>데이터 단계:</b> {_esc(metrics.get('data_stage'))}<br>처음부터 모든 포맷을 만들지 말고 1차 포맷 성과를 본 뒤 확장하세요.</div>
<h2>작품별 성과 대시보드</h2>{table(report.dashboard_rows)}
<h2>전략 추천</h2>{table(report.strategy_recommendations)}
<h2>시리즈 후보</h2>{table(report.series_candidates)}
<h2>포맷 확장 후보</h2>{table(report.format_expansion_candidates)}
<h2>다음 4주 제작 계획</h2>{table(report.next_production_plan)}
<h2>추가로 필요한 데이터</h2>{table(report.data_needs)}
<h2>안전 노트</h2><ul>{''.join(f'<li>{_esc(x)}</li>' for x in report.safety_notes)}</ul>
</body></html>"""
        path.write_text(html, encoding="utf-8")

    def _zip_run(self, run_dir: Path, zip_path: Path) -> None:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in run_dir.rglob("*"):
                if fp == zip_path or fp.is_dir():
                    continue
                zf.write(fp, fp.relative_to(run_dir))
