from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import csv
import hashlib
import html
import json
import re
import time

from modules.constants import AI_RISK_KEYWORDS, FORBIDDEN_STYLE_KEYWORDS


@dataclass
class AssetLicenseRecord:
    filename: str
    asset_type: str
    source: str
    license_type: str
    commercial_use: str
    modification_allowed: str
    attribution_required: str
    risk_score: int
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceFileRecord:
    file_path: str
    file_name: str
    file_type: str
    size_bytes: int
    sha256: str
    modified_at: str
    purpose: str
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DefenseFinding:
    category: str
    severity: str
    score: int
    finding: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DefenseReport:
    project_name: str
    overall_risk_score: int
    final_status: str
    summary: str
    findings: list[DefenseFinding]
    asset_records: list[AssetLicenseRecord]
    evidence_records: list[EvidenceFileRecord]
    ai_usage_check: dict[str, Any]
    originality_check: dict[str, Any]
    required_actions: list[str]
    html_path: str
    json_path: str
    csv_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "overall_risk_score": self.overall_risk_score,
            "final_status": self.final_status,
            "summary": self.summary,
            "findings": [x.to_dict() for x in self.findings],
            "asset_records": [x.to_dict() for x in self.asset_records],
            "evidence_records": [x.to_dict() for x in self.evidence_records],
            "ai_usage_check": self.ai_usage_check,
            "originality_check": self.originality_check,
            "required_actions": self.required_actions,
            "html_path": self.html_path,
            "json_path": self.json_path,
            "csv_path": self.csv_path,
        }


