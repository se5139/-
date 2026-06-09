from __future__ import annotations

import hashlib
import json
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "release"
MEMORY_DIR = ROOT / "memory"
OUTPUTS_DIR = ROOT / "outputs"
EXPORT_LIMIT = 10


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def recent_output_dirs(limit: int = EXPORT_LIMIT) -> list[Path]:
    if not OUTPUTS_DIR.exists():
        return []
    dirs = [path for path in OUTPUTS_DIR.iterdir() if path.is_dir()]
    return sorted(dirs, key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def add_file(archive: zipfile.ZipFile, source: Path, target: Path) -> None:
    if source.exists() and source.is_file():
        archive.write(source, target)


def main() -> int:
    RELEASE_DIR.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    zip_path = RELEASE_DIR / f"sync_state_export_{timestamp}.zip"
    latest_path = RELEASE_DIR / "sync_state_export_latest.zip"
    checksum_path = RELEASE_DIR / f"sync_state_export_{timestamp}.sha256.txt"
    latest_checksum_path = RELEASE_DIR / "sync_state_export_latest.sha256.txt"
    manifest_path = RELEASE_DIR / f"sync_state_export_{timestamp}_manifest.json"
    latest_manifest_path = RELEASE_DIR / "sync_state_export_latest_manifest.json"

    output_dirs = recent_output_dirs()
    manifest = {
        "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "export_type": "kakao_emoticon_v100_sync_state",
        "memory_files": ["memory/evolution_memory.json", "memory/api_usage_ledger.json"],
        "output_dir_limit": EXPORT_LIMIT,
        "output_dirs": [path.name for path in output_dirs],
        "import_entry": "IMPORT_SYNC_STATE.bat",
        "notes": [
            "Extract this ZIP into the app folder, then run IMPORT_SYNC_STATE.bat.",
            "Existing memory files are backed up before import.",
            "Recent outputs are copied into outputs/ without deleting existing outputs.",
        ],
    }

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("SYNC_STATE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        add_file(archive, ROOT / "IMPORT_SYNC_STATE.bat", Path("IMPORT_SYNC_STATE.bat"))
        add_file(archive, ROOT / "scripts" / "import_sync_state.py", Path("scripts/import_sync_state.py"))
        add_file(archive, MEMORY_DIR / "evolution_memory.json", Path("sync_state_payload/memory/evolution_memory.json"))
        add_file(archive, MEMORY_DIR / "api_usage_ledger.json", Path("sync_state_payload/memory/api_usage_ledger.json"))
        for output_dir in output_dirs:
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, Path("sync_state_payload/outputs") / output_dir.name / file_path.relative_to(output_dir))

    checksum = sha256_file(zip_path)
    checksum_path.write_text(f"{checksum}  {zip_path.name}\n", encoding="utf-8")
    manifest.update(
        {
            "zip_name": zip_path.name,
            "zip_size_bytes": zip_path.stat().st_size,
            "sha256": checksum,
        }
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_path.write_bytes(zip_path.read_bytes())
    latest_checksum_path.write_text(f"{checksum}  {latest_path.name}\n", encoding="utf-8")
    latest_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[sync-export] zip: {zip_path}")
    print(f"[sync-export] latest: {latest_path}")
    print(f"[sync-export] outputs included: {len(output_dirs)}")
    print(f"[sync-export] sha256: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
