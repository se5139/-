from pathlib import Path
from PIL import Image, ImageDraw

from modules.character_search_center.keyword_analyzer import KeywordAnalyzer
from modules.character_search_center.concept_expander import ConceptExpander
from modules.character_search_center.multi_source_mixer import MultiSourceMixer
from modules.expression_bank.expression_generator import ExpressionGenerator
from modules.format_engine.format_recommender import FormatRecommender
from modules.animated_text_emoticon.frame_builder import AnimatedTextFrameBuilder
from modules.trend_intelligence.manual_trend_analyzer import ManualTrendAnalyzer
from modules.reporting.html_reporter import HtmlReporter
from modules.prototype_generator.character_prototype_builder import CharacterPrototypeBuilder
from modules.submission_package.submission_package_builder import SubmissionPackageBuilder
from modules.profit_pipeline.pipeline_planner import ProfitPipelinePlanner
from modules.profit_pipeline.submission_tracker import SubmissionTracker
from modules.quality_checker.submission_quality_reviewer import SubmissionQualityReviewer
from modules.trend_intelligence.thirty_day_trend_engine import ThirtyDayTrendEngine
from modules.trend_intelligence.kipris_trademark_checker import KiprisTrademarkChecker
from modules.copyright_guard.defense_center import CopyrightDefenseCenter
from modules.installer_health.diagnostics import InstallationDiagnostics
from modules.policy_compliance.human_origin_workflow import HumanOriginWorkflow
from modules.beginner_creator.direct_character_creator import BeginnerCharacterCreator, DuoCharacterInput
from modules.beginner_creator.multi_material_creator import MultiMaterialCharacterCreator, MaterialSpec
from modules.candidate_curation import CandidateGalleryBuilder
from modules.candidate_curation.expression_face_engine import ExpressionFaceEngine
from modules.part_editor import PartMotionEditor
from modules.chat_preview import ChatPreviewReviewer
from modules.sample_set import SampleSetBuilder
from modules.data_safety import DataSafetyManager
from modules.growth_learning import GrowthLearningEngine
from modules.workflow_wizard import WorkflowWizard
from modules.drawing_canvas import DrawingCanvasLayerEditor
from modules.consistency_checker import SetConsistencyReviewer
from modules.free_drawing import FreeDrawingCanvas
from modules.drawing_refine import DrawingRefineEngine

out = Path("outputs/check")
out.mkdir(parents=True, exist_ok=True)

profile = KeywordAnalyzer().analyze("보리와 쌀, 예의 바른데 항상 피곤한 직장인 캐릭터")
concepts = ConceptExpander().expand(profile, 3)
mixer = MultiSourceMixer()
materials = mixer.parse_materials(profile.raw_text)
blend = mixer.blend_images([])
blend_concepts = mixer.build_blend_concepts(materials, profile, blend, 3)
expressions = ExpressionGenerator().generate(concepts[0].name, 80)
scores = FormatRecommender().score(profile.raw_text, expressions)
trend = ManualTrendAnalyzer().analyze("퇴근 월요병 번아웃 넵 확인했습니다 죄송합니다 직장인 공감")
api_trend_report = ThirtyDayTrendEngine().run(
    keywords=["직장인 공감", "퇴근", "월요병", "넵", "확인했습니다", "보리와 쌀"],
    manual_text="퇴근 월요병 번아웃 넵 확인했습니다 죄송합니다 직장인 공감 피곤 문구와 같이 움직이는 이모티콘",
    days=30,
    output_dir=out / "trend_reports",
)
trademark_checks = KiprisTrademarkChecker().check_keywords(["보리와 쌀", "춘식이 느낌", "직장인 감자"])

install_diag_report = InstallationDiagnostics().run(project_root=Path.cwd(), app_version="19.0.0", output_dir=out / "installer_diagnostics")

human_origin_report = HumanOriginWorkflow().build_report(
    project_name="quick_check_human_origin",
    concept_text="직접 스케치 기반 보리와 쌀 캐릭터. AI는 문구 후보와 품질 검사에만 사용.",
    ai_usage_mode="시장 분석/품질 검사/문구 분류에만 사용",
    evidence_paths=[out],
    output_dir=out / "human_origin_compliance",
    has_hand_sketch=True,
    has_layer_files=True,
    has_revision_history=True,
    has_source_license_log=True,
    has_final_package=True,
)

