from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
from PIL import Image, ImageOps

CSV_CAPTURE_TYPES: Dict[str, Dict[str, Any]] = {
    "review_results": {
        "label": "카카오 심사 결과",
        "required": ["project_name", "format", "status"],
        "columns": ["project_name", "format", "submit_date", "result_date", "status", "rejection_reason", "revision_note", "next_action", "source_note"],
    },
    "sales_notes": {
        "label": "월별 판매/정산 메모",
        "required": ["project_name", "month"],
        "columns": ["project_name", "month", "format", "revenue_memo", "usage_memo", "user_reaction", "next_strategy", "source_note"],
    },
    "phrase_feedback": {
        "label": "문구 반응/사용성 메모",
        "required": ["project_name", "phrase"],
        "columns": ["project_name", "phrase", "category", "reaction_score", "note", "next_action", "source_note"],
    },
    "rejection_reasons": {
        "label": "반려 사유/수정 이력",
        "required": ["project_name", "rejection_reason"],
        "columns": ["project_name", "version", "format", "rejection_reason", "problem_area", "revision_note", "resubmit_plan", "source_note"],
    },
    "quality_results": {
        "label": "품질검사/규격검사 결과",
        "required": ["project_name"],
        "columns": ["project_name", "check_date", "format", "quality_score", "spec_score", "chat_score", "warnings", "next_action", "source_note"],
    },
    "trend_notes": {
        "label": "트렌드/참고자료 메모",
        "required": ["source_title"],
        "columns": ["source_title", "source_type", "source_url", "keyword", "claim_summary", "safe_idea", "risk_note", "source_note"],
    },
}

COLUMN_ALIASES = {
    "프로젝트명": "project_name", "캐릭터명": "project_name", "세트명": "project_name",
    "포맷": "format", "유형": "format",
    "제출일": "submit_date", "심사일": "result_date", "결과일": "result_date", "출시일": "result_date",
    "결과": "status", "상태": "status", "승인여부": "status",
    "반려사유": "rejection_reason", "미승인사유": "rejection_reason", "거절사유": "rejection_reason",
    "수정메모": "revision_note", "수정내용": "revision_note", "개선내용": "revision_note",
    "다음액션": "next_action", "다음전략": "next_strategy",
    "월": "month", "정산월": "month", "매출월": "month",
    "매출": "revenue_memo", "정산": "revenue_memo", "판매메모": "revenue_memo",
    "사용메모": "usage_memo", "반응": "user_reaction", "사용자반응": "user_reaction",
    "문구": "phrase", "멘트": "phrase", "카테고리": "category", "분류": "category",
    "반응점수": "reaction_score", "점수": "reaction_score", "메모": "note",
    "버전": "version", "문제영역": "problem_area", "재제출계획": "resubmit_plan",
    "검사일": "check_date", "품질점수": "quality_score", "규격점수": "spec_score", "채팅점수": "chat_score", "경고": "warnings",
    "자료명": "source_title", "출처명": "source_title", "자료유형": "source_type", "출처유형": "source_type", "URL": "source_url", "링크": "source_url",
    "키워드": "keyword", "주장요약": "claim_summary", "안전아이디어": "safe_idea", "위험메모": "risk_note", "출처메모": "source_note",
}

