from __future__ import annotations

import html
import json
import re
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageSequence, ImageStat


SNAPSHOT_KEYS = [
    "profile",
    "concepts",
    "expressions",
    "format_scores",
    "trend_result",
    "prototype_specs",
    "prototype_results",
    "expression_pack_files",
    "expression_pack_zip",
    "submission_result",
    "quality_review",
    "drawing_canvas_report",
    "drawing_refine_report",
    "direct_illustration_report",
    "v70_set_completion_report",
    "v71_pre_submission_qc_report",
    "v72_submission_autofix_lock_report",
    "v73_final_user_approval_report",
    "v76_rejection_to_regeneration_report",
    "v80_final_delivery_report",
]

INVALID_WINDOWS_CHARS = set('<>:"/\\|?*')
RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, (list, tuple, set)):
            return [_jsonable(item) for item in value]
        if isinstance(value, dict):
            return {str(key): _jsonable(item) for key, item in value.items()}
        return str(value)


def save_project_snapshot(session_state: Any, out_dir: Path, app_version: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "app_version": app_version,
        "state": {},
    }
    for key in SNAPSHOT_KEYS:
        if key in session_state:
            payload["state"][key] = _jsonable(session_state.get(key))
    path = out_dir / "recent_project_snapshot.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_project_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def filename_findings(name: str) -> list[str]:
    findings: list[str] = []
    parts = re.split(r"[\\/]", name)
    for part in parts:
        if not part or part in {".", ".."}:
            findings.append("비어 있거나 위험한 경로 조각이 있습니다.")
            continue
        if any(ch in INVALID_WINDOWS_CHARS or ord(ch) < 32 for ch in part):
            findings.append(f"Windows 파일명 금지 문자가 있습니다: {part}")
        if Path(part).stem.upper() in RESERVED_WINDOWS_NAMES:
            findings.append(f"Windows 예약 이름입니다: {part}")
        if len(part) > 80:
            findings.append(f"파일명이 너무 깁니다: {part[:36]}...")
    return findings


def _edge_alpha_ratio(image: Image.Image) -> float:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    if width < 2 or height < 2:
        return 1.0
    alpha = rgba.getchannel("A")
    edge_pixels = []
    edge_pixels.extend(alpha.crop((0, 0, width, 1)).getdata())
    edge_pixels.extend(alpha.crop((0, height - 1, width, height)).getdata())
    edge_pixels.extend(alpha.crop((0, 0, 1, height)).getdata())
    edge_pixels.extend(alpha.crop((width - 1, 0, width, height)).getdata())
    return sum(1 for value in edge_pixels if value > 12) / max(1, len(edge_pixels))


def analyze_image_bytes(name: str, data: bytes) -> dict[str, Any]:
    issues = filename_findings(name)
    status = "PASS"
    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            fmt = (image.format or Path(name).suffix.lstrip(".") or "unknown").upper()
            frame_count = sum(1 for _ in ImageSequence.Iterator(image)) if fmt == "GIF" else 1
            first_frame = image.copy()
            luma = first_frame.convert("L")
            stat = ImageStat.Stat(luma)
            contrast = float(stat.extrema[0][1] - stat.extrema[0][0])
            edge_ratio = _edge_alpha_ratio(first_frame)

        if width != 360 or height != 360:
            issues.append(f"권장 크기 360x360과 다릅니다: {width}x{height}")
        if len(data) > 1024 * 1024:
            issues.append("파일 크기가 1MB를 넘습니다. 제출 전 공식 용량 기준을 다시 확인하세요.")
        if fmt == "GIF" and frame_count < 2:
            issues.append("GIF인데 프레임이 1개뿐입니다.")
        if contrast < 42:
            issues.append("전체 대비가 낮아 작은 썸네일에서 글자/그림이 묻힐 수 있습니다.")
        if edge_ratio > 0.18:
            issues.append("이미지가 가장자리까지 닿아 글자 또는 그림 잘림 가능성이 있습니다.")

        if any("금지" in item or "예약" in item or "위험" in item for item in issues):
            status = "FAIL"
        elif issues:
            status = "WARN"
        return {
            "file_name": name,
            "status": status,
            "format": fmt,
            "width": width,
            "height": height,
            "bytes": len(data),
            "frames": frame_count,
            "contrast": round(contrast, 1),
            "edge_touch_ratio": round(edge_ratio, 3),
            "issues": issues,
        }
    except Exception as exc:
        return {
            "file_name": name,
            "status": "FAIL",
            "format": "unknown",
            "width": None,
            "height": None,
            "bytes": len(data),
            "frames": 0,
            "contrast": 0,
            "edge_touch_ratio": 0,
            "issues": [f"이미지 분석 실패: {exc}"],
        }


