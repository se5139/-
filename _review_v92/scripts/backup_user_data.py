from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.data_safety import DataSafetyManager

if __name__ == "__main__":
    manager = DataSafetyManager()
    report = manager.create_backup(root=ROOT, project_name="manual_backup", output_dir=ROOT / "outputs" / "data_safety")
    print("BACKUP_OK", report.backup_zip_path)
    print("SHA256", report.backup_sha256)
    print("REPORT", report.html_path)
