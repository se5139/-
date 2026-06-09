import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from modules.free_drawing import FreeDrawingCanvas
from modules.drawing_refine import DrawingRefineEngine

out = Path('outputs/v25_check')
out.mkdir(parents=True, exist_ok=True)
# 1) sample strokes -> free drawing image
free = FreeDrawingCanvas()
strokes = free.sample_strokes('보리쌀', color='#2E2924')
img = free.render_strokes(strokes)
source = out / 'v25_source_freehand.png'
img.save(source)
# 2) intentionally rough second sample with clear face/body/eyes/mouth
rough = Image.new('RGBA', (360, 360), (255,255,255,0))
d = ImageDraw.Draw(rough)
d.ellipse((95, 55, 265, 215), outline=(35,30,25,255), width=8)
d.ellipse((120, 190, 250, 310), outline=(35,30,25,255), width=8)
d.ellipse((140, 120, 153, 133), fill=(35,30,25,255))
d.ellipse((205, 120, 218, 133), fill=(35,30,25,255))
d.arc((150, 142, 210, 178), 0, 180, fill=(35,30,25,255), width=5)
rough_source = out / 'v25_source_rough_character.png'
rough.save(rough_source)
engine = DrawingRefineEngine()
report = engine.build_project(
    input_image_path=rough_source,
    output_dir=out / 'drawing_refine_project',
    project_name='v25_drawing_refine_check',
    starter_expression_count=32,
    variant_count=12,
)
assert Path(report.normalized_png_path).exists()
assert Path(report.parts_overlay_path).exists()
assert Path(report.parts_manifest_path).exists()
assert Path(report.expression_manifest_path).exists()
assert Path(report.expression_csv_path).exists()
assert Path(report.html_path).exists()
assert Path(report.zip_path).exists()
assert report.part_count >= 6
assert report.variant_count == 12
assert report.starter_expression_count == 32
assert any('eye' in p['part']['name'] for p in report.part_files)
assert any(v['key'] == 'sorry' for v in report.variant_files)
assert any(row['phrase'] == '확인했습니다' for row in report.starter_expressions)
print('v25_drawing_refine_check PASS', report.part_count, report.variant_count, Path(report.zip_path).name)
