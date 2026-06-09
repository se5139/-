from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


class ProjectExporter:
    def __init__(self, base_dir: str | Path = "outputs") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_project_dir(self, project_name: str) -> Path:
        safe = "".join(c for c in project_name if c.isalnum() or c in "-_ ").strip() or "emoticon_project"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.base_dir / f"{safe}_{stamp}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_json(self, data: dict[str, Any], path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_expressions_csv(self, expressions: list[dict[str, Any]], path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not expressions:
            path.write_text("", encoding="utf-8")
            return path
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(expressions[0].keys()))
            writer.writeheader()
            writer.writerows(expressions)
        return path

    def zip_dir(self, source_dir: str | Path, output_zip_base: str | Path) -> Path:
        zip_path = shutil.make_archive(str(output_zip_base), "zip", str(source_dir))
        return Path(zip_path)
