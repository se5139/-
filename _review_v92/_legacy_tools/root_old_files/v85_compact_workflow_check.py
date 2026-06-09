from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app.py'
CONST = ROOT / 'modules' / 'constants.py'
errors=[]
text = APP.read_text(encoding='utf-8')
const = CONST.read_text(encoding='utf-8')
required = [
    'COMPACT_WORKFLOWS',
    '1 제작 시작 · 정지형/움직이는형 미리보기',
    '2 세트 구성 · 32개/24개 품질 진화',
    '3 검사 · 자동보정 · 제출 전 승인',
    '4 반려 대응 · 캡처/OCR · 재생성',
    '5 최종 납품 · 백업/리포트/재검사',
    '고급 세부 메뉴 보기',
]
for marker in required:
    if marker not in text:
        errors.append(f'missing app marker: {marker}')
if '85.0.0' not in const or 'v85' not in const:
    errors.append('constants not updated to v85')
root_bats = [p.name for p in ROOT.glob('*.bat')]
legacy_root = [x for x in root_bats if re.search(r'V(4[0-9]|5[0-9]|6[0-9]|7[0-9]|8[0-4])', x, re.I)]
allowed = {'00_DOUBLE_CLICK_THIS_FIRST_BUILD_SETUP_EXE.bat','00_STEP_1_BUILD_SETUP_EXE.bat','00_STEP_2_PORTABLE_INSTALL_NOW.bat','00_STEP_3_START_PROGRAM.bat','0_BUILD_WINDOWS_INSTALLER_EXE.bat','1_INSTALL_NOW.bat','2_START_PROGRAM.bat','3_CREATE_SHORTCUTS_ONLY.bat','4_REPAIR_ENVIRONMENT.bat','5_OPEN_OUTPUTS.bat','6_RUN_DIAGNOSTICS.bat','OPEN_V85_INNO_SCRIPT.bat','46_V85_COMPACT_WORKFLOW_CHECK.bat','START_WINDOWS.bat'}
unknown = [x for x in root_bats if x not in allowed]
if legacy_root:
    errors.append('legacy version BATs still exposed in root: '+', '.join(legacy_root[:10]))
if unknown:
    errors.append('unexpected root BATs: '+', '.join(unknown[:10]))
if errors:
    print('[v85][FAIL]')
    for e in errors:
        print(' -', e)
    raise SystemExit(1)
print('[v85][PASS] compact workflow markers found')
print('[v85][PASS] root BAT count:', len(root_bats))
print('[v85][PASS] root BATs:', ', '.join(sorted(root_bats)))
