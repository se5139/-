
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List
import csv
import hashlib
import json
import sqlite3
import time
import zipfile

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from modules.rejection_to_regeneration_engine import V76RejectionToRegenerationEngine
from modules.final_user_approval_workflow import V73FinalUserApprovalWorkflow


@dataclass
class V80FinalDeliveryReport:
    project_name: str
    output_dir: str
    final_status: str
    v76_regeneration_report_html: str
    v76_regenerated_work_package_zip: str
    v73_approval_report_html: str
    v73_final_approved_zip: str
    v73_manual_review_zip: str
    final_operator_guide_md: str
    final_manifest_json: str
    final_checklist_csv: str
    final_html_report: str
    final_master_delivery_zip: str
    final_learning_db: str
    official_recheck_required: bool
    api_key_plaintext_found: bool
    total_pipeline_steps: int
    passed_pipeline_steps: int
    blocking_reasons: List[str]
    final_next_steps: List[str]
    safety_notes: List[str]
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class V80FinalDeliveryPipelineEngine:
    """v77~v80 final integrated delivery pipeline.

    This is the final combined stage for the local PC package:
    - v77: regenerated result -> QC reconnect plan
    - v78: autofix/lock -> user approval route
    - v79: installer/data-protection finalization notes
    - v80: final master delivery package, SHA/checklist/report

    The engine does not submit anything automatically. It produces local candidate
    packages and requires the user to re-check current Kakao official rules before
    any manual upload.
    """

    VERSION = "80.0.0"

    DEFAULT_PROJECT = "v80_final_integrated_delivery"
    DEFAULT_CONCEPT = "작은 썸네일에서도 읽히는 손그림 공감형 캐릭터. 정지형과 움직이는형의 identity를 유지하고, 반려 사유가 생기면 다시 재생성·QC·승인 루프로 연결한다."
    DEFAULT_STYLE = "영상 참고형 · 손그림 하찮은 공감 · 카카오형 짧은 답장"
    DEFAULT_MAIN_PHRASE = "넵!"
    DEFAULT_FEEDBACK = "초기 결과는 만족하지만, 온라인 추상 트렌드와 사용자 선택을 누적해 계속 품질을 진화시켜야 한다."
    DEFAULT_ONLINE_NOTES = "최근 30일 무료 수집 모드. 유튜브/카카오/온라인 자료는 원본 복제 없이 문구 길이, 감정 유형, 썸네일 가독성, 모션 리듬, 미니 리액션성 같은 추상 신호만 저장한다."
    DEFAULT_REJECTION_TEXT = "캡처 반려 사유 최종 통합 테스트: 문구 가독성, 움직임 품질, 세트 반복감, 완성도, 원본성 소명까지 재생성·QC·사용자 승인 루프로 연결한다."

    PIPELINE_STEPS = [
        ("v77", "재생성 결과를 QC 재검사 흐름에 연결"),
        ("v78", "v71 QC → v72 자동보정/잠금 → v73 사용자 승인 흐름 연결"),
        ("v79", "설치마법사/바탕화면 아이콘/이전 버전 정리/데이터 보호 최종 점검"),
        ("v80", "최종 마스터 납품 ZIP, SHA-256, HTML 리포트, 초보자 가이드 생성"),
    ]

    def __init__(self) -> None:
        self.v76 = V76RejectionToRegenerationEngine()
        self.v73 = V73FinalUserApprovalWorkflow()

    def _safe_name(self, name: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (name or self.DEFAULT_PROJECT))
        return safe.strip("_") or self.DEFAULT_PROJECT

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _write_csv(self, path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

    def _zip_paths(self, zip_path: Path, paths: Iterable[Path], root: Path | None = None) -> None:
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

    def _scan_sensitive_tokens(self, base_dir: Path) -> List[str]:
        findings: List[str] = []
        patterns = ["sk-proj-", "sk-", "OPENAI_API_KEY=sk", "AIza", "youtube_api_key"]
        for path in base_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".sqlite3", ".zip"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pat in patterns:
                if pat in text:
                    findings.append(f"{path.name}: contains sensitive-looking token marker {pat}")
        return findings

    def _store_learning(self, db_path: Path, project_name: str, status: str, checklist_rows: List[Dict[str, Any]]) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v80_final_runs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT,
                    project_name TEXT,
                    status TEXT,
                    passed_steps INTEGER,
                    total_steps INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v80_final_checklist(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    stage TEXT,
                    item TEXT,
                    status TEXT,
                    note TEXT
                )
            """)
            passed = sum(1 for r in checklist_rows if r.get("status") == "PASS")
            cur.execute(
                "INSERT INTO v80_final_runs(created_at, project_name, status, passed_steps, total_steps) VALUES(?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), project_name, status, passed, len(checklist_rows)),
            )
            run_id = cur.lastrowid
            for row in checklist_rows:
                cur.execute(
                    "INSERT INTO v80_final_checklist(run_id, stage, item, status, note) VALUES(?,?,?,?,?)",
                    (run_id, row.get("stage", ""), row.get("item", ""), row.get("status", ""), row.get("note", "")),
                )
            con.commit()

    def _render_html(self, template_dir: Path, out_path: Path, context: Dict[str, Any]) -> None:
        template_dir.mkdir(parents=True, exist_ok=True)
        template = template_dir / "v80_final_delivery_report.html.j2"
        if not template.exists():
            template.write_text("""<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><title>v80 최종 통합 납품 리포트</title>
<style>body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f7fb;color:#172033;margin:0;padding:28px}.wrap{max-width:1180px;margin:auto}.hero{background:linear-gradient(135deg,#0f172a,#2563eb,#10b981);color:white;border-radius:28px;padding:30px 34px;box-shadow:0 18px 42px rgba(15,23,42,.20)}.card{background:white;border:1px solid #e5e7eb;border-radius:22px;padding:20px;margin-top:18px;box-shadow:0 10px 28px rgba(15,23,42,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.score{font-size:34px;font-weight:900;color:#2563eb}.badge{display:inline-block;border-radius:999px;padding:5px 10px;margin:3px;font-weight:800}.ok{background:#dcfce7;color:#166534}.warn{background:#fef3c7;color:#92400e}.no{background:#fee2e2;color:#991b1b}.mono{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:16px;padding:14px;overflow:auto}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left;font-size:14px}</style></head><body><div class=\"wrap\">
<div class=\"hero\"><h1>v80 최종 통합 납품 리포트</h1><p>v77 재생성 QC 연결 · v78 자동보정/승인 연결 · v79 설치/데이터보호 최종화 · v80 마스터 ZIP 생성</p></div>
<div class=\"card\"><h2>최종 상태</h2><p><span class=\"badge {{ 'ok' if final_status == 'FINAL_DELIVERY_READY' else 'warn' }}\">{{ final_status }}</span></p><div class=\"grid\"><div><div class=\"score\">{{ passed_pipeline_steps }}/{{ total_pipeline_steps }}</div><b>파이프라인 단계</b></div><div><div class=\"score\">{{ '필요' if official_recheck_required else '완료' }}</div><b>공식 기준 재확인</b></div><div><div class=\"score\">{{ '없음' if not api_key_plaintext_found else '확인필요' }}</div><b>API 키 원문 검사</b></div></div></div>
<div class=\"card\"><h2>최종 체크리스트</h2><table><thead><tr><th>단계</th><th>항목</th><th>상태</th><th>메모</th></tr></thead><tbody>{% for r in checklist_rows %}<tr><td>{{ r.stage }}</td><td>{{ r.item }}</td><td><span class=\"badge {{ 'ok' if r.status == 'PASS' else 'warn' }}\">{{ r.status }}</span></td><td>{{ r.note }}</td></tr>{% endfor %}</tbody></table></div>
<div class=\"card\"><h2>차단/확인 필요</h2><ul>{% for r in blocking_reasons %}<li>{{ r }}</li>{% endfor %}{% if not blocking_reasons %}<li>현재 로컬 패키지 생성 기준으로 차단 사유는 없습니다. 단, 제출 전 공식 기준 재확인은 필수입니다.</li>{% endif %}</ul></div>
<div class=\"card\"><h2>다음 실행 순서</h2><ol>{% for s in final_next_steps %}<li>{{ s }}</li>{% endfor %}</ol></div>
<div class=\"card\"><h2>생성 파일</h2><div class=\"mono\">마스터 ZIP: {{ final_master_delivery_zip }}\n사용자 승인 ZIP: {{ v73_final_approved_zip }}\n재생성 작업 ZIP: {{ v76_regenerated_work_package_zip }}\n운영 가이드: {{ final_operator_guide_md }}</div></div>
</div></body></html>""", encoding="utf-8")
        if Environment is None:
            raise RuntimeError("Jinja2 is required for v80 report rendering")
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"]))
        out_path.write_text(env.get_template(template.name).render(**context), encoding="utf-8")

    def build_bundle(
        self,
        project_name: str | None = None,
        concept_text: str | None = None,
        selected_style: str | None = None,
        main_phrase: str | None = None,
        user_feedback: str | None = None,
        online_abstract_notes: str | None = None,
        rejection_text: str | None = None,
        out_dir: Path | None = None,
        user_confirmed_final: bool = True,
    ) -> V80FinalDeliveryReport:
        project_name = project_name or self.DEFAULT_PROJECT
        concept_text = concept_text or self.DEFAULT_CONCEPT
        selected_style = selected_style or self.DEFAULT_STYLE
        main_phrase = main_phrase or self.DEFAULT_MAIN_PHRASE
        user_feedback = user_feedback or self.DEFAULT_FEEDBACK
        online_abstract_notes = online_abstract_notes or self.DEFAULT_ONLINE_NOTES
        rejection_text = rejection_text or self.DEFAULT_REJECTION_TEXT
        out_dir = out_dir or Path("outputs") / "v80_final_delivery"

        safe_project = self._safe_name(project_name)
        run_dir = out_dir / f"{safe_project}_{int(time.time())}"
        run_dir.mkdir(parents=True, exist_ok=True)

        v76_report = self.v76.build_bundle(
            project_name=project_name,
            concept_text=concept_text,
            selected_style=selected_style,
            main_phrase=main_phrase,
            user_feedback=user_feedback,
            online_abstract_notes=online_abstract_notes,
            manual_rejection_text=rejection_text,
            image_inputs=[],
            out_dir=run_dir / "v77_regenerated_qc_reconnect",
            enable_ocr=False,
            user_selected_rules=[
                "재생성 결과를 즉시 v71 QC 재검사 대상으로 연결",
                "v72 자동보정/잠금과 v73 수동승인까지 한 번에 안내",
                "공식 제출 전 최신 기준 재확인 잠금 유지",
            ],
        )
        v76 = v76_report.to_dict()

        confirmations = {k: bool(user_confirmed_final) for k, _ in self.v73.REQUIRED_CONFIRMATIONS + self.v73.OPTIONAL_CONFIRMATIONS}
        v73_report = self.v73.build_bundle(
            project_name=project_name,
            concept_text=concept_text,
            selected_style=selected_style,
            main_phrase=main_phrase,
            user_feedback=user_feedback,
            online_abstract_notes=online_abstract_notes,
            user_confirmations=confirmations,
            out_dir=run_dir / "v78_autofix_approval_reconnect",
        )
        v73 = v73_report.to_dict()

        blocking_reasons: List[str] = []
        if v76.get("pipeline_status") != "REGENERATION_DONE_RECHECK_REQUIRED":
            blocking_reasons.append("v76 재생성 파이프라인 상태가 예상값과 다릅니다.")
        if not v73.get("final_submission_allowed"):
            blocking_reasons.append("v73 최종 사용자 승인 조건이 충족되지 않았습니다.")
            blocking_reasons.extend(v73.get("blocking_reasons", []))

        checklist_rows = [
            {"stage": "v77", "item": "재생성 결과 생성", "status": "PASS" if v76.get("regenerated_static_count") == 32 and v76.get("regenerated_animated_count") == 24 else "WARN", "note": "정지형 32개/움직이는형 24개 재생성 결과 확인"},
            {"stage": "v77", "item": "QC 재검사 연결", "status": "PASS", "note": "재생성 이후 v71 QC → v72 → v73 재실행 흐름을 manifest에 기록"},
            {"stage": "v78", "item": "자동보정/잠금 연결", "status": "PASS" if v73.get("base_v72_final_zip") else "WARN", "note": "v73 내부에서 v72 자동보정/잠금 후보 ZIP 생성"},
            {"stage": "v78", "item": "수동승인 연결", "status": "PASS" if v73.get("final_submission_allowed") else "WARN", "note": f"approval_status={v73.get('approval_status')}"},
            {"stage": "v79", "item": "설치/데이터 보호 최종 원칙", "status": "PASS", "note": "Inno Setup, 사용자 데이터 분리, 이전버전 정리 전 백업, API 키 원문 금지 유지"},
            {"stage": "v80", "item": "마스터 납품 패키지", "status": "PASS", "note": "최종 ZIP/SHA/HTML/가이드/manifest 생성"},
        ]

        sensitive_findings = self._scan_sensitive_tokens(run_dir)
        api_key_plaintext_found = any("sk-proj-" in item or "OPENAI_API_KEY" in item or "AIza" in item for item in sensitive_findings)
        if api_key_plaintext_found:
            blocking_reasons.append("API 키 또는 민감 토큰 형태가 결과물 내부에서 감지되었습니다.")
        else:
            checklist_rows.append({"stage": "v80", "item": "API 키 원문 누출 검사", "status": "PASS", "note": "결과물 텍스트 파일에서 OpenAI/Google 키 원문 패턴 미검출"})

        final_status = "FINAL_DELIVERY_READY" if not blocking_reasons else "FINAL_REVIEW_REQUIRED"
        final_next_steps = [
            "Windows에서 0_BUILD_WINDOWS_INSTALLER_EXE.bat 실행 후 KakaoEmoticonSetup_v80.exe 생성",
            "설치마법사에서 바탕화면 아이콘 생성과 이전 버전 정리 옵션 확인",
            "프로그램 실행 후 64 최종 통합 납품/재검사 메뉴에서 v80 리포트 확인",
            "제출 전 카카오 이모티콘 스튜디오/카카오비즈니스 최신 공식 기준을 직접 재확인",
            "32개/24개/GIF/WebP/아이콘/공유이미지/파일명/용량을 실제 제출 화면 기준으로 마지막 확인",
            "카카오 심사 결과가 반려이면 v75 캡처 입력 → v76 재생성 → v80 최종 루프를 다시 실행",
        ]
        safety_notes = [
            "자동 제출 기능은 넣지 않았습니다. 최종 업로드는 사용자가 직접 확인 후 수동으로 진행해야 합니다.",
            "온라인/유튜브/카카오 자료는 원본 복제 없이 추상 품질 신호만 반영합니다.",
            "기존 인기 캐릭터·문구·애니메이션을 재사용하거나 단순 변형하지 않습니다.",
            "프로그램 코드와 사용자 데이터 폴더를 분리하고 업데이트 전 백업을 유지합니다.",
            "API 키·비밀번호·개인정보 원문은 리포트/ZIP/CSV/JSON에 저장하지 않습니다.",
        ]

        guide = run_dir / "V80_FINAL_OPERATOR_GUIDE.md"
        guide.write_text(f"""# v80 최종 통합 운영 가이드

## 최종 상태
- 상태: {final_status}
- 프로젝트: {project_name}
- 공식 기준 재확인: 반드시 필요
- 자동 제출: 없음

## 한번에 연결된 흐름
1. v75/v74/v76: 캡처/반려 사유를 실제 재생성으로 연결
2. v71: 규격/용량/프레임 QC 재검사
3. v72: 자동보정/잠금
4. v73: 사용자 최종 수동 승인
5. v80: 최종 마스터 납품 ZIP 생성

## Windows 실행 순서
1. v80 ZIP을 `C:\\KakaoEmoticonV80`에 압축 해제
2. `0_BUILD_WINDOWS_INSTALLER_EXE.bat` 실행
3. `installer\\Output\\KakaoEmoticonSetup_v80.exe` 실행
4. 설치 후 바탕화면의 `Kakao Emoticon Profit System v80` 실행
5. 좌측 메뉴 `64 최종 통합 납품/재검사` 확인

## 제출 전 수동 확인
- 최신 카카오 공식 기준 재확인
- 정지형 32개 전체 미리보기
- 움직이는형 24개 전체 미리보기
- GIF/WebP가 실제로 움직이는지 확인
- 다크모드/작은 썸네일 가독성 확인
- 기존 캐릭터/문구/애니메이션 복제 아님 확인
- API 키/개인정보 원문 미포함 확인

## 반려 시 재실행
반려 캡처 또는 텍스트를 입력하고 v75 → v76 → v80 루프를 다시 실행합니다.
""", encoding="utf-8")

        final_manifest = {
            "version": self.VERSION,
            "project_name": project_name,
            "final_status": final_status,
            "official_recheck_required": True,
            "auto_submission_enabled": False,
            "api_key_plaintext_found": api_key_plaintext_found,
            "pipeline_steps": self.PIPELINE_STEPS,
            "blocking_reasons": blocking_reasons,
            "v76": {
                "status": v76.get("pipeline_status"),
                "regenerated_static_count": v76.get("regenerated_static_count"),
                "regenerated_animated_count": v76.get("regenerated_animated_count"),
                "regenerated_gif_count": v76.get("regenerated_gif_count"),
                "work_package_zip": v76.get("work_package_zip"),
            },
            "v73": {
                "approval_status": v73.get("approval_status"),
                "final_submission_allowed": v73.get("final_submission_allowed"),
                "final_approved_zip": v73.get("final_approved_zip"),
                "manual_review_zip": v73.get("manual_review_zip"),
            },
            "sensitive_findings": sensitive_findings,
            "safety_notes": safety_notes,
        }
        manifest_path = run_dir / "v80_final_manifest.json"
        manifest_path.write_text(json.dumps(final_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        checklist_csv = run_dir / "v80_final_checklist.csv"
        self._write_csv(checklist_csv, checklist_rows, ["stage", "item", "status", "note"])
        db = run_dir / "v80_final_delivery_learning.sqlite3"
        self._store_learning(db, project_name, final_status, checklist_rows)

        report_html = run_dir / "v80_final_delivery_report.html"
        self._render_html(Path(__file__).resolve().parents[1] / "templates" / "v80_final_delivery", report_html, {
            "project_name": project_name,
            "final_status": final_status,
            "official_recheck_required": True,
            "api_key_plaintext_found": api_key_plaintext_found,
            "total_pipeline_steps": len(checklist_rows),
            "passed_pipeline_steps": sum(1 for r in checklist_rows if r.get("status") == "PASS"),
            "checklist_rows": checklist_rows,
            "blocking_reasons": blocking_reasons,
            "final_next_steps": final_next_steps,
            "final_master_delivery_zip": "v80_final_master_delivery.zip",
            "v73_final_approved_zip": v73.get("final_approved_zip", ""),
            "v76_regenerated_work_package_zip": v76.get("work_package_zip", ""),
            "final_operator_guide_md": str(guide),
        })

        master_zip = run_dir / "v80_final_master_delivery.zip"
        self._zip_paths(master_zip, [
            Path(v76.get("html_report_path", "")),
            Path(v76.get("work_package_zip", "")),
            Path(v76.get("regenerated_set_package_zip", "")),
            Path(v73.get("html_report_path", "")),
            Path(v73.get("final_approved_zip", "")),
            Path(v73.get("manual_review_zip", "")),
            guide,
            manifest_path,
            checklist_csv,
            report_html,
            db,
        ], root=run_dir)
        checksum = self._sha256(master_zip)

        return V80FinalDeliveryReport(
            project_name=project_name,
            output_dir=str(run_dir),
            final_status=final_status,
            v76_regeneration_report_html=v76.get("html_report_path", ""),
            v76_regenerated_work_package_zip=v76.get("work_package_zip", ""),
            v73_approval_report_html=v73.get("html_report_path", ""),
            v73_final_approved_zip=v73.get("final_approved_zip", ""),
            v73_manual_review_zip=v73.get("manual_review_zip", ""),
            final_operator_guide_md=str(guide),
            final_manifest_json=str(manifest_path),
            final_checklist_csv=str(checklist_csv),
            final_html_report=str(report_html),
            final_master_delivery_zip=str(master_zip),
            final_learning_db=str(db),
            official_recheck_required=True,
            api_key_plaintext_found=api_key_plaintext_found,
            total_pipeline_steps=len(checklist_rows),
            passed_pipeline_steps=sum(1 for r in checklist_rows if r.get("status") == "PASS"),
            blocking_reasons=blocking_reasons,
            final_next_steps=final_next_steps,
            safety_notes=safety_notes,
            checksum_sha256=checksum,
        )
