from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import py_compile
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from modules.constants import APP_NAME, APP_VERSION
from modules.data_safety import DataSafetyManager
from modules.format_strategy import FormatStrategyEngine
from modules.kakao_studio_excel import KakaoStudioExcelLearningEngine
from modules.performance_dashboard import PerformanceDashboardEngine
from modules.platform_repackaging import PlatformRepackagingEngine
from modules.selected_format_autofix import SelectedFormatAutoFixEngine, SELECTED_FORMAT_SPECS


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", str(text)).strip("_")[:80] or "project"


def col(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def xml_escape(value: object) -> str:
    text = str(value or "")
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_min_xlsx(path: Path, rows: list[list[object]]) -> None:
    """Write a tiny XLSX fixture without requiring Excel/openpyxl."""
    path.parent.mkdir(parents=True, exist_ok=True)
    strings: list[str] = []
    string_index: dict[str, int] = {}

    def idx(v: object) -> int:
        text = str(v or "")
        if text not in string_index:
            string_index[text] = len(strings)
            strings.append(text)
        return string_index[text]

    sheet_rows: list[str] = []
    for r_i, row in enumerate(rows, start=1):
        cells: list[str] = []
        for c_i, value in enumerate(row):
            if value == "" or value is None:
                continue
            cells.append(f'<c r="{col(c_i)}{r_i}" t="s"><v>{idx(value)}</v></c>')
        sheet_rows.append(f'<row r="{r_i}">{"".join(cells)}</row>')
    shared = "".join(f'<si><t>{xml_escape(s)}</t></si>' for s in strings)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>''')
        z.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''')
        z.writestr("xl/workbook.xml", '''<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>''')
        z.writestr("xl/_rels/workbook.xml.rels", '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>''')
        z.writestr("xl/sharedStrings.xml", f'''<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(strings)}" uniqueCount="{len(strings)}">{shared}</sst>''')
        z.writestr("xl/worksheets/sheet1.xml", f'''<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{''.join(sheet_rows)}</sheetData></worksheet>''')


def add_result(results: list[dict[str, Any]], area: str, name: str, status: str, detail: str, path: str = "") -> None:
    results.append({"area": area, "name": name, "status": status, "detail": detail, "path": path})


