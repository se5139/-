from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--yes", action="store_true"); ap.add_argument("--current-version", default="83")
    args=ap.parse_args()
    report={"version":"83","time":datetime.now().isoformat(timespec="seconds"),"mode":"safe-placeholder","message":"Old-version cleanup is intentionally conservative. User data folders are not deleted.","current_version":args.current_version,"yes":args.yes}
    out=Path("outputs")/"cleanup"/"v84_cleanup_report.json"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
