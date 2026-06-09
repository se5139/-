from __future__ import annotations

import shutil
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "sync_state_payload"


def copy_file_with_backup(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backup = target.with_suffix(target.suffix + f".backup_{time.strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(target, backup)
        print(f"[sync-import] backup: {backup}")
    shutil.copy2(source, target)
    print(f"[sync-import] imported: {target}")


def copy_tree_merge(source_dir: Path, target_dir: Path) -> int:
    copied = 0
    if not source_dir.exists():
        return copied
    for source in source_dir.rglob("*"):
        if not source.is_file():
            continue
        target = target_dir / source.relative_to(source_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    return copied


def main() -> int:
    if not (ROOT / "app.py").exists():
        print("[sync-import] app.py was not found. Extract this ZIP into the app folder first.")
        return 1
    if not PAYLOAD.exists():
        print("[sync-import] sync_state_payload folder was not found.")
        return 1

    memory_payload = PAYLOAD / "memory"
    outputs_payload = PAYLOAD / "outputs"
    for name in ["evolution_memory.json", "api_usage_ledger.json"]:
        source = memory_payload / name
        if source.exists():
            copy_file_with_backup(source, ROOT / "memory" / name)

    copied_outputs = copy_tree_merge(outputs_payload, ROOT / "outputs")
    print(f"[sync-import] output files copied: {copied_outputs}")
    print("[sync-import] complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
