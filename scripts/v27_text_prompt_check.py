from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.text_prompt_creator import TextPromptEmoticonEngine

out = Path('outputs/v27_text_prompt_check')
engine = TextPromptEmoticonEngine()
report = engine.build_project(
    out,
    '팽이버섯 한 묶음을 얼굴로 형상화해주고 성격은 다정하고 예의 바르게 인사하며 "안녕하세요" 라고 한다',
    project_name='v27_text_prompt_check',
    format_key='animated_text',
    expression_count=16,
)
assert Path(report.preview_png_path).exists()
assert Path(report.preview_gif_path).exists()
assert Path(report.html_path).exists()
assert Path(report.json_path).exists()
assert Path(report.csv_path).exists()
assert Path(report.zip_path).exists()
assert report.spec['material'].startswith('팽이버섯')
assert report.spec['phrase'] == '안녕하세요'
print('v27_text_prompt_check PASS', report.spec['material'], report.spec['phrase'], Path(report.zip_path).name)