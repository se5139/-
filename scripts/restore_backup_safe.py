from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.data_safety import DataSafetyManager

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/restore_backup_safe.py <backup_zip_path>")
        raise SystemExit(1)
    manager = DataSafetyManager()
    report = manager.restore_backup_safe(sys.argv[1], output_dir=ROOT / "outputs" / "data_safety")
    print("RESTORE_STATUS", report.overall_status, report.score)
    print("REPORT", report.html_path)