STATUS_VALUES = {"준비", "제출", "승인", "반려", "미승인", "수정 후 재제출", "출시", "판매 반응 양호", "판매 반응 낮음"}


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_name(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", str(text)).strip("_")
    return text[:80] or "data"


@dataclass
class DataIngestionReport:
    data_type: str
    data_type_label: str
    mode: str
    imported_rows: int
    valid_rows: int
    warning_count: int
    error_count: int
    decision: str
    cleaned_records: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
    extracted_candidates: List[Dict[str, Any]]
    files: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataIngestionPipeline:
    """CSV/캡처 기반 운영 데이터 입력 파이프라인.

    원칙:
    - 원본 CSV/캡처는 original 폴더에 보존한다.
    - 정리본은 cleaned 폴더에 별도 저장한다.
    - 기존 데이터는 덮어쓰지 않고 jsonl로 누적한다.
    - 캡처 OCR은 환경별 오차가 크므로 기본은 이미지 보존+수동 메모 추출이며, 사용자가 확인한 뒤 학습 데이터로 반영한다.
    """

    def __init__(self) -> None:
        self.types = CSV_CAPTURE_TYPES

    def generate_templates(self, output_dir: Path) -> Dict[str, str]:
        out = Path(output_dir)
        tmpl = out / "templates"
        tmpl.mkdir(parents=True, exist_ok=True)
        paths: Dict[str, str] = {}
        for key, spec in CSV_CAPTURE_TYPES.items():
            fp = tmpl / f"template_{key}.csv"
            sample = self._sample_row(key)
            with fp.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=spec["columns"])
                writer.writeheader()
                writer.writerow(sample)
            paths[key] = str(fp)
        zip_path = out / f"csv_templates_{_now()}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in tmpl.glob("*.csv"):
                zf.write(fp, fp.name)
        paths["zip"] = str(zip_path)
        return paths

    def import_csv(self, csv_path: Path, data_type: str, output_dir: Path) -> DataIngestionReport:
        out = Path(output_dir)
        data_type = data_type if data_type in CSV_CAPTURE_TYPES else "review_results"
        spec = CSV_CAPTURE_TYPES[data_type]
        run_dir = out / f"csv_import_{data_type}_{_now()}"
        original_dir = run_dir / "original"
        cleaned_dir = run_dir / "cleaned"
        report_dir = run_dir / "report"
        original_dir.mkdir(parents=True, exist_ok=True)
        cleaned_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        original_path = original_dir / Path(csv_path).name
        shutil.copy2(csv_path, original_path)

        df, read_warning = self._read_csv_robust(original_path)
        warnings: List[str] = []
        errors: List[str] = []
        if read_warning:
            warnings.append(read_warning)
        clean_df = self._normalize_columns(df)
        clean_df = self._ensure_columns(clean_df, spec["columns"])
        clean_df = clean_df[spec["columns"]]
        records = clean_df.fillna("").to_dict(orient="records")

        row_warnings, row_errors = self._validate_records(records, data_type)
        warnings.extend(row_warnings)
        errors.extend(row_errors)

        cleaned_csv = cleaned_dir / f"cleaned_{data_type}.csv"
        clean_df.to_csv(cleaned_csv, index=False, encoding="utf-8-sig")
        cleaned_json = cleaned_dir / f"cleaned_{data_type}.json"
        cleaned_json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

        jsonl_path = self._append_learning_records(out, data_type, records, source="csv", original_path=str(original_path))
        html_path = report_dir / f"csv_import_{data_type}.html"
        json_path = report_dir / f"csv_import_{data_type}.json"
        csv_errors_path = report_dir / f"csv_import_{data_type}_errors.csv"
        pd.DataFrame([{"level":"warning", "message": w} for w in warnings] + [{"level":"error", "message": e} for e in errors]).to_csv(csv_errors_path, index=False, encoding="utf-8-sig")

        files = {
            "run_dir": str(run_dir),
            "original_path": str(original_path),
            "cleaned_csv_path": str(cleaned_csv),
            "cleaned_json_path": str(cleaned_json),
            "learning_jsonl_path": str(jsonl_path),
            "html_path": str(html_path),
            "json_path": str(json_path),
            "error_csv_path": str(csv_errors_path),
        }
        decision = self._decision(len(records), len(errors), len(warnings))
        report = DataIngestionReport(
            data_type=data_type,
            data_type_label=spec["label"],
            mode="csv",
            imported_rows=len(records),
            valid_rows=max(0, len(records) - len(errors)),
            warning_count=len(warnings),
            error_count=len(errors),
            decision=decision,
            cleaned_records=records,
            warnings=warnings,
            errors=errors,
            extracted_candidates=[],
            files=files,
        )
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_html(report, html_path)
        zip_path = run_dir / f"csv_import_{data_type}.zip"
        self._zip_run(run_dir, zip_path)
        report.files["zip_path"] = str(zip_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def import_captures(self, image_paths: Iterable[Path], data_type: str, output_dir: Path, manual_text: str = "") -> DataIngestionReport:
        out = Path(output_dir)
        data_type = data_type if data_type in CSV_CAPTURE_TYPES else "review_results"
        spec = CSV_CAPTURE_TYPES[data_type]
        run_dir = out / f"capture_import_{data_type}_{_now()}"
        original_dir = run_dir / "original_captures"
        preview_dir = run_dir / "previews"
        cleaned_dir = run_dir / "cleaned"
        report_dir = run_dir / "report"
        for d in [original_dir, preview_dir, cleaned_dir, report_dir]:
            d.mkdir(parents=True, exist_ok=True)

        records: List[Dict[str, Any]] = []
        warnings: List[str] = []
        errors: List[str] = []
        candidates: List[Dict[str, Any]] = []
        image_paths = list(image_paths)
        if not image_paths:
            errors.append("캡처 이미지가 없습니다.")

        extracted = self._extract_from_manual_text(manual_text, data_type)
        for idx, src in enumerate(image_paths, start=1):
            src = Path(src)
            dst = original_dir / f"capture_{idx:02d}_{_safe_name(src.name)}"
            shutil.copy2(src, dst)
            preview = self._make_preview(dst, preview_dir / f"preview_{idx:02d}.png")
            meta = self._image_meta(dst)
            candidate = {
                "capture_no": idx,
                "file_name": dst.name,
                "sha256": _sha256(dst),
                "width": meta.get("width"),
                "height": meta.get("height"),
                "mode": meta.get("mode"),
                "preview_path": str(preview),
                "manual_text_excerpt": manual_text[:300],
                "extracted_status": extracted.get("status", ""),
                "extracted_dates": ", ".join(extracted.get("dates", [])),
                "extracted_numbers": ", ".join(extracted.get("numbers", [])),
            }
            candidates.append(candidate)
            record = {col: "" for col in spec["columns"]}
            record.update(self._record_from_extracted(data_type, extracted, manual_text))
            record["source_note"] = f"capture:{dst.name}; 사용자가 캡처 내용을 확인 후 저장 필요"
            records.append(record)

        if manual_text.strip() and not image_paths:
            record = {col: "" for col in spec["columns"]}
            record.update(self._record_from_extracted(data_type, extracted, manual_text))
            record["source_note"] = "manual_text_only"
            records.append(record)

        warnings.append("캡처 텍스트 인식은 화면/해상도/폰트에 따라 오차가 큽니다. v38은 원본 캡처 보존 + 사용자가 붙여넣은 메모 추출 + 확인 후 저장 구조입니다.")
        row_warnings, row_errors = self._validate_records(records, data_type, allow_empty_project=True)
        warnings.extend(row_warnings)
        errors.extend(row_errors)

        cleaned_csv = cleaned_dir / f"capture_cleaned_{data_type}.csv"
        pd.DataFrame(records, columns=spec["columns"]).to_csv(cleaned_csv, index=False, encoding="utf-8-sig")
        candidates_csv = cleaned_dir / f"capture_extracted_candidates_{data_type}.csv"
        pd.DataFrame(candidates).to_csv(candidates_csv, index=False, encoding="utf-8-sig")
        cleaned_json = cleaned_dir / f"capture_cleaned_{data_type}.json"
        cleaned_json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

        jsonl_path = self._append_learning_records(out, data_type, records, source="capture", original_path=str(original_dir))
        html_path = report_dir / f"capture_import_{data_type}.html"
        json_path = report_dir / f"capture_import_{data_type}.json"
        files = {
            "run_dir": str(run_dir),
            "original_capture_dir": str(original_dir),
            "cleaned_csv_path": str(cleaned_csv),
            "candidate_csv_path": str(candidates_csv),
            "cleaned_json_path": str(cleaned_json),
            "learning_jsonl_path": str(jsonl_path),
            "html_path": str(html_path),
            "json_path": str(json_path),
        }
        decision = self._decision(len(records), len(errors), len(warnings))
        report = DataIngestionReport(
            data_type=data_type,
            data_type_label=spec["label"],
            mode="capture",
            imported_rows=len(records),
            valid_rows=max(0, len(records) - len(errors)),
            warning_count=len(warnings),
            error_count=len(errors),
            decision=decision,
            cleaned_records=records,
            warnings=warnings,
            errors=errors,
            extracted_candidates=candidates,
            files=files,
        )
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_html(report, html_path)
        zip_path = run_dir / f"capture_import_{data_type}.zip"
        self._zip_run(run_dir, zip_path)
        report.files["zip_path"] = str(zip_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _sample_row(self, data_type: str) -> Dict[str, str]:
        base = {col: "" for col in CSV_CAPTURE_TYPES[data_type]["columns"]}
        if data_type == "review_results":
            base.update({"project_name":"보리와쌀", "format":"문구형정지", "submit_date":"2026-06-05", "result_date":"2026-06-20", "status":"반려", "rejection_reason":"캐릭터성이 약함", "revision_note":"보리/쌀 성격 차이 강화", "next_action":"v29 개선 엔진 실행"})
        elif data_type == "sales_notes":
            base.update({"project_name":"보리와쌀", "month":"2026-08", "format":"문구형정지", "revenue_memo":"첫 달 반응 보통", "usage_memo":"확인/감사 문구가 자주 쓰임", "user_reaction":"직장인 반응 좋음", "next_strategy":"직장인편 2탄 검토"})
        elif data_type == "phrase_feedback":
            base.update({"project_name":"보리와쌀", "phrase":"확인했어유", "category":"확인", "reaction_score":"5", "note":"짧고 쓰기 좋음", "next_action":"유사 확인 문구 확장"})
        elif data_type == "rejection_reasons":
            base.update({"project_name":"보리와쌀", "version":"1차", "format":"문구형정지", "rejection_reason":"대화 활용성이 낮음", "problem_area":"문구", "revision_note":"짧은 답장형 문구 추가", "resubmit_plan":"수정 후 재제출"})
        elif data_type == "quality_results":
            base.update({"project_name":"보리와쌀", "check_date":"2026-06-05", "format":"문구형정지", "quality_score":"82", "spec_score":"90", "chat_score":"85", "warnings":"문구 2개 길이 주의", "next_action":"문구 축약"})
        elif data_type == "trend_notes":
            base.update({"source_title":"이모티콘 참고영상", "source_type":"YouTube", "source_url":"", "keyword":"짧은 문구", "claim_summary":"그림보다 콘셉트와 멘트가 중요", "safe_idea":"32문구 선기획 강화", "risk_note":"수익 보장 표현 금지"})
        return base

    def _read_csv_robust(self, path: Path) -> tuple[pd.DataFrame, str]:
        encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
        last_exc: Optional[Exception] = None
        for enc in encodings:
            try:
                return pd.read_csv(path, encoding=enc, dtype=str).fillna(""), ("" if enc == "utf-8-sig" else f"인코딩 {enc}로 읽었습니다. 한글이 깨지면 UTF-8-SIG로 다시 저장하세요.")
            except Exception as exc:
                last_exc = exc
        raise ValueError(f"CSV를 읽을 수 없습니다: {last_exc}")

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        rename = {}
        used = set()
        for col in df.columns:
            clean_col = str(col).strip()
            mapped = COLUMN_ALIASES.get(clean_col, clean_col)
            if mapped in used:
                mapped = f"{mapped}_dup"
            rename[col] = mapped
            used.add(mapped)
        return df.rename(columns=rename)

    def _ensure_columns(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        out = df.copy()
        for col in columns:
            if col not in out.columns:
                out[col] = ""
        return out

    def _validate_records(self, records: List[Dict[str, Any]], data_type: str, allow_empty_project: bool = False) -> tuple[List[str], List[str]]:
        spec = CSV_CAPTURE_TYPES[data_type]
        warnings: List[str] = []
        errors: List[str] = []
        required = spec["required"]
        for idx, rec in enumerate(records, start=2):
            for col in required:
                if allow_empty_project and col == "project_name":
                    continue
                if not str(rec.get(col, "")).strip():
                    errors.append(f"{idx}행: 필수값 '{col}'이 비어 있습니다.")
            status = str(rec.get("status", "")).strip()
            if status and status not in STATUS_VALUES:
                warnings.append(f"{idx}행: status '{status}'는 권장값이 아닙니다. 권장: {', '.join(sorted(STATUS_VALUES))}")
            for date_col in ["submit_date", "result_date", "check_date"]:
                val = str(rec.get(date_col, "")).strip()
                if val and not re.match(r"^\d{4}[-/.]?\d{1,2}[-/.]?\d{1,2}$", val):
                    warnings.append(f"{idx}행: {date_col} 날짜 형식 확인 필요: {val}")
            score_val = str(rec.get("reaction_score", "")).strip()
            if score_val:
                try:
                    n = float(score_val)
                    if not 0 <= n <= 5:
                        warnings.append(f"{idx}행: reaction_score는 0~5 권장입니다: {score_val}")
                except ValueError:
                    warnings.append(f"{idx}행: reaction_score 숫자 변환 확인 필요: {score_val}")
        return warnings, errors

    def _extract_from_manual_text(self, text: str, data_type: str) -> Dict[str, Any]:
        text = text or ""
        dates = re.findall(r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b|\b\d{4}년\s*\d{1,2}월\b", text)
        numbers = re.findall(r"\d[\d,]*(?:\.\d+)?\s*(?:원|만원|개|회|점|%)?", text)
        status = ""
        for s in ["승인", "반려", "미승인", "제출", "출시", "수정 후 재제출"]:
            if s in text:
                status = s
                break
        phrases = re.findall(r"['\"“”‘’]([^'\"“”‘’]{1,30})['\"“”‘’]", text)
        return {"dates": dates, "numbers": numbers, "status": status, "phrases": phrases, "raw_text": text}

    def _record_from_extracted(self, data_type: str, extracted: Dict[str, Any], manual_text: str) -> Dict[str, str]:
        rec: Dict[str, str] = {}
        dates = extracted.get("dates", [])
        nums = extracted.get("numbers", [])
        status = extracted.get("status", "")
        phrases = extracted.get("phrases", [])
        if data_type == "review_results":
            rec.update({"status": status, "result_date": dates[0] if dates else "", "rejection_reason": self._summarize_text(manual_text), "source_note": "capture/manual"})
        elif data_type == "sales_notes":
            rec.update({"month": dates[0] if dates else "", "revenue_memo": ", ".join(nums[:5]), "user_reaction": self._summarize_text(manual_text)})
        elif data_type == "phrase_feedback":
            rec.update({"phrase": phrases[0] if phrases else "", "note": self._summarize_text(manual_text)})
        elif data_type == "rejection_reasons":
            rec.update({"rejection_reason": self._summarize_text(manual_text), "revision_note": "캡처 확인 후 수정 필요"})
        elif data_type == "quality_results":
            rec.update({"check_date": dates[0] if dates else "", "warnings": self._summarize_text(manual_text)})
        else:
            rec.update({"source_title": "캡처/메모", "claim_summary": self._summarize_text(manual_text)})
        return rec

    def _summarize_text(self, text: str, limit: int = 180) -> str:
        clean = re.sub(r"\s+", " ", text or "").strip()
        return clean[:limit]

    def _make_preview(self, image_path: Path, preview_path: Path) -> Path:
        try:
            im = Image.open(image_path).convert("RGBA")
            im.thumbnail((900, 900))
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            bg.alpha_composite(im)
            bg.save(preview_path)
        except Exception:
            shutil.copy2(image_path, preview_path)
        return preview_path

    def _image_meta(self, image_path: Path) -> Dict[str, Any]:
        try:
            with Image.open(image_path) as im:
                return {"width": im.width, "height": im.height, "mode": im.mode, "format": im.format}
        except Exception:
            return {}

    def _append_learning_records(self, output_dir: Path, data_type: str, records: List[Dict[str, Any]], source: str, original_path: str) -> Path:
        store = Path(output_dir) / "UserData" / "growth_learning" / "imports"
        store.mkdir(parents=True, exist_ok=True)
        jsonl = store / f"{data_type}.jsonl"
        ts = datetime.now().isoformat(timespec="seconds")
        with jsonl.open("a", encoding="utf-8") as f:
            for rec in records:
                payload = {"imported_at": ts, "data_type": data_type, "source": source, "original_path": original_path, "record": rec}
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return jsonl

    def _decision(self, rows: int, errors: int, warnings: int) -> str:
        if rows <= 0 or errors > 0:
            return "수정 필요"
        if warnings > 0:
            return "확인 후 저장 권장"
        return "저장 가능"

    def _write_html(self, report: DataIngestionReport, path: Path) -> None:
        def esc(x: Any) -> str:
            return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows = "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in rec.values()) + "</tr>" for rec in report.cleaned_records[:200])
        headers = ""
        if report.cleaned_records:
            headers = "<tr>" + "".join(f"<th>{esc(k)}</th>" for k in report.cleaned_records[0].keys()) + "</tr>"
        warnings = "".join(f"<li>{esc(w)}</li>" for w in report.warnings)
        errors = "".join(f"<li>{esc(e)}</li>" for e in report.errors)
        html = f"""<!doctype html>
<html lang=\"ko\"><head><meta charset=\"utf-8\"><title>v38 CSV/캡처 입력 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;line-height:1.55}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #ddd;padding:6px;vertical-align:top}}th{{background:#f5f5f5}}.ok{{background:#eef9f0;padding:12px;border-radius:8px}}.warn{{background:#fff7e6;padding:12px;border-radius:8px}}.err{{background:#fff0f0;padding:12px;border-radius:8px}}</style></head>
<body>
<h1>v38 CSV/캡처 데이터 가져오기 리포트</h1>
<div class=\"ok\"><b>유형:</b> {esc(report.data_type_label)} / <b>방식:</b> {esc(report.mode)} / <b>판정:</b> {esc(report.decision)}</div>
<p>가져온 행: {report.imported_rows} / 유효 행 추정: {report.valid_rows} / 경고: {report.warning_count} / 오류: {report.error_count}</p>
<h2>경고</h2><div class=\"warn\"><ul>{warnings}</ul></div>
<h2>오류</h2><div class=\"err\"><ul>{errors}</ul></div>
<h2>정리 데이터 미리보기</h2><table>{headers}{rows}</table>
<h2>파일</h2><pre>{esc(json.dumps(report.files, ensure_ascii=False, indent=2))}</pre>
<p>주의: 캡처 기반 데이터는 OCR/수동 메모 오차가 있을 수 있으므로 사용자가 최종 확인한 뒤 성장형 학습 데이터로 확정해야 합니다.</p>
</body></html>"""
        path.write_text(html, encoding="utf-8")

    def _zip_run(self, run_dir: Path, zip_path: Path) -> None:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in run_dir.rglob("*"):
                if fp == zip_path or fp.is_dir():
                    continue
                zf.write(fp, fp.relative_to(run_dir))
