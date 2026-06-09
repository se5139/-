from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


@dataclass
class SubmissionLockChecklistReport:
    project_name: str
    created_at: str
    unlock_status: str
    passed_required: int
    total_required: int
    passed_optional: int
    total_optional: int
    risk_score: int
    checklist_items: List[Dict[str, Any]]
    blockers: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    next_actions: List[str]
    unlock_certificate_path: str | None
    html_path: str
    json_path: str
    csv_path: str
    zip_path: str
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SubmissionLockChecklistEngine:
    """제출 전 필수 확인을 통과해야 최종 ZIP 생성/제출을 권장하는 잠금 체크리스트.

    이 엔진은 카카오 승인 보장이 아니라, 직접 창작 기반의 제작물에 대해
    품질·저작권·데이터 보호·정책 위험을 최종 확인하도록 돕는 안전장치다.
    """

    REQUIRED_ITEMS = [
        ("origin_evidence", "직접 창작 원본/스케치/자유 드로잉/도형 생성 기록이 있음", "직접 창작 기준/드로잉 리포트"),
        ("ai_no_final", "제출용 완성 이미지를 생성형 AI로 만들거나 AI 사용을 은폐하지 않았음", "AI 정책 대응"),
        ("copyright_report", "저작권/상표권 방어 리포트를 생성하고 고위험 표현을 제거했음", "저작권 방어 센터"),
        ("quality_review", "최종 품질검사에서 크기·용량·투명 배경·문구 잘림을 확인했음", "최종 품질 검사"),
        ("chat_preview", "카카오톡 채팅창 미리보기에서 작은 화면·흰/어두운 배경 가독성을 확인했음", "채팅창 미리보기"),
        ("count_format", "선택 포맷의 24개/32개 등 기획 수량과 파일명이 맞음", "제출 패키지"),
        ("backup_done", "제출 전 현재 프로젝트와 사용자 데이터를 백업했음", "데이터 보호/백업"),
    ]

    OPTIONAL_ITEMS = [
        ("consistency", "세트 전체 캐릭터 크기·색상·위치 일관성을 검사했음", "일관성 검사"),
        ("rejection_review", "반려 사유/문제점이 있다면 v29 개선 리포트로 보완했음", "반려 사유 개선"),
        ("growth_saved", "성장형 학습 엔진에 결과를 저장해 다음 제작 개선에 반영했음", "성장형 학습"),
        ("api_trend", "30일 트렌드/시장성 분석을 확인했음", "무료 API 분석"),
        ("expression_balance", "표현 후보의 감정/상황 균형과 반복감을 확인했음", "후보 갤러리"),
    ]

    def build_report(
        self,
        output_dir: Path | str,
        *,
        project_name: str,
        manual_checks: Dict[str, bool],
        context_reports: Dict[str, Any] | None = None,
        notes: str = "",
    ) -> SubmissionLockChecklistReport:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        context_reports = context_reports or {}
        items: List[Dict[str, Any]] = []

        for key, label, area in self.REQUIRED_ITEMS:
            auto_signal = self._auto_signal(key, context_reports)
            checked = bool(manual_checks.get(key, False))
            passed = checked and auto_signal["status"] != "missing_strong"
            items.append({
                "key": key,
                "type": "required",
                "label": label,
                "area": area,
                "user_checked": checked,
                "auto_status": auto_signal["status"],
                "auto_message": auto_signal["message"],
                "passed": passed,
                "fix_hint": self._fix_hint(key),
            })

        for key, label, area in self.OPTIONAL_ITEMS:
            auto_signal = self._auto_signal(key, context_reports)
            checked = bool(manual_checks.get(key, False))
            passed = checked or auto_signal["status"] in {"present", "ok"}
            items.append({
                "key": key,
                "type": "optional",
                "label": label,
                "area": area,
                "user_checked": checked,
                "auto_status": auto_signal["status"],
                "auto_message": auto_signal["message"],
                "passed": passed,
                "fix_hint": self._fix_hint(key),
            })

        required = [i for i in items if i["type"] == "required"]
        optional = [i for i in items if i["type"] == "optional"]
        passed_required = sum(1 for i in required if i["passed"])
        passed_optional = sum(1 for i in optional if i["passed"])
        blockers = [i for i in required if not i["passed"]]
        warnings = [i for i in optional if not i["passed"]]
        risk_score = max(0, 100 - int((passed_required / max(1, len(required))) * 85) - int((passed_optional / max(1, len(optional))) * 15))
        unlock_status = "최종 ZIP 생성 가능" if not blockers else "최종 ZIP 생성 잠금"
        next_actions = self._next_actions(blockers, warnings)

        certificate_path: str | None = None
        if not blockers:
            certificate = {
                "project_name": project_name,
                "created_at": created_at,
                "unlock_status": unlock_status,
                "required_items_passed": passed_required,
                "required_items_total": len(required),
                "note": "이 인증서는 제출 가능성을 보장하지 않으며, 최종 제출 전 카카오 공식 최신 기준 확인이 필요합니다.",
            }
            cert_file = out / "submission_unlock_certificate.json"
            cert_file.write_text(json.dumps(certificate, ensure_ascii=False, indent=2), encoding="utf-8")
            certificate_path = str(cert_file)

        csv_path = out / "submission_lock_checklist.csv"
        self._write_csv(csv_path, items)

        report_payload = {
            "project_name": project_name,
            "created_at": created_at,
            "unlock_status": unlock_status,
            "passed_required": passed_required,
            "total_required": len(required),
            "passed_optional": passed_optional,
            "total_optional": len(optional),
            "risk_score": risk_score,
            "checklist_items": items,
            "blockers": blockers,
            "warnings": warnings,
            "next_actions": next_actions,
            "notes": notes,
            "context_report_keys": sorted(context_reports.keys()),
            "unlock_certificate_path": certificate_path,
        }
        json_path = out / "submission_lock_checklist_report.json"
        json_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        html_path = out / "submission_lock_checklist_report.html"
        html_path.write_text(self._build_html(report_payload), encoding="utf-8")

        zip_path = out / f"{self._safe_name(project_name)}_v30_submission_lock_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in [csv_path, json_path, html_path]:
                zf.write(p, p.name)
            if certificate_path:
                zf.write(Path(certificate_path), Path(certificate_path).name)

        checksum = self._sha256(zip_path)
        (zip_path.with_suffix(zip_path.suffix + ".sha256.txt")).write_text(checksum, encoding="utf-8")

        return SubmissionLockChecklistReport(
            project_name=project_name,
            created_at=created_at,
            unlock_status=unlock_status,
            passed_required=passed_required,
            total_required=len(required),
            passed_optional=passed_optional,
            total_optional=len(optional),
            risk_score=risk_score,
            checklist_items=items,
            blockers=blockers,
            warnings=warnings,
            next_actions=next_actions,
            unlock_certificate_path=certificate_path,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
            checksum_sha256=checksum,
        )

    def _auto_signal(self, key: str, reports: Dict[str, Any]) -> Dict[str, str]:
        mapping = {
            "origin_evidence": ["human_origin_report", "drawing_canvas_report", "free_drawing_report", "drawing_refine_report", "text_prompt_report"],
            "ai_no_final": ["human_origin_report", "copyright_defense_report"],
            "copyright_report": ["copyright_defense_report"],
            "quality_review": ["quality_review"],
            "chat_preview": ["chat_preview_report"],
            "count_format": ["submission_result", "candidate_gallery_report", "sample_set_report"],
            "backup_done": ["data_safety_report"],
            "consistency": ["consistency_report"],
            "rejection_review": ["rejection_improvement_report"],
            "growth_saved": ["growth_learning_report", "growth_learning_save_result"],
            "api_trend": ["api_trend_report", "trend_result"],
            "expression_balance": ["candidate_gallery_report", "balance"],
        }
        keys = mapping.get(key, [])
        present = [k for k in keys if reports.get(k)]
        if present:
            return {"status": "present", "message": "연결된 리포트 감지: " + ", ".join(present)}
        strong_required = {"origin_evidence", "ai_no_final", "copyright_report", "quality_review", "chat_preview", "count_format", "backup_done"}
        return {
            "status": "missing_strong" if key in strong_required else "missing",
            "message": "연결된 리포트가 없습니다. 사용자가 직접 확인 체크하면 임시 통과 가능하지만, 실제 제출 전 해당 탭 실행을 권장합니다.",
        }

    def _fix_hint(self, key: str) -> str:
        hints = {
            "origin_evidence": "13 직접 창작 기준, 22/24/25 드로잉 관련 탭에서 원본과 체크섬을 생성하세요.",
            "ai_no_final": "AI 완성본 제출/은폐가 아닌지 확인하고 직접 창작 기준 리포트를 생성하세요.",
            "copyright_report": "11 저작권 방어 센터에서 자료 출처·상표·유사 키워드를 점검하세요.",
            "quality_review": "9 최종 품질 검사에서 크기/용량/투명 배경/잘림을 재검사하세요.",
            "chat_preview": "17 채팅창 미리보기에서 작은 크기와 어두운 배경을 확인하세요.",
            "count_format": "7 제출 패키지 또는 15 후보 갤러리에서 수량/파일명/포맷을 확인하세요.",
            "backup_done": "19 데이터 보호/백업에서 업데이트·제출 전 백업 ZIP을 생성하세요.",
            "consistency": "23 일관성 검사로 색상/크기/위치 편차를 확인하세요.",
            "rejection_review": "29 반려 사유 개선에서 문제점을 입력하고 수정안을 만드세요.",
            "growth_saved": "20 성장형 학습 엔진에 현재 결과를 저장하세요.",
            "api_trend": "10 무료 API 분석 강화 또는 2 30일 분석을 실행하세요.",
            "expression_balance": "15 후보 갤러리에서 감정/상황 균형과 반복감을 확인하세요.",
        }
        return hints.get(key, "관련 탭에서 재검토하세요.")

    def _next_actions(self, blockers: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> List[str]:
        actions = [b["fix_hint"] for b in blockers]
        if not actions and warnings:
            actions.extend(w["fix_hint"] for w in warnings[:3])
        if not actions:
            actions.append("잠금 체크리스트 기준 필수 항목은 통과했습니다. 제출 전 카카오 이모티콘 스튜디오 최신 가이드를 다시 확인하세요.")
        return actions

    def _write_csv(self, path: Path, rows: List[Dict[str, Any]]) -> None:
        fields = ["key", "type", "label", "area", "user_checked", "auto_status", "auto_message", "passed", "fix_hint"]
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _build_html(self, payload: Dict[str, Any]) -> str:
        def esc(x: Any) -> str:
            return html.escape(str(x))

        def table(rows: Iterable[Dict[str, Any]], fields: List[str]) -> str:
            rows = list(rows or [])
            if not rows:
                return "<p>없음</p>"
            head = "".join(f"<th>{esc(f)}</th>" for f in fields)
            body = []
            for row in rows:
                body.append("<tr>" + "".join(f"<td>{esc(row.get(f, ''))}</td>" for f in fields) + "</tr>")
            return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"

        status_class = "ok" if payload.get("unlock_status") == "최종 ZIP 생성 가능" else "danger"
        return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>v30 제출 전 잠금 체크리스트</title>
<style>
body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55;color:#222}}
.card{{border:1px solid #ddd;border-radius:12px;padding:18px;margin:16px 0;background:#fafafa}}
.ok{{background:#eaf8ef;border-left:6px solid #28a745;padding:12px}}
.danger{{background:#fff0f0;border-left:6px solid #d33;padding:12px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border:1px solid #ddd;padding:8px;vertical-align:top}}th{{background:#f0f3f8}}
</style></head><body>
<h1>v30 제출 전 잠금 체크리스트</h1>
<div class="card"><b>프로젝트:</b> {esc(payload.get('project_name'))}<br><b>생성 시간:</b> {esc(payload.get('created_at'))}<br><b>상태:</b> <span class="{status_class}">{esc(payload.get('unlock_status'))}</span><br><b>필수 통과:</b> {payload.get('passed_required')} / {payload.get('total_required')}<br><b>선택 통과:</b> {payload.get('passed_optional')} / {payload.get('total_optional')}<br><b>위험 점수:</b> {payload.get('risk_score')} / 100</div>
<div class="card"><h2>필수/선택 체크리스트</h2>{table(payload.get('checklist_items'), ['type','label','area','user_checked','auto_status','passed','fix_hint'])}</div>
<div class="card"><h2>잠금 원인</h2>{table(payload.get('blockers'), ['label','area','auto_message','fix_hint'])}</div>
<div class="card"><h2>주의 항목</h2>{table(payload.get('warnings'), ['label','area','auto_message','fix_hint'])}</div>
<div class="card"><h2>다음 행동</h2><ul>{''.join(f'<li>{esc(a)}</li>' for a in payload.get('next_actions', []))}</ul></div>
<p>이 체크리스트는 심사 통과 보장이 아니라 제출 전 자체 안전 점검입니다.</p>
</body></html>"""

    def _safe_name(self, name: str) -> str:
        return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (name or "project"))[:80] or "project"

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
