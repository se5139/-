import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.free_drawing import FreeDrawingCanvas

out = Path('outputs/v25_check')
out.mkdir(parents=True, exist_ok=True)
engine = FreeDrawingCanvas()
strokes = engine.sample_strokes('보리쌀', color='#2E2924')
text_strokes = engine.parse_strokes_from_text(
    'face: 108,125 125,80 180,55 235,80 252,125 235,170 180,195 125,170 108,125\n'
    'body: 110,230 150,195 210,195 250,230 220,280 140,280 110,230\n'
    'eye: 150,120 151,120\neye2: 210,120 211,120\nsmile: 150,150 165,165 180,172 195,165 210,150',
    color='#2E2924', width=8,
)
report = engine.build_project(strokes=text_strokes + strokes[:2], output_dir=out, project_name='v25_free_drawing_check')
assert Path(report.canvas_png_path).exists()
assert Path(report.preview_png_path).exists()
assert Path(report.auto_clean_png_path).exists()
assert Path(report.line_art_png_path).exists()
assert Path(report.layer_manifest_path).exists()
assert Path(report.csv_path).exists()
assert Path(report.html_path).exists()
assert Path(report.zip_path).exists()
assert report.stroke_count >= 5
assert report.point_count >= 20
print('v25_free_drawing_check PASS', report.stroke_count, report.point_count, Path(report.zip_path).name)
