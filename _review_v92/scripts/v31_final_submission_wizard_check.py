import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.final_submission_wizard import FinalSubmissionWizard
from modules.prototype_generator.character_prototype_builder import PrototypeSpec

out = Path('outputs/v32_check')
spec = PrototypeSpec(
    name='보리와쌀_검사',
    materials=['보리','쌀'],
    body_shape='듀오형',
    palette=['#C99A4A','#F8F4E6','#2A2A2A','#FFFFFF'],
    face_style='공손한 미소',
    accessory='말풍선 꼬리',
    motion_hint='문구와 함께 인사',
    originality_note='직접 창작 기반 테스트 시안',
)
expressions = [
    {'phrase':'안녕하세요','emotion':'인사','recommended_motion':'손흔들기'},
    {'phrase':'확인했습니다','emotion':'확인','recommended_motion':'체크 도장 + 문구 쿵 등장'},
    {'phrase':'감사합니다','emotion':'감사','recommended_motion':'꾸벅 숙이기'},
    {'phrase':'죄송합니다','emotion':'사과','recommended_motion':'작아짐 + 땀방울'},
] * 8
lock = {'unlock_status':'최종 ZIP 생성 가능','passed_required':7,'total_required':7,'risk_score':0,'blockers':[]}
report = FinalSubmissionWizard().build(
    out,
    project_name='v32_check_project',
    format_key='static_text',
    target_count=32,
    spec=spec,
    expressions=expressions,
    lock_report=lock,
    linked_reports={},
    allow_draft_when_locked=False,
)
assert report.gate_status == '통과'
assert report.final_zip_status == '생성 가능'
assert report.final_zip_path and Path(report.final_zip_path).exists()
assert report.checksum_sha256 and len(report.checksum_sha256) == 64
assert Path(report.html_path).exists()
assert Path(report.json_path).exists()
assert Path(report.checklist_csv_path).exists()
print('v32 final submission wizard check PASS')
