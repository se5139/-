
from __future__ import annotations
import ast, json, re, sys, zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
results = []
def add(name, ok, detail=""):
    results.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

app = root / "app.py"
const = root / "modules" / "constants.py"
module = root / "modules" / "api_key_safety" / "openai_key_guard.py"
text = app.read_text(encoding="utf-8")
try:
    ast.parse(text); add("app.py AST syntax", True)
except Exception as exc:
    add("app.py AST syntax", False, repr(exc))
try:
    ast.parse(module.read_text(encoding="utf-8")); add("v58 key guard AST syntax", True)
except Exception as exc:
    add("v58 key guard AST syntax", False, repr(exc))
ct = const.read_text(encoding="utf-8")
add("version constants", "v58" in ct and "58.0.0" in ct)
add("v58 page label", "50 API 키 안전보관/교체" in text and "selected_page_index == 49" in text)
add("50 sidebar pages", text.count("selected_page_index == ") == 50, f"count={text.count('selected_page_index == ')}")
add("OpenAI key guard imported", "OpenAIKeySafetyEngine" in text and "ApiKeySafetyConfig" in text)
add("raw key not stored marker", "키 원문은 저장하지 않았습니다" in text and "store_raw_key" in module.read_text(encoding="utf-8"))
add("env var template", "OPENAI_API_KEY" in module.read_text(encoding="utf-8") and "SET_OPENAI_API_KEY_TEMPLATE.bat" in module.read_text(encoding="utf-8"))
add("paid calls default blocked", "paid_calls_allowed: bool = False" in module.read_text(encoding="utf-8"))
# Detect accidental real-looking OpenAI key in project files, excluding regex source/test files that contain patterns only.
secret_re = re.compile(r"(?:sk|sk-proj)-[A-Za-z0-9_\-]{40,}")
leaks = []
for p in root.rglob("*"):
    if p.is_file() and p.suffix.lower() in {".py", ".txt", ".md", ".json", ".csv", ".bat", ".ps1", ".iss"}:
        data = p.read_text(encoding="utf-8", errors="ignore")
        for m in secret_re.finditer(data):
            value = m.group(0)
            if "A-Za-z0-9" in value or "PASTE_NEW_OPENAI" in value:
                continue
            leaks.append(str(p.relative_to(root)))
add("no real OpenAI API key embedded", len(leaks) == 0, ", ".join(leaks[:5]))
add("installer v58 script", (root/"installer"/"KakaoEmoticonSetup_v58.iss").exists())
add("build v58 script", (root/"scripts"/"build_inno_installer_v58.py").exists() and (root/"0_BUILD_WINDOWS_INSTALLER_EXE.bat").exists())

# Smoke test engine without saving raw key.
sys.path.insert(0, str(root))
try:
    from modules.api_key_safety import OpenAIKeySafetyEngine, ApiKeySafetyConfig
    out = root / "outputs" / "v58_api_key_safety_check"
    report = OpenAIKeySafetyEngine().build_report(out, ApiKeySafetyConfig(), openai_api_key="", uploaded_paths=[], notes="local first")
    add("v58 engine smoke test", report["key_status"]["provided"] is False and Path(report["json_path"]).exists())
    saved = Path(report["json_path"]).read_text(encoding="utf-8")
    add("report contains no placeholder real key", "sk-proj-" not in saved and "PASTE_NEW_OPENAI_API_KEY_HERE" not in saved)
except Exception as exc:
    add("v58 engine smoke test", False, repr(exc))

out = root / "outputs" / "v58_api_key_safety_check_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))
failed = [r for r in results if r["status"] != "PASS"]
if failed:
    sys.exit(1)
