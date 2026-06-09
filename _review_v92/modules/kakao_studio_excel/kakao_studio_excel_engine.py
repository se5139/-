from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_name(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", str(text)).strip("_")[:80] or "data"


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        # '0원', '1,200건' 같은 형태 대응
        m = re.search(r"-?\d+(?:\.\d+)?", text)
        return float(m.group(0)) if m else 0.0


def _int(value: Any) -> int:
    return int(round(_num(value)))


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_date(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    text = text.replace(".", "-").replace("/", "-")
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return text


def _extract_period(text: str) -> Dict[str, str]:
    text = _clean(text)
    # 조회기간 : 2026.05.29 ~ 2026.06.04 / 판매기간 : ...
    m = re.search(r"(\d{4}[./-]\d{1,2}[./-]\d{1,2})\s*~\s*(\d{4}[./-]\d{1,2}[./-]\d{1,2})", text)
    if m:
        return {"start_date": _normalize_date(m.group(1)), "end_date": _normalize_date(m.group(2)), "raw": text}
    return {"start_date": "", "end_date": "", "raw": text}


def _col_index(cell_ref: str) -> int:
    letters = re.match(r"([A-Z]+)", cell_ref or "A").group(1)
    idx = 0
    for ch in letters:
        idx = idx * 26 + ord(ch) - 64
    return idx - 1


@dataclass
class KakaoStudioExcelReport:
    project_name: str
    imported_at: str
    plus_file: str
    sales_file: str
    period: Dict[str, str]
    plus_rows: List[Dict[str, Any]]
    sales_summary: List[Dict[str, Any]]
    sales_details: List[Dict[str, Any]]
    performance_scores: List[Dict[str, Any]]
    extension_recommendations: List[Dict[str, Any]]
    data_health: Dict[str, Any]
    warnings: List[str]
    files: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SimpleXlsxReader:
    """의존성 없는 XLSX 값 읽기 도구.

    카카오 스튜디오에서 내려받은 리포트처럼 수식보다 값·표 구조가 중요한 파일을 읽기 위한
    가벼운 파서다. 외부 라이브러리 없이 zip/xml만 사용한다.
    """

    def read_rows(self, path: Path) -> List[List[str]]:
        path = Path(path)
        with zipfile.ZipFile(path) as zf:
            shared = self._read_shared_strings(zf)
            sheet_name = self._first_sheet_path(zf)
            root = ET.fromstring(zf.read(sheet_name))
            rows: List[List[str]] = []
            for row in root.findall(".//m:row", NS):
                cell_map: Dict[int, str] = {}
                max_idx = -1
                for cell in row.findall("m:c", NS):
                    ref = cell.attrib.get("r", "A1")
                    idx = _col_index(ref)
                    value = self._cell_value(cell, shared)
                    cell_map[idx] = value
                    max_idx = max(max_idx, idx)
                if max_idx >= 0:
                    rows.append([cell_map.get(i, "") for i in range(max_idx + 1)])
                else:
                    rows.append([])
            return rows

    def _first_sheet_path(self, zf: zipfile.ZipFile) -> str:
        sheet_paths = sorted(name for name in zf.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        if not sheet_paths:
            raise ValueError("XLSX 안에서 worksheet를 찾지 못했습니다.")
        return sheet_paths[0]

    def _read_shared_strings(self, zf: zipfile.ZipFile) -> List[str]:
        if "xl/sharedStrings.xml" not in zf.namelist():
            return []
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        result = []
        for si in root.findall("m:si", NS):
            text = "".join(t.text or "" for t in si.findall(".//m:t", NS))
            result.append(text)
        return result

    def _cell_value(self, cell: ET.Element, shared: List[str]) -> str:
        t = cell.attrib.get("t")
        if t == "s":
            v = cell.find("m:v", NS)
            if v is not None and v.text is not None:
                try:
                    return shared[int(v.text)]
                except Exception:
                    return v.text or ""
            return ""
        if t == "inlineStr":
            return "".join(node.text or "" for node in cell.findall(".//m:t", NS))
        v = cell.find("m:v", NS)
        if v is not None and v.text is not None:
            return v.text
        return ""


class KakaoStudioExcelLearningEngine:
    """카카오 이모티콘 스튜디오 공식 엑셀 리포트 2종을 학습 데이터로 누적한다.

    지원 파일:
    1) 이모티콘 플러스 발신 통계: 날짜, 이모티콘명, 시리즈명, 발신수, 이용자수
    2) 판매내역: 판매기간, 국가별 요약, 판매일, 유형, 이모티콘 제목, 시리즈명, 구분, 건수/통화/금액
    """

    def __init__(self) -> None:
        self.reader = SimpleXlsxReader()

    def build_report(
        self,
        output_dir: Path,
        plus_xlsx: Optional[Path] = None,
        sales_xlsx: Optional[Path] = None,
        project_name: str = "kakao_studio_excel_learning",
        confirm_save: bool = True,
    ) -> KakaoStudioExcelReport:
        output_dir = Path(output_dir)
        run_dir = output_dir / f"kakao_studio_excel_v39_{_now()}"
        original_dir = run_dir / "original_excel"
        cleaned_dir = run_dir / "cleaned"
        report_dir = run_dir / "report"
        for d in [original_dir, cleaned_dir, report_dir]:
            d.mkdir(parents=True, exist_ok=True)

        warnings: List[str] = []
        plus_rows: List[Dict[str, Any]] = []
        sales_summary: List[Dict[str, Any]] = []
        sales_details: List[Dict[str, Any]] = []
        periods: List[Dict[str, str]] = []
        plus_file_name = ""
        sales_file_name = ""

        if plus_xlsx:
            dst = original_dir / Path(plus_xlsx).name
            shutil.copy2(plus_xlsx, dst)
            plus_file_name = dst.name
            try:
                rows = self.reader.read_rows(dst)
                parsed = self.parse_plus_report(rows)
                plus_rows = parsed["rows"]
                periods.append(parsed["period"])
                if not plus_rows:
                    warnings.append("구독발신 엑셀에서 실제 발신 데이터 행이 없습니다. 양식은 저장하지만 학습 점수는 0으로 계산됩니다.")
            except Exception as exc:
                warnings.append(f"구독발신 엑셀 처리 실패: {exc}")
        else:
            warnings.append("구독발신 엑셀이 업로드되지 않았습니다.")

        if sales_xlsx:
            dst = original_dir / Path(sales_xlsx).name
            shutil.copy2(sales_xlsx, dst)
            sales_file_name = dst.name
            try:
                rows = self.reader.read_rows(dst)
                parsed = self.parse_sales_report(rows)
                sales_summary = parsed["summary"]
                sales_details = parsed["details"]
                periods.append(parsed["period"])
                if not sales_details and not any(_num(r.get("sales_count", 0)) or _num(r.get("sales_amount_vat", 0)) for r in sales_summary):
                    warnings.append("판매내역 엑셀에서 실제 판매 상세 데이터가 없고 요약 금액/건수도 0입니다. 구조 확인용으로 저장됩니다.")
            except Exception as exc:
                warnings.append(f"판매내역 엑셀 처리 실패: {exc}")
        else:
            warnings.append("판매내역 엑셀이 업로드되지 않았습니다.")

        period = self._merge_periods(periods)
        scores = self.compute_performance_scores(plus_rows, sales_details)
        recommendations = self.build_extension_recommendations(scores, plus_rows, sales_summary, sales_details)
        health = self.data_health(plus_rows, sales_summary, sales_details, warnings)

        files: Dict[str, str] = {
            "run_dir": str(run_dir),
            "original_dir": str(original_dir),
        }
        files.update(self._write_csv_json(cleaned_dir, "plus_rows", plus_rows))
        files.update(self._write_csv_json(cleaned_dir, "sales_summary", sales_summary))
        files.update(self._write_csv_json(cleaned_dir, "sales_details", sales_details))
        files.update(self._write_csv_json(cleaned_dir, "performance_scores", scores))
        files.update(self._write_csv_json(cleaned_dir, "extension_recommendations", recommendations))
        jsonl_path = self._append_learning_records(output_dir, project_name, plus_rows, sales_summary, sales_details, scores, confirm_save)
        files["learning_jsonl_path"] = str(jsonl_path)

        report = KakaoStudioExcelReport(
            project_name=project_name,
            imported_at=datetime.now().isoformat(timespec="seconds"),
            plus_file=plus_file_name,
            sales_file=sales_file_name,
            period=period,
            plus_rows=plus_rows,
            sales_summary=sales_summary,
            sales_details=sales_details,
            performance_scores=scores,
            extension_recommendations=recommendations,
            data_health=health,
            warnings=warnings,
            files=files,
        )
        html_path = report_dir / "kakao_studio_excel_v39.html"
        json_path = report_dir / "kakao_studio_excel_v39.json"
        self._write_html(report, html_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        files["html_path"] = str(html_path)
        files["json_path"] = str(json_path)

        zip_path = run_dir / "kakao_studio_excel_v39.zip"
        self._zip_run(run_dir, zip_path)
        files["zip_path"] = str(zip_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def parse_plus_report(self, rows: List[List[str]]) -> Dict[str, Any]:
        period = {"start_date": "", "end_date": "", "raw": ""}
        header_idx = -1
        header = []
        for i, row in enumerate(rows):
            joined = " ".join(_clean(x) for x in row)
            if "조회기간" in joined:
                period = _extract_period(joined)
            normalized = [_clean(x) for x in row]
            if "날짜" in normalized and "이모티콘명" in normalized and "발신수" in normalized:
                header_idx = i
                header = normalized
                break
        if header_idx < 0:
            return {"period": period, "rows": []}

        col = {name: idx for idx, name in enumerate(header)}
        parsed: List[Dict[str, Any]] = []
        for row in rows[header_idx + 1:]:
            if not any(_clean(x) for x in row):
                continue
            rec = {
                "date": _normalize_date(self._get(row, col.get("날짜"))),
                "emoticon_name": _clean(self._get(row, col.get("이모티콘명"))),
                "series_name": _clean(self._get(row, col.get("시리즈명"))),
                "sent_count": _int(self._get(row, col.get("발신수"))),
                "user_count": _int(self._get(row, col.get("이용자수"))),
            }
            rec["repeat_rate"] = round(rec["sent_count"] / rec["user_count"], 3) if rec["user_count"] else 0
            if rec["date"] or rec["emoticon_name"] or rec["sent_count"] or rec["user_count"]:
                parsed.append(rec)
        return {"period": period, "rows": parsed}

    def parse_sales_report(self, rows: List[List[str]]) -> Dict[str, Any]:
        period = {"start_date": "", "end_date": "", "raw": ""}
        for row in rows:
            joined = " ".join(_clean(x) for x in row)
            if "판매기간" in joined:
                period = _extract_period(joined)
                break

        summary = self._parse_sales_summary(rows)
        details = self._parse_sales_details(rows)
        return {"period": period, "summary": summary, "details": details}

    def _parse_sales_summary(self, rows: List[List[str]]) -> List[Dict[str, Any]]:
        countries: List[str] = []
        count_row: Optional[List[str]] = None
        amount_row: Optional[List[str]] = None
        for row in rows[:10]:
            clean = [_clean(x) for x in row]
            if "구분" in clean and any(x in clean for x in ["국내", "일본", "글로벌"]):
                idx = clean.index("구분")
                countries = [x for x in clean[idx + 1:] if x]
            if "판매 건수" in clean:
                count_row = clean
            if any("판매금액" in x for x in clean):
                amount_row = clean
        result = []
        if countries and count_row:
            start_idx = count_row.index("판매 건수") + 1 if "판매 건수" in count_row else 2
            for i, country in enumerate(countries):
                count = _int(count_row[start_idx + i] if start_idx + i < len(count_row) else 0)
                amount = 0.0
                if amount_row:
                    amount_start = next((j for j, v in enumerate(amount_row) if "판매금액" in v), 1) + 1
                    amount = _num(amount_row[amount_start + i] if amount_start + i < len(amount_row) else 0)
                result.append({"market": country, "sales_count": count, "sales_amount_vat": amount})
        return result

    def _parse_sales_details(self, rows: List[List[str]]) -> List[Dict[str, Any]]:
        header_idx = -1
        for i, row in enumerate(rows):
            clean = [_clean(x) for x in row]
            if "판매일" in clean and "이모티콘 제목" in clean:
                header_idx = i
                break
        if header_idx < 0:
            return []
        details: List[Dict[str, Any]] = []
        for row in rows[header_idx + 2:]:
            if not any(_clean(x) for x in row):
                continue
            # 카카오 판매내역 구조: B 판매일, C 유형, D 제목, F 시리즈명, G 구분, H 건수, I 통화, J 금액
            rec = {
                "sale_date": _normalize_date(self._get(row, 1)),
                "type": _clean(self._get(row, 2)),
                "emoticon_title": _clean(self._get(row, 3)),
                "series_name": _clean(self._get(row, 5)),
                "market": _clean(self._get(row, 6)),
                "sales_count": _int(self._get(row, 7)),
                "currency": _clean(self._get(row, 8)),
                "amount": _num(self._get(row, 9)),
            }
            if any([rec["sale_date"], rec["emoticon_title"], rec["series_name"], rec["sales_count"], rec["amount"]]):
                details.append(rec)
        return details

    def compute_performance_scores(self, plus_rows: List[Dict[str, Any]], sales_details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        bucket: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for row in plus_rows:
            key = (row.get("emoticon_name") or "미지정", row.get("series_name") or "")
            rec = bucket.setdefault(key, {"emoticon_name": key[0], "series_name": key[1], "sent_count": 0, "user_count": 0, "sales_count": 0, "sales_amount": 0.0})
            rec["sent_count"] += _int(row.get("sent_count", 0))
            rec["user_count"] += _int(row.get("user_count", 0))
        for row in sales_details:
            key = (row.get("emoticon_title") or "미지정", row.get("series_name") or "")
            rec = bucket.setdefault(key, {"emoticon_name": key[0], "series_name": key[1], "sent_count": 0, "user_count": 0, "sales_count": 0, "sales_amount": 0.0})
            rec["sales_count"] += _int(row.get("sales_count", 0))
            rec["sales_amount"] += _num(row.get("amount", 0))

        scores = []
        for rec in bucket.values():
            repeat_rate = rec["sent_count"] / rec["user_count"] if rec["user_count"] else 0
            plus_score = min(60, rec["sent_count"] * 0.15 + rec["user_count"] * 0.5 + repeat_rate * 5)
            sales_score = min(40, rec["sales_count"] * 4 + rec["sales_amount"] / 10000)
            total = round(plus_score + sales_score, 1)
            rec2 = dict(rec)
            rec2["repeat_rate"] = round(repeat_rate, 3)
            rec2["plus_score"] = round(plus_score, 1)
            rec2["sales_score"] = round(sales_score, 1)
            rec2["total_score"] = total
            rec2["interpretation"] = self._score_interpretation(rec2)
            scores.append(rec2)
        return sorted(scores, key=lambda x: x.get("total_score", 0), reverse=True)

    def build_extension_recommendations(
        self,
        scores: List[Dict[str, Any]],
        plus_rows: List[Dict[str, Any]],
        sales_summary: List[Dict[str, Any]],
        sales_details: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        total_sent = sum(_int(r.get("sent_count", 0)) for r in plus_rows)
        total_users = sum(_int(r.get("user_count", 0)) for r in plus_rows)
        total_sales_count = sum(_int(r.get("sales_count", 0)) for r in sales_details) or sum(_int(r.get("sales_count", 0)) for r in sales_summary)
        total_sales_amount = sum(_num(r.get("amount", 0)) for r in sales_details) or sum(_num(r.get("sales_amount_vat", 0)) for r in sales_summary)
        recs: List[Dict[str, Any]] = []
        if total_sent <= 0 and total_sales_count <= 0:
            recs.append({
                "priority": 1,
                "recommendation": "데이터 축적 우선",
                "reason": "현재 업로드된 파일에 실제 발신/판매 데이터가 없거나 0입니다.",
                "next_action": "출시 후 주간/월간 엑셀을 계속 업로드해 기준 데이터를 쌓습니다.",
            })
            recs.append({
                "priority": 2,
                "recommendation": "1차 포맷 유지",
                "reason": "성과 데이터가 없을 때는 미니/큰/움직이는 확장을 바로 판단하지 않습니다.",
                "next_action": "v37의 1차 추천 포맷 1개에 집중하고 품질검사·가독성 데이터를 먼저 확보합니다.",
            })
            return recs
        if total_sent > 0 and total_users > 0:
            repeat_rate = total_sent / total_users
            if repeat_rate >= 2.0:
                recs.append({"priority": 1, "recommendation": "시리즈화 검토", "reason": f"발신수/이용자수 반복률이 {repeat_rate:.2f}로 반복 사용 경향이 있습니다.", "next_action": "같은 캐릭터의 상황별 2탄 또는 직장/감정/사투리 편을 검토합니다."})
            else:
                recs.append({"priority": 1, "recommendation": "문구 사용성 보강", "reason": f"반복률이 {repeat_rate:.2f}로 아직 강하지 않습니다.", "next_action": "짧은 답장형·검색 키워드형 문구를 추가하고 채팅 미리보기 점수를 재확인합니다."})
        if total_sales_count > 0 or total_sales_amount > 0:
            recs.append({"priority": 2, "recommendation": "구매 전환형 제목/대표 이미지 분석", "reason": f"판매 {total_sales_count}건, 금액 {total_sales_amount:,.0f} 데이터가 있습니다.", "next_action": "판매가 발생한 제목·시리즈명을 기준으로 제목 후보와 공유 이미지를 보강합니다."})
        if total_sent > 0 and total_sales_count <= 0:
            recs.append({"priority": 3, "recommendation": "이모티콘 플러스 사용성 유지", "reason": "구독 발신은 있으나 구매 데이터가 약합니다.", "next_action": "플러스 검색 키워드·짧은 문구 중심의 사용성은 유지하고 판매형 제목/대표 이미지를 개선합니다."})
        return recs

    def data_health(self, plus_rows: List[Dict[str, Any]], sales_summary: List[Dict[str, Any]], sales_details: List[Dict[str, Any]], warnings: List[str]) -> Dict[str, Any]:
        sent = sum(_int(r.get("sent_count", 0)) for r in plus_rows)
        users = sum(_int(r.get("user_count", 0)) for r in plus_rows)
        sales_count = sum(_int(r.get("sales_count", 0)) for r in sales_details) or sum(_int(r.get("sales_count", 0)) for r in sales_summary)
        amount = sum(_num(r.get("amount", 0)) for r in sales_details) or sum(_num(r.get("sales_amount_vat", 0)) for r in sales_summary)
        score = 0
        score += 25 if plus_rows else 0
        score += 25 if sent or users else 0
        score += 25 if (sales_details or sales_summary) else 0
        score += 25 if sales_count or amount else 0
        level = "학습 가능" if score >= 75 else "구조 저장/추가 데이터 필요" if score >= 25 else "데이터 부족"
        return {"health_score": score, "level": level, "plus_rows": len(plus_rows), "total_sent": sent, "total_users": users, "sales_detail_rows": len(sales_details), "total_sales_count": sales_count, "total_sales_amount": amount, "warning_count": len(warnings)}

    def _score_interpretation(self, rec: Dict[str, Any]) -> str:
        if rec.get("sent_count", 0) and rec.get("sales_count", 0):
            return "구독 사용성과 구매 반응이 모두 있는 후보"
        if rec.get("sent_count", 0):
            return "이모티콘 플러스 발신 중심 반응 후보"
        if rec.get("sales_count", 0) or rec.get("sales_amount", 0):
            return "판매 중심 반응 후보"
        return "성과 데이터 부족"

    def _merge_periods(self, periods: List[Dict[str, str]]) -> Dict[str, str]:
        starts = [p.get("start_date") for p in periods if p.get("start_date")]
        ends = [p.get("end_date") for p in periods if p.get("end_date")]
        return {"start_date": min(starts) if starts else "", "end_date": max(ends) if ends else "", "raw": " / ".join(p.get("raw", "") for p in periods if p.get("raw"))}

    def _get(self, row: List[str], idx: Optional[int]) -> str:
        if idx is None or idx < 0 or idx >= len(row):
            return ""
        return row[idx]

    def _write_csv_json(self, out: Path, name: str, records: List[Dict[str, Any]]) -> Dict[str, str]:
        out.mkdir(parents=True, exist_ok=True)
        csv_path = out / f"{name}.csv"
        json_path = out / f"{name}.json"
        if records:
            keys = list(dict.fromkeys(k for rec in records for k in rec.keys()))
        else:
            keys = ["note"]
            records = [{"note": "데이터 없음"}]
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(records)
        json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return {f"{name}_csv_path": str(csv_path), f"{name}_json_path": str(json_path)}

    def _append_learning_records(
        self,
        output_dir: Path,
        project_name: str,
        plus_rows: List[Dict[str, Any]],
        sales_summary: List[Dict[str, Any]],
        sales_details: List[Dict[str, Any]],
        scores: List[Dict[str, Any]],
        confirm_save: bool,
    ) -> Path:
        store = Path(output_dir) / "UserData" / "growth_learning" / "kakao_studio_excel"
        store.mkdir(parents=True, exist_ok=True)
        jsonl = store / "kakao_studio_excel_imports.jsonl"
        payload = {
            "imported_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "confirm_save": bool(confirm_save),
            "plus_rows": plus_rows,
            "sales_summary": sales_summary,
            "sales_details": sales_details,
            "performance_scores": scores,
        }
        if confirm_save:
            with jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        else:
            draft = store / f"kakao_studio_excel_draft_{_now()}.json"
            draft.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return draft
        return jsonl

    def _write_html(self, report: KakaoStudioExcelReport, path: Path) -> None:
        def esc(x: Any) -> str:
            return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def table(records: List[Dict[str, Any]], limit: int = 80) -> str:
            if not records:
                return "<p>데이터 없음</p>"
            keys = list(dict.fromkeys(k for rec in records for k in rec.keys()))
            head = "<tr>" + "".join(f"<th>{esc(k)}</th>" for k in keys) + "</tr>"
            body = "".join("<tr>" + "".join(f"<td>{esc(rec.get(k, ''))}</td>" for k in keys) + "</tr>" for rec in records[:limit])
            return f"<table>{head}{body}</table>"

        warnings = "".join(f"<li>{esc(w)}</li>" for w in report.warnings)
        recs = "".join(f"<li><b>{esc(r.get('recommendation'))}</b>: {esc(r.get('reason'))} → {esc(r.get('next_action'))}</li>" for r in report.extension_recommendations)
        html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>v39 카카오 스튜디오 엑셀 성과 학습 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:24px;line-height:1.55}}table{{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0 24px}}th,td{{border:1px solid #ddd;padding:6px;vertical-align:top}}th{{background:#f5f5f5}}.card{{background:#f8fbff;border:1px solid #dce7f7;padding:12px;border-radius:8px;margin:10px 0}}.warn{{background:#fff7e6;border:1px solid #ffe0a3;padding:12px;border-radius:8px}}</style></head>
<body>
<h1>v39 카카오 스튜디오 엑셀 성과 학습 리포트</h1>
<div class="card"><b>프로젝트:</b> {esc(report.project_name)}<br><b>기간:</b> {esc(report.period.get('start_date'))} ~ {esc(report.period.get('end_date'))}<br><b>데이터 건강도:</b> {esc(report.data_health.get('level'))} / {esc(report.data_health.get('health_score'))}점</div>
<h2>경고/확인 필요</h2><div class="warn"><ul>{warnings}</ul></div>
<h2>확장/학습 추천</h2><ul>{recs}</ul>
<h2>작품별 성과 점수</h2>{table(report.performance_scores)}
<h2>이모티콘 플러스 발신 통계</h2>{table(report.plus_rows)}
<h2>판매 요약</h2>{table(report.sales_summary)}
<h2>판매 상세</h2>{table(report.sales_details)}
<h2>생성 파일</h2><pre>{esc(json.dumps(report.files, ensure_ascii=False, indent=2))}</pre>
<p>주의: 이 리포트는 카카오 스튜디오 엑셀을 정리한 학습 보조 자료이며, 승인이나 수익을 보장하지 않습니다. 데이터가 0이거나 비어 있으면 판단보다 누적 저장을 우선합니다.</p>
</body></html>"""
        path.write_text(html, encoding="utf-8")

    def _zip_run(self, run_dir: Path, zip_path: Path) -> None:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in run_dir.rglob("*"):
                if fp == zip_path or fp.is_dir():
                    continue
                zf.write(fp, fp.relative_to(run_dir))
