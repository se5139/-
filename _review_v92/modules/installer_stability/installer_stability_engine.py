from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import socket
import sys
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class StabilityCheck:
    category: str
    name: str
    status: str
    message: str
    detail: str = ""
    fix_hint: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class InstallerStabilityEngine:
    """v43 설치형 안정화/실행 오류 진단 엔진.

    목적:
    - 초보자가 설치/실행 중 막혔을 때 원인을 빠르게 확인한다.
    - 사용자 데이터는 코드 폴더와 분리하고 원본을 보존한다.
    - 오류 진단 리포트와 지원용 ZIP을 생성한다.
    """

    REQUIRED_FILES = [
        "app.py",
        "requirements.txt",
        "modules/constants.py",
        "START_WINDOWS.bat",
        "00_STEP_2_PORTABLE_INSTALL_NOW.bat",
        "00_STEP_3_START_PROGRAM.bat",
        "00_STEP_4_SAFE_CLEAN_OLD_VERSIONS.bat",
        "4_REPAIR_ENVIRONMENT.bat",
        "8_BACKUP_USER_DATA.bat",
    ]
    IMPORTANT_PACKAGES = ["streamlit", "pandas", "PIL"]
    DEFAULT_PORTS = [8520, 8521, 8522, 8501]

    def __init__(self, output_base: str | Path):
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        project_root: str | Path,
        run_mode: str = "full",
        app_version: str = "43.0.0",
        ports: Iterable[int] | None = None,
        make_backup: bool = True,
        include_outputs_summary: bool = True,
    ) -> dict:
        root = Path(project_root).resolve()
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = self.output_base / f"installer_stability_{run_id}"
        out_dir.mkdir(parents=True, exist_ok=True)

        checks: list[StabilityCheck] = []
        checks.append(self._check_python())
        checks.append(self._check_os())
        checks.append(self._check_path(root))
        checks.append(self._check_required_files(root))
        checks.append(self._check_requirements(root))
        checks.extend(self._check_packages())
        checks.append(self._check_write_permission(root))
        checks.append(self._check_user_data_location())
        checks.extend(self._check_ports(list(ports or self.DEFAULT_PORTS)))
        checks.append(self._check_launcher_bats(root))
        checks.append(self._check_venv(root))
        if include_outputs_summary:
            checks.append(self._check_outputs_size(root))

        support_files: list[str] = []
        backup_path = ""
        if make_backup:
            backup_path = self._make_light_backup(root, out_dir)
            if backup_path:
                support_files.append(backup_path)
                checks.append(StabilityCheck("Backup", "Light backup", "PASS", "설치 안정화 점검용 경량 백업 생성", backup_path, "정식 작업 전에는 19 데이터 보호/백업 기능으로 전체 백업을 권장합니다."))
            else:
                checks.append(StabilityCheck("Backup", "Light backup", "WARN", "백업 대상 폴더를 찾지 못했거나 백업을 생성하지 못했습니다.", "", "필요하면 8_BACKUP_USER_DATA.bat를 실행하세요."))

        repair_steps = self._build_repair_steps(checks)
        bat_files = self._write_helper_bats(root)
        support_files.extend(bat_files)

        score = self._score(checks)
        status = self._overall_status(checks)
        report = {
            "version": "v43",
            "app_version": app_version,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "project_root": str(root),
            "run_mode": run_mode,
            "overall_status": status,
            "score": score,
            "checks": [c.to_dict() for c in checks],
            "repair_steps": repair_steps,
            "support_files": support_files,
            "backup_path": backup_path,
            "notes": [
                "v43은 설치/실행 안정화와 오류 진단을 위한 단계입니다.",
                "사용자 데이터는 코드 폴더와 분리하고, 업데이트 전 백업을 우선합니다.",
                "자동 복구는 원본 삭제 없이 진단/재설치/포트 정리/로그 수집 중심으로 수행합니다.",
            ],
        }

        json_path = out_dir / "installer_stability_v43.json"
        html_path = out_dir / "installer_stability_v43.html"
        csv_path = out_dir / "installer_stability_v43_checks.csv"
        notes_path = out_dir / "installer_stability_v43_repair_steps.txt"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        csv_path.write_text(self._checks_csv(checks), encoding="utf-8-sig")
        notes_path.write_text("\n".join(f"{i+1}. {step}" for i, step in enumerate(repair_steps)), encoding="utf-8")
        html_path.write_text(self._render_html(report), encoding="utf-8")

        zip_path = out_dir / "installer_stability_v43_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in [json_path, html_path, csv_path, notes_path]:
                zf.write(fp, arcname=fp.name)
            for fp in support_files:
                p = Path(fp)
                if p.exists() and p.is_file():
                    zf.write(p, arcname=f"support/{p.name}")
        report["files"] = {
            "output_dir": str(out_dir),
            "html_path": str(html_path),
            "json_path": str(json_path),
            "csv_path": str(csv_path),
            "notes_path": str(notes_path),
            "zip_path": str(zip_path),
            "zip_sha256": self._sha256(zip_path),
        }
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _check_python(self) -> StabilityCheck:
        version = sys.version_info
        ok = version.major == 3 and version.minor >= 10
        return StabilityCheck(
            "Python",
            "Python version",
            "PASS" if ok else "FAIL",
            f"Python {version.major}.{version.minor}.{version.micro}",
            sys.executable,
            "Python 3.10 이상을 권장합니다." if not ok else "",
        )

    def _check_os(self) -> StabilityCheck:
        sysname = platform.system()
        detail = platform.platform()
        return StabilityCheck("System", "Operating system", "PASS", sysname, detail)

    def _check_path(self, root: Path) -> StabilityCheck:
        path = str(root)
        if len(path) > 180:
            return StabilityCheck("Path", "Install path length", "WARN", "설치 경로가 깁니다.", path, "C:\\KakaoEmoticon 같은 짧은 경로를 권장합니다.")
        if any(ch in path for ch in ["#", "%", "&"]):
            return StabilityCheck("Path", "Special characters", "WARN", "경로에 특수문자가 포함되어 있습니다.", path, "공백/특수문자가 적은 폴더로 옮기면 실행 오류가 줄어듭니다.")
        return StabilityCheck("Path", "Install path", "PASS", "설치 경로 양호", path)

    def _check_required_files(self, root: Path) -> StabilityCheck:
        missing = [name for name in self.REQUIRED_FILES if not (root / name).exists()]
        if missing:
            return StabilityCheck("Project", "Required files", "FAIL", "필수 파일 누락", ", ".join(missing), "ZIP을 새 폴더에 다시 압축 해제하세요.")
        return StabilityCheck("Project", "Required files", "PASS", "필수 파일 확인", str(root))

    def _check_requirements(self, root: Path) -> StabilityCheck:
        req = root / "requirements.txt"
        if not req.exists():
            return StabilityCheck("Project", "requirements.txt", "FAIL", "requirements.txt 없음", str(req), "ZIP을 다시 압축 해제하세요.")
        text = req.read_text(encoding="utf-8", errors="ignore")
        missing_terms = [term for term in ["streamlit", "pandas", "Pillow"] if term.lower() not in text.lower()]
        if missing_terms:
            return StabilityCheck("Project", "requirements.txt", "WARN", "핵심 패키지 명시가 부족할 수 있습니다.", ", ".join(missing_terms), "4_REPAIR_ENVIRONMENT.bat 실행 전 requirements.txt를 확인하세요.")
        return StabilityCheck("Project", "requirements.txt", "PASS", "requirements.txt 확인", str(req))

    def _check_packages(self) -> list[StabilityCheck]:
        results: list[StabilityCheck] = []
        import importlib.util
        for pkg in self.IMPORTANT_PACKAGES:
            ok = importlib.util.find_spec(pkg) is not None
            results.append(StabilityCheck("Package", pkg, "PASS" if ok else "WARN", "설치됨" if ok else "미설치 또는 현재 환경에서 감지 안 됨", "", "00_STEP_2_PORTABLE_INSTALL_NOW.bat 또는 4_REPAIR_ENVIRONMENT.bat 실행" if not ok else ""))
        return results

    def _check_write_permission(self, root: Path) -> StabilityCheck:
        target = root / "outputs" / "v43_write_test"
        try:
            target.mkdir(parents=True, exist_ok=True)
            fp = target / "test.txt"
            fp.write_text("ok", encoding="utf-8")
            fp.unlink(missing_ok=True)
            return StabilityCheck("Permission", "outputs writable", "PASS", "outputs 폴더 쓰기 가능", str(target))
        except Exception as exc:
            return StabilityCheck("Permission", "outputs writable", "FAIL", "outputs 폴더 쓰기 실패", str(exc), "바탕화면/문서 등 권한이 있는 폴더로 이동하세요.")

    def _check_user_data_location(self) -> StabilityCheck:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        user_data = Path(local) / "KakaoEmoticonProfitSystem" / "UserData"
        try:
            user_data.mkdir(parents=True, exist_ok=True)
            return StabilityCheck("Data", "Separated user data folder", "PASS", "사용자 데이터 폴더 확인/생성", str(user_data))
        except Exception as exc:
            return StabilityCheck("Data", "Separated user data folder", "WARN", "사용자 데이터 폴더 생성 실패", str(exc), "프로그램 폴더 내 user_data를 임시로 사용하세요.")

    def _check_ports(self, ports: list[int]) -> list[StabilityCheck]:
        checks: list[StabilityCheck] = []
        for port in ports:
            in_use = self._port_in_use(port)
            checks.append(StabilityCheck("Port", f"127.0.0.1:{port}", "WARN" if in_use else "PASS", "사용 중" if in_use else "사용 가능", "", "7_STOP_PORTS.bat 또는 scripts/stop_port.py로 정리" if in_use else ""))
        return checks

    @staticmethod
    def _port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.3)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    def _check_launcher_bats(self, root: Path) -> StabilityCheck:
        bats = ["00_STEP_2_PORTABLE_INSTALL_NOW.bat", "00_STEP_3_START_PROGRAM.bat", "00_STEP_4_SAFE_CLEAN_OLD_VERSIONS.bat", "4_REPAIR_ENVIRONMENT.bat", "START_WINDOWS.bat"]
        missing = [b for b in bats if not (root / b).exists()]
        if missing:
            return StabilityCheck("Launcher", "BAT launchers", "WARN", "일부 실행/복구 BAT 누락", ", ".join(missing), "ZIP을 다시 압축 해제하거나 v43 보조 BAT를 사용하세요.")
        return StabilityCheck("Launcher", "BAT launchers", "PASS", "실행/복구/백업 BAT 확인", ", ".join(bats))

    def _check_venv(self, root: Path) -> StabilityCheck:
        venv = root / ".venv"
        if not venv.exists():
            return StabilityCheck("Venv", "Virtual environment", "WARN", ".venv 없음", str(venv), "첫 설치 전이면 정상입니다. 00_STEP_2_PORTABLE_INSTALL_NOW.bat 실행 시 생성됩니다.")
        return StabilityCheck("Venv", "Virtual environment", "PASS", ".venv 확인", str(venv))

    def _check_outputs_size(self, root: Path) -> StabilityCheck:
        out = root / "outputs"
        if not out.exists():
            return StabilityCheck("Output", "outputs folder", "WARN", "outputs 폴더가 아직 없습니다.", str(out), "프로그램 실행 후 자동 생성됩니다.")
        total = 0
        count = 0
        for fp in out.rglob("*"):
            if fp.is_file():
                count += 1
                try:
                    total += fp.stat().st_size
                except OSError:
                    pass
        mb = total / (1024 * 1024)
        status = "WARN" if mb > 500 else "PASS"
        hint = "오래된 출력물은 백업 후 정리하세요. 자동 삭제는 하지 않습니다." if status == "WARN" else ""
        return StabilityCheck("Output", "outputs size", status, f"파일 {count}개 · {mb:.1f}MB", str(out), hint)

    def _make_light_backup(self, root: Path, out_dir: Path) -> str:
        targets = [root / "settings", root / "data", root / "user_data"]
        existing = [p for p in targets if p.exists()]
        if not existing:
            return ""
        zip_path = out_dir / "v43_light_user_data_backup.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for base in existing:
                for fp in base.rglob("*"):
                    if fp.is_file():
                        try:
                            zf.write(fp, arcname=str(fp.relative_to(root)))
                        except Exception:
                            pass
        return str(zip_path)

    def _write_helper_bats(self, root: Path) -> list[str]:
        created: list[str] = []
        diag = root / "10_V43_DIAGNOSE_AND_REPAIR.bat"
        diag.write_text(r"""@echo off
chcp 65001 >nul
title Kakao Emoticon Profit System v43 Diagnose
echo [v43] 설치/실행 진단을 시작합니다.
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe scripts\v43_installer_stability_check.py
) else (
  py -3 scripts\v43_installer_stability_check.py
)
pause
""", encoding="utf-8")
        support = root / "11_V43_COLLECT_SUPPORT_PACKAGE.bat"
        support.write_text(r"""@echo off
chcp 65001 >nul
title Kakao Emoticon Profit System v43 Support Package
echo [v43] 진단/지원 패키지를 생성합니다.
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe scripts\v43_installer_stability_check.py --support
) else (
  py -3 scripts\v43_installer_stability_check.py --support
)
pause
""", encoding="utf-8")
        created.extend([str(diag), str(support)])
        return created

    @staticmethod
    def _build_repair_steps(checks: list[StabilityCheck]) -> list[str]:
        steps = []
        if any(c.status == "FAIL" and c.category == "Python" for c in checks):
            steps.append("Python 3.10 이상 설치 후 새 명령 프롬프트에서 다시 실행합니다.")
        if any(c.category == "Package" and c.status in {"WARN", "FAIL"} for c in checks):
            steps.append("00_STEP_2_PORTABLE_INSTALL_NOW.bat 또는 4_REPAIR_ENVIRONMENT.bat를 실행해 패키지를 재설치합니다.")
        if any(c.category == "Port" and c.status == "WARN" for c in checks):
            steps.append("7_STOP_PORTS.bat를 실행하거나, 실행 중인 Streamlit 창을 닫고 다시 시작합니다.")
        if any(c.category == "Permission" and c.status == "FAIL" for c in checks):
            steps.append("프로그램 폴더를 바탕화면/문서/C:\\KakaoEmoticon 같은 쓰기 가능한 경로로 옮깁니다.")
        if any(c.category == "Project" and c.status == "FAIL" for c in checks):
            steps.append("ZIP 파일을 새 폴더에 다시 압축 해제합니다. 기존 UserData는 백업 후 연결합니다.")
        steps.append("업데이트 전에는 8_BACKUP_USER_DATA.bat 또는 19 데이터 보호/백업 탭으로 백업합니다.")
        steps.append("문제가 계속되면 v43 HTML/JSON 리포트와 support ZIP을 보관해 원인 확인에 사용합니다.")
        return steps

    @staticmethod
    def _score(checks: list[StabilityCheck]) -> int:
        fail = sum(1 for c in checks if c.status == "FAIL")
        warn = sum(1 for c in checks if c.status == "WARN")
        return max(0, 100 - fail * 25 - warn * 7)

    @staticmethod
    def _overall_status(checks: list[StabilityCheck]) -> str:
        if any(c.status == "FAIL" for c in checks):
            return "수정 필요"
        if any(c.status == "WARN" for c in checks):
            return "주의"
        return "정상"

    @staticmethod
    def _checks_csv(checks: list[StabilityCheck]) -> str:
        lines = ["category,name,status,message,detail,fix_hint"]
        def esc(v: str) -> str:
            v = str(v or "").replace('"', '""')
            return f'"{v}"'
        for c in checks:
            lines.append(",".join(esc(getattr(c, field)) for field in ["category", "name", "status", "message", "detail", "fix_hint"]))
        return "\n".join(lines)

    @staticmethod
    def _render_html(report: dict) -> str:
        rows = []
        for c in report.get("checks", []):
            color = {"PASS": "#e8fff0", "WARN": "#fff6d8", "FAIL": "#ffe8e8"}.get(c.get("status"), "#fff")
            rows.append(f"<tr style='background:{color}'><td>{c.get('category')}</td><td>{c.get('name')}</td><td><b>{c.get('status')}</b></td><td>{c.get('message')}</td><td>{c.get('detail')}</td><td>{c.get('fix_hint')}</td></tr>")
        steps = "".join(f"<li>{s}</li>" for s in report.get("repair_steps", []))
        notes = "".join(f"<li>{s}</li>" for s in report.get("notes", []))
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v43 설치형 안정화 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:32px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#222;color:#fff}}.box{{padding:16px;background:#f5f7fb;border-radius:12px;margin:12px 0}}</style></head><body>
<h1>카카오 이모티콘 수익화 시스템 v43 설치형 안정화 리포트</h1>
<div class='box'><b>생성일:</b> {report.get('created_at')}<br><b>상태:</b> {report.get('overall_status')} · <b>점수:</b> {report.get('score')}<br><b>프로젝트 경로:</b> {report.get('project_root')}</div>
<h2>권장 복구 순서</h2><ol>{steps}</ol>
<h2>진단 결과</h2><table><thead><tr><th>분류</th><th>항목</th><th>상태</th><th>메시지</th><th>상세</th><th>복구 힌트</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>운영 노트</h2><ul>{notes}</ul>
</body></html>"""

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
