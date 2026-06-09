
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import re
import zipfile


@dataclass
class ApiKeySafetyConfig:
    project_name: str = "kakao_emoticon_v58"
    mode: str = "local_first_zero_cost"
    openai_optional: bool = True
    paid_calls_allowed: bool = False
    local_file_first: bool = True
    max_collection_days: int = 30
    daily_openai_analysis_limit: int = 0
    monthly_budget_krw: int = 0
    use_environment_variable: bool = True
    env_var_name: str = "OPENAI_API_KEY"


class OpenAIKeySafetyEngine:
    """Security guard for optional OpenAI API usage.

    The engine never stores raw API keys. It only validates format, masks keys,
    creates safe templates, and writes reports without secrets.
    """

    SECRET_PATTERN = re.compile(r"(?:sk|sk-proj)-[A-Za-z0-9_\-]{20,}")

    def mask_key(self, key: str | None) -> str:
        if not key:
            return "not_provided"
        clean = key.strip()
        if len(clean) <= 12:
            return "provided_but_too_short"
        return f"{clean[:7]}...{clean[-4:]}"

    def classify_key(self, key: str | None) -> dict:
        clean = (key or "").strip()
        if not clean:
            return {
                "provided": False,
                "type": "none",
                "masked": "not_provided",
                "format_ok": False,
                "message": "OpenAI API key was not entered. Local analysis remains available.",
            }
        is_project = clean.startswith("sk-proj-")
        is_legacy = clean.startswith("sk-") and not is_project
        format_ok = bool(self.SECRET_PATTERN.fullmatch(clean))
        return {
            "provided": True,
            "type": "project_key" if is_project else ("legacy_key" if is_legacy else "unknown"),
            "masked": self.mask_key(clean),
            "format_ok": format_ok,
            "message": "Key format looks usable, but raw key will not be saved." if format_ok else "Key format is not recognized. Do not save it until verified.",
        }

    def scan_text_for_secrets(self, text: str) -> list[str]:
        found = []
        for match in self.SECRET_PATTERN.finditer(text or ""):
            found.append(self.mask_key(match.group(0)))
        return found

    def scan_paths_for_secrets(self, paths: list[Path]) -> list[dict]:
        rows: list[dict] = []
        for path in paths:
            try:
                if not path.exists() or not path.is_file():
                    continue
                if path.suffix.lower() == ".zip":
                    with zipfile.ZipFile(path) as zf:
                        for info in zf.infolist()[:300]:
                            if info.file_size > 512_000:
                                continue
                            if Path(info.filename).suffix.lower() not in {".txt", ".md", ".json", ".csv", ".env", ".bat", ".ps1", ".py"}:
                                continue
                            try:
                                data = zf.read(info).decode("utf-8", errors="ignore")
                            except Exception:
                                continue
                            hits = self.scan_text_for_secrets(data)
                            if hits:
                                rows.append({"source": str(path), "inside": info.filename, "masked_matches": hits})
                else:
                    if path.stat().st_size > 512_000:
                        continue
                    data = path.read_text(encoding="utf-8", errors="ignore")
                    hits = self.scan_text_for_secrets(data)
                    if hits:
                        rows.append({"source": str(path), "inside": "", "masked_matches": hits})
            except Exception as exc:
                rows.append({"source": str(path), "inside": "", "error": repr(exc), "masked_matches": []})
        return rows

    def write_safe_templates(self, out_dir: Path, env_var_name: str = "OPENAI_API_KEY") -> dict:
        out_dir.mkdir(parents=True, exist_ok=True)
        bat = out_dir / "SET_OPENAI_API_KEY_TEMPLATE.bat"
        ps1 = out_dir / "SET_OPENAI_API_KEY_TEMPLATE.ps1"
        bat.write_text(
            "@echo off\r\n"
            "echo This template does not contain a real API key.\r\n"
            f"setx {env_var_name} \"PASTE_NEW_OPENAI_API_KEY_HERE\"\r\n"
            "echo Restart the app after setting the environment variable.\r\n"
            "pause\r\n",
            encoding="ascii",
        )
        ps1.write_text(
            "# This template does not contain a real API key.\n"
            f"[Environment]::SetEnvironmentVariable('{env_var_name}', 'PASTE_NEW_OPENAI_API_KEY_HERE', 'User')\n"
            "Write-Host 'Restart the app after setting the environment variable.'\n",
            encoding="ascii",
        )
        guide = out_dir / "OPENAI_API_KEY_SAFE_SETUP_GUIDE.txt"
        guide.write_text(
            "OpenAI API Key Safe Setup Guide\n"
            "================================\n"
            "1. Do not paste real keys into source code, reports, ZIP files, or screenshots.\n"
            "2. Use a newly generated/replaced key if a key was exposed in a chat or text file.\n"
            "3. Set OPENAI_API_KEY as a user environment variable.\n"
            "4. Keep paid calls disabled unless you explicitly approve them.\n"
            "5. The program's default mode is local-first zero-cost analysis.\n",
            encoding="utf-8",
        )
        return {"bat_template": str(bat), "ps1_template": str(ps1), "guide": str(guide)}

    def build_report(
        self,
        out_dir: Path,
        config: ApiKeySafetyConfig,
        openai_api_key: str | None = None,
        uploaded_paths: list[Path] | None = None,
        notes: str = "",
    ) -> dict:
        out_dir.mkdir(parents=True, exist_ok=True)
        key_status = self.classify_key(openai_api_key)
        note_secret_hits = self.scan_text_for_secrets(notes)
        file_secret_hits = self.scan_paths_for_secrets(uploaded_paths or [])
        templates = self.write_safe_templates(out_dir, config.env_var_name)
        safety_warnings: list[str] = []
        if key_status.get("provided"):
            safety_warnings.append("Raw OpenAI API key was entered for validation only. It was not saved in this report.")
        if note_secret_hits or file_secret_hits:
            safety_warnings.append("Possible API key text was detected in notes/files. Rotate exposed keys before real use.")
        if config.paid_calls_allowed:
            safety_warnings.append("Paid calls are enabled in the config. This is not recommended for first run.")
        else:
            safety_warnings.append("Paid calls are blocked. Local-first zero-cost mode is active.")
        if config.daily_openai_analysis_limit <= 0:
            safety_warnings.append("OpenAI analysis limit is 0/day. No OpenAI API call should be made by default.")
        conclusion = {
            "current_status": "v56 installation passed, v57 sidebar UI improved, v58 adds OpenAI key safety and rotation workflow.",
            "api_key_file_judgement": "The uploaded text file appears to contain an OpenAI project API key. Treat it as exposed and replace/rotate it before production use.",
            "recommended_next_step": "Use a newly created key via environment variable only; keep local/ZIP analysis first and paid calls blocked.",
            "program_direction": "Python-centered local PC program remains the final deliverable. Inno Setup is only the Windows installer wrapper.",
        }
        report = {
            "version": "58.0.0",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "config": asdict(config),
            "key_status": key_status,
            "note_secret_hits_masked": note_secret_hits,
            "file_secret_hits_masked": file_secret_hits,
            "templates": templates,
            "safety_warnings": safety_warnings,
            "quota_policy": {
                "collection_days_max": config.max_collection_days,
                "local_file_zip_first": config.local_file_first,
                "openai_optional": config.openai_optional,
                "paid_calls_allowed": config.paid_calls_allowed,
                "daily_openai_analysis_limit": config.daily_openai_analysis_limit,
                "monthly_budget_krw": config.monthly_budget_krw,
            },
            "workflow_application": {
                "api_call_mode": "disabled_by_default",
                "input_priority": ["local_files_zip", "manual_notes", "youtube_google_free_quota", "optional_openai_advanced_analysis"],
                "store_raw_key": False,
                "store_masked_key_only": True,
                "env_var_name": config.env_var_name,
            },
            "conclusion": conclusion,
        }
        json_path = out_dir / "v58_openai_api_key_safety_report.json"
        html_path = out_dir / "v58_openai_api_key_safety_report.html"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        html = ["<html><meta charset='utf-8'><body><h1>v58 OpenAI API Key Safety Report</h1>"]
        html.append(f"<p><b>Mode:</b> {config.mode}</p>")
        html.append(f"<p><b>Key status:</b> {key_status.get('type')} / {key_status.get('masked')}</p>")
        html.append("<h2>Safety warnings</h2><ul>")
        for w in safety_warnings:
            html.append(f"<li>{w}</li>")
        html.append("</ul><h2>Conclusion</h2><pre>")
        html.append(json.dumps(conclusion, ensure_ascii=False, indent=2))
        html.append("</pre></body></html>")
        html_path.write_text("\n".join(html), encoding="utf-8")
        report["json_path"] = str(json_path)
        report["html_path"] = str(html_path)
        return report
