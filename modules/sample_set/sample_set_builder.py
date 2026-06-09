from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List
import csv
import json
import time
import zipfile

from modules.beginner_creator.multi_material_creator import MultiMaterialCharacterCreator, MaterialSpec
from modules.candidate_curation import CandidateGalleryBuilder
from modules.part_editor import PartMotionEditor
from modules.chat_preview import ChatPreviewReviewer
from modules.submission_package.submission_package_builder import SubmissionPackageBuilder
from modules.quality_checker.submission_quality_reviewer import SubmissionQualityReviewer
from modules.prototype_generator.character_prototype_builder import PrototypeSpec
from modules.constants import FORMAT_LABELS, PLANNING_COUNTS


@dataclass
class SampleSetReport:
    project_name: str
    format_key: str
    format_label: str
    target_count: int
    material_count: int
    generated_expression_count: int
    selected_count: int
    sample_status: str
    sample_score: int
    pipeline_steps: List[Dict[str, Any]]
    material_report: Dict[str, Any]
    candidate_gallery_report: Dict[str, Any]
    part_edit_report: Dict[str, Any]
    chat_preview_report: Dict[str, Any]
    submission_result: Dict[str, Any]
    quality_review: Dict[str, Any]
    selected_expression_table: List[Dict[str, Any]]
    output_files: Dict[str, str]
    zip_path: str
    html_path: str
    json_path: str
    csv_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SampleSetBuilder:
    """v18 첫 실제 샘플 세트 제작 모드.

    소재/성격/말투 입력에서 시작해, 표현 후보 생성 → 24/32개 세트 선별 →
    표정/파츠 편집 → 채팅창 미리보기 → 제출 패키지 → 최종 품질 검사까지
    한 번에 묶어주는 초보자용 실행 흐름입니다.

    주의: 이 결과물은 제출 준비 보조 패키지이며, 카카오 승인/수익 보장이 아닙니다.
    실제 제출 전 공식 스튜디오 규격과 AI 활용 제한, 저작권/상표권 위험을 재확인해야 합니다.
    """

    def _safe_name(self, value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in str(value))[:48] or "sample_set"

    def default_materials(self) -> List[MaterialSpec]:
        return [
            MaterialSpec(name="보리", color="연갈색", personality="까칠하지만 은근히 챙김", tone="투덜거림, 짧게 말함", base_shape="알갱이형", role="중심"),
            MaterialSpec(name="쌀", color="아이보리", personality="온순하고 다정함", tone="부드럽고 위로하는 말투", base_shape="둥근형", role="보조"),
        ]

    def build_sample_set(
        self,
        specs: List[MaterialSpec] | List[Dict[str, Any]] | None,
        output_dir: str | Path,
        project_name: str = "보리와쌀_첫샘플세트",
        format_key: str = "static_text",
        target_count: int | None = None,
        expression_count: int = 80,
        preview_limit: int = 12,
        include_dark: bool = True,
        include_small: bool = True,
        uploaded_files: List[Any] | None = None,
    ) -> SampleSetReport:
        if format_key not in FORMAT_LABELS:
            raise ValueError(f"지원하지 않는 포맷입니다: {format_key}")
        output_dir = Path(output_dir)
        safe_project = self._safe_name(project_name)
        root = output_dir / safe_project
        root.mkdir(parents=True, exist_ok=True)

        material_specs = self._normalize_specs(specs)
        target = int(target_count or PLANNING_COUNTS.get(format_key, 32))
        target = max(1, min(target, 40))
        expression_count = max(target, min(int(expression_count or 80), 140))
        preview_limit = max(4, min(int(preview_limit or 12), target))

        steps: List[Dict[str, Any]] = []
        steps.append({"step": 1, "name": "소재/성격/말투 입력", "status": "완료", "note": f"{len(material_specs)}개 소재"})

        material_report = MultiMaterialCharacterCreator().build_project(
            specs=material_specs,
            uploaded_files=uploaded_files or [],
            output_dir=root / "01_multi_material_creator",
            project_name=safe_project,
            expression_count=expression_count,
            preview_count=min(16, target),
        )
        steps.append({"step": 2, "name": "멀티소재 캐릭터/표현 후보 생성", "status": "완료", "note": f"표현 후보 {len(material_report.expression_table)}개"})

        gallery_report = CandidateGalleryBuilder().build_gallery_pack(
            specs=material_specs,
            expressions=material_report.expression_table,
            output_dir=root / "02_candidate_gallery",
            project_name=safe_project,
            format_key=format_key,
            target_count=target,
        )
        steps.append({"step": 3, "name": "최종 세트 자동 선별", "status": "완료", "note": f"선택 {gallery_report.selected_count}개"})

        # 첫 샘플 세트는 자동 유지값을 기본으로 하지만, 사용자가 이후 16번 편집기에서 수정할 수 있도록 편집 리포트를 생성한다.
        part_report = PartMotionEditor().build_edit_pack(
            expressions=gallery_report.selected_expressions,
            output_dir=root / "03_part_motion_editor",
            project_name=safe_project,
            format_key=format_key,
            global_overrides={
                "eye_style": "자동 유지",
                "brow_style": "자동 유지",
                "mouth_style": "자동 유지",
                "body_motion": "자동 유지",
                "text_motion": "자동 유지",
                "effects": "자동 유지",
                "font_size": 28,
                "char_x": 178,
                "char_y": 142,
                "text_x": 180,
                "text_y": 250,
            },
            preview_limit=preview_limit,
        )
        steps.append({"step": 4, "name": "표정/파츠/문구/움직임 자동 편집안 생성", "status": "완료", "note": f"미리보기 {len(part_report.preview_files)}개"})

        chat_report = ChatPreviewReviewer().build_preview_pack(
            expressions=part_report.edited_expressions,
            output_dir=root / "04_chat_preview_final_review",
            project_name=safe_project,
            format_key=format_key,
            preview_files=part_report.preview_files,
            preview_limit=preview_limit,
            include_dark=include_dark,
            include_small=include_small,
        )
        steps.append({"step": 5, "name": "카카오톡 채팅창 미리보기/최종검수", "status": "완료", "note": f"채팅 사용성 {chat_report.chat_usability_score}점"})

        submission_spec = self._prototype_spec_from_materials(material_specs, safe_project, format_key)
        submission_result = SubmissionPackageBuilder().build(
            spec=submission_spec,
            expressions=part_report.edited_expressions,
            output_root=root / "05_submission_package",
            project_name=safe_project,
            format_key=format_key,
            target_count=target,
        )
        steps.append({"step": 6, "name": "제출 준비 패키지 생성", "status": "완료", "note": f"파일 {submission_result.created_count}개"})

        quality_review = SubmissionQualityReviewer().review(
            package_dir=submission_result.package_dir,
            format_key=format_key,
            expressions=part_report.edited_expressions,
            output_dir=root / "06_quality_review",
        )
        steps.append({"step": 7, "name": "제출 전 품질검사", "status": quality_review.final_status, "note": f"품질 {quality_review.overall_score}점"})

        score = int(round((chat_report.chat_usability_score * 0.55) + (quality_review.overall_score * 0.45)))
        if score >= 82 and "수정 필요" not in quality_review.final_status:
            status = "첫 샘플 세트 검토 양호"
        elif score >= 68:
            status = "보완 후 첫 제출 후보"
        else:
            status = "수정 후 재생성 권장"

        selected_table = self._make_selected_table(part_report.edited_expressions)
        csv_path = root / "sample_set_selected_expressions.csv"
        self._write_csv(selected_table, csv_path)
        data: Dict[str, Any] = {
            "project_name": project_name,
            "format_key": format_key,
            "format_label": FORMAT_LABELS.get(format_key, format_key),
            "target_count": target,
            "material_specs": [s.to_dict() for s in material_specs],
            "sample_status": status,
            "sample_score": score,
            "pipeline_steps": steps,
            "selected_expression_table": selected_table,
            "notice": "첫 실제 샘플 세트 제작 보조 결과입니다. 카카오 승인/수익 보장 결과가 아니며, 제출 전 공식 가이드·AI 정책·저작권/상표권 위험을 재확인하세요.",
            "material_report": material_report.to_dict(),
            "candidate_gallery_report": gallery_report.to_dict(),
            "part_edit_report": part_report.to_dict(),
            "chat_preview_report": chat_report.to_dict(),
            "submission_result": submission_result.to_dict(),
            "quality_review": quality_review.to_dict(),
        }
        json_path = root / "sample_set_report.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path = root / "sample_set_report.html"
        html_path.write_text(self._html_report(data), encoding="utf-8")

        zip_path = output_dir / f"{safe_project}_v18_sample_set_pack.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, arcname=str(p.relative_to(root.parent)))

        output_files = {
            "sample_html": str(html_path),
            "sample_json": str(json_path),
            "selected_csv": str(csv_path),
            "sample_zip": str(zip_path),
            "submission_zip": str(submission_result.zip_path),
            "quality_html": str(quality_review.html_path),
            "chat_preview_html": str(chat_report.html_path),
            "part_edit_html": str(part_report.html_path),
            "candidate_gallery_html": str(gallery_report.html_path),
        }
        return SampleSetReport(
            project_name=project_name,
            format_key=format_key,
            format_label=FORMAT_LABELS.get(format_key, format_key),
            target_count=target,
            material_count=len(material_specs),
            generated_expression_count=len(material_report.expression_table),
            selected_count=gallery_report.selected_count,
            sample_status=status,
            sample_score=score,
            pipeline_steps=steps,
            material_report=material_report.to_dict(),
            candidate_gallery_report=gallery_report.to_dict(),
            part_edit_report=part_report.to_dict(),
            chat_preview_report=chat_report.to_dict(),
            submission_result=submission_result.to_dict(),
            quality_review=quality_review.to_dict(),
            selected_expression_table=selected_table,
            output_files=output_files,
            zip_path=str(zip_path),
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
        )

    def _normalize_specs(self, specs: List[MaterialSpec] | List[Dict[str, Any]] | None) -> List[MaterialSpec]:
        if not specs:
            return self.default_materials()
        out: List[MaterialSpec] = []
        for item in specs[:5]:
            if isinstance(item, MaterialSpec):
                out.append(item)
            elif isinstance(item, dict):
                out.append(MaterialSpec(
                    name=str(item.get("name", f"소재{len(out)+1}")),
                    color=str(item.get("color", "아이보리")),
                    personality=str(item.get("personality", "온순함")),
                    tone=str(item.get("tone", "부드러운 말투")),
                    base_shape=str(item.get("base_shape", "둥근형")),
                    role=str(item.get("role", "대화 보조")),
                ))
        return out or self.default_materials()

    def _prototype_spec_from_materials(self, specs: List[MaterialSpec], project_name: str, format_key: str) -> PrototypeSpec:
        colors = [self._color_to_hex(s.color, i) for i, s in enumerate(specs)]
        while len(colors) < 3:
            colors.append(["#D8B36A", "#F4E6B5", "#2A2A2A"][len(colors)])
        shape = "듀오형" if len(specs) == 2 else ("알갱이형" if len(specs) >= 3 else specs[0].base_shape)
        accessory = "말풍선 꼬리" if format_key in ["static_text", "animated_text"] else "싹"
        motion = "문구와 캐릭터가 같이 움직이는 샘플 세트" if format_key == "animated_text" else "문구 중심 첫 샘플 세트"
        return PrototypeSpec(
            name=project_name,
            materials=[s.name for s in specs],
            body_shape=shape,
            palette=colors[:5],
            face_style="공손한 미소",
            accessory=accessory,
            motion_hint=motion,
            originality_note="사용자가 입력한 소재·색상·성격·말투를 기반으로 만든 첫 샘플 세트용 절차형 시안입니다. 기존 캐릭터의 구체적 표현을 복제하지 않습니다.",
        )

    def _color_to_hex(self, value: str, idx: int) -> str:
        named = {
            "연갈색": "#C99A5C", "갈색": "#966437", "아이보리": "#F4EBCD", "흰색": "#FFF9F0",
            "노랑": "#F5D250", "연노랑": "#FAE682", "초록": "#78B45A", "회색": "#A0A0A0",
            "분홍": "#F0A0B4", "보라": "#AA8CD2", "주황": "#EC9146", "빨강": "#DC5555",
            "파랑": "#5F96DC", "검정": "#2D2D2D",
        }
        if value.startswith("#") and len(value) in (7, 9):
            return value[:7]
        return named.get(value, ["#C99A5C", "#F4EBCD", "#E0A05C", "#A0A0A0", "#78B45A"][idx % 5])

    def _make_selected_table(self, expressions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        table: List[Dict[str, Any]] = []
        for idx, expr in enumerate(expressions, start=1):
            plan = expr.get("expression_plan") or {}
            table.append({
                "no": idx,
                "phrase": expr.get("phrase", ""),
                "category": expr.get("category", ""),
                "face_summary": expr.get("face_summary", ""),
                "eye": plan.get("eye_style", ""),
                "mouth": plan.get("mouth_style", ""),
                "body_motion": plan.get("body_motion", ""),
                "text_motion": plan.get("text_motion", ""),
                "effects": ",".join(plan.get("effects", [])) if isinstance(plan.get("effects"), list) else str(plan.get("effects", "")),
                "status": "초안 생성",
            })
        return table

    def _write_csv(self, rows: List[Dict[str, Any]], path: Path) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _html_report(self, data: Dict[str, Any]) -> str:
        rows = "".join(
            f"<tr><td>{r.get('no')}</td><td>{r.get('category')}</td><td>{r.get('phrase')}</td><td>{r.get('face_summary')}</td><td>{r.get('body_motion')}</td><td>{r.get('text_motion')}</td></tr>"
            for r in data.get("selected_expression_table", [])
        )
        steps = "".join(
            f"<li><b>{s.get('step')}. {s.get('name')}</b> — {s.get('status')} · {s.get('note')}</li>"
            for s in data.get("pipeline_steps", [])
        )
        mats = ", ".join([m.get("name", "") for m in data.get("material_specs", [])])
        return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<title>v18 첫 샘플 세트 리포트</title>
<style>body{{font-family:Arial,'Malgun Gothic',sans-serif;line-height:1.55;margin:32px;color:#222}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#f5f5f5}}.card{{background:#fff7d8;border:1px solid #ead27a;border-radius:14px;padding:18px;margin:16px 0}}.warn{{background:#fff1f1;border:1px solid #f0b0b0;border-radius:12px;padding:14px}}</style></head><body>
<h1>카카오 이모티콘 수익화 시스템 v18 · 첫 샘플 세트</h1>
<div class='card'><b>프로젝트:</b> {data.get('project_name')}<br><b>포맷:</b> {data.get('format_label')}<br><b>소재:</b> {mats}<br><b>샘플 점수:</b> {data.get('sample_score')}점<br><b>판정:</b> {data.get('sample_status')}</div>
<h2>생성 흐름</h2><ol>{steps}</ol>
<h2>선택 표현표</h2><table><tr><th>No</th><th>분류</th><th>문구</th><th>표정 요약</th><th>몸동작</th><th>문구 움직임</th></tr>{rows}</table>
<div class='warn'><b>주의:</b> 이 리포트는 제작/검수 보조자료입니다. 카카오 승인·수익을 보장하지 않으며, 제출 전 공식 가이드·AI 활용 제한·저작권/상표권 위험을 다시 확인해야 합니다.</div>
</body></html>"""
