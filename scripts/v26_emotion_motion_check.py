from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.emotion_motion_variation import EmotionMotionVariationEngine

out = Path('outputs/v26_check')
engine = EmotionMotionVariationEngine()
expressions = engine.default_expression_seed(32)
report = engine.build_project(
    output_dir=out,
    project_name='v26_emotion_motion_check',
    expressions=expressions,
    character_name='보리와 쌀',
    personality='보리는 까칠하고 투덜, 쌀은 온순하고 다정',
    tone='보리는 짧게 투덜, 쌀은 부드럽게 위로',
    format_key='animated_text',
    emotion_intensity=4,
    motion_intensity=4,
    preview_count=12,
)
assert Path(report.html_path).exists(), 'html missing'
assert Path(report.json_path).exists(), 'json missing'
assert Path(report.csv_path).exists(), 'csv missing'
assert Path(report.zip_path).exists(), 'zip missing'
assert Path(report.sample_static_path).exists(), 'static preview missing'
assert Path(report.sample_gif_path).exists(), 'gif preview missing'
assert report.plan_count == 32, report.plan_count
families = {p['family'] for p in report.plans}
assert '슬픔' in families, families
assert any('따봉' in p['family'] for p in report.plans), families
print('v26_emotion_motion_check PASS', report.plan_count, report.preview_count, Path(report.zip_path).name)
