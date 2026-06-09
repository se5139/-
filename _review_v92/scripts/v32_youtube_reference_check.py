from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.youtube_reference import YoutubeReferenceAnalyzer

out = Path('outputs/v32_check')
out.mkdir(parents=True, exist_ok=True)
iframe = '<iframe width="560" height="315" src="https://www.youtube.com/embed/J7YLGUtzTHc?si=DOyzEayXVzL6BkYp" title="YouTube video player"></iframe>'
transcript = '''
1
00:00:01,000 --> 00:00:03,000
AI로 만든 이모티콘은 승인 거부될 수 있습니다.

00:00:04,000 --> 00:00:08,000
직접 스케치를 남기고 레이어와 수정 이력을 기록하세요.

00:00:09,000 --> 00:00:13,000
유튜브 댓글과 조회수, 키워드를 분석해서 이모티콘 문구와 캐릭터 방향을 정합니다.

00:00:14,000 --> 00:00:18,000
AI 티 안 나게 숨겨서 제출하라는 말은 위험합니다.
'''
report = YoutubeReferenceAnalyzer().analyze(
    out,
    url_or_iframe=iframe,
    transcript_text=transcript,
    uploaded_transcripts=[('note.txt', '문구 가독성과 채팅창 미리보기 기능을 강화하면 좋습니다.')],
    manual_notes='이 영상은 이모티콘 수익화 참고자료이며 안전한 기능만 추출해야 합니다.',
)
assert report.video_id == 'J7YLGUtzTHc'
assert len(report.risky_claims) >= 1
assert any('직접 창작' in x.get('feature','') for x in report.safe_feature_ideas)
for key, fp in report.files.items():
    assert Path(fp).exists(), (key, fp)
print('v32_youtube_reference_check PASS', report.video_id, len(report.risky_claims), len(report.safe_feature_ideas))