beginner_spec = DuoCharacterInput(
    material_a="보리",
    material_b="쌀",
    personality_a="까칠하지만 은근히 챙김",
    personality_b="온순하고 다정함",
    tone_a="투덜거림, 짧게 말함",
    tone_b="부드럽고 위로하는 말투",
    color_a="연갈색",
    color_b="아이보리",
    relationship="투덜이와 다정이 콤비",
    target="직장인/일상 답장",
)
beginner_report = BeginnerCharacterCreator().build_project(
    spec=beginner_spec,
    output_dir=out / "beginner_creator",
    project_name="quick_check_beginner_creator",
    expression_count=80,
    preview_count=12,
)

# v18: 1~5개 소재 + 스케치/첨부파일 기반 멀티 캐릭터 생성 검사
multi_specs = [
    MaterialSpec(name="보리", color="연갈색", personality="까칠하지만 은근히 챙김", tone="투덜거림, 짧게 말함", base_shape="알갱이형", role="중심"),
    MaterialSpec(name="쌀", color="아이보리", personality="온순하고 다정함", tone="부드럽고 위로하는 말투", base_shape="둥근형", role="보조"),
    MaterialSpec(name="감자", color="연노랑", personality="피곤하지만 성실함", tone="작게 한숨 섞인 말투", base_shape="둥근형", role="리액션"),
    MaterialSpec(name="고구마", color="주황", personality="느긋하고 포근함", tone="느긋하고 둥근 말투", base_shape="길쭉형", role="확장"),
    MaterialSpec(name="메모지", color="회색", personality="업무에 눌려 구겨짐", tone="짧은 업무 답장 말투", base_shape="네모형", role="문구 담당"),
]
# 직접 그린 스케치 사진을 흉내낸 샘플 첨부 파일
sketch = Image.new("RGBA", (420, 320), (255, 255, 255, 0))
sd = ImageDraw.Draw(sketch)
sd.ellipse((80, 70, 250, 230), fill=(220, 180, 110, 255), outline=(30,30,30,255), width=5)
sd.ellipse((130, 125, 145, 140), fill=(20,20,20,255))
sd.arc((135, 145, 195, 180), 0, 180, fill=(20,20,20,255), width=3)
sketch_path = out / "quick_check_user_sketch.png"
sketch.save(sketch_path)
multi_report = MultiMaterialCharacterCreator().build_project(
    specs=multi_specs,
    uploaded_files=[sketch_path],
    output_dir=out / "multi_material_creator",
    project_name="quick_check_multi_material_creator",
    expression_count=80,
    preview_count=12,
)

# v18: 표현 후보 80개에서 포맷별 24/32개 선택 + 표정 자동 구성 검사
candidate_gallery_report = CandidateGalleryBuilder().build_gallery_pack(
    specs=multi_specs,
    expressions=multi_report.expression_table,
    output_dir=out / "candidate_gallery",
    project_name="quick_check_candidate_gallery",
    format_key="static_text",
    target_count=32,
)
animated_candidate_gallery_report = CandidateGalleryBuilder().build_gallery_pack(
    specs=multi_specs,
    expressions=multi_report.expression_table,
    output_dir=out / "candidate_gallery",
    project_name="quick_check_candidate_gallery_animated",
    format_key="animated_text",
    target_count=24,
)

# v18: 표정·파츠·문구·움직임 편집기 검사
part_edit_report = PartMotionEditor().build_edit_pack(
    expressions=candidate_gallery_report.selected_expressions,
    output_dir=out / "part_motion_editor",
    project_name="quick_check_part_motion_editor",
    format_key="static_text",
    global_overrides={
        "eye_style": "happy",
        "brow_style": "soft",
        "mouth_style": "small_smile",
        "body_motion": "작게 끄덕임",
        "text_motion": "도장처럼 찍힘",
        "effects": "check",
        "font_size": 28,
        "char_x": 178,
        "char_y": 142,
        "text_x": 180,
        "text_y": 250,
    },
    preview_limit=12,
)
animated_part_edit_report = PartMotionEditor().build_edit_pack(
    expressions=animated_candidate_gallery_report.selected_expressions,
    output_dir=out / "part_motion_editor",
    project_name="quick_check_part_motion_editor_animated",
    format_key="animated_text",
    global_overrides={
        "body_motion": "몸이 작아지며 꾸벅",
        "text_motion": "작게 떨림",
        "effects": "sweat",
        "font_size": 27,
        "char_x": 178,
        "char_y": 142,
        "text_x": 180,
        "text_y": 250,
    },
    preview_limit=8,
)

