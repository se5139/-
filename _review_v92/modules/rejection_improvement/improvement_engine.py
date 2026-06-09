from __future__ import annotations

import csv
import hashlib
import html
import json
import shutil
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


@dataclass
class RejectionImprovementReport:
    project_name: str
    created_at: str
    reason_text: str
    detected_categories: List[str]
    severity_score: int
    verdict: str
    action_plan: List[Dict[str, Any]]
    risky_items: List[Dict[str, Any]]
    revised_expressions: List[Dict[str, Any]]
    checklist: List[Dict[str, Any]]
    html_path: str
    json_path: str
    csv_path: str
    revised_csv_path: str
    zip_path: str
    checksum_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RejectionImprovementEngine:
    """카카오 이모티콘 심사/품질 문제 사유를 입력하면 개선 액션을 만드는 규칙형 엔진.

    법적/심사 통과 보장이 아니라, 사용자가 직접 창작한 이모티콘 세트를 보완하기 위한
    제작 검토 도구로 사용한다.
    """

    CATEGORY_RULES: Dict[str, Dict[str, Any]] = {
        "character_weak": {
            "label": "캐릭터성/매력 약함",
            "keywords": ["캐릭터", "매력", "개성", "시그니처", "세계관", "약함", "평범"],
            "severity": 20,
            "actions": [
                "대표 말버릇 5~8개를 세트에 추가한다.",
                "캐릭터 고유 표정 3개를 강화한다. 예: 보리=투덜/옆눈, 쌀=부드러운 미소.",
                "일반 문구 6개 이상을 캐릭터 말투가 드러나는 문구로 교체한다.",
                "캐릭터 관계성/세계관 카드를 갱신한다.",
            ],
        },
        "conversation_low": {
            "label": "대화 활용성 낮음",
            "keywords": ["대화", "사용성", "활용", "쓸 곳", "쓸데", "실사용", "활용성", "카톡"],
            "severity": 18,
            "actions": [
                "실사용 답장형 표현 비율을 30% 이상으로 올린다.",
                "넵/확인/감사/죄송/부탁/수고/잘자/축하 계열을 보강한다.",
                "너무 상황이 좁은 문구를 일상 답장형 문구로 교체한다.",
                "문구 길이를 줄이고 1초 안에 읽히게 만든다.",
            ],
        },
        "readability_low": {
            "label": "문구 가독성 낮음",
            "keywords": ["가독", "글자", "문구", "작", "잘림", "읽", "대비", "말풍선"],
            "severity": 18,
            "actions": [
                "글자 크기를 키우고 문구를 8~12자 내외로 줄인다.",
                "문구 위치를 캐릭터와 겹치지 않도록 상하좌우 재배치한다.",
                "흰/어두운 배경 대비 검사를 다시 실행한다.",
                "말풍선 여백과 외곽선을 보강한다.",
            ],
        },
        "emotion_weak": {
            "label": "감정/표정 전달 약함",
            "keywords": ["감정", "표정", "전달", "눈", "입", "리액션", "약", "밋밋"],
            "severity": 16,
            "actions": [
                "표정 강도를 1단계 올린다.",
                "눈/입/눈썹/효과를 감정별 하위표현으로 재배정한다.",
                "슬픔·감사·분노·당황 등 핵심 감정은 하위표현을 2개 이상 섞는다.",
                "작은 화면에서도 보이도록 눈/입 비율을 키운다.",
            ],
        },
        "motion_awkward": {
            "label": "움직임/모션 어색함",
            "keywords": ["움직", "모션", "GIF", "프레임", "타이밍", "어색", "반복", "뚝뚝", "속도"],
            "severity": 16,
            "actions": [
                "프레임 시작/중간/강조/마지막 자세를 5~6단계로 재정리한다.",
                "문구 등장 타이밍을 캐릭터 동작 이후로 맞춘다.",
                "반복 재생 연결 프레임을 추가한다.",
                "모션 강도는 포맷과 문구 길이에 맞춰 1단계 낮추거나 높인다.",
            ],
        },
        "repetition_high": {
            "label": "세트 반복감 높음",
            "keywords": ["반복", "비슷", "중복", "같은", "단조", "다 똑같"],
            "severity": 16,
            "actions": [
                "같은 감정 표현은 하위표현으로 분산한다. 예: 슬픔=눈물 한 방울/훌쩍임/오열.",
                "같은 동작은 제스처 변형으로 분산한다. 예: 따봉=한손/양손/큰손/통통.",
                "전체 24/32개를 감정·답장·관계·시그니처 비율로 재분배한다.",
                "문구 유사도가 높은 표현 6개 이상을 교체한다.",
            ],
        },
        "similarity_risk": {
            "label": "저작권/상표/유사성 위험",
            "keywords": ["유사", "저작권", "상표", "모방", "비슷", "브랜드", "춘식", "라이언", "산리오", "포켓몬"],
            "severity": 25,
            "actions": [
                "캐릭터명·색상·실루엣·말투를 동시에 변경한다.",
                "유명 캐릭터/브랜드 연상 키워드를 제거한다.",
                "저작권 방어 센터에서 출처·스케치·레이어 기록을 갱신한다.",
                "직접 창작 원본을 기준으로 새 콘셉트 방향을 다시 만든다.",
            ],
        },
        "ai_policy_risk": {
            "label": "AI 정책/직접 창작 증거 부족",
            "keywords": ["AI", "생성형", "인공지능", "ai", "midjourney", "stable", "티", "모르게", "은폐"],
            "severity": 25,
            "actions": [
                "제출용 완성 이미지에 생성형 AI 사용이 있으면 제출을 중단하고 직접 창작 원본으로 재작업한다.",
                "직접 그린 스케치/자유 드로잉/레이어 원본/수정 이력을 보강한다.",
                "AI는 시장 분석·문구 분류·품질검사 보조 범위로만 기록한다.",
                "직접 창작 기준 리포트와 SHA-256 증거 기록을 다시 생성한다.",
            ],
        },
        "format_issue": {
            "label": "규격/파일/포맷 문제",
            "keywords": ["규격", "용량", "크기", "파일", "포맷", "투명", "배경", "png", "gif", "수량"],
            "severity": 15,
            "actions": [
                "제출 패키지의 수량·크기·확장자·용량·투명 배경을 다시 검사한다.",
                "포맷별 검사 기준으로 최종 품질검사를 재실행한다.",
                "파일명 순번과 누락 파일을 확인한다.",
                "움직이는 문구형은 GIF 프레임 수와 용량 위험을 줄인다.",
            ],
        },
    }

    DEFAULT_EXPRESSIONS: List[str] = [
        "안녕하세요", "넵", "확인했습니다", "감사합니다", "죄송합니다", "부탁드려요", "좋아요", "최고예요",
        "축하해요", "파이팅", "잠시만요", "괜찮아요", "수고하셨습니다", "퇴근하고 싶습니다", "피곤합니다", "잘자요",
        "울컥", "당황했습니다", "부들부들", "기다릴게요", "완료했습니다", "어렵습니다", "마음만 받겠습니다", "살려주세요",
        "보고 싶어요", "조심히 와요", "오늘도 버팁니다", "구겨져도 갑니다", "칭찬받으면 싹납니다", "영혼은 퇴근했습니다", "작아지는 중", "조용히 파이팅",
    ]

    def classify(self, reason_text: str) -> List[str]:
        text = (reason_text or "").lower()
        detected = []
        for key, rule in self.CATEGORY_RULES.items():
            if any(str(k).lower() in text for k in rule["keywords"]):
                detected.append(key)
        if not detected:
            detected = ["character_weak", "conversation_low"]
        return detected

    def severity(self, categories: List[str]) -> int:
        score = sum(int(self.CATEGORY_RULES[c]["severity"]) for c in categories if c in self.CATEGORY_RULES)
        return min(100, max(10, score))

    def verdict(self, severity: int) -> str:
        if severity >= 70:
            return "재제출 전 대폭 수정 필요"
        if severity >= 40:
            return "보완 후 재검토 권장"
        return "부분 보완 후 재확인"

    def build_action_plan(self, categories: List[str]) -> List[Dict[str, Any]]:
        plan = []
        priority = 1
        for cat in categories:
            rule = self.CATEGORY_RULES.get(cat)
            if not rule:
                continue
            for action in rule["actions"]:
                plan.append({
                    "priority": priority,
                    "category": cat,
                    "category_label": rule["label"],
                    "action": action,
                    "target_area": self._target_area(cat),
                })
                priority += 1
        return plan

    def _target_area(self, category: str) -> str:
        return {
            "character_weak": "캐릭터 세계관/말투/표정",
            "conversation_low": "표현 은행/문구 구성",
            "readability_low": "문구 크기/위치/대비",
            "emotion_weak": "표정/눈/입/효과",
            "motion_awkward": "GIF 타임라인/문구 움직임",
            "repetition_high": "24·32개 세트 구성",
            "similarity_risk": "이름/실루엣/색상/저작권 방어",
            "ai_policy_risk": "직접 창작 증거/AI 사용 범위",
            "format_issue": "제출 패키지/품질검사",
        }.get(category, "전체")

    def analyze_items(self, expressions: Iterable[Dict[str, Any]] | None, categories: List[str]) -> List[Dict[str, Any]]:
        rows = list(expressions or [])
        if not rows:
            rows = [{"number": i + 1, "phrase": p, "emotion": self._guess_emotion(p)} for i, p in enumerate(self.DEFAULT_EXPRESSIONS)]
        risky = []
        for i, row in enumerate(rows, start=1):
            phrase = str(row.get("phrase") or row.get("text") or row.get("문구") or "").strip()
            if not phrase:
                phrase = f"표현 {i}"
            issues = []
            if len(phrase) > 14:
                issues.append("문구 길이 조정")
            if any(k in phrase for k in ["춘식이", "라이언", "산리오", "포켓몬", "비슷"]):
                issues.append("유사성 위험 문구")
            if categories and "repetition_high" in categories and phrase in [r.get("phrase") for r in risky]:
                issues.append("중복 문구")
            if "conversation_low" in categories and self._guess_emotion(phrase) not in ["확인", "감사", "사과", "응원", "일상"]:
                issues.append("실사용성 재검토")
            if "emotion_weak" in categories and self._guess_emotion(phrase) in ["슬픔", "분노", "당황", "감사", "사과"]:
                issues.append("표정 강도 보강")
            if issues:
                risky.append({
                    "number": row.get("number", i),
                    "phrase": phrase,
                    "emotion": row.get("emotion") or self._guess_emotion(phrase),
                    "issues": ", ".join(issues),
                    "recommended_fix": self._fix_for_issue(issues[0]),
                })
        return risky[:40]

    def build_revised_expressions(self, categories: List[str], base_expressions: Iterable[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
        # 실사용 답장형 + 캐릭터성 + 감정 하위표현을 섞어 32개 개선 세트를 만든다.
        phrase_pool: List[Tuple[str, str, str]] = [
            ("인사", "안녕하세요", "부드러운 미소 + 작은 손흔들기"),
            ("확인", "확인했습니다", "집중 눈 + 체크 도장"),
            ("확인", "넵", "작게 끄덕임"),
            ("감사", "감사합니다", "고마운 미소 + 하트"),
            ("사과", "죄송합니다", "처진 눈 + 땀 + 꾸벅"),
            ("부탁", "부탁드려요", "조심스러운 눈 + 두 손 모음"),
            ("응원", "파이팅", "양손 따봉 + 반짝임"),
            ("축하", "축하해요", "활짝 웃음 + 반짝임"),
            ("일상", "수고하셨습니다", "고개 꾸벅"),
            ("피곤", "잠시만요", "반눈 + 아래로 처짐"),
            ("피곤", "퇴근하고 싶습니다", "영혼 빠진 표정"),
            ("거절", "어렵습니다", "미안한 눈 + 작은 손사래"),
            ("대기", "기다릴게요", "차분한 미소"),
            ("관계", "괜찮아요", "따뜻한 눈 + 작은 하트"),
            ("수면", "잘자요", "감은 눈 + Zzz"),
            ("시그니처", "구겨져도 갑니다", "캐릭터 고유 포즈"),
            ("시그니처", "칭찬받으면 싹납니다", "시그니처 효과"),
            ("시그니처", "영혼은 퇴근했습니다", "영혼 빠짐 모션"),
            ("슬픔", "눈물 납니다", "눈물 한 방울"),
            ("슬픔", "울컥", "눈물 고임"),
            ("당황", "당황했습니다", "큰 눈 + 물음표"),
            ("분노", "부들부들", "찡그림 + 떨림"),
            ("기쁨", "좋아요", "양손 따봉"),
            ("기쁨", "최고예요", "큰손 따봉 + 반짝임"),
            ("완료", "완료했습니다", "도장처럼 문구 등장"),
            ("민망", "마음만 받겠습니다", "옆눈 + 어색한 미소"),
            ("피곤", "살려주세요", "녹아내림"),
            ("관계", "보고 싶어요", "수줍은 눈 + 하트"),
            ("안전", "조심히 와요", "걱정 눈 + 작은 손흔들기"),
            ("일상", "오늘도 버팁니다", "작게 버티는 포즈"),
            ("시그니처", "작아지는 중", "몸이 작아짐"),
            ("응원", "조용히 파이팅", "무표정 작은 따봉"),
        ]
        # 카테고리별 보정
        if "conversation_low" in categories:
            phrase_pool[:0] = [("확인", "봤습니다", "작은 끄덕임"), ("감사", "고맙습니다", "부드러운 미소"), ("사과", "미안해요", "작게 꾸벅")]
        if "character_weak" in categories:
            phrase_pool.append(("시그니처", "나답게 해볼게요", "대표 포즈"))
            phrase_pool.append(("시그니처", "겉으론 그래도 챙깁니다", "캐릭터성 강조"))
        if "repetition_high" in categories:
            phrase_pool.append(("슬픔", "안 운다...", "참는 눈물"))
            phrase_pool.append(("따봉", "뭐... 괜찮네", "무표정 한손 따봉"))
        revised = []
        seen = set()
        for idx, (emotion, phrase, face_motion) in enumerate(phrase_pool, start=1):
            if phrase in seen:
                continue
            seen.add(phrase)
            revised.append({
                "number": len(revised) + 1,
                "emotion": emotion,
                "phrase": phrase,
                "face_motion_plan": face_motion,
                "revision_reason": "반려/문제 사유에 맞춰 실사용성·캐릭터성·가독성을 보강한 후보",
                "recommended_format": "문구 결합형 정지" if emotion in ["확인", "감사", "사과", "일상"] else "움직이는 문구형 후보",
            })
            if len(revised) >= 32:
                break
        return revised

    def checklist(self, categories: List[str]) -> List[Dict[str, Any]]:
        base = [
            ("직접 창작 원본/스케치/자유 드로잉 기록 확인", "필수"),
            ("저작권/상표권 방어 리포트 재생성", "필수" if "similarity_risk" in categories else "권장"),
            ("24개/32개 세트 감정 균형 재검사", "필수"),
            ("채팅창 작은 화면/어두운 배경 미리보기 재검사", "필수"),
            ("최종 품질검사와 데이터 백업 실행", "필수"),
            ("AI 완성본 제출 또는 은폐 목적이 아닌지 확인", "필수" if "ai_policy_risk" in categories else "권장"),
        ]
        return [{"item": item, "level": level, "checked": False} for item, level in base]

    def build_report(
        self,
        output_dir: Path | str,
        project_name: str,
        reason_text: str,
        expressions: Iterable[Dict[str, Any]] | None = None,
    ) -> RejectionImprovementReport:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        categories = self.classify(reason_text)
        severity = self.severity(categories)
        verdict = self.verdict(severity)
        action_plan = self.build_action_plan(categories)
        risky_items = self.analyze_items(expressions, categories)
        revised = self.build_revised_expressions(categories, expressions)
        checklist = self.checklist(categories)

        data = {
            "project_name": project_name,
            "created_at": created_at,
            "reason_text": reason_text,
            "detected_categories": categories,
            "detected_category_labels": [self.CATEGORY_RULES[c]["label"] for c in categories],
            "severity_score": severity,
            "verdict": verdict,
            "action_plan": action_plan,
            "risky_items": risky_items,
            "revised_expressions": revised,
            "checklist": checklist,
            "notice": "이 리포트는 심사 통과 보장이 아니라 재제작/재검토 보조 자료입니다.",
        }

        json_path = output_dir / "rejection_improvement_report.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        csv_path = output_dir / "improvement_action_plan.csv"
        self._write_csv(csv_path, action_plan, ["priority", "category_label", "target_area", "action"])
        revised_csv_path = output_dir / "revised_expression_set.csv"
        self._write_csv(revised_csv_path, revised, ["number", "emotion", "phrase", "face_motion_plan", "recommended_format", "revision_reason"])
        html_path = output_dir / "rejection_improvement_report.html"
        html_path.write_text(self._build_html(data), encoding="utf-8")

        zip_path = output_dir / f"{project_name}_v29_rejection_improvement_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in [json_path, csv_path, revised_csv_path, html_path]:
                if fp.exists():
                    zf.write(fp, fp.name)
        checksum = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        (output_dir / f"{zip_path.name}.sha256.txt").write_text(checksum, encoding="utf-8")

        return RejectionImprovementReport(
            project_name=project_name,
            created_at=created_at,
            reason_text=reason_text,
            detected_categories=categories,
            severity_score=severity,
            verdict=verdict,
            action_plan=action_plan,
            risky_items=risky_items,
            revised_expressions=revised,
            checklist=checklist,
            html_path=str(html_path),
            json_path=str(json_path),
            csv_path=str(csv_path),
            revised_csv_path=str(revised_csv_path),
            zip_path=str(zip_path),
            checksum_sha256=checksum,
        )

    def _guess_emotion(self, phrase: str) -> str:
        checks = [
            ("감사", ["감사", "고마", "땡큐"]),
            ("사과", ["죄송", "미안", "사과"]),
            ("확인", ["확인", "넵", "봤", "완료", "접수"]),
            ("응원", ["파이팅", "응원"]),
            ("축하", ["축하", "대박", "최고"]),
            ("피곤", ["피곤", "퇴근", "살려", "기절", "졸려"]),
            ("슬픔", ["울", "눈물", "슬프"]),
            ("분노", ["화", "부들", "건드리지"]),
            ("당황", ["당황", "어", "뭐야"]),
        ]
        for label, keys in checks:
            if any(k in phrase for k in keys):
                return label
        return "일상"

    def _fix_for_issue(self, issue: str) -> str:
        if "문구" in issue:
            return "짧은 답장형 문구로 교체하고 글자 크기/위치를 재검사"
        if "유사" in issue:
            return "명칭·색상·실루엣·말투를 동시에 변경"
        if "표정" in issue:
            return "눈/입/효과 강도를 한 단계 올리고 감정 하위표현 적용"
        if "중복" in issue:
            return "같은 의미의 표현을 캐릭터 시그니처 문구로 교체"
        return "표현 후보와 포맷 적합도 재검토"

    def _write_csv(self, path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _build_html(self, data: Dict[str, Any]) -> str:
        def table(rows: List[Dict[str, Any]], fields: List[str]) -> str:
            if not rows:
                return "<p>해당 없음</p>"
            th = "".join(f"<th>{html.escape(f)}</th>" for f in fields)
            trs = []
            for row in rows:
                tds = "".join(f"<td>{html.escape(str(row.get(f, '')))}</td>" for f in fields)
                trs.append(f"<tr>{tds}</tr>")
            return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"
        labels = [self.CATEGORY_RULES[c]["label"] for c in data.get("detected_categories", [])]
        return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>v29 반려 사유 개선 리포트</title>
<style>
body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:28px;line-height:1.55;color:#222}}
.card{{border:1px solid #ddd;border-radius:12px;padding:18px;margin:16px 0;background:#fafafa}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border:1px solid #ddd;padding:8px;vertical-align:top}}th{{background:#f0f3f8}}
.badge{{display:inline-block;background:#1f6feb;color:#fff;border-radius:999px;padding:4px 10px;margin:3px}}
.warn{{background:#fff4d6;border-left:5px solid #f0b400;padding:12px}}
</style></head><body>
<h1>v29 반려 사유 기반 자동 개선 리포트</h1>
<div class="card"><b>프로젝트:</b> {html.escape(data['project_name'])}<br><b>생성 시간:</b> {html.escape(data['created_at'])}<br><b>판정:</b> {html.escape(data['verdict'])}<br><b>위험/보완 점수:</b> {data['severity_score']} / 100</div>
<div class="card"><h2>입력한 사유</h2><p>{html.escape(data.get('reason_text',''))}</p></div>
<div class="card"><h2>자동 분류</h2>{''.join(f'<span class="badge">{html.escape(x)}</span>' for x in labels)}</div>
<div class="card"><h2>우선 개선 액션</h2>{table(data.get('action_plan', []), ['priority','category_label','target_area','action'])}</div>
<div class="card"><h2>수정 필요 가능 표현</h2>{table(data.get('risky_items', []), ['number','phrase','emotion','issues','recommended_fix'])}</div>
<div class="card"><h2>재구성 표현 세트 후보</h2>{table(data.get('revised_expressions', []), ['number','emotion','phrase','face_motion_plan','recommended_format'])}</div>
<div class="card"><h2>재제출 전 체크리스트</h2>{table(data.get('checklist', []), ['level','item','checked'])}</div>
<p class="warn">이 리포트는 심사 통과 보장이 아니라, 사용자가 직접 창작한 이모티콘 세트를 보완하기 위한 검토 자료입니다.</p>
</body></html>"""