def analyze_uploaded_package(name: str, data: bytes) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if name.lower().endswith(".zip"):
        with zipfile.ZipFile(BytesIO(data)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                suffix = Path(info.filename).suffix.lower()
                if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                    rows.append(analyze_image_bytes(info.filename, archive.read(info)))
                else:
                    issues = filename_findings(info.filename)
                    if issues:
                        rows.append({
                            "file_name": info.filename,
                            "status": "FAIL",
                            "format": suffix.lstrip(".").upper() or "FILE",
                            "width": None,
                            "height": None,
                            "bytes": info.file_size,
                            "frames": None,
                            "contrast": None,
                            "edge_touch_ratio": None,
                            "issues": issues,
                        })
    else:
        rows.append(analyze_image_bytes(name, data))

    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    warn_count = sum(1 for row in rows if row["status"] == "WARN")
    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    failed_rows = [row for row in rows if row["status"] in {"FAIL", "WARN"}]
    return {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "source_name": name,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "rows": rows,
        "failed_rows": failed_rows,
        "overall_status": "FAIL" if fail_count else "WARN" if warn_count else "PASS",
    }


def rerun_failed_items(previous_report: dict[str, Any]) -> dict[str, Any]:
    rows = previous_report.get("failed_rows") or []
    return {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "source_name": previous_report.get("source_name", "previous_failed_items"),
        "pass_count": 0,
        "warn_count": sum(1 for row in rows if row.get("status") == "WARN"),
        "fail_count": sum(1 for row in rows if row.get("status") == "FAIL"),
        "rows": rows,
        "failed_rows": rows,
        "overall_status": "FAIL" if any(row.get("status") == "FAIL" for row in rows) else "WARN" if rows else "PASS",
        "note": "원본 파일 없이 이전 실패/경고 항목만 빠르게 요약했습니다. 파일을 다시 올리면 실제 재검사를 수행합니다.",
    }


def create_one_page_summary(report: dict[str, Any], out_dir: Path, app_version: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    body_rows = []
    for row in report.get("rows", [])[:160]:
        issues = "<br>".join(html.escape(str(item)) for item in row.get("issues", [])) or "없음"
        body_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('status', '')))}</td>"
            f"<td>{html.escape(str(row.get('file_name', '')))}</td>"
            f"<td>{html.escape(str(row.get('format', '')))}</td>"
            f"<td>{html.escape(str(row.get('width', '')))}x{html.escape(str(row.get('height', '')))}</td>"
            f"<td>{html.escape(str(row.get('frames', '')))}</td>"
            f"<td>{issues}</td>"
            "</tr>"
        )
    path = out_dir / "one_page_submission_summary.html"
    path.write_text(
        f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>제출 전 한 장 요약 리포트</title>
  <style>
    body {{ font-family: "Malgun Gothic", Arial, sans-serif; margin: 32px; color: #25221d; background: #f7f4ed; }}
    main {{ max-width: 1040px; margin: auto; background: #fffdf8; border: 1px solid #ded5c7; padding: 28px; }}
    h1 {{ margin: 0 0 8px; }}
    .meta {{ color: #766f64; margin-bottom: 20px; }}
    .score {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 18px 0; }}
    .score div {{ border: 1px solid #ded5c7; padding: 14px; background: #fbf6eb; }}
    .score b {{ display: block; font-size: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
    th, td {{ border-bottom: 1px solid #ded5c7; padding: 9px; text-align: left; vertical-align: top; }}
    th {{ background: #e6f3ee; }}
  </style>
</head>
<body>
<main>
  <h1>제출 전 한 장 요약 리포트</h1>
  <div class="meta">앱 버전 {html.escape(app_version)} · 생성 시각 {html.escape(str(report.get("checked_at", "")))} · 원본 {html.escape(str(report.get("source_name", "")))}</div>
  <div class="score">
    <div><span>전체 상태</span><b>{html.escape(str(report.get("overall_status", "")))}</b></div>
    <div><span>PASS</span><b>{html.escape(str(report.get("pass_count", 0)))}</b></div>
    <div><span>WARN</span><b>{html.escape(str(report.get("warn_count", 0)))}</b></div>
    <div><span>FAIL</span><b>{html.escape(str(report.get("fail_count", 0)))}</b></div>
  </div>
  <p>이 리포트는 로컬 사전 자가검사 결과입니다. 실제 제출 전에는 카카오 공식 기준, 저작권, 상표권, 유사성을 직접 재확인해야 합니다.</p>
  <table>
    <thead><tr><th>상태</th><th>파일명</th><th>형식</th><th>크기</th><th>프레임</th><th>확인 사항</th></tr></thead>
    <tbody>{''.join(body_rows)}</tbody>
  </table>
</main>
</body>
</html>""",
        encoding="utf-8",
    )
    return path
