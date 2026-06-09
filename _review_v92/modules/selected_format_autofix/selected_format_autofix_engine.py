from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont, ImageSequence


@dataclass(frozen=True)
class FormatSpec:
    key: str
    label: str
    count: int
    canvas_size: tuple[int, int]
    image_ext: str
    max_kb: int
    min_animated_webp: int = 0
    max_frames: int | None = None
    icon_required: bool = True
    icon_size: tuple[int, int] = (78, 78)
    icon_max_kb: int = 16
    share_required: bool = True
    share_size: tuple[int, int] = (600, 166)
    share_max_kb: int = 500
    note: str = ""


SELECTED_FORMAT_SPECS: dict[str, FormatSpec] = {
    "static_text": FormatSpec(
        key="static_text",
        label="문구 결합형 멈춰있는 이모티콘",
        count=32,
        canvas_size=(360, 360),
        image_ext="png",
        max_kb=150,
        note="초기 1차 포맷 추천에서 가장 자주 선택되는 안전한 문구형 정지 포맷입니다.",
    ),
    "static": FormatSpec(
        key="static",
        label="멈춰있는 이모티콘",
        count=32,
        canvas_size=(360, 360),
        image_ext="png",
        max_kb=150,
        note="문구보다 표정/포즈 전달력이 강한 캐릭터에 적합합니다.",
    ),
    "animated_text": FormatSpec(
        key="animated_text",
        label="움직이는 문구 결합형 이모티콘",
        count=24,
        canvas_size=(360, 360),
        image_ext="webp",
        max_kb=650,
        min_animated_webp=3,
        max_frames=24,
        note="1차 성과 확인 후 확장 후보로 쓰는 경우가 많습니다. WebP 3개 이상을 우선 확인합니다.",
    ),
    "animated": FormatSpec(
        key="animated",
        label="움직이는 이모티콘",
        count=24,
        canvas_size=(360, 360),
        image_ext="webp",
        max_kb=650,
        min_animated_webp=3,
        max_frames=24,
        note="캐릭터 동작 자체가 강한 경우에 적합합니다.",
    ),
    "mini_static": FormatSpec(
        key="mini_static",
        label="멈춰있는 미니 이모티콘",
        count=42,
        canvas_size=(180, 180),
        image_ext="png",
        max_kb=100,
        icon_required=False,
        note="1차 데이터가 쌓인 뒤 단순 조합/미니 확장 후보로 검토합니다.",
    ),
    "mini_animated": FormatSpec(
        key="mini_animated",
        label="움직이는 미니 이모티콘",
        count=35,
        canvas_size=(180, 180),
        image_ext="webp",
        max_kb=500,
        min_animated_webp=3,
        max_frames=18,
        icon_required=False,
        note="미니 이모티콘에서 움직임이 꼭 필요한 경우에만 확장 후보로 둡니다.",
    ),
    "big_static": FormatSpec(
        key="big_static",
        label="멈춰있는 큰 이모티콘",
        count=16,
        canvas_size=(540, 540),
        image_ext="png",
        max_kb=1024,
        note="강한 표정/리액션 데이터가 쌓인 뒤 확장 후보로 검토합니다.",
    ),
}


@dataclass
class FixRecord:
    source_file: str
    fixed_file: str
    role: str
    before_size: str
    after_size: str
    before_kb: float
    after_kb: float
    status: str
    notes: str


