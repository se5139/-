from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    checks = []
    def add(name: str, ok: bool, detail: str = ''):
        checks.append({'name': name, 'ok': bool(ok), 'detail': detail})

    app = ROOT / 'app.py'
    constants = ROOT / 'modules' / 'constants.py'
    module = ROOT / 'modules' / 'kakao_motion_preview_improver.py'
    iss = ROOT / 'installer' / 'KakaoEmoticonSetup_v61.iss'
    build = ROOT / 'scripts' / 'build_inno_installer_v61.py'
    cleanup = ROOT / 'scripts' / 'cleanup_old_versions_v61.py'

    for p in [app, constants, module, iss, build, cleanup, ROOT / '0_BUILD_WINDOWS_INSTALLER_EXE.bat']:
        add(f'file exists: {p.relative_to(ROOT)}', p.exists())

    try:
        ast.parse(app.read_text(encoding='utf-8'))
        add('app.py AST parse', True)
    except Exception as exc:
        add('app.py AST parse', False, repr(exc))

    try:
        ast.parse(module.read_text(encoding='utf-8'))
        add('v61 module AST parse', True)
    except Exception as exc:
        add('v61 module AST parse', False, repr(exc))

    try:
        from modules.constants import APP_VERSION, APP_NAME
        add('APP_VERSION 61.0.0', APP_VERSION == '61.0.0', APP_VERSION)
        add('APP_NAME contains v61', 'v61' in APP_NAME, APP_NAME)
    except Exception as exc:
        add('constants import', False, repr(exc))

    try:
        from modules.kakao_motion_preview_improver import KakaoMotionPreviewImprover
        with tempfile.TemporaryDirectory() as td:
            report = KakaoMotionPreviewImprover().build_report(
                project_name='v61_smoke_test',
                concept_text='하찮은 직장인 답장형 캐릭터',
                style_preset='하찮은 공감형',
                selected_style_suggestions=[
                    '굵은 외곽선과 큰 실루엣',
                    '눈·입 대비 강화',
                    '정지형 identity를 움직이는형에도 고정',
                    '3개 GIF 모션 샘플을 바로 미리보기',
                    '24개 구성: 21 PNG + 3 GIF 계획 생성',
                ],
                online_notes='미니 리액션 짧은 공감 문구',
                out_dir=Path(td),
                main_phrase='넵',
            ).to_dict()
            required = ['static_preview_png', 'animated_preview_gif', 'contact_sheet_path', 'kakao_24_plan_csv', 'package_zip_path']
            for key in required:
                p = Path(report[key])
                add(f'smoke output exists: {key}', p.exists() and p.stat().st_size > 0, str(p))
            add('animated variants count >= 3', len(report.get('animated_variants', [])) >= 3)
            add('gif preview visible score 100', report.get('quality_scores', {}).get('gif_preview_visible') == 100)
            add('24 plan rows == 24', len(report.get('apply_payload', {}).get('expressions', [])) == 24)
            with zipfile.ZipFile(report['package_zip_path']) as zf:
                names = zf.namelist()
                add('package contains main GIF', any(n.endswith('.gif') for n in names), ','.join(names[:10]))
    except Exception as exc:
        add('v61 engine smoke test', False, repr(exc))

    app_text = app.read_text(encoding='utf-8') if app.exists() else ''
    add('PAGE_LABELS has 51st v61 menu', '51 카카오형 GIF 미리보기/트렌드 개선' in app_text)
    add('base64 GIF inline preview present', 'data:image/gif;base64' in app_text)
    add('selected_page_index == 50 block present', 'if selected_page_index == 50:' in app_text)
    add('OpenAI key raw leak absent', 'sk-proj-' not in ''.join(p.read_text(encoding='utf-8', errors='ignore') for p in [app, module, constants] if p.exists()))

    if iss.exists():
        iss_text = iss.read_text(encoding='utf-8', errors='ignore')
        add('installer v61 output filename', 'KakaoEmoticonSetup_v61' in iss_text)
        add('installer app dir v61', 'KakaoEmoticonProfitSystemV61' in iss_text)
        add('installer cleanup v61', '14_V61_CLEAN_OLD_VERSIONS_AND_EXTRACTED.bat' in iss_text)
        add('installer run v61 title', 'Run Kakao Emoticon Profit System v61' in iss_text)

    ok = all(c['ok'] for c in checks)
    report = {'ok': ok, 'checks': checks}
    out = ROOT / 'kakao_emoticon_profit_system_v61_verification_report.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
