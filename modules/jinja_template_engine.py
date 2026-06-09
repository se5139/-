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
class JinjaRenderResult:
    ok: bool
    generated_at: str
    project_name: str
    template_dir: str
    output_dir: str
    html_report_path: str
    prompt_path: str
    motion_plan_path: str
    manifest_path: str
    package_zip_path: str
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JinjaTemplateEngine:
    """Jinja2 based template engine for reports, prompts, and motion plans.

    The engine intentionally renders only original project data and abstract trend signals.
    It blocks API key-like strings from being written into reports or packages.
    """

    def __init__(self, template_dir: str | Path | None = None) -> None:
        base = Path(__file__).resolve().parents[1]
        self.template_dir = Path(template_dir) if template_dir else base / "templates" / "v62_jinja"
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(("html", "xml")),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["safe_join"] = self._safe_join
        self.env.filters["mask_secret"] = self._mask_secret

    @staticmethod
    def _safe_join(value: Any, sep: str = ", ") -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple, set)):
            return sep.join(str(x) for x in value)
        return str(value)

    @staticmethod
    def _mask_secret(value: Any) -> str:
        text = str(value or "")
        return API_KEY_PATTERN.sub(lambda m: m.group(0)[:8] + "..." + m.group(0)[-4:], text)

    @staticmethod
    def _strip_api_keys(text: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        if API_KEY_PATTERN.search(text):
            warnings.append("API key-like text was detected and masked before saving.")
        return API_KEY_PATTERN.sub(lambda m: m.group(0)[:8] + "..." + m.group(0)[-4:], text), warnings

    @staticmethod
    def _slug(text: str) -> str:
        slug = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", text).strip("_")
        return slug[:64] or "v62_jinja_project"

    def render_bundle(
        self,
        project_name: str,
        concept_text: str,
        style_preset: str,
        selected_suggestions: list[str],
        trend_signals: list[str],
        v61_report: dict[str, Any] | None,
        out_dir: str | Path,
    ) -> JinjaRenderResult:
        now = datetime.now().isoformat(timespec="seconds")
        project_name, warnings_a = self._strip_api_keys(project_name or "v62_jinja_project")
        concept_text, warnings_b = self._strip_api_keys(concept_text or "")
        style_preset, warnings_c = self._strip_api_keys(style_preset or "하찮은 공감형")
        selected_suggestions = [self._strip_api_keys(x)[0] for x in (selected_suggestions or [])]
        trend_signals = [self._strip_api_keys(x)[0] for x in (trend_signals or [])]
        warnings = warnings_a + warnings_b + warnings_c

        out = Path(out_dir) / self._slug(project_name)
        out.mkdir(parents=True, exist_ok=True)

        report_summary = self._summarize_v61(v61_report or {})
        context = {
            "generated_at": now,
            "project_name": project_name,
            "concept_text": concept_text,
            "style_preset": style_preset,
            "selected_suggestions": selected_suggestions,
            "trend_signals": trend_signals,
            "v61_summary": report_summary,
            "safety_notes": [
                "기존 캐릭터·유명 IP·유명인 이미지를 복제하지 않습니다.",
                "온라인 자료는 문구 길이, 감정 분포, 포즈 리듬, 가독성 같은 추상 신호만 반영합니다.",
                "API 키 원문은 리포트/ZIP에 저장하지 않습니다.",
            ],
            "kakao_planning": {
                "static_count": 32,
                "animated_count": 24,
                "animated_gif_minimum": 3,
                "canvas": "360x360",
                "animated_frame_limit": "24 frames 이하 초안",
            },
        }

        html = self.env.get_template("kakao_report.html.j2").render(**context)
        prompt = self.env.get_template("prompt_pack.md.j2").render(**context)
        motion = self.env.get_template("motion_plan.csv.j2").render(**context)
        manifest = {
            "engine": "Jinja2",
            "version": "v62",
            "generated_at": now,
            "project_name": project_name,
            "template_dir": str(self.template_dir),
            "outputs": {},
            "safety": {
                "api_key_raw_saved": False,
                "copyright_clone_mode": False,
                "trend_signal_mode": "abstract_only",
            },
            "context_preview": {
                "style_preset": style_preset,
                "selected_suggestions_count": len(selected_suggestions),
                "trend_signal_count": len(trend_signals),
            },
        }

        outputs = {
            "html_report_path": out / "v62_jinja_report.html",
            "prompt_path": out / "v62_prompt_pack.md",
            "motion_plan_path": out / "v62_motion_plan.csv",
            "manifest_path": out / "v62_manifest.json",
        }
        outputs["html_report_path"].write_text(html, encoding="utf-8")
        outputs["prompt_path"].write_text(prompt, encoding="utf-8")
        outputs["motion_plan_path"].write_text(motion, encoding="utf-8-sig")
        manifest["outputs"] = {k: str(v) for k, v in outputs.items()}
        outputs["manifest_path"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        package = out / "v62_jinja_template_bundle.zip"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for key, path in outputs.items():
                zf.write(path, arcname=path.name)

        # Final package-level leakage check.
        leakage = []
        for path in list(outputs.values()):
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            if API_KEY_PATTERN.search(text):
                leakage.append(path.name)
        if leakage:
            raise RuntimeError("API key-like string remained in generated files: " + ", ".join(leakage))

        return JinjaRenderResult(
            ok=True,
            generated_at=now,
            project_name=project_name,
            template_dir=str(self.template_dir),
            output_dir=str(out),
            html_report_path=str(outputs["html_report_path"]),
            prompt_path=str(outputs["prompt_path"]),
            motion_plan_path=str(outputs["motion_plan_path"]),
            manifest_path=str(outputs["manifest_path"]),
            package_zip_path=str(package),
            warnings=warnings,
        )

    @staticmethod
    def _summarize_v61(report: dict[str, Any]) -> dict[str, Any]:
        if not report:
            return {
                "available": False,
                "static_preview": "",
                "animated_previews": [],
                "plan_count": 0,
            }
        animated = []
        for key in ["primary_gif_path", "bounce_gif_path", "bow_gif_path", "shake_gif_path"]:
            value = report.get(key)
            if value:
                animated.append({"label": key, "path": value})
        return {
            "available": True,
            "static_preview": report.get("static_png_path", ""),
            "animated_previews": animated,
            "plan_count": len(report.get("kakao_24_plan", []) or []),
            "html_report_path": report.get("html_report_path", ""),
            "package_zip_path": report.get("package_zip_path", ""),
        }
