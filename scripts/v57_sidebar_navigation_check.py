from __future__ import annotations
import ast, json, re, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = root / "app.py"
const = root / "modules" / "constants.py"
results = []

def add(name, ok, detail=""):
    results.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

text = app.read_text(encoding="utf-8")
try:
    ast.parse(text)
    add("app.py AST syntax", True)
except Exception as exc:
    add("app.py AST syntax", False, repr(exc))

add("uses PAGE_LABELS", "PAGE_LABELS =" in text)
add("removed top main_tabs navigation", "main_tabs" not in text and "main_tabs = st.tabs" not in text)
add("sidebar radio navigation", "st.sidebar" in text and "st.radio" in text and "v57_sidebar_page_radio" in text)
add("navigation search", "v57_nav_search" in text and "메뉴 검색" in text)
add("49 page labels", text.count('selected_page_index == ') == 49, f"count={text.count('selected_page_index == ')}")
add("short caption", "전체 기능 이력 보기" in text and "좌측 세로 메뉴" in text)
ct = const.read_text(encoding="utf-8")
add("version constants", 'v57' in ct and '57.0.0' in ct)

# no dangerous deletion in UI patch
bad_patterns = ["Remove-Item", "rmtree(", "shutil.rmtree"]
add("no deletion logic added to app", not any(p in text for p in bad_patterns))

out = root / "outputs" / "v57_sidebar_navigation_check_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
failed = [r for r in results if r["status"] != "PASS"]
print(json.dumps(results, ensure_ascii=False, indent=2))
if failed:
    sys.exit(1)
