from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class HtmlReporter:
    def write_report(self, report_data: dict[str, Any], output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        title = report_data.get("title", "이모티콘 분석 리포트")
        sections = []
        for key, value in report_data.items():
            if key == "title":
                continue
            sections.append(self._section(key, value))
        body = "\n".join(sections)
        html_doc = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<title>{html.escape(title)}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', 'Apple SD Gothic Neo', Arial, sans-serif; margin: 32px; line-height: 1.55; color: #222; }}
h1 {{ font-size: 28px; }}
h2 {{ margin-top: 28px; border-bottom: 2px solid #eee; padding-bottom: 6px; }}
pre {{ background: #f7f7f8; padding: 16px; border-radius: 10px; overflow-x: auto; white-space: pre-wrap; }}
.badge {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #eee; margin-right: 6px; }}
.footer {{ margin-top: 40px; color: #666; font-size: 13px; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p><span class="badge">생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span><span class="badge">로컬 Python 리포트</span></p>
{body}
<div class="footer">이 리포트는 법적 판정서가 아니라 제작 전 위험을 낮추기 위한 검토 자료입니다. 제출 전 카카오 이모티콘 스튜디오의 최신 공식 가이드를 다시 확인하세요.</div>
</body>
</html>"""
        output_path.write_text(html_doc, encoding="utf-8")
        return output_path

    def _section(self, key: str, value: Any) -> str:
        pretty_key = html.escape(str(key))
        if isinstance(value, str):
            content = f"<p>{html.escape(value)}</p>"
        else:
            content = f"<pre>{html.escape(json.dumps(value, ensure_ascii=False, indent=2))}</pre>"
        return f"<h2>{pretty_key}</h2>\n{content}"
