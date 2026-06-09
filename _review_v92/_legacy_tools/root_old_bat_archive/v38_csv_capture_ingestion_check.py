from pathlib import Path
import shutil
import tempfile
from PIL import Image, ImageDraw
from modules.data_ingestion import DataIngestionPipeline

root = Path(tempfile.mkdtemp(prefix='v38_check_'))
pipe = DataIngestionPipeline()
paths = pipe.generate_templates(root / 'out')
assert Path(paths['zip']).exists()

sample_csv = Path(paths['review_results'])
report = pipe.import_csv(sample_csv, 'review_results', root / 'out')
assert report.imported_rows >= 1
assert Path(report.files['cleaned_csv_path']).exists()
assert Path(report.files['learning_jsonl_path']).exists()
assert Path(report.files['zip_path']).exists()

img = root / 'capture.png'
im = Image.new('RGB', (640, 360), 'white')
d = ImageDraw.Draw(im)
d.text((20, 20), '보리와쌀 승인 2026-06-05 매출 10000원', fill='black')
im.save(img)
cap = pipe.import_captures([img], 'sales_notes', root / 'out', manual_text='보리와쌀 2026-06-05 승인 매출 10000원 반응 좋음')
assert cap.imported_rows == 1
assert cap.extracted_candidates
assert Path(cap.files['cleaned_csv_path']).exists()
assert Path(cap.files['zip_path']).exists()
print('v38_csv_capture_ingestion_check PASS')
