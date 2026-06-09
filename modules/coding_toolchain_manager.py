from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

API_KEY_PATTERN = re.compile(r"sk-(?:proj|[A-Za-z0-9])[-_A-Za-z0-9]{20,}")

@dataclass
class ToolchainRow:
    category: str
    tools: list[str]
    role: str
    status: str
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class TemplateEngineRow:
    engine: str
    use_case: str
    decision: str
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class CodingToolchainResult:
    ok: bool
    generated_at: str
    project_name: str
    output_dir: str
    html_report_path: str
    prompt_pack_path: str
    toolchain_matrix_path: str
    template_engine_matrix_path: str
    install_checklist_path: str
    manifest_path: str
    package_zip_path: str
    toolchain: list[dict[str, Any]]
    template_engines: list[dict[str, Any]]
    warnings: list[str]
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class CodingToolchainManager:
    """v64 coding-program/toolchain manager.

    This module records the practical coding-program stack for this local PC
    Python project. It does not force every available tool into the runtime;
    instead it separates main runtime tools, optional developer tools, packaging
    tools, template engines, and AI coding assistants.
    """
    def __init__(self, template_dir: str | Path | None = None) -> None:
        base = Path(__file__).resolve().parents[1]
        self.template_dir = Path(template_dir) if template_dir else base / "templates" / "v64_coding_toolchain_manager"
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(("html", "xml")),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["mask_secret"] = self._mask_secret
        self.toolchain = self._build_toolchain()
        self.template_engines = self._build_template_engines()

    @staticmethod
    def _mask_secret(value: Any) -> str:
        return API_KEY_PATTERN.sub(lambda m: m.group(0)[:8] + "..." + m.group(0)[-4:], str(value or ""))

    @staticmethod
    def _strip_api_keys(text: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        if API_KEY_PATTERN.search(text or ""):
            warnings.append("API key-like text was detected and masked before saving.")
        return API_KEY_PATTERN.sub(lambda m: m.group(0)[:8] + "..." + m.group(0)[-4:], text or ""), warnings

    @staticmethod
    def _slug(text: str) -> str:
        slug = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", text).strip("_")
        return slug[:64] or "v64_coding_toolchain"

    def _build_toolchain(self) -> list[ToolchainRow]:
        return [
            ToolchainRow("Main language", ["Python"], "Core local PC program, data analysis, image/GIF generation, packaging scripts", "required"),
            ToolchainRow("UI layer", ["Streamlit", "PySide6 optional", "CustomTkinter optional"], "Current UI stays Streamlit; desktop UI options are kept as future adapters", "active plus optional"),
            ToolchainRow("Template engines", ["Jinja2", "Mako optional", "Django Template evaluated", "Chameleon evaluated"], "Separate HTML reports, prompts, style rulebooks, motion plans from Python logic", "active policy"),
            ToolchainRow("Data/storage", ["SQLite", "JSON", "CSV", "Excel", "pandas", "openpyxl"], "Learning data, sales/plus report ingestion, project manifests, backups", "required/optional by feature"),
            ToolchainRow("Image/GIF/video", ["Pillow", "imageio", "ffmpeg", "moviepy optional"], "PNG/GIF preview, animated draft, media conversion", "Pillow active; media tools optional"),
            ToolchainRow("Code editors/IDE", ["VS Code", "PyCharm", "Visual Studio optional"], "Developer editing, debugging, inspections, Windows build support", "external developer tools"),
            ToolchainRow("Version control", ["Git", "GitHub optional"], "Version history, rollback, release tags, source backup", "recommended"),
            ToolchainRow("Packaging", ["PyInstaller", "Inno Setup", "ZIP", "SHA-256"], "Python app packaging, Windows installer, integrity check", "Inno active; PyInstaller optional next"),
            ToolchainRow("Quality checks", ["compileall", "pytest", "ruff", "mypy optional"], "Syntax check, smoke tests, lint/type checks, release validation", "compileall active; dev tools optional"),
            ToolchainRow("AI coding assistants", ["ChatGPT", "GitHub Copilot optional", "Cursor optional", "Replit AI optional"], "Development assistance only; final package remains local Python program", "optional"),
        ]

    def _build_template_engines(self) -> list[TemplateEngineRow]:
        return [
            TemplateEngineRow("Jinja2", "HTML report, prompt pack, CSV/JSON text artifacts", "Primary engine because it is fast, expressive, Python-native, and fits Streamlit local packaging."),
            TemplateEngineRow("Mako", "Advanced prompt/code-like text templates", "Optional adapter only; installed via requirements but not required for normal user flow."),
            TemplateEngineRow("Django Template", "Django web projects", "Evaluated but not bundled because this is not a Django server app."),
            TemplateEngineRow("Chameleon", "HTML/XML TAL-style templates", "Evaluated but not bundled to keep the local app lighter."),
            TemplateEngineRow("Handlebars/Mustache", "Logic-light template concept", "Concept reference only; no JavaScript runtime added to final Python package."),
        ]

    def render_toolchain_bundle(self, project_name: str, out_dir: str | Path) -> CodingToolchainResult:
        now = datetime.now().isoformat(timespec="seconds")
        project_name, warnings = self._strip_api_keys(project_name or "v64_coding_toolchain_project")
        out = Path(out_dir) / self._slug(project_name)
        out.mkdir(parents=True, exist_ok=True)
        fixed_rule = "Final deliverable stays a Python-centered local PC executable/installable program. Other coding programs are used only when they fit the project purpose."
        install_checklist = [
            "Python 3.11+", "VS Code or PyCharm", "Git", "Inno Setup 6", "Jinja2", "Mako optional", "Pillow", "pandas", "Streamlit", "ZIP + SHA-256 check",
        ]
        context = {
            "generated_at": now,
            "project_name": project_name,
            "fixed_rule": fixed_rule,
            "toolchain": [x.to_dict() for x in self.toolchain],
            "template_engines": [x.to_dict() for x in self.template_engines],
            "install_checklist": install_checklist,
        }
        outputs = {
            "html_report_path": out / "v64_coding_toolchain_report.html",
            "prompt_pack_path": out / "v64_coding_toolchain_prompt_pack.md",
            "toolchain_matrix_path": out / "v64_toolchain_matrix.csv",
            "template_engine_matrix_path": out / "v64_template_engine_matrix.json",
            "install_checklist_path": out / "v64_install_checklist.json",
            "manifest_path": out / "v64_manifest.json",
        }
        outputs["html_report_path"].write_text(self.env.get_template("toolchain_report.html.j2").render(**context), encoding="utf-8")
        outputs["prompt_pack_path"].write_text(self.env.get_template("toolchain_prompt.md.j2").render(**context), encoding="utf-8")
        outputs["toolchain_matrix_path"].write_text(self.env.get_template("toolchain_matrix.csv.j2").render(**context), encoding="utf-8-sig")
        outputs["template_engine_matrix_path"].write_text(self.env.get_template("template_engine_matrix.json.j2").render(**context), encoding="utf-8")
        outputs["install_checklist_path"].write_text(json.dumps(install_checklist, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest = {
            "version": "v64",
            "generated_at": now,
            "project_name": project_name,
            "final_deliverable": "Python-centered local PC installer/executable",
            "primary_template_engine": "Jinja2",
            "optional_template_engine": "Mako",
            "raw_api_key_saved": False,
            "outputs": {k: str(v) for k, v in outputs.items()},
        }
        outputs["manifest_path"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        package = out / "v64_coding_toolchain_bundle.zip"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in outputs.values():
                zf.write(p, arcname=p.name)
        for p in outputs.values():
            if API_KEY_PATTERN.search(p.read_text(encoding="utf-8-sig", errors="ignore")):
                raise RuntimeError(f"API key-like string remained in {p.name}")
        return CodingToolchainResult(
            ok=True,
            generated_at=now,
            project_name=project_name,
            output_dir=str(out),
            html_report_path=str(outputs["html_report_path"]),
            prompt_pack_path=str(outputs["prompt_pack_path"]),
            toolchain_matrix_path=str(outputs["toolchain_matrix_path"]),
            template_engine_matrix_path=str(outputs["template_engine_matrix_path"]),
            install_checklist_path=str(outputs["install_checklist_path"]),
            manifest_path=str(outputs["manifest_path"]),
            package_zip_path=str(package),
            toolchain=[x.to_dict() for x in self.toolchain],
            template_engines=[x.to_dict() for x in self.template_engines],
            warnings=warnings,
        )
