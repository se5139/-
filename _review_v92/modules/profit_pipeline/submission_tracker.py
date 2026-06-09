from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import csv
import json


@dataclass
class SubmissionRecord:
    created_at: str
    character_name: str
    format_label: str
    status: str
    submitted_at: str
    result_at: str
    rejection_reason: str
    revision_note: str
    sales_note: str
    next_action: str

    def to_dict(self) -> dict:
        return asdict(self)


class SubmissionTracker:
    """심사/반려/출시 결과를 누적 기록하는 로컬 JSON/CSV 관리기."""

    def __init__(self, store_path: str | Path) -> None:
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict]:
        if not self.store_path.exists():
            return []
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def add(self, record: SubmissionRecord) -> list[dict]:
        records = self.load()
        records.append(record.to_dict())
        self.store_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return records

    def make_record(
        self,
        character_name: str,
        format_label: str,
        status: str,
        submitted_at: str = "",
        result_at: str = "",
        rejection_reason: str = "",
        revision_note: str = "",
        sales_note: str = "",
    ) -> SubmissionRecord:
        next_action = self.recommend_next_action(status, rejection_reason, sales_note)
        return SubmissionRecord(
            created_at=datetime.now().isoformat(timespec="seconds"),
            character_name=character_name.strip() or "미지정 캐릭터",
            format_label=format_label.strip() or "미지정 포맷",
            status=status,
            submitted_at=submitted_at,
            result_at=result_at,
            rejection_reason=rejection_reason.strip(),
            revision_note=revision_note.strip(),
            sales_note=sales_note.strip(),
            next_action=next_action,
        )

    def recommend_next_action(self, status: str, rejection_reason: str, sales_note: str) -> str:
        text = f"{status} {rejection_reason} {sales_note}"
        if "승인" in status or "출시" in status:
            return "같은 캐릭터의 2차 포맷/시리즈 후보를 준비"
        if "반려" in status:
            if any(k in text for k in ["규격", "용량", "크기", "파일", "투명"]):
                return "제출 패키지 검사 기준으로 크기/용량/파일명/투명 배경 재검사"
            if any(k in text for k in ["유사", "저작", "상표", "AI", "모방"]):
                return "외형/명칭/문구/AI 사용 여부를 변경하고 저작권 방어 리포트 재생성"
            return "문구 사용성, 감정 전달력, 캐릭터 세계관을 강화한 수정판 제작"
        if "제출" in status:
            return "심사 결과가 나오면 사유와 날짜를 기록"
        return "표현 은행과 포맷 추천 결과를 기준으로 첫 제출 패키지 생성"

    def stats(self, records: list[dict] | None = None) -> dict:
        records = records if records is not None else self.load()
        total = len(records)
        status_counts: dict[str, int] = {}
        for rec in records:
            status = str(rec.get("status", "미지정"))
            status_counts[status] = status_counts.get(status, 0) + 1
        return {
            "총 기록": total,
            "상태별 기록": status_counts,
            "승인/출시 기록": sum(v for k, v in status_counts.items() if "승인" in k or "출시" in k),
            "반려 기록": sum(v for k, v in status_counts.items() if "반려" in k),
        }

    def export_csv(self, csv_path: str | Path, records: list[dict] | None = None) -> Path:
        records = records if records is not None else self.load()
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "created_at", "character_name", "format_label", "status", "submitted_at",
            "result_at", "rejection_reason", "revision_note", "sales_note", "next_action"
        ]
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for rec in records:
                writer.writerow({field: rec.get(field, "") for field in fields})
        return csv_path
