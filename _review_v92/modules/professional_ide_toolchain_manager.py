
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

API_KEY_PATTERN = re.compile(r"sk-(?:proj|[A-Za-z0-9])[-_A-Za-z0-9]{20,}")

@dataclass
class IDEToolRow:
    priority: int
    tool: str
    category: str
    primary_domain: str
    project_role: str
    adoption_policy: str
    install_stage: str
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class DevStackRow:
    layer: str
    selected_tools: list[str]
    why: str
    runtime_impact: str
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class V65ProfessionalIDEResult:
    ok: bool
    generated_at: str
    project_name: str
    output_dir: str
    html_report_path: str
    ide_matrix_path: str
    stack_policy_path: str
    install_guide_path: str
    vscode_recommendations_path: str
    pycharm_note_path: str
    manifest_path: str
    package_zip_path: str
    ide_tools: list[dict[str, Any]]
    dev_stack: list[dict[str, Any]]
    warnings: list[str]
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class ProfessionalIDEToolchainManager:
    """v65 professional IDE/toolchain integration manager.

    Professional IDEs are managed as developer-side tools only. The end-user
    package remains a Python-centered local PC app.
    """

    def __init__(self, template_dir: str | Path | None = None) -> None:
        base = Path(__file__).resolve().parents[1]
        self.template_dir = Path(template_dir) if template_dir else base / 'templates' / 'v65_professional_ide_toolchain'
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(('html', 'xml')),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.ide_tools = self._build_ide_tools()
        self.dev_stack = self._build_dev_stack()

    @staticmethod
    def _slug(text: str) -> str:
        cleaned = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", text or "").strip('_')
        return cleaned[:64] or 'v65_professional_ide_toolchain'

    @staticmethod
    def _mask_api_keys(text: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        if API_KEY_PATTERN.search(text or ''):
            warnings.append('API key-like text was detected and masked before saving.')
        return API_KEY_PATTERN.sub(lambda m: m.group(0)[:8] + '...' + m.group(0)[-4:], text or ''), warnings

    def _build_ide_tools(self) -> list[IDEToolRow]:
        return [
            IDEToolRow(1, 'PyCharm Professional', 'Python IDE', 'Python, data analysis, debugging', 'Primary professional IDE for this Python-centered local PC app', 'recommended developer tool; not bundled', 'install on developer PC if available'),
            IDEToolRow(2, 'Visual Studio Code', 'General code editor/IDE', 'Python, web files, JSON, scripts', 'Lightweight everyday editor, extension hub, quick inspection', 'recommended developer tool; not bundled', 'install on developer PC'),
            IDEToolRow(3, 'Visual Studio', 'Windows/.NET IDE', 'C#, C++, Windows desktop tooling', 'Optional support for Windows-specific helper apps and native build checks', 'optional; not required for normal runtime', 'install only if Windows native development is needed'),
            IDEToolRow(4, 'WebStorm', 'Web IDE', 'JavaScript, TypeScript, React, Vue', 'Optional future admin dashboard/front-end tooling', 'optional expansion tool', 'install only for web dashboard expansion'),
            IDEToolRow(5, 'Android Studio', 'Android IDE', 'Kotlin, Java, Android apps', 'Optional future Play Store/mobile companion app route', 'future expansion tool', 'install only for mobile app phase'),
            IDEToolRow(6, 'IntelliJ IDEA Ultimate', 'Java/Kotlin IDE', 'Java, Kotlin, Spring', 'Optional backend/server expansion route', 'future expansion tool', 'install only for server phase'),
            IDEToolRow(7, 'Rider', '.NET/Game IDE', 'C#, .NET, Unity', 'Optional .NET or Unity prototype route', 'future expansion tool', 'install only if selected'),
            IDEToolRow(8, 'CLion', 'C/C++ IDE', 'C, C++, CMake', 'Optional high-performance image/video/native extension route', 'specialized optional tool', 'install only if native extension is required'),
            IDEToolRow(9, 'Eclipse IDE', 'Open-source Java IDE', 'Java, plugin ecosystems', 'Fallback free Java IDE option', 'optional alternative', 'not required'),
            IDEToolRow(10, 'Apache NetBeans', 'Open-source Java/PHP IDE', 'Java, PHP, HTML5, JavaScript', 'Fallback free Java/PHP/web IDE option', 'optional alternative', 'not required'),
        ]

    def _build_dev_stack(self) -> list[DevStackRow]:
        return [
            DevStackRow('Final runtime', ['Python', 'Streamlit', 'Pillow', 'pandas', 'Jinja2'], 'Local PC production tool with image/GIF/data/report features.', 'included in package requirements'),
            DevStackRow('Template/report layer', ['Jinja2 primary', 'Mako optional'], 'Separate HTML reports, prompt packs, style rulebooks, and motion plans from core Python logic.', 'Jinja2 included; Mako optional'),
            DevStackRow('Developer IDE layer', ['PyCharm Professional', 'VS Code'], 'Best fit for Python code inspection, debugging, search, project navigation, and fast edits.', 'external only'),
            DevStackRow('Windows installer layer', ['Inno Setup', 'PyInstaller optional', 'Visual Studio optional'], 'Installer EXE, desktop shortcuts, uninstall entry, and future executable wrapping.', 'build-time only'),
            DevStackRow('Quality layer', ['compileall', 'pytest', 'ruff', 'mypy optional'], 'Release needs syntax, smoke, lint, optional type, ZIP integrity, and SHA-256 checks.', 'developer/check scripts only'),
            DevStackRow('Version control layer', ['Git', 'GitHub optional'], 'Track v-series changes, rollback, release tags, and source backups.', 'developer only'),
            DevStackRow('Future web/mobile expansion', ['WebStorm', 'Android Studio', 'Xcode requires Mac'], 'Only used when the project moves beyond local PC into web/mobile products.', 'future optional'),
        ]

    def render_bundle(self, project_name: str, out_dir: str | Path) -> V65ProfessionalIDEResult:
        project_name, warnings = self._mask_api_keys(project_name or 'v65_professional_ide_toolchain_project')
        now = datetime.now().isoformat(timespec='seconds')
        out = Path(out_dir) / self._slug(project_name)
        out.mkdir(parents=True, exist_ok=True)
        context = {
            'generated_at': now,
            'project_name': project_name,
            'fixed_rule': 'Final deliverable remains a Python-centered local PC executable/installable program. Professional IDEs are development tools, not required end-user runtime dependencies.',
            'ide_tools': [x.to_dict() for x in self.ide_tools],
            'dev_stack': [x.to_dict() for x in self.dev_stack],
            'source_policy': 'Use current official documentation when changing tool versions. Do not bundle paid IDEs into the final user package.',
        }
        outputs = {
            'html_report_path': out / 'v65_professional_ide_toolchain_report.html',
            'ide_matrix_path': out / 'v65_professional_ide_matrix.csv',
            'stack_policy_path': out / 'v65_development_stack_policy.json',
            'install_guide_path': out / 'v65_developer_install_guide.md',
            'vscode_recommendations_path': out / 'v65_vscode_recommended_extensions.json',
            'pycharm_note_path': out / 'v65_pycharm_project_note.md',
            'manifest_path': out / 'v65_manifest.json',
        }
        outputs['html_report_path'].write_text(self.env.get_template('ide_toolchain_report.html.j2').render(**context), encoding='utf-8')
        outputs['ide_matrix_path'].write_text(self.env.get_template('ide_matrix.csv.j2').render(**context), encoding='utf-8-sig')
        outputs['install_guide_path'].write_text(self.env.get_template('developer_install_guide.md.j2').render(**context), encoding='utf-8')
        outputs['stack_policy_path'].write_text(json.dumps(context['dev_stack'], ensure_ascii=False, indent=2), encoding='utf-8')
        outputs['vscode_recommendations_path'].write_text(json.dumps({
            'recommendations': [
                'ms-python.python', 'ms-python.vscode-pylance', 'ms-python.debugpy',
                'ms-toolsai.jupyter', 'charliermarsh.ruff', 'redhat.vscode-yaml'
            ],
            'unwantedRecommendations': []
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        pycharm_note = """# v65 PyCharm Professional project note

- Use PyCharm Professional as the main professional Python IDE when available.
- Keep Streamlit/Pillow/pandas/Jinja2 as the actual runtime stack.
- Configure interpreter to `.venv` after running `4_REPAIR_ENVIRONMENT.bat`.
- Run `python -m compileall .` and the v65 check script before packaging.
- Do not store raw API keys inside project files.
"""
        outputs['pycharm_note_path'].write_text(pycharm_note, encoding='utf-8')
        manifest = {
            'version': 'v65',
            'generated_at': now,
            'project_name': project_name,
            'final_deliverable': 'Python-centered local PC installer/executable',
            'primary_ide': 'PyCharm Professional',
            'secondary_ide': 'Visual Studio Code',
            'windows_native_optional': 'Visual Studio',
            'web_optional': 'WebStorm',
            'mobile_optional': ['Android Studio', 'Xcode requires Mac'],
            'raw_api_key_saved': False,
            'outputs': {k: str(v) for k, v in outputs.items()},
        }
        outputs['manifest_path'].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        package = out / 'v65_professional_ide_toolchain_bundle.zip'
        with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for p in outputs.values():
                zf.write(p, arcname=p.name)
        for p in outputs.values():
            if API_KEY_PATTERN.search(p.read_text(encoding='utf-8-sig', errors='ignore')):
                raise RuntimeError(f'API key-like string remained in {p.name}')
        return V65ProfessionalIDEResult(
            ok=True,
            generated_at=now,
            project_name=project_name,
            output_dir=str(out),
            html_report_path=str(outputs['html_report_path']),
            ide_matrix_path=str(outputs['ide_matrix_path']),
            stack_policy_path=str(outputs['stack_policy_path']),
            install_guide_path=str(outputs['install_guide_path']),
            vscode_recommendations_path=str(outputs['vscode_recommendations_path']),
            pycharm_note_path=str(outputs['pycharm_note_path']),
            manifest_path=str(outputs['manifest_path']),
            package_zip_path=str(package),
            ide_tools=[x.to_dict() for x in self.ide_tools],
            dev_stack=[x.to_dict() for x in self.dev_stack],
            warnings=warnings,
        )
