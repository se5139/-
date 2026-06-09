
from __future__ import annotations

import csv
import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None


@dataclass
class PipelineStage:
    order: int
    stage: str
    primary_tool: str
    support_tools: list[str]
    output: str
    verification: str
    final_rule: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class V66ExecutionResult:
    ok: bool
    project_name: str
    generated_at: str
    stages: list[dict[str, Any]]
    html_report_path: str
    workflow_markdown_path: str
    tool_usage_matrix_path: str
    qa_checklist_path: str
    vscode_tasks_path: str
    vscode_launch_path: str
    github_workflow_path: str
    pyproject_path: str
    manifest_path: str
    package_zip_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MultiToolExecutionPipeline:
    """v66: apply the previously selected coding tools as a real development workflow.

    This module does not embed paid IDEs inside the runtime package. It creates
    an executable development policy, generated configs, and verification files
    that keep the final deliverable Python-centered while using specialized tools
    during development.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        self.template_dir = template_dir or root / "templates" / "v66_multi_tool_execution"
        self.stages = [
            PipelineStage(1, "요구사항 정리", "ChatGPT", ["VS Code", "PyCharm"], "기능 요구사항/변경 로그", "요구사항 누락 검사", "최종 산출물은 Python 로컬 설치형"),
            PipelineStage(2, "Python 핵심 로직 구현", "Python", ["PyCharm Professional", "VS Code"], "modules/*.py", "compileall + smoke test", "Python 중심 코드 유지"),
            PipelineStage(3, "UI 연결", "Streamlit", ["Jinja2", "Pillow", "pandas"], "app.py 좌측 메뉴/미리보기", "AST 검사 + 라우팅 검사", "초보자용 로컬 UI 유지"),
            PipelineStage(4, "템플릿 분리", "Jinja2", ["Mako optional"], "HTML/Markdown/CSV 템플릿", "Jinja 렌더링 검사", "복잡한 문자열은 템플릿으로 분리"),
            PipelineStage(5, "이미지/GIF 처리", "Pillow", ["imageio", "ffmpeg optional"], "PNG/GIF/미리보기 시트", "파일 생성/용량/프레임 검사", "정지형 기반 움직이는형 연결"),
            PipelineStage(6, "데이터 분석", "pandas", ["openpyxl", "SQLite", "JSON", "CSV"], "성과/트렌드/학습 데이터", "샘플 엑셀/CSV 파싱 검사", "사용자 데이터 보호"),
            PipelineStage(7, "품질 검사", "pytest", ["ruff", "mypy", "compileall"], "검증 리포트", "2중·3중 검사", "수정 후 재검사"),
            PipelineStage(8, "설치 패키징", "Inno Setup", ["PyInstaller optional", "BAT", "SHA-256"], "Windows 설치마법사/ZIP", "ZIP 무결성 + SHA-256", "Python 프로그램을 설치형으로 감싸기"),
            PipelineStage(9, "버전관리", "Git", ["GitHub", "GitHub Actions"], "변경 이력/워크플로우", "CI용 quality check", "기존 기능 삭제 금지"),
            PipelineStage(10, "전문 IDE 적용", "PyCharm Professional", ["VS Code", "Visual Studio", "WebStorm", "Android Studio"], "개발 설정/가이드", "설정 파일 존재 검사", "IDE는 개발 보조, 런타임 강제 포함 금지"),
        ]

    def _env(self) -> Any:
        if Environment is None:
            raise RuntimeError("Jinja2 is not installed. Run 4_REPAIR_ENVIRONMENT.bat first.")
        return Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _render(self, template_name: str, context: dict[str, Any]) -> str:
        return self._env().get_template(template_name).render(**context)

    def render_bundle(self, project_name: str, out_dir: Path) -> V66ExecutionResult:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        config_dir = out_dir / "generated_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        stages = [s.to_dict() for s in self.stages]
        context = {
            "project_name": project_name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "stages": stages,
            "final_policy": "Python-centered local PC installer with specialist tools used only where they add value.",
        }
        html_path = out_dir / "v66_multi_tool_execution_report.html"
        workflow_md_path = out_dir / "v66_development_workflow.md"
        html_path.write_text(self._render("execution_report.html.j2", context), encoding="utf-8")
        workflow_md_path.write_text(self._render("workflow.md.j2", context), encoding="utf-8")

        matrix_path = out_dir / "v66_tool_usage_matrix.csv"
        with matrix_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["order", "stage", "primary_tool", "support_tools", "output", "verification", "final_rule"])
            writer.writeheader()
            for s in stages:
                row = dict(s)
                row["support_tools"] = ", ".join(row["support_tools"])
                writer.writerow(row)

        qa_path = out_dir / "v66_quality_gate_checklist.json"
        qa_payload = {
            "must_pass": [
                "Python compileall PASS",
                "app.py AST PASS",
                "Jinja2 template rendering PASS",
                "No API key plaintext in package",
                "ZIP integrity PASS",
                "SHA-256 created",
                "Existing feature menu preserved",
                "User data protection scripts present",
            ],
            "manual_windows_checks": [
                "Build installer EXE with 0_BUILD_WINDOWS_INSTALLER_EXE.bat",
                "Install with desktop shortcut option checked",
                "Run main desktop icon",
                "Confirm animated GIF preview moves in browser",
            ],
        }
        qa_path.write_text(json.dumps(qa_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        vscode_tasks = {
            "version": "2.0.0",
            "tasks": [
                {"label": "v66 compileall", "type": "shell", "command": "python", "args": ["-m", "compileall", "."]},
                {"label": "v66 check", "type": "shell", "command": "python", "args": ["scripts/v66_multi_tool_execution_check.py"]},
                {"label": "build installer", "type": "shell", "command": "0_BUILD_WINDOWS_INSTALLER_EXE.bat", "windows": {"command": "0_BUILD_WINDOWS_INSTALLER_EXE.bat"}},
            ],
        }
        vscode_launch = {
            "version": "0.2.0",
            "configurations": [
                {"name": "Run Streamlit app", "type": "python", "request": "launch", "module": "streamlit", "args": ["run", "app.py", "--server.port", "8520"]}
            ],
        }
        vscode_tasks_path = config_dir / "tasks.json"
        vscode_launch_path = config_dir / "launch.json"
        vscode_tasks_path.write_text(json.dumps(vscode_tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        vscode_launch_path.write_text(json.dumps(vscode_launch, ensure_ascii=False, indent=2), encoding="utf-8")

        github_dir = config_dir / ".github" / "workflows"
        github_dir.mkdir(parents=True, exist_ok=True)
        github_workflow_path = github_dir / "quality-check.yml"
        github_workflow_path.write_text(self._render("github_quality_check.yml.j2", context), encoding="utf-8")

        pyproject_path = config_dir / "pyproject.toml"
        pyproject_path.write_text(self._render("pyproject.toml.j2", context), encoding="utf-8")

        manifest_path = out_dir / "v66_manifest.json"
        manifest = {
            "project_name": project_name,
            "generated_at": context["generated_at"],
            "version": "v66",
            "final_deliverable": "Python-centered local PC installer",
            "primary_runtime": ["Python", "Streamlit", "Jinja2", "Pillow", "pandas"],
            "development_tools": ["PyCharm Professional", "VS Code", "Visual Studio", "WebStorm", "Android Studio", "Git", "Inno Setup"],
            "stages": stages,
            "files": {
                "html_report": str(html_path),
                "workflow_markdown": str(workflow_md_path),
                "tool_usage_matrix": str(matrix_path),
                "qa_checklist": str(qa_path),
                "vscode_tasks": str(vscode_tasks_path),
                "vscode_launch": str(vscode_launch_path),
                "github_workflow": str(github_workflow_path),
                "pyproject": str(pyproject_path),
            },
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        package_zip_path = out_dir / "v66_multi_tool_execution_bundle.zip"
        with zipfile.ZipFile(package_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in [html_path, workflow_md_path, matrix_path, qa_path, vscode_tasks_path, vscode_launch_path, github_workflow_path, pyproject_path, manifest_path]:
                zf.write(p, p.relative_to(out_dir))
        return V66ExecutionResult(
            ok=True,
            project_name=project_name,
            generated_at=context["generated_at"],
            stages=stages,
            html_report_path=str(html_path),
            workflow_markdown_path=str(workflow_md_path),
            tool_usage_matrix_path=str(matrix_path),
            qa_checklist_path=str(qa_path),
            vscode_tasks_path=str(vscode_tasks_path),
            vscode_launch_path=str(vscode_launch_path),
            github_workflow_path=str(github_workflow_path),
            pyproject_path=str(pyproject_path),
            manifest_path=str(manifest_path),
            package_zip_path=str(package_zip_path),
        )
