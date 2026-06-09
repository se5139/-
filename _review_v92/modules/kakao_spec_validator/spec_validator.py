from __future__ import annotations

import csv
import json
import os
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image

KB = 1024
MB = 1024 * 1024

KAKAO_SPEC_TABLE: Dict[str, Dict[str, Any]] = {
    "static": {
        "label": "멈춰있는 이모티콘",
        "items": {"count": 32, "formats": ["PNG"], "sizes": [(360, 360)], "max_bytes": 150 * KB, "min_webp": 0},
        "icon": {"count": 1, "formats": ["PNG"], "sizes": [(78, 78)], "max_bytes": 16 * KB},
        "share": {"count": 1, "formats": ["PNG"], "sizes": [(600, 166)], "max_bytes": 500 * KB, "submission_required": False},
        "common": ["72dpi 권장", "RGB 권장", "이모티콘/아이콘 배경 투명", "다크모드 대비용 흰색 아웃라인 권장"],
    },
    "animated": {
        "label": "움직이는 이모티콘",
        "items": {"count": 24, "formats": ["WEBP", "PNG"], "sizes": [(360, 360)], "max_bytes": 650 * KB, "min_webp": 3, "max_frames": 24, "loop_count": 4},
        "icon": {"count": 1, "formats": ["PNG"], "sizes": [(78, 78)], "max_bytes": 16 * KB},
        "share": {"count": 1, "formats": ["PNG"], "sizes": [(600, 166)], "max_bytes": 500 * KB, "submission_required": False},
        "sound": {"count": 24, "formats": ["MP3"], "max_seconds": 5, "max_bytes": 200 * KB, "max_bitrate_kbps": 128, "submission_required": False, "min_submit_samples": 3},
        "common": ["움직이는 WebP 3개 이상 필수", "나머지는 PNG 제출 가능", "WebP 제작 시 Kakao WebP Animator 사용 권장", "마지막 프레임은 대표 미리보기로 쓰이므로 중요", "텍스트는 다크모드에서도 보이도록 흰색 아웃라인 권장"],
    },
    "big": {
        "label": "큰 이모티콘",
        "items": {"count": 16, "formats": ["WEBP", "PNG"], "sizes": [(540, 540), (300, 540), (540, 300)], "max_bytes": 1 * MB, "min_webp": 3, "max_frames": 24, "loop_count": 4},
        "icon": {"count": 1, "formats": ["PNG"], "sizes": [(78, 78)], "max_bytes": 16 * KB},
        "share": {"count": 1, "formats": ["PNG"], "sizes": [(600, 166)], "max_bytes": 500 * KB, "submission_required": False},
        "sound": {"count": 16, "formats": ["MP3"], "max_seconds": 5, "max_bytes": 200 * KB, "max_bitrate_kbps": 128, "submission_required": False, "min_submit_samples": 3},
        "common": ["정사각 540x540, 세로 300x540, 가로 540x300 중 선택", "움직이는 WebP 3개 이상 필수 기준으로 검사", "사운드형 선택 시 MP3 5초 이하/200KB 이하"],
    },
    "mini_static": {
        "label": "멈춰있는 미니 이모티콘",
        "items": {"count": 42, "formats": ["PNG"], "sizes": [(180, 180)], "max_bytes": 100 * KB, "min_webp": 0},
        "share": {"count": 1, "formats": ["PNG"], "sizes": [(600, 166)], "max_bytes": 500 * KB, "submission_required": False},
        "common": ["42개 PNG", "180x180", "배경 투명", "채팅방/입력창 배경에서 가독성 확인", "상품 매력을 보여주는 순서 배치 권장"],
    },
    "mini_animated": {
        "label": "움직이는 미니 이모티콘",
        "items": {"count": 35, "formats": ["WEBP", "PNG"], "sizes": [(180, 180)], "max_bytes": 500 * KB, "min_webp": 3, "max_frames": 18, "loop_count": 4},
        "share": {"count": 1, "formats": ["PNG"], "sizes": [(600, 166)], "max_bytes": 500 * KB, "submission_required": False},
        "common": ["35개 이미지", "움직이는 WebP 3개 이상 필수", "나머지는 PNG 제출 가능", "180x180", "미니 이모티콘은 순서/조합/연결성 배치가 중요"],
    },
}

IMAGE_EXTS = {".png", ".webp", ".gif", ".jpg", ".jpeg"}
AUDIO_EXTS = {".mp3"}

@dataclass
class FileCheck:
    role: str
    file: str
    ext: str
    width: Optional[int] = None
    height: Optional[int] = None
    bytes: int = 0
    kb: float = 0.0
    frames: Optional[int] = None
    has_alpha: Optional[bool] = None
    mode: Optional[str] = None
    expected: str = ""
    status: str = "PASS"
    warnings: str = ""


