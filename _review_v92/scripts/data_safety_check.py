from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.data_safety import DataSafetyManager

if __name__ == "__main__":
    manager = DataSafetyManager()
    dirs = manager.ensure_user_data_dirs(ROOT)
    report = manager.create_backup(root=ROOT, project_name="safety_check_backup", output_dir=ROOT / "outputs" / "data_safety")
    verify = manager.verify_backup(report.backup_zip_path, output_dir=ROOT / "outputs" / "data_safety", project_name="safety_check_verify")
    print("USER_DATA_DIRS")
    for k, v in dirs.items():
        print(k, v)
    print("BACKUP", report.backup_zip_path, report.overall_status, report.score)
    print("VERIFY", verify.overall_status, verify.score)
