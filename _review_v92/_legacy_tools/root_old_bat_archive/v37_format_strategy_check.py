from pathlib import Path
from modules.format_strategy import FormatStrategyEngine

out = Path('outputs/check_v37_format_strategy')
report = FormatStrategyEngine().build_report(
    out,
    project_name='보리와 쌀 v37 테스트',
    character_concept='까칠하지만 은근히 챙기는 보리와 온순하고 다정한 쌀 듀오. 직장인 짧은 답장 중심.',
    phrase_examples='넵, 확인했습니다, 뭐... 고맙다, 괜찮아유, 퇴근하고 싶어요, 좋아요, 죄송합니다',
    personality='보리=투덜/까칠, 쌀=다정/부드러움',
    motion_strength=2,
    expression_variety_score=76,
    chat_readability_score=84,
    quality_score=80,
    review_status='아직 제출 전',
    approval_count=0,
    rejection_count=0,
    sales_signal='아직 데이터 없음',
)
d = report.to_dict()
assert d['primary_format']['format_key'] in {'static_text', 'static'}
assert d['primary_format']['recommended_role'] == '1차 실제 제작 포맷'
assert len(d['format_scores']) >= 6
assert len(d['expansion_roadmap']) >= 3
assert len(d['data_requirements']) >= 5
for key in ['html_path', 'json_path', 'scores_csv_path', 'roadmap_csv_path', 'data_requirements_csv_path', 'notes_txt_path', 'zip_path']:
    p = Path(d['files'][key])
    assert p.exists(), f'missing {p}'
print('v37_format_strategy_check PASS')
