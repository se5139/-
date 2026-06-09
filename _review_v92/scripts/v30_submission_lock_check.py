from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.submission_lock import SubmissionLockChecklistEngine

out = ROOT / 'outputs' / 'v30_check'
manual = {
    'origin_evidence': True,
    'ai_no_final': True,
    'copyright_report': True,
    'quality_review': True,
    'chat_preview': True,
    'count_format': True,
    'backup_done': True,
    'consistency': True,
    'rejection_review': True,
    'growth_saved': False,
    'api_trend': False,
    'expression_balance': True,
}
context = {
    'human_origin_report': {'ok': True},
    'copyright_defense_report': {'ok': True},
    'quality_review': {'ok': True},
    'chat_preview_report': {'ok': True},
    'submission_result': {'ok': True},
    'data_safety_report': {'ok': True},
    'consistency_report': {'ok': True},
    'rejection_improvement_report': {'ok': True},
    'candidate_gallery_report': {'ok': True},
}
report = SubmissionLockChecklistEngine().build_report(out, project_name='v30_check_project', manual_checks=manual, context_reports=context, notes='검사용')
assert report.passed_required == report.total_required, report
assert Path(report.html_path).exists()
assert Path(report.json_path).exists()
assert Path(report.csv_path).exists()
assert Path(report.zip_path).exists()
assert report.unlock_certificate_path and Path(report.unlock_certificate_path).exists()
print('v30 submission lock checklist PASS')
