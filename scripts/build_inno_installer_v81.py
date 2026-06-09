from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

APP_EXE = "KakaoEmoticonSetup_v81.exe"
SCRIPT_NAME = "KakaoEmoticonSetup_v81.iss"

def say(msg: str) -> None:
    print(msg, flush=True)

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
            input=str(lnk), text=True, capture_output=True, timeout=10,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().splitlines()[-1].strip() or None
    except Exception:
        return None
    return None

def find_inno_compilers() -> list[Path]:
    say("[v81] Searching for Inno Setup compiler...")
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
    for base in unique(common):
        candidates += [base/"ISCC.exe", base/"Compil32.exe"]

    # Shortcuts can be slow on some PCs, so limit aggressively and print progress.
    user=Path.home()
    shortcut_dirs=[user/"Desktop", user/"OneDrive"/"Desktop", user/"OneDrive"/"바탕 화면", user/"바탕 화면"]
    appdata=env.get("APPDATA")
    if appdata:
        shortcut_dirs.append(Path(appdata)/"Microsoft"/"Windows"/"Start Menu"/"Programs")
    checked_links=0
    for d in unique(shortcut_dirs):
        if d.exists():
            say(f"[v81] Checking shortcuts in: {d}")
            for lnk in list(d.rglob("*Inno*Setup*.lnk"))[:20]:
                checked_links += 1
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
    say(f"[v81] Detected compiler candidates: {len(valid)}")
    for v in valid[:5]:
        say(f"  - {v}")
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
            matches = sorted((root/"installer").glob("KakaoEmoticonSetup_v*.iss")) if (root/"installer").exists() else []
            iss = matches[-1] if matches else preferred
    return root, iss

def build(root: Path, iss: Path) -> dict:
    report={"time": datetime.now().isoformat(timespec="seconds"), "root": str(root), "iss": str(iss), "ok": False, "errors": [], "candidates": []}
    say("[v81] Kakao Emoticon installer build started.")
    say(f"[v81] Root: {root}")
    say(f"[v81] Inno script: {iss}")
    if not root.exists():
        report["errors"].append("root folder does not exist")
        say("[v81][ERROR] Root folder does not exist.")
        return report
    if not iss.exists():
        report["errors"].append("iss file does not exist")
        say("[v81][ERROR] Inno .iss file does not exist.")
        return report
    compilers=find_inno_compilers()
    report["candidates"]=[str(x) for x in compilers]
    if not compilers:
        msg="Inno Setup compiler not found. Install Inno Setup 6 or open the .iss file manually with Inno Setup Compiler."
        report["errors"].append(msg)
        say("[v81][ERROR] " + msg)
        return report
    out_dir=iss.parent/"Output"
    out_dir.mkdir(parents=True, exist_ok=True)
    for compiler in compilers:
        say(f"[v81] Trying compiler: {compiler}")
        cmd=[str(compiler), str(iss)] if compiler.name.lower()=="iscc.exe" else [str(compiler), "/cc", str(iss)]
        report["used"] = str(compiler); report["cmd"] = cmd
        try:
            res=subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=900)
            report["last_result"]={"returncode": res.returncode, "stdout_tail": res.stdout[-4000:], "stderr_tail": res.stderr[-4000:]}
            say(f"[v81] Compiler return code: {res.returncode}")
            if res.stdout.strip():
                say("[v81] Compiler output tail:")
                say(res.stdout[-1200:])
            if res.stderr.strip():
                say("[v81] Compiler error tail:")
                say(res.stderr[-1200:])
            exe=out_dir/APP_EXE
            if res.returncode==0 and exe.exists() and exe.stat().st_size>0:
                report.update({"ok": True, "output": str(exe), "output_size": exe.stat().st_size})
                say("[v81] Installer EXE created successfully.")
                say(f"[v81] Output: {exe}")
                return report
        except subprocess.TimeoutExpired:
            report["last_result"]={"exception": "timeout after 900 seconds"}
            say("[v81][ERROR] Compiler timed out after 900 seconds.")
        except Exception as e:
            report["last_result"]={"exception": repr(e)}
            say(f"[v81][ERROR] Exception while running compiler: {e!r}")
    report["errors"].append("Inno Setup build failed with detected compiler candidates")
    say("[v81][ERROR] Build failed with detected compiler candidates.")
    return report

def main(argv: list[str] | None = None) -> int:
    ap=argparse.ArgumentParser(description="Build the Kakao Emoticon v81 Windows installer. Arguments are optional; paths are inferred when omitted.")
    ap.add_argument("--root", required=False)
    ap.add_argument("--iss", required=False)
    args=ap.parse_args(argv)
    root, iss = infer_paths(args.root, args.iss)
    report=build(root, iss)
    report_path=iss.parent/"v81_inno_build_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    say(f"[v81] Build report: {report_path}")
    if not report.get("ok"):
        say("")
        say("[v81] Build failed or compiler not found.")
        say("[v81] Fix 1: install Inno Setup 6 including command-line compiler.")
        say("[v81] Fix 2: run OPEN_V81_INNO_SCRIPT.bat and compile from the Inno Setup window.")
        say("[v81] Fix 3: set ISCC_PATH to the full path of ISCC.exe, then run this again.")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
