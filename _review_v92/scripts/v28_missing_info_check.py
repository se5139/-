
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.text_prompt_creator import MissingInfoAssistant

engine = MissingInfoAssistant()
prompt = '팽이버섯 한 묶음을 얼굴로 형상화해주고 예의 바르게 인사하며 "안녕하세요"라고 한다'
analysis = engine.analyze_prompt(prompt)
assert 'legs' in analysis.missing_fields
assert 'arms' in analysis.missing_fields
selected = {f: opts[0]['value'] for f, opts in analysis.candidates.items() if opts}
report = engine.build_project(Path('outputs/v28_missing_info_check'), prompt, project_name='v28_missing_info_check', selected_values=selected, mode='candidate', expression_count=12)
assert Path(report.zip_path).exists()
assert Path(report.html_path).exists()
assert report.preview_report is not None
report_keep = engine.build_project(Path('outputs/v28_missing_info_check_keep'), prompt, project_name='v28_missing_info_keep_check', selected_values={}, mode='keep_as_is', expression_count=12)
assert report_keep.final_prompt == prompt
print('v28_missing_info_check PASS', len(analysis.missing_fields), Path(report.zip_path).name, Path(report_keep.zip_path).name)
