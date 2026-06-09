from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import csv
import hashlib
import json
import shutil
import sqlite3
import time
import zipfile

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None

from modules.rejection_resubmission_loop import V74RejectionResubmissionLoop


@dataclass
class V75CaptureRejectionIngestionReport:
    project_name: str
    output_dir: str
    capture_status: str
    image_count: int
    ocr_available: bool
    ocr_attempted_count: int
    extracted_text_count: int
    combined_rejection_text: str
    capture_manifest_json: str
    capture_analysis_csv: str
    ocr_candidates_csv: str
    capture_contact_sheet_png: str
    image_archive_zip: str
    v74_html_report_path: str
    v74_action_plan_csv: str
    v74_resubmission_work_package_zip: str
    v75_html_report_path: str
    v75_work_package_zip: str
    learning_db: str
    checksum_sha256: str
    safety_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class V75CaptureRejectionIngestionEngine:
    """v75 캡처 이미지 반려 사유 입력/OCR 보조 엔진.

    목적:
    - 카카오 심사 결과/반려 사유 캡처 이미지를 원본 보존한다.
    - OCR이 가능하면 보조 추출을 시도한다. 실패해도 작업은 중단하지 않는다.
    - 사용자가 수동 교정한 텍스트와 결합해 v74 반려 대비/재제출 루프로 넘긴다.

    주의:
    - OCR은 보조 기능이다. 한글 OCR 정확도와 Windows 설치 상태를 보장하지 않는다.
    - 원본 캡처는 복제/재사용이 아니라 반려 사유 기록용으로만 보존한다.
    """

    VERSION = "75.0.0"
    SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    SAMPLE_REJECTION_TEXT = """심사 결과 캡처 보조 입력입니다.
문구가 길어 작은 화면에서 가독성이 낮아 보입니다.
일부 표현이 반복적으로 보이며 움직임이 단순합니다.
캐릭터 고유성이 더 분명해야 합니다."""

    def __init__(self) -> None:
        self.v74 = V74RejectionResubmissionLoop()

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _write_csv(self, path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

    def _write_json(self, path: Path, obj: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def _zip_paths(self, zip_path: Path, paths: Iterable[Path], root: Path | None = None) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                if not p.exists():
                    continue
                if p.is_dir():
                    for child in p.rglob("*"):
                        if child.is_file():
                            arc = str(child.relative_to(root or p.parent)) if (root or p.parent) in child.parents else child.name
                            zf.write(child, arc)
                else:
                    try:
                        arc = str(p.relative_to(root)) if root else p.name
                    except Exception:
                        arc = p.name
                    zf.write(p, arc)

    def _save_images(self, image_inputs: Iterable[Tuple[str, bytes]], out_dir: Path) -> List[Dict[str, Any]]:
        raw_dir = out_dir / "capture_originals"
        normalized_dir = out_dir / "capture_normalized"
        raw_dir.mkdir(parents=True, exist_ok=True)
        normalized_dir.mkdir(parents=True, exist_ok=True)
        rows: List[Dict[str, Any]] = []
        for idx, (name, data) in enumerate(image_inputs, start=1):
            suffix = Path(name).suffix.lower() or ".png"
            safe_name = f"capture_{idx:02d}{suffix if suffix in self.SUPPORTED_IMAGE_SUFFIXES else '.png'}"
            raw_path = raw_dir / safe_name
            raw_path.write_bytes(data)
            try:
                with Image.open(raw_path) as im0:
                    im = ImageOps.exif_transpose(im0).convert("RGBA")
                    w, h = im.size
                    thumb = im.copy()
                    thumb.thumbnail((720, 720), Image.Resampling.LANCZOS)
                    norm_path = normalized_dir / f"capture_{idx:02d}_normalized.png"
                    thumb.save(norm_path)
                    # Lightweight visual metrics for routing; no OCR required.
                    gray = ImageOps.grayscale(im.resize((min(480, max(1, w)), max(1, int(h * min(480, max(1, w)) / max(1, w))))))
                    hist = gray.histogram()
                    pixels = sum(hist) or 1
                    dark_ratio = sum(hist[:80]) / pixels
                    light_ratio = sum(hist[200:]) / pixels
                    rows.append({
                        "no": idx,
                        "original_name": name,
                        "saved_original": str(raw_path),
                        "normalized_preview": str(norm_path),
                        "width": w,
                        "height": h,
                        "mode": im0.mode,
                        "file_size_bytes": raw_path.stat().st_size,
                        "dark_ratio": round(dark_ratio, 4),
                        "light_ratio": round(light_ratio, 4),
                        "analysis_note": "캡처 원본 보존 및 OCR/수동입력 연계 대상",
                        "status": "ok",
                    })
            except Exception as exc:
                rows.append({
                    "no": idx,
                    "original_name": name,
                    "saved_original": str(raw_path),
                    "normalized_preview": "",
                    "width": "",
                    "height": "",
                    "mode": "",
                    "file_size_bytes": raw_path.stat().st_size if raw_path.exists() else 0,
                    "dark_ratio": "",
                    "light_ratio": "",
                    "analysis_note": f"이미지 열기 실패: {exc}",
                    "status": "error",
                })
        return rows

    def _try_ocr(self, image_rows: List[Dict[str, Any]], languages: str = "kor+eng") -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        available = pytesseract is not None
        for row in image_rows:
            normalized = Path(str(row.get("normalized_preview", "")))
            no = row.get("no", "")
            if not normalized.exists():
                rows.append({"no": no, "ocr_engine": "pytesseract", "available": available, "status": "skipped", "text": "", "note": "normalized image missing"})
                continue
            if not available:
                rows.append({"no": no, "ocr_engine": "pytesseract", "available": False, "status": "unavailable", "text": "", "note": "pytesseract/Tesseract 미설치: 수동 교정 입력 사용"})
                continue
            try:
                text = pytesseract.image_to_string(Image.open(normalized), lang=languages) or ""
                rows.append({"no": no, "ocr_engine": "pytesseract", "available": True, "status": "ok", "text": text.strip(), "note": "OCR 보조 추출 완료; 반드시 사용자 교정 필요"})
            except Exception as exc:
                rows.append({"no": no, "ocr_engine": "pytesseract", "available": True, "status": "failed", "text": "", "note": f"OCR 실패: {exc}"})
        return rows

    def _contact_sheet(self, image_rows: List[Dict[str, Any]], out_path: Path) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        thumbs: List[Tuple[int, Image.Image, str]] = []
        for row in image_rows:
            p = Path(str(row.get("normalized_preview", "")))
            if not p.exists():
                continue
            with Image.open(p) as im:
                thumb = ImageOps.exif_transpose(im).convert("RGB")
                thumb.thumbnail((260, 190), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (280, 230), "white")
                x = (280 - thumb.width) // 2
                canvas.paste(thumb, (x, 18))
                draw = ImageDraw.Draw(canvas)
                draw.text((14, 202), f"#{row.get('no')} {row.get('width')}x{row.get('height')}", fill=(35, 45, 60))
                thumbs.append((int(row.get("no", 0) or 0), canvas, str(row.get("original_name", ""))))
        if not thumbs:
            sheet = Image.new("RGB", (680, 220), "white")
            ImageDraw.Draw(sheet).text((28, 96), "No valid capture images", fill=(0, 0, 0))
            sheet.save(out_path)
            return
        cols = 3
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 300 + 20, rows * 250 + 20), (245, 247, 251))
        for i, (_, img, _) in enumerate(thumbs):
            x = 10 + (i % cols) * 300
            y = 10 + (i // cols) * 250
            sheet.paste(img, (x, y))
        sheet.save(out_path)

    def _render_html(self, template_root: Path, out_path: Path, context: Dict[str, Any]) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if Environment is None:
            html = "<html><body><h1>v75 Capture Report</h1><pre>" + json.dumps(context, ensure_ascii=False, indent=2) + "</pre></body></html>"
            out_path.write_text(html, encoding="utf-8")
            return
        env = Environment(loader=FileSystemLoader(str(template_root)), autoescape=select_autoescape(["html", "xml"]))
        tmpl = env.get_template("v75_capture_rejection_report.html.j2")
        out_path.write_text(tmpl.render(**context), encoding="utf-8")

    def _learning_db(self, db_path: Path, manifest: Dict[str, Any]) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS capture_rejection_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, project_name TEXT, image_count INTEGER, ocr_available INTEGER, extracted_text_count INTEGER, manifest_json TEXT)"
            )
            conn.execute(
                "INSERT INTO capture_rejection_runs (created_at, project_name, image_count, ocr_available, extracted_text_count, manifest_json) VALUES (?, ?, ?, ?, ?, ?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), manifest.get("project_name"), manifest.get("image_count", 0), 1 if manifest.get("ocr_available") else 0, manifest.get("extracted_text_count", 0), json.dumps(manifest, ensure_ascii=False)),
            )
            conn.commit()
        finally:
            conn.close()

    def build_bundle(
        self,
        project_name: str,
        concept_text: str,
        selected_style: str,
        main_phrase: str,
        user_feedback: str,
        online_abstract_notes: str,
        manual_rejection_text: str,
        image_inputs: Iterable[Tuple[str, bytes]] | None,
        out_dir: Path,
        enable_ocr: bool = True,
    ) -> V75CaptureRejectionIngestionReport:
        safe_project = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (project_name or "v75_capture_rejection")).strip("_") or "v75_capture_rejection"
        run_dir = Path(out_dir) / f"{safe_project}_{int(time.time())}"
        run_dir.mkdir(parents=True, exist_ok=True)

        image_rows = self._save_images(image_inputs or [], run_dir)
        contact_sheet = run_dir / "v75_capture_contact_sheet.png"
        self._contact_sheet(image_rows, contact_sheet)

        ocr_rows = self._try_ocr(image_rows) if enable_ocr else [
            {"no": r.get("no", ""), "ocr_engine": "disabled", "available": False, "status": "disabled", "text": "", "note": "사용자가 OCR 시도를 끔"} for r in image_rows
        ]
        ocr_available = any(bool(r.get("available")) for r in ocr_rows)
        extracted_texts = [str(r.get("text", "")).strip() for r in ocr_rows if str(r.get("text", "")).strip()]

        manual_text = (manual_rejection_text or "").strip()
        combined = "\n".join([x for x in [manual_text, *extracted_texts] if x]).strip()
        if not combined:
            combined = self.SAMPLE_REJECTION_TEXT

        capture_csv = run_dir / "v75_capture_analysis.csv"
        self._write_csv(capture_csv, image_rows, ["no", "original_name", "saved_original", "normalized_preview", "width", "height", "mode", "file_size_bytes", "dark_ratio", "light_ratio", "analysis_note", "status"])
        ocr_csv = run_dir / "v75_ocr_candidates.csv"
        self._write_csv(ocr_csv, ocr_rows, ["no", "ocr_engine", "available", "status", "text", "note"])

        # Feed the corrected/captured rejection text into v74 loop.
        v74_result = self.v74.build_bundle(
            project_name=f"{safe_project}_from_capture",
            concept_text=concept_text,
            selected_style=selected_style,
            main_phrase=main_phrase,
            user_feedback=user_feedback + "\n[v75 캡처 입력] 캡처 이미지와 수동/OCR 후보 텍스트를 기준으로 반려 개선 루프를 실행했습니다.",
            online_abstract_notes=online_abstract_notes,
            rejection_text=combined,
            out_dir=run_dir / "v74_rejection_loop",
        )
        v74_dict = v74_result.to_dict()

        manifest = {
            "version": self.VERSION,
            "project_name": project_name,
            "capture_status": "ready_for_v74_loop",
            "image_count": len(image_rows),
            "ocr_available": ocr_available,
            "ocr_attempted_count": len(ocr_rows),
            "extracted_text_count": len(extracted_texts),
            "combined_rejection_text": combined,
            "safety_notes": [
                "OCR은 보조 기능이며 한글 인식 정확도를 보장하지 않습니다.",
                "캡처 이미지는 반려 사유 기록용으로 보존하며 타 캐릭터 복제에 사용하지 않습니다.",
                "수동 교정 텍스트를 최종 기준으로 삼고 v74 개선 루프에 전달합니다.",
                "API 키, 비밀번호, 개인정보 원문은 패키지에 저장하지 않는 원칙을 유지합니다.",
            ],
            "v74_result": v74_dict,
        }
        manifest_json = run_dir / "v75_capture_manifest.json"
        self._write_json(manifest_json, manifest)

        db_path = run_dir / "v75_capture_rejection_learning.sqlite3"
        self._learning_db(db_path, manifest)

        html_path = run_dir / "v75_capture_rejection_report.html"
        template_root = Path(__file__).resolve().parents[1] / "templates" / "v75_capture_rejection_ingestion"
        self._render_html(template_root, html_path, {
            "project_name": project_name,
            "concept_text": concept_text,
            "selected_style": selected_style,
            "main_phrase": main_phrase,
            "image_rows": image_rows,
            "ocr_rows": ocr_rows,
            "combined_rejection_text": combined,
            "v74_result": v74_dict,
            "manifest": manifest,
            "contact_sheet_name": contact_sheet.name,
        })

        image_archive = run_dir / "v75_capture_image_archive.zip"
        self._zip_paths(image_archive, [run_dir / "capture_originals", run_dir / "capture_normalized", contact_sheet], root=run_dir)

        work_zip = run_dir / "v75_capture_to_resubmission_work_package.zip"
        self._zip_paths(work_zip, [
            html_path, capture_csv, ocr_csv, manifest_json, contact_sheet, image_archive, db_path,
            Path(v74_dict.get("html_report_path", "")),
            Path(v74_dict.get("action_plan_csv", "")),
            Path(v74_dict.get("resubmission_work_package_zip", "")),
            Path(v74_dict.get("locked_review_zip", "")),
        ], root=run_dir)
        checksum = self._sha256(work_zip)

        return V75CaptureRejectionIngestionReport(
            project_name=project_name,
            output_dir=str(run_dir),
            capture_status="ready_for_v74_loop",
            image_count=len(image_rows),
            ocr_available=ocr_available,
            ocr_attempted_count=len(ocr_rows),
            extracted_text_count=len(extracted_texts),
            combined_rejection_text=combined,
            capture_manifest_json=str(manifest_json),
            capture_analysis_csv=str(capture_csv),
            ocr_candidates_csv=str(ocr_csv),
            capture_contact_sheet_png=str(contact_sheet),
            image_archive_zip=str(image_archive),
            v74_html_report_path=str(v74_dict.get("html_report_path", "")),
            v74_action_plan_csv=str(v74_dict.get("action_plan_csv", "")),
            v74_resubmission_work_package_zip=str(v74_dict.get("resubmission_work_package_zip", "")),
            v75_html_report_path=str(html_path),
            v75_work_package_zip=str(work_zip),
            learning_db=str(db_path),
            checksum_sha256=checksum,
            safety_notes=manifest["safety_notes"],
        )
