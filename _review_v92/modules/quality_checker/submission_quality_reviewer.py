from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import json
import math
import re

from PIL import Image, ImageChops, ImageSequence, ImageStat

from modules.constants import FORMAT_LABELS, PLANNING_COUNTS


@dataclass
class FileQualityCheck:
    no: int
    filename: str
    ext: str
    width: int
    height: int
    size_bytes: int
    alpha_coverage_pct: float
    min_margin_px: int
    frame_count: int
    motion_change_pct: float
    estimated_phrase: str
    readability_score: int
    quality_score: int
    status: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DuplicateFinding:
    kind: str
    target: str
    matches: list[str]
    severity: str
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SyncFinding:
    filename: str
    frame_count: int
    motion_change_pct: float
    sync_status: str
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SubmissionQualityReport:
    package_dir: str
    format_key: str
    format_label: str
    expected_count: int
    actual_count: int
    overall_score: int
    final_status: str
    summary: str
    warnings: list[str]
    file_checks: list[dict[str, Any]]
    duplicate_findings: list[dict[str, Any]]
    expression_balance: dict[str, Any]
    sync_findings: list[dict[str, Any]]
    json_path: str
    html_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SubmissionQualityReviewer:
    """제출 직전 품질 검사를 수행합니다.

    공식 심사 기준을 대체하지 않습니다. 이 모듈은 크기/용량/투명도/가독성/중복/움직임
    동기화 같은 기술·기획 위험을 사전에 줄이기 위한 로컬 검사 도구입니다.
    """

    CANVAS = (360, 360)
    PNG_WARN_BYTES = 500 * 1024
    GIF_WARN_BYTES = 2 * 1024 * 1024

    def review(
        self,
        package_dir: str | Path,
        format_key: str,
        expressions: list[dict[str, Any]] | list[Any] | None = None,
        output_dir: str | Path | None = None,
    ) -> SubmissionQualityReport:
        package_dir = Path(package_dir)
        item_dir = package_dir / "items" if (package_dir / "items").exists() else package_dir
        output_dir = Path(output_dir or package_dir / "meta")
        output_dir.mkdir(parents=True, exist_ok=True)
        exprs = self._normalize_expressions(expressions)
        files = sorted([p for p in item_dir.iterdir() if p.is_file() and p.suffix.lower() in [".png", ".gif", ".webp"]]) if item_dir.exists() else []
        expected_count = PLANNING_COUNTS.get(format_key, len(files))
        warnings: list[str] = []
        if not item_dir.exists():
            warnings.append("items 폴더를 찾지 못했습니다. 패키지 경로를 확인하세요.")
        if len(files) < expected_count:
            warnings.append(f"생성 수량 {len(files)}개가 내부 기획 기준 {expected_count}개보다 적습니다. 공식 제출 기준을 다시 확인하세요.")
        if len(files) > 40:
            warnings.append("파일 수가 많습니다. 실제 제출 포맷별 필요 수량에 맞게 선별하세요.")

        file_checks = []
        hashes: dict[str, str] = {}
        for idx, path in enumerate(files, start=1):
            phrase = self._phrase_for_index(exprs, idx)
            check = self._check_file(idx, path, format_key, phrase)
            file_checks.append(check)
            try:
                hashes[path.name] = self._average_hash(path)
            except Exception:
                pass

        selected_exprs = exprs[:len(files)] if files else exprs
        duplicate_findings = self._find_duplicate_files(hashes)
        duplicate_findings.extend(self._find_duplicate_phrases(selected_exprs))
        expression_balance = self._expression_balance(selected_exprs)
        sync_findings = self._sync_findings(file_checks, format_key)

        warning_count = len(warnings)
        warning_count += sum(1 for c in file_checks if c.status != "PASS")
        warning_count += sum(1 for d in duplicate_findings if d.severity == "높음") * 2
        warning_count += sum(1 for d in duplicate_findings if d.severity == "중간")
        warning_count += len(expression_balance.get("warnings", []))
        warning_count += sum(1 for s in sync_findings if s.sync_status != "PASS")

        avg_file_score = round(sum(c.quality_score for c in file_checks) / max(1, len(file_checks))) if file_checks else 0
        count_penalty = 12 if len(files) < expected_count else 0
        overall_score = max(0, min(100, avg_file_score - warning_count * 2 - count_penalty))
        if overall_score >= 85 and not warnings and all(c.status == "PASS" for c in file_checks):
            final_status = "제출 준비 양호"
        elif overall_score >= 70:
            final_status = "보완 후 제출 권장"
        else:
            final_status = "제출 전 수정 필요"
        summary = self._build_summary(overall_score, final_status, len(files), expected_count, format_key)

        report = SubmissionQualityReport(
            package_dir=str(package_dir),
            format_key=format_key,
            format_label=FORMAT_LABELS.get(format_key, format_key),
            expected_count=expected_count,
            actual_count=len(files),
            overall_score=overall_score,
            final_status=final_status,
            summary=summary,
            warnings=warnings,
            file_checks=[c.to_dict() for c in file_checks],
            duplicate_findings=[d.to_dict() for d in duplicate_findings],
            expression_balance=expression_balance,
            sync_findings=[s.to_dict() for s in sync_findings],
            json_path="",
            html_path="",
        )
        json_path = output_dir / "final_submission_review.json"
        html_path = output_dir / "final_submission_review.html"
        report.json_path = str(json_path)
        report.html_path = str(html_path)
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(self._html_report(report), encoding="utf-8")
        return report

    def _normalize_expressions(self, expressions: list[dict[str, Any]] | list[Any] | None) -> list[dict[str, Any]]:
        normalized = []
        for item in expressions or []:
            if hasattr(item, "to_dict"):
                normalized.append(item.to_dict())
            elif isinstance(item, dict):
                normalized.append(dict(item))
        return normalized

    def _phrase_for_index(self, exprs: list[dict[str, Any]], idx: int) -> str:
        if 0 <= idx - 1 < len(exprs):
            item = exprs[idx - 1]
            return str(item.get("phrase") or item.get("text") or "")
        return ""

    def _check_file(self, idx: int, path: Path, format_key: str, phrase: str) -> FileQualityCheck:
        notes: list[str] = []
        width = height = 0
        frame_count = 1
        motion_change_pct = 0.0
        alpha_coverage_pct = 0.0
        min_margin = 999
        ext = path.suffix.lower()
        quality_score = 100
        try:
            with Image.open(path) as im:
                frames = []
                if ext == ".gif":
                    for f in ImageSequence.Iterator(im):
                        frame = f.convert("RGBA").resize(self.CANVAS)
                        frames.append(frame)
                    frame_count = len(frames)
                    base = frames[0] if frames else im.convert("RGBA")
                    width, height = base.size
                    if frames:
                        motion_change_pct = self._motion_change(frames)
                else:
                    base = im.convert("RGBA")
                    width, height = base.size
                    frames = [base]
                alpha = base.getchannel("A")
                alpha_nonzero = alpha.point(lambda p: 255 if p > 8 else 0)
                bbox = alpha_nonzero.getbbox()
                alpha_pixels = sum(1 for p in alpha_nonzero.getdata() if p > 0)
                alpha_coverage_pct = round(alpha_pixels / (width * height) * 100, 2) if width and height else 0.0
                if bbox:
                    left, top, right, bottom = bbox
                    min_margin = min(left, top, width - right, height - bottom)
                else:
                    min_margin = 0
                    notes.append("캐릭터/문구가 비어 있는 이미지처럼 보입니다.")
        except Exception as exc:
            notes.append(f"이미지 읽기 실패: {exc}")
            quality_score -= 45

        expected_ext = ".gif" if format_key in ["animated", "animated_text"] else ".png"
        if ext != expected_ext:
            notes.append(f"확장자 확인 필요: 기대 {expected_ext}")
            quality_score -= 20
        if (width, height) != self.CANVAS:
            notes.append("360×360 크기가 아닙니다.")
            quality_score -= 25
        size_bytes = path.stat().st_size if path.exists() else 0
        limit = self.GIF_WARN_BYTES if expected_ext == ".gif" else self.PNG_WARN_BYTES
        if size_bytes > limit:
            notes.append("파일 용량 압축 권장")
            quality_score -= 12
        if min_margin <= 4:
            notes.append("캐릭터/문구가 가장자리와 너무 가깝습니다. 잘림 위험이 있습니다.")
            quality_score -= 12
        elif min_margin <= 10:
            notes.append("여백이 좁습니다. 작은 화면에서 답답해 보일 수 있습니다.")
            quality_score -= 5
        if alpha_coverage_pct < 5:
            notes.append("보이는 요소가 너무 작거나 투명 영역이 과도합니다.")
            quality_score -= 10
        if alpha_coverage_pct > 88:
            notes.append("화면을 너무 꽉 채웁니다. 말풍선/캐릭터 잘림을 확인하세요.")
            quality_score -= 8
        readability = self._readability_score(phrase)
        if readability < 65:
            notes.append("문구가 길어 360×360 화면에서 가독성 저하 가능성이 큽니다.")
            quality_score -= 10
        elif readability < 78:
            notes.append("문구 길이를 조금 줄이면 가독성이 좋아집니다.")
            quality_score -= 4
        if format_key in ["animated", "animated_text"]:
            if frame_count < 6:
                notes.append("프레임 수가 적어 움직임이 부자연스러울 수 있습니다.")
                quality_score -= 8
            if frame_count > 24:
                notes.append("프레임 수가 많아 용량 증가 위험이 있습니다.")
                quality_score -= 8
            if motion_change_pct < 0.7:
                notes.append("프레임 변화가 작아 움직이는 느낌이 약할 수 있습니다.")
                quality_score -= 8
            if motion_change_pct > 35:
                notes.append("프레임 변화가 커서 흔들림/깜빡임이 과할 수 있습니다.")
                quality_score -= 6
        status = "PASS" if quality_score >= 80 and not any("아닙니다" in n or "실패" in n for n in notes) else "CHECK"
        return FileQualityCheck(
            no=idx,
            filename=path.name,
            ext=ext,
            width=width,
            height=height,
            size_bytes=size_bytes,
            alpha_coverage_pct=alpha_coverage_pct,
            min_margin_px=0 if min_margin == 999 else int(min_margin),
            frame_count=frame_count,
            motion_change_pct=round(motion_change_pct, 2),
            estimated_phrase=phrase,
            readability_score=readability,
            quality_score=max(0, min(100, quality_score)),
            status=status,
            notes=notes or ["기본 품질 검사 통과"],
        )

    def _readability_score(self, phrase: str) -> int:
        phrase = phrase or ""
        # 한글/영문 혼합 길이 기준의 보수적 추정. 실제 렌더링 폰트 검사는 별도 보강 가능.
        length = len(phrase.strip())
        if length <= 5:
            return 96
        if length <= 8:
            return 90
        if length <= 12:
            return 80
        if length <= 16:
            return 68
        if length <= 20:
            return 55
        return 42

    def _motion_change(self, frames: list[Image.Image]) -> float:
        if len(frames) < 2:
            return 0.0
        changes = []
        prev = frames[0].convert("L")
        for frame in frames[1:]:
            cur = frame.convert("L")
            diff = ImageChops.difference(prev, cur)
            stat = ImageStat.Stat(diff)
            changes.append(stat.mean[0] / 255 * 100)
            prev = cur
        return float(sum(changes) / max(1, len(changes)))

    def _average_hash(self, path: Path) -> str:
        with Image.open(path) as im:
            if path.suffix.lower() == ".gif":
                frame = next(ImageSequence.Iterator(im)).convert("L")
            else:
                frame = im.convert("L")
            small = frame.resize((8, 8), Image.LANCZOS)
            values = list(small.getdata())
            avg = sum(values) / len(values)
            return "".join("1" if v >= avg else "0" for v in values)

    def _hamming(self, a: str, b: str) -> int:
        return sum(ch1 != ch2 for ch1, ch2 in zip(a, b))

    def _find_duplicate_files(self, hashes: dict[str, str]) -> list[DuplicateFinding]:
        findings: list[DuplicateFinding] = []
        names = list(hashes)
        if len(names) < 2:
            return findings

        parent = {name: name for name in names}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for i, name in enumerate(names):
            for other in names[i + 1:]:
                dist = self._hamming(hashes[name], hashes[other])
                # 절차형 시안은 같은 캐릭터를 기반으로 표현만 바뀌므로 너무 엄격하게 잡지 않습니다.
                if dist <= 2:
                    union(name, other)

        groups: dict[str, list[str]] = defaultdict(list)
        for name in names:
            groups[find(name)].append(name)

        for group in groups.values():
            if len(group) >= 3:
                findings.append(DuplicateFinding(
                    kind="이미지 유사",
                    target=group[0],
                    matches=group[1:8],
                    severity="중간" if len(group) <= 5 else "높음",
                    note="같은 캐릭터 기반 표현이 시각적으로 비슷합니다. 핵심 표정/효과/문구 위치 차이를 일부 키우면 세트 다양성이 좋아집니다.",
                ))
        return findings

    def _normalize_phrase(self, phrase: str) -> str:
        return re.sub(r"\s+|[.?!~…ㅠㅜㅋ]+", "", phrase.strip().lower())

    def _find_duplicate_phrases(self, exprs: list[dict[str, Any]]) -> list[DuplicateFinding]:
        findings: list[DuplicateFinding] = []
        phrases = [str(e.get("phrase") or e.get("text") or "") for e in exprs]
        normalized = [(p, self._normalize_phrase(p)) for p in phrases if p]
        seen: dict[str, list[str]] = defaultdict(list)
        for original, norm in normalized:
            seen[norm].append(original)
        for norm, originals in seen.items():
            if norm and len(originals) > 1:
                findings.append(DuplicateFinding("문구 중복", originals[0], originals[1:], "높음", "동일/거의 동일한 문구가 반복됩니다."))
        for i, (p, n) in enumerate(normalized):
            close = []
            for p2, n2 in normalized[i + 1:]:
                if n and n2 and n != n2 and SequenceMatcher(None, n, n2).ratio() >= 0.86:
                    close.append(p2)
            if close:
                findings.append(DuplicateFinding("문구 유사", p, close[:5], "중간", "역할이 비슷한 문구가 많으면 세트가 단조로워질 수 있습니다."))
        return findings[:30]

    def _expression_balance(self, exprs: list[dict[str, Any]]) -> dict[str, Any]:
        categories = Counter(str(e.get("category") or e.get("emotion") or "기타") for e in exprs)
        formats = Counter(str(e.get("recommended_format") or "미지정") for e in exprs)
        total = max(1, len(exprs))
        warnings = []
        reply_count = categories.get("기본 답장", 0) + categories.get("확인", 0)
        reaction_count = categories.get("감정 리액션", 0) + categories.get("당황", 0) + categories.get("분노", 0) + categories.get("기쁨", 0)
        apology_count = categories.get("감사/사과", 0) + categories.get("감사", 0) + categories.get("사과", 0)
        if reply_count / total < 0.18:
            warnings.append("기본 답장형 표현 비율이 낮습니다. 넵/확인/잠시만요 계열을 보강하세요.")
        if reaction_count / total < 0.15:
            warnings.append("감정 리액션형 표현 비율이 낮습니다. 당황/기쁨/화남/민망 계열을 보강하세요.")
        if apology_count / total < 0.10:
            warnings.append("감사/사과/부탁 표현이 부족합니다. 실사용성이 낮아질 수 있습니다.")
        top_category = categories.most_common(1)[0] if categories else ("없음", 0)
        if top_category[1] / total > 0.38:
            warnings.append(f"'{top_category[0]}' 표현이 과도하게 많습니다. 감정 구성을 분산하세요.")
        return {
            "total_expressions": len(exprs),
            "category_counts": dict(categories),
            "format_counts": dict(formats),
            "top_category": {"name": top_category[0], "count": top_category[1]},
            "warnings": warnings,
            "recommended_mix": {
                "실사용 답장형": "약 30%",
                "감정 리액션형": "약 25%",
                "감사/사과/부탁형": "약 15%",
                "관계/대화 유지형": "약 15%",
                "시그니처/확장형": "약 15%",
            },
        }

    def _sync_findings(self, checks: list[FileQualityCheck], format_key: str) -> list[SyncFinding]:
        if format_key not in ["animated", "animated_text"]:
            return []
        findings: list[SyncFinding] = []
        for c in checks:
            if c.frame_count < 6:
                status = "CHECK"
                note = "프레임 수가 적어 캐릭터/문구 동기화가 단순해 보일 수 있습니다."
            elif c.motion_change_pct < 0.7:
                status = "CHECK"
                note = "프레임 변화가 약합니다. 문구 등장/캐릭터 동작 타이밍을 더 분명히 하세요."
            elif c.readability_score < 65:
                status = "CHECK"
                note = "문구가 길어 움직임 중 가독성이 떨어질 수 있습니다."
            else:
                status = "PASS"
                note = "기본 동기화 검사 통과"
            findings.append(SyncFinding(c.filename, c.frame_count, c.motion_change_pct, status, note))
        return findings

    def _build_summary(self, score: int, status: str, actual: int, expected: int, format_key: str) -> str:
        return f"{FORMAT_LABELS.get(format_key, format_key)} 패키지 {actual}개를 검사했습니다. 내부 기획 기준은 {expected}개이며, 최종 점수는 {score}점입니다. 판정: {status}."

    def _html_report(self, report: SubmissionQualityReport) -> str:
        def esc(v: Any) -> str:
            return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        file_rows = []
        for item in report.file_checks:
            notes = "; ".join(item.get("notes") or [])
            cls = "pass" if item.get("status") == "PASS" else "check"
            file_rows.append(
                f"<tr class='{cls}'><td>{item['no']:02d}</td><td>{esc(item['filename'])}</td><td>{item['width']}×{item['height']}</td><td>{item['size_bytes']:,}</td><td>{item['readability_score']}</td><td>{item['min_margin_px']}</td><td>{item['frame_count']}</td><td>{item['motion_change_pct']}</td><td>{item['quality_score']}</td><td>{item['status']}</td><td>{esc(notes)}</td></tr>"
            )
        warnings_html = "".join(f"<li>{esc(w)}</li>" for w in report.warnings) or "<li>패키지 수량 경고 없음</li>"
        dup_html = "".join(
            f"<li><b>{esc(d['kind'])}</b> · {esc(d['target'])} → {esc(', '.join(d['matches']))} / {esc(d['note'])}</li>" for d in report.duplicate_findings
        ) or "<li>중복 위험 없음</li>"
        balance_warnings = "".join(f"<li>{esc(w)}</li>" for w in report.expression_balance.get("warnings", [])) or "<li>표현 균형 기본 통과</li>"
        sync_rows = "".join(
            f"<tr><td>{esc(s['filename'])}</td><td>{s['frame_count']}</td><td>{s['motion_change_pct']}</td><td>{esc(s['sync_status'])}</td><td>{esc(s['note'])}</td></tr>" for s in report.sync_findings
        ) or "<tr><td colspan='5'>정지형 포맷이거나 동기화 검사 대상이 아닙니다.</td></tr>"
        return f"""<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<title>Final Submission Review</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 32px; line-height: 1.55; color: #222; }}
.card {{ border: 1px solid #e4e4e4; border-radius: 14px; padding: 18px; margin: 16px 0; background: #fff; }}
.score {{ font-size: 34px; font-weight: 800; }}
.pass td {{ background: #f7fff8; }}
.check td {{ background: #fff8e6; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
th, td {{ border: 1px solid #ddd; padding: 7px; font-size: 12px; vertical-align: top; }}
th {{ background: #f1f1f1; }}
.notice {{ background: #fff6d8; padding: 12px; border-radius: 10px; }}
</style>
</head>
<body>
<h1>최종 제출 전 품질 리뷰</h1>
<div class='card'>
<div class='score'>{report.overall_score}점</div>
<p><b>판정:</b> {esc(report.final_status)}</p>
<p>{esc(report.summary)}</p>
<p><b>포맷:</b> {esc(report.format_label)} / <b>패키지:</b> {esc(report.package_dir)}</p>
</div>
<div class='notice'>이 리포트는 제출 전 기술·기획 검사용입니다. 공식 제출 기준, 저작권·상표권, 생성형 AI 제한, 폰트/이미지 라이선스는 제출 직전 별도로 확인해야 합니다.</div>
<h2>패키지 경고</h2><ul>{warnings_html}</ul>
<h2>파일별 품질 검사</h2>
<table><thead><tr><th>No</th><th>파일</th><th>크기</th><th>용량</th><th>가독성</th><th>최소여백</th><th>프레임</th><th>움직임%</th><th>점수</th><th>상태</th><th>메모</th></tr></thead><tbody>{''.join(file_rows)}</tbody></table>
<h2>표현 중복/유사 위험</h2><ul>{dup_html}</ul>
<h2>표현 구성 균형</h2>
<p><b>총 표현:</b> {report.expression_balance.get('total_expressions', 0)}개</p>
<ul>{balance_warnings}</ul>
<pre>{esc(json.dumps(report.expression_balance.get('category_counts', {}), ensure_ascii=False, indent=2))}</pre>
<h2>움직이는 문구 동기화 검사</h2>
<table><thead><tr><th>파일</th><th>프레임</th><th>움직임 변화%</th><th>상태</th><th>메모</th></tr></thead><tbody>{sync_rows}</tbody></table>
<h2>수동 최종 체크</h2>
<ul>
<li>공식 카카오 이모티콘 스튜디오 최신 제출 기준과 수량을 확인했습니다.</li>
<li>기존 캐릭터·브랜드·작가 그림체·문구를 모방하지 않았습니다.</li>
<li>생성형 AI 완성 이미지를 제출용으로 사용하지 않았습니다.</li>
<li>사용한 폰트·이미지·소재·효과의 상업적 이용 권리를 확인했습니다.</li>
<li>캐릭터 원본 스케치, 제작 과정, 수정 이력을 보관했습니다.</li>
</ul>
</body></html>"""
