from __future__ import annotations
import json, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
results=[]
def add(name, ok, detail=""):
    results.append({"name":name,"status":"PASS" if ok else "FAIL","detail":detail})
for rel in ["installer/KakaoEmoticonSetup_v57.iss","BUILD_V57_SETUP_EXE.bat","OPEN_V57_INNO_SCRIPT.bat","scripts/create_shortcuts_v57.py","scripts/cleanup_old_versions_v57.py","scripts/build_inno_installer_v57.py"]:
    add(f"exists:{rel}",(root/rel).exists())
iss=(root/"installer/KakaoEmoticonSetup_v57.iss").read_text(encoding="utf-8")
add("installer output v57","KakaoEmoticonSetup_v57" in iss)
add("installer app dir v57","KakaoEmoticonProfitSystemV57" in iss)
add("installer run label v57","Run Kakao Emoticon Profit System v57" in iss)
add("installer cleanup v57","run_cleanup_old_versions_v57.bat" in iss)
build=(root/"BUILD_V57_SETUP_EXE.bat").read_text(encoding="utf-8", errors="ignore")
add("build uses v57 helper","build_inno_installer_v57.py" in build and "KakaoEmoticonSetup_v57.iss" in build)
install=(root/"1_INSTALL_NOW.bat").read_text(encoding="utf-8", errors="ignore")
add("portable installer target v57","KakaoEmoticonProfitSystemV57" in install and "KakaoEmoticonV57" in install)
shortcut=(root/"3_CREATE_SHORTCUTS_ONLY.bat").read_text(encoding="utf-8", errors="ignore")
add("shortcut helper v57","create_shortcuts_v57.py" in shortcut)
# ASCII for BATs and ISS
for rel in ["0_BUILD_WINDOWS_INSTALLER_EXE.bat","BUILD_V57_SETUP_EXE.bat","OPEN_V57_INNO_SCRIPT.bat","3_CREATE_SHORTCUTS_ONLY.bat","1_INSTALL_NOW.bat","installer/KakaoEmoticonSetup_v57.iss"]:
    try:
        (root/rel).read_bytes().decode("ascii")
        add(f"ascii:{rel}", True)
    except Exception as exc:
        add(f"ascii:{rel}", False, repr(exc))
out=root/"outputs"/"v57_installer_token_check_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))
if any(r["status"]!="PASS" for r in results):
    sys.exit(1)