# v18: 실제 카카오톡 채팅창 미리보기 + 최종 검수 검사
chat_preview_report = ChatPreviewReviewer().build_preview_pack(
    expressions=part_edit_report.edited_expressions,
    output_dir=out / "chat_preview_final_review",
    project_name="quick_check_chat_preview",
    format_key="static_text",
    preview_files=part_edit_report.preview_files,
    preview_limit=8,
    include_dark=True,
    include_small=True,
)
animated_chat_preview_report = ChatPreviewReviewer().build_preview_pack(
    expressions=animated_part_edit_report.edited_expressions,
    output_dir=out / "chat_preview_final_review",
    project_name="quick_check_chat_preview_animated",
    format_key="animated_text",
    preview_files=animated_part_edit_report.preview_files,
    preview_limit=6,
    include_dark=True,
    include_small=True,
)


# v18: 첫 실제 샘플 세트 제작 모드 검사
sample_set_report = SampleSetBuilder().build_sample_set(
    specs=multi_specs[:2],
    output_dir=out / "sample_sets",
    project_name="quick_check_barley_rice_sample_set",
    format_key="static_text",
    target_count=32,
    expression_count=80,
    preview_limit=8,
    include_dark=True,
    include_small=True,
)
animated_sample_set_report = SampleSetBuilder().build_sample_set(
    specs=multi_specs[:2],
    output_dir=out / "sample_sets",
    project_name="quick_check_barley_rice_animated_sample_set",
    format_key="animated_text",
    target_count=24,
    expression_count=80,
    preview_limit=6,
    include_dark=True,
    include_small=True,
)


# v21: 초보자 전체 제작 마법사 검사
workflow_report = WorkflowWizard().build_wizard_report(
    specs=multi_specs[:2],
    output_dir=out / "workflow_wizard",
    project_name="quick_check_workflow_wizard",
    format_key="static_text",
    target_count=32,
    expression_count=80,
    run_sample_generation=True,
    include_dark=True,
    include_small=True,
)

# v23: 캐릭터 일관성 검사/자동 보정 검사
consistency_report = SetConsistencyReviewer().build_consistency_pack(
    expressions=part_edit_report.edited_expressions,
    preview_files=part_edit_report.preview_files,
    output_dir=out / "set_consistency_review",
    project_name="quick_check_set_consistency",
    format_key="static_text",
    auto_correct=True,
    preview_limit=12,
)
animated_consistency_report = SetConsistencyReviewer().build_consistency_pack(
    expressions=animated_part_edit_report.edited_expressions,
    preview_files=animated_part_edit_report.preview_files,
    output_dir=out / "set_consistency_review",
    project_name="quick_check_set_consistency_animated",
    format_key="animated_text",
    auto_correct=True,
    preview_limit=8,
)


