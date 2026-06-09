from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

APP_EXE = "KakaoEmoticonSetup_v90.exe"
SCRIPT_NAME = "KakaoEmoticonSetup_v90.iss"
REPORT_NAME = "v90_inno_build_report.json"

def say(msg: str) -> None:
    print(msg, flush=True)

def norm_path(value: str | Path | None) -> Path | None:
    if not value:
        return None
    try:
        return Path(str(value).strip().strip('"')).expanduser()
    except Exception:
        return None

def unique(paths):
    out=[]; seen=set()
    for p in paths:
        pp=norm_path(p)
        if not pp:
            continue
        key=str(pp).lower()
        if key not in seen:
            seen.add(key); out.append(pp)
    return out

def find_inno_compilers() -> list[Path]:
    say("[v90] Searching for Inno Setup compiler...")
    env=os.environ
    candidates=[]

    say("[v90] Checking environment variables and PATH...")
    for name in ["ISCC", "ISCC_EXE", "ISCC_PATH", "INNO_SETUP_ISCC"]:
        if env.get(name):
            candidates.append(env[name])
    for name in ["INNO_SETUP_DIR", "INNOSETUP_DIR"]:
        if env.get(name):
            base=norm_path(env[name])
            if base:
                candidates += [base/"ISCC.exe", base/"Compil32.exe"]
    for exe in ["ISCC.exe", "ISCC", "Compil32.exe", "Compil32"]:
        w=shutil.which(exe)
        if w:
            candidates.append(w)

    say("[v90] Checking standard install folders...")
    roots=[]
    for key in ["ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA", "APPDATA", "USERPROFILE"]:
        if env.get(key):
            roots.append(Path(env[key]))
    common=[]
    for root in roots:
        common += [
            root/"Inno Setup 6", root/"Inno Setup 5",
            root/"Programs"/"Inno Setup 6", root/"Programs"/"Inno Setup 5",
            root/"AppData"/"Local"/"Programs"/"Inno Setup 6",
            root/"AppData"/"Local"/"Programs"/"Inno Setup 5",
        ]
    common += [Path("C:/Program Files (x86)/Inno Setup 6"), Path("C:/Program Files/Inno Setup 6"), Path("C:/Program Files (x86)/Inno Setup 5"), Path("C:/Program Files/Inno Setup 5")]
    for base in unique(common):
        candidates += [base/"ISCC.exe", base/"Compil32.exe"]

    say("[v90] Checking known desktop/start-menu shortcut target folders only, without recursive scan...")
    # Avoid slow recursive shortcut scans. If the compiler is still not found, the user can open the .iss file manually.
    valid=[]
    for p in unique(candidates):
        try:
            if p.exists() and p.is_file() and p.name.lower() in {"iscc.exe", "compil32.exe"}:
                valid.append(p.resolve())
        except Exception:
            pass
    valid=unique(valid)
    valid.sort(key=lambda x: (0 if x.name.lower()=="iscc.exe" else 1, len(str(x))))
    say(f"[v90] Compiler candidates found: {len(valid)}")
    for v in valid[:8]:
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
        matches = sorted((root/"installer").glob("KakaoEmoticonSetup_v*.iss")) if (root/"installer").exists() else []
        iss = preferred if preferred.exists() else (matches[-1] if matches else preferred)
    return root, iss

def stream_process(cmd: list[str], cwd: Path, timeout: int=900) -> tuple[int, str]:
    say("[v90] Running compiler command:")
    say("[v90] " + " ".join('"'+x+'"' if ' ' in x else x for x in cmd))
    proc=subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1)
    start=time.time()
    lines=[]; last=start
    try:
        while True:
            if proc.stdout is None:
                break
            line=proc.stdout.readline()
            if line:
                line=line.rstrip("\n")
                lines.append(line)
                say(line)
                last=time.time()
            elif proc.poll() is not None:
                break
            else:
                if time.time()-last > 15:
                    say("[v90] Still working... waiting for compiler output.")
                    last=time.time()
                if time.time() - start > timeout:
                    proc.kill()
                    return 124, "\n".join(lines + ["TIMEOUT"])
                time.sleep(0.2)
    finally:
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    return proc.returncode or 0, "\n".join(lines)

def build(root: Path, iss: Path) -> dict:
    report={"time": datetime.now().isoformat(timespec="seconds"), "version": "88", "root": str(root), "iss": str(iss), "ok": False, "errors": [], "candidates": []}
    say("============================================================")
    say("[v90] Kakao Emoticon installer build started.")
    say("[v90] This is a STEP-BY-STEP visible build. It should not look frozen.")
    say("============================================================")
    say(f"[v90] Root: {root}")
    say(f"[v90] Inno script: {iss}")
    if not root.exists():
        report["errors"].append("Root folder does not exist."); say("[v90][ERROR] Root folder does not exist."); return report
    if not iss.exists():
        report["errors"].append("Inno .iss file does not exist."); say("[v90][ERROR] Inno .iss file does not exist."); return report
    out_dir=iss.parent/"Output"; out_dir.mkdir(parents=True, exist_ok=True)
    compilers=find_inno_compilers(); report["candidates"]=[str(x) for x in compilers]
    if not compilers:
        msg="Inno Setup compiler was not found. Use _advanced_tools/advanced_bat/OPEN_V90_INNO_SCRIPT.bat or install Inno Setup 6 with command-line compiler."
        report["errors"].append(msg); say("[v90][ERROR] " + msg); return report
    for compiler in compilers:
        say("------------------------------------------------------------")
        say(f"[v90] Trying compiler: {compiler}")
        cmd=[str(compiler), str(iss)] if compiler.name.lower()=="iscc.exe" else [str(compiler), "/cc", str(iss)]
        report["used"] = str(compiler); report["cmd"] = cmd
        try:
            code, output = stream_process(cmd, root)
            report["last_result"]={"returncode": code, "output_tail": output[-6000:]}
            say(f"[v90] Compiler return code: {code}")
            exe=out_dir/APP_EXE
            if code==0 and exe.exists() and exe.stat().st_size>0:
                report.update({"ok": True, "output": str(exe), "output_size": exe.stat().st_size})
                say("[v90] Installer EXE created successfully.")
                say(f"[v90] Output: {exe}")
                return report
            else:
                say("[v90] Output EXE was not found after this compiler attempt.")
        except Exception as e:
            report["last_result"]={"exception": repr(e)}
            say(f"[v90][ERROR] Exception while running compiler: {e!r}")
    report["errors"].append("Build failed with all detected compiler candidates.")
    return report

def main(argv: list[str] | None = None) -> int:
    ap=argparse.ArgumentParser(description="Build the Kakao Emoticon v90 Windows installer with visible step logs.")
    ap.add_argument("--root", required=False)
    ap.add_argument("--iss", required=False)
    args=ap.parse_args(argv)
    root, iss = infer_paths(args.root, args.iss)
    report=build(root, iss)
    report_path=iss.parent/REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    say(f"[v90] Build report: {report_path}")
    if not report.get("ok"):
        say("")
        say("[v90] Build failed or compiler not found.")
        say("[v90] Next actions:")
        say("  1. Run _advanced_tools/advanced_bat/OPEN_V90_INNO_SCRIPT.bat and click Build > Compile.")
        say("  2. Or install Inno Setup 6 and run this BAT again.")
        say("  3. Send installer\\v90_inno_build_report.json if it fails again.")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
