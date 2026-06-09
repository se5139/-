from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.installer_health.diagnostics import InstallationDiagnostics

report = InstallationDiagnostics().run(project_root=ROOT, app_version='32.0.0', output_dir=ROOT / 'outputs' / 'installer_diagnostics')
print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
print('HTML:', report.html_path)
print('JSON:', report.json_path)
