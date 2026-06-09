from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import json
import re
import shutil
import zipfile

from PIL import Image, ImageSequence

from modules.constants import FORMAT_LABELS, PLANNING_COUNTS
from modules.prototype_generator.character_prototype_builder import CharacterPrototypeBuilder, PrototypeSpec
from modules.animated_text_emoticon.frame_builder import AnimatedTextFrameBuilder


@dataclass
class SubmissionFileCheck:
    no: int
    filename: str
    format_key: str
    width: int
    height: int
    size_bytes: int
    has_alpha: bool
    ext_ok: bool
    size_ok: bool
    dimension_ok: bool
    notes: list[str]

    @property
    def status(self) -> str:
        return "PASS" if self.ext_ok and self.size_ok and self.dimension_ok else "CHECK"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status
        return data


@dataclass
class SubmissionPackageResult:
    project_name: str
    format_key: str
    format_label: str
    expected_count: int
    created_count: int
    package_dir: str
    zip_path: str
    manifest_path: str
    checklist_path: str
    file_checks: list[dict[str, Any]]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SubmissionPackageBuilder:
    """포맷별 제출 준비 폴더를 만듭니다.

    이 모듈은 카카오 공식 심사 통과를 보장하지 않습니다. 포맷별 수량은 내부 기획
    기준이며, 제출 직전 공식 스튜디오 가이드를 다시 확인해야 합니다.
    """

    CANVAS = (360, 360)
    PNG_WARN_BYTES = 500 * 1024
    GIF_WARN_BYTES = 2 * 1024 * 1024

    def __init__(self) -> None:
        self.prototype_builder = CharacterPrototypeBuilder()
        self.gif_builder = AnimatedTextFrameBuilder()

    def build(
        self,
        spec: PrototypeSpec,
        expressions: list[dict[str, Any]] | list[Any] | None,
        output_root: str | Path,
        project_name: str,
        format_key: str = "static_text",
        target_count: int | None = None,
    ) -> SubmissionPackageResult:
        if format_key not in FORMAT_LABELS:
            raise ValueError(f"지원하지 않는 포맷입니다: {format_key}")
        output_root = Path(output_root)
        safe_project = self._safe_name(project_name or "kakao_emoticon_project")
        package_dir = output_root / safe_project / format_key
        if package_dir.exists():
            shutil.rmtree(package_dir)
        item_dir = package_dir / "items"
        meta_dir = package_dir / "meta"
        item_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)

        exprs = self._normalize_expressions(expressions)
        count = int(target_count or PLANNING_COUNTS.get(format_key, 24))
        count = max(1, min(count, len(exprs) if exprs else count))
        warnings: list[str] = []
        if not expressions:
            warnings.append("표현 은행이 비어 있어 기본 표현으로 패키지를 생성했습니다.")
        if count < PLANNING_COUNTS.get(format_key, count):
            warnings.append("현재 생성 수량이 내부 기획 기준 수량보다 적습니다. 최종 제출 전 포맷별 공식 필요 수량을 확인하세요.")

        file_paths: list[Path] = []
        for idx, expr in enumerate(exprs[:count], start=1):
            phrase = str(expr.get("phrase") or expr.get("text") or "확인했습니다")
            emotion = str(expr.get("emotion") or expr.get("category") or "기본")
            recommended_motion = str(expr.get("recommended_motion") or "통통 튐")
            if format_key in ["static", "static_text", "big", "series"]:
                show_phrase = format_key in ["static_text", "big"]
                image = self.prototype_builder.render_single(spec, expression=emotion, phrase=(phrase if show_phrase else None))
                path = item_dir / f"{idx:02d}.png"
                image.save(path)
            elif format_key in ["animated", "animated_text"]:
                base_path = meta_dir / f"base_{idx:02d}.png"
                base_image = self.prototype_builder.render_single(spec, expression=emotion, phrase=None)
                base_image.save(base_path)
                path = item_dir / f"{idx:02d}.gif"
                if format_key == "animated_text":
                    gif_phrase = phrase
                else:
                    gif_phrase = self._minimal_symbol_phrase(emotion)
                self.gif_builder.build_gif(
                    base_path,
                    gif_phrase,
                    path,
                    text_motion=self._text_motion_for(phrase, emotion, recommended_motion),
                    character_motion=self._character_motion_for(recommended_motion, emotion),
                    frames=8,
                    duration_ms=110,
                )
            else:
                raise ValueError(f"지원하지 않는 포맷입니다: {format_key}")
            file_paths.append(path)

        file_checks = [self._check_file(i, p, format_key) for i, p in enumerate(file_paths, start=1)]
        fail_count = sum(1 for c in file_checks if c.status != "PASS")
        if fail_count:
            warnings.append(f"검사 확인 필요 파일 {fail_count}개가 있습니다.")
        if format_key in ["animated", "animated_text"]:
            oversized = [c.filename for c in file_checks if c.size_bytes > self.GIF_WARN_BYTES]
            if oversized:
                warnings.append("GIF 용량이 큰 파일이 있습니다. 프레임 수/색상 수/움직임을 줄여 압축하세요.")

        manifest = {
            "project_name": project_name,
            "format_key": format_key,
            "format_label": FORMAT_LABELS.get(format_key, format_key),
            "expected_count_internal_planning": PLANNING_COUNTS.get(format_key),
            "created_count": len(file_paths),
            "prototype_spec": spec.to_dict(),
            "items": [c.to_dict() for c in file_checks],
            "warnings": warnings,
            "notice": "이 패키지는 제출 준비 보조 자료입니다. 카카오 공식 제출 규격, AI 활용 제한, 저작권/상표권 위험은 제출 직전 반드시 재확인하세요.",
        }
        manifest_path = meta_dir / "submission_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        checklist_path = meta_dir / "submission_checklist.html"
        checklist_path.write_text(self._html_checklist(manifest), encoding="utf-8")

        zip_path = output_root / f"{safe_project}_{format_key}_submission_package.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(package_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=str(path.relative_to(package_dir.parent)))

        return SubmissionPackageResult(
            project_name=project_name,
            format_key=format_key,
            format_label=FORMAT_LABELS.get(format_key, format_key),
            expected_count=PLANNING_COUNTS.get(format_key, len(file_paths)),
            created_count=len(file_paths),
            package_dir=str(package_dir),
            zip_path=str(zip_path),
            manifest_path=str(manifest_path),
            checklist_path=str(checklist_path),
            file_checks=[c.to_dict() for c in file_checks],
            warnings=warnings,
        )

    def _normalize_expressions(self, expressions: list[dict[str, Any]] | list[Any] | None) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in expressions or []:
            if hasattr(item, "to_dict"):
                normalized.append(item.to_dict())
            elif isinstance(item, dict):
                normalized.append(dict(item))
        if normalized:
            return normalized
        return [
            {"phrase": "넵", "emotion": "확인", "recommended_motion": "작게 끄덕임"},
            {"phrase": "확인했습니다", "emotion": "확인", "recommended_motion": "체크 도장 + 문구 쿵 등장"},
            {"phrase": "감사합니다", "emotion": "감사", "recommended_motion": "꾸벅 숙이기 + 문구 부드럽게 등장"},
            {"phrase": "죄송합니다", "emotion": "사과", "recommended_motion": "작아짐 + 땀방울 + 문구 떨림"},
            {"phrase": "퇴근하고 싶습니다", "emotion": "피곤", "recommended_motion": "녹아내림/구겨짐 + 글자 축 처짐"},
            {"phrase": "잠시만요", "emotion": "기다림", "recommended_motion": "점 3개 순차 등장"},
            {"phrase": "좋아요", "emotion": "기쁨", "recommended_motion": "통통 튐"},
            {"phrase": "살려주세요", "emotion": "당황", "recommended_motion": "부들부들 + 땀방울"},
        ]

    def _check_file(self, no: int, path: Path, format_key: str) -> SubmissionFileCheck:
        notes: list[str] = []
        expected_ext = ".gif" if format_key in ["animated", "animated_text"] else ".png"
        ext_ok = path.suffix.lower() == expected_ext
        if not ext_ok:
            notes.append(f"확장자 확인 필요: 기대 {expected_ext}")
        width = height = 0
        has_alpha = False
        try:
            with Image.open(path) as im:
                if path.suffix.lower() == ".gif":
                    first = next(ImageSequence.Iterator(im)).convert("RGBA")
                    width, height = first.size
                    has_alpha = True
                else:
                    im = im.convert("RGBA")
                    width, height = im.size
                    has_alpha = im.getextrema()[3][0] < 255
        except Exception as exc:
            notes.append(f"이미지 읽기 실패: {exc}")
        dimension_ok = (width, height) == self.CANVAS
        if not dimension_ok:
            notes.append("360×360 크기 확인 필요")
        size_bytes = path.stat().st_size if path.exists() else 0
        limit = self.GIF_WARN_BYTES if expected_ext == ".gif" else self.PNG_WARN_BYTES
        size_ok = size_bytes <= limit
        if not size_ok:
            notes.append("용량 압축 권장")
        if expected_ext == ".png" and not has_alpha:
            notes.append("투명 배경 여부 확인 권장")
        return SubmissionFileCheck(no, path.name, format_key, width, height, size_bytes, has_alpha, ext_ok, size_ok, dimension_ok, notes)

    def _text_motion_for(self, phrase: str, emotion: str, motion: str) -> str:
        text = f"{phrase} {emotion} {motion}"
        if any(k in text for k in ["확인", "접수", "완료", "체크"]):
            return "도장처럼 등장"
        if any(k in text for k in ["죄송", "사과", "당황", "분노", "부들", "떨림"]):
            return "살짝 떨림"
        if any(k in text for k in ["감사", "잘자", "위로", "괜찮"]):
            return "천천히 나타남"
        if any(k in text for k in ["퇴근", "피곤", "살려", "구겨", "축"]):
            return "축 처짐"
        if "넵" in text or "기다" in text:
            return "점 세 개 순차 등장"
        return "도장처럼 등장"

    def _character_motion_for(self, motion: str, emotion: str) -> str:
        text = f"{motion} {emotion}"
        if any(k in text for k in ["꾸벅", "감사", "사과"]):
            return "꾸벅"
        if any(k in text for k in ["작아", "민망"]):
            return "작아짐"
        if any(k in text for k in ["부들", "흔들", "분노", "당황"]):
            return "부들부들 흔들림"
        if any(k in text for k in ["피곤", "축", "녹아", "구겨"]):
            return "축 처짐"
        return "통통 튐"

    def _minimal_symbol_phrase(self, emotion: str) -> str:
        if "감사" in emotion:
            return "꾸벅"
        if "사과" in emotion:
            return "ㅠㅠ"
        if "확인" in emotion:
            return "✓"
        if "피곤" in emotion:
            return "..."
        return "!"

    def _safe_name(self, value: str) -> str:
        cleaned = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", value).strip("_")
        return cleaned[:80] or "kakao_emoticon_project"

    def _html_checklist(self, manifest: dict[str, Any]) -> str:
        rows = []
        for item in manifest["items"]:
            status = item.get("status", "CHECK")
            notes = ", ".join(item.get("notes") or [])
            rows.append(
                f"<tr><td>{item['no']:02d}</td><td>{item['filename']}</td><td>{item['width']}×{item['height']}</td><td>{item['size_bytes']:,}</td><td>{status}</td><td>{notes}</td></tr>"
            )
        warnings = "".join(f"<li>{w}</li>" for w in manifest.get("warnings", [])) or "<li>기본 검사 경고 없음</li>"
        return f"""<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<title>Submission Checklist</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 32px; line-height: 1.55; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 13px; }}
th {{ background: #f3f3f3; }}
.notice {{ background: #fff7dc; padding: 12px 16px; border-radius: 10px; }}
.pass {{ color: #167a32; font-weight: 700; }}
</style>
</head>
<body>
<h1>카카오 이모티콘 제출 준비 체크리스트</h1>
<p><b>프로젝트:</b> {manifest['project_name']}</p>
<p><b>포맷:</b> {manifest['format_label']} / 생성 수량 {manifest['created_count']}개</p>
<div class='notice'>{manifest['notice']}</div>
<h2>자동 경고</h2>
<ul>{warnings}</ul>
<h2>파일 검사</h2>
<table>
<thead><tr><th>No</th><th>파일명</th><th>크기</th><th>용량(byte)</th><th>상태</th><th>메모</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<h2>최종 수동 확인</h2>
<ul>
<li>공식 카카오 이모티콘 스튜디오의 최신 포맷/용량/수량 기준을 다시 확인했습니다.</li>
<li>기존 캐릭터, 브랜드, 작가의 그림체·표정·문구를 모방하지 않았습니다.</li>
<li>생성형 AI 완성 이미지를 제출용으로 사용하지 않았습니다.</li>
<li>사용한 폰트·이미지·효과의 상업적 이용 권리를 확인했습니다.</li>
<li>캐릭터 원본 스케치와 제작 이력을 별도로 보관했습니다.</li>
</ul>
</body>
</html>"""
