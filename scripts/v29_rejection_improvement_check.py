from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.rejection_improvement import RejectionImprovementEngine

out = Path('outputs/check_v29')
out.mkdir(parents=True, exist_ok=True)
engine = RejectionImprovementEngine()
report = engine.build_report(
    output_dir=out,
    project_name='quick_check_rejection_improvement',
    reason_text='캐릭터성이 약하고 대화 활용성이 낮으며 문구가 작아서 잘 안 읽힙니다. 세트가 반복적이고 감정 전달도 약합니다.',
)
assert report.severity_score >= 40, report.severity_score
assert len(report.detected_categories) >= 3, report.detected_categories
assert len(report.action_plan) >= 6, len(report.action_plan)
assert len(report.revised_expressions) == 32, len(report.revised_expressions)
for fp in [report.html_path, report.json_path, report.csv_path, report.revised_csv_path, report.zip_path]:
    assert Path(fp).exists(), fp
print('v29 rejection improvement check PASS')
print(report.verdict)
print(report.checksum_sha256)
