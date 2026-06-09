from __future__ import annotations

import csv
import hashlib
import html
import json
import shutil
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from modules.constants import FORMAT_LABELS, PLANNING_COUNTS
from modules.prototype_generator.character_prototype_builder import PrototypeSpec
from modules.submission_package.submission_package_builder import SubmissionPackageBuilder


@dataclass
class FinalSubmissionWizardReport:
    project_name: str
    created_at: str
    format_key: str
    format_label: str
    target_count: int
    gate_status: str
    final_zip_status: str
    final_zip_path: str | None
    package_zip_path: str | None
    manifest_path: str
    html_path: str
    json_path: str
    checklist_csv_path: str
    included_files: list[dict[str, Any]]
    blockers: list[str]
    warnings: list[str]
    next_actions: list[str]
    checksum_sha256: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FinalSubmissionWizard:
    """v31 최종 제출 패키지 생성 마법사.

    v30 제출 전 잠금 체크리스트를 기준으로 최종 ZIP 생성을 통제한다.
    이 기능은 카카오 승인 보장이 아니라, 제출 직전 파일·리포트·증거자료를
    한 폴더/ZIP로 묶어 점검하기 위한 로컬 제작 보조 기능이다.
    """

    def build(
        self,
        output_dir: str | Path,
        *,
        project_name: str,
        format_key: str,
        target_count: int | None,
        spec: PrototypeSpec | None,
        expressions: list[dict[str, Any]] | list[Any] | None,
        lock_report: dict[str, Any] | None,
        linked_reports: dict[str, Any] | None = None,
        allow_draft_when_locked: bool = False,
    ) -> FinalSubmissionWizardReport:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        safe_project = self._safe_name(project_name)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linked_reports = linked_reports or {}
        format_key = format_key if format_key in FORMAT_LABELS else "static_text"
        target = int(target_count or PLANNING_COUNTS.get(format_key, 32))
        target = max(1, min(target, 64))

        blockers: list[str] = []
        warnings: list[str] = []
        lock_ok = self._is_unlocked(lock_report)
        if not lock_report:
            blockers.append("v30 제출 전 잠금 체크리스트 리포트가 없습니다.")
        elif not lock_ok:
            blockers.append("v30 체크리스트가 '최종 ZIP 생성 가능' 상태가 아닙니다.")
            for item in lock_report.get("blockers", [])[:5]:
                label = item.get("label") or item.get("key") or "미통과 필수 항목"
                blockers.append(f"미통과: {label}")

        if not spec:
            warnings.append("선택된 캐릭터 시안이 없어 기본 절차형 시안을 사용합니다. 실제 제출 전 직접 만든 원본/시안으로 다시 생성하세요.")
            spec = self._default_spec(project_name)
        if not expressions:
            warnings.append("표현 세트가 없어 기본 표현으로 최종 패키지를 생성합니다. 실제 제출 전 후보 갤러리에서 24개/32개 세트를 확정하세요.")

        gate_status = "통과" if lock_ok else "잠금"
        final_zip_status = "생성 가능" if lock_ok else ("초안 ZIP만 생성" if allow_draft_when_locked else "생성 차단")
        package_result = None
        package_zip_path: str | None = None
        final_zip_path: str | None = None
        checksum: str | None = None
        included: list[dict[str, Any]] = []

        package_area = out / "package_build"
        final_area = out / "final_bundle"
        if package_area.exists():
            shutil.rmtree(package_area)
        if final_area.exists():
            shutil.rmtree(final_area)
        package_area.mkdir(parents=True, exist_ok=True)
        final_area.mkdir(parents=True, exist_ok=True)

        should_build_zip = lock_ok or allow_draft_when_locked
        if should_build_zip:
            package_result = SubmissionPackageBuilder().build(
                spec,
                expressions,
                package_area,
                project_name=safe_project,
                format_key=format_key,
                target_count=target,
            )
            package_zip_path = package_result.zip_path
            if package_result.warnings:
                warnings.extend([f"제출 패키지 경고: {w}" for w in package_result.warnings])

        # 메타 리포트 먼저 작성
        manifest = {
            "project_name": project_name,
            "created_at": created_at,
            "format_key": format_key,
            "format_label": FORMAT_LABELS.get(format_key, format_key),
            "target_count": target,
            "gate_status": gate_status,
            "final_zip_status": final_zip_status,
            "lock_report_summary": self._summarize_lock(lock_report),
            "linked_report_keys": sorted([k for k, v in linked_reports.items() if v]),
            "package_result": package_result.to_dict() if package_result else None,
            "warnings": warnings,
            "blockers": blockers,
            "notice": "이 ZIP은 제출 준비 보조 자료입니다. 카카오 승인/수익 보장을 의미하지 않으며, 제출 직전 공식 최신 기준을 다시 확인하세요.",
        }
        json_path = out / "final_submission_wizard_report.json"
        json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path = out / "final_submission_wizard_report.html"
        html_path.write_text(self._html(manifest), encoding="utf-8")
        checklist_csv = out / "final_submission_wizard_checklist.csv"
        self._write_csv(checklist_csv, manifest)
        manifest_path = out / "final_submission_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        if should_build_zip and package_zip_path:
            final_zip_path = str(out / f"{safe_project}_v31_final_submission_bundle.zip")
            with zipfile.ZipFile(final_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for p in [json_path, html_path, checklist_csv, manifest_path]:
                    zf.write(p, f"meta/{p.name}")
                    included.append(self._file_info(p, f"meta/{p.name}"))
                package_zip = Path(package_zip_path)
                if package_zip.exists():
                    zf.write(package_zip, f"submission_package/{package_zip.name}")
                    included.append(self._file_info(package_zip, f"submission_package/{package_zip.name}"))
                # 관련 리포트 파일이 있으면 존재하는 경로만 추가
                for key, rep in linked_reports.items():
                    for path_key in ["html_path", "json_path", "csv_path", "zip_path", "report_path", "checklist_path", "manifest_path"]:
                        fp = self._path_from(rep, path_key)
                        if fp and fp.exists() and fp.is_file():
                            arc = f"linked_reports/{key}/{fp.name}"
                            try:
                                zf.write(fp, arc)
                                included.append(self._file_info(fp, arc))
                            except Exception:
                                pass
            checksum = self._sha256(Path(final_zip_path))
            Path(final_zip_path + ".sha256.txt").write_text(checksum, encoding="utf-8")
        else:
            final_zip_path = None

        next_actions = self._next_actions(lock_ok, allow_draft_when_locked, blockers, warnings)
        final_manifest = dict(manifest)
        final_manifest.update({
            "final_zip_path": final_zip_path,
            "package_zip_path": package_zip_path,
            "included_files": included,
            "checksum_sha256": checksum,
            "next_actions": next_actions,
        })
        json_path.write_text(json.dumps(final_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_path.write_text(json.dumps(final_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(self._html(final_manifest), encoding="utf-8")

        return FinalSubmissionWizardReport(
            project_name=project_name,
            created_at=created_at,
            format_key=format_key,
            format_label=FORMAT_LABELS.get(format_key, format_key),
            target_count=target,
            gate_status=gate_status,
            final_zip_status=final_zip_status,
            final_zip_path=final_zip_path,
            package_zip_path=package_zip_path,
            manifest_path=str(manifest_path),
            html_path=str(html_path),
            json_path=str(json_path),
            checklist_csv_path=str(checklist_csv),
            included_files=included,
            blockers=blockers,
            warnings=warnings,
            next_actions=next_actions,
            checksum_sha256=checksum,
        )

    def _is_unlocked(self, report: dict[str, Any] | None) -> bool:
        if not report:
            return False
        status = str(report.get("unlock_status", ""))
        return "가능" in status and not report.get("blockers")

    def _summarize_lock(self, report: dict[str, Any] | None) -> dict[str, Any]:
        if not report:
            return {"status": "없음"}
        return {
            "unlock_status": report.get("unlock_status"),
            "passed_required": report.get("passed_required"),
            "total_required": report.get("total_required"),
            "risk_score": report.get("risk_score"),
            "blocker_count": len(report.get("blockers", [])),
        }

    def _default_spec(self, project_name: str) -> PrototypeSpec:
        return PrototypeSpec(
            name=project_name or "직접창작 캐릭터",
            materials=["보리", "쌀"],
            body_shape="듀오형",
            palette=["#C99A4A", "#F8F4E6", "#2A2A2A", "#FFFFFF"],
            face_style="공손한 미소",
            accessory="말풍선 꼬리",
            motion_hint="문구와 함께 작게 움직이는 인사",
            originality_note="기본 절차형 시안입니다. 실제 제출 전 사용자가 직접 만든 원본/스케치/도형 기반 시안으로 교체하세요.",
        )

    def _path_from(self, rep: Any, key: str) -> Path | None:
        if isinstance(rep, dict) and rep.get(key):
            return Path(str(rep.get(key)))
        return None

    def _file_info(self, path: Path, arcname: str) -> dict[str, Any]:
        return {"path": str(path), "arcname": arcname, "size_bytes": path.stat().st_size, "sha256": self._sha256(path)}

    def _write_csv(self, path: Path, manifest: dict[str, Any]) -> None:
        rows = []
        for key, value in (manifest.get("lock_report_summary") or {}).items():
            rows.append({"section": "lock", "item": key, "value": value})
        for warning in manifest.get("warnings", []):
            rows.append({"section": "warning", "item": "warning", "value": warning})
        for blocker in manifest.get("blockers", []):
            rows.append({"section": "blocker", "item": "blocker", "value": blocker})
        rows.extend([
            {"section": "format", "item": "format_label", "value": manifest.get("format_label")},
            {"section": "format", "item": "target_count", "value": manifest.get("target_count")},
            {"section": "gate", "item": "final_zip_status", "value": manifest.get("final_zip_status")},
        ])
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["section", "item", "value"])
            writer.writeheader()
            writer.writerows(rows)

    def _html(self, manifest: dict[str, Any]) -> str:
        rows = "".join(
            f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
            for k, v in {
                "프로젝트명": manifest.get("project_name"),
                "생성일": manifest.get("created_at"),
                "포맷": manifest.get("format_label"),
                "목표 수량": manifest.get("target_count"),
                "잠금 상태": manifest.get("gate_status"),
                "최종 ZIP 상태": manifest.get("final_zip_status"),
                "최종 ZIP": manifest.get("final_zip_path"),
                "SHA-256": manifest.get("checksum_sha256"),
            }.items()
        )
        blockers = "".join(f"<li>{html.escape(str(x))}</li>" for x in manifest.get("blockers", [])) or "<li>없음</li>"
        warnings = "".join(f"<li>{html.escape(str(x))}</li>" for x in manifest.get("warnings", [])) or "<li>없음</li>"
        actions = "".join(f"<li>{html.escape(str(x))}</li>" for x in manifest.get("next_actions", [])) or "<li>공식 최신 기준 재확인</li>"
        files = "".join(
            f"<tr><td>{html.escape(str(f.get('arcname')))}</td><td>{f.get('size_bytes')}</td><td><code>{html.escape(str(f.get('sha256')))}</code></td></tr>"
            for f in manifest.get("included_files", [])
        )
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<title>v31 최종 제출 패키지 생성 마법사</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55}}table{{border-collapse:collapse;width:100%;margin:12px 0}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#f4f4f4}}code{{font-size:12px}}.box{{background:#fff8e1;border:1px solid #f0d27a;padding:12px;border-radius:8px}}</style>
</head><body><h1>v31 최종 제출 패키지 생성 마법사</h1>
<div class='box'>이 리포트는 제출 준비 보조 자료입니다. 카카오 승인·수익 보장을 의미하지 않으며 제출 직전 공식 최신 기준과 정책을 다시 확인해야 합니다.</div>
<table><tbody>{rows}</tbody></table>
<h2>차단 항목</h2><ul>{blockers}</ul><h2>경고</h2><ul>{warnings}</ul><h2>다음 행동</h2><ul>{actions}</ul>
<h2>포함 파일</h2><table><thead><tr><th>ZIP 내부 경로</th><th>용량</th><th>SHA-256</th></tr></thead><tbody>{files}</tbody></table>
</body></html>"""

    def _next_actions(self, lock_ok: bool, allow_draft: bool, blockers: list[str], warnings: list[str]) -> list[str]:
        if not lock_ok and not allow_draft:
            return ["v30 제출 전 잠금 체크리스트의 필수 항목을 먼저 통과시키세요.", "품질검사·채팅 미리보기·저작권 방어·데이터 백업 리포트를 생성한 뒤 다시 실행하세요."]
        if not lock_ok and allow_draft:
            return ["초안 ZIP은 생성됐지만 제출용으로 사용하지 마세요.", "v30 체크리스트를 통과한 뒤 최종 ZIP을 다시 생성하세요."]
        actions = ["최종 ZIP과 SHA-256 값을 별도 보관하세요.", "카카오 이모티콘 스튜디오 최신 제출 기준과 생성형 AI 제한 정책을 다시 확인하세요."]
        if warnings:
            actions.insert(0, "경고 항목을 검토하고 필요하면 해당 탭에서 보완하세요.")
        return actions

    def _safe_name(self, text: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(text).strip())
        return safe[:80] or "kakao_emoticon_project"

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
