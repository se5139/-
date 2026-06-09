from __future__ import annotations

import importlib.util
import json
import os
import platform
import socket
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class DiagnosticItem:
    category: str
    name: str
    status: str
    message: str
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiagnosticReport:
    created_at: str
    app_version: str
    overall_status: str
    score: int
    items: list[DiagnosticItem]
    recommended_actions: list[str]
    html_path: str = ""
    json_path: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["items"] = [item.to_dict() for item in self.items]
        return data


class InstallationDiagnostics:
    REQUIRED_PACKAGES = ["streamlit", "pandas", "PIL"]
    DEFAULT_PORTS = [8520, 8521, 8522]

    def run(self, project_root: str | Path = ".", app_version: str = "9.0.0", ports: Iterable[int] | None = None, output_dir: str | Path | None = None) -> DiagnosticReport:
        root = Path(project_root).resolve()
        ports = list(ports or self.DEFAULT_PORTS)
        items: list[DiagnosticItem] = []
        actions: list[str] = []

        items.append(self._check_python())
        items.append(self._check_os())
        items.append(self._check_project_files(root))
        items.extend(self._check_packages())
        items.append(self._check_output_writable(root))
        items.extend(self._check_ports(ports))
        items.append(self._check_venv(root))
        items.append(self._check_launcher_files(root))

        for item in items:
            if item.status == "FAIL":
                if item.category == "Python":
                    actions.append("Python 3.10 이상을 설치하거나, Windows에서 py 명령이 동작하는지 확인하세요.")
                elif item.category == "Package":
                    actions.append("4_REPAIR_ENVIRONMENT.bat를 실행해 Python 패키지를 다시 설치하세요.")
                elif item.category == "Project":
                    actions.append("ZIP을 새 폴더에 다시 압축 해제한 뒤 실행하세요.")
                elif item.category == "Output":
                    actions.append("쓰기 권한이 있는 폴더, 예: 바탕화면 또는 문서 폴더 아래로 옮겨 실행하세요.")
                elif item.category == "Port":
                    actions.append("4_REPAIR_ENVIRONMENT.bat 또는 scripts\\stop_port.py로 사용 중인 포트를 정리하세요.")
            elif item.status == "WARN":
                if item.category == "Venv":
                    actions.append("처음 실행 전이면 정상일 수 있습니다. START_WINDOWS.bat 또는 00_STEP_2_PORTABLE_INSTALL_NOW.bat를 실행하세요.")
                elif item.category == "Launcher":
                    actions.append("루트 폴더의 실행 BAT 파일이 없으면 ZIP을 다시 압축 해제하세요.")

        fail_count = sum(1 for i in items if i.status == "FAIL")
        warn_count = sum(1 for i in items if i.status == "WARN")
        score = max(0, 100 - fail_count * 20 - warn_count * 7)
        if fail_count:
            status = "수정 필요"
        elif warn_count:
            status = "주의"
        else:
            status = "정상"
        if not actions:
            actions.append("현재 진단 기준에서는 실행에 큰 문제가 발견되지 않았습니다.")

        report = DiagnosticReport(
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            app_version=app_version,
            overall_status=status,
            score=score,
            items=items,
            recommended_actions=actions,
        )

        if output_dir is not None:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            json_path = out / "installation_diagnostic_report.json"
            html_path = out / "installation_diagnostic_report.html"
            json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            html_path.write_text(self._render_html(report), encoding="utf-8")
            report.json_path = str(json_path)
            report.html_path = str(html_path)
        return report

    def _check_python(self) -> DiagnosticItem:
        version = sys.version_info
        ok = version.major == 3 and version.minor >= 10
        status = "PASS" if ok else "FAIL"
        return DiagnosticItem(
            "Python",
            "Python version",
            status,
            f"Python {version.major}.{version.minor}.{version.micro}",
            sys.executable,
        )

    def _check_os(self) -> DiagnosticItem:
        return DiagnosticItem("System", "Operating system", "PASS", platform.platform(), os.getcwd())

    def _check_project_files(self, root: Path) -> DiagnosticItem:
        required = ["app.py", "requirements.txt", "modules/constants.py"]
        missing = [p for p in required if not (root / p).exists()]
        if missing:
            return DiagnosticItem("Project", "Required files", "FAIL", "필수 파일 누락", ", ".join(missing))
        return DiagnosticItem("Project", "Required files", "PASS", "필수 파일 확인", str(root))

    def _check_packages(self) -> list[DiagnosticItem]:
        results = []
        for pkg in self.REQUIRED_PACKAGES:
            ok = importlib.util.find_spec(pkg) is not None
            results.append(DiagnosticItem("Package", pkg, "PASS" if ok else "WARN", "설치됨" if ok else "설치 필요 · START/REPAIR 실행 시 자동 설치"))
        return results

    def _check_output_writable(self, root: Path) -> DiagnosticItem:
        out = root / "outputs" / "diagnostics_tmp"
        try:
            out.mkdir(parents=True, exist_ok=True)
            test_file = out / "write_test.txt"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return DiagnosticItem("Output", "Write permission", "PASS", "outputs 폴더 쓰기 가능", str(out))
        except Exception as exc:
            return DiagnosticItem("Output", "Write permission", "FAIL", "outputs 폴더 쓰기 실패", str(exc))

    def _check_ports(self, ports: list[int]) -> list[DiagnosticItem]:
        results = []
        for port in ports:
            in_use = self._port_in_use(port)
            status = "WARN" if in_use and port != 8520 else "PASS"
            if in_use and port == 8520:
                status = "WARN"
            msg = "사용 중" if in_use else "비어 있음"
            results.append(DiagnosticItem("Port", f"127.0.0.1:{port}", status, msg))
        return results

    @staticmethod
    def _port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    def _check_venv(self, root: Path) -> DiagnosticItem:
        venv = root / ".venv"
        if not venv.exists():
            return DiagnosticItem("Venv", "Virtual environment", "WARN", ".venv 없음 · 첫 실행 시 자동 생성 가능", str(venv))
        return DiagnosticItem("Venv", "Virtual environment", "PASS", ".venv 확인", str(venv))

    def _check_launcher_files(self, root: Path) -> DiagnosticItem:
        required = ["START_WINDOWS.bat", "00_STEP_2_PORTABLE_INSTALL_NOW.bat", "00_STEP_3_START_PROGRAM.bat", "4_REPAIR_ENVIRONMENT.bat", "00_STEP_4_SAFE_CLEAN_OLD_VERSIONS.bat"]
        missing = [p for p in required if not (root / p).exists()]
        if missing:
            return DiagnosticItem("Launcher", "Launcher BAT files", "WARN", "일부 실행 파일 누락", ", ".join(missing))
        return DiagnosticItem("Launcher", "Launcher BAT files", "PASS", "실행/설치/복구 BAT 확인", ", ".join(required))

    @staticmethod
    def _render_html(report: DiagnosticReport) -> str:
        rows = []
        for item in report.items:
            color = {"PASS": "#e8fff0", "WARN": "#fff8d8", "FAIL": "#ffe8e8"}.get(item.status, "#fff")
            rows.append(
                f"<tr style='background:{color}'><td>{item.category}</td><td>{item.name}</td><td><b>{item.status}</b></td><td>{item.message}</td><td>{item.detail}</td></tr>"
            )
        actions = "".join(f"<li>{a}</li>" for a in report.recommended_actions)
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>Installation Diagnostic Report</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:32px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#333;color:white}}</style></head><body>
<h1>카카오 이모티콘 수익화 시스템 v9 설치/실행 진단</h1>
<p><b>생성일:</b> {report.created_at}</p><p><b>상태:</b> {report.overall_status} · <b>점수:</b> {report.score}</p>
<h2>권장 조치</h2><ul>{actions}</ul>
<h2>진단 결과</h2><table><thead><tr><th>분류</th><th>항목</th><th>상태</th><th>메시지</th><th>상세</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>"""
