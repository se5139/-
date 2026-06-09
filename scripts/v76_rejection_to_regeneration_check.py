from __future__ import annotations
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.rejection_to_regeneration_engine import V76RejectionToRegenerationEngine


def make_sample_image(path: Path) -> None:
    img = Image.new('RGB', (920, 540), 'white')
    d = ImageDraw.Draw(img)
    d.rectangle((32, 32, 888, 508), outline=(124, 58, 237), width=6)
    lines = [
        '카카오 심사 결과 캡처 예시',
        '문구가 길고 작은 화면에서 가독성이 낮아 보입니다.',
        '표정과 포즈가 반복되어 세트 다양성이 부족합니다.',
        '움직임이 단순해 GIF 모션 차이를 강화해 주세요.',
        '캐릭터 고유성을 더 분명하게 보여 주세요.',
    ]
    y = 64
    for line in lines:
        d.text((70, y), line, fill=(20, 30, 45))
        y += 76
    img.save(path)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / 'outputs' / 'v76_check'
    out.mkdir(parents=True, exist_ok=True)
    sample = out / 'sample_rejection_capture.png'
    make_sample_image(sample)
    engine = V76RejectionToRegenerationEngine()
    result = engine.build_bundle(
        project_name='v76_check_rejection_to_regeneration',
        concept_text='작은 썸네일에서도 보이는 손그림 공감형 캐릭터 세트를 반려 사유 기반으로 실제 재생성한다.',
        selected_style=engine.v70.STYLE_PRESETS[0],
        main_phrase='넵',
        user_feedback='초기 방향은 만족하지만 문구, 표정, 모션, 세트 다양성을 실제 결과에 반영해 다시 생성한다.',
        online_abstract_notes='온라인 자료는 추상 신호만 반영한다.',
        manual_rejection_text=engine.DEFAULT_REJECTION_TEXT,
        image_inputs=[('sample_rejection_capture.png', sample.read_bytes())],
        out_dir=out,
        enable_ocr=False,
        user_selected_rules=['문구 2~7자 우선', 'GIF 모션 차이 크게', '32개/24개 중복감 줄이기'],
    )
    d = result.to_dict()
    required_keys = [
        'html_report_path', 'work_package_zip', 'regeneration_action_plan_csv', 'regeneration_prompt_md',
        'regeneration_manifest_json', 'regenerated_set_package_zip', 'regenerated_static_32_gallery',
        'regenerated_animated_24_gallery', 'regenerated_gif_contact_sheet', 'connected_v74_action_plan_csv',
        'capture_v75_report_html', 'learning_db'
    ]
    missing = [k for k in required_keys if not Path(d.get(k, '')).exists()]
    checks = {
        'ok': not missing and d['regenerated_static_count'] == 32 and d['regenerated_animated_count'] == 24 and d['regenerated_gif_count'] >= 3,
        'missing': missing,
        'pipeline_status': d['pipeline_status'],
        'categories': d['detected_categories'],
        'regenerated_static_count': d['regenerated_static_count'],
        'regenerated_animated_count': d['regenerated_animated_count'],
        'regenerated_gif_count': d['regenerated_gif_count'],
        'output_dir': d['output_dir'],
        'work_package_zip': d['work_package_zip'],
    }
    report = root / 'v76_rejection_to_regeneration_check_report.json'
    report.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if checks['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
