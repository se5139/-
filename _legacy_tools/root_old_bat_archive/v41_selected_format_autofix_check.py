from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

from modules.selected_format_autofix import SelectedFormatAutoFixEngine, SELECTED_FORMAT_SPECS


def make_sample_inputs(root: Path) -> Path:
    src = root / 'sample_sources'
    src.mkdir(parents=True, exist_ok=True)
    for i, size in enumerate([(420, 360), (360, 390), (512, 512), (300, 360)], start=1):
        im = Image.new('RGBA', size, (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([30, 30, size[0]-30, size[1]-30], fill=(255, 235, 190, 255), outline=(45, 40, 35, 255), width=5)
        d.text((50, 50), f'{i}', fill=(45, 40, 35, 255))
        im.save(src / f'source_{i:02d}.png')
    return src


def main() -> None:
    out = Path('outputs/v41_check')
    out.mkdir(parents=True, exist_ok=True)
    src = make_sample_inputs(out)
    engine = SelectedFormatAutoFixEngine(out)
    report_static = engine.run(src, 'static_text', project_name='v41_static_text_check', title='보리와 쌀')
    assert Path(report_static['zip_path']).exists(), 'static zip missing'
    assert report_static['selected_format'] == 'static_text'
    fixed_dir = Path(report_static['fixed_dir'])
    main_pngs = sorted(p for p in fixed_dir.glob('*.png') if p.name[:2].isdigit())
    assert len(main_pngs) == SELECTED_FORMAT_SPECS['static_text'].count, len(main_pngs)
    assert Path(fixed_dir / 'icon_78x78.png').exists(), 'icon missing'
    assert Path(fixed_dir / 'share_600x166.png').exists(), 'share missing'
    for p in main_pngs[:5]:
        assert Image.open(p).size == (360, 360), f'bad size {p}'

    report_animated = engine.run(src, 'animated_text', project_name='v41_animated_text_check', title='보리와 쌀')
    assert Path(report_animated['zip_path']).exists(), 'animated zip missing'
    webps = sorted(Path(report_animated['fixed_dir']).glob('*.webp'))
    assert len(webps) >= SELECTED_FORMAT_SPECS['animated_text'].min_animated_webp, len(webps)
    for p in webps[:3]:
        assert Image.open(p).size == (360, 360), f'bad webp size {p}'
    print('v41 selected format autofix check PASS')
    print('static records:', len(report_static['records']))
    print('animated records:', len(report_animated['records']))


if __name__ == '__main__':
    main()
