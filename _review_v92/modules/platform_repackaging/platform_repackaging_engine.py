from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class PlatformTarget:
    key: str
    label: str
    role: str
    draft_size: tuple[int, int]
    output_ext: str
    count_hint: str
    official_check_note: str
    recommendation_note: str


PLATFORM_TARGETS: dict[str, PlatformTarget] = {
    "naver_ogq": PlatformTarget(
        key="naver_ogq",
        label="네이버 OGQ/블로그 스티커 초안",
        role="카카오 반려/확장 시 블로그·OGQ용 스티커로 재활용 검토",
        draft_size=(740, 640),
        output_ext="png",
        count_hint="플랫폼 공식 기준 확인 후 수량 조정",
        official_check_note="OGQ 공식 최신 제작 가이드 확인 필요. 이 출력은 제출 전 초안/검토용입니다.",
        recommendation_note="문구형 정지/리액션형 캐릭터와 궁합이 좋습니다.",
    ),
    "line_sticker": PlatformTarget(
        key="line_sticker",
        label="LINE 스티커 초안",
        role="해외/글로벌 반응 검토용 스티커 재활용",
        draft_size=(370, 320),
        output_ext="png",
        count_hint="LINE Creators Market 공식 기준 확인 후 수량 조정",
        official_check_note="LINE 공식 최신 규격 확인 필요. 이 출력은 초안/검토용입니다.",
        recommendation_note="짧은 리액션, 표정 중심 표현, 언어 의존이 낮은 표현에 적합합니다.",
    ),
    "band_sticker": PlatformTarget(
        key="band_sticker",
        label="밴드 스티커 초안",
        role="모임/동호회/가족·지역 커뮤니티용 재활용",
        draft_size=(360, 360),
        output_ext="png",
        count_hint="밴드 공식 기준 확인 후 수량 조정",
        official_check_note="밴드 스티커 공식 최신 기준 확인 필요. 이 출력은 초안/검토용입니다.",
        recommendation_note="사투리/지역성/가족·모임 문구와 잘 맞습니다.",
    ),
    "sns_square": PlatformTarget(
        key="sns_square",
        label="SNS 정사각 카드 초안",
        role="인스타그램 피드/카드뉴스/홍보용",
        draft_size=(1080, 1080),
        output_ext="png",
        count_hint="대표 6~12장으로 홍보 카드 구성 권장",
        official_check_note="SNS 업로드용 초안입니다. 각 플랫폼 권장 해상도는 업로드 전 확인하세요.",
        recommendation_note="이모티콘 출시 전후 홍보 카드, 캐릭터 세계관 소개에 적합합니다.",
    ),
    "sns_story": PlatformTarget(
        key="sns_story",
        label="SNS 세로 스토리/릴스 초안",
        role="인스타그램 스토리/릴스/쇼츠용 세로 홍보 소재",
        draft_size=(1080, 1920),
        output_ext="png",
        count_hint="대표 3~6장 또는 짧은 릴스 장면으로 구성 권장",
        official_check_note="SNS 업로드용 초안입니다. 영상화 시 별도 편집/음원 권리 확인이 필요합니다.",
        recommendation_note="캐릭터 탄생 과정, 4컷툰, 출시 알림에 적합합니다.",
    ),
    "goods_png": PlatformTarget(
        key="goods_png",
        label="굿즈/인쇄용 PNG 초안",
        role="스티커·엽서·굿즈 시안 검토용",
        draft_size=(2000, 2000),
        output_ext="png",
        count_hint="대표 캐릭터/시그니처 표정 중심으로 선별 권장",
        official_check_note="인쇄 제작 전 해상도, 색상, 라이선스, 폰트 권리를 별도 확인하세요.",
        recommendation_note="승인/반응이 좋은 캐릭터를 2차 IP 상품으로 확장할 때 적합합니다.",
    ),
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_name(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in str(text))
    return cleaned[:80] or "asset"


def _read_font(size: int = 28):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for cand in candidates:
        p = Path(cand)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                pass
    return ImageFont.load_default()


class PlatformRepackagingEngine:
    def __init__(self, output_root: str | Path):
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        input_dir: str | Path,
        project_name: str,
        title: str,
        selected_platforms: Iterable[str],
        source_format: str = "문구 결합형 멈춰있는 이모티콘",
        purpose: str = "카카오 1차 포맷 이후 확장/재활용 검토",
        max_assets_per_platform: int = 12,
        use_placeholders_when_empty: bool = True,
    ) -> dict[str, Any]:
        input_dir = Path(input_dir)
        selected = [k for k in selected_platforms if k in PLATFORM_TARGETS]
        if not selected:
            raise ValueError("선택된 플랫폼이 없습니다.")
        work_dir = self.output_root / _safe_name(project_name)
        original_dir = work_dir / "original"
        draft_root = work_dir / "draft_repackaged"
        report_dir = work_dir / "report"
        for d in [original_dir, draft_root, report_dir]:
            d.mkdir(parents=True, exist_ok=True)

        source_files = self._collect_sources(input_dir, original_dir)
        if not source_files and use_placeholders_when_empty:
            source_files = self._create_placeholder_sources(original_dir, title)
        if not source_files:
            raise ValueError("입력 이미지가 없습니다. 원본 파일을 업로드하거나 샘플 생성을 허용하세요.")

        records: list[dict[str, Any]] = []
        platform_summaries: list[dict[str, Any]] = []
        for platform_key in selected:
            target = PLATFORM_TARGETS[platform_key]
            platform_dir = draft_root / platform_key
            platform_dir.mkdir(parents=True, exist_ok=True)
            chosen = source_files[: max(1, int(max_assets_per_platform))]
            platform_records = []
            for idx, src in enumerate(chosen, start=1):
                out_name = f"{idx:02d}_{platform_key}_{_safe_name(src.stem)}.{target.output_ext}"
                out_path = platform_dir / out_name
                self._convert_image(src, out_path, target, title=title)
                rec = {
                    "platform": platform_key,
                    "platform_label": target.label,
                    "source_file": src.name,
                    "output_file": str(out_path),
                    "draft_size": f"{target.draft_size[0]}x{target.draft_size[1]}",
                    "output_bytes": out_path.stat().st_size,
                    "sha256": _sha256(out_path),
                    "status": "DRAFT",
                    "official_check_required": True,
                    "note": target.official_check_note,
                }
                platform_records.append(rec)
                records.append(rec)
            readme = platform_dir / "README_OFFICIAL_CHECK_REQUIRED.txt"
            readme.write_text(
                f"{target.label}\n\n"
                f"용도: {target.role}\n"
                f"수량 기준: {target.count_hint}\n"
                f"주의: {target.official_check_note}\n"
                f"추천 메모: {target.recommendation_note}\n"
                "\n이 폴더는 최종 제출 보장 패키지가 아니라 플랫폼별 재활용 초안입니다.\n"
                "각 플랫폼의 최신 공식 규격, 권리, 폰트, 파일명, 용량 기준을 제출 직전 다시 확인하세요.\n",
                encoding="utf-8",
            )
            platform_summaries.append({
                "platform": platform_key,
                "platform_label": target.label,
                "role": target.role,
                "draft_size": f"{target.draft_size[0]}x{target.draft_size[1]}",
                "asset_count": len(platform_records),
                "count_hint": target.count_hint,
                "official_check_note": target.official_check_note,
                "recommendation_note": target.recommendation_note,
            })

        roadmap = self._build_roadmap(selected)
        risk_notes = [
            "카카오 1차 포맷 제작/검증을 우선하고, 다른 플랫폼은 반려·승인·성과 데이터 이후 선택적으로 확장하세요.",
            "재패키징 초안은 최종 제출 파일이 아닙니다. 플랫폼별 최신 공식 규격 확인이 필요합니다.",
            "타 플랫폼으로 확장하더라도 기존 캐릭터/상표/폰트/이미지 권리 검사는 다시 진행해야 합니다.",
            "카카오에서 반려된 소재를 그대로 복사해 다른 플랫폼에 올리기보다, 반려 사유를 먼저 개선한 뒤 재활용하세요.",
        ]
        data = {
            "project_name": project_name,
            "title": title,
            "source_format": source_format,
            "purpose": purpose,
            "platform_summaries": platform_summaries,
            "records": records,
            "roadmap": roadmap,
            "risk_notes": risk_notes,
            "created_dirs": {
                "work_dir": str(work_dir),
                "original_dir": str(original_dir),
                "draft_root": str(draft_root),
                "report_dir": str(report_dir),
            },
        }
        json_path = report_dir / "platform_repackaging_v42.json"
        html_path = report_dir / "platform_repackaging_v42.html"
        csv_path = report_dir / "platform_repackaging_v42_records.csv"
        roadmap_csv_path = report_dir / "platform_repackaging_v42_roadmap.csv"
        notes_path = report_dir / "platform_repackaging_v42_notes.txt"
        self._write_csv(csv_path, records)
        self._write_csv(roadmap_csv_path, roadmap)
        notes_path.write_text("\n".join(risk_notes), encoding="utf-8")
        html_path.write_text(self._html(data), encoding="utf-8")
        zip_path = work_dir / f"{_safe_name(project_name)}_v42_platform_repackaging_pack.zip"
        self._zip_dir(work_dir, zip_path)
        data["files"] = {
            "html_path": str(html_path),
            "json_path": str(json_path),
            "records_csv_path": str(csv_path),
            "roadmap_csv_path": str(roadmap_csv_path),
            "notes_path": str(notes_path),
            "zip_path": str(zip_path),
        }
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def _collect_sources(self, input_dir: Path, original_dir: Path) -> list[Path]:
        exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        files = []
        if input_dir.exists():
            for p in sorted(input_dir.iterdir()):
                if p.is_file() and p.suffix.lower() in exts:
                    dest = original_dir / _safe_name(p.name)
                    shutil.copy2(p, dest)
                    files.append(dest)
        return files

    def _create_placeholder_sources(self, original_dir: Path, title: str) -> list[Path]:
        font = _read_font(24)
        files = []
        labels = ["안녕", "확인", "고마워", "죄송", "좋아요", "피곤", "축하", "잘자"]
        for i, label in enumerate(labels, start=1):
            im = Image.new("RGBA", (360, 360), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            color = [(255, 236, 178, 255), (210, 235, 255, 255), (220, 245, 215, 255), (245, 220, 235, 255)][i % 4]
            d.rounded_rectangle([65, 50, 295, 270], radius=70, fill=color, outline=(45, 45, 45, 255), width=5)
            d.ellipse([130, 120, 145, 135], fill=(40, 40, 40, 255))
            d.ellipse([215, 120, 230, 135], fill=(40, 40, 40, 255))
            d.arc([145, 140, 215, 195], 10, 170, fill=(40, 40, 40, 255), width=4)
            d.rounded_rectangle([75, 285, 285, 340], radius=12, fill=(255, 255, 255, 235), outline=(70, 70, 70, 255), width=2)
            d.text((105, 298), label, font=font, fill=(35, 35, 35, 255))
            p = original_dir / f"placeholder_{i:02d}.png"
            im.save(p)
            files.append(p)
        return files

    def _convert_image(self, src: Path, out_path: Path, target: PlatformTarget, title: str) -> None:
        src_im = Image.open(src).convert("RGBA")
        canvas = Image.new("RGBA", target.draft_size, (0, 0, 0, 0))
        margin_x = max(24, int(target.draft_size[0] * 0.08))
        margin_y = max(24, int(target.draft_size[1] * 0.08))
        max_w = target.draft_size[0] - margin_x * 2
        max_h = target.draft_size[1] - margin_y * 2
        if target.key == "sns_story":
            max_h = int(target.draft_size[1] * 0.46)
            margin_y = int(target.draft_size[1] * 0.18)
        ratio = min(max_w / max(1, src_im.width), max_h / max(1, src_im.height))
        new_size = (max(1, int(src_im.width * ratio)), max(1, int(src_im.height * ratio)))
        resized = src_im.resize(new_size, Image.LANCZOS)
        pos = ((target.draft_size[0] - new_size[0]) // 2, (target.draft_size[1] - new_size[1]) // 2)
        if target.key in {"sns_square", "sns_story"}:
            canvas = Image.new("RGBA", target.draft_size, (250, 250, 247, 255))
            d = ImageDraw.Draw(canvas)
            font = _read_font(48 if target.key == "sns_story" else 36)
            small = _read_font(28 if target.key == "sns_story" else 22)
            d.text((margin_x, max(30, margin_y // 3)), title[:24], font=font, fill=(35, 35, 35, 255))
            d.text((margin_x, target.draft_size[1] - margin_y), "출시/확장 홍보 초안 · 공식 규격 별도 확인", font=small, fill=(90, 90, 90, 255))
        canvas.alpha_composite(resized, pos)
        canvas.save(out_path, optimize=True)

    def _build_roadmap(self, selected: list[str]) -> list[dict[str, Any]]:
        return [
            {"step": 1, "phase": "카카오 1차 포맷 유지", "action": "v37/v40에서 추천된 1개 포맷으로 먼저 심사·성과 데이터를 확보", "decision_rule": "초기에는 확장보다 1차 포맷 완성도 우선"},
            {"step": 2, "phase": "반려/승인 데이터 반영", "action": "v29 반려 개선, v39/v40 성과 대시보드 결과를 누적", "decision_rule": "반려 사유가 해결되기 전에는 동일 파일을 타 플랫폼에 무리하게 확장하지 않음"},
            {"step": 3, "phase": "선택 플랫폼 초안 제작", "action": ", ".join(PLATFORM_TARGETS[k].label for k in selected), "decision_rule": "캐릭터 콘셉트와 문구 사용성이 유지되는 플랫폼만 선택"},
            {"step": 4, "phase": "공식 규격 재확인", "action": "각 플랫폼 최신 제출 규격·권리·파일명·용량 기준 확인", "decision_rule": "v42 출력물은 초안이며 최종 제출 전 별도 검수 필요"},
            {"step": 5, "phase": "2차 IP 확장 판단", "action": "인스타툰·굿즈·라인/OGQ/밴드 중 반응 좋은 방향으로만 확장", "decision_rule": "데이터 부족 시 보류"},
        ]

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return
        keys: list[str] = []
        for row in rows:
            for k in row.keys():
                if k not in keys:
                    keys.append(k)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)

    def _html(self, data: dict[str, Any]) -> str:
        def table(rows: list[dict[str, Any]]) -> str:
            if not rows:
                return "<p>데이터 없음</p>"
            keys = []
            for row in rows:
                for k in row.keys():
                    if k not in keys:
                        keys.append(k)
            head = "".join(f"<th>{k}</th>" for k in keys)
            body = "".join("<tr>" + "".join(f"<td>{row.get(k, '')}</td>" for k in keys) + "</tr>" for row in rows)
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        css = '<style>body{font-family:Arial,"Noto Sans KR",sans-serif;margin:28px;line-height:1.5}table{border-collapse:collapse;width:100%;margin:12px 0}th,td{border:1px solid #ddd;padding:8px;font-size:13px}th{background:#f5f5f5}.warn{background:#fff4d6;padding:12px;border-left:5px solid #d39b00}</style>'
        notes = "".join(f"<li>{n}</li>" for n in data.get("risk_notes", []))
        return f'''<!doctype html><html><head><meta charset="utf-8"><title>v42 플랫폼별 재패키징</title>{css}</head><body>
<h1>v42 플랫폼별 재패키징 리포트</h1>
<p><b>프로젝트:</b> {data.get('project_name')} / <b>작품:</b> {data.get('title')}</p>
<div class="warn"><b>중요:</b> 이 리포트의 타 플랫폼 출력물은 공식 제출 보장본이 아니라 재활용 초안입니다. 제출 전 각 플랫폼 최신 공식 규격을 확인하세요.</div>
<h2>플랫폼 요약</h2>{table(data.get('platform_summaries', []))}
<h2>생성 파일</h2>{table(data.get('records', []))}
<h2>확장 로드맵</h2>{table(data.get('roadmap', []))}
<h2>위험/주의 노트</h2><ul>{notes}</ul>
</body></html>'''

    def _zip_dir(self, folder: Path, zip_path: Path) -> None:
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in folder.rglob("*"):
                if p == zip_path or not p.is_file():
                    continue
                zf.write(p, p.relative_to(folder))
