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
class TemplateEngineChoice:
    engine: str
    role: str
    status: str
    reason: str
    dependency: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TemplateManagerResult:
    ok: bool
    generated_at: str
    project_name: str
    selected_primary_engine: str
    output_dir: str
    html_report_path: str
    prompt_template_path: str
    style_rulebook_path: str
    motion_template_path: str
    engine_matrix_path: str
    manifest_path: str
    package_zip_path: str
    warnings: list[str]
    engine_choices: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TemplateEngineManager:
    """Template-engine router for the Kakao Emoticon local program.

    Active renderer: Jinja2. Optional adapter: Mako for advanced prompt/text templates
    when the dependency is installed by requirements. Django Templates and Chameleon are
    evaluated but not loaded as runtime dependencies because the app is a Streamlit local
    PC package, not a full Django site or XML/TAL web application.
    """

    def __init__(self, template_dir: str | Path | None = None) -> None:
        base = Path(__file__).resolve().parents[1]
        self.template_dir = Path(template_dir) if template_dir else base / "templates" / "v63_template_manager"
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(("html", "xml")),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["safe_join"] = self._safe_join
        self.env.filters["mask_secret"] = self._mask_secret
        self.engine_choices = self._build_engine_matrix()

    @staticmethod
    def _safe_join(value: Any, sep: str = ", ") -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple, set)):
            return sep.join(str(x) for x in value)
        return str(value)

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
        return slug[:64] or "v63_template_project"

    @staticmethod
    def _mako_available() -> bool:
        try:
            import mako  # noqa: F401
            return True
        except Exception:
            return False

    def _build_engine_matrix(self) -> list[TemplateEngineChoice]:
        mako_status = "optional_installed" if self._mako_available() else "optional_ready_after_pip_install"
        return [
            TemplateEngineChoice(
                engine="Jinja2",
                role="primary",
                status="active",
                reason="HTML report, prompt pack, CSV/JSON text artifacts need safe autoescape, inheritance, filters, and strict undefined checks.",
                dependency="Jinja2>=3.1.6",
            ),
            TemplateEngineChoice(
                engine="Mako",
                role="advanced_text_optional",
                status=mako_status,
                reason="Useful for power-user prompt/code-like text templates, but not required for normal Streamlit UI flow.",
                dependency="Mako>=1.3.12",
            ),
            TemplateEngineChoice(
                engine="Django Template Language",
                role="evaluated_not_loaded",
                status="not_selected",
                reason="Good inside Django projects, but this program is a local Streamlit app and does not need the full Django framework.",
                dependency="not bundled",
            ),
            TemplateEngineChoice(
                engine="Chameleon",
                role="evaluated_not_loaded",
                status="not_selected",
                reason="Strong for HTML/XML TAL templates, but less suitable for the current markdown/CSV/prompt/report workflow.",
                dependency="not bundled",
            ),
            TemplateEngineChoice(
                engine="Handlebars/Mustache family",
                role="concept_reference",
                status="not_selected_for_python_runtime",
                reason="Popular logic-light style; the same separation principle is reflected through Jinja2 templates without adding a JS runtime.",
                dependency="not bundled",
            ),
        ]

    def render_manager_bundle(
        self,
        project_name: str,
        concept_text: str,
        intended_outputs: list[str],
        selected_template_policy: str,
        trend_signals: list[str],
        out_dir: str | Path,
    ) -> TemplateManagerResult:
        now = datetime.now().isoformat(timespec="seconds")
        project_name, w1 = self._strip_api_keys(project_name or "v63_template_project")
        concept_text, w2 = self._strip_api_keys(concept_text or "")
        selected_template_policy, w3 = self._strip_api_keys(selected_template_policy or "Jinja2 primary")
        trend_signals = [self._strip_api_keys(x)[0] for x in (trend_signals or [])]
        intended_outputs = [self._strip_api_keys(x)[0] for x in (intended_outputs or [])]
        warnings = w1 + w2 + w3

        out = Path(out_dir) / self._slug(project_name)
        out.mkdir(parents=True, exist_ok=True)

        context = {
            "generated_at": now,
            "project_name": project_name,
            "concept_text": concept_text,
            "selected_template_policy": selected_template_policy,
            "intended_outputs": intended_outputs,
            "trend_signals": trend_signals,
            "engine_choices": [x.to_dict() for x in self.engine_choices],
            "active_engine": "Jinja2",
            "optional_engine": "Mako",
            "safety_notes": [
                "OpenAI/API keys are never written as raw text in generated reports or packages.",
                "Template output uses original user project data and abstract trend signals only.",
                "Existing Kakao/IP characters are not copied; style is built from independent concept rules.",
            ],
            "template_governance": {
                "ui": "Streamlit remains the app UI layer.",
                "reporting": "Jinja2 templates generate HTML reports.",
                "prompting": "Jinja2/Mako-ready prompt templates are separated from Python logic.",
                "motion_plan": "CSV/JSON motion plan templates are separated from engine code.",
                "future_extension": "Additional template engines can be added through adapters only when they are useful.",
            },
        }

        html = self.env.get_template("engine_decision_report.html.j2").render(**context)
        prompt = self.env.get_template("prompt_template.md.j2").render(**context)
        style_rulebook = self.env.get_template("style_rulebook.json.j2").render(**context)
        motion_template = self.env.get_template("motion_template.csv.j2").render(**context)

        outputs = {
            "html_report_path": out / "v63_template_engine_decision_report.html",
            "prompt_template_path": out / "v63_prompt_template.md",
            "style_rulebook_path": out / "v63_style_rulebook.json",
            "motion_template_path": out / "v63_motion_template.csv",
            "engine_matrix_path": out / "v63_engine_matrix.json",
            "manifest_path": out / "v63_manifest.json",
        }
        outputs["html_report_path"].write_text(html, encoding="utf-8")
        outputs["prompt_template_path"].write_text(prompt, encoding="utf-8")
        outputs["style_rulebook_path"].write_text(style_rulebook, encoding="utf-8")
        outputs["motion_template_path"].write_text(motion_template, encoding="utf-8-sig")
        outputs["engine_matrix_path"].write_text(json.dumps([x.to_dict() for x in self.engine_choices], ensure_ascii=False, indent=2), encoding="utf-8")

        manifest = {
            "version": "v63",
            "generated_at": now,
            "project_name": project_name,
            "primary_engine": "Jinja2",
            "optional_engine": "Mako",
            "template_dir": str(self.template_dir),
            "outputs": {k: str(v) for k, v in outputs.items()},
            "raw_api_key_saved": False,
            "copyright_clone_mode": False,
        }
        outputs["manifest_path"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        package = out / "v63_template_engine_manager_bundle.zip"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in outputs.values():
                zf.write(p, arcname=p.name)

        leaks = []
        for p in outputs.values():
            if API_KEY_PATTERN.search(p.read_text(encoding="utf-8-sig", errors="ignore")):
                leaks.append(p.name)
        if leaks:
            raise RuntimeError("API key-like string remained in generated files: " + ", ".join(leaks))

        return TemplateManagerResult(
            ok=True,
            generated_at=now,
            project_name=project_name,
            selected_primary_engine="Jinja2",
            output_dir=str(out),
            html_report_path=str(outputs["html_report_path"]),
            prompt_template_path=str(outputs["prompt_template_path"]),
            style_rulebook_path=str(outputs["style_rulebook_path"]),
            motion_template_path=str(outputs["motion_template_path"]),
            engine_matrix_path=str(outputs["engine_matrix_path"]),
            manifest_path=str(outputs["manifest_path"]),
            package_zip_path=str(package),
            warnings=warnings,
            engine_choices=[x.to_dict() for x in self.engine_choices],
        )
