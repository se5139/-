from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class CreationLogger:
    def __init__(self, project_dir: str | Path) -> None:
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.project_dir / "creation_log.json"
        if not self.log_path.exists():
            self._write({"events": []})

    def add_event(self, event_type: str, payload: dict[str, Any]) -> None:
        data = self._read()
        data.setdefault("events", []).append(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "type": event_type,
                "payload": payload,
            }
        )
        self._write(data)

    def register_file(self, file_path: str | Path, role: str) -> dict[str, str]:
        path = Path(file_path)
        sha = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
        info = {"role": role, "path": str(path), "sha256": sha}
        self.add_event("file_registered", info)
        return info

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.log_path.read_text(encoding="utf-8"))
        except Exception:
            return {"events": []}

    def _write(self, data: dict[str, Any]) -> None:
        self.log_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