# v19: 데이터 보호/백업/마이그레이션 검사
data_safety_manager = DataSafetyManager()
data_safety_dirs = data_safety_manager.ensure_user_data_dirs(Path.cwd())
small_backup_sample = out / "data_safety_input_sample"
small_backup_sample.mkdir(parents=True, exist_ok=True)
(small_backup_sample / "sample_user_data.txt").write_text("quick check data safety sample", encoding="utf-8")
data_backup_report = data_safety_manager.create_backup(
    root=Path.cwd(),
    project_name="quick_check_data_safety",
    extra_paths=[small_backup_sample],
    output_dir=out / "data_safety",
)
data_verify_report = data_safety_manager.verify_backup(
    data_backup_report.backup_zip_path,
    output_dir=out / "data_safety",
    project_name="quick_check_data_safety_verify",
)
data_restore_report = data_safety_manager.restore_backup_safe(
    data_backup_report.backup_zip_path,
    restore_root=out / "safe_restore",
    output_dir=out / "data_safety",
    project_name="quick_check_data_safety_restore",
)
copyright_report = CopyrightDefenseCenter().build_report(
    project_name="quick_check_defense",
    concept_text=profile.raw_text + " 기존 캐릭터를 모방하지 않고 직접 제작",
    phrase_text="\n".join([e.phrase for e in expressions[:20]]),
    visual_notes="단순 도형 기반 360x360 시안, 문구와 캐릭터 움직임 동기화",
    ai_usage_mode="아이디어/문구 추천만 사용",
    ai_notes="제출용 완성 이미지는 직접 제작 레이어/프로그램 생성 시안 기반. AI는 기획 보조로만 기록.",
    asset_rows=[
        {"filename":"sample_character.png", "asset_type":"원본 스케치", "source":"직접 제작", "license_type":"본인 창작", "commercial_use":"가능", "modification_allowed":"가능", "attribution_required":"불필요", "note":"quick check sample"},
        {"filename":"font", "asset_type":"폰트", "source":"상업 이용 가능 폰트로 교체 필요", "license_type":"미확인", "commercial_use":"미확인", "modification_allowed":"미확인", "attribution_required":"미확인", "note":"실제 제출 전 확인"},
    ],
    evidence_paths=[out],
    output_dir=out / "copyright_defense",
)