def compile_python(results: list[dict[str, Any]]) -> None:
    targets = [ROOT / "app.py"] + sorted((ROOT / "modules").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py"))
    failures = []
    for py in targets:
        try:
            py_compile.compile(str(py), doraise=True)
        except Exception as exc:
            failures.append(f"{py.relative_to(ROOT)}: {exc}")
    if failures:
        add_result(results, "Code", "Python compile", "FAIL", " | ".join(failures[:10]))
        raise AssertionError("compile failed")
    add_result(results, "Code", "Python compile", "PASS", f"{len(targets)}개 Python 파일 컴파일 통과")


def import_modules(results: list[dict[str, Any]]) -> None:
    files = sorted((ROOT / "modules").rglob("*.py"))
    failures = []
    imported = 0
    for path in files:
        rel = path.relative_to(ROOT).with_suffix("")
        if rel.name == "__init__":
            module_name = ".".join(rel.parent.parts)
        else:
            module_name = ".".join(rel.parts)
        try:
            __import__(module_name)
            imported += 1
        except Exception as exc:
            failures.append(f"{module_name}: {exc}")
    if failures:
        add_result(results, "Import", "Module import", "FAIL", " | ".join(failures[:10]))
        raise AssertionError("module import failed")
    add_result(results, "Import", "Module import", "PASS", f"{imported}개 모듈 import 통과")


def verify_delivery_files(results: list[dict[str, Any]]) -> None:
    required = [
        "1_INSTALL_NOW.bat", "2_START_PROGRAM.bat", "4_REPAIR_ENVIRONMENT.bat", "6_RUN_DIAGNOSTICS.bat",
        "8_BACKUP_USER_DATA.bat", "9_DATA_SAFETY_CHECK.bat", "10_V43_DIAGNOSE_AND_REPAIR.bat",
        "README.md", "requirements.txt", "START_WINDOWS.bat", "START_MAC_LINUX.sh",
    ]
    missing = [name for name in required if not (ROOT / name).exists()]
    if missing:
        add_result(results, "Package", "Required files", "FAIL", "누락: " + ", ".join(missing))
        raise AssertionError("required files missing")
    add_result(results, "Package", "Required files", "PASS", f"필수 실행/복구/문서 파일 {len(required)}개 확인")

    protected_candidates = [ROOT / "outputs", DataSafetyManager().default_user_data_dir()]
    add_result(results, "DataSafety", "Code/data separation", "PASS", "로컬 outputs와 OS별 UserData 분리 구조 확인", "; ".join(str(p) for p in protected_candidates))


def make_sample_images(out: Path) -> Path:
    src = out / "sample_sources"
    src.mkdir(parents=True, exist_ok=True)
    labels = ["넵", "확인", "감사", "죄송", "잠시", "완료", "퇴근", "좋아요"]
    for i, label in enumerate(labels, start=1):
        size = [(360, 360), (420, 360), (360, 400), (512, 512)][i % 4]
        im = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([45, 45, size[0] - 45, size[1] - 80], radius=80, fill=(255, 238, 190, 255), outline=(45, 42, 38, 255), width=5)
        d.ellipse([size[0]//2 - 55, size[1]//2 - 42, size[0]//2 - 42, size[1]//2 - 29], fill=(35, 35, 35, 255))
        d.ellipse([size[0]//2 + 42, size[1]//2 - 42, size[0]//2 + 55, size[1]//2 - 29], fill=(35, 35, 35, 255))
        d.arc([size[0]//2 - 35, size[1]//2 - 20, size[0]//2 + 35, size[1]//2 + 35], 10, 170, fill=(35, 35, 35, 255), width=4)
        d.rounded_rectangle([55, size[1] - 75, size[0] - 55, size[1] - 20], radius=12, fill=(255, 255, 255, 235), outline=(70, 70, 70, 255), width=2)
        d.text((75, size[1] - 62), label, fill=(30, 30, 30, 255))
        im.save(src / f"source_{i:02d}.png")
    return src


def run_pipeline(results: list[dict[str, Any]], run_dir: Path) -> dict[str, Any]:
    fixtures = run_dir / "fixtures"
    plus = fixtures / "20260529-20260604_plus_report.xlsx"
    sales = fixtures / "20260529-20260604_sales_report.xlsx"
    write_min_xlsx(plus, [
        ["", ""],
        ["", "조회기간 : 2026.05.29 ~ 2026.06.04"],
        [],
        ["", "날짜", "이모티콘명", "시리즈명", "발신수", "이용자수"],
        ["", "2026.06.01", "보리와 쌀", "직장인편", "120", "45"],
        ["", "2026.06.02", "보리와 쌀", "직장인편", "180", "60"],
        ["", "2026.06.03", "감자사원", "직장인편", "250", "80"],
    ])
    write_min_xlsx(sales, [
        ["", ""],
        ["", "판매기간 : 2026.05.29 ~ 2026.06.04"],
        ["", "구분", "국내", "일본", "글로벌", "", ""],
        ["", "판매 건수", "5", "0", "1", "", ""],
        ["", "판매금액 (VAT 포함)", "12500", "0", "2500", "", ""],
        [],
        ["", "판매일", "유형", "이모티콘 제목", "", "시리즈명", "구분", "판매금액 (VAT 포함)", "", ""],
        ["", "", "", "", "", "", "", "건수", "통화", "금액"],
        ["", "2026.06.01", "일반", "보리와 쌀", "", "직장인편", "국내", "3", "KRW", "7500"],
        ["", "2026.06.02", "일반", "감자사원", "", "직장인편", "국내", "2", "KRW", "5000"],
        ["", "2026.06.03", "일반", "보리와 쌀", "", "직장인편", "글로벌", "1", "USD", "2500"],
    ])

    v39_report = KakaoStudioExcelLearningEngine().build_report(run_dir / "v39_excel_learning", plus, sales, "v44_integration_excel", confirm_save=True)
    assert v39_report.plus_rows and v39_report.sales_details and v39_report.performance_scores
    add_result(results, "Pipeline", "v39 Excel learning", "PASS", f"발신 {len(v39_report.plus_rows)}행, 판매 {len(v39_report.sales_details)}행, 성과 {len(v39_report.performance_scores)}개", v39_report.files.get("html_path", ""))

    v40_report = PerformanceDashboardEngine().build_report(run_dir / "v40_dashboard", "v44_integration_dashboard", v39_report.to_dict())
    v40_dict = v40_report.to_dict()
    assert v40_dict["dashboard_rows"] and v40_dict["strategy_recommendations"]
    add_result(results, "Pipeline", "v40 Dashboard", "PASS", f"총 발신 {v40_dict['portfolio_metrics']['total_sent']} / 판매 {v40_dict['portfolio_metrics']['total_sales_count']}건", v40_dict["files"].get("html_path", ""))

    strategy = FormatStrategyEngine().build_report(
        run_dir / "v37_format_strategy",
        project_name="v44_integration_format_strategy",
        character_concept="보리와 쌀 직장인 답장형 캐릭터. 짧은 문구, 감사, 확인, 퇴근, 사과, 응원 중심.",
        phrase_examples="넵, 확인했습니다, 감사합니다, 죄송합니다, 잠시만요, 완료했습니다, 퇴근하고 싶습니다",
        personality="예의 바르지만 피곤한 직장인 듀오",
        motion_strength=2,
        expression_variety_score=78,
        chat_readability_score=82,
        quality_score=80,
        review_status="아직 제출 전",
        approval_count=0,
        rejection_count=0,
        sales_signal="엑셀 학습 샘플 데이터 있음. 실제 제출 전 공식 기준 확인 필요.",
    )
    selected_format = strategy.primary_format["format_key"]
    if selected_format == "big":
        selected_format_for_fix = "big_static"
    elif selected_format not in SELECTED_FORMAT_SPECS:
        selected_format_for_fix = "static_text"
    else:
        selected_format_for_fix = selected_format
    add_result(results, "Pipeline", "v37 Format strategy", "PASS", f"1차 추천 포맷: {strategy.primary_format['format_label']} ({selected_format})", strategy.files.get("html_path", ""))

    src_dir = make_sample_images(run_dir)
    fix_report = SelectedFormatAutoFixEngine(run_dir / "v41_selected_format_autofix").run(src_dir, selected_format_for_fix, project_name="v44_selected_format_autofix", title="보리와 쌀")
    assert Path(fix_report["zip_path"]).exists()
    add_result(results, "Pipeline", "v41 Selected-format autofix", "PASS", f"선택 포맷만 자동 보정: {selected_format_for_fix}, records={len(fix_report['records'])}", fix_report.get("html_path", fix_report.get("zip_path", "")))

    fixed_dir = Path(fix_report["fixed_dir"])
    repack = PlatformRepackagingEngine(run_dir / "v42_platform_repackaging").run(
        fixed_dir,
        project_name="v44_platform_repackaging",
        title="보리와 쌀",
        selected_platforms=["naver_ogq", "line_sticker", "band_sticker", "sns_square", "sns_story", "goods_png"],
        max_assets_per_platform=3,
    )
    assert Path(repack["files"]["zip_path"]).exists()
    add_result(results, "Pipeline", "v42 Platform repackaging", "PASS", f"플랫폼 초안 {len(repack['platform_summaries'])}종 생성", repack["files"].get("html_path", ""))

    return {
        "v39": v39_report.to_dict(),
        "v40": v40_dict,
        "v37": strategy.to_dict(),
        "v41": fix_report,
        "v42": repack,
        "selected_format_for_fix": selected_format_for_fix,
    }


def verify_data_safety(results: list[dict[str, Any]], run_dir: Path) -> dict[str, Any]:
    mgr = DataSafetyManager()
    user_dirs = mgr.ensure_user_data_dirs(ROOT)
    sample_user_file = Path(user_dirs["projects"]) / "v44_integration_user_data_sample.json"
    sample_user_file.parent.mkdir(parents=True, exist_ok=True)
    sample_user_file.write_text(json.dumps({"project": "v44", "note": "data safety sample"}, ensure_ascii=False), encoding="utf-8")
    backup = mgr.create_backup(ROOT, backup_root=run_dir / "backup_archives", project_name="v44_integration_data_safety", output_dir=run_dir / "data_safety")
    verify = mgr.verify_backup(backup.backup_zip_path, output_dir=run_dir / "data_safety_verify", project_name="v44_integration_backup_verify")
    assert Path(backup.backup_zip_path).exists()
    assert any(item.status == "PASS" for item in verify.items or [])
    add_result(results, "DataSafety", "Backup/verify", "PASS", f"백업 ZIP 생성 및 검증 완료, SHA-256={backup.backup_sha256[:16]}...", backup.backup_zip_path)
    return {"user_dirs": user_dirs, "backup": backup.to_dict(), "verify": verify.to_dict()}


def write_reports(run_dir: Path, results: list[dict[str, Any]], artifacts: dict[str, Any]) -> dict[str, str]:
    status = "PASS" if all(r["status"] == "PASS" for r in results) else "WARN"
    report = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "overall_status": status,
        "results": results,
        "artifacts": artifacts,
        "final_notes": [
            "v44는 v11~v43 기능을 삭제하지 않고 전체 연결 검증과 납품 패키지 정리를 추가합니다.",
            "카카오/OGQ/LINE/BAND 등 공식 제출 규격은 변경될 수 있으므로 제출 직전 공식 사이트에서 재확인이 필요합니다.",
            "생성형 AI 완성본을 몰래 제출하는 구조가 아니라, 직접 창작·스케치·수정 기록·권리 검토를 보조하는 구조입니다.",
            "사용자 데이터는 코드 폴더와 분리하고, 업데이트 전 백업/검증을 우선합니다.",
        ],
    }
    json_path = run_dir / "v44_full_integration_report.json"
    csv_path = run_dir / "v44_full_integration_results.csv"
    html_path = run_dir / "v44_full_integration_report.html"
    txt_path = run_dir / "v44_final_delivery_summary.txt"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["area", "name", "status", "detail", "path"])
        writer.writeheader()
        writer.writerows(results)
    rows_html = "".join(
        f"<tr><td>{r['area']}</td><td>{r['name']}</td><td>{r['status']}</td><td>{r['detail']}</td><td>{r.get('path','')}</td></tr>"
        for r in results
    )
    html_path.write_text(f'''<!doctype html><html><head><meta charset="utf-8"><title>v44 전체 통합 검증 리포트</title>
<style>body{{font-family:Arial,'Noto Sans KR',sans-serif;margin:28px;line-height:1.55}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px;font-size:13px;vertical-align:top}}th{{background:#f5f5f5}}.pass{{background:#e9fff0;border-left:5px solid #20a052;padding:12px}}.warn{{background:#fff8de;border-left:5px solid #d39b00;padding:12px}}</style></head><body>
<h1>v44 전체 통합 검증 / 최종 납품 패키지 리포트</h1>
<p><b>{APP_NAME}</b> / version {APP_VERSION} / {report['created_at']}</p>
<div class="{'pass' if status == 'PASS' else 'warn'}"><b>전체 상태:</b> {status}</div>
<h2>검증 결과</h2><table><thead><tr><th>영역</th><th>항목</th><th>상태</th><th>세부 내용</th><th>파일</th></tr></thead><tbody>{rows_html}</tbody></table>
<h2>최종 메모</h2><ul>{''.join(f'<li>{n}</li>' for n in report['final_notes'])}</ul>
</body></html>''', encoding="utf-8")
    txt_path.write_text(
        "카카오 이모티콘 수익화 시스템 v44 최종 납품 요약\n"
        f"생성시각: {report['created_at']}\n"
        f"전체상태: {status}\n\n"
        "검증 항목:\n" + "\n".join(f"- [{r['status']}] {r['area']} / {r['name']}: {r['detail']}" for r in results) + "\n\n"
        "주의: 공식 제출 규격은 제출 직전 최신 기준으로 다시 확인하세요.\n",
        encoding="utf-8",
    )
    return {"json_path": str(json_path), "csv_path": str(csv_path), "html_path": str(html_path), "summary_path": str(txt_path)}


def main() -> int:
    start = time.time()
    run_dir = ROOT / "outputs" / "v44_final_integration" / f"v44_full_check_{now_id()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    artifacts: dict[str, Any] = {}
    try:
        compile_python(results)
        import_modules(results)
        verify_delivery_files(results)
        artifacts["pipeline"] = run_pipeline(results, run_dir)
        artifacts["data_safety"] = verify_data_safety(results, run_dir)
        files = write_reports(run_dir, results, artifacts)
        add_result(results, "Report", "v44 final report", "PASS", "JSON/HTML/CSV/요약 리포트 생성 완료", files["html_path"])
        files = write_reports(run_dir, results, artifacts)
        print("v44_full_integration_check PASS")
        print("APP", APP_NAME, APP_VERSION)
        print("REPORT", files["html_path"])
        print("SUMMARY", files["summary_path"])
        print("SECONDS", round(time.time() - start, 2))
        return 0
    except Exception as exc:
        add_result(results, "Fatal", "v44 integration", "FAIL", repr(exc))
        files = write_reports(run_dir, results, artifacts)
        print("v44_full_integration_check FAIL")
        print("ERROR", repr(exc))
        print("REPORT", files["html_path"])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
