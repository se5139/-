from pathlib import Path
from modules.dialect_expression import DialectLifeExpressionEngine

out = Path('outputs/check_v33')
report = DialectLifeExpressionEngine().build_report(
    out,
    region='충청권',
    material='청주 감자',
    personality='느긋하지만 성실하고 예의 바름',
    tone='부드러운 생활형 사투리, 짧고 부담 없는 답장',
    context='직장인/일상 답장용',
    personal_dialect_text='그려유, 괜찮아유, 천천히 해유, 고맙슈, 어쩐대유',
    target_count=32,
    format_key='static_text',
)
assert report.region == '충청권'
assert len(report.phrase_set) == 32
assert len(report.title_candidates) >= 5
assert report.files and all(Path(p).exists() for p in report.files.values())
print('v33 dialect engine PASS')
