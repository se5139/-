from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import csv
import hashlib
import json
import shutil
import sqlite3
import time
import zipfile

from PIL import Image, ImageSequence

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from modules.pre_submission_qc_engine import V71PreSubmissionQCEngine


@dataclass
class V72SubmissionAutofixLockReport:
    project_name: str
    output_dir: str
    base_qc_zip: str
    base_qc_report_html: str
    static_export_dir: str
    animated_export_dir: str
    static_export_zip: str
    animated_export_zip: str
    final_submission_zip: str
    locked_review_zip: str
    autofix_log_csv: str
    autofix_log_json: str
    final_manifest_json: str
    lock_manifest_json: str
    html_report_path: str
    learning_db: str
    package_status: str
    submission_lock_required: bool
    lock_reasons: List[str]
    autofix_actions: List[str]
    exported_static_count: int
    exported_animated_count: int
    exported_gif_count: int
    base_pass_count: int
    base_warn_count: int
    base_fail_count: int
    final_scores: Dict[str, int]
    safety_notes: List[str]
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class V72SubmissionAutofixLockEngine(V71PreSubmissionQCEngine):
    """v72 제출 패키지 잠금/자동 보정 엔진.

    v71 QC 결과를 기반으로 안전한 범위의 자동 보정(파일명 정리, PNG 최적화,
    GIF 프레임/용량 후보 점검, 제출 패키지 잠금/해제 판단)을 수행한다.
    원본은 덮어쓰지 않고 final_export 폴더에 복사/보정본만 생성한다.
    """

    VERSION = "72.0.0"

    AUTOFIX_RULES = [
        "v71 QC FAIL이 있으면 최종 제출 ZIP 잠금",
        "원본 덮어쓰기 금지, final_export 폴더에 보정본 생성",
        "파일명 static_01.png~static_32.png 정규화",
        "파일명 animated_01.png/gif~animated_24 정규화",
        "PNG 360x360 재저장 및 optimize 적용",
        "GIF 24프레임 이하/2MB 이하 사전 확인",
        "필수 GIF 3개 이상 유지",
        "잠금 해제 조건과 남은 공식 재확인 항목을 manifest에 기록",
        "Jinja2 HTML 제출 패키지 리포트 생성",
        "API 키 원문 저장 금지와 기존 캐릭터 복제 금지 유지",
    ]

    def _sha256_v72(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _read_csv_rows(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _find_source_file(self, base_dir: Path, source_name: str) -> Path | None:
        # Prefer exact leaf-name match inside the generated v70 base set.
        matches = list(base_dir.rglob(source_name))
        if matches:
            return matches[0]
        return None

    def _png_autofix(self, src: Path, dst: Path) -> Tuple[str, Dict[str, Any]]:
        dst.parent.mkdir(parents=True, exist_ok=True)
        info: Dict[str, Any] = {"source_bytes": src.stat().st_size if src.exists() else 0}
        try:
            with Image.open(src) as im:
                im = im.convert("RGBA")
                if im.size != self.STUDIO_DRAFT_LIMITS["size"]:
                    im = im.resize(self.STUDIO_DRAFT_LIMITS["size"], Image.LANCZOS)
                    action = "resize_360_rgba_optimize"
                else:
                    action = "rgba_optimize"
                im.save(dst, format="PNG", optimize=True)
                info.update({"width": im.size[0], "height": im.size[1], "mode": "RGBA", "target_bytes": dst.stat().st_size})
                if dst.stat().st_size > self.STUDIO_DRAFT_LIMITS["static_png_max_bytes"]:
                    info["warning"] = "still_over_static_png_limit"
                return action, info
        except Exception as exc:
            shutil.copy2(src, dst)
            info["error"] = str(exc)
            info["target_bytes"] = dst.stat().st_size
            return "copy_fallback", info

    def _gif_autofix(self, src: Path, dst: Path) -> Tuple[str, Dict[str, Any]]:
        dst.parent.mkdir(parents=True, exist_ok=True)
        info: Dict[str, Any] = {"source_bytes": src.stat().st_size if src.exists() else 0}
        try:
            frames: List[Image.Image] = []
            durations: List[int] = []
            with Image.open(src) as im:
                for frame in ImageSequence.Iterator(im):
                    frames.append(frame.convert("RGBA").resize(self.STUDIO_DRAFT_LIMITS["size"], Image.LANCZOS))
                    durations.append(int(frame.info.get("duration", 90)))
            original_count = len(frames)
            if len(frames) > self.STUDIO_DRAFT_LIMITS["gif_max_frames"]:
                step = max(1, len(frames) // self.STUDIO_DRAFT_LIMITS["gif_max_frames"])
                frames = frames[::step][: self.STUDIO_DRAFT_LIMITS["gif_max_frames"]]
                durations = durations[::step][: len(frames)]
                action = "gif_frame_reduce_resize"
            else:
                action = "gif_resize_copy"
            if not frames:
                shutil.copy2(src, dst)
                return "gif_copy_fallback", {"error": "no_frames", "target_bytes": dst.stat().st_size}
            frames[0].save(dst, save_all=True, append_images=frames[1:], duration=durations or 90, loop=0, disposal=2, optimize=True)
            info.update({"source_frames": original_count, "target_frames": len(frames), "target_bytes": dst.stat().st_size})
            if dst.stat().st_size > self.STUDIO_DRAFT_LIMITS["animated_gif_max_bytes"]:
                info["warning"] = "still_over_gif_limit"
            return action, info
        except Exception as exc:
            shutil.copy2(src, dst)
            info["error"] = str(exc)
            info["target_bytes"] = dst.stat().st_size
            return "gif_copy_fallback", info

    def _copy_autofix(self, src: Path, dst: Path) -> Tuple[str, Dict[str, Any]]:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() == ".png":
            return self._png_autofix(src, dst.with_suffix(".png"))
        if src.suffix.lower() == ".gif":
            return self._gif_autofix(src, dst.with_suffix(".gif"))
        shutil.copy2(src, dst)
        return "copy_no_change", {"source_bytes": src.stat().st_size, "target_bytes": dst.stat().st_size}

    def _write_rows_v72(self, csv_path: Path, json_path: Path, rows: List[Dict[str, Any]]) -> None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        keys: List[str] = []
        for row in rows:
            for k in row.keys():
                if k not in keys:
                    keys.append(k)
        if not keys:
            keys = ["status", "action"]
            rows = [{"status": "WARN", "action": "no_actions"}]
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def _zip_paths_v72(self, zip_path: Path, paths: List[Path], root: Path | None = None) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                if not p.exists():
                    continue
                if p.is_dir():
                    for child in p.rglob("*"):
                        if child.is_file():
                            arc = str(child.relative_to(root or p.parent))
                            zf.write(child, arc)
                else:
                    arc = str(p.relative_to(root)) if root and p.is_relative_to(root) else p.name
                    zf.write(p, arc)

    def _store_v72_learning(self, db: Path, project_name: str, status: str, scores: Dict[str, int], counts: Dict[str, int]) -> None:
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v72_submission_autofix_runs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    package_status TEXT,
                    exported_static_count INTEGER,
                    exported_animated_count INTEGER,
                    exported_gif_count INTEGER,
                    final_readiness INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v72_submission_autofix_scores(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    score_key TEXT,
                    score_value INTEGER
                )
            """)
            cur.execute(
                "INSERT INTO v72_submission_autofix_runs(created_at, project_name, package_status, exported_static_count, exported_animated_count, exported_gif_count, final_readiness) VALUES(?,?,?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), project_name, status, counts.get("static", 0), counts.get("animated", 0), counts.get("gif", 0), scores.get("final_package_readiness", 0)),
            )
            run_id = cur.lastrowid
            for k, v in scores.items():
                cur.execute("INSERT INTO v72_submission_autofix_scores(run_id, score_key, score_value) VALUES(?,?,?)", (run_id, k, int(v)))
            con.commit()

    def _render_v72_report(self, template_dir: Path, out_path: Path, context: Dict[str, Any]) -> None:
        template_dir.mkdir(parents=True, exist_ok=True)
        template = template_dir / "v72_submission_autofix_lock_report.html.j2"
        if not template.exists():
            template.write_text("""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>v72 제출 패키지 자동보정/잠금 리포트</title>
<style>
body{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f7fb;color:#172033;margin:0;padding:28px}.wrap{max-width:1180px;margin:auto}.hero{background:linear-gradient(135deg,#111827,#059669,#14b8a6);color:white;border-radius:28px;padding:28px 32px;box-shadow:0 18px 42px rgba(15,23,42,.20)}.card{background:white;border:1px solid #e5e7eb;border-radius:22px;padding:20px;margin-top:18px;box-shadow:0 10px 28px rgba(15,23,42,.06)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}.score{font-size:30px;font-weight:800;color:#059669}.badge{display:inline-block;background:#dcfce7;color:#166534;border-radius:999px;padding:5px 10px;margin:3px;font-weight:700}.lock{background:#fee2e2;color:#991b1b}.unlock{background:#dcfce7;color:#166534}.mono{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:16px;padding:14px;overflow:auto}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left;font-size:14px}
</style></head><body><div class="wrap"><div class="hero"><h1>v72 제출 패키지 자동보정/잠금 리포트</h1><p>v71 QC → 안전 자동보정 → 파일명 정규화 → 최종 ZIP 잠금/해제</p></div>
<div class="card"><h2>패키지 상태</h2><p><span class="badge {{ 'lock' if submission_lock_required else 'unlock' }}">{{ package_status }}</span></p><p>정지형 {{ exported_static_count }}개 · 움직이는형 {{ exported_animated_count }}개 · GIF {{ exported_gif_count }}개</p>{% for r in rules %}<span class="badge">{{ r }}</span>{% endfor %}</div>
<div class="card"><h2>최종 점수</h2><div class="grid">{% for k,v in final_scores.items() %}<div><div class="score">{{ v }}</div><b>{{ k }}</b></div>{% endfor %}</div></div>
<div class="card"><h2>잠금 사유</h2><ul>{% for item in lock_reasons %}<li>{{ item }}</li>{% endfor %}{% if not lock_reasons %}<li>현재 로컬 샘플 기준 제출 후보 ZIP 잠금 사유는 없습니다. 단, 공식 기준은 제출 직전 다시 확인해야 합니다.</li>{% endif %}</ul></div>
<div class="card"><h2>자동 보정 작업</h2><ul>{% for item in autofix_actions %}<li>{{ item }}</li>{% endfor %}</ul></div>
<div class="card"><h2>샘플 보정 로그</h2><table><thead><tr><th>구역</th><th>원본</th><th>최종명</th><th>작업</th><th>상태</th></tr></thead><tbody>{% for row in log_rows[:50] %}<tr><td>{{ row.area }}</td><td>{{ row.source_file }}</td><td>{{ row.final_name }}</td><td>{{ row.action }}</td><td>{{ row.status }}</td></tr>{% endfor %}</tbody></table></div>
<div class="card"><h2>보안/공식 확인 메모</h2><div class="mono">{{ safety_note }}</div></div>
</div></body></html>""", encoding="utf-8")
        if Environment is None:
            raise RuntimeError("Jinja2 is required for v72 report rendering")
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"]))
        out_path.write_text(env.get_template(template.name).render(**context), encoding="utf-8")

    def build_bundle(
        self,
        project_name: str,
        concept_text: str,
        selected_style: str,
        selected_rules: List[str],
        main_phrase: str,
        user_feedback: str,
        online_abstract_notes: str,
        out_dir: Path,
    ) -> V72SubmissionAutofixLockReport:
        safe_project = self._safe_name_v70(project_name or "v72_submission_autofix_lock")
        run_dir = out_dir / f"{safe_project}_{int(time.time())}"
        run_dir.mkdir(parents=True, exist_ok=True)

        qc = super().build_bundle(
            project_name=project_name,
            concept_text=concept_text,
            selected_style=selected_style,
            selected_rules=selected_rules,
            main_phrase=main_phrase,
            user_feedback=user_feedback,
            online_abstract_notes=online_abstract_notes,
            out_dir=run_dir / "base_v71_qc",
        )
        qc_dict = qc.to_dict()
        base_dir = Path(qc.output_dir)
        export_plan = self._read_csv_rows(Path(qc.normalized_export_plan_csv))
        final_root = run_dir / "final_export"
        static_dir = final_root / "static_32"
        animated_dir = final_root / "animated_24"
        log_rows: List[Dict[str, Any]] = []
        exported_static = 0
        exported_animated = 0
        exported_gif = 0

        for row in export_plan:
            source_name = row.get("source_file", "")
            recommended_name = row.get("recommended_name", "")
            area = row.get("package_area", "")
            src = self._find_source_file(base_dir, source_name)
            if not src:
                log_rows.append({"area": area, "source_file": source_name, "final_name": recommended_name, "action": "missing_source", "status": "FAIL", "details": "source not found"})
                continue
            target_dir = static_dir if area == "static_32" else animated_dir
            # Keep extension aligned with source if official plan gave png but source is gif.
            dst = target_dir / recommended_name
            if src.suffix.lower() == ".gif" and dst.suffix.lower() != ".gif":
                dst = dst.with_suffix(".gif")
            action, info = self._copy_autofix(src, dst)
            if area == "static_32":
                exported_static += 1
            elif area == "animated_24":
                exported_animated += 1
                if dst.suffix.lower() == ".gif":
                    exported_gif += 1
            status = "WARN" if info.get("warning") else ("FAIL" if info.get("error") and action.endswith("fallback") else "PASS")
            log_rows.append({
                "area": area,
                "source_file": source_name,
                "final_name": dst.name,
                "final_path": str(dst),
                "action": action,
                "status": status,
                "source_bytes": info.get("source_bytes", 0),
                "target_bytes": info.get("target_bytes", 0),
                "target_frames": info.get("target_frames", ""),
                "warning": info.get("warning", ""),
                "error": info.get("error", ""),
            })

        autofix_csv = run_dir / "v72_autofix_log.csv"
        autofix_json = run_dir / "v72_autofix_log.json"
        self._write_rows_v72(autofix_csv, autofix_json, log_rows)

        lock_reasons: List[str] = []
        if qc.fail_count > 0:
            lock_reasons.append(f"v71 QC FAIL {qc.fail_count}개가 남아 있어 최종 제출 패키지를 잠금 처리합니다.")
        if exported_static != self.STUDIO_DRAFT_LIMITS["static_count"]:
            lock_reasons.append(f"정지형 내보내기 수량이 {exported_static}개입니다. 기대값은 32개입니다.")
        if exported_animated != self.STUDIO_DRAFT_LIMITS["animated_count"]:
            lock_reasons.append(f"움직이는형 내보내기 수량이 {exported_animated}개입니다. 기대값은 24개입니다.")
        if exported_gif < self.STUDIO_DRAFT_LIMITS["required_gif_min"]:
            lock_reasons.append(f"GIF 후보가 {exported_gif}개입니다. 최소 3개 이상 필요합니다.")
        if any(r.get("status") == "FAIL" for r in log_rows):
            lock_reasons.append("자동 보정 로그에 FAIL 항목이 있습니다.")

        submission_lock_required = bool(lock_reasons)
        package_status = "LOCKED_REVIEW_ONLY" if submission_lock_required else "UNLOCKED_LOCAL_CANDIDATE"
        final_scores = {
            "final_package_readiness": 55 if submission_lock_required else 94,
            "autofix_success": max(0, 100 - sum(1 for r in log_rows if r.get("status") == "FAIL") * 15 - sum(1 for r in log_rows if r.get("status") == "WARN") * 3),
            "static_export_count": int(exported_static / max(1, self.STUDIO_DRAFT_LIMITS["static_count"]) * 100),
            "animated_export_count": int(exported_animated / max(1, self.STUDIO_DRAFT_LIMITS["animated_count"]) * 100),
            "gif_export_count": 100 if exported_gif >= 3 else 45,
            "official_recheck_needed": 100,
        }
        autofix_actions = [
            "원본 파일은 덮어쓰지 않고 final_export 폴더에 보정본을 생성했습니다.",
            "정지형 파일명은 static_01.png~static_32.png 구조로 정리했습니다.",
            "움직이는형 파일명은 animated_01~animated_24 구조로 정리했습니다.",
            "PNG는 RGBA 360x360, optimize=True로 재저장했습니다.",
            "GIF는 360x360과 프레임 수 제한 후보를 다시 점검했습니다.",
            "FAIL이 있으면 최종 제출 ZIP 대신 검토용 잠금 ZIP만 제공합니다.",
        ]
        safety_notes = [
            "이 패키지는 로컬 제출 후보이며 카카오 공식 승인이나 수익을 보장하지 않습니다.",
            "제출 직전 카카오 이모티콘 스튜디오의 최신 공식 규격을 다시 확인해야 합니다.",
            "온라인 자료는 추상 트렌드 신호로만 사용하며 기존 캐릭터/문구/애니메이션 복제는 금지합니다.",
            "API 키 원문은 결과물에 포함하지 않습니다.",
        ]
        final_manifest = {
            "version": self.VERSION,
            "project_name": project_name,
            "package_status": package_status,
            "submission_lock_required": submission_lock_required,
            "exported_counts": {"static": exported_static, "animated": exported_animated, "gif": exported_gif},
            "base_qc": {"pass": qc.pass_count, "warn": qc.warn_count, "fail": qc.fail_count, "overall": qc.overall_status},
            "final_scores": final_scores,
            "official_recheck_required": True,
            "copy_safety_required": True,
        }
        final_manifest_json = run_dir / "v72_final_submission_manifest.json"
        final_manifest_json.write_text(json.dumps(final_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        lock_manifest = {
            "version": self.VERSION,
            "package_status": package_status,
            "lock_reasons": lock_reasons,
            "unlock_conditions": [
                "v71 QC FAIL 0개",
                "정지형 32개 내보내기 완료",
                "움직이는형 24개 내보내기 완료",
                "GIF 후보 3개 이상 유지",
                "제출 직전 최신 공식 기준 재확인",
            ],
        }
        lock_manifest_json = run_dir / "v72_lock_manifest.json"
        lock_manifest_json.write_text(json.dumps(lock_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        db = run_dir / "v72_submission_autofix_learning.sqlite3"
        self._store_v72_learning(db, project_name, package_status, final_scores, {"static": exported_static, "animated": exported_animated, "gif": exported_gif})
        html_report = run_dir / "v72_submission_autofix_lock_report.html"
        self._render_v72_report(Path(__file__).resolve().parents[1] / "templates" / "v72_submission_autofix_lock", html_report, {
            "project_name": project_name,
            "package_status": package_status,
            "submission_lock_required": submission_lock_required,
            "rules": self.AUTOFIX_RULES,
            "exported_static_count": exported_static,
            "exported_animated_count": exported_animated,
            "exported_gif_count": exported_gif,
            "final_scores": final_scores,
            "lock_reasons": lock_reasons,
            "autofix_actions": autofix_actions,
            "log_rows": log_rows,
            "safety_note": "\n".join(safety_notes),
        })
        static_zip = run_dir / "v72_static_32_final_export.zip"
        animated_zip = run_dir / "v72_animated_24_final_export.zip"
        final_zip = run_dir / "v72_final_submission_candidate.zip"
        locked_zip = run_dir / "v72_locked_review_package.zip"
        self._zip_paths_v72(static_zip, [static_dir], root=final_root)
        self._zip_paths_v72(animated_zip, [animated_dir], root=final_root)
        if submission_lock_required:
            # Include only review materials, not an unlocked final export.
            self._zip_paths_v72(locked_zip, [html_report, autofix_csv, autofix_json, final_manifest_json, lock_manifest_json, Path(qc.pre_submission_qc_zip)], root=run_dir)
            self._zip_paths_v72(final_zip, [html_report, lock_manifest_json], root=run_dir)
            checksum_target = locked_zip
        else:
            self._zip_paths_v72(final_zip, [static_dir, animated_dir, static_zip, animated_zip, html_report, autofix_csv, autofix_json, final_manifest_json, lock_manifest_json, db, Path(qc.pre_submission_qc_zip)], root=run_dir)
            self._zip_paths_v72(locked_zip, [html_report, autofix_csv, autofix_json, final_manifest_json, lock_manifest_json], root=run_dir)
            checksum_target = final_zip
        checksum = self._sha256_v72(checksum_target)
        return V72SubmissionAutofixLockReport(
            project_name=project_name,
            output_dir=str(run_dir),
            base_qc_zip=qc.pre_submission_qc_zip,
            base_qc_report_html=qc.html_report_path,
            static_export_dir=str(static_dir),
            animated_export_dir=str(animated_dir),
            static_export_zip=str(static_zip),
            animated_export_zip=str(animated_zip),
            final_submission_zip=str(final_zip),
            locked_review_zip=str(locked_zip),
            autofix_log_csv=str(autofix_csv),
            autofix_log_json=str(autofix_json),
            final_manifest_json=str(final_manifest_json),
            lock_manifest_json=str(lock_manifest_json),
            html_report_path=str(html_report),
            learning_db=str(db),
            package_status=package_status,
            submission_lock_required=submission_lock_required,
            lock_reasons=lock_reasons,
            autofix_actions=autofix_actions,
            exported_static_count=exported_static,
            exported_animated_count=exported_animated,
            exported_gif_count=exported_gif,
            base_pass_count=qc.pass_count,
            base_warn_count=qc.warn_count,
            base_fail_count=qc.fail_count,
            final_scores=final_scores,
            safety_notes=safety_notes,
            checksum_sha256=checksum,
        )
