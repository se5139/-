from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class DataSafetyItem:
    category: str
    name: str
    status: str
    message: str
    path: str = ""
    size_bytes: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DataSafetyReport:
    created_at: str
    project_name: str
    action: str
    overall_status: str
    score: int
    backup_zip_path: str = ""
    manifest_path: str = ""
    html_path: str = ""
    json_path: str = ""
    csv_path: str = ""
    backup_sha256: str = ""
    protected_paths: list[str] | None = None
    items: list[DataSafetyItem] | None = None
    recommended_actions: list[str] | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["items"] = [item.to_dict() for item in (self.items or [])]
        return data


class DataSafetyManager:
    """데이터 보호/백업/마이그레이션 관리자.

    원칙:
    - 프로그램 코드와 사용자 데이터는 분리합니다.
    - 업데이트 전에는 반드시 백업 ZIP을 먼저 만듭니다.
    - 복구는 기본적으로 별도 폴더에 안전 복원합니다. 기존 데이터 덮어쓰기는 사용자가 수동 확인해야 합니다.
    - 백업 ZIP에는 manifest.json과 SHA-256 검증값을 함께 기록합니다.
    """

    EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "backups", "backup_archives"}
    DEFAULT_PROTECTED_NAMES = ["outputs", "projects", "data", "settings", "user_data"]

    def default_user_data_dir(self, app_folder: str = "KakaoEmoticonProfitSystem") -> Path:
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            return base / app_folder / "UserData"
        return Path.home() / ".kakao_emoticon_profit_system" / "UserData"

    def ensure_user_data_dirs(self, root: str | Path = ".") -> dict[str, str]:
        root = Path(root).resolve()
        user_data = self.default_user_data_dir()
        folders = {
            "user_data": user_data,
            "projects": user_data / "projects",
            "outputs": user_data / "outputs",
            "backups": user_data / "backups",
            "settings": user_data / "settings",
            "migration_logs": user_data / "migration_logs",
        }
        for folder in folders.values():
            folder.mkdir(parents=True, exist_ok=True)
        # 로컬 outputs는 기존 기능 호환을 위해 유지합니다.
        (root / "outputs").mkdir(parents=True, exist_ok=True)
        return {k: str(v) for k, v in folders.items()}

    def collect_protected_paths(self, root: str | Path = ".", extra_paths: Iterable[str | Path] | None = None) -> list[Path]:
        root = Path(root).resolve()
        paths: list[Path] = []
        for name in self.DEFAULT_PROTECTED_NAMES:
            p = root / name
            if p.exists():
                paths.append(p)
        user_data = self.default_user_data_dir()
        if user_data.exists():
            paths.append(user_data)
        for item in extra_paths or []:
            p = Path(item).expanduser().resolve()
            if p.exists():
                paths.append(p)
        # 중복 제거
        unique: list[Path] = []
        seen = set()
        for p in paths:
            key = str(p)
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique

    def create_backup(
        self,
        root: str | Path = ".",
        backup_root: str | Path | None = None,
        project_name: str = "kakao_emoticon_project",
        extra_paths: Iterable[str | Path] | None = None,
        output_dir: str | Path | None = None,
    ) -> DataSafetyReport:
        root = Path(root).resolve()
        self.ensure_user_data_dirs(root)
        protected = self.collect_protected_paths(root, extra_paths)
        if backup_root is None:
            backup_root = self.default_user_data_dir() / "backups"
        backup_root = Path(backup_root).expanduser().resolve()
        backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._safe_filename(project_name)
        backup_zip = backup_root / f"{safe_name}_backup_{stamp}.zip"

        manifest = {
            "project_name": project_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "root": str(root),
            "protected_paths": [str(p) for p in protected],
            "files": [],
            "notes": [
                "프로그램 업데이트 전 자동 백업",
                "복구 시 기존 데이터 직접 덮어쓰기보다 별도 폴더 복원을 우선 권장",
            ],
        }
        items: list[DataSafetyItem] = []
        seen_archive_names: set[str] = set()
        with zipfile.ZipFile(backup_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for base in protected:
                if base.is_file():
                    self._add_file_to_zip(zf, base, root, manifest, items, seen_archive_names)
                else:
                    for file in base.rglob("*"):
                        if not file.is_file():
                            continue
                        if any(part in self.EXCLUDE_DIRS for part in file.parts):
                            continue
                        self._add_file_to_zip(zf, file, root, manifest, items, seen_archive_names)
            zf.writestr("_backup_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        sha = self.sha256_file(backup_zip)
        sha_path = backup_zip.with_suffix(backup_zip.suffix + ".sha256.txt")
        sha_path.write_text(f"{sha}  {backup_zip.name}\n", encoding="utf-8")

        if not items:
            items.append(DataSafetyItem("Backup", "No user files", "WARN", "백업 대상 사용자 데이터가 거의 없습니다.", str(root)))
        items.append(DataSafetyItem("Backup", "Backup ZIP", "PASS", "백업 ZIP 생성 완료", str(backup_zip), backup_zip.stat().st_size))
        items.append(DataSafetyItem("Integrity", "SHA-256", "PASS", sha, str(sha_path)))
        report = self._make_report(
            project_name=project_name,
            action="backup",
            items=items,
            protected_paths=[str(p) for p in protected],
            backup_zip_path=str(backup_zip),
            backup_sha256=sha,
        )
        self._write_report(report, output_dir or (root / "outputs" / "data_safety"))
        return report

    def verify_backup(self, backup_zip_path: str | Path, output_dir: str | Path | None = None, project_name: str = "backup_verify") -> DataSafetyReport:
        backup_zip = Path(backup_zip_path).expanduser().resolve()
        items: list[DataSafetyItem] = []
        if not backup_zip.exists():
            items.append(DataSafetyItem("Verify", "Backup ZIP", "FAIL", "백업 파일이 없습니다.", str(backup_zip)))
            report = self._make_report(project_name, "verify", items, backup_zip_path=str(backup_zip))
            self._write_report(report, output_dir or Path("outputs/data_safety"))
            return report
        sha = self.sha256_file(backup_zip)
        try:
            with zipfile.ZipFile(backup_zip, "r") as zf:
                bad = zf.testzip()
                names = zf.namelist()
                has_manifest = "_backup_manifest.json" in names
                if bad:
                    items.append(DataSafetyItem("Verify", "ZIP integrity", "FAIL", f"손상된 파일 발견: {bad}", str(backup_zip)))
                else:
                    items.append(DataSafetyItem("Verify", "ZIP integrity", "PASS", "ZIP 무결성 검사 통과", str(backup_zip), backup_zip.stat().st_size))
                items.append(DataSafetyItem("Verify", "Manifest", "PASS" if has_manifest else "WARN", "manifest 확인" if has_manifest else "manifest 없음", str(backup_zip)))
                items.append(DataSafetyItem("Verify", "File count", "PASS", f"{len(names)}개 항목 포함", str(backup_zip)))
        except Exception as exc:
            items.append(DataSafetyItem("Verify", "Open ZIP", "FAIL", f"ZIP 열기 실패: {exc}", str(backup_zip)))
        items.append(DataSafetyItem("Integrity", "SHA-256", "PASS", sha, str(backup_zip)))
        report = self._make_report(project_name, "verify", items, backup_zip_path=str(backup_zip), backup_sha256=sha)
        self._write_report(report, output_dir or Path("outputs/data_safety"))
        return report

    def restore_backup_safe(
        self,
        backup_zip_path: str | Path,
        restore_root: str | Path | None = None,
        output_dir: str | Path | None = None,
        project_name: str = "backup_restore",
    ) -> DataSafetyReport:
        backup_zip = Path(backup_zip_path).expanduser().resolve()
        if restore_root is None:
            restore_root = self.default_user_data_dir() / "restored_backups"
        restore_root = Path(restore_root).expanduser().resolve()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = restore_root / f"restore_{stamp}"
        items: list[DataSafetyItem] = []
        if not backup_zip.exists():
            items.append(DataSafetyItem("Restore", "Backup ZIP", "FAIL", "백업 파일이 없습니다.", str(backup_zip)))
            report = self._make_report(project_name, "restore", items, backup_zip_path=str(backup_zip))
            self._write_report(report, output_dir or Path("outputs/data_safety"))
            return report
        target.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(backup_zip, "r") as zf:
                zf.extractall(target)
            items.append(DataSafetyItem("Restore", "Safe restore", "PASS", "기존 데이터를 덮어쓰지 않고 별도 폴더에 복원 완료", str(target)))
            items.append(DataSafetyItem("Restore", "Manual review", "WARN", "복원된 파일을 확인한 뒤 필요한 파일만 수동으로 옮기세요.", str(target)))
        except Exception as exc:
            items.append(DataSafetyItem("Restore", "Extract", "FAIL", f"복원 실패: {exc}", str(target)))
        report = self._make_report(project_name, "restore", items, backup_zip_path=str(backup_zip))
        self._write_report(report, output_dir or Path("outputs/data_safety"))
        return report

    def migrate_from_old_version(
        self,
        old_root: str | Path,
        new_root: str | Path = ".",
        output_dir: str | Path | None = None,
        project_name: str = "version_migration",
    ) -> DataSafetyReport:
        old_root = Path(old_root).expanduser().resolve()
        new_root = Path(new_root).expanduser().resolve()
        items: list[DataSafetyItem] = []
        if not old_root.exists():
            items.append(DataSafetyItem("Migration", "Old version folder", "FAIL", "구버전 폴더가 없습니다.", str(old_root)))
            report = self._make_report(project_name, "migration", items)
            self._write_report(report, output_dir or (new_root / "outputs" / "data_safety"))
            return report
        # 구버전 먼저 백업
        backup_report = self.create_backup(root=old_root, project_name=f"{project_name}_pre_migration", output_dir=output_dir or (new_root / "outputs" / "data_safety"))
        items.append(DataSafetyItem("Migration", "Pre-migration backup", "PASS", "구버전 데이터 백업 생성", backup_report.backup_zip_path))
        user_data = self.default_user_data_dir()
        user_data.mkdir(parents=True, exist_ok=True)
        copied = 0
        for name in self.DEFAULT_PROTECTED_NAMES:
            src = old_root / name
            if not src.exists() or name in {"backups"}:
                continue
            dst = user_data / name
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
            else:
                for file in src.rglob("*"):
                    if not file.is_file() or any(part in self.EXCLUDE_DIRS for part in file.parts):
                        continue
                    rel = file.relative_to(src)
                    target = dst / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        shutil.copy2(file, target)
                        copied += 1
        items.append(DataSafetyItem("Migration", "Copied files", "PASS" if copied else "WARN", f"{copied}개 파일을 사용자 데이터 폴더로 이전", str(user_data)))
        report = self._make_report(project_name, "migration", items, protected_paths=[str(user_data)])
        self._write_report(report, output_dir or (new_root / "outputs" / "data_safety"))
        return report

    def _add_file_to_zip(self, zf: zipfile.ZipFile, file: Path, root: Path, manifest: dict, items: list[DataSafetyItem], seen_archive_names: set[str] | None = None) -> None:
        try:
            try:
                arc = file.relative_to(root)
                arcname = Path("project_root") / arc
            except ValueError:
                arcname = Path("external_user_data") / file.name if file.is_file() else Path("external_user_data") / file.relative_to(file.anchor)
            archive_name = str(arcname).replace("\\", "/")
            if seen_archive_names is not None:
                if archive_name in seen_archive_names:
                    return
                seen_archive_names.add(archive_name)
            info = {
                "path": str(file),
                "archive_name": archive_name,
                "size_bytes": file.stat().st_size,
                "sha256": self.sha256_file(file),
                "modified_at": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
            manifest["files"].append(info)
            zf.write(file, archive_name)
            items.append(DataSafetyItem("BackupFile", file.name, "PASS", "백업 포함", str(file), file.stat().st_size))
        except Exception as exc:
            items.append(DataSafetyItem("BackupFile", file.name, "WARN", f"백업 제외: {exc}", str(file)))

    @staticmethod
    def sha256_file(path: str | Path) -> str:
        h = hashlib.sha256()
        with Path(path).open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _safe_filename(name: str) -> str:
        allowed = []
        for ch in name.strip() or "project":
            if ch.isalnum() or ch in "-_()[]가-힣 ":
                allowed.append(ch)
            else:
                allowed.append("_")
        return "".join(allowed).strip().replace(" ", "_")[:80]

    def _make_report(
        self,
        project_name: str,
        action: str,
        items: list[DataSafetyItem],
        protected_paths: list[str] | None = None,
        backup_zip_path: str = "",
        backup_sha256: str = "",
    ) -> DataSafetyReport:
        fail = sum(1 for i in items if i.status == "FAIL")
        warn = sum(1 for i in items if i.status == "WARN")
        score = max(0, 100 - fail * 25 - warn * 8)
        if fail:
            status = "수정 필요"
        elif warn:
            status = "주의"
        else:
            status = "정상"
        actions = []
        if action == "backup":
            actions.append("기능 추가/업데이트 전 이 백업 ZIP과 SHA-256 파일을 보관하세요.")
        if any(i.status == "WARN" for i in items):
            actions.append("경고 항목을 확인하고, 중요한 프로젝트 파일이 빠지지 않았는지 확인하세요.")
        if any(i.status == "FAIL" for i in items):
            actions.append("실패 항목 해결 전 업데이트/복원을 진행하지 마세요.")
        if not actions:
            actions.append("현재 데이터 보호 검사 기준에서는 큰 문제가 발견되지 않았습니다.")
        return DataSafetyReport(
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project_name=project_name,
            action=action,
            overall_status=status,
            score=score,
            backup_zip_path=backup_zip_path,
            backup_sha256=backup_sha256,
            protected_paths=protected_paths or [],
            items=items,
            recommended_actions=actions,
        )

    def _write_report(self, report: DataSafetyReport, output_dir: str | Path) -> DataSafetyReport:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        base = f"data_safety_{report.action}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        json_path = out / f"{base}.json"
        html_path = out / f"{base}.html"
        csv_path = out / f"{base}.csv"
        data = report.to_dict()
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["category", "name", "status", "message", "path", "size_bytes"])
            writer.writeheader()
            for item in report.items or []:
                writer.writerow(item.to_dict())
        html_path.write_text(self._render_html(report), encoding="utf-8")
        report.json_path = str(json_path)
        report.html_path = str(html_path)
        report.csv_path = str(csv_path)
        return report

    @staticmethod
    def _render_html(report: DataSafetyReport) -> str:
        rows = []
        for item in report.items or []:
            color = {"PASS": "#e8fff0", "WARN": "#fff8d8", "FAIL": "#ffe8e8"}.get(item.status, "#fff")
            rows.append(
                f"<tr style='background:{color}'><td>{item.category}</td><td>{item.name}</td><td><b>{item.status}</b></td><td>{item.message}</td><td>{item.path}</td><td>{item.size_bytes}</td></tr>"
            )
        paths = "".join(f"<li>{p}</li>" for p in (report.protected_paths or [])) or "<li>기록 없음</li>"
        actions = "".join(f"<li>{a}</li>" for a in (report.recommended_actions or []))
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>Data Safety Report</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:32px;line-height:1.55}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px;font-size:13px}}th{{background:#333;color:white}}code{{background:#f4f4f4;padding:2px 5px;border-radius:4px}}</style></head><body>
<h1>카카오 이모티콘 수익화 시스템 v19 데이터 보호 리포트</h1>
<p><b>생성일:</b> {report.created_at}</p>
<p><b>프로젝트:</b> {report.project_name} · <b>작업:</b> {report.action}</p>
<p><b>상태:</b> {report.overall_status} · <b>점수:</b> {report.score}</p>
<p><b>백업 ZIP:</b> <code>{report.backup_zip_path}</code></p>
<p><b>SHA-256:</b> <code>{report.backup_sha256}</code></p>
<h2>보호 대상 경로</h2><ul>{paths}</ul>
<h2>권장 조치</h2><ul>{actions}</ul>
<h2>검사/백업 결과</h2><table><thead><tr><th>분류</th><th>항목</th><th>상태</th><th>메시지</th><th>경로</th><th>크기</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>"""
