from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.installer_stability import InstallerStabilityEngine
from modules.constants import APP_VERSION


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--support", action="store_true", help="support package mode")
    args = parser.parse_args()
    engine = InstallerStabilityEngine(ROOT / "outputs" / "installer_stability_v43")
    report = engine.run(ROOT, app_version=APP_VERSION, make_backup=True, include_outputs_summary=True, run_mode="support" if args.support else "diagnose")
    print("[v43] overall_status:", report.get("overall_status"))
    print("[v43] score:", report.get("score"))
    print("[v43] html:", report.get("files", {}).get("html_path"))
    print("[v43] zip:", report.get("files", {}).get("zip_path"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