img = Image.new("RGBA", (360, 360), (255, 255, 255, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((90, 70, 270, 250), radius=30, fill=(245, 230, 160, 255), outline=(40, 40, 40, 255), width=4)
d.ellipse((135, 130, 150, 145), fill=(20, 20, 20, 255))
d.ellipse((210, 130, 225, 145), fill=(20, 20, 20, 255))
d.arc((145, 145, 215, 190), 0, 180, fill=(20, 20, 20, 255), width=3)
base = out / "sample_character.png"
img.save(base)
AnimatedTextFrameBuilder().build_gif(base, "확인했습니다", out / "sample.gif")

builder = CharacterPrototypeBuilder()
specs = builder.build_specs(materials, blend, blend_concepts, 4)
prototype_results = builder.render_prototypes(specs, out / "prototypes")
expression_files = builder.render_expression_pack(specs[0], expressions, out / "prototype_expression_pack", 8)
zip_path = builder.zip_files(expression_files, out / "prototype_expression_pack.zip")
submission_result = SubmissionPackageBuilder().build(
    spec=specs[0],
    expressions=[e.to_dict() for e in expressions],
    output_root=out / "submission_packages",
    project_name="quick_check_submission",
    format_key="static_text",
    target_count=12,
)
animated_submission_result = SubmissionPackageBuilder().build(
    spec=specs[0],
    expressions=[e.to_dict() for e in expressions],
    output_root=out / "submission_packages",
    project_name="quick_check_animated_text",
    format_key="animated_text",
    target_count=6,
)

plan = ProfitPipelinePlanner().build(
    character_name=concepts[0].name,
    profile=profile.to_dict(),
    trend_result=trend.to_dict(),
    format_scores=[s.to_dict() for s in scores],
    expressions=[e.to_dict() for e in expressions],
    desired_monthly_submissions=1,
)
tracker = SubmissionTracker(out / "submission_history.json")
record = tracker.make_record(
    character_name=concepts[0].name,
    format_label=plan.primary_format,
    status="준비",
    rejection_reason="",
    revision_note="quick check",
    sales_note="",
)
records = tracker.add(record)
csv_path = tracker.export_csv(out / "submission_history.csv", records)

quality_review = SubmissionQualityReviewer().review(
    package_dir=submission_result.package_dir,
    format_key=submission_result.format_key,
    expressions=[e.to_dict() for e in expressions],
    output_dir=out / "submission_packages" / "quality_review",
)
animated_quality_review = SubmissionQualityReviewer().review(
    package_dir=animated_submission_result.package_dir,
    format_key=animated_submission_result.format_key,
    expressions=[e.to_dict() for e in expressions],
    output_dir=out / "submission_packages" / "animated_quality_review",
)


# v20: 누적 데이터 성장형 추천 엔진 검사
growth_engine = GrowthLearningEngine()
growth_save = growth_engine.record_snapshot(
    project_name="quick_check_growth_learning",
    concept_text=profile.raw_text,
    profile=profile.to_dict(),
    expressions=[e.to_dict() for e in expressions],
    format_scores=[s.to_dict() for s in scores],
    trend_result=trend.to_dict(),
    api_trend_report=api_trend_report.to_dict(),
    candidate_gallery_report=candidate_gallery_report.to_dict(),
    quality_review=quality_review.to_dict(),
    chat_preview_report=chat_preview_report.to_dict(),
    copyright_report=copyright_report.to_dict(),
    sample_set_report=sample_set_report.to_dict(),
    output_root=out / "growth_learning_store",
)
growth_outcome = growth_engine.record_outcome(
    project_name="quick_check_growth_learning",
    character_name="보리와 쌀",
    format_key="static_text",
    status="준비",
    rejection_reason="quick check",
    revenue_amount=0,
    downloads_or_sales_count=0,
    output_root=out / "growth_learning_store",
)
growth_report = growth_engine.build_growth_report(
    project_name="quick_check_growth_learning",
    output_dir=out / "growth_learning_reports",
    store_root=out / "growth_learning_store",
)

HtmlReporter().write_report({
    "title": "quick check report",
    "profile": profile.to_dict(),
    "concepts": [c.to_dict() for c in concepts],
    "materials": [m.to_dict() for m in materials],
    "blend_concepts": [c.to_dict() for c in blend_concepts],
    "format_scores": [s.to_dict() for s in scores],
    "trend": trend.to_dict(),
    "prototype_results": [r.to_dict() for r in prototype_results],
    "expression_files": expression_files,
    "submission_result": submission_result.to_dict(),
    "animated_submission_result": animated_submission_result.to_dict(),
    "profit_pipeline_plan": plan.to_dict(),
    "submission_records": records,
    "quality_review": quality_review.to_dict(),
    "animated_quality_review": animated_quality_review.to_dict(),
    "api_trend_report": api_trend_report.to_dict(),
    "trademark_checks": [t.to_dict() for t in trademark_checks],
    "copyright_report": copyright_report.to_dict(),
    "install_diag_report": install_diag_report.to_dict(),
    "human_origin_report": human_origin_report.to_dict(),
    "beginner_creator_report": beginner_report.to_dict(),
    "multi_material_creator_report": multi_report.to_dict(),
    "candidate_gallery_report": candidate_gallery_report.to_dict(),
    "animated_candidate_gallery_report": animated_candidate_gallery_report.to_dict(),
    "part_edit_report": part_edit_report.to_dict(),
    "animated_part_edit_report": animated_part_edit_report.to_dict(),
    "chat_preview_report": chat_preview_report.to_dict(),
    "animated_chat_preview_report": animated_chat_preview_report.to_dict(),
    "sample_set_report": sample_set_report.to_dict(),
    "animated_sample_set_report": animated_sample_set_report.to_dict(),
    "data_backup_report": data_backup_report.to_dict(),
    "data_verify_report": data_verify_report.to_dict(),
    "data_restore_report": data_restore_report.to_dict(),
    "growth_learning_report": growth_report.to_dict(),
    "consistency_report": consistency_report.to_dict(),
    "animated_consistency_report": animated_consistency_report.to_dict(),
    "free_drawing_report": "generated later in v24/v25 check",
    "drawing_refine_report": "generated later in v25 check",
}, out / "report.html")

assert len(materials) >= 2
assert len(blend_concepts) == 3
assert len(prototype_results) == 4
assert len(expression_files) == 8
assert zip_path.exists()
assert Path(submission_result.zip_path).exists()
assert Path(animated_submission_result.zip_path).exists()
assert submission_result.created_count == 12
assert animated_submission_result.created_count == 6
assert len(plan.steps) == 3
assert len(plan.series_candidates) >= 3
assert csv_path.exists()
assert records[-1]["next_action"]
assert Path(quality_review.html_path).exists()
assert Path(animated_quality_review.html_path).exists()
assert Path(api_trend_report.html_path).exists()
assert Path(api_trend_report.json_path).exists()
assert api_trend_report.recommended_formats
assert any(t.risk_score >= 70 for t in trademark_checks)
assert Path(install_diag_report.html_path).exists()
assert Path(install_diag_report.json_path).exists()
assert Path(human_origin_report.html_path).exists()
assert Path(human_origin_report.json_path).exists()
assert Path(beginner_report.html_path).exists()
assert Path(beginner_report.json_path).exists()
assert Path(beginner_report.zip_path).exists()
assert len(beginner_report.expression_table) == 80
assert len(beginner_report.generated_assets) >= 15
assert Path(multi_report.html_path).exists()
assert Path(multi_report.json_path).exists()
assert Path(multi_report.zip_path).exists()
assert len(multi_report.material_specs) == 5
assert len(multi_report.source_files) == 1
assert len(multi_report.expression_table) == 80
assert len(multi_report.generated_assets) >= 18
assert Path(candidate_gallery_report.html_path).exists()
assert Path(candidate_gallery_report.json_path).exists()
assert Path(candidate_gallery_report.csv_path).exists()
assert Path(candidate_gallery_report.zip_path).exists()
assert candidate_gallery_report.selected_count == 32
assert all("expression_plan" in r and "face_summary" in r for r in candidate_gallery_report.selected_expressions)
assert any("sweat" in r["expression_plan"].get("effects", []) or r["expression_plan"].get("mouth_style") == "sad" for r in candidate_gallery_report.selected_expressions)
assert Path(animated_candidate_gallery_report.zip_path).exists()
assert animated_candidate_gallery_report.selected_count == 24
assert all("expression_plan" in r and "body_motion" in r["expression_plan"] for r in animated_candidate_gallery_report.selected_expressions)
assert any(Path(g["file_path"]).suffix.lower() == ".gif" for g in animated_candidate_gallery_report.generated_files)
assert Path(part_edit_report.html_path).exists()
assert Path(part_edit_report.json_path).exists()
assert Path(part_edit_report.csv_path).exists()
assert Path(part_edit_report.zip_path).exists()
assert part_edit_report.edited_count == candidate_gallery_report.selected_count
assert part_edit_report.final_check_table
assert part_edit_report.timeline_table
assert any(item["kind"] == "png_preview" for item in part_edit_report.preview_files)
assert Path(animated_part_edit_report.zip_path).exists()
assert animated_part_edit_report.edited_count == animated_candidate_gallery_report.selected_count
assert animated_part_edit_report.timeline_table
assert any(item["kind"] in ["gif_preview", "png_preview"] for item in animated_part_edit_report.preview_files)
assert Path(chat_preview_report.html_path).exists()
assert Path(chat_preview_report.json_path).exists()
assert Path(chat_preview_report.csv_path).exists()
assert Path(chat_preview_report.zip_path).exists()
assert chat_preview_report.preview_count >= 8
assert chat_preview_report.chat_usability_score >= 0
assert Path(animated_chat_preview_report.zip_path).exists()
assert animated_chat_preview_report.preview_count >= 6
assert Path(sample_set_report.zip_path).exists()
assert Path(sample_set_report.html_path).exists()
assert sample_set_report.selected_count == 32
assert sample_set_report.submission_result["created_count"] == 32
assert sample_set_report.quality_review["actual_count"] == 32
assert Path(animated_sample_set_report.zip_path).exists()
assert Path(data_backup_report.backup_zip_path).exists()
assert data_backup_report.backup_sha256
assert Path(data_backup_report.html_path).exists()
assert Path(data_verify_report.html_path).exists()
assert data_verify_report.score >= 0
assert Path(data_restore_report.html_path).exists()
assert growth_save["saved"]
assert growth_outcome["saved"]
assert Path(growth_report.html_path).exists()
assert Path(growth_report.json_path).exists()
assert Path(growth_report.csv_path).exists()
assert growth_report.confidence_score >= 0


# v22: 직접 그리기 캔버스/레이어 편집기 검사
canvas_editor = DrawingCanvasLayerEditor()
canvas_layers = canvas_editor.build_layers_from_presets([
    "둥근 얼굴", "알갱이 몸통", "점눈 왼쪽", "점눈 오른쪽",
    "웃는 입", "왼팔", "오른팔", "땀 효과", "말풍선"
], base_color="#D1A164", label_text="보리쌀")
drawing_canvas_report = canvas_editor.build_canvas_project(
    layers=canvas_layers,
    output_dir=out / "direct_canvas_layer_editor",
    project_name="quick_check_direct_canvas"
)

# v24: 마우스/태블릿 펜/터치 기반 자유 드로잉 캔버스 강화 검사
free_canvas = FreeDrawingCanvas()
free_strokes = free_canvas.sample_strokes("보리쌀", color="#2E2924")
free_text_strokes = free_canvas.parse_strokes_from_text(
    "face: 108,125 125,80 180,55 235,80 252,125 235,170 180,195 125,170 108,125\n"
    "body: 110,230 150,195 210,195 250,230 220,280 140,280 110,230\n"
    "eye: 150,120 151,120\neye2: 210,120 211,120\nsmile: 150,150 165,165 180,172 195,165 210,150",
    color="#2E2924",
    width=8,
)
free_drawing_report = free_canvas.build_project(
    strokes=free_text_strokes + free_strokes[:2],
    output_dir=out / "free_drawing_canvas",
    project_name="quick_check_free_drawing_canvas",
)

# v25: 자유 드로잉 자동 정리 + 파츠 추정 + 표정 확장 검사
drawing_refine_report = DrawingRefineEngine().build_project(
    input_image_path=Path(free_drawing_report.auto_clean_png_path),
    output_dir=out / "drawing_refine_v25",
    project_name="quick_check_drawing_refine_v25",
    starter_expression_count=32,
    variant_count=12,
)

assert Path(consistency_report.html_path).exists()
assert Path(consistency_report.json_path).exists()
assert Path(consistency_report.csv_path).exists()
assert Path(consistency_report.zip_path).exists()
assert consistency_report.source_count == part_edit_report.edited_count
assert consistency_report.consistency_score >= 0
assert any(item["kind"] == "corrected_preview" for item in consistency_report.generated_files)
assert Path(animated_consistency_report.zip_path).exists()
assert animated_consistency_report.source_count == animated_part_edit_report.edited_count
assert Path(workflow_report.html_path).exists()
assert Path(workflow_report.json_path).exists()
assert Path(workflow_report.csv_path).exists()
assert Path(workflow_report.zip_path).exists()
assert Path(drawing_canvas_report.transparent_png_path).exists()
assert Path(drawing_canvas_report.preview_png_path).exists()
assert Path(drawing_canvas_report.manifest_path).exists()
assert Path(drawing_canvas_report.csv_path).exists()
assert Path(drawing_canvas_report.html_path).exists()
assert Path(drawing_canvas_report.zip_path).exists()
assert drawing_canvas_report.layer_count >= 8
assert Path(free_drawing_report.canvas_png_path).exists()
assert Path(free_drawing_report.auto_clean_png_path).exists()
assert Path(free_drawing_report.layer_manifest_path).exists()
assert Path(free_drawing_report.csv_path).exists()
assert Path(free_drawing_report.html_path).exists()
assert Path(free_drawing_report.zip_path).exists()
assert Path(drawing_refine_report.normalized_png_path).exists()
assert Path(drawing_refine_report.parts_overlay_path).exists()
assert Path(drawing_refine_report.parts_manifest_path).exists()
assert Path(drawing_refine_report.expression_csv_path).exists()
assert Path(drawing_refine_report.zip_path).exists()
assert drawing_refine_report.part_count >= 6
assert drawing_refine_report.variant_count == 12
assert drawing_refine_report.starter_expression_count == 32
assert free_drawing_report.stroke_count >= 5
assert free_drawing_report.point_count >= 20
assert workflow_report.progress_percent >= 80
assert workflow_report.sample_set_report is not None
assert animated_sample_set_report.selected_count == 24
assert animated_sample_set_report.submission_result["created_count"] == 24
assert human_origin_report.compliance_score >= 0
assert Path(copyright_report.html_path).exists()
assert Path(copyright_report.json_path).exists()
assert Path(copyright_report.csv_path).exists()
assert copyright_report.overall_risk_score >= 0
assert quality_review.actual_count == submission_result.created_count
assert animated_quality_review.actual_count == animated_submission_result.created_count
print("PASS")
print(scores[0].label, scores[0].score)
print("materials", [m.name for m in materials])
print("prototypes", [Path(r.file_path).name for r in prototype_results])
print("submission", Path(submission_result.zip_path).name, submission_result.created_count)
print("animated_submission", Path(animated_submission_result.zip_path).name, animated_submission_result.created_count)
print("pipeline", plan.primary_format, "steps", len(plan.steps))
print("tracker", Path(csv_path).name, len(records))
print("quality", quality_review.final_status, quality_review.overall_score)
print("animated_quality", animated_quality_review.final_status, animated_quality_review.overall_score)
print("api_trend", api_trend_report.recommended_formats[0], len(api_trend_report.top_keywords))
print("trademark", max(t.risk_score for t in trademark_checks), [t.keyword for t in trademark_checks])
print("copyright_defense", copyright_report.final_status, copyright_report.overall_risk_score)
print("installer_diagnostics", install_diag_report.overall_status, install_diag_report.score)
print("human_origin", human_origin_report.final_status, human_origin_report.compliance_score)
print("beginner_creator", Path(beginner_report.zip_path).name, len(beginner_report.expression_table), len(beginner_report.generated_assets))
print("multi_material_creator", Path(multi_report.zip_path).name, len(multi_report.material_specs), len(multi_report.source_files), len(multi_report.expression_table), len(multi_report.generated_assets))
print("candidate_gallery", Path(candidate_gallery_report.zip_path).name, candidate_gallery_report.selected_count, len(candidate_gallery_report.generated_files), "face_plans", len([r for r in candidate_gallery_report.selected_expressions if r.get("expression_plan")]))
print("animated_candidate_gallery", Path(animated_candidate_gallery_report.zip_path).name, animated_candidate_gallery_report.selected_count, len(animated_candidate_gallery_report.generated_files), "face_plans", len([r for r in animated_candidate_gallery_report.selected_expressions if r.get("expression_plan")]))
print("part_motion_editor", Path(part_edit_report.zip_path).name, part_edit_report.edited_count, len(part_edit_report.preview_files), len(part_edit_report.final_check_table))
print("animated_part_motion_editor", Path(animated_part_edit_report.zip_path).name, animated_part_edit_report.edited_count, len(animated_part_edit_report.preview_files), len(animated_part_edit_report.timeline_table))
print("chat_preview", Path(chat_preview_report.zip_path).name, chat_preview_report.preview_count, chat_preview_report.chat_usability_score, chat_preview_report.final_status)
print("animated_chat_preview", Path(animated_chat_preview_report.zip_path).name, animated_chat_preview_report.preview_count, animated_chat_preview_report.chat_usability_score, animated_chat_preview_report.final_status)
print("sample_set", Path(sample_set_report.zip_path).name, sample_set_report.selected_count, sample_set_report.sample_score, sample_set_report.sample_status)
print("animated_sample_set", Path(animated_sample_set_report.zip_path).name, animated_sample_set_report.selected_count, animated_sample_set_report.sample_score, animated_sample_set_report.sample_status)
print("data_safety", Path(data_backup_report.backup_zip_path).name, data_backup_report.overall_status, data_verify_report.overall_status, data_restore_report.overall_status)
print("growth_learning", growth_report.learning_level, growth_report.confidence_score, growth_report.total_events, growth_report.total_outcomes)
print("workflow_wizard", Path(workflow_report.zip_path).name, workflow_report.progress_percent, workflow_report.current_phase)
print("drawing_canvas", Path(drawing_canvas_report.zip_path).name, drawing_canvas_report.layer_count, Path(drawing_canvas_report.transparent_png_path).name)
print("free_drawing_canvas", Path(free_drawing_report.zip_path).name, free_drawing_report.stroke_count, free_drawing_report.point_count, Path(free_drawing_report.auto_clean_png_path).name)
print("drawing_refine_v25", Path(drawing_refine_report.zip_path).name, drawing_refine_report.part_count, drawing_refine_report.variant_count, drawing_refine_report.starter_expression_count)
