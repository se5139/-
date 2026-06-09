from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List
import csv
import hashlib
import json
import shutil
import sqlite3
import time
import zipfile

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from modules.submission_autofix_lock_engine import V72SubmissionAutofixLockEngine


@dataclass
class V73FinalUserApprovalReport:
    project_name: str
    output_dir: str
    base_v72_html_report: str
    base_v72_final_zip: str
    base_v72_locked_zip: str
    approval_status: str
    final_submission_allowed: bool
    approval_score: int
    required_checked_count: int
    required_total_count: int
    optional_checked_count: int
    blocking_reasons: List[str]
    user_confirmations: Dict[str, bool]
    approval_checklist_csv: str
    approval_manifest_json: str
    html_report_path: str
    final_approved_zip: str
    manual_review_zip: str
    learning_db: str
    checksum_sha256: str
    safety_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class V73FinalUserApprovalWorkflow(V72SubmissionAutofixLockEngine):
    """v73 최종 사용자 확인/수동 승인 워크플로우.

    v72 자동보정/잠금 결과를 그대로 신뢰해 자동 제출하지 않고, 사용자가 직접
    캐릭터 원본성, 문구, 32/24 전체 미리보기, GIF, 저작권/유사성, 공식 기준
    재확인 여부를 체크해야 최종 승인 ZIP을 열어준다.
    """

    VERSION = "73.0.0"

    REQUIRED_CONFIRMATIONS = [
        ("human_origin_checked", "직접 창작 원본/스케치/도형/입력 기반임을 확인"),
        ("static_32_reviewed", "정지형 32개 전체 미리보기 확인"),
        ("animated_24_reviewed", "움직이는형 24개 전체 미리보기 확인"),
        ("required_gif_reviewed", "필수 GIF 3개 이상을 실제 움직임으로 확인"),
        ("phrases_reviewed", "문구 오탈자/과도한 길이/상황 적합성 확인"),
        ("darkmode_readability_checked", "다크모드/작은 썸네일 가독성 확인"),
        ("copyright_similarity_checked", "기존 캐릭터·문구·애니메이션 복제 아님 확인"),
        ("official_spec_rechecked", "제출 직전 최신 카카오 공식 기준 재확인"),
        ("api_key_not_included_checked", "API 키·비밀번호·개인정보 원문 미포함 확인"),
        ("user_final_approval", "사용자 최종 승인"),
    ]

    OPTIONAL_CONFIRMATIONS = [
        ("backup_done", "제출 전 작업 폴더/사용자 데이터 백업 완료"),
        ("series_plan_saved", "2탄/미니/큰 이모티콘 확장 메모 저장"),
        ("trend_notes_saved", "온라인 추상 트렌드 신호 메모 저장"),
        ("rejection_plan_ready", "반려 시 수정 계획/개선 체크리스트 준비"),
    ]

    def _sha256_v73(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _zip_paths_v73(self, zip_path: Path, paths: List[Path], root: Path | None = None) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                if not p.exists():
                    continue
                if p.is_dir():
                    for child in p.rglob("*"):
                        if child.is_file():
                            try:
                                arc = str(child.relative_to(root or p.parent))
                            except Exception:
                                arc = child.name
                            zf.write(child, arc)
                else:
                    try:
                        arc = str(p.relative_to(root)) if root else p.name
                    except Exception:
                        arc = p.name
                    zf.write(p, arc)

    def _write_checklist(self, path: Path, confirmations: Dict[str, bool]) -> None:
        rows: List[Dict[str, Any]] = []
        for key, label in self.REQUIRED_CONFIRMATIONS:
            rows.append({"type": "required", "key": key, "label": label, "checked": bool(confirmations.get(key, False))})
        for key, label in self.OPTIONAL_CONFIRMATIONS:
            rows.append({"type": "optional", "key": key, "label": label, "checked": bool(confirmations.get(key, False))})
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["type", "key", "label", "checked"])
            writer.writeheader()
            writer.writerows(rows)

    def _store_v73_learning(self, db: Path, project_name: str, status: str, score: int, confirmations: Dict[str, bool]) -> None:
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v73_final_user_approval_runs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    approval_status TEXT,
                    approval_score INTEGER,
                    required_checked_count INTEGER,
                    required_total_count INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v73_final_user_approval_items(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    item_key TEXT,
                    checked INTEGER
                )
            """)
            required_checked = sum(1 for k, _ in self.REQUIRED_CONFIRMATIONS if confirmations.get(k, False))
            cur.execute(
                "INSERT INTO v73_final_user_approval_runs(created_at, project_name, approval_status, approval_score, required_checked_count, required_total_count) VALUES(?,?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), project_name, status, int(score), required_checked, len(self.REQUIRED_CONFIRMATIONS)),
            )
            run_id = cur.lastrowid
            for key, _ in self.REQUIRED_CONFIRMATIONS + self.OPTIONAL_CONFIRMATIONS:
                cur.execute("INSERT INTO v73_final_user_approval_items(run_id, item_key, checked) VALUES(?,?,?)", (run_id, key, int(bool(confirmations.get(key, False)))))
            con.commit()

    def _render_v73_report(self, template_dir: Path, out_path: Path, context: Dict[str, Any]) -> None:
        template_dir.mkdir(parents=True, exist_ok=True)
        template = template_dir / "v73_final_user_approval_report.html.j2"
        if not template.exists():
            template.write_text("""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>v73 최종 사용자 확인/수동 승인 리포트</title>