class CopyrightDefenseCenter:
    """저작권/상표권/AI 정책 위험을 '법적 판정'이 아닌 제작 전 방어 리포트로 정리합니다."""

    allowed_commercial_markers = ["직접 제작", "직접 촬영", "상업 이용 가능", "OFL", "CC0", "공공누리 제1유형", "구매 라이선스"]
    risky_license_markers = ["출처 모름", "인터넷 캡처", "팬아트", "스크린샷", "기존 캐릭터", "상업 불가", "개인용"]

    def make_asset_records(self, rows: Iterable[dict[str, Any]]) -> list[AssetLicenseRecord]:
        records: list[AssetLicenseRecord] = []
        for row in rows:
            filename = str(row.get("filename", "")).strip() or "미기재"
            asset_type = str(row.get("asset_type", "기타")).strip() or "기타"
            source = str(row.get("source", "")).strip() or "미기재"
            license_type = str(row.get("license_type", "")).strip() or "미기재"
            commercial_use = str(row.get("commercial_use", "미확인")).strip() or "미확인"
            modification_allowed = str(row.get("modification_allowed", "미확인")).strip() or "미확인"
            attribution_required = str(row.get("attribution_required", "미확인")).strip() or "미확인"
            note = str(row.get("note", "")).strip()
            blob = " ".join([source, license_type, commercial_use, modification_allowed, attribution_required, note])
            risk = self._license_risk(blob)
            records.append(AssetLicenseRecord(
                filename=filename,
                asset_type=asset_type,
                source=source,
                license_type=license_type,
                commercial_use=commercial_use,
                modification_allowed=modification_allowed,
                attribution_required=attribution_required,
                risk_score=risk,
                note=note,
            ))
        return records

    def scan_evidence_files(self, paths: Iterable[str | Path], purpose: str = "창작 과정 증거") -> list[EvidenceFileRecord]:
        records: list[EvidenceFileRecord] = []
        for raw in paths:
            if not raw:
                continue
            p = Path(raw)
            candidates = []
            if p.exists() and p.is_file():
                candidates = [p]
            elif p.exists() and p.is_dir():
                candidates = [x for x in p.rglob("*") if x.is_file() and not x.name.startswith(".")]
            for fp in candidates[:300]:
                try:
                    data = fp.read_bytes()
                    digest = hashlib.sha256(data).hexdigest()
                    stat = fp.stat()
                    records.append(EvidenceFileRecord(
                        file_path=str(fp),
                        file_name=fp.name,
                        file_type=fp.suffix.lower() or "unknown",
                        size_bytes=stat.st_size,
                        sha256=digest,
                        modified_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                        purpose=purpose,
                        note="원본/수정/출력 이력 증빙용 체크섬 기록",
                    ))
                except Exception:
                    continue
        return records

    def analyze_ai_usage(self, ai_usage_mode: str, prompts_or_notes: str) -> dict[str, Any]:
        text = f"{ai_usage_mode} {prompts_or_notes}".lower()
        hits = [kw for kw in AI_RISK_KEYWORDS if kw.lower() in text]
        risk = 0
        mode = ai_usage_mode.strip()
        if "제출용 완성" in mode or "완성 이미지" in mode:
            risk += 80
        elif "시안" in mode or "참고" in mode:
            risk += 35
        elif "문구" in mode or "아이디어" in mode or "사용 안 함" in mode:
            risk += 10
        risk += min(20, len(hits) * 5)
        risk = min(100, risk)
        status = "낮음" if risk <= 25 else "주의" if risk <= 55 else "높음"
        return {
            "mode": ai_usage_mode,
            "risk_score": risk,
            "status": status,
            "detected_keywords": hits,
            "recommendation": "제출용 완성 이미지는 직접 제작 레이어/원본 기반으로 유지하고, AI는 기획·문구·아이디어 보조로 분리 기록하세요.",
        }

    def analyze_originality(self, concept_text: str, phrase_text: str, visual_notes: str) -> dict[str, Any]:
        raw = f"{concept_text}\n{phrase_text}\n{visual_notes}"
        lowered = raw.lower()
        forbidden_hits = [kw for kw in FORBIDDEN_STYLE_KEYWORDS if kw.lower() in lowered]
        mimic_patterns = re.findall(r"(.{0,8}(비슷|느낌|스타일|따라|닮게|같이).{0,8})", raw)
        common_materials = ["고양이", "강아지", "토끼", "곰", "직장인", "감자", "고구마"]
        common_hits = [m for m in common_materials if m in raw]
        risk = min(100, len(forbidden_hits) * 18 + len(mimic_patterns) * 12 + max(0, len(common_hits)-2) * 4)
        originality_score = max(0, 100 - risk + (10 if any(x in raw for x in ["세계관", "말투", "시그니처", "움직임", "독창"]) else 0))
        originality_score = min(100, originality_score)
        return {
            "risk_score": risk,
            "originality_score": originality_score,
            "forbidden_hits": forbidden_hits,
            "mimic_phrase_hits": [m[0] for m in mimic_patterns],
            "common_material_hits": common_hits,
            "recommendation": "흔한 소재는 가능하지만 외형·말투·세계관·움직임 중 최소 2개 이상을 독자적으로 설계하세요.",
        }

    def build_report(
        self,
        project_name: str,
        concept_text: str,
        phrase_text: str,
        visual_notes: str,
        ai_usage_mode: str,
        ai_notes: str,
        asset_rows: Iterable[dict[str, Any]],
        evidence_paths: Iterable[str | Path],
        output_dir: str | Path,
    ) -> DefenseReport:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        asset_records = self.make_asset_records(asset_rows)
        evidence_records = self.scan_evidence_files(evidence_paths)
        ai_check = self.analyze_ai_usage(ai_usage_mode, ai_notes)
        originality = self.analyze_originality(concept_text, phrase_text, visual_notes)

        findings: list[DefenseFinding] = []
        if originality["forbidden_hits"]:
            findings.append(DefenseFinding(
                category="유사 캐릭터/브랜드 키워드",
                severity="높음",
                score=85,
                finding="기존 유명 캐릭터·브랜드 또는 모방 방향 키워드가 감지되었습니다: " + ", ".join(originality["forbidden_hits"]),
                recommendation="해당 키워드를 제거하고 외형·색상·말투·세계관을 독립 방향으로 재설계하세요.",
            ))
        if originality["mimic_phrase_hits"]:
            findings.append(DefenseFinding(
                category="모방 표현",
                severity="주의",
                score=60,
                finding="'느낌/스타일/비슷하게' 계열 표현이 감지되었습니다.",
                recommendation="참조 대상이 아닌 캐릭터 고유 설정과 동작 언어로 다시 작성하세요.",
            ))
        if ai_check["risk_score"] >= 55:
            findings.append(DefenseFinding(
                category="AI 활용 위험",
                severity="높음",
                score=ai_check["risk_score"],
                finding="제출용 완성 이미지에 생성형 AI 사용 가능성이 높게 기록되었습니다.",
                recommendation="AI 사용분은 기획 참고로 분리하고, 제출본은 직접 제작 원본/레이어 기반으로 다시 구성하세요.",
            ))
        elif ai_check["risk_score"] >= 30:
            findings.append(DefenseFinding(
                category="AI 활용 기록 필요",
                severity="주의",
                score=ai_check["risk_score"],
                finding="AI가 시안/참고 단계에 사용된 것으로 기록되었습니다.",
                recommendation="AI 결과물을 직접 제출하지 않았다는 구분과 직접 수정/제작 기록을 남기세요.",
            ))
        high_asset = [r for r in asset_records if r.risk_score >= 65]
        if high_asset:
            findings.append(DefenseFinding(
                category="자료/폰트 라이선스",
                severity="높음",
                score=max(r.risk_score for r in high_asset),
                finding=f"출처·상업 이용·수정 허용이 불명확한 자료 {len(high_asset)}건이 있습니다.",
                recommendation="출처를 직접 제작/직접 촬영/상업 이용 가능 라이선스로 재확인하거나 해당 자료를 제외하세요.",
            ))
        if not evidence_records:
            findings.append(DefenseFinding(
                category="창작 과정 증거",
                severity="주의",
                score=45,
                finding="원본 스케치/레이어/출력물 체크섬 기록이 없습니다.",
                recommendation="원본 스케치, 레이어, 수정 전후 파일, 최종 산출물을 증거 경로에 포함하세요.",
            ))

        raw_scores = [originality["risk_score"], ai_check["risk_score"]] + [r.risk_score for r in asset_records] + [f.score for f in findings]
        overall = min(100, int(sum(raw_scores) / max(1, len(raw_scores))) + (8 if not evidence_records else 0))
        final_status = "방어 자료 양호" if overall <= 25 else "보완 후 제출 권장" if overall <= 55 else "제출 전 수정 필요"
        required_actions = self._required_actions(findings, asset_records, evidence_records)
        summary = f"{project_name} 저작권 방어 점수는 {overall}/100입니다. 판정: {final_status}."

        report = DefenseReport(
            project_name=project_name,
            overall_risk_score=overall,
            final_status=final_status,
            summary=summary,
            findings=findings,
            asset_records=asset_records,
            evidence_records=evidence_records,
            ai_usage_check=ai_check,
            originality_check=originality,
            required_actions=required_actions,
            html_path="",
            json_path="",
            csv_path="",
        )

        json_path = output_dir / "copyright_defense_report.json"
        html_path = output_dir / "copyright_defense_report.html"
        csv_path = output_dir / "asset_license_log.csv"
        json_path.write_text(json.dumps(report.to_dict() | {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_html(report, html_path)
        self._write_asset_csv(asset_records, csv_path)
        report.html_path = str(html_path)
        report.json_path = str(json_path)
        report.csv_path = str(csv_path)
        json_path.write_text(json.dumps(report.to_dict() | {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _license_risk(self, text: str) -> int:
        lowered = text.lower()
        risk = 35
        if any(marker.lower() in lowered for marker in self.allowed_commercial_markers):
            risk -= 25
        if any(marker.lower() in lowered for marker in self.risky_license_markers):
            risk += 45
        if "미확인" in text or "미기재" in text:
            risk += 20
        if "상업" in text and any(x in text for x in ["불가", "금지", "안됨"]):
            risk += 45
        if "수정" in text and any(x in text for x in ["불가", "금지", "안됨"]):
            risk += 25
        return max(0, min(100, risk))

    def _required_actions(self, findings: list[DefenseFinding], assets: list[AssetLicenseRecord], evidence: list[EvidenceFileRecord]) -> list[str]:
        actions = []
        if any(f.severity == "높음" for f in findings):
            actions.append("고위험 항목을 수정한 뒤 리포트를 다시 생성하세요.")
        if any(a.risk_score >= 65 for a in assets):
            actions.append("상업 이용/수정 허용이 불명확한 이미지·폰트·효과 자료를 교체하거나 라이선스를 보강하세요.")
        if not evidence:
            actions.append("원본 스케치, 레이어, 수정 전후 파일, 최종 출력물을 증거 폴더로 지정하세요.")
        actions.append("이 리포트는 법적 확정 판단이 아니므로, 고위험 상품은 제출 전 공식 기준과 필요 시 전문가 검토를 병행하세요.")
        return actions

    def _write_asset_csv(self, records: list[AssetLicenseRecord], path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(AssetLicenseRecord("", "", "", "", "", "", "", 0, "").to_dict().keys()))
            writer.writeheader()
            for r in records:
                writer.writerow(r.to_dict())

    def _write_html(self, report: DefenseReport, path: Path) -> None:
        def table(rows: list[dict[str, Any]]) -> str:
            if not rows:
                return "<p>기록 없음</p>"
            headers = list(rows[0].keys())
            head = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
            body = "".join("<tr>" + "".join(f"<td>{html.escape(str(row.get(h, '')))}</td>" for h in headers) + "</tr>" for row in rows)
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

        status_color = "#0b7a3b" if report.overall_risk_score <= 25 else "#9a6700" if report.overall_risk_score <= 55 else "#b42318"
        html_text = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>저작권 방어 리포트</title>
<style>
body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:32px;line-height:1.55;color:#222}}
h1,h2{{color:#111}} .score{{font-size:28px;font-weight:700;color:{status_color}}}
table{{border-collapse:collapse;width:100%;margin:12px 0 24px}} th,td{{border:1px solid #ddd;padding:8px;font-size:13px;vertical-align:top}} th{{background:#f5f5f5}}
.badge{{display:inline-block;padding:4px 10px;border-radius:999px;background:#f2f4f7}}
.warning{{background:#fff7ed;border-left:4px solid #f97316;padding:12px;margin:12px 0}}
</style></head><body>
<h1>저작권/상표권 방어 센터 리포트</h1>
<p class="score">위험도 {report.overall_risk_score}/100 · {html.escape(report.final_status)}</p>
<p>{html.escape(report.summary)}</p>
<div class="warning">이 리포트는 제작 전 위험도 검토 자료이며, 법적 확정 판단 또는 카카오 승인 보장이 아닙니다.</div>
<h2>필수 보완/확인 항목</h2><ul>{''.join(f'<li>{html.escape(a)}</li>' for a in report.required_actions)}</ul>
<h2>주요 발견</h2>{table([f.to_dict() for f in report.findings])}
<h2>AI 사용 체크</h2><pre>{html.escape(json.dumps(report.ai_usage_check, ensure_ascii=False, indent=2))}</pre>
<h2>독창성/유사 위험 체크</h2><pre>{html.escape(json.dumps(report.originality_check, ensure_ascii=False, indent=2))}</pre>
<h2>자료·폰트·이미지 라이선스 기록</h2>{table([r.to_dict() for r in report.asset_records])}
<h2>창작 과정 증거 파일</h2>{table([r.to_dict() for r in report.evidence_records])}
</body></html>"""
        path.write_text(html_text, encoding="utf-8")
