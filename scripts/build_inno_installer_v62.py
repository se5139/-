from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

APP_EXE = "KakaoEmoticonSetup_v62.exe"
SCRIPT_NAME = "KakaoEmoticonSetup_v62.iss"


def unique(paths):
    out=[]; seen=set()
    for p in paths:
        if not p:
            continue
        try:
            s=str(Path(str(p).strip('"')).expanduser())
        except Exception:
            continue
        k=s.lower()
        if k not in seen:
            seen.add(k); out.append(Path(s))
    return out


def resolve_shortcut_target(lnk: Path) -> str | None:
    if os.name != "nt" or not lnk.exists():
        return None
    ps = (
        "$p=[Console]::In.ReadToEnd().Trim(); "
        "$ws=New-Object -ComObject WScript.Shell; "
        "$s=$ws.CreateShortcut($p); "
        "Write-Output $s.TargetPath"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            input=str(lnk), text=True, capture_output=True, timeout=15,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().splitlines()[-1].strip() or None
    except Exception:
        return None
    return None


def find_inno_compilers() -> list[Path]:
    env=os.environ; candidates=[]
    for name in ["ISCC", "ISCC_EXE", "ISCC_PATH", "INNO_SETUP_ISCC"]:
        v=env.get(name)
        if v: candidates.append(Path(v.strip('"')))
    for name in ["INNO_SETUP_DIR", "INNOSETUP_DIR"]:
        v=env.get(name)
        if v:
            base=Path(v.strip('"'))
            candidates += [base/"ISCC.exe", base/"Compil32.exe"]
    for exe in ["ISCC.exe", "ISCC", "Compil32.exe", "Compil32"]:
        w=shutil.which(exe)
        if w: candidates.append(Path(w))
    roots=[]
    for key in ["ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA", "APPDATA", "USERPROFILE"]:
        v=env.get(key)
        if v: roots.append(Path(v))
    common=[]
    for root in roots:
        common += [
            root/"Inno Setup 6", root/"Inno Setup 5",
            root/"Programs"/"Inno Setup 6", root/"Programs"/"Inno Setup 5",
            root/"AppData"/"Local"/"Programs"/"Inno Setup 6",
            root/"AppData"/"Local"/"Programs"/"Inno Setup 5",
        ]
    for base in [Path("C:/Program Files (x86)"), Path("C:/Program Files")]:
        common += [base/"Inno Setup 6", base/"Inno Setup 5"]
    for d in unique(common):
        candidates += [d/"ISCC.exe", d/"Compil32.exe"]
    user=Path.home()
    shortcut_dirs=[user/"Desktop", user/"OneDrive"/"Desktop", user/"OneDrive"/"바탕 화면", user/"바탕 화면"]
    appdata=env.get("APPDATA")
    if appdata:
        shortcut_dirs.append(Path(appdata)/"Microsoft"/"Windows"/"Start Menu"/"Programs")
    for d in unique(shortcut_dirs):
        if d.exists():
            for lnk in list(d.rglob("*Inno*Setup*.lnk"))[:50]:
                target=resolve_shortcut_target(lnk)
                if target:
                    tp=Path(target)
                    candidates += [tp, tp.parent/"ISCC.exe", tp.parent/"Compil32.exe"]
    valid=[]
    for p in unique(candidates):
        try:
            if p.exists() and p.is_file() and p.name.lower() in {"iscc.exe", "compil32.exe"}:
                valid.append(p)
        except Exception:
            pass
    valid.sort(key=lambda x: (0 if x.name.lower()=="iscc.exe" else 1, len(str(x))))
    return valid


def infer_paths(root_arg: str | None, iss_arg: str | None) -> tuple[Path, Path]:
    script_path = Path(__file__).resolve()
    inferred_root = script_path.parents[1]
    root = Path(root_arg).resolve() if root_arg else inferred_root
    if iss_arg:
        iss = Path(iss_arg).resolve()
    else:
        preferred = root/"installer"/SCRIPT_NAME
        if preferred.exists():
            iss = preferred
        else:
            # Fallback for accidental direct runs in old package folders.
            matches = sorted((root/"installer").glob("KakaoEmoticonSetup_v*.iss")) if (root/"installer").exists() else []
            iss = matches[-1] if matches else preferred
    return root, iss


def build(root: Path, iss: Path) -> dict:
    report={"time": datetime.now().isoformat(timespec="seconds"), "root": str(root), "iss": str(iss), "ok": False, "errors": [], "candidates": []}
    if not root.exists():
        report["errors"].append("root folder does not exist")
        return report
    if not iss.exists():
        report["errors"].append("iss file does not exist")
        return report
    compilers=find_inno_compilers()
    report["candidates"]=[str(x) for x in compilers]
    if not compilers:
        report["errors"].append("Inno Setup compiler not found. Install Inno Setup 6 or open the .iss file manually with Inno Setup Compiler.")
        return report
    out_dir=iss.parent/"Output"
    out_dir.mkdir(parents=True, exist_ok=True)
    for compiler in compilers:
        cmd=[str(compiler), str(iss)] if compiler.name.lower()=="iscc.exe" else [str(compiler), "/cc", str(iss)]
        report["used"] = str(compiler); report["cmd"] = cmd
        try:
            res=subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=900)
            report["last_result"]={"returncode": res.returncode, "stdout_tail": res.stdout[-4000:], "stderr_tail": res.stderr[-4000:]}
            exe=out_dir/APP_EXE
            if res.returncode==0 and exe.exists() and exe.stat().st_size>0:
                report.update({"ok": True, "output": str(exe), "output_size": exe.stat().st_size})
                return report
        except Exception as e:
            report["last_result"]={"exception": repr(e)}
    report["errors"].append("Inno Setup build failed with detected compiler candidates")
    return report


def main(argv: list[str] | None = None) -> int:
    ap=argparse.ArgumentParser(description="Build the Kakao Emoticon v62 Windows installer. Arguments are optional; paths are inferred when omitted.")
    ap.add_argument("--root", required=False)
    ap.add_argument("--iss", required=False)
    args=ap.parse_args(argv)
    root, iss = infer_paths(args.root, args.iss)
    report=build(root, iss)
    report_path=iss.parent/"v62_inno_build_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report.get("ok"):
        print("\n[v62] Build failed or compiler not found.")
        print("[v62] Fix 1: install Inno Setup 6 including command-line compiler.")
        print("[v62] Fix 2: run OPEN_V62_INNO_SCRIPT.bat and compile from the Inno Setup window.")
        print("[v62] Fix 3: set ISCC_PATH to the full path of ISCC.exe, then run this again.")
        return 1
    print("\n[v62] Installer EXE created successfully.")
    print(f"[v62] Output: {report.get('output')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
