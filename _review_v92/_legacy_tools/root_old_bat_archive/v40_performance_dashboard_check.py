from pathlib import Path
import json

from modules.performance_dashboard import PerformanceDashboardEngine

sample_v39_report = {
    "period": {"start_date": "2026-05-29", "end_date": "2026-06-04"},
    "plus_rows": [
        {"date": "2026-05-29", "emoticon_name": "보리와 쌀", "series_name": "보리쌀", "sent_count": 1250, "user_count": 430, "repeat_rate": 2.907},
        {"date": "2026-05-30", "emoticon_name": "감자사원", "series_name": "직장인", "sent_count": 3500, "user_count": 1200, "repeat_rate": 2.917},
        {"date": "2026-05-31", "emoticon_name": "팽이버섯씨", "series_name": "버섯", "sent_count": 120, "user_count": 90, "repeat_rate": 1.333},
    ],
    "sales_summary": [
        {"market": "국내", "sales_count": 47, "sales_amount_vat": 117500},
        {"market": "일본", "sales_count": 0, "sales_amount_vat": 0},
        {"market": "글로벌", "sales_count": 0, "sales_amount_vat": 0},
    ],
    "sales_details": [
        {"sale_date": "2026-05-29", "type": "이모티콘", "emoticon_title": "감자사원", "series_name": "직장인", "market": "국내", "sales_count": 35, "currency": "KRW", "amount": 87500},
        {"sale_date": "2026-05-30", "type": "이모티콘", "emoticon_title": "보리와 쌀", "series_name": "보리쌀", "market": "국내", "sales_count": 12, "currency": "KRW", "amount": 30000},
    ],
    "performance_scores": [],
}

out = Path("outputs/v40_check")
report = PerformanceDashboardEngine().build_report(out, "v40_check_project", sample_v39_report)
d = report.to_dict()
assert d["portfolio_metrics"]["project_count"] >= 3
assert d["portfolio_metrics"]["total_sent"] == 4870
assert d["dashboard_rows"], "dashboard rows missing"
assert d["strategy_recommendations"], "strategy recommendations missing"
assert d["series_candidates"], "series candidates missing"
assert d["format_expansion_candidates"], "format expansion candidates missing"
assert d["next_production_plan"], "next production plan missing"
for key in ["html_path", "json_path", "dashboard_rows_csv_path", "strategy_recommendations_csv_path", "zip_path"]:
    path = Path(d["files"].get(key, ""))
    assert path.exists(), f"missing {key}: {path}"
print("v40_performance_dashboard_check PASS")
print(json.dumps(d["portfolio_metrics"], ensure_ascii=False))