class SelectedFormatAutoFixEngine:
    """Selected-format-only converter.

    v41 intentionally does NOT produce every Kakao format at once. It fixes only the
    single first-format selected by the v37/v40 strategy pipeline and stores other
    formats as future expansion candidates.
    """

    def __init__(self, output_root: Path | str):
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _safe_name(name: str) -> str:
        keep = []
        for ch in name.strip():
            if ch.isalnum() or ch in ("-", "_", "."):
                keep.append(ch)
            elif ch.isspace():
                keep.append("_")
        return "".join(keep)[:80] or "project"

    def _collect_sources(self, input_dir: Path) -> list[Path]:
        if not input_dir.exists():
            return []
        allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        return sorted([p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in allowed])

    def _make_placeholder(self, path: Path, index: int, size: tuple[int, int], label: str) -> None:
        w, h = size
        im = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        body = (255, 244, 210, 255)
        line = (56, 48, 42, 255)
        cx, cy = w // 2, h // 2
        r = max(28, min(w, h) // 3)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=body, outline=line, width=max(2, min(w, h)//90))
        eye_r = max(2, min(w, h)//45)
        d.ellipse([cx - r//3 - eye_r, cy - r//6 - eye_r, cx - r//3 + eye_r, cy - r//6 + eye_r], fill=line)
        d.ellipse([cx + r//3 - eye_r, cy - r//6 - eye_r, cx + r//3 + eye_r, cy - r//6 + eye_r], fill=line)
        d.arc([cx-r//3, cy, cx+r//3, cy+r//3], 10, 170, fill=line, width=max(2, min(w, h)//100))
        text = f"{index:02d}"
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", max(12, min(w, h)//9))
        except Exception:
            font = ImageFont.load_default()
        bbox = d.textbbox((0,0), text, font=font)
        d.rounded_rectangle([8, 8, 8 + (bbox[2]-bbox[0]) + 16, 8 + (bbox[3]-bbox[1]) + 12], radius=8, fill=(255,255,255,210), outline=line)
        d.text((16, 14), text, fill=line, font=font)
        path.parent.mkdir(parents=True, exist_ok=True)
        im.save(path, optimize=True)

    def _flatten_first_frame(self, src: Path) -> Image.Image:
        im = Image.open(src)
        try:
            if getattr(im, "is_animated", False):
                im.seek(0)
            return im.convert("RGBA")
        finally:
            try:
                im.close()
            except Exception:
                pass

    def _fit_to_canvas(self, src: Path, size: tuple[int, int], margin: int = 10) -> Image.Image:
        base = self._flatten_first_frame(src)
        w, h = size
        max_w, max_h = max(1, w - margin * 2), max(1, h - margin * 2)
        base.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        out = Image.new("RGBA", size, (0, 0, 0, 0))
        out.alpha_composite(base, ((w - base.width) // 2, (h - base.height) // 2))
        return out

    def _save_png_under_limit(self, im: Image.Image, out_path: Path, max_kb: int) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        im.save(out_path, optimize=True)
        if out_path.stat().st_size <= max_kb * 1024:
            return
        # Reduce color count while preserving transparency as much as possible.
        colors = [256, 192, 128, 96, 64, 48, 32]
        for c in colors:
            test = im.convert("RGBA").quantize(colors=c, method=Image.Quantize.MEDIANCUT).convert("RGBA")
            test.save(out_path, optimize=True)
            if out_path.stat().st_size <= max_kb * 1024:
                return
        # Last-resort: leave optimized file and report the issue.

    def _save_webp_under_limit(self, srcs: list[Path], out_path: Path, size: tuple[int, int], max_kb: int, max_frames: int | None) -> tuple[int, str]:
        frames: list[Image.Image] = []
        notes = []
        for src in srcs:
            try:
                im = Image.open(src)
                if getattr(im, "is_animated", False):
                    for fr in ImageSequence.Iterator(im):
                        tmp = fr.convert("RGBA")
                        tmp.thumbnail((size[0] - 20, size[1] - 20), Image.Resampling.LANCZOS)
                        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
                        canvas.alpha_composite(tmp, ((size[0]-tmp.width)//2, (size[1]-tmp.height)//2))
                        frames.append(canvas)
                else:
                    frames.append(self._fit_to_canvas(src, size))
            except Exception:
                continue
        if not frames:
            # generate simple two-frame placeholder motion
            temp = out_path.with_suffix(".placeholder.png")
            self._make_placeholder(temp, 1, size, "motion")
            base = Image.open(temp).convert("RGBA")
            shifted = Image.new("RGBA", size, (0,0,0,0))
            shifted.alpha_composite(base, (0, -4))
            frames = [base, shifted, base]
            try:
                temp.unlink()
            except Exception:
                pass
            notes.append("소스 부족으로 기본 모션 플레이스홀더 생성")
        if max_frames and len(frames) > max_frames:
            step = len(frames) / max_frames
            frames = [frames[int(i * step)] for i in range(max_frames)]
            notes.append(f"프레임 수를 {max_frames}개 이하로 조정")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        for quality in [90, 82, 74, 66, 58, 50, 42, 35]:
            frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=90, loop=0, format="WEBP", quality=quality, method=6)
            if out_path.stat().st_size <= max_kb * 1024:
                return len(frames), "; ".join(notes) or f"WebP quality {quality} 저장"
        return len(frames), "; ".join(notes + ["용량 기준 초과 가능: 수동 확인 필요"])

    def _make_icon_and_share(self, primary: Path, fixed_dir: Path, spec: FormatSpec, title: str) -> list[FixRecord]:
        records: list[FixRecord] = []
        primary_kb = primary.stat().st_size / 1024 if primary.exists() else 0
        if spec.icon_required:
            icon = self._fit_to_canvas(primary, spec.icon_size, margin=4)
            icon_path = fixed_dir / "icon_78x78.png"
            self._save_png_under_limit(icon, icon_path, spec.icon_max_kb)
            records.append(FixRecord(primary.name, icon_path.name, "아이콘", "source", f"{spec.icon_size[0]}x{spec.icon_size[1]}", primary_kb, icon_path.stat().st_size/1024, "PASS" if icon_path.stat().st_size <= spec.icon_max_kb*1024 else "WARN", "78x78 아이콘 자동 생성"))
        if spec.share_required:
            w, h = spec.share_size
            share = Image.new("RGBA", spec.share_size, (255, 246, 222, 255))
            d = ImageDraw.Draw(share)
            try:
                font_title = ImageFont.truetype("DejaVuSans.ttf", 34)
                font_small = ImageFont.truetype("DejaVuSans.ttf", 18)
            except Exception:
                font_title = ImageFont.load_default()
                font_small = ImageFont.load_default()
            char = self._fit_to_canvas(primary, (140, 140), margin=4)
            share.alpha_composite(char, (25, 13))
            clean_title = title[:18]
            d.text((190, 48), clean_title, fill=(44, 38, 32, 255), font=font_title)
            d.text((192, 94), spec.label[:28], fill=(96, 82, 68, 255), font=font_small)
            share_path = fixed_dir / "share_600x166.png"
            self._save_png_under_limit(share, share_path, spec.share_max_kb)
            records.append(FixRecord(primary.name, share_path.name, "공유 이미지", "source", "600x166", primary_kb, share_path.stat().st_size/1024, "PASS" if share_path.stat().st_size <= spec.share_max_kb*1024 else "WARN", "600x166 공유 이미지 자동 생성"))
        return records

    def run(
        self,
        input_dir: Path | str,
        selected_format: str,
        project_name: str = "selected_format_project",
        title: str = "이모티콘 프로젝트",
        use_placeholders_when_empty: bool = True,
    ) -> dict[str, Any]:
        spec = SELECTED_FORMAT_SPECS[selected_format]
        input_dir = Path(input_dir)
        safe_project = self._safe_name(project_name)
        run_dir = self.output_root / safe_project
        original_dir = run_dir / "original"
        fixed_dir = run_dir / "fixed_selected_format_only"
        report_dir = run_dir / "report"
        for d in [original_dir, fixed_dir, report_dir]:
            d.mkdir(parents=True, exist_ok=True)

        sources = self._collect_sources(input_dir)
        if sources:
            for src in sources:
                dst = original_dir / src.name
                if src.resolve() != dst.resolve():
                    shutil.copy2(src, dst)
            sources = self._collect_sources(original_dir)
        elif use_placeholders_when_empty:
            for i in range(1, spec.count + 1):
                p = original_dir / f"placeholder_{i:02d}.png"
                self._make_placeholder(p, i, spec.canvas_size, spec.key)
            sources = self._collect_sources(original_dir)

        records: list[FixRecord] = []
        created_main: list[Path] = []

        if spec.image_ext == "png":
            for i in range(spec.count):
                src = sources[i % len(sources)] if sources else None
                out_path = fixed_dir / f"{i+1:02d}.png"
                if src is not None:
                    before_size = f"{Image.open(src).size[0]}x{Image.open(src).size[1]}"
                    before_kb = src.stat().st_size / 1024
                    im = self._fit_to_canvas(src, spec.canvas_size)
                else:
                    before_size = "none"
                    before_kb = 0
                    self._make_placeholder(out_path, i+1, spec.canvas_size, spec.key)
                    im = Image.open(out_path).convert("RGBA")
                self._save_png_under_limit(im, out_path, spec.max_kb)
                after_kb = out_path.stat().st_size / 1024
                status = "PASS" if after_kb <= spec.max_kb else "WARN"
                records.append(FixRecord(src.name if src else "generated", out_path.name, "본문 이미지", before_size, f"{spec.canvas_size[0]}x{spec.canvas_size[1]}", round(before_kb, 2), round(after_kb, 2), status, "선택된 1차 포맷 기준으로만 PNG 맞춤/압축"))
                created_main.append(out_path)
        else:
            # Animated formats: first min_animated_webp items as WebP, rest as PNG still previews if desired.
            motion_count = max(spec.min_animated_webp, min(spec.count, spec.min_animated_webp or spec.count))
            for i in range(spec.count):
                src = sources[i % len(sources)] if sources else None
                if i < motion_count:
                    out_path = fixed_dir / f"{i+1:02d}.webp"
                    frame_count, note = self._save_webp_under_limit([src] if src else [], out_path, spec.canvas_size, spec.max_kb, spec.max_frames)
                    before_size = "animated/source" if src else "generated"
                    before_kb = src.stat().st_size / 1024 if src else 0
                    after_kb = out_path.stat().st_size / 1024
                    status = "PASS" if after_kb <= spec.max_kb and (not spec.max_frames or frame_count <= spec.max_frames) else "WARN"
                    records.append(FixRecord(src.name if src else "generated", out_path.name, "움직이는 WebP", before_size, f"{spec.canvas_size[0]}x{spec.canvas_size[1]} / {frame_count} frames", round(before_kb,2), round(after_kb,2), status, note))
                    created_main.append(out_path)
                else:
                    out_path = fixed_dir / f"{i+1:02d}.png"
                    if src:
                        im = self._fit_to_canvas(src, spec.canvas_size)
                        before_size = f"{Image.open(src).size[0]}x{Image.open(src).size[1]}"
                        before_kb = src.stat().st_size / 1024
                    else:
                        before_size = "generated"
                        before_kb = 0
                        self._make_placeholder(out_path, i+1, spec.canvas_size, spec.key)
                        im = Image.open(out_path).convert("RGBA")
                    self._save_png_under_limit(im, out_path, min(spec.max_kb, 150))
                    records.append(FixRecord(src.name if src else "generated", out_path.name, "정지 PNG 보조", before_size, f"{spec.canvas_size[0]}x{spec.canvas_size[1]}", round(before_kb,2), round(out_path.stat().st_size/1024,2), "PASS", "움직이는 포맷의 PNG 보조 이미지 자동 생성"))
                    created_main.append(out_path)

        if created_main:
            records.extend(self._make_icon_and_share(created_main[0], fixed_dir, spec, title))

        # manifest and reports
        checks_csv = report_dir / "selected_format_autofix_checks.csv"
        with checks_csv.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(records[0]).keys()) if records else ["status"])
            writer.writeheader()
            for r in records:
                writer.writerow(asdict(r))

        manifest = {
            "version": "v41",
            "project_name": project_name,
            "selected_format": spec.key,
            "selected_format_label": spec.label,
            "principle": "v37/v40에서 추천된 1차 포맷 1개만 자동 변환/압축합니다. 나머지 포맷은 확장 후보로만 보관합니다.",
            "spec": asdict(spec),
            "directories": {"original": str(original_dir), "fixed": str(fixed_dir), "report": str(report_dir)},
            "file_count_fixed_main": len(created_main),
            "records": [asdict(r) for r in records],
            "fixed_files_sha256": {p.name: self.sha256_file(p) for p in sorted(fixed_dir.glob("*")) if p.is_file()},
            "manual_notes": [
                "카카오 공식 기준은 변경될 수 있으므로 최종 제출 직전 스튜디오 최신 가이드를 재확인하세요.",
                "자동 압축 파일은 원본을 덮어쓰지 않고 fixed_selected_format_only 폴더에 따로 저장됩니다.",
                "움직이는 포맷은 반복 재생 자연스러움과 마지막 프레임 대표성을 사람이 직접 확인해야 합니다.",
            ],
        }
        json_path = report_dir / "selected_format_autofix_report.json"
        json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        txt_path = report_dir / "selected_format_autofix_notes.txt"
        txt_path.write_text("\n".join(manifest["manual_notes"]), encoding="utf-8")

        html_path = report_dir / "selected_format_autofix_report.html"
        rows = "".join(
            f"<tr><td>{r.role}</td><td>{r.source_file}</td><td>{r.fixed_file}</td><td>{r.before_size}</td><td>{r.after_size}</td><td>{r.before_kb:.1f}KB</td><td>{r.after_kb:.1f}KB</td><td>{r.status}</td><td>{r.notes}</td></tr>"
            for r in records
        )
        html = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v41 선택 포맷 자동수정</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #ddd;padding:8px}}th{{background:#f6f2ea}}.pass{{color:#176b35;font-weight:bold}}.warn{{color:#a05a00;font-weight:bold}}</style></head><body>
<h1>v41 선택된 1차 포맷 자동 변환/압축 리포트</h1>
<p><b>프로젝트:</b> {project_name}</p><p><b>선택 포맷:</b> {spec.label}</p>
<p>이 리포트는 모든 포맷을 한 번에 만들지 않고, 전략 엔진에서 선택된 1개 포맷만 제출 규격에 맞춰 자동 보정한 결과입니다.</p>
<h2>검사/수정 결과</h2><table><thead><tr><th>역할</th><th>원본</th><th>수정본</th><th>수정 전</th><th>수정 후</th><th>수정 전 용량</th><th>수정 후 용량</th><th>상태</th><th>메모</th></tr></thead><tbody>{rows}</tbody></table>
<h2>주의사항</h2><ul>{''.join(f'<li>{n}</li>' for n in manifest['manual_notes'])}</ul>
</body></html>"""
        html_path.write_text(html, encoding="utf-8")

        zip_path = run_dir / f"{safe_project}_v41_selected_format_autofix_pack.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for folder in [original_dir, fixed_dir, report_dir]:
                for p in folder.rglob("*"):
                    if p.is_file():
                        zf.write(p, p.relative_to(run_dir))
        return {
            "project_name": project_name,
            "selected_format": spec.key,
            "selected_format_label": spec.label,
            "run_dir": str(run_dir),
            "original_dir": str(original_dir),
            "fixed_dir": str(fixed_dir),
            "html_path": str(html_path),
            "json_path": str(json_path),
            "csv_path": str(checks_csv),
            "notes_path": str(txt_path),
            "zip_path": str(zip_path),
            "records": [asdict(r) for r in records],
            "pass_count": sum(1 for r in records if r.status == "PASS"),
            "warn_count": sum(1 for r in records if r.status != "PASS"),
        }
