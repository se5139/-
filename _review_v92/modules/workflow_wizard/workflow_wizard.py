from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import json
import time
import zipfile

from modules.beginner_creator.multi_material_creator import MaterialSpec
from modules.constants import FORMAT_LABELS, PLANNING_COUNTS
from modules.sample_set import SampleSetBuilder


@dataclass
class WizardStep:
    step_no: int
    title: str
    status: str
    description: str
    output_hint: str
    next_action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WizardReport:
    project_name: str
    format_key: str
    format_label: str
    material_count: int
    target_count: int
    expression_count: int
    progress_percent: int
    current_phase: str
    next_recommended_step: str
    wizard_steps: List[Dict[str, Any]]
    material_specs: List[Dict[str, Any]]
    sample_set_report: Optional[Dict[str, Any]]
    output_files: Dict[str, str]
    html_path: str
    json_path: str
    csv_path: str
    zip_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorkflowWizard:
    """v21 초보자 전체 제작 마법사.

    기능이 많아진 v20 구조를 처음 사용자도 순서대로 사용할 수 있도록
    1단계 소재 선택부터 제출 패키지/백업/성장형 학습 저장까지 안내하고,
    원하면 첫 샘플 세트 생성까지 한 번에 실행합니다.
    """

    DEFAULT_STEPS = [
        (1, "소재/캐릭터 방식 선택", "단어·도형·스케치·첨부파일 중 시작 방식을 정합니다.", "소재/성격/말투 입력", "색상·성격·말투 후보를 고르세요."),
        (2, "색상·성격·말투 후보 선택", "색상 후보, 성격 후보, 말투 후보를 고르고 360×360 미리보기를 확인합니다.", "미리보기 PNG", "표현 후보를 생성하세요."),
        (3, "표현 후보 은행 생성", "80~120개 표현 후보를 만들고 실사용/감정/시그니처 비율을 확인합니다.", "표현 후보 JSON/CSV", "24개/32개 최종 세트를 선별하세요."),
        (4, "24개·32개 최종 세트 선택", "중복·가독성·감정 균형 기준으로 최종 후보를 고릅니다.", "선택 표현 CSV", "표정/파츠/움직임을 확인하세요."),
        (5, "표정·파츠·문구·움직임 편집", "눈/입/효과/문구 위치/움직임 타임라인을 수정합니다.", "편집 미리보기 PNG/GIF", "채팅창 미리보기를 확인하세요."),
        (6, "카카오톡 채팅창 미리보기", "흰 배경·어두운 배경·작은 크기에서 읽힘과 잘림을 검사합니다.", "채팅 미리보기 HTML", "품질검사를 실행하세요."),
        (7, "제출 전 품질검사", "크기·용량·투명 배경·문구 잘림·표현 균형을 검사합니다.", "품질검사 HTML/JSON", "저작권 방어 리포트를 생성하세요."),
        (8, "저작권/상표권/직접 창작 기준", "자료 출처, 직접 창작 증거, AI 사용 범위, 상표/유사 위험을 기록합니다.", "방어 리포트 HTML", "제출 패키지를 생성하세요."),
        (9, "제출 패키지 생성", "선택한 포맷에 맞춰 PNG/GIF 파일과 manifest를 정리합니다.", "제출 ZIP", "백업을 생성하세요."),
        (10, "데이터 보호 백업", "업데이트 전 ZIP 백업과 SHA-256 무결성 검사를 수행합니다.", "백업 ZIP/SHA", "성장형 학습 엔진에 저장하세요."),
        (11, "성장형 학습 저장", "제작/검사/반려/판매 데이터를 누적해 다음 추천에 반영합니다.", "growth_learning_report", "다음 캐릭터/포맷을 기획하세요."),
    ]

    def _safe_name(self, value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in str(value))[:60] or "workflow_wizard"

    def default_materials(self) -> List[MaterialSpec]:
        return [
            MaterialSpec(name="보리", color="연갈색", personality="까칠하지만 은근히 챙김", tone="투덜거림, 짧게 말함", base_shape="알갱이형", role="중심"),
            MaterialSpec(name="쌀", color="아이보리", personality="온순하고 다정함", tone="부드럽고 위로하는 말투", base_shape="둥근형", role="보조"),
        ]

    def normalize_specs(self, specs: List[MaterialSpec] | List[Dict[str, Any]] | None) -> List[MaterialSpec]:
        if not specs:
            return self.default_materials()
        normalized: List[MaterialSpec] = []
        for item in specs[:5]:
            if isinstance(item, MaterialSpec):
                normalized.append(item)
            elif isinstance(item, dict):
                normalized.append(MaterialSpec(
                    name=str(item.get("name") or item.get("소재") or "소재"),
                    color=str(item.get("color") or item.get("색상") or "아이보리"),
                    personality=str(item.get("personality") or item.get("성격") or "온순하고 다정함"),
                    tone=str(item.get("tone") or item.get("말투") or "부드러운 말투"),
                    base_shape=str(item.get("base_shape") or item.get("도형") or "둥근형"),
                    role=str(item.get("role") or item.get("역할") or "보조"),
                ))
        return normalized or self.default_materials()

    def build_wizard_report(
        self,
        specs: List[MaterialSpec] | List[Dict[str, Any]] | None,
        output_dir: str | Path,
        project_name: str = "초보자_전체_제작_마법사",
        format_key: str = "static_text",
        target_count: int | None = None,
        expression_count: int = 80,
        completed_step_count: int = 0,
        run_sample_generation: bool = True,
        include_dark: bool = True,
        include_small: bool = True,
    ) -> WizardReport:
        if format_key not in FORMAT_LABELS:
            raise ValueError(f"지원하지 않는 포맷입니다: {format_key}")
        output_dir = Path(output_dir)
        safe_project = self._safe_name(project_name)
        root = output_dir / safe_project
        root.mkdir(parents=True, exist_ok=True)
        material_specs = self.normalize_specs(specs)
        target = int(target_count or PLANNING_COUNTS.get(format_key, 32))
        target = max(1, min(target, 40))
        expression_count = max(target, min(int(expression_count or 80), 140))

        sample_set_report: Optional[Dict[str, Any]] = None
        completed = int(completed_step_count or 0)
        if run_sample_generation:
            sample_report = SampleSetBuilder().build_sample_set(
                specs=material_specs,
                output_dir=root / "sample_set_flow",
                project_name=safe_project,
                format_key=format_key,
                target_count=target,
                expression_count=expression_count,
                preview_limit=min(12, target),
                include_dark=include_dark,
                include_small=include_small,
            )
            sample_set_report = sample_report.to_dict()
            completed = max(completed, 9)
        completed = max(0, min(completed, len(self.DEFAULT_STEPS)))

        steps: List[WizardStep] = []
        for no, title, desc, output_hint, next_action in self.DEFAULT_STEPS:
            if no <= completed:
                status = "완료"
            elif no == completed + 1:
                status = "현재 단계"
            else:
                status = "대기"
            steps.append(WizardStep(no, title, status, desc, output_hint, next_action))

        progress = int(round(completed / len(self.DEFAULT_STEPS) * 100))
        current = next((s.title for s in steps if s.status == "현재 단계"), "전체 흐름 완료")
        next_action = next((s.next_action for s in steps if s.status == "현재 단계"), "성장형 학습 리포트를 확인하고 다음 세트를 기획하세요.")

        material_dicts = [s.to_dict() for s in material_specs]
        step_dicts = [s.to_dict() for s in steps]
        csv_path = root / "workflow_wizard_steps.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["step_no", "title", "status", "description", "output_hint", "next_action"])
            writer.writeheader(); writer.writerows(step_dicts)

        data = {
            "project_name": project_name,
            "format_key": format_key,
            "format_label": FORMAT_LABELS.get(format_key, format_key),
            "material_specs": material_dicts,
            "target_count": target,
            "expression_count": expression_count,
            "progress_percent": progress,
            "current_phase": current,
            "next_recommended_step": next_action,
            "wizard_steps": step_dicts,
            "sample_set_report": sample_set_report,
            "notice": "초보자 전체 제작 마법사는 순서 안내와 자동 실행 보조 기능입니다. 카카오 승인/수익 보장이 아니며, 제출 전 공식 가이드와 직접 창작/저작권/AI 정책을 다시 확인해야 합니다.",
        }
        json_path = root / "workflow_wizard_report.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path = root / "workflow_wizard_report.html"
        html_path.write_text(self._html_report(data), encoding="utf-8")

        zip_path = output_dir / f"{safe_project}_v21_workflow_wizard_pack.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, arcname=str(p.relative_to(root.parent)))

        output_files = {
            "wizard_html": str(html_path),
            "wizard_json": str(json_path),
            "wizard_csv": str(csv_path),
            "wizard_zip": str(zip_path),
        }
        if sample_set_report:
            for k in ["zip_path", "html_path", "json_path", "csv_path"]:
                if sample_set_report.get(k):
                    output_files[f"sample_set_{k}"] = sample_set_report[k]
        return WizardReport(
            project_name=project_name,
            format_key=format_key,
            format_label=FORMAT_LABELS.get(format_key, format_key),
            material_count=len(material_specs),
            target_count=target,
            expression_count=expression_count,
            progress_percent=progress,
            current_phase=current,
            next_recommended_step=next_action,
            wizard_steps=step_dicts,
            material_specs=material_dicts,
            sample_set_report=sample_set_report,
            output_files=output_files,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            zip_path=str(zip_path),
        )

    def _html_report(self, data: Dict[str, Any]) -> str:
        def esc(x: Any) -> str:
            return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows = "".join(
            f"<tr><td>{s['step_no']}</td><td>{esc(s['title'])}</td><td>{esc(s['status'])}</td><td>{esc(s['description'])}</td><td>{esc(s['next_action'])}</td></tr>"
            for s in data.get("wizard_steps", [])
        )
        mats = "".join(
            f"<tr><td>{esc(m.get('name',''))}</td><td>{esc(m.get('color',''))}</td><td>{esc(m.get('personality',''))}</td><td>{esc(m.get('tone',''))}</td><td>{esc(m.get('base_shape',''))}</td><td>{esc(m.get('role',''))}</td></tr>"
            for m in data.get("material_specs", [])
        )
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>v21 초보자 전체 제작 마법사</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.6}}table{{border-collapse:collapse;width:100%;margin:14px 0}}th,td{{border:1px solid #ddd;padding:8px;vertical-align:top}}th{{background:#f5f5f5}}.card{{border:1px solid #ddd;border-radius:12px;padding:16px;margin:12px 0;background:#fafafa}}.warn{{background:#fff7e6;border-left:5px solid #f0a500;padding:12px}}</style></head><body>
<h1>v21 초보자 전체 제작 마법사</h1>
<div class='card'><b>프로젝트:</b> {esc(data.get('project_name'))}<br><b>포맷:</b> {esc(data.get('format_label'))}<br><b>진행률:</b> {data.get('progress_percent')}%<br><b>현재 단계:</b> {esc(data.get('current_phase'))}<br><b>다음 행동:</b> {esc(data.get('next_recommended_step'))}</div>
<div class='warn'>{esc(data.get('notice'))}</div>
<h2>소재 설정</h2><table><thead><tr><th>소재</th><th>색상</th><th>성격</th><th>말투</th><th>도형</th><th>역할</th></tr></thead><tbody>{mats}</tbody></table>
<h2>제작 단계</h2><table><thead><tr><th>번호</th><th>단계</th><th>상태</th><th>설명</th><th>다음 행동</th></tr></thead><tbody>{rows}</tbody></table>
</body></html>"""
