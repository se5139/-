
from __future__ import annotations

import ast
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.static_to_animated_apply import StaticToAnimatedApplyEngine


def main() -> int:
    out = ROOT / 'outputs' / 'v52_check'
    engine = StaticToAnimatedApplyEngine()
    report = engine.build_report(
        project_name='v52_check',
        concept_text='보리와 쌀, 직장인 답장형 정지형 캐릭터를 기반으로 움직이는형 생성',
        selected_suggestion_ids=['bold_outline','face_contrast','animated_identity_lock','text_motion_sync','series_ready'],
        phrase='넵',
        out_dir=out,
    ).to_dict()
    required = ['static_png_path','animated_gif_path','json_path','html_path','zip_path']
    missing = [k for k in required if not Path(report[k]).exists()]
    if missing:
        print('[FAIL] missing outputs:', missing)
        return 1
    if not report.get('apply_payload', {}).get('prototype_results'):
        print('[FAIL] apply payload missing prototype_results')
        return 1
    if len(report.get('expression_table', [])) < 24:
        print('[FAIL] expression table too short')
        return 1
    with zipfile.ZipFile(report['zip_path'], 'r') as zf:
        names = set(zf.namelist())
    expected = {'v52_static_regenerated_from_selected_suggestions.png','v52_animated_from_static_identity.gif','v52_motion_plan_identity_locked.json'}
    if not expected.issubset(names):
        print('[FAIL] package missing expected files:', expected - names)
        return 1
    app_text = (ROOT / 'app.py').read_text(encoding='utf-8')
    ast.parse(app_text)
    markers = [
        '49 정지형 기반 움직이는형/제안 반영',
        'v52_static_to_animated_report',
        'StaticToAnimatedApplyEngine',
        '선택 제안 반영해서 정지형 재생성 + 움직이는형 생성',
        '생성 결과를 현재 제작 흐름에 적용',
    ]
    miss = [m for m in markers if m not in app_text]
    if miss:
        print('[FAIL] app markers missing:', miss)
        return 1
    print(json.dumps({
        'status': 'PASS',
        'static_png': report['static_png_path'],
        'animated_gif': report['animated_gif_path'],
        'zip_path': report['zip_path'],
        'expression_count': len(report.get('expression_table', [])),
        'selected_suggestions': len(report.get('selected_suggestions', [])),
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
