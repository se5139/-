from pathlib import Path
import zipfile

from modules.taste_experience import TasteExperienceMotionEngine

out = Path('outputs/v35_check')
report = TasteExperienceMotionEngine().build_report(
    out,
    favorites='낙서형 캐릭터, 직장인 공감, 소박한 음식, 충청권 말투',
    hobbies='수영, 산책, 유튜브 쇼츠 보기',
    life_experience='직장인이라 짧은 답장과 피곤한 리액션을 자주 쓴다. 충청권 생활 말투도 조금 넣고 싶다.',
    daily_observation='점심시간에 다들 지친 표정, 퇴근 직전 영혼 없는 답장, 귀찮지만 예의는 지키는 상황',
    persona='피곤하지만 예의 바른 작은 감자 캐릭터',
    target_count=32,
    motion_difficulty='4컷 기본 모션',
    include_platform_reuse=True,
)
assert len(report.concept_candidates) >= 4
assert len(report.phrase_plan) == 32
assert len(report.motion_template_plan) >= 3
assert len(report.platform_reuse_plan) >= 5
assert len(report.content_calendar) == 4
files = report.files
for key in ['html_path','json_path','concept_csv_path','phrase_csv_path','motion_csv_path','platform_csv_path','calendar_csv_path','notes_txt_path','zip_path']:
    p = Path(files[key])
    assert p.exists() and p.stat().st_size > 0, (key, p)
with zipfile.ZipFile(files['zip_path']) as zf:
    bad = zf.testzip()
    assert bad is None, bad
print('v35 taste/experience motion engine check PASS')
