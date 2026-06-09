
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import hashlib
import json
from typing import Iterable, Any


AI_COMPLETION_RISK_TERMS = [
    "AI 완성본", "생성형 AI 완성", "이미지 생성 AI", "미드저니", "midjourney",
    "스테이블디퓨전", "stable diffusion", "dall-e", "dalle", "AI가 만든 걸 모르게",
    "AI 티 안나게", "검수 회피", "탐지 우회", "모르게 제출", "속이기",
]

HUMAN_WORKFLOW_STAGES = [
    "1. 손스케치/러프 원본 생성",
    "2. 캐릭터 설정서 작성",
    "3. 직접 레이어 분리: 몸통/눈/입/팔/효과/말풍선",
    "4. 표현별 수동 수정 기록",
    "5. 24종/32종 세트 균형 검토",
    "6. 직접 편집 PNG/GIF 출력",
    "7. 저작권·상표·폰트·자료 출처 기록",
    "8. 제출 전 공식 가이드 재확인",
]

@dataclass
class ComplianceFinding:
    level: str
    title: str
    detail: str
    action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HumanOriginReport:
    project_name: str
    created_at: str
    concept_text: str
    ai_usage_mode: str
    human_input_score: int
    compliance_score: int
    final_status: str
    findings: list[dict[str, Any]]
    workflow_stages: list[str]
    required_evidence: list[str]
    evidence_files: list[dict[str, Any]]
    allowed_ai_uses: list[str]
    blocked_uses: list[str]
    html_path: str
    json_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HumanOriginWorkflow:
    """Create a policy-compliant human-origin workflow report.

    This module deliberately does NOT help hide AI use or bypass platform review.
    Its purpose is to keep the project in a direct-human-creation workflow,
    while allowing AI only for low-risk ideation, phrase brainstorming, and quality checks.
    """

    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest()

    def scan_evidence(self, evidence_paths: Iterable[str | Path]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for raw in evidence_paths:
            path = Path(raw)
            if not path.exists():
                continue
            files = [path] if path.is_file() else [p for p in path.rglob('*') if p.is_file()]
            for p in files[:300]:
                try:
                    records.append({
                        "filename": p.name,
                        "path": str(p),
                        "suffix": p.suffix.lower(),
                        "size_bytes": p.stat().st_size,
                        "modified_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds'),
                        "sha256": self._hash_file(p),
                    })
                except Exception as exc:
                    records.append({"filename": p.name, "path": str(p), "error": str(exc)})
        return records

    def build_report(
        self,
        project_name: str,
        concept_text: str,
        ai_usage_mode: str,
        evidence_paths: Iterable[str | Path],
        output_dir: str | Path,
        has_hand_sketch: bool = False,
        has_layer_files: bool = False,
        has_revision_history: bool = False,
        has_source_license_log: bool = False,
        has_final_package: bool = False,
    ) -> HumanOriginReport:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        findings: list[ComplianceFinding] = []
        text = f"{concept_text}\n{ai_usage_mode}".lower()
        risky_terms = [term for term in AI_COMPLETION_RISK_TERMS if term.lower() in text]
        if risky_terms:
            findings.append(ComplianceFinding(
                "high",
                "AI 사용 은폐/우회 위험 표현 감지",
                ", ".join(risky_terms),
                "AI 사용을 숨기거나 검수를 우회하려는 기능은 제외하고, 직접 창작 증거 기록 방식으로 전환하세요.",
            ))
        if "제출용 완성" in ai_usage_mode or "완성 이미지" in ai_usage_mode:
            findings.append(ComplianceFinding(
                "high",
                "제출용 완성 이미지에 AI 사용 위험",
                "카카오 운영 원칙상 생성형 AI 활용 이모티콘 제안은 제한될 수 있습니다.",
                "제출용 이미지는 직접 스케치/레이어/수동 편집 기반으로 다시 제작하고 기록을 남기세요.",
            ))
        evidence_files = self.scan_evidence(evidence_paths)
        flags = {
            "손스케치/러프 원본": has_hand_sketch,
            "레이어 파일": has_layer_files,
            "수정 이력": has_revision_history,
            "출처/라이선스 기록": has_source_license_log,
            "최종 제출 패키지": has_final_package,
        }
        for label, ok in flags.items():
            if not ok:
                findings.append(ComplianceFinding(
                    "medium",
                    f"{label} 증거 부족",
                    f"{label} 체크가 아직 완료되지 않았습니다.",
                    f"{label}을 저장하고 SHA-256 증거 기록에 포함하세요.",
                ))
        human_input_score = sum(20 for ok in flags.values() if ok)
        penalty = 0
        for f in findings:
            penalty += 25 if f.level == "high" else 10 if f.level == "medium" else 3
        compliance_score = max(0, min(100, human_input_score - penalty + 20))
        if any(f.level == "high" for f in findings):
            final_status = "제출 전 수정 필요"
        elif compliance_score >= 80:
            final_status = "직접 창작 증거 양호"
        else:
            final_status = "증거 보완 후 제출 권장"
        required_evidence = [
            "손스케치/러프 원본 파일",
            "캐릭터 설정서와 세계관 메모",
            "레이어 원본 파일: 몸통/눈/입/팔/효과/문구",
            "수정 전후 파일 또는 작업 단계 캡처",
            "표현 24종/32종 목록과 수정 메모",
            "폰트·효과·이미지 출처/라이선스 표",
            "최종 PNG/GIF 출력물과 생성 시각",
            "카카오 공식 가이드 재확인 메모",
        ]
        allowed_ai_uses = [
            "시장/키워드 분석 보조",
            "문구 후보 브레인스토밍",
            "표현 은행 분류/중복 검사",
            "품질 검사/가독성/용량 검사",
            "저작권 위험 키워드 경고",
        ]
        blocked_uses = [
            "제출용 완성 이미지 생성",
            "기존 캐릭터 스타일 모방 프롬프트",
            "AI 사용 사실 은폐 또는 검수 우회",
            "타인 이미지/이모티콘 대량 저장 후 복제",
        ]
        report = HumanOriginReport(
            project_name=project_name,
            created_at=datetime.now().isoformat(timespec='seconds'),
            concept_text=concept_text,
            ai_usage_mode=ai_usage_mode,
            human_input_score=human_input_score,
            compliance_score=compliance_score,
            final_status=final_status,
            findings=[f.to_dict() for f in findings],
            workflow_stages=HUMAN_WORKFLOW_STAGES,
            required_evidence=required_evidence,
            evidence_files=evidence_files,
            allowed_ai_uses=allowed_ai_uses,
            blocked_uses=blocked_uses,
            html_path=str(out / "human_origin_compliance_report.html"),
            json_path=str(out / "human_origin_compliance_report.json"),
        )
        self._write_json(report)
        self._write_html(report)
        return report

    def _write_json(self, report: HumanOriginReport) -> None:
        Path(report.json_path).write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

    def _write_html(self, report: HumanOriginReport) -> None:
        def rows(items):
            return "".join(f"<tr><td>{i}</td></tr>" for i in items)
        finding_rows = "".join(
            f"<tr><td>{f['level']}</td><td>{f['title']}</td><td>{f['detail']}</td><td>{f['action']}</td></tr>"
            for f in report.findings
        ) or "<tr><td colspan='4'>특이사항 없음</td></tr>"
        evidence_rows = "".join(
            f"<tr><td>{e.get('filename','')}</td><td>{e.get('suffix','')}</td><td>{e.get('size_bytes','')}</td><td><code>{e.get('sha256','')}</code></td></tr>"
            for e in report.evidence_files[:200]
        ) or "<tr><td colspan='4'>증거 파일 없음</td></tr>"
        html = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>직접 창작 기준 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55}} table{{border-collapse:collapse;width:100%;margin:12px 0}}td,th{{border:1px solid #ddd;padding:8px;vertical-align:top}}th{{background:#f5f5f5}} .box{{padding:12px;border-radius:8px;background:#f7f7f7;margin:12px 0}} code{{font-size:11px}}</style></head><body>
<h1>직접 창작 기준 / AI 정책 대응 리포트</h1>
<div class='box'><b>프로젝트:</b> {report.project_name}<br><b>판정:</b> {report.final_status}<br><b>직접 창작 증거 점수:</b> {report.human_input_score}/100<br><b>준수 점수:</b> {report.compliance_score}/100</div>
<p>이 리포트는 AI 사용을 숨기거나 검수를 우회하기 위한 문서가 아니라, 직접 창작 과정과 자료 출처를 정리하기 위한 내부 검토 자료입니다.</p>
<h2>발견 항목</h2><table><tr><th>수준</th><th>항목</th><th>내용</th><th>조치</th></tr>{finding_rows}</table>
<h2>직접 창작 권장 단계</h2><table>{rows(report.workflow_stages)}</table>
<h2>필수 증거 자료</h2><table>{rows(report.required_evidence)}</table>
<h2>허용 가능한 AI 보조 범위</h2><table>{rows(report.allowed_ai_uses)}</table>
<h2>차단해야 할 사용</h2><table>{rows(report.blocked_uses)}</table>
<h2>증거 파일 SHA-256</h2><table><tr><th>파일</th><th>형식</th><th>용량</th><th>SHA-256</th></tr>{evidence_rows}</table>
</body></html>"""
        Path(report.html_path).write_text(html, encoding='utf-8')
