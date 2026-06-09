from __future__ import annotations
from pathlib import Path
import zipfile

from modules.kakao_studio_excel import KakaoStudioExcelLearningEngine


def col(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def write_min_xlsx(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    strings: list[str] = []
    string_index: dict[str, int] = {}
    def idx(v: object) -> int:
        text = str(v or "")
        if text not in string_index:
            string_index[text] = len(strings)
            strings.append(text)
        return string_index[text]
    sheet_rows = []
    for r_i, row in enumerate(rows, start=1):
        cells = []
        for c_i, value in enumerate(row):
            if value == "" or value is None:
                continue
            cells.append(f'<c r="{col(c_i)}{r_i}" t="s"><v>{idx(value)}</v></c>')
        sheet_rows.append(f'<row r="{r_i}">{"".join(cells)}</row>')
    shared = ''.join(f'<si><t>{s}</t></si>' for s in strings)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>''')
        z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''')
        z.writestr('xl/workbook.xml', '''<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>''')
        z.writestr('xl/_rels/workbook.xml.rels', '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>''')
        z.writestr('xl/sharedStrings.xml', f'''<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(strings)}" uniqueCount="{len(strings)}">{shared}</sst>''')
        z.writestr('xl/worksheets/sheet1.xml', f'''<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{''.join(sheet_rows)}</sheetData></worksheet>''')


out = Path('outputs/check/v39')
out.mkdir(parents=True, exist_ok=True)
plus = out / 'sample_plus_report.xlsx'
sales = out / 'sample_sales_report.xlsx'
write_min_xlsx(plus, [
    ['', ''],
    ['', '조회기간 : 2026.05.29 ~ 2026.06.04'],
    [],
    ['', '날짜', '이모티콘명', '시리즈명', '발신수', '이용자수'],
    ['', '2026.06.01', '보리와 쌀', '직장인편', '120', '45'],
    ['', '2026.06.02', '보리와 쌀', '직장인편', '180', '60'],
])
write_min_xlsx(sales, [
    ['', ''],
    ['', '판매기간 : 2026.05.29 ~ 2026.06.04'],
    ['', '구분', '국내', '일본', '글로벌', '', ''],
    ['', '판매 건수', '3', '0', '1', '', ''],
    ['', '판매금액 (VAT 포함)', '7500', '0', '2500', '', ''],
    [],
    ['', '판매일', '유형', '이모티콘 제목', '', '시리즈명', '구분', '판매금액 (VAT 포함)', '', ''],
    ['', '', '', '', '', '', '', '건수', '통화', '금액'],
    ['', '2026.06.01', '일반', '보리와 쌀', '', '직장인편', '국내', '3', 'KRW', '7500'],
    ['', '2026.06.02', '일반', '보리와 쌀', '', '직장인편', '글로벌', '1', 'USD', '2500'],
])
report = KakaoStudioExcelLearningEngine().build_report(out, plus, sales, 'quick_check_v39', confirm_save=True)
assert report.plus_rows and report.sales_summary and report.sales_details, '엑셀 파싱 결과가 비어 있습니다.'
assert report.performance_scores and report.performance_scores[0]['sent_count'] == 300, report.performance_scores
assert Path(report.files['html_path']).exists()
assert Path(report.files['zip_path']).exists()
print('v39 카카오 스튜디오 엑셀 성과 학습 검사 PASS')
print('plus_rows', len(report.plus_rows), 'sales_details', len(report.sales_details), 'scores', len(report.performance_scores))
