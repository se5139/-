from pathlib import Path
from PIL import Image
from modules.kakao_spec_validator import KakaoSpecValidator

base = Path('outputs/v36_check_sample')
items = base / 'items'
items.mkdir(parents=True, exist_ok=True)
# static sample: 32 valid 360 PNG, icon/share
for i in range(32):
    img = Image.new('RGBA', (360, 360), (255, 255, 255, 0))
    img.save(items / f'{i+1:02d}.png', optimize=True)
icon = base / 'icon.png'
Image.new('RGBA', (78, 78), (255, 255, 255, 0)).save(icon, optimize=True)
share = base / 'share.png'
Image.new('RGBA', (600, 166), (255, 255, 255, 0)).save(share, optimize=True)
report = KakaoSpecValidator().build_report(Path('outputs/v36_check_report'), base, 'static')
assert report['product_type'] == 'static'
assert report['counts']['item'] == 32, report['counts']
assert report['decision'] in ['제출 전 규격 상태 양호', '보완 후 제출 권장'], report['decision']
for key in ['json_path', 'csv_path', 'html_path', 'notes_path', 'zip_path']:
    assert Path(report['files'][key]).exists(), key
print('v36 kakao spec validator PASS')
