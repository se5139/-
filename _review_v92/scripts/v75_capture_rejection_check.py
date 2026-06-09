from __future__ import annotations
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.capture_rejection_ingestion import V75CaptureRejectionIngestionEngine


def make_sample_image(path: Path) -> None:
    img = Image.new('RGB', (900, 520), 'white')
    d = ImageDraw.Draw(img)
    d.rectangle((30, 30, 870, 490), outline=(30, 80, 160), width=6)
    lines = [
        '카카오 심사 결과 캡처 예시',
        '문구가 길고 작은 화면에서 가독성이 낮아 보입니다.',
        '움직임이 단순하고 일부 표현이 반복됩니다.',
        '캐릭터 고유성을 더 강화해 주세요.',
    ]
    y = 70
    for line in lines:
        d.text((70, y), line, fill=(20, 30, 45))
        y += 80
    img.save(path)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / 'outputs' / 'v75_check'
    out.mkdir(parents=True, exist_ok=True)
    sample = out / 'sample_rejection_capture.png'
    make_sample_image(sample)
    engine = V75CaptureRejectionIngestionEngine()
    result = engine.build_bundle(
        project_name='v75_check_capture_rejection',
        concept_text='작은 썸네일에서도 보이는 손그림 공감형 캐릭터 세트를 캡처 반려 사유 기반으로 개선한다.',
        selected_style=engine.v74.STYLE_PRESETS[0],
        main_phrase='넵',
        user_feedback='초기 방향은 만족하지만 캡처 반려 사유를 바탕으로 품질을 개선한다.',
        online_abstract_notes='온라인 자료는 추상 신호만 반영한다.',
        manual_rejection_text=engine.SAMPLE_REJECTION_TEXT,
        image_inputs=[('sample_rejection_capture.png', sample.read_bytes())],
        out_dir=out,
        enable_ocr=False,
    )
    d = result.to_dict()
    required_keys = [
        'capture_manifest_json', 'capture_analysis_csv', 'ocr_candidates_csv', 'capture_contact_sheet_png',
        'image_archive_zip', 'v75_html_report_path', 'v75_work_package_zip', 'learning_db',
        'v74_html_report_path', 'v74_action_plan_csv', 'v74_resubmission_work_package_zip'
    ]
    missing = [k for k in required_keys if not Path(d.get(k, '')).exists()]
    checks = {
        'ok': not missing and d['image_count'] == 1 and d['capture_status'] == 'ready_for_v74_loop',
        'missing': missing,
        'image_count': d['image_count'],
        'ocr_available': d['ocr_available'],
        'extracted_text_count': d['extracted_text_count'],
        'output_dir': d['output_dir'],
        'work_zip': d['v75_work_package_zip'],
    }
    report = root / 'v75_capture_rejection_check_report.json'
    report.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if checks['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