def _is_transparent(img: Image.Image) -> bool:
    if img.mode in ("RGBA", "LA"):
        alpha = img.getchannel("A")
        return alpha.getextrema()[0] < 255
    if img.mode == "P" and "transparency" in img.info:
        return True
    return False


def _safe_image_info(path: Path) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[bool], Optional[str], Optional[str]]:
    try:
        with Image.open(path) as im:
            width, height = im.size
            frames = getattr(im, "n_frames", 1)
            has_alpha = _is_transparent(im)
            return width, height, frames, has_alpha, im.mode, None
    except Exception as exc:
        return None, None, None, None, None, str(exc)


def _role_from_path(path: Path) -> str:
    name = path.name.lower()
    parent = " ".join([p.lower() for p in path.parts[-4:]])
    txt = parent + " " + name
    if path.suffix.lower() in AUDIO_EXTS:
        return "sound"
    if any(k in txt for k in ["icon", "아이콘", "tab"]):
        return "icon"
    if any(k in txt for k in ["share", "gift", "banner", "공유", "썸네일", "thumbnail"]):
        return "share"
    return "item"


def _format_name(path: Path) -> str:
    return path.suffix.replace(".", "").upper()


class KakaoSpecValidator:
    """Validate local Kakao emoticon package candidates against captured/current guide rules.

    This is an internal pre-flight checker. It never guarantees approval; it only flags likely
    size/count/format/visibility risks before final submission.
    """

    def scan_source(self, source_dir: Path) -> Dict[str, List[Path]]:
        source_dir = Path(source_dir)
        files = {"item": [], "icon": [], "share": [], "sound": [], "other": []}
        if not source_dir.exists():
            return files
        for p in sorted(source_dir.rglob("*")):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext in IMAGE_EXTS or ext in AUDIO_EXTS:
                role = _role_from_path(p)
                files.setdefault(role, []).append(p)
            else:
                files["other"].append(p)
        return files

    def _check_image(self, path: Path, role: str, rule: Dict[str, Any]) -> FileCheck:
        width, height, frames, has_alpha, mode, err = _safe_image_info(path)
        fc = FileCheck(role=role, file=str(path), ext=_format_name(path), bytes=path.stat().st_size, kb=round(path.stat().st_size / KB, 1))
        fc.width = width
        fc.height = height
        fc.frames = frames
        fc.has_alpha = has_alpha
        fc.mode = mode
        warnings: List[str] = []
        if err:
            warnings.append(f"이미지 열기 실패: {err}")
        if fc.ext not in rule.get("formats", []):
            warnings.append(f"파일 형식 불일치: {fc.ext}, 허용={rule.get('formats')}")
        if width is not None and height is not None and (width, height) not in rule.get("sizes", []):
            warnings.append(f"이미지 크기 불일치: {width}x{height}, 허용={rule.get('sizes')}")
        if path.stat().st_size > rule.get("max_bytes", 10**12):
            warnings.append(f"용량 초과: {round(path.stat().st_size/KB,1)}KB > {round(rule.get('max_bytes')/KB,1)}KB")
        if role in {"item", "icon"} and fc.ext in {"PNG", "WEBP"} and has_alpha is False:
            warnings.append("투명 배경/알파 없음: 제출 전 배경 투명 여부 확인 필요")
        max_frames = rule.get("max_frames")
        if max_frames and fc.ext in {"WEBP", "GIF"} and frames and frames > max_frames:
            warnings.append(f"프레임 수 초과: {frames} > {max_frames}")
        fc.expected = self._format_expected(rule)
        if warnings:
            fc.status = "WARN"
            fc.warnings = " / ".join(warnings)
        return fc

    def _check_sound(self, path: Path, rule: Dict[str, Any]) -> FileCheck:
        fc = FileCheck(role="sound", file=str(path), ext=_format_name(path), bytes=path.stat().st_size, kb=round(path.stat().st_size / KB, 1))
        warnings = []
        if fc.ext not in rule.get("formats", []):
            warnings.append(f"파일 형식 불일치: {fc.ext}")
        if path.stat().st_size > rule.get("max_bytes", 10**12):
            warnings.append(f"용량 초과: {round(path.stat().st_size/KB,1)}KB > {round(rule.get('max_bytes')/KB,1)}KB")
        # Duration/bitrate are intentionally left for ffprobe-based optional future checks.
        warnings.append("재생시간 5초 이하/128k 이하 여부는 ffprobe 또는 원본 편집툴에서 추가 확인 권장")
        fc.expected = f"MP3 / 5초 이하 / {round(rule.get('max_bytes',0)/KB)}KB 이하 / 128k 이하"
        if warnings:
            fc.status = "WARN"
            fc.warnings = " / ".join(warnings)
        return fc

    def _format_expected(self, rule: Dict[str, Any]) -> str:
        sizes = ", ".join([f"{w}x{h}" for w, h in rule.get("sizes", [])])
        fmts = "/".join(rule.get("formats", []))
        maxb = rule.get("max_bytes")
        if maxb:
            unit = f"{round(maxb/KB)}KB" if maxb < MB else f"{round(maxb/MB,1)}MB"
        else:
            unit = ""
        frame = f", {rule.get('max_frames')}프레임 이하" if rule.get("max_frames") else ""
        return f"{fmts} / {sizes} / {unit}{frame}"

    def validate(self, source_dir: Path, product_type: str) -> Dict[str, Any]:
        if product_type not in KAKAO_SPEC_TABLE:
            raise ValueError(f"Unknown product_type: {product_type}")
        spec = KAKAO_SPEC_TABLE[product_type]
        grouped = self.scan_source(Path(source_dir))
        checks: List[FileCheck] = []
        item_rule = spec["items"]
        for p in grouped.get("item", []):
            checks.append(self._check_image(p, "item", item_rule))
        if "icon" in spec:
            for p in grouped.get("icon", []):
                checks.append(self._check_image(p, "icon", spec["icon"]))
        if "share" in spec:
            for p in grouped.get("share", []):
                checks.append(self._check_image(p, "share", spec["share"]))
        if "sound" in spec:
            for p in grouped.get("sound", []):
                checks.append(self._check_sound(p, spec["sound"]))

        counts = {
            "item": len(grouped.get("item", [])),
            "icon": len(grouped.get("icon", [])),
            "share": len(grouped.get("share", [])),
            "sound": len(grouped.get("sound", [])),
            "webp_items": sum(1 for p in grouped.get("item", []) if p.suffix.lower() == ".webp"),
            "png_items": sum(1 for p in grouped.get("item", []) if p.suffix.lower() == ".png"),
        }
        failures: List[str] = []
        warnings: List[str] = []
        expected_items = item_rule.get("count")
        if counts["item"] != expected_items:
            failures.append(f"이모티콘 이미지 수량 불일치: {counts['item']}개 / 필요 {expected_items}개")
        min_webp = item_rule.get("min_webp", 0)
        if min_webp and counts["webp_items"] < min_webp:
            failures.append(f"움직이는 WebP 최소 수량 부족: {counts['webp_items']}개 / 최소 {min_webp}개")
        if "icon" in spec and counts["icon"] < spec["icon"].get("count", 0):
            warnings.append(f"아이콘 이미지 부족: {counts['icon']}개 / 권장 {spec['icon'].get('count')}개")
        if "share" in spec and counts["share"] < spec["share"].get("count", 0):
            warnings.append(f"공유 이미지 부족: {counts['share']}개 / 상품 구성용 권장 {spec['share'].get('count')}개")
        if "sound" in spec and counts["sound"]:
            if counts["sound"] not in {spec["sound"].get("count"), spec["sound"].get("min_submit_samples", 3)}:
                warnings.append("사운드 파일 수량은 선택한 사운드형 제안 조건에 맞춰 다시 확인 필요")
        for c in checks:
            if c.status != "PASS":
                warnings.append(f"{Path(c.file).name}: {c.warnings}")
        manual_notes = self.manual_notes(product_type)
        score = 100
        score -= min(50, len(failures) * 15)
        score -= min(35, len(warnings) * 3)
        if score >= 90 and not failures:
            decision = "제출 전 규격 상태 양호"
        elif score >= 70 and not failures:
            decision = "보완 후 제출 권장"
        else:
            decision = "제출 전 수정 필요"
        return {
            "product_type": product_type,
            "product_label": spec["label"],
            "source_dir": str(source_dir),
            "counts": counts,
            "score": max(score, 0),
            "decision": decision,
            "failures": failures,
            "warnings": warnings,
            "manual_notes": manual_notes,
            "spec": spec,
            "checks": [asdict(c) for c in checks],
        }

    def manual_notes(self, product_type: str) -> List[str]:
        notes = [
            "웹/모바일 환경 기준 72dpi, RGB 색상 모드로 제작하세요.",
            "텍스트는 다크모드 배경에서도 보이도록 흰색 아웃라인/대비를 확인하세요.",
            "아이콘/이모티콘 배경은 투명으로 제작하세요.",
            "공식 가이드는 바뀔 수 있으므로 최종 제출 직전 카카오 이모티콘 스튜디오 최신 안내를 재확인하세요.",
        ]
        if product_type in {"animated", "big", "mini_animated"}:
            notes += [
                "WebP는 카카오 WebP Animator 기준으로 변환하고, 프레임 수와 반복 횟수를 확인하세요.",
                "재생이 끝나는 마지막 프레임은 미리보기/키보드 대표컷으로 쓰일 수 있으므로 가장 대표적인 장면으로 구성하세요.",
                "모든 프레임은 같은 크기와 해상도로 맞추고 빈 프레임이 없도록 확인하세요.",
            ]
        if product_type in {"mini_static", "mini_animated"}:
            notes += [
                "미니 이모티콘은 상품 매력을 잘 보여주는 이미지를 상단에 배치하세요.",
                "같은 얼굴/사물 종류는 묶고, 이어서 배치했을 때 의미가 생기는 이미지는 연속 배치하세요.",
                "채팅방과 입력창 등 다양한 배경에서 가독성을 확인하세요.",
            ]
        if product_type in {"animated", "big"}:
            notes.append("사운드형을 선택할 때만 MP3 샘플/전체 파일을 제작하고, 사운드 아이콘 39x39 자동 표시가 주요 요소를 가리지 않게 디자인하세요.")
        return notes

    def build_report(self, output_dir: Path, source_dir: Path, product_type: str) -> Dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        data = self.validate(source_dir, product_type)
        stem = f"kakao_spec_{product_type}"
        json_path = output_dir / f"{stem}.json"
        csv_path = output_dir / f"{stem}_file_checks.csv"
        html_path = output_dir / f"{stem}.html"
        notes_path = output_dir / f"{stem}_manual_notes.txt"
        zip_path = output_dir / f"{stem}.zip"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            fieldnames = ["role", "file", "ext", "width", "height", "bytes", "kb", "frames", "has_alpha", "mode", "expected", "status", "warnings"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data["checks"]:
                writer.writerow({k: row.get(k) for k in fieldnames})
        notes_path.write_text("\n".join(data["manual_notes"]), encoding="utf-8")
        html_path.write_text(self._html(data), encoding="utf-8")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in [json_path, csv_path, html_path, notes_path]:
                zf.write(p, p.name)
        data["files"] = {
            "json_path": str(json_path),
            "csv_path": str(csv_path),
            "html_path": str(html_path),
            "notes_path": str(notes_path),
            "zip_path": str(zip_path),
        }
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def _html(self, data: Dict[str, Any]) -> str:
        def esc(x: Any) -> str:
            return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows = "".join(
            f"<tr><td>{esc(c.get('role'))}</td><td>{esc(Path(c.get('file','')).name)}</td><td>{esc(c.get('ext'))}</td><td>{esc(c.get('width'))}x{esc(c.get('height'))}</td><td>{esc(c.get('kb'))}KB</td><td>{esc(c.get('frames'))}</td><td>{esc(c.get('status'))}</td><td>{esc(c.get('warnings'))}</td></tr>"
            for c in data.get("checks", [])
        )
        failures = "".join(f"<li>{esc(x)}</li>" for x in data.get("failures", [])) or "<li>없음</li>"
        warnings = "".join(f"<li>{esc(x)}</li>" for x in data.get("warnings", [])) or "<li>없음</li>"
        notes = "".join(f"<li>{esc(x)}</li>" for x in data.get("manual_notes", []))
        counts = "".join(f"<li>{esc(k)}: {esc(v)}</li>" for k, v in data.get("counts", {}).items())
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>카카오 규격 검수 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px;font-size:13px}}th{{background:#f5f5f5}}.card{{background:#f7f7fb;border:1px solid #e5e5ee;border-radius:10px;padding:16px;margin:14px 0}}</style></head><body>
<h1>카카오 이모티콘 규격 검수 리포트</h1>
<div class='card'><b>포맷:</b> {esc(data.get('product_label'))}<br><b>판정:</b> {esc(data.get('decision'))}<br><b>점수:</b> {esc(data.get('score'))}</div>
<h2>수량 요약</h2><ul>{counts}</ul>
<h2>수정 필요</h2><ul>{failures}</ul>
<h2>주의/확인</h2><ul>{warnings}</ul>
<h2>파일별 검사</h2><table><tr><th>역할</th><th>파일</th><th>형식</th><th>크기</th><th>용량</th><th>프레임</th><th>상태</th><th>메모</th></tr>{rows}</table>
<h2>수동 확인 메모</h2><ul>{notes}</ul>
<p>이 리포트는 제출 전 사전 점검용이며 카카오 승인이나 최신 공식 규격 충족을 보장하지 않습니다. 최종 제출 직전 공식 스튜디오 안내를 다시 확인하세요.</p>
</body></html>"""
