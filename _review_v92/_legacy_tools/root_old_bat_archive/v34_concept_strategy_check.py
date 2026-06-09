from pathlib import Path
import json
from modules.concept_strategy import ConceptStrategyEngine

out = Path('outputs/v34_check')
report = ConceptStrategyEngine().build_report(
    out,
    concept_text='게으르고 나른한 뚱냥이 캐릭터. 누워서 나른하다냥이라고 말한다. 멘트가 크고 짧게 들어간다.',
    material='',
    target_user='일상 카톡 답장/리액션',
    personality='',
    tone='',
    format_focus='auto',
    target_count=32,
    include_mini_strategy=True,
)
data = report.to_dict()
assert data['specificity_score'] >= 60, data['specificity_score']
assert len(data['title_candidates']) >= 5
assert len(data['phrase_plan']) == 32
assert len(data['motion_templates']) >= 8
assert len(data['format_recommendation']) >= 4
for key in ['html_path','json_path','phrase_csv_path','title_csv_path','motion_csv_path','zip_path']:
    p = Path(data['files'][key])
    assert p.exists(), p
print('v34_concept_strategy_check PASS')