<style>
body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;color:#172033;margin:0;padding:28px}.wrap{max-width:1160px;margin:auto}.hero{background:linear-gradient(135deg,#111827,#7c3aed,#f97316);color:white;border-radius:28px;padding:28px 32px;box-shadow:0 18px 42px rgba(15,23,42,.20)}.card{background:white;border:1px solid #e5e7eb;border-radius:22px;padding:20px;margin-top:18px;box-shadow:0 10px 28px rgba(15,23,42,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.score{font-size:34px;font-weight:900;color:#7c3aed}.badge{display:inline-block;border-radius:999px;padding:5px 10px;margin:3px;font-weight:800}.ok{background:#dcfce7;color:#166534}.no{background:#fee2e2;color:#991b1b}.wait{background:#fef3c7;color:#92400e}.mono{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:16px;padding:14px;overflow:auto}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left;font-size:14px}
</style></head><body><div class="wrap"><div class="hero"><h1>v73 최종 사용자 확인/수동 승인 리포트</h1><p>자동보정 결과를 최종 제출 후보로 내보내기 전, 사용자가 직접 확인하고 승인하는 단계입니다.</p></div>
<div class="card"><h2>승인 상태</h2><p><span class="badge {{ 'ok' if final_submission_allowed else 'wait' }}">{{ approval_status }}</span></p><div class="grid"><div><div class="score">{{ approval_score }}</div><b>승인 점수</b></div><div><div class="score">{{ required_checked_count }}/{{ required_total_count }}</div><b>필수 확인</b></div><div><div class="score">{{ optional_checked_count }}</div><b>선택 확인</b></div></div></div>
<div class="card"><h2>필수 확인 항목</h2><table><thead><tr><th>상태</th><th>항목</th></tr></thead><tbody>{% for item in required_items %}<tr><td><span class="badge {{ 'ok' if item.checked else 'no' }}">{{ '확인' if item.checked else '미확인' }}</span></td><td>{{ item.label }}</td></tr>{% endfor %}</tbody></table></div>
<div class="card"><h2>잠금/차단 사유</h2><ul>{% for r in blocking_reasons %}<li>{{ r }}</li>{% endfor %}{% if not blocking_reasons %}<li>현재 사용자 확인 기준으로 최종 승인 후보 ZIP 생성이 가능합니다.</li>{% endif %}</ul></div>
<div class="card"><h2>안전 메모</h2><div class="mono">{{ safety_note }}</div></div>
</div></body></html>""", encoding="utf-8")
        if Environment is None:
            raise RuntimeError("Jinja2 is required for v73 report rendering")
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"]))
        out_path.write_text(env.get_template(template.name).render(**context), encoding="utf-8")

    def build_bundle(
        self,
        project_name: str,
        concept_text: str,
        selected_style: str,
        main_phrase: str,
        user_feedback: str,
        online_abstract_notes: str,
        user_confirmations: Dict[str, bool],
        out_dir: Path,
    ) -> V73FinalUserApprovalReport:
        safe_project = self._safe_name_v70(project_name or "v73_final_user_approval")
        run_dir = out_dir / f"{safe_project}_{int(time.time())}"
        run_dir.mkdir(parents=True, exist_ok=True)

        base_v72 = super().build_bundle(
            project_name=project_name,
            concept_text=concept_text,
            selected_style=selected_style,
            selected_rules=self.AUTOFIX_RULES,
            main_phrase=main_phrase,
            user_feedback=user_feedback,
            online_abstract_notes=online_abstract_notes,
            out_dir=run_dir / "base_v72_autofix_lock",
        )
        v72 = base_v72.to_dict()

        blocking: List[str] = []
        if v72.get("submission_lock_required"):
            blocking.append("v72 자동보정/잠금 단계에서 잠금 사유가 남아 있습니다.")
            blocking.extend(v72.get("lock_reasons", []))
        missing_required = [label for key, label in self.REQUIRED_CONFIRMATIONS if not user_confirmations.get(key, False)]
        for label in missing_required:
            blocking.append(f"필수 확인 미완료: {label}")

        required_checked = len(self.REQUIRED_CONFIRMATIONS) - len(missing_required)
        optional_checked = sum(1 for key, _ in self.OPTIONAL_CONFIRMATIONS if user_confirmations.get(key, False))
        final_allowed = not blocking
        approval_status = "USER_APPROVED_FINAL_CANDIDATE" if final_allowed else "WAITING_USER_REVIEW"
        approval_score = min(100, int(required_checked / len(self.REQUIRED_CONFIRMATIONS) * 90) + min(10, optional_checked * 3))

        checklist_csv = run_dir / "v73_user_approval_checklist.csv"
        self._write_checklist(checklist_csv, user_confirmations)
        manifest = {
            "version": self.VERSION,
            "project_name": project_name,
            "approval_status": approval_status,
            "final_submission_allowed": final_allowed,
            "approval_score": approval_score,
            "required_checked_count": required_checked,
            "required_total_count": len(self.REQUIRED_CONFIRMATIONS),
            "optional_checked_count": optional_checked,
            "blocking_reasons": blocking,
            "user_confirmations": user_confirmations,
            "base_v72": {
                "package_status": v72.get("package_status"),
                "submission_lock_required": v72.get("submission_lock_required"),
                "final_submission_zip": v72.get("final_submission_zip"),
                "locked_review_zip": v72.get("locked_review_zip"),
            },
            "official_recheck_required": True,
            "manual_user_approval_required": True,
        }
        approval_manifest = run_dir / "v73_user_approval_manifest.json"
        approval_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        safety_notes = [
            "v73은 자동 제출 기능이 아니라 사용자의 최종 확인/수동 승인 워크플로우입니다.",
            "최종 승인 ZIP은 로컬 후보일 뿐이며 카카오 승인이나 수익을 보장하지 않습니다.",
            "제출 직전 카카오 이모티콘 스튜디오의 최신 공식 기준을 다시 확인해야 합니다.",
            "기존 캐릭터·문구·애니메이션 복제 금지 원칙을 유지합니다.",
            "API 키 원문, 비밀번호, 개인정보 원문을 결과 ZIP에 포함하지 않습니다.",
        ]
        html_report = run_dir / "v73_final_user_approval_report.html"
        required_items = [{"key": k, "label": l, "checked": bool(user_confirmations.get(k, False))} for k, l in self.REQUIRED_CONFIRMATIONS]
        self._render_v73_report(Path(__file__).resolve().parents[1] / "templates" / "v73_final_user_approval", html_report, {
            "project_name": project_name,
            "approval_status": approval_status,
            "final_submission_allowed": final_allowed,
            "approval_score": approval_score,
            "required_checked_count": required_checked,
            "required_total_count": len(self.REQUIRED_CONFIRMATIONS),
            "optional_checked_count": optional_checked,
            "required_items": required_items,
            "blocking_reasons": blocking,
            "safety_note": "\n".join(safety_notes),
        })

        db = run_dir / "v73_final_user_approval_learning.sqlite3"
        self._store_v73_learning(db, project_name, approval_status, approval_score, user_confirmations)

        approved_zip = run_dir / "v73_user_approved_final_candidate.zip"
        review_zip = run_dir / "v73_manual_review_package.zip"
        base_final = Path(v72.get("final_submission_zip", ""))
        base_locked = Path(v72.get("locked_review_zip", ""))
        if final_allowed:
            self._zip_paths_v73(approved_zip, [base_final, html_report, checklist_csv, approval_manifest, db], root=run_dir)
            self._zip_paths_v73(review_zip, [base_locked, html_report, checklist_csv, approval_manifest], root=run_dir)
            checksum_target = approved_zip
        else:
            self._zip_paths_v73(review_zip, [base_locked, html_report, checklist_csv, approval_manifest, db], root=run_dir)
            self._zip_paths_v73(approved_zip, [html_report, approval_manifest], root=run_dir)
            checksum_target = review_zip
        checksum = self._sha256_v73(checksum_target)

        return V73FinalUserApprovalReport(
            project_name=project_name,
            output_dir=str(run_dir),
            base_v72_html_report=v72.get("html_report_path", ""),
            base_v72_final_zip=v72.get("final_submission_zip", ""),
            base_v72_locked_zip=v72.get("locked_review_zip", ""),
            approval_status=approval_status,
            final_submission_allowed=final_allowed,
            approval_score=approval_score,
            required_checked_count=required_checked,
            required_total_count=len(self.REQUIRED_CONFIRMATIONS),
            optional_checked_count=optional_checked,
            blocking_reasons=blocking,
            user_confirmations=user_confirmations,
            approval_checklist_csv=str(checklist_csv),
            approval_manifest_json=str(approval_manifest),
            html_report_path=str(html_report),
            final_approved_zip=str(approved_zip),
            manual_review_zip=str(review_zip),
            learning_db=str(db),
            checksum_sha256=checksum,
            safety_notes=safety_notes,
        )
