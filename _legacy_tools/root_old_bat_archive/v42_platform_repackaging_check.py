from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

from modules.platform_repackaging import PlatformRepackagingEngine, PLATFORM_TARGETS


def make_sample_inputs(root: Path) -> Path:
    src = root / "sample_sources"
    src.mkdir(parents=True, exist_ok=True)
    for i in range(1, 5):
        im = Image.new("RGBA", (360, 360), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([55, 55, 305, 280], radius=70, fill=(255, 240, 190, 255), outline=(45, 45, 45, 255), width=5)
        d.ellipse([130, 130, 145, 145], fill=(35, 35, 35, 255))
        d.ellipse([215, 130, 230, 145], fill=(35, 35, 35, 255))
        d.arc([145, 150, 215, 205], 15, 165, fill=(35, 35, 35, 255), width=4)
        d.text((125, 300), f"TEST{i}", fill=(35, 35, 35, 255))
        im.save(src / f"sample_{i:02d}.png")
    return src


def main() -> None:
    out = Path("outputs/v42_check")
    out.mkdir(parents=True, exist_ok=True)
    src = make_sample_inputs(out)
    platforms = ["naver_ogq", "line_sticker", "band_sticker", "sns_square", "sns_story", "goods_png"]
    report = PlatformRepackagingEngine(out).run(
        input_dir=src,
        project_name="v42_platform_repackaging_check",
        title="보리와 쌀",
        selected_platforms=platforms,
        source_format="문구 결합형 멈춰있는 이모티콘",
        max_assets_per_platform=3,
    )
    assert Path(report["files"]["zip_path"]).exists(), "zip missing"
    assert len(report["platform_summaries"]) == len(platforms)
    assert len(report["records"]) == len(platforms) * 3
    for rec in report["records"]:
        p = Path(rec["output_file"])
        assert p.exists(), f"missing {p}"
        assert Image.open(p).size == PLATFORM_TARGETS[rec["platform"]].draft_size, rec
    print("v42 platform repackaging check PASS")
    print("platforms:", len(report["platform_summaries"]))
    print("records:", len(report["records"]))


if __name__ == "__main__":
    main()
