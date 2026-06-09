from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pandas as pd
import streamlit as st

from modules.constants import APP_NAME, APP_VERSION, FORMAT_LABELS, PLANNING_COUNTS
from modules.character_search_center.keyword_analyzer import KeywordAnalyzer
from modules.character_search_center.concept_expander import ConceptExpander
from modules.character_search_center.image_feature_analyzer import ImageFeatureAnalyzer
from modules.character_search_center.multi_source_mixer import MultiSourceMixer
from modules.expression_bank.expression_generator import ExpressionGenerator
from modules.expression_bank.balance_checker import ExpressionBalanceChecker
from modules.format_engine.format_recommender import FormatRecommender
from modules.format_engine.originality_scorer import OriginalityScorer
from modules.copyright_guard.keyword_guard import KeywordGuard
from modules.animated_text_emoticon.frame_builder import AnimatedTextFrameBuilder
from modules.animated_text_emoticon.text_motion_templates import TEXT_MOTION_PRESETS
from modules.trend_intelligence.manual_trend_analyzer import ManualTrendAnalyzer
from modules.trend_intelligence.youtube_collector import YoutubeCollector
from modules.trend_intelligence.naver_datalab_collector import NaverDatalabCollector
from modules.reporting.html_reporter import HtmlReporter
from modules.project_store.exporter import ProjectExporter
from modules.prototype_generator.character_prototype_builder import CharacterPrototypeBuilder, PrototypeSpec
from modules.submission_package.submission_package_builder import SubmissionPackageBuilder
from modules.profit_pipeline.pipeline_planner import ProfitPipelinePlanner
from modules.profit_pipeline.submission_tracker import SubmissionTracker
from modules.quality_checker.submission_quality_reviewer import SubmissionQualityReviewer
from modules.trend_intelligence.thirty_day_trend_engine import ThirtyDayTrendEngine
from modules.trend_intelligence.youtube_collector import YoutubeCollector
from modules.copyright_guard.defense_center import CopyrightDefenseCenter
from modules.installer_health.diagnostics import InstallationDiagnostics
from modules.policy_compliance.human_origin_workflow import HumanOriginWorkflow
from modules.beginner_creator.direct_character_creator import BeginnerCharacterCreator, DuoCharacterInput
from modules.beginner_creator.multi_material_creator import MultiMaterialCharacterCreator, MaterialSpec
from modules.beginner_creator.creator_presets import COLOR_PRESET_LABELS, COLOR_PALETTES, PERSONALITY_PRESETS, TONE_PRESETS, ROLE_PRESETS, color_from_palette, preset_value, palette_swatch_html
from modules.candidate_curation import CandidateGalleryBuilder
from modules.part_editor import PartMotionEditor
from modules.chat_preview import ChatPreviewReviewer
from modules.sample_set import SampleSetBuilder
from modules.data_safety import DataSafetyManager
from modules.growth_learning import GrowthLearningEngine
from modules.workflow_wizard import WorkflowWizard
from modules.drawing_canvas import DrawingCanvasLayerEditor, CanvasLayer
from modules.consistency_checker import SetConsistencyReviewer
from modules.free_drawing import FreeDrawingCanvas
from modules.drawing_refine import DrawingRefineEngine
from modules.emotion_motion_variation import EmotionMotionVariationEngine
from modules.text_prompt_creator import TextPromptEmoticonEngine, MissingInfoAssistant
from modules.rejection_improvement import RejectionImprovementEngine
from modules.submission_lock import SubmissionLockChecklistEngine
from modules.final_submission_wizard import FinalSubmissionWizard
from modules.youtube_reference import YoutubeReferenceAnalyzer
from modules.dialect_expression import DialectLifeExpressionEngine
from modules.concept_strategy import ConceptStrategyEngine
from modules.taste_experience import TasteExperienceMotionEngine
from modules.kakao_spec_validator import KakaoSpecValidator, KAKAO_SPEC_TABLE
from modules.format_strategy import FormatStrategyEngine
from modules.data_ingestion import CSV_CAPTURE_TYPES, DataIngestionPipeline
from modules.kakao_studio_excel import KakaoStudioExcelLearningEngine
from modules.performance_dashboard import PerformanceDashboardEngine
from modules.selected_format_autofix import SelectedFormatAutoFixEngine, SELECTED_FORMAT_SPECS
from modules.platform_repackaging import PlatformRepackagingEngine, PLATFORM_TARGETS
from modules.installer_stability import InstallerStabilityEngine
from modules.evolution_quality import CharacterTrendEvolutionEngine, StaticAnimatedEvolutionEngine
from modules.free_api_safety import FreeApiSafetyConfig, FreeApiSafetyEngine
from modules.api_guardrail_ledger import V51ApiGuardrailConfig, V51ApiGuardrailLedgerEngine
from modules.static_to_animated_apply import StaticToAnimatedApplyEngine
from modules.api_key_safety import OpenAIKeySafetyEngine, ApiKeySafetyConfig
from modules.kakao_motion_preview_improver import KakaoMotionPreviewImprover
from modules.video_reference_quality_engine import VideoReferenceQualityEngine
from modules.jinja_template_engine import JinjaTemplateEngine
from modules.template_engine_manager import TemplateEngineManager
from modules.coding_toolchain_manager import CodingToolchainManager
from modules.professional_ide_toolchain_manager import ProfessionalIDEToolchainManager
from modules.multi_tool_execution_pipeline import MultiToolExecutionPipeline
from modules.continuous_quality_evolution import ContinuousQualityEvolutionEngine
from modules.actual_quality_upgrade_engine import V69ActualQualityUpgradeEngine
from modules.set_completeness_engine import V70SetCompletenessEngine
from modules.pre_submission_qc_engine import V71PreSubmissionQCEngine
from modules.submission_autofix_lock_engine import V72SubmissionAutofixLockEngine
from modules.final_user_approval_workflow import V73FinalUserApprovalWorkflow
from modules.rejection_resubmission_loop import V74RejectionResubmissionLoop
from modules.capture_rejection_ingestion import V75CaptureRejectionIngestionEngine
from modules.rejection_to_regeneration_engine import V76RejectionToRegenerationEngine
from modules.final_delivery_pipeline import V80FinalDeliveryPipelineEngine
from modules.evolution_learning_collector import EvolutionLearningCollector
from modules.workbench_enhancements import (
    analyze_uploaded_package,
    create_one_page_summary,
    load_project_snapshot,
    rerun_failed_items,
    save_project_snapshot,
)


st.set_page_config(page_title=APP_NAME, page_icon="💬", layout="wide")

BASE_OUTPUT = Path("outputs")
BASE_OUTPUT.mkdir(exist_ok=True)


def init_state() -> None:
    defaults = {
        "profile": None,
        "concepts": [],
        "expressions": [],
        "format_scores": [],
        "trend_result": None,
        "image_profile": None,
        "image_profiles": [],
        "multi_image_blend": None,
        "material_tokens": [],
        "blend_concepts": [],
        "last_gif": None,
        "prototype_specs": [],
        "prototype_results": [],
        "selected_prototype_index": 0,
        "expression_pack_files": [],
        "expression_pack_zip": None,
        "report_path": None,
        "submission_result": None,
        "pipeline_plan": None,
        "submission_history": [],
        "submission_csv_path": None,
        "quality_review": None,
        "api_trend_report": None,
        "copyright_defense_report": None,
        "install_diag_report": None,
        "human_origin_report": None,
        "beginner_creator_report": None,
        "multi_material_creator_report": None,
        "candidate_gallery_report": None,
        "part_edit_report": None,
        "chat_preview_report": None,
        "sample_set_report": None,
        "data_safety_report": None,
        "growth_learning_report": None,
        "growth_learning_save_result": None,
        "workflow_wizard_report": None,
        "drawing_canvas_report": None,
        "consistency_report": None,
        "free_drawing_report": None,
        "drawing_refine_report": None,
        "emotion_motion_report": None,
        "text_prompt_report": None,
        "missing_info_report": None,
        "missing_info_analysis": None,
        "rejection_improvement_report": None,
        "submission_lock_report": None,
        "final_submission_wizard_report": None,
        "youtube_reference_report": None,
        "dialect_life_expression_report": None,
        "concept_strategy_report": None,
        "taste_experience_report": None,
        "kakao_spec_report": None,
        "format_strategy_report": None,
        "data_ingestion_report": None,
        "kakao_studio_excel_report": None,
        "performance_dashboard_report": None,
        "selected_format_autofix_report": None,
        "platform_repackaging_report": None,
        "installer_stability_report": None,
        "active_text_prompt": None,
        "active_generation_profile": None,
        "applied_missing_info_profile": None,
        "v48_evolution_report": None,
        "v48_evolution_applied": None,
        "v49_static_animated_evolution_report": None,
        "v49_static_animated_evolution_applied": None,
        "v50_free_api_safety_report": None,
        "v50_free_api_safety_applied": None,
        "v51_api_guardrail_report": None,
        "v51_api_guardrail_applied": None,
        "v52_static_to_animated_report": None,
        "v52_static_to_animated_applied": None,
        "v58_api_key_safety_report": None,
        "v58_api_key_safety_applied": None,
        "v61_kakao_motion_preview_report": None,
        "v61_kakao_motion_preview_applied": None,
        "v62_jinja_template_report": None,
        "v62_jinja_template_applied": None,
        "v63_template_engine_manager_report": None,
        "v63_template_engine_manager_applied": None,
        "v66_multi_tool_execution_report": None,
        "v66_multi_tool_execution_applied": None,
        "v64_coding_toolchain_report": None,
        "v64_coding_toolchain_applied": None,
        "v65_professional_ide_toolchain_report": None,
        "v65_professional_ide_toolchain_applied": None,
        "v72_submission_autofix_lock_report": None,
        "v73_final_user_approval_report": None,
        "v75_capture_rejection_report": None,
        "v76_rejection_to_regeneration_report": None,
        "v80_final_delivery_report": None,
        "recent_project_snapshot_path": None,
        "quick_submission_check_report": None,
        "quick_submission_summary_path": None,
        "first_run_tutorial_done": False,
        "auto_save_enabled": True,
        "evolution_learning_report": None,
        "evolution_learning_due_status": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def asdict_list(items):
    result = []
    for item in items:
        if hasattr(item, "to_dict"):
            result.append(item.to_dict())
        elif isinstance(item, dict):
            result.append(item)
    return result


init_state()

st.markdown("""
<style>
:root {
    --app-bg:#f4f1eb;
    --panel:#fffdf8;
    --panel-strong:#fbf6eb;
    --ink:#25221d;
    --muted:#766f64;
    --line:#ded5c7;
    --accent:#1f7a6b;
    --accent-2:#c86f3a;
    --accent-soft:#e6f3ee;
    --shadow:0 16px 42px rgba(57, 45, 28, .10);
}
.stApp { background:
    radial-gradient(circle at 16% 10%, rgba(31,122,107,.16), transparent 28%),
    linear-gradient(180deg, #f7f4ed 0%, #eee8dd 100%);
    color: var(--ink);
}
.block-container { padding-top: 1.1rem; max-width: 1360px; }
h1, h2, h3 { letter-spacing: 0; color: var(--ink); }
p, li, .stMarkdown, .stCaption { color: var(--muted); }
.stAppHeader { background: transparent; }

.app-hero {
    background: linear-gradient(135deg, #fffdf8 0%, #f6efe3 52%, #e5f1eb 100%);
    border: 1px solid rgba(86, 69, 45, .16);
    border-radius: 8px;
    padding: 28px 30px;
    box-shadow: var(--shadow);
    margin: 0 0 18px 0;
}
.app-kicker { color: var(--accent); font-size: 13px; font-weight: 800; margin-bottom: 8px; }
.app-hero h1 { font-size: 34px; line-height: 1.16; margin: 0; }
.app-hero p { max-width: 860px; font-size: 16px; line-height: 1.65; margin: 12px 0 0; color: #5d574f; }
.app-hero-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 18px; }
.app-stat {
    background: rgba(255,255,255,.72);
    border: 1px solid rgba(86, 69, 45, .13);
    border-radius: 8px;
    padding: 12px 14px;
}
.app-stat b { display:block; color:var(--ink); font-size:18px; }
.app-stat span { color:var(--muted); font-size:12px; }

.workflow-card, .v49-card, .v57-status-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 18px;
    box-shadow: 0 10px 30px rgba(57,45,28,.07);
}
.workflow-card h3 { margin: 0 0 8px; font-size: 18px; }
.workflow-card p { margin: 0; line-height: 1.55; }
.v49-hero, .v57-hero {
    background: linear-gradient(135deg, #20352f 0%, #1f7a6b 60%, #d18247 100%);
    padding: 22px 24px;
    border-radius: 8px;
    color: white;
    box-shadow: 0 14px 34px rgba(57,45,28,.14);
    margin-bottom: 16px;
}
.v49-hero h2, .v57-hero h3 { margin: 0; color: white; }
.v49-hero p, .v57-hero p { color: #fff6e8; margin: 8px 0 0; }
.v49-step {
    background: #fffdf8;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 13px 15px;
    margin: 8px 0;
}
.v49-step b { color: var(--accent); }
div.stButton > button, div.stDownloadButton > button {
    border-radius: 8px;
    border: 1px solid rgba(31,122,107,.22);
    font-weight: 800;
}
div.stButton > button[kind="primary"] {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
    padding: .65rem 1.1rem;
}
div.stButton > button[kind="primary"]:hover { background: #17665a; border-color:#17665a; }

/* v57 sidebar navigation polish */
section[data-testid="stSidebar"] { min-width: 305px !important; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #fbf8f0 0%, #ede5d8 100%);
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] * { color: var(--ink) !important; }
[data-testid="stSidebar"] .stRadio label { color: var(--ink) !important; }
[data-testid="stSidebar"] [role="radiogroup"] label {
    background: rgba(255,255,255,.60);
    border: 1px solid rgba(86,69,45,.12);
    border-radius: 8px;
    padding: 8px 10px;
    margin: 5px 0;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #fffdf8; border-color: rgba(31,122,107,.35); }
[data-testid="stSidebar"] [data-testid="stAlert"] {
    background: rgba(255,253,248,.72);
    border: 1px solid var(--line);
    border-radius: 8px;
}
.v57-status-card { margin-bottom: 12px; }
input, textarea, .stSelectbox div[data-baseweb="select"] > div {
    border-radius: 8px !important;
}
@media (max-width: 760px) {
    .app-hero { padding: 22px 18px; }
    .app-hero h1 { font-size: 27px; }
    .app-hero-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .recommend-grid { grid-template-columns: 1fr !important; }
}

</style>
""", unsafe_allow_html=True)

st.markdown(
    f"""
    <section class="app-hero">
      <div class="app-kicker">LOCAL CREATOR WORKBENCH · v{APP_VERSION}</div>
      <h1>{APP_NAME}</h1>
      <p>아이디어 정리부터 PNG/GIF 세트 제작, 제출 전 QC, 반려 대응, 최종 납품 패키지까지 한 화면에서 이어서 진행하는 로컬 제작 도구입니다.</p>
      <div class="app-hero-grid">
        <div class="app-stat"><b>5</b><span>간소화 작업 흐름</span></div>
        <div class="app-stat"><b>32/24</b><span>정지형·움직이는형 기준</span></div>
        <div class="app-stat"><b>QC</b><span>규격·용량·프레임 검사</span></div>
        <div class="app-stat"><b>ZIP</b><span>최종 패키지 정리</span></div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="recommend-grid" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 18px 0;">
      <div class="workflow-card">
        <h3>다음 보완 1순위</h3>
        <p>최근 작업을 자동 저장하고, 마지막으로 만들던 프로젝트를 첫 화면에서 바로 이어서 여는 기능.</p>
      </div>
      <div class="workflow-card">
        <h3>유용한 추가 기능</h3>
        <p>제출 전 체크 결과를 한 장짜리 요약 리포트로 만들고, 실패 항목만 다시 실행하는 기능.</p>
      </div>
      <div class="workflow-card">
        <h3>품질 향상 기능</h3>
        <p>PNG/GIF 미리보기에서 글자 잘림, 대비 부족, 파일명 위험을 눈에 띄게 표시하는 기능.</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ENHANCEMENT_OUTPUT = BASE_OUTPUT / "workbench_enhancements"
SNAPSHOT_PATH = ENHANCEMENT_OUTPUT / "recent_project_snapshot.json"

if not st.session_state.get("first_run_tutorial_done"):
    with st.expander("처음 실행 안내", expanded=True):
        st.markdown(
            """
            1. 왼쪽 `작업 패널`에서 큰 흐름을 고릅니다.
            2. 먼저 샘플을 만들고, 세트 구성에서 32개 PNG / 24개 GIF 후보를 정리합니다.
            3. 제출 전에는 아래 `빠른 제출 점검`에 ZIP이나 이미지를 올려 파일명, 크기, 대비, 가장자리 잘림 가능성을 확인합니다.
            4. 작업을 멈추기 전 `현재 작업 자동저장`을 누르면 다음 실행 때 이어서 불러올 수 있습니다.
            """
        )
        if st.button("처음 실행 안내 닫기", key="close_first_run_tutorial"):
            st.session_state.first_run_tutorial_done = True

with st.expander("작업 관리 · 자동저장 / 빠른 재검사 / 한 장 리포트", expanded=True):
    st.checkbox("최근 작업 자동저장 켜기", key="auto_save_enabled")
    if st.session_state.get("auto_save_enabled"):
        auto_saved_path = save_project_snapshot(st.session_state, ENHANCEMENT_OUTPUT, APP_VERSION)
        st.session_state.recent_project_snapshot_path = str(auto_saved_path)
        st.caption(f"자동저장 활성화됨: {auto_saved_path}")

    save_col, load_col, report_col = st.columns([1, 1, 1.2])
    with save_col:
        if st.button("현재 작업 자동저장", type="primary", key="save_recent_project_snapshot"):
            saved_path = save_project_snapshot(st.session_state, ENHANCEMENT_OUTPUT, APP_VERSION)
            st.session_state.recent_project_snapshot_path = str(saved_path)
            st.success(f"자동저장 완료: {saved_path}")
    with load_col:
        if SNAPSHOT_PATH.exists():
            st.caption(f"최근 저장: {SNAPSHOT_PATH.name}")
            if st.button("이어서 만들기", key="load_recent_project_snapshot"):
                snapshot = load_project_snapshot(SNAPSHOT_PATH)
                for key, value in snapshot.get("state", {}).items():
                    st.session_state[key] = value
                st.success("최근 작업을 불러왔습니다. 왼쪽 작업 흐름을 선택해 이어서 진행하세요.")
        else:
            st.caption("아직 저장된 작업이 없습니다.")
    with report_col:
        current_report = st.session_state.get("quick_submission_check_report")
        if current_report:
            st.metric("최근 빠른 점검 상태", current_report.get("overall_status", ""))
            if st.button("최종 제출용 한 장 요약 리포트 생성", key="make_one_page_summary"):
                summary_path = create_one_page_summary(current_report, ENHANCEMENT_OUTPUT, APP_VERSION)
                st.session_state.quick_submission_summary_path = str(summary_path)
                st.success(f"요약 리포트 생성 완료: {summary_path}")
        else:
            st.caption("빠른 점검을 먼저 실행하면 한 장 요약 리포트를 만들 수 있습니다.")

    st.markdown("### 빠른 제출 점검")
    st.caption("PNG/GIF/JPG/WebP 또는 ZIP을 올리면 파일명 위험, 360×360 여부, 용량, GIF 프레임, 대비, 가장자리 잘림 가능성을 빠르게 봅니다.")
    quick_upload = st.file_uploader(
        "점검할 이미지 또는 ZIP",
        type=["png", "jpg", "jpeg", "gif", "webp", "zip"],
        key="quick_submission_check_upload",
    )
    qc1, qc2 = st.columns([1, 1])
    with qc1:
        if st.button("빠른 제출 점검 실행", type="primary", key="run_quick_submission_check"):
            if not quick_upload:
                st.error("점검할 이미지나 ZIP을 먼저 올려주세요.")
            else:
                report = analyze_uploaded_package(quick_upload.name, quick_upload.getvalue())
                st.session_state.quick_submission_check_report = report
                st.success("빠른 제출 점검을 완료했습니다.")
    with qc2:
        if st.button("실패/경고 항목만 다시 보기", key="rerun_failed_submission_items"):
            previous = st.session_state.get("quick_submission_check_report")
            if previous:
                st.session_state.quick_submission_check_report = rerun_failed_items(previous)
                st.info("실패/경고 항목만 다시 요약했습니다. 실제 재검사는 파일을 다시 올려 실행하세요.")
            else:
                st.warning("먼저 빠른 제출 점검을 실행하세요.")

    quick_report = st.session_state.get("quick_submission_check_report")
    if quick_report:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("상태", quick_report.get("overall_status"))
        m2.metric("PASS", quick_report.get("pass_count"))
        m3.metric("WARN", quick_report.get("warn_count"))
        m4.metric("FAIL", quick_report.get("fail_count"))
        rows = quick_report.get("rows", [])
        if rows:
            display_rows = []
            for row in rows:
                display_rows.append({
                    "상태": row.get("status"),
                    "파일명": row.get("file_name"),
                    "형식": row.get("format"),
                    "크기": f"{row.get('width')}x{row.get('height')}" if row.get("width") else "",
                    "프레임": row.get("frames"),
                    "문제/경고": " / ".join(row.get("issues", [])) or "없음",
                })
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True, height=260)
        summary_path = st.session_state.get("quick_submission_summary_path")
        if summary_path and Path(summary_path).exists():
            st.download_button(
                "한 장 요약 리포트 다운로드",
                data=Path(summary_path).read_bytes(),
                file_name=Path(summary_path).name,
                mime="text/html",
                key="download_one_page_summary",
            )
with st.expander("전체 기능 이력 보기", expanded=False):
    st.markdown("""
    - v11~v44: 직접 창작 기반 캐릭터 제작, 품질검사, 제출 패키지, 데이터 보호, 성과 분석
    - v45~v54: 설치/실행 안정화, 이전 버전 정리, 바탕화면 아이콘, Windows 설치 오류 수정
    - v55~v56: Inno Setup 설치마법사 전환, 컴파일러 탐지 보강
    - v57: 복잡한 상단 가로 탭을 제거하고 좌측 세로 메뉴/검색형 메뉴로 전환
    - v58: 업로드된 OpenAI 키 노출 위험을 반영해 키 회전/환경변수/원문 미저장 안전모드 추가
    - v61: 정지형 생성 후 움직이는 GIF가 화면에서 바로 보이는 미리보기/카카오형 품질 개선 탭 추가
    - v62: Jinja2 템플릿 엔진을 추가해 HTML 리포트/프롬프트/모션 계획 템플릿을 분리
    - v63: 템플릿 엔진 관리 계층을 추가해 Jinja2를 주 엔진으로 고정하고 Mako는 선택 보조 엔진으로 준비
    - v64~v66: 코딩 프로그램 설명 메뉴는 더 이상 확장하지 않고, 해당 도구들은 실제 개발 과정에만 활용
    - v67: 영상 검토 기준을 반영해 정지형→움직이는형 품질, GIF 실제 미리보기, 선택 제안 반영 재생성을 강화
    - v68: 온라인/유튜브/카카오 자료를 원본 복제 없이 추상 신호로 누적하고 사용자 만족도 기반 품질 진화 엔진 추가
    - v69: 실제 그림체/모션 품질 고도화, 손그림 질감, 표정 다양성, 다크모드 대비, 다음 생성 메모리 강화
    - v70: 32개 정지형/24개 움직이는형 세트 완성도 강화, 감정·문구·포즈 중복 점검, 제출 후보 패키지 생성
    - v71: 제출 전 규격/용량/프레임 QC 강화, 파일명 정규화 계획, 제출 전 잠금 판단
    - v72: QC 결과 기반 자동 보정, 최종 제출 후보 ZIP 잠금/해제, 원본 보존형 final_export 생성
    - v73: 최종 제출 전 사용자 수동 승인 체크리스트, 32/24/GIF/저작권/공식 기준 확인 후 승인 후보 ZIP 생성
    - v80: v77~v80 최종 통합. 재생성 결과를 QC·자동보정·수동승인·마스터 납품 ZIP까지 한번에 연결
    - v90: 새 버전 설치/업그레이드 성공 후 이전 버전 폴더를 사용자 데이터 후보 백업 후 정리하는 흐름 추가
    """)

with st.sidebar:
    st.header("작업 패널")
    st.markdown(
        """
        <div class="workflow-card">
          <h3>오늘의 추천 순서</h3>
          <p>1. 제작 시작에서 샘플을 만들고<br>
          2. 세트 구성으로 32/24개를 정리한 뒤<br>
          3. QC와 최종 납품에서 제출 후보 ZIP을 확인하세요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption("세부 기능은 아래 고급 메뉴에서 검색할 수 있습니다.")
    st.warning(
        "제작 보조 도구입니다. 제출 전 카카오 공식 가이드와 저작권/상표권 위험은 직접 최종 확인해야 합니다."
    )

PAGE_LABELS = ['1 캐릭터 통합 검색/결합', '2 30일 분석', '3 표현 은행', '4 포맷 추천', '5 캐릭터 시안 생성', '6 움직이는 문구 제작', '7 제출 패키지', '8 수익 파이프라인', '9 최종 품질 검사', '10 무료 API 분석 강화', '11 저작권 방어 센터', '12 설치/실행 진단', '13 직접 창작 기준', '14 초보자/멀티소재 직접 만들기', '15 후보 갤러리/세트 선택', '16 표정/파츠 편집기', '17 채팅창 미리보기/최종검수', '18 첫 샘플 세트 제작', '19 데이터 보호/백업', '20 성장형 학습 엔진', '21 제작 마법사', '22 직접 그리기 캔버스', '23 일관성 검사/자동보정', '24 자유 드로잉 캔버스', '25 드로잉 정리/파츠추정', '26 감정/모션 확장', '27 텍스트 설명 생성', '28 누락 정보 후보/재구성', '29 반려 사유 개선', '30 제출 전 잠금 체크리스트', '31 최종 제출 패키지', '32 유튜브 참고영상/자막 분석', '33 지역·사투리 문구', '34 구체 콘셉트/멘트/모션 전략', '35 취향/경험·모션 템플릿', '36 카카오 규격/용량 검수', '37 1차 포맷/확장 전략', '38 CSV/캡처 데이터 입력', '39 카카오 스튜디오 엑셀 성과', '40 성과 대시보드/다음 방향', '41 리포트 저장', '42 선택 포맷 자동수정', '43 플랫폼별 재패키징', '44 설치형 안정화/오류 진단', '45 후보 적용/정지형 품질 진화', '46 후보 적용/정지형/움직이는형 품질 진화', '47 무료 API 수집 안전모드', '48 API 키/쿼터 장부/유료차단', '49 정지형 기반 움직이는형/제안 반영', '50 API 키 안전보관/교체', '51 카카오형 GIF 미리보기/트렌드 개선', '52 Jinja2 템플릿 리포트/프롬프트 엔진', '53 템플릿 엔진 관리/분리 구조', '54 실제 제작 품질 개선/영상 기준 반영', '55 지속 진화형 품질개선/온라인 추상 분석', '56 실제 그림체/모션 품질 고도화', '57 세트 완성도 강화/24·32 구성', '58 제출 전 규격/용량/프레임 QC', '59 제출 패키지 자동보정/잠금', '60 제출 전 최종 사용자 확인/수동 승인', '61 반려 대비/재제출 개선 루프', '62 캡처 이미지 반려 사유 입력/OCR 보조', '63 캡처 반려 사유→실제 재생성 자동 연결', '64 최종 통합 납품/재검사']

st.markdown(
    """
    <div class="v57-hero">
      <h3>간소화 워크플로우</h3>
      <p>기존 64개 세부 메뉴를 5개 큰 흐름으로 묶었습니다. 정지형은 PNG, 움직이는형은 GIF, JPG는 확인용 미리보기로 자동 분리됩니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

COMPACT_WORKFLOWS = [
    {
        "label": "1 제작 시작 · 정지형/움직이는형 미리보기",
        "old_index": 53,
        "covers": "기존 1·14·21·27·34·51·54 단계 묶음",
        "goal": "소재/문구/스타일을 입력하고 정지형 PNG, 움직이는 GIF, 확인용 JPG 미리보기를 바로 확인합니다.",
    },
    {
        "label": "2 세트 구성 · 32개/24개 품질 진화",
        "old_index": 56,
        "covers": "기존 55·56·57 단계 묶음",
        "goal": "캐릭터 identity를 유지하면서 정지형 PNG 32개와 움직이는 GIF 24개 세트를 만듭니다.",
    },
    {
        "label": "3 검사 · 자동보정 · 제출 전 승인",
        "old_index": 58,
        "covers": "기존 58·59·60 단계 묶음",
        "goal": "규격/용량/프레임을 검사하고 자동보정 후 사용자가 최종 승인할 수 있게 합니다.",
    },
    {
        "label": "4 반려 대응 · 캡처/OCR · 재생성",
        "old_index": 62,
        "covers": "기존 61·62·63 단계 묶음",
        "goal": "반려 사유 텍스트나 캡처를 받아 개선안과 실제 재생성 결과로 연결합니다.",
    },
    {
        "label": "5 최종 납품 · 백업/리포트/재검사",
        "old_index": 63,
        "covers": "기존 64 및 최종 리포트/manifest/ZIP 묶음",
        "goal": "최종 PNG/GIF 제출 후보 ZIP, JPG 미리보기, 체크리스트, 리포트, 데이터 보호 상태와 이전 버전 정리를 한 번에 확인합니다.",
    },
]

with st.sidebar:
    st.markdown("### ✅ 간소화 작업 흐름")
    compact_labels = [item["label"] for item in COMPACT_WORKFLOWS]
    compact_default = st.session_state.get("v86_compact_workflow_label", compact_labels[0])
    compact_index = compact_labels.index(compact_default) if compact_default in compact_labels else 0
    selected_compact_label = st.radio(
        "큰 흐름 선택",
        compact_labels,
        index=compact_index,
        key="v86_compact_workflow_radio",
        label_visibility="collapsed",
    )
    st.session_state["v86_compact_workflow_label"] = selected_compact_label
    compact_item = COMPACT_WORKFLOWS[compact_labels.index(selected_compact_label)]
    selected_page_index = compact_item["old_index"]
    selected_page_label = PAGE_LABELS[selected_page_index]

    st.info(compact_item["covers"])
    st.caption(compact_item["goal"])

    with st.expander("고급 세부 메뉴 보기", expanded=False):
        st.caption("문제가 있을 때만 기존 세부 기능을 직접 선택하세요.")
        nav_query = st.text_input("세부 메뉴 검색", placeholder="예: QC, 반려, GIF, API", key="v86_advanced_nav_search")
        if nav_query.strip():
            filtered_pages = [label for label in PAGE_LABELS if nav_query.strip().lower() in label.lower()]
            if not filtered_pages:
                st.warning("검색 결과가 없습니다. 전체 세부 메뉴를 표시합니다.")
                filtered_pages = PAGE_LABELS
        else:
            filtered_pages = PAGE_LABELS
        advanced_label = st.selectbox("세부 기능 직접 선택", filtered_pages, index=0, key="v86_advanced_page_select")
        if st.button("선택한 세부 기능으로 이동", key="v86_go_advanced_page"):
            st.session_state["v86_force_advanced_label"] = advanced_label
            selected_page_label = advanced_label
            selected_page_index = PAGE_LABELS.index(advanced_label)

    st.markdown("---")
    st.caption(f"실행 내부 단계: {selected_page_index + 1} / {len(PAGE_LABELS)}")

if st.session_state.get("v86_force_advanced_label"):
    forced_label = st.session_state.get("v86_force_advanced_label")
    if forced_label in PAGE_LABELS:
        selected_page_label = forced_label
        selected_page_index = PAGE_LABELS.index(forced_label)

st.markdown(
    f"""
    <div class="v57-status-card">
      <b>현재 간소화 흐름</b> · {selected_compact_label}<br>
      <span style="color:#64748b;">내부 실행 기능: {selected_page_label}</span><br>
      <span style="color:#64748b;">단계는 줄이고, 내부에서는 필요한 하위 기능을 묶어서 실행하는 구조입니다.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if selected_page_index == 0:
    st.subheader("캐릭터 통합 검색창 / 복합 소재 결합")
    st.write("단어/문장 또는 직접 만든 이미지/사진 3~5종을 넣으면, 그대로 합성하지 않고 독창 캐릭터 후보와 위험 요소를 분석합니다.")

    col1, col2 = st.columns([1.2, 0.8])
    with col1:
        concept_input = st.text_area(
            "캐릭터 키워드/문장 또는 복수 소재",
            value="보리와 쌀, 예의 바른 직장인 캐릭터, 문구와 같이 움직이는 이모티콘",
            height=120,
            help="예: 보리와 쌀 / 감자, 고구마 / 메모지+돌멩이 / 직접 찍은 사물 3~5장 + 단어 설명",
        )
        uploaded_files = st.file_uploader(
            "직접 만든 이미지/사진 첨부 · 3~5종 권장",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            help="기존 캐릭터를 저장·복제하는 용도가 아니라, 사용자가 직접 만든 이미지나 직접 촬영한 사진에서 색감/형태 힌트만 추출합니다.",
        )
        analyze_btn = st.button("캐릭터/복합 소재 분석 실행", type="primary")

    with col2:
        st.markdown("### 검사 원칙")
        st.markdown(
            """
            - 기존 캐릭터 모방 방향 차단  
            - 이미지 3~5종 색감/형태 힌트 분석  
            - 보리와 쌀 / 감자, 고구마 같은 복수 소재 결합  
            - 독창적 세계관/말투/움직임 추천  
            - AI 완성본 제출 위험 경고  
            - 포맷별 제작 가능성 점검
            """
        )

    if analyze_btn:
        analyzer = KeywordAnalyzer()
        profile = analyzer.analyze(concept_input)
        concepts = ConceptExpander().expand(profile, count=10)
        originality = OriginalityScorer().score(concept_input, base_count=len(profile.bases), has_worldview=True)
        st.session_state.profile = profile.to_dict()
        st.session_state.concepts = asdict_list(concepts)
        st.session_state.originality = originality

        mixer = MultiSourceMixer()
        material_tokens = mixer.parse_materials(concept_input)
        st.session_state.material_tokens = asdict_list(material_tokens)

        image_profiles = []
        uploaded_paths = []
        if uploaded_files:
            image_analyzer = ImageFeatureAnalyzer()
            for idx, uploaded in enumerate(uploaded_files[:5], start=1):
                suffix = Path(uploaded.name).suffix or ".png"
                temp_path = Path(tempfile.gettempdir()) / f"uploaded_character_mix_{idx}{suffix}"
                temp_path.write_bytes(uploaded.getvalue())
                uploaded_paths.append(str(temp_path))
                image_profiles.append(image_analyzer.analyze(temp_path))
            st.session_state.image_profiles = asdict_list(image_profiles)
            st.session_state.image_profile = st.session_state.image_profiles[0] if st.session_state.image_profiles else None
            st.session_state.uploaded_image_paths = uploaded_paths
        else:
            st.session_state.image_profiles = []
            st.session_state.image_profile = None
            st.session_state.uploaded_image_paths = []

        multi_image_blend = mixer.blend_images(image_profiles)
        blend_concepts = mixer.build_blend_concepts(material_tokens, profile, multi_image_blend, count=10)
        st.session_state.multi_image_blend = multi_image_blend.to_dict()
        st.session_state.blend_concepts = asdict_list(blend_concepts)

    if st.session_state.profile:
        st.markdown("### 분석 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("저작권/유사 위험도", st.session_state.profile["risk_score"])
        c2.metric("독창성 점수", st.session_state.originality["originality_score"])
        c3.metric("분석된 본체 후보", len(st.session_state.profile["bases"]))

        if st.session_state.profile["risk_findings"]:
            st.error("유사/정책 위험 키워드가 감지되었습니다.")
            st.dataframe(pd.DataFrame(st.session_state.profile["risk_findings"]), use_container_width=True)
        else:
            st.success("1차 키워드 검사에서 고위험 모방 키워드는 발견되지 않았습니다.")

        st.markdown("### 독창 캐릭터 후보")
        st.dataframe(pd.DataFrame(st.session_state.concepts), use_container_width=True)

        if st.session_state.material_tokens:
            st.markdown("### 복수 단어/소재 분석")
            st.dataframe(pd.DataFrame(st.session_state.material_tokens), use_container_width=True)

        if st.session_state.multi_image_blend:
            st.markdown("### 이미지 3~5종 결합 분석")
            if st.session_state.multi_image_blend.get("warnings"):
                for warning in st.session_state.multi_image_blend["warnings"]:
                    st.warning(warning)
            st.json(st.session_state.multi_image_blend)

        if st.session_state.image_profiles:
            st.markdown("### 첨부 이미지별 분석")
            st.dataframe(pd.DataFrame(st.session_state.image_profiles), use_container_width=True)

        if st.session_state.blend_concepts:
            st.markdown("### 복합 소재 독창 캐릭터 후보")
            st.dataframe(pd.DataFrame(st.session_state.blend_concepts), use_container_width=True)

if selected_page_index == 1:
    st.subheader("최근 30일 트렌드 분석")
    st.write("무료 API 키가 없어도 수동 입력으로 먼저 분석할 수 있고, API 키가 있으면 YouTube/Naver 데이터 수집을 시도할 수 있습니다.")

    mode = st.radio("분석 모드", ["수동 입력 분석", "YouTube API 수집", "네이버 데이터랩 수집"], horizontal=True, key="v48_trend_mode_radio")

    if mode == "수동 입력 분석":
        raw_trends = st.text_area(
            "최근 30일간 본 영상 제목/댓글/검색어/아이디어를 붙여넣기",
            value="퇴근 월요병 번아웃 넵 확인했습니다 죄송합니다 직장인 공감 피곤 살려주세요 오늘도 버팁니다 회사생활 업무 메모지 구겨짐",
            height=180,
        )
        if st.button("수동 트렌드 분석"):
            result = ManualTrendAnalyzer().analyze(raw_trends)
            st.session_state.trend_result = result.to_dict()

    elif mode == "YouTube API 수집":
        st.info("YouTube Data API 키가 필요합니다. 키는 현재 세션에서만 사용하고 파일로 저장하지 않습니다.")
        yt_key = st.text_input("YouTube API Key", type="password")
        query = st.text_input("검색어", value="직장인 공감 이모티콘")
        max_results = st.slider("수집 영상 수", 1, 20, 5)
        if st.button("YouTube 최근 30일 수집"):
            try:
                items = YoutubeCollector(yt_key).search_recent(query, max_results=max_results, days=30)
                st.session_state.youtube_items = [x.to_dict() for x in items]
                combined = " ".join(item.title for item in items)
                st.session_state.trend_result = ManualTrendAnalyzer().analyze(combined).to_dict()
                st.success(f"영상 {len(items)}개 수집 완료")
            except Exception as exc:
                st.error(f"YouTube 수집 실패: {exc}")

        if st.session_state.get("youtube_items"):
            st.dataframe(pd.DataFrame(st.session_state.youtube_items), use_container_width=True)

    else:
        st.info("네이버 데이터랩 API Client ID/Secret이 필요합니다. 키는 현재 세션에서만 사용합니다.")
        naver_id = st.text_input("Naver Client ID", type="password")
        naver_secret = st.text_input("Naver Client Secret", type="password")
        group_name = st.text_input("키워드 그룹명", value="직장인 이모티콘")
        keywords = st.text_input("키워드 콤마 구분", value="퇴근,월요병,직장인,넵,확인했습니다")
        if st.button("네이버 데이터랩 30일 수집"):
            try:
                points = NaverDatalabCollector(naver_id, naver_secret).fetch_keyword_trend(
                    group_name, [k.strip() for k in keywords.split(",") if k.strip()], days=30
                )
                st.session_state.naver_points = [p.to_dict() for p in points]
                st.session_state.trend_result = ManualTrendAnalyzer().analyze(keywords).to_dict()
                st.success(f"데이터 포인트 {len(points)}개 수집 완료")
            except Exception as exc:
                st.error(f"네이버 데이터랩 수집 실패: {exc}")

        if st.session_state.get("naver_points"):
            st.line_chart(pd.DataFrame(st.session_state.naver_points).set_index("period"))

    if st.session_state.trend_result:
        st.markdown("### 30일 분석 결과")
        st.write(st.session_state.trend_result["summary"])
        st.dataframe(pd.DataFrame(st.session_state.trend_result["top_keywords"], columns=["keyword", "count"]), use_container_width=True)
        st.write("추천 타깃:", ", ".join(st.session_state.trend_result["suggested_targets"]))
        st.write("추천 문구:", ", ".join(st.session_state.trend_result["suggested_phrases"]))
        st.write("추천 포맷:", ", ".join(FORMAT_LABELS.get(x, x) for x in st.session_state.trend_result["suggested_formats"]))
        if st.button("v48 추천 문구를 표현 은행에 적용", key="v48_apply_trend_to_expression_bank"):
            phrases = list(st.session_state.trend_result.get("suggested_phrases", []))
            phrases += [k for k, _ in st.session_state.trend_result.get("top_keywords", [])[:12] if isinstance(k, str) and len(k) <= 12]
            phrases = [p for i, p in enumerate(phrases) if p and p not in phrases[:i]]
            st.session_state.expressions = [
                {"no": idx + 1, "category": "트렌드", "phrase": phrase, "usage_score": max(60, 92 - idx), "emotion": "트렌드", "format_hint": "static_text", "motion_hint": "정지형에서도 표정/포즈 차이를 주어 적용"}
                for idx, phrase in enumerate((phrases or ["넵", "확인했습니다", "감사합니다"])[:32])
            ]
            st.session_state.active_generation_profile = {"source": "v48_trend_apply", "phrases": phrases[:32]}
            st.success(f"추천 문구 {len(st.session_state.expressions)}개를 표현 은행에 적용했습니다. 이제 15번 후보 갤러리/세트 선택에서 바로 사용할 수 있습니다.")

if selected_page_index == 2:
    st.subheader("캐릭터 1종 표현 은행")
    st.write("캐릭터 1종당 후보 표현을 80개 이상 만들고, 최종 제출용은 포맷에 맞게 선별합니다.")
    concept_name = st.text_input("캐릭터명/콘셉트명", value=(st.session_state.concepts[0]["name"] if st.session_state.concepts else "업무에 눌린 메모지"))
    expression_count = st.slider("표현 후보 개수", 40, 120, 80, step=10)
    if st.button("표현 은행 생성", type="primary"):
        expressions = ExpressionGenerator().generate(concept_name, expression_count)
        st.session_state.expressions = asdict_list(expressions)
        st.session_state.balance = ExpressionBalanceChecker().check(expressions)

    if st.session_state.expressions:
        st.metric("표현 후보", len(st.session_state.expressions))
        st.json(st.session_state.balance)
        st.dataframe(pd.DataFrame(st.session_state.expressions), use_container_width=True)

if selected_page_index == 3:
    st.subheader("다중 포맷 추천")
    if not st.session_state.expressions:
        st.warning("먼저 표현 은행을 생성하세요.")
    else:
        full_concept_text = " ".join([
            json.dumps(st.session_state.profile, ensure_ascii=False) if st.session_state.profile else "",
            json.dumps(st.session_state.trend_result, ensure_ascii=False) if st.session_state.trend_result else "",
        ])
        if st.button("포맷별 적합도 계산", type="primary"):
            # dict를 ExpressionItem처럼 쓰지 않고 필요한 필드만 가진 간단 객체로 변환
            from modules.expression_bank.expression_generator import ExpressionItem
            expr_objs = [ExpressionItem(**item) for item in st.session_state.expressions]
            scores = FormatRecommender().score(full_concept_text, expr_objs)
            st.session_state.format_scores = asdict_list(scores)
        if st.session_state.format_scores:
            st.dataframe(pd.DataFrame(st.session_state.format_scores), use_container_width=True)
            top = st.session_state.format_scores[0]
            st.success(f"1순위 추천: {top['label']} / 적합도 {top['score']}점")
            st.markdown(
                """
                **운영 방향**  
                1순위 포맷으로 첫 세트를 제작하고, 예비 표현 10~20개를 남깁니다.  
                심사 결과와 시장 반응을 기록한 뒤 2순위 포맷으로 확장합니다.
                """
            )

if selected_page_index == 4:
    st.subheader("360×360 독창 캐릭터 시안 생성")
    st.write("복수 단어/이미지 분석 결과를 바탕으로 기존 사진을 직접 합성하지 않고, 단순 도형 기반의 새 캐릭터 PNG 시안을 만듭니다.")

    proto_count = st.slider("생성할 캐릭터 시안 수", 3, 10, 6)
    pack_count = st.slider("선택 시안으로 만들 표현 PNG 수", 4, 24, 12, step=2)
    st.caption("주의: 이 기능은 제출용 완성 이미지 보장이 아니라 직접 창작 방향을 빠르게 확인하는 초안 생성 기능입니다.")

    if st.button("360×360 캐릭터 시안 생성", type="primary"):
        builder = CharacterPrototypeBuilder()
        materials = []
        for item in st.session_state.material_tokens or []:
            materials.append(type("MaterialObj", (), item))
        # dataclass가 아니어도 name/category/role_hint/motion_hint/phrase_hint 속성만 있으면 처리 가능
        image_blend = None
        if st.session_state.multi_image_blend:
            image_blend = type("ImageBlendObj", (), st.session_state.multi_image_blend)
        blend_concepts = st.session_state.blend_concepts or []
        specs = builder.build_specs(materials, image_blend, blend_concepts, count=proto_count)
        out_dir = BASE_OUTPUT / "prototypes"
        results = builder.render_prototypes(specs, out_dir)
        st.session_state.prototype_specs = [spec.to_dict() for spec in specs]
        st.session_state.prototype_results = [r.to_dict() for r in results]
        st.success(f"캐릭터 시안 {len(results)}개 생성 완료")

    if st.session_state.prototype_results:
        st.markdown("### 생성된 캐릭터 시안")
        cols = st.columns(3)
        for idx, result in enumerate(st.session_state.prototype_results):
            with cols[idx % 3]:
                st.image(result["file_path"], caption=result["preview_label"], width=220)
                st.caption(result["spec"].get("motion_hint", ""))

        labels = [r["preview_label"] for r in st.session_state.prototype_results]
        selected_label = st.selectbox("표현 세트를 만들 시안 선택", labels, index=min(st.session_state.selected_prototype_index, len(labels)-1))
        selected_idx = labels.index(selected_label)
        st.session_state.selected_prototype_index = selected_idx
        st.json(st.session_state.prototype_results[selected_idx]["spec"])

        if st.button("선택 시안으로 표현 PNG 세트 생성", type="primary"):
            builder = CharacterPrototypeBuilder()
            spec = PrototypeSpec(**st.session_state.prototype_results[selected_idx]["spec"])
            expr_dir = BASE_OUTPUT / "prototype_expression_pack"
            files = builder.render_expression_pack(spec, st.session_state.expressions, expr_dir, count=pack_count)
            zip_path = builder.zip_files(files, BASE_OUTPUT / "prototype_expression_pack.zip")
            st.session_state.expression_pack_files = files
            st.session_state.expression_pack_zip = str(zip_path)
            st.success(f"표현 PNG {len(files)}개 생성 완료")

    if st.session_state.expression_pack_files:
        st.markdown("### 표현 PNG 미리보기")
        cols = st.columns(4)
        for idx, fp in enumerate(st.session_state.expression_pack_files[:12]):
            with cols[idx % 4]:
                st.image(fp, width=160)
        if st.session_state.expression_pack_zip and Path(st.session_state.expression_pack_zip).exists():
            st.download_button(
                "표현 PNG ZIP 다운로드",
                data=Path(st.session_state.expression_pack_zip).read_bytes(),
                file_name="prototype_expression_pack.zip",
                mime="application/zip",
            )


if selected_page_index == 5:
    st.subheader("움직이는 문구 결합형 GIF 샘플 제작")
    st.write("직접 만든 PNG/JPG 캐릭터를 넣고, 문구와 캐릭터가 자연스럽게 같이 움직이는 샘플 GIF를 만듭니다.")
    uploaded_for_gif = st.file_uploader("GIF 제작용 캐릭터 이미지", type=["png", "jpg", "jpeg", "webp"], key="gif_upload")
    phrase = st.text_input("문구", value="확인했습니다")
    text_motion = st.selectbox("문구 움직임", list(TEXT_MOTION_PRESETS.keys()))
    char_motion = st.selectbox("캐릭터 움직임", ["통통 튐", "꾸벅", "작아짐", "부들부들 흔들림", "축 처짐"])
    if st.button("GIF 샘플 생성", type="primary"):
        if not uploaded_for_gif:
            st.error("캐릭터 이미지를 먼저 첨부하세요.")
        else:
            suffix = Path(uploaded_for_gif.name).suffix or ".png"
            temp_path = Path(tempfile.gettempdir()) / f"gif_base_character{suffix}"
            temp_path.write_bytes(uploaded_for_gif.getvalue())
            out_path = BASE_OUTPUT / "animated_text_sample.gif"
            try:
                AnimatedTextFrameBuilder().build_gif(temp_path, phrase, out_path, text_motion=text_motion, character_motion=char_motion)
                st.session_state.last_gif = str(out_path)
                st.success("GIF 샘플 생성 완료")
            except Exception as exc:
                st.error(f"GIF 생성 실패: {exc}")
    if st.session_state.last_gif and Path(st.session_state.last_gif).exists():
        st.image(st.session_state.last_gif, caption="움직이는 문구 결합형 샘플", width=260)
        st.download_button("GIF 다운로드", data=Path(st.session_state.last_gif).read_bytes(), file_name="animated_text_sample.gif", mime="image/gif")

if selected_page_index == 6:
    st.subheader("제출용 패키지 자동 정리")
    st.write("선택한 360×360 캐릭터 시안과 표현 은행을 포맷별 제출 준비 폴더로 정리합니다. 01.png/01.gif 같은 파일명, manifest, HTML 체크리스트, ZIP을 자동 생성합니다.")

    if not st.session_state.prototype_results:
        st.warning("먼저 5번 탭에서 캐릭터 시안을 생성하세요.")
    else:
        labels = [r["preview_label"] for r in st.session_state.prototype_results]
        selected_label = st.selectbox("패키지로 만들 캐릭터 시안", labels, key="submission_proto_select")
        selected_idx = labels.index(selected_label)
        submission_project_name = st.text_input("제출 패키지 프로젝트명", value="kakao_emoticon_submission_v5", key="v48_submission_project_name")
        format_options = {
            "static": "멈춰있는 이모티콘",
            "static_text": "문구 결합형 멈춰있는 이모티콘",
            "animated": "움직이는 이모티콘",
            "animated_text": "움직이는 문구 결합형 이모티콘",
            "big": "큰 이모티콘",
        }
        format_key = st.selectbox("제작 포맷", list(format_options.keys()), format_func=lambda k: format_options[k], index=1, key="v48_submission_format_key")
        default_count = 32 if format_key in ["static", "static_text"] else 24 if format_key in ["animated", "animated_text"] else 16
        target_count = st.slider("생성 수량", 4, 40, default_count, step=1, key="v48_submission_target_count")
        st.caption("수량/용량/형식 기준은 내부 기획 기준입니다. 카카오 공식 스튜디오의 최신 제출 기준은 제출 직전 다시 확인해야 합니다.")

        if st.button("제출 준비 패키지 생성", type="primary"):
            try:
                spec = PrototypeSpec(**st.session_state.prototype_results[selected_idx]["spec"])
                result = SubmissionPackageBuilder().build(
                    spec=spec,
                    expressions=st.session_state.expressions,
                    output_root=BASE_OUTPUT / "submission_packages",
                    project_name=submission_project_name,
                    format_key=format_key,
                    target_count=target_count,
                )
                st.session_state.submission_result = result.to_dict()
                st.success(f"제출 준비 패키지 생성 완료: {result.created_count}개")
            except Exception as exc:
                st.error(f"제출 패키지 생성 실패: {exc}")

    if st.session_state.submission_result:
        result = st.session_state.submission_result
        c1, c2, c3 = st.columns(3)
        c1.metric("포맷", result["format_label"])
        c2.metric("생성 수량", result["created_count"])
        c3.metric("내부 기준 수량", result["expected_count"])
        if result.get("warnings"):
            for warning in result["warnings"]:
                st.warning(warning)
        st.markdown("### 파일 검사 결과")
        st.dataframe(pd.DataFrame(result["file_checks"]), use_container_width=True)
        zip_path = Path(result["zip_path"])
        checklist_path = Path(result["checklist_path"])
        if zip_path.exists():
            st.download_button("제출 준비 패키지 ZIP 다운로드", data=zip_path.read_bytes(), file_name=zip_path.name, mime="application/zip")
        if checklist_path.exists():
            st.download_button("제출 체크리스트 HTML 다운로드", data=checklist_path.read_bytes(), file_name="submission_checklist.html", mime="text/html")

if selected_page_index == 7:
    st.subheader("수익 파이프라인 / 심사·판매 기록")
    st.write("캐릭터 1종을 어떤 포맷으로 먼저 제출하고, 어떤 포맷/시리즈로 확장할지 30/60/90일 운영 계획으로 정리합니다.")

    suggested_name = "새 캐릭터"
    if st.session_state.blend_concepts:
        suggested_name = st.session_state.blend_concepts[0].get("name", suggested_name)
    elif st.session_state.concepts:
        suggested_name = st.session_state.concepts[0].get("name", suggested_name)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        pipeline_character_name = st.text_input("파이프라인 캐릭터명", value=suggested_name)
        monthly_submissions = st.slider("월 목표 제출 후보 수", 1, 4, 1)
        st.caption("목표 수가 높을수록 빠른 반복 제작 루트로 계산하지만, 승인/수익을 보장하지 않습니다.")
        if st.button("수익 파이프라인 생성", type="primary"):
            plan = ProfitPipelinePlanner().build(
                character_name=pipeline_character_name,
                profile=st.session_state.profile,
                trend_result=st.session_state.trend_result,
                format_scores=st.session_state.format_scores,
                expressions=st.session_state.expressions,
                desired_monthly_submissions=monthly_submissions,
            )
            st.session_state.pipeline_plan = plan.to_dict()
            plan_path = BASE_OUTPUT / "profit_pipeline_plan.json"
            plan_path.write_text(json.dumps(st.session_state.pipeline_plan, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success("수익 파이프라인 생성 완료")

    with col_b:
        st.markdown("### 파이프라인 판단 기준")
        st.markdown(
            """
            - 1차: 제작 효율과 실사용성이 높은 포맷  
            - 2차: 문구/움직임/큰 리액션 중 강점 확장  
            - 3차: 심사 결과와 반응을 기반으로 시리즈화  
            - 반려 시: 사유를 기록하고 표현 은행/포맷을 재조정  
            """
        )

    if st.session_state.pipeline_plan:
        plan = st.session_state.pipeline_plan
        st.markdown("### 파이프라인 요약")
        st.success(plan.get("summary", ""))
        c1, c2, c3 = st.columns(3)
        c1.metric("1차 포맷", plan.get("primary_format", "-"))
        c2.metric("2차 포맷", plan.get("secondary_format", "-"))
        c3.metric("추천 키워드", len(plan.get("top_keywords", [])))
        st.write("**포지셔닝:**", plan.get("positioning", ""))
        st.write("**우선 문구:**", ", ".join(plan.get("priority_phrases", [])))

        st.markdown("### 30/60/90일 제작 단계")
        st.dataframe(pd.DataFrame(plan.get("steps", [])), use_container_width=True)

        st.markdown("### 시리즈 확장 후보")
        st.dataframe(pd.DataFrame(plan.get("series_candidates", [])), use_container_width=True)

        st.markdown("### KPI/기록 템플릿")
        st.json(plan.get("kpi_template", {}))
        plan_path = BASE_OUTPUT / "profit_pipeline_plan.json"
        if plan_path.exists():
            st.download_button("수익 파이프라인 JSON 다운로드", data=plan_path.read_bytes(), file_name="profit_pipeline_plan.json", mime="application/json")

    st.divider()
    st.markdown("## 심사/판매 기록")
    tracker = SubmissionTracker(BASE_OUTPUT / "submission_history.json")
    current_history = tracker.load()
    st.session_state.submission_history = current_history

    with st.form("submission_record_form"):
        r1, r2, r3 = st.columns(3)
        with r1:
            rec_character = st.text_input("기록 캐릭터명", value=pipeline_character_name)
            rec_status = st.selectbox("상태", ["준비", "제출", "승인", "반려", "수정 후 재제출", "출시"], key="v48_submission_record_status")
        with r2:
            rec_format = st.text_input("포맷", value=(st.session_state.pipeline_plan or {}).get("primary_format", "문구 결합형 멈춰있는 이모티콘"))
            rec_submitted_at = st.text_input("제출일", value="")
        with r3:
            rec_result_at = st.text_input("결과일", value="")
            st.write("")
            save_record = st.form_submit_button("기록 추가")
        rec_rejection = st.text_area("반려/수정 사유", value="", height=80)
        rec_revision = st.text_area("수정 메모", value="", height=80)
        rec_sales = st.text_area("판매/정산/반응 메모", value="", height=80)

        if save_record:
            record = tracker.make_record(
                character_name=rec_character,
                format_label=rec_format,
                status=rec_status,
                submitted_at=rec_submitted_at,
                result_at=rec_result_at,
                rejection_reason=rec_rejection,
                revision_note=rec_revision,
                sales_note=rec_sales,
            )
            records = tracker.add(record)
            st.session_state.submission_history = records
            st.success(f"기록 추가 완료 · 다음 행동: {record.next_action}")

    records = st.session_state.submission_history
    if records:
        stats = tracker.stats(records)
        s1, s2, s3 = st.columns(3)
        s1.metric("총 기록", stats["총 기록"])
        s2.metric("승인/출시", stats["승인/출시 기록"])
        s3.metric("반려", stats["반려 기록"])
        st.dataframe(pd.DataFrame(records), use_container_width=True)
        csv_path = tracker.export_csv(BASE_OUTPUT / "submission_history.csv", records)
        st.session_state.submission_csv_path = str(csv_path)
        st.download_button("심사/판매 기록 CSV 다운로드", data=Path(csv_path).read_bytes(), file_name="submission_history.csv", mime="text/csv")
    else:
        st.info("아직 심사/판매 기록이 없습니다. 제출 준비가 끝나면 이곳에 상태와 사유를 누적하세요.")


if selected_page_index == 8:
    st.subheader("최종 제출 전 품질 검사")
    st.write("제출 패키지 폴더를 기준으로 크기, 용량, 투명 배경, 글자 가독성, 잘림 위험, 표현 중복, 감정 구성 균형, 움직이는 문구 동기화 상태를 검사합니다.")

    quality_package_dir = None
    quality_format_key = "static_text"
    if st.session_state.submission_result:
        quality_package_dir = st.session_state.submission_result.get("package_dir")
        quality_format_key = st.session_state.submission_result.get("format_key", "static_text")
        st.success("최근 생성한 제출 패키지를 자동으로 불러왔습니다.")
        st.code(quality_package_dir)
    else:
        st.warning("먼저 7번 탭에서 제출 패키지를 생성하면 자동 검사가 쉬워집니다.")
        quality_package_dir = st.text_input("직접 검사할 패키지 폴더 경로", value="outputs/submission_packages")
        quality_format_key = st.selectbox("검사 포맷", ["static", "static_text", "animated", "animated_text", "big"], format_func=lambda k: FORMAT_LABELS.get(k, k), index=1)

    st.markdown("### 검사 기준")
    st.markdown("""
    - **기술 품질:** 360×360 크기, 확장자, 용량, 투명도, 여백/잘림 위험  
    - **가독성:** 문구 길이, 작은 화면에서 읽기 쉬운지  
    - **표현 구성:** 답장형/감정형/감사·사과형 비율  
    - **중복 위험:** 비슷한 이미지와 비슷한 문구 반복 여부  
    - **움직임 동기화:** GIF 프레임 수, 움직임 변화량, 문구 길이와 동작 적합성
    """)

    if st.button("최종 품질 검사 실행", type="primary"):
        try:
            review = SubmissionQualityReviewer().review(
                package_dir=quality_package_dir,
                format_key=quality_format_key,
                expressions=st.session_state.expressions,
            )
            st.session_state.quality_review = review.to_dict()
            st.success("최종 품질 검사 완료")
        except Exception as exc:
            st.error(f"품질 검사 실패: {exc}")

    if st.session_state.quality_review:
        review = st.session_state.quality_review
        c1, c2, c3 = st.columns(3)
        c1.metric("최종 품질 점수", review["overall_score"])
        c2.metric("판정", review["final_status"])
        c3.metric("검사 파일", review["actual_count"])
        st.write(review["summary"])
        if review.get("warnings"):
            for warning in review["warnings"]:
                st.warning(warning)
        st.markdown("### 파일별 검사 결과")
        st.dataframe(pd.DataFrame(review["file_checks"]), use_container_width=True)
        st.markdown("### 표현 중복/유사 위험")
        if review["duplicate_findings"]:
            st.dataframe(pd.DataFrame(review["duplicate_findings"]), use_container_width=True)
        else:
            st.success("표현 중복/유사 위험이 크게 감지되지 않았습니다.")
        st.markdown("### 표현 구성 균형")
        st.json(review["expression_balance"])
        st.markdown("### 움직이는 문구 동기화 검사")
        if review["sync_findings"]:
            st.dataframe(pd.DataFrame(review["sync_findings"]), use_container_width=True)
        else:
            st.info("정지형 포맷이거나 동기화 검사 대상이 아닙니다.")
        html_path = Path(review["html_path"])
        json_path = Path(review["json_path"])
        if html_path.exists():
            st.download_button("최종 품질 리뷰 HTML 다운로드", data=html_path.read_bytes(), file_name="final_submission_review.html", mime="text/html")
        if json_path.exists():
            st.download_button("최종 품질 리뷰 JSON 다운로드", data=json_path.read_bytes(), file_name="final_submission_review.json", mime="application/json")



if selected_page_index == 9:
    st.subheader("무료 API 기반 30일 트렌드 분석 강화")
    st.write("YouTube, 네이버 데이터랩, KIPRIS/상표 위험 체크를 한 화면에서 묶어 최근 30일 기준 제작 방향을 분석합니다. API 키가 없으면 수동 입력과 오프라인 명칭 위험 체크만으로도 사용할 수 있습니다.")

    st.markdown("### 분석 키워드")
    default_keywords = "직장인 공감, 퇴근, 월요병, 넵, 확인했습니다, 죄송합니다, 카톡 이모티콘"
    keyword_text = st.text_area("최근 30일 분석 키워드 · 쉼표/줄바꿈 구분", value=default_keywords, height=90)
    manual_text_v7 = st.text_area(
        "수동 보강 데이터 · 최근 30일 영상 제목/댓글/검색어/아이디어 붙여넣기",
        value="퇴근 월요병 번아웃 넵 확인했습니다 죄송합니다 직장인 공감 피곤 살려주세요 문구와 같이 움직이는 이모티콘",
        height=120,
    )
    days_v7 = st.slider("분석 기간", 7, 60, 30)

    st.markdown("### 무료 API 키 입력 · 현재 세션에서만 사용")
    c1, c2, c3 = st.columns(3)
    with c1:
        yt_key_v7 = st.text_input("YouTube Data API Key", type="password", key="yt_key_v7")
        yt_max_v7 = st.slider("키워드당 YouTube 영상 수", 1, 10, 3)
        yt_comments_v7 = st.checkbox("상위 댓글도 일부 분석", value=False)
        yt_comment_count_v7 = st.slider("영상당 댓글 수", 1, 5, 2, disabled=not yt_comments_v7)
    with c2:
        naver_id_v7 = st.text_input("Naver DataLab Client ID", type="password", key="naver_id_v7")
        naver_secret_v7 = st.text_input("Naver DataLab Client Secret", type="password", key="naver_secret_v7")
        st.caption("네이버 데이터랩은 상대 검색량 흐름을 보기 위한 용도입니다.")
    with c3:
        kipris_key_v7 = st.text_input("KIPRIS Service Key · 선택", type="password", key="kipris_key_v7")
        kipris_url_v7 = st.text_input("KIPRIS API URL · 선택", value="", key="kipris_url_v7")
        st.caption("URL/권한이 없으면 오프라인 위험 키워드 검사만 수행합니다.")

    clean_keyword_preview = [x.strip() for x in keyword_text.replace("\n", ",").split(",") if x.strip()]
    st.markdown("### YouTube quota 사용량 추정")
    st.json(YoutubeCollector.estimate_quota(len(clean_keyword_preview), yt_max_v7, yt_comments_v7))

    if st.button("v7 무료 API 30일 통합 분석 실행", type="primary"):
        try:
            report = ThirtyDayTrendEngine().run(
                keywords=clean_keyword_preview,
                manual_text=manual_text_v7,
                days=days_v7,
                youtube_api_key=yt_key_v7,
                youtube_max_per_keyword=yt_max_v7,
                include_youtube_comments=yt_comments_v7,
                comments_per_video=yt_comment_count_v7,
                naver_client_id=naver_id_v7,
                naver_client_secret=naver_secret_v7,
                kipris_service_key=kipris_key_v7,
                kipris_endpoint_url=kipris_url_v7,
                trademark_keywords=clean_keyword_preview,
                output_dir=BASE_OUTPUT / "trend_reports",
            )
            st.session_state.api_trend_report = report.to_dict()
            # 기존 포맷 추천/수익 파이프라인에서도 재사용되도록 요약값을 trend_result에 반영합니다.
            st.session_state.trend_result = {
                "top_keywords": report.top_keywords,
                "suggested_targets": report.recommended_characters,
                "suggested_phrases": report.recommended_phrases,
                "suggested_formats": report.recommended_formats,
                "summary": f"최근 {report.days}일 분석 기준 핵심 키워드는 " + ", ".join(k for k, _ in report.top_keywords[:5]) + " 입니다.",
            }
            st.success("v7 통합 트렌드 분석 완료")
        except Exception as exc:
            st.error(f"v7 통합 분석 실패: {exc}")

    if st.session_state.api_trend_report:
        report = st.session_state.api_trend_report
        st.markdown("### v7 통합 분석 요약")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("분석 키워드", len(report.get("keywords", [])))
        c2.metric("YouTube 수집", len(report.get("youtube_items", [])))
        c3.metric("네이버 그룹", len(report.get("naver_groups", [])))
        c4.metric("상표 체크", len(report.get("trademark_results", [])))
        st.write("**추천 포맷:**", " → ".join(report.get("recommended_formats", [])))
        st.write("**추천 문구:**", ", ".join(report.get("recommended_phrases", [])))
        st.write("**추천 캐릭터 방향:**")
        st.write(report.get("recommended_characters", []))
        if report.get("caution_notes"):
            for note in report["caution_notes"]:
                st.warning(note)
        st.markdown("### 핵심 키워드")
        st.dataframe(pd.DataFrame(report.get("top_keywords", []), columns=["키워드", "빈도"]), use_container_width=True)
        st.markdown("### YouTube 수집 데이터")
        if report.get("youtube_items"):
            st.dataframe(pd.DataFrame(report["youtube_items"]), use_container_width=True)
        else:
            st.info("YouTube API 키가 없거나 수집 결과가 없으면 수동 입력 기반 분석만 표시됩니다.")
        st.markdown("### 네이버 데이터랩 결과")
        if report.get("naver_groups"):
            st.json(report["naver_groups"])
        else:
            st.info("네이버 API 키가 없거나 수집 결과가 없으면 생략됩니다.")
        st.markdown("### 상표/명칭 위험 체크")
        st.dataframe(pd.DataFrame(report.get("trademark_results", [])), use_container_width=True)
        html_path = Path(report.get("html_path", ""))
        json_path = Path(report.get("json_path", ""))
        if html_path.exists():
            st.download_button("30일 분석 HTML 리포트 다운로드", data=html_path.read_bytes(), file_name="trend_30day_report.html", mime="text/html")
        if json_path.exists():
            st.download_button("30일 분석 JSON 다운로드", data=json_path.read_bytes(), file_name="trend_30day_report.json", mime="application/json")



if selected_page_index == 10:
    st.subheader("저작권/상표권 방어 센터")
    st.write("기존 캐릭터 모방, AI 완성본 제출 위험, 자료·폰트 라이선스, 창작 과정 증거를 한 번에 정리합니다. 법적 확정 판단이 아니라 제출 전 위험도 방어 리포트입니다.")

    suggested_defense_name = "kakao_emoticon_defense"
    if st.session_state.blend_concepts:
        suggested_defense_name = st.session_state.blend_concepts[0].get("name", suggested_defense_name)
    elif st.session_state.concepts:
        suggested_defense_name = st.session_state.concepts[0].get("name", suggested_defense_name)

    defense_project_name = st.text_input("방어 리포트 프로젝트명", value=suggested_defense_name, key="v48_defense_project_name")
    defense_concept_text = st.text_area(
        "캐릭터 콘셉트/세계관",
        value=json.dumps(st.session_state.profile or {}, ensure_ascii=False, indent=2) if st.session_state.profile else "예의 바르고 피곤한 복합 소재 캐릭터. 기존 캐릭터를 참고하지 않고 직접 제작한 원본 기반.",
        height=130,
        key="v48_defense_concept_text",
    )
    defense_phrase_text = st.text_area(
        "대표 문구/말투",
        value="\n".join([x.get("phrase", "") for x in (st.session_state.expressions or [])[:20]]) if st.session_state.expressions else "넵\n확인했습니다\n감사합니다\n죄송합니다\n퇴근하고 싶습니다",
        height=130,
    )
    defense_visual_notes = st.text_area(
        "외형/색상/움직임 설명",
        value=json.dumps(st.session_state.prototype_results[:2], ensure_ascii=False, indent=2) if st.session_state.prototype_results else "단순 도형 기반 360×360 투명 배경 캐릭터. 문구와 캐릭터 움직임을 동기화.",
        height=130,
    )

    st.markdown("### AI 사용 기록")
    ai_usage_mode = st.selectbox(
        "AI 사용 구분",
        ["사용 안 함", "아이디어/문구 추천만 사용", "시안 참고용으로만 사용", "제출용 완성 이미지에 사용됨"],
        index=1,
    )
    ai_notes = st.text_area("AI 사용 메모/프롬프트 기록", value="기획·문구·표현 은행 보조 용도. 제출용 완성 이미지는 직접 제작 레이어와 프로그램 생성 시안 기반으로 관리.", height=90)

    st.markdown("### 자료·폰트·이미지 라이선스 기록")
    default_assets = pd.DataFrame([
        {"filename": "character_sketch.png", "asset_type": "원본 스케치", "source": "직접 제작", "license_type": "본인 창작", "commercial_use": "가능", "modification_allowed": "가능", "attribution_required": "불필요", "note": "최초 캐릭터 원본"},
        {"filename": "font", "asset_type": "폰트", "source": "상업 이용 가능 폰트로 교체 필요", "license_type": "미확인", "commercial_use": "미확인", "modification_allowed": "미확인", "attribution_required": "미확인", "note": "제출 전 실제 사용 폰트명 기록"},
    ])
    asset_df = st.data_editor(default_assets, num_rows="dynamic", use_container_width=True, key="asset_license_editor")

    st.markdown("### 창작 과정 증거 경로")
    auto_paths = []
    if st.session_state.get("expression_pack_zip"):
        auto_paths.append(str(st.session_state.expression_pack_zip))
    if st.session_state.submission_result:
        auto_paths.append(st.session_state.submission_result.get("package_dir", ""))
    auto_paths.append("outputs/prototypes")
    evidence_path_text = st.text_area(
        "원본/레이어/수정 전후/최종 출력 파일 또는 폴더 경로 · 줄바꿈 구분",
        value="\n".join([p for p in auto_paths if p]),
        height=100,
    )

    st.markdown("### 검사 범위")
    st.markdown(
        """
        - 기존 유명 캐릭터·브랜드명·모방 표현 키워드 검사  
        - AI 사용 단계별 위험도 분리  
        - 폰트/이미지/효과 자료의 상업 이용·수정 허용 기록  
        - 원본/수정/출력 파일 SHA-256 체크섬 증거화  
        - 최종 `copyright_defense_report.html/json` + `asset_license_log.csv` 생성
        """
    )

    if st.button("저작권 방어 리포트 생성", type="primary"):
        try:
            rows = asset_df.to_dict(orient="records") if hasattr(asset_df, "to_dict") else []
            evidence_paths = [x.strip() for x in evidence_path_text.splitlines() if x.strip()]
            report = CopyrightDefenseCenter().build_report(
                project_name=defense_project_name,
                concept_text=defense_concept_text,
                phrase_text=defense_phrase_text,
                visual_notes=defense_visual_notes,
                ai_usage_mode=ai_usage_mode,
                ai_notes=ai_notes,
                asset_rows=rows,
                evidence_paths=evidence_paths,
                output_dir=BASE_OUTPUT / "copyright_defense",
            )
            st.session_state.copyright_defense_report = report.to_dict()
            st.success("저작권 방어 리포트 생성 완료")
        except Exception as exc:
            st.error(f"저작권 방어 리포트 생성 실패: {exc}")

    if st.session_state.copyright_defense_report:
        report = st.session_state.copyright_defense_report
        c1, c2, c3 = st.columns(3)
        c1.metric("위험도", report["overall_risk_score"])
        c2.metric("판정", report["final_status"])
        c3.metric("증거 파일", len(report.get("evidence_records", [])))
        st.write(report.get("summary", ""))
        if report.get("required_actions"):
            for action in report["required_actions"]:
                st.warning(action)
        st.markdown("### 주요 발견")
        if report.get("findings"):
            st.dataframe(pd.DataFrame(report["findings"]), use_container_width=True)
        else:
            st.success("고위험 발견 항목이 크게 감지되지 않았습니다.")
        st.markdown("### 자료 라이선스 기록")
        st.dataframe(pd.DataFrame(report.get("asset_records", [])), use_container_width=True)
        st.markdown("### 창작 과정 증거 기록")
        st.dataframe(pd.DataFrame(report.get("evidence_records", [])), use_container_width=True)
        for label, path_key, mime in [
            ("저작권 방어 HTML 다운로드", "html_path", "text/html"),
            ("저작권 방어 JSON 다운로드", "json_path", "application/json"),
            ("자료 라이선스 CSV 다운로드", "csv_path", "text/csv"),
        ]:
            fp = Path(report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 11:
    st.subheader("설치/실행 진단")
    st.write("Windows 설치형/로컬 실행 환경을 점검합니다. Python 버전, 필수 패키지, 출력 폴더 쓰기 권한, 포트 사용 여부, 실행 BAT 파일 존재 여부를 확인합니다.")

    diag_root = Path.cwd()
    diag_ports = st.text_input("검사할 포트 · 콤마 구분", value="8520,8521,8522")
    st.markdown("### 실행 안정화 파일")
    st.markdown(
        r"""
        - `1_INSTALL_NOW.bat`: `%LOCALAPPDATA%\KakaoEmoticonProfitSystemV18`에 설치 복사 + 바로가기 생성
        - `2_START_PROGRAM.bat`: 설치/휴대용 폴더에서 앱 실행
        - `3_CREATE_SHORTCUTS_ONLY.bat`: 바탕화면 바로가기 재생성
        - `4_REPAIR_ENVIRONMENT.bat`: Python 가상환경 재설치 + 패키지 재설치 + 진단
        - `5_OPEN_OUTPUTS.bat`: 결과물 폴더 열기
        - `6_RUN_DIAGNOSTICS.bat`: 설치/실행 진단 HTML 생성
        - `7_STOP_PORTS.bat`: 8520~8522 포트 정리
        """
    )

    if st.button("설치/실행 진단 실행", type="primary"):
        try:
            ports = [int(x.strip()) for x in diag_ports.split(",") if x.strip().isdigit()] or [8520]
            report = InstallationDiagnostics().run(
                project_root=diag_root,
                app_version=APP_VERSION,
                ports=ports,
                output_dir=BASE_OUTPUT / "installer_diagnostics",
            )
            st.session_state.install_diag_report = report.to_dict()
            st.success("설치/실행 진단 완료")
        except Exception as exc:
            st.error(f"설치/실행 진단 실패: {exc}")

    if st.session_state.install_diag_report:
        report = st.session_state.install_diag_report
        c1, c2, c3 = st.columns(3)
        c1.metric("진단 점수", report.get("score", 0))
        c2.metric("전체 상태", report.get("overall_status", "-"))
        c3.metric("진단 항목", len(report.get("items", [])))
        st.markdown("### 권장 조치")
        for action in report.get("recommended_actions", []):
            st.info(action)
        st.markdown("### 진단 상세")
        st.dataframe(pd.DataFrame(report.get("items", [])), use_container_width=True)
        html_path = Path(report.get("html_path", ""))
        json_path = Path(report.get("json_path", ""))
        if html_path.exists():
            st.download_button("설치 진단 HTML 다운로드", data=html_path.read_bytes(), file_name="installation_diagnostic_report.html", mime="text/html")
        if json_path.exists():
            st.download_button("설치 진단 JSON 다운로드", data=json_path.read_bytes(), file_name="installation_diagnostic_report.json", mime="application/json")

    st.warning("Windows에서 한글 경로/권한/포트 충돌 문제가 생기면 4_REPAIR_ENVIRONMENT.bat와 7_STOP_PORTS.bat를 먼저 실행하세요.")


if selected_page_index == 12:
    st.subheader("직접 창작 기준 / AI 정책 대응")
    st.write("AI 사용을 숨기거나 검수를 우회하는 기능은 제공하지 않습니다. 대신 직접 창작 증거, 레이어 원본, 수정 이력, 자료 출처를 기록해 제출 전 리스크를 낮추는 방식으로 관리합니다.")
    st.warning("카카오 공식 운영 원칙상 생성형 AI 활용 이모티콘 제안은 제한될 수 있습니다. 제출용 완성 이미지는 직접 창작 기반으로 관리하세요.")

    human_project = st.text_input("창작 기준 프로젝트명", value="direct_creation_project")
    human_concept = st.text_area("콘셉트/제작 메모", value="직접 스케치한 보리와 쌀 캐릭터. 프로그램은 문구 후보, 품질 검사, 파일 정리 보조에만 사용.")
    human_ai_mode = st.selectbox(
        "AI/자동화 사용 범위",
        [
            "사용 안 함",
            "아이디어/문구 추천만 사용",
            "시장 분석/품질 검사/문구 분류에만 사용",
            "시안 참고용으로만 사용",
            "제출용 완성 이미지에 사용됨",
        ],
        index=2,
    )
    st.markdown("### 직접 창작 증거 체크")
    c1, c2, c3 = st.columns(3)
    has_sketch = c1.checkbox("손스케치/러프 원본 있음", value=False)
    has_layers = c2.checkbox("레이어 원본 있음", value=False)
    has_revisions = c3.checkbox("수정 이력 있음", value=False)
    c4, c5 = st.columns(2)
    has_license = c4.checkbox("자료/폰트 라이선스 기록 있음", value=False)
    has_package = c5.checkbox("최종 제출 패키지 있음", value=bool(st.session_state.submission_result))
    evidence_default = str(BASE_OUTPUT)
    evidence_input = st.text_area("증거 파일/폴더 경로 · 줄바꿈 구분", value=evidence_default)

    if st.button("직접 창작 기준 리포트 생성", type="primary"):
        try:
            evidence_paths = [line.strip() for line in evidence_input.splitlines() if line.strip()]
            report = HumanOriginWorkflow().build_report(
                project_name=human_project,
                concept_text=human_concept,
                ai_usage_mode=human_ai_mode,
                evidence_paths=evidence_paths,
                output_dir=BASE_OUTPUT / "human_origin_compliance",
                has_hand_sketch=has_sketch,
                has_layer_files=has_layers,
                has_revision_history=has_revisions,
                has_source_license_log=has_license,
                has_final_package=has_package,
            )
            st.session_state.human_origin_report = report.to_dict()
            st.success("직접 창작 기준 리포트 생성 완료")
        except Exception as exc:
            st.error(f"직접 창작 기준 리포트 생성 실패: {exc}")

    if st.session_state.human_origin_report:
        report = st.session_state.human_origin_report
        c1, c2, c3 = st.columns(3)
        c1.metric("준수 점수", report.get("compliance_score", 0))
        c2.metric("직접 창작 증거 점수", report.get("human_input_score", 0))
        c3.metric("판정", report.get("final_status", "-"))
        st.markdown("### 발견 항목")
        if report.get("findings"):
            st.dataframe(pd.DataFrame(report.get("findings", [])), use_container_width=True)
        else:
            st.success("고위험 발견 항목이 없습니다.")
        st.markdown("### 허용 가능한 AI 보조 범위")
        st.write(report.get("allowed_ai_uses", []))
        st.markdown("### 차단해야 할 사용")
        st.write(report.get("blocked_uses", []))
        st.markdown("### 증거 파일")
        st.dataframe(pd.DataFrame(report.get("evidence_files", [])), use_container_width=True)
        html_path = Path(report.get("html_path", ""))
        json_path = Path(report.get("json_path", ""))
        if html_path.exists():
            st.download_button("직접 창작 기준 HTML 다운로드", data=html_path.read_bytes(), file_name=html_path.name, mime="text/html")
        if json_path.exists():
            st.download_button("직접 창작 기준 JSON 다운로드", data=json_path.read_bytes(), file_name=json_path.name, mime="application/json")


if selected_page_index == 13:
    st.subheader("초보자 직접 캐릭터 만들기 모드")
    st.write("동그라미 얼굴·몸통·눈·입·기본색·성격·말투만 입력해도, 프로그램이 듀오 캐릭터 시안·표현 후보·움직이는 문구 장면·창작 증거를 자동 정리합니다.")
    st.info("이 기능은 AI 완성본을 숨기는 기능이 아니라, 사용자가 정한 기본 도형/색/성격/말투를 직접 창작 출발점으로 기록하고 확장하는 기능입니다.")

    st.markdown("## v18 색상·성격·말투 후보 선택 + 실시간 미리보기")
    st.write("도형으로 직접 만들거나, 내가 그린 스케치 사진/PNG/JPG/WEBP 파일을 첨부하고, 소재를 1~5개까지 입력해 멀티 캐릭터 세트를 만들 수 있습니다.")
    st.warning("첨부 이미지는 그대로 합성/복제하지 않고, 색감·형태·비율 힌트와 창작 증거로만 사용합니다.")

    multi_project = st.text_input("v18 멀티소재 프로젝트명", value="bori_rice_multi_creator", key="multi_project")
    material_count = st.slider("소재 개수", 1, 5, 2, step=1, key="multi_material_count")

    st.markdown("### 색상 후보 팔레트")
    palette_cols = st.columns(3)
    for pidx, pname in enumerate(COLOR_PRESET_LABELS):
        with palette_cols[pidx % 3]:
            st.markdown(palette_swatch_html(pname), unsafe_allow_html=True)
    global_palette = st.selectbox("전체 색상 후보", COLOR_PRESET_LABELS, index=0, key="global_color_palette")
    st.caption("각 소재별로 전체 팔레트를 그대로 쓰거나, 소재마다 다른 색상 후보/직접입력을 선택할 수 있습니다.")

    material_specs = []
    shape_options = ["둥근형", "알갱이형", "길쭉형", "납작형", "네모형"]
    default_names = ["보리", "쌀", "감자", "고구마", "메모지"]
    default_personality_labels = ["까칠하지만 은근히 챙김", "온순하고 다정함", "피곤하지만 성실함", "느긋하고 포근함", "업무에 눌려 구겨짐"]
    default_tone_labels = ["투덜거림, 짧게 말함", "부드럽고 위로하는 말투", "작게 한숨 섞인 말투", "느긋하고 둥근 말투", "짧은 업무 답장 말투"]
    personality_labels = [x.label for x in PERSONALITY_PRESETS]
    tone_labels = [x.label for x in TONE_PRESETS]
    color_mode_options = ["전체 팔레트 자동", "소재별 후보 선택", "직접 입력"]

    for i in range(material_count):
        with st.expander(f"소재 {i+1} 설정", expanded=(i < 2)):
            mcols = st.columns([1, 1, 1, 1])
            with mcols[0]:
                name = st.text_input(f"소재 {i+1} 이름", value=default_names[i], key=f"multi_name_{i}")
                base_shape = st.selectbox(f"소재 {i+1} 기본 도형", shape_options, index=min(i, len(shape_options)-1), key=f"multi_shape_{i}")
            with mcols[1]:
                color_mode = st.selectbox(f"소재 {i+1} 색상 선택 방식", color_mode_options, index=0, key=f"multi_color_mode_{i}")
                if color_mode == "전체 팔레트 자동":
                    color = color_from_palette(global_palette, i)
                    st.markdown(f"<div style='display:flex;align-items:center;gap:8px'><span style='display:inline-block;width:34px;height:22px;background:{color};border:1px solid #777;border-radius:4px'></span><code>{color}</code></div>", unsafe_allow_html=True)
                elif color_mode == "소재별 후보 선택":
                    selected_palette = st.selectbox(f"소재 {i+1} 색상 후보", COLOR_PRESET_LABELS, index=min(i, len(COLOR_PRESET_LABELS)-1), key=f"multi_color_palette_{i}")
                    color = color_from_palette(selected_palette, i)
                    st.markdown(f"<div style='display:flex;align-items:center;gap:8px'><span style='display:inline-block;width:34px;height:22px;background:{color};border:1px solid #777;border-radius:4px'></span><code>{color}</code></div>", unsafe_allow_html=True)
                else:
                    color = st.text_input(f"소재 {i+1} 직접 색상", value=color_from_palette(global_palette, i), key=f"multi_color_direct_{i}", help="예: 연갈색, 아이보리, #C89A5C")
            with mcols[2]:
                p_default = default_personality_labels[i]
                p_index = personality_labels.index(p_default) if p_default in personality_labels else 0
                p_label = st.selectbox(f"소재 {i+1} 성격 후보", personality_labels, index=p_index, key=f"multi_personality_preset_{i}")
                if p_label == "직접 입력":
                    personality = st.text_input(f"소재 {i+1} 직접 성격", value=p_default, key=f"multi_personality_direct_{i}")
                else:
                    personality = preset_value(PERSONALITY_PRESETS, p_label, p_default)
                    st.caption(personality)
            with mcols[3]:
                t_default = default_tone_labels[i]
                t_index = tone_labels.index(t_default) if t_default in tone_labels else 0
                t_label = st.selectbox(f"소재 {i+1} 말투 후보", tone_labels, index=t_index, key=f"multi_tone_preset_{i}")
                if t_label == "직접 입력":
                    tone = st.text_input(f"소재 {i+1} 직접 말투", value=t_default, key=f"multi_tone_direct_{i}")
                else:
                    tone = preset_value(TONE_PRESETS, t_label, t_default)
                    st.caption(tone)
                role = st.selectbox(f"소재 {i+1} 역할 후보", ROLE_PRESETS, index=min(i, len(ROLE_PRESETS)-1), key=f"multi_role_{i}")
            material_specs.append(MaterialSpec(name=name, color=color, personality=personality, tone=tone, base_shape=base_shape, role=role))

    st.markdown("### 선택값 실시간 미리보기")
    live_preview = st.checkbox("선택한 색상·성격·말투·도형으로 360×360 미리보기 자동 표시", value=True, key="live_preview_enabled")
    if live_preview:
        try:
            preview_root = BASE_OUTPUT / "live_preview" / multi_project
            preview_root.mkdir(parents=True, exist_ok=True)
            preview_creator = MultiMaterialCharacterCreator()
            preview_assets = preview_creator.render_multi_group(material_specs, preview_root / "assets", f"{multi_project}_live")
            preview_exprs = preview_creator.build_expression_table(material_specs, 8)
            preview_assets.extend(preview_creator.render_expression_previews(material_specs, preview_exprs, preview_root / "expressions", f"{multi_project}_live", 4))
            st.markdown("#### 360×360 캐릭터/표현 미리보기")
            pcols = st.columns(5)
            for idx, asset in enumerate(preview_assets[:10]):
                fp = Path(asset.get("file_path", ""))
                if fp.exists():
                    with pcols[idx % 5]:
                        st.image(str(fp), caption=asset.get("label", ""), width=130)
            st.markdown("#### 선택값 기반 표현 후보 일부")
            st.dataframe(pd.DataFrame(preview_exprs[:8]), use_container_width=True)
            st.markdown("#### 움직이는 문구형 장면 후보")
            st.dataframe(pd.DataFrame(preview_creator.build_motion_scenes(material_specs)), use_container_width=True)
        except Exception as exc:
            st.error(f"미리보기 생성 실패: {exc}")

    multi_files = st.file_uploader(
        "스케치 사진/직접 만든 이미지/첨부파일 업로드",
        type=["png", "jpg", "jpeg", "webp", "bmp", "txt", "json"],
        accept_multiple_files=True,
        key="multi_source_files",
        help="내가 그린 스케치 사진, 직접 만든 PNG/JPG/WEBP, 설명 파일을 첨부할 수 있습니다. 권장 1~5개."
    )
    m1, m2, m3 = st.columns(3)
    with m1:
        multi_expression_count = st.slider("v18 표현 후보 수", 40, 120, 80, step=10, key="multi_expr_count")
    with m2:
        multi_preview_count = st.slider("v18 PNG 미리보기 수", 4, 24, 12, step=2, key="multi_preview_count")
    with m3:
        st.write(" ")
        st.write(" ")
        run_multi = st.button("v18 멀티소재 캐릭터 프로젝트 생성", type="primary")

    if run_multi:
        try:
            report = MultiMaterialCharacterCreator().build_project(
                specs=material_specs,
                uploaded_files=multi_files or [],
                output_dir=BASE_OUTPUT / "multi_material_creator",
                project_name=multi_project,
                expression_count=multi_expression_count,
                preview_count=multi_preview_count,
            )
            st.session_state.multi_material_creator_report = report.to_dict()
            st.session_state.expressions = [
                {"no": row["no"], "category": row["category"], "phrase": row["phrase"], "usage_score": 82, "emotion": row["category"], "format_hint": row["format_recommendation"], "motion_hint": row["motion_hint"]}
                for row in report.expression_table
            ]
            st.success("v18 멀티소재 캐릭터 프로젝트 생성 완료")
        except Exception as exc:
            st.error(f"v18 멀티소재 캐릭터 생성 실패: {exc}")

    if st.session_state.multi_material_creator_report:
        mreport = st.session_state.multi_material_creator_report
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("소재 수", len(mreport.get("material_specs", [])))
        mc2.metric("첨부자료", len(mreport.get("source_files", [])))
        mc3.metric("표현 후보", len(mreport.get("expression_table", [])))
        st.markdown("### v18 생성 캐릭터/표현 미리보기")
        massets = [a for a in mreport.get("generated_assets", []) if a.get("asset_type") in ["prototype", "material_candidate", "expression_preview"]]
        mcols = st.columns(5)
        for idx, asset in enumerate(massets[:20]):
            fp = Path(asset.get("file_path", ""))
            if fp.exists():
                with mcols[idx % 5]:
                    st.image(str(fp), caption=asset.get("label", ""), width=130)
        if mreport.get("source_files"):
            st.markdown("### 첨부자료 분석/증거")
            st.dataframe(pd.DataFrame(mreport.get("source_files", [])), use_container_width=True)
        st.markdown("### v18 표현 후보")
        st.dataframe(pd.DataFrame(mreport.get("expression_table", [])), use_container_width=True)
        st.markdown("### v18 움직이는 문구 장면")
        st.dataframe(pd.DataFrame(mreport.get("motion_scene_table", [])), use_container_width=True)
        for label, path_key, mime in [
            ("v18 멀티소재 리포트 HTML 다운로드", "html_path", "text/html"),
            ("v18 멀티소재 리포트 JSON 다운로드", "json_path", "application/json"),
            ("v18 멀티소재 패키지 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(mreport.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)

    st.divider()
    st.markdown("## v11 듀오 캐릭터 빠른 생성")

    c1, c2 = st.columns(2)
    with c1:
        beginner_project = st.text_input("프로젝트명", value="bori_rice_beginner_creator", key="v48_beginner_project")
        material_a = st.text_input("캐릭터 A 소재", value="보리")
        color_a = st.text_input("캐릭터 A 기본색", value="연갈색", help="예: 연갈색, 아이보리, #C89A5C")
        personality_a = st.text_input("캐릭터 A 성격", value="까칠하지만 은근히 챙김")
        tone_a = st.text_input("캐릭터 A 말투", value="투덜거림, 짧게 말함")
    with c2:
        material_b = st.text_input("캐릭터 B 소재", value="쌀")
        color_b = st.text_input("캐릭터 B 기본색", value="아이보리", help="예: 아이보리, 흰색, #F4EBCD")
        personality_b = st.text_input("캐릭터 B 성격", value="온순하고 다정함")
        tone_b = st.text_input("캐릭터 B 말투", value="부드럽고 위로하는 말투")
        target = st.text_input("주 사용 대상/상황", value="직장인/일상 답장")

    c3, c4, c5 = st.columns(3)
    with c3:
        base_shape = st.selectbox("기본 도형", ["둥근형", "알갱이형", "길쭉형", "납작형", "네모형"], index=0, key="v48_beginner_base_shape")
    with c4:
        relationship = st.text_input("둘의 관계성", value="투덜이와 다정이 콤비")
    with c5:
        preview_count = st.slider("표현 PNG 미리보기 수", 4, 24, 12, step=2, key="v48_beginner_preview_count")
    expression_count = st.slider("생성할 표현 후보 수", 40, 120, 80, step=10, key="beginner_expr_count")
    creator_note = st.text_area("직접 창작 메모", value="사용자가 직접 정한 소재·도형·색상·성격·말투를 바탕으로 단순 시안을 만들고, 프로그램이 표현/움직임/창작 기록을 확장합니다.", height=80)

    if st.button("초보자 직접 캐릭터 프로젝트 생성", type="primary"):
        try:
            spec = DuoCharacterInput(
                material_a=material_a,
                material_b=material_b,
                personality_a=personality_a,
                personality_b=personality_b,
                tone_a=tone_a,
                tone_b=tone_b,
                color_a=color_a,
                color_b=color_b,
                base_shape=base_shape,
                relationship=relationship,
                target=target,
                creator_note=creator_note,
            )
            report = BeginnerCharacterCreator().build_project(
                spec=spec,
                output_dir=BASE_OUTPUT / "beginner_creator",
                project_name=beginner_project,
                expression_count=expression_count,
                preview_count=preview_count,
            )
            st.session_state.beginner_creator_report = report.to_dict()
            # 표현 은행/소재 분석 흐름에 바로 재사용할 수 있도록 일부 반영
            st.session_state.expressions = [
                {"no": row["no"], "category": row["category"], "phrase": row["phrase"], "usage_score": 80, "emotion": row["category"], "format_hint": row["format_recommendation"], "motion_hint": row["motion_hint"]}
                for row in report.expression_table
            ]
            st.success("초보자 직접 캐릭터 프로젝트 생성 완료")
        except Exception as exc:
            st.error(f"초보자 직접 캐릭터 생성 실패: {exc}")

    if st.session_state.beginner_creator_report:
        report = st.session_state.beginner_creator_report
        c1, c2, c3 = st.columns(3)
        c1.metric("생성 자산", len(report.get("generated_assets", [])))
        c2.metric("표현 후보", len(report.get("expression_table", [])))
        c3.metric("움직임 장면", len(report.get("motion_scene_table", [])))

        st.markdown("### 생성된 캐릭터/표현 미리보기")
        assets = report.get("generated_assets", [])
        preview_assets = [a for a in assets if a.get("asset_type") in ["prototype", "expression_preview", "layer_candidate"]]
        cols = st.columns(4)
        for idx, asset in enumerate(preview_assets[:16]):
            fp = Path(asset.get("file_path", ""))
            if fp.exists():
                with cols[idx % 4]:
                    st.image(str(fp), caption=asset.get("label", ""), width=150)

        st.markdown("### 표현 후보")
        st.dataframe(pd.DataFrame(report.get("expression_table", [])), use_container_width=True)
        st.markdown("### 움직이는 문구 장면")
        st.dataframe(pd.DataFrame(report.get("motion_scene_table", [])), use_container_width=True)
        st.markdown("### 창작 과정 타임라인")
        st.dataframe(pd.DataFrame(report.get("human_origin_timeline", [])), use_container_width=True)

        for label, path_key, mime in [
            ("초보자 창작 리포트 HTML 다운로드", "html_path", "text/html"),
            ("초보자 창작 리포트 JSON 다운로드", "json_path", "application/json"),
            ("초보자 창작 패키지 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 14:
    st.subheader("후보 갤러리 / 24개·32개 세트 자동 선택 + 표정 자동 구성")
    st.write("표현 후보 80~120개 중에서 중복·가독성·감정 균형·포맷 적합도를 기준으로 24개 또는 32개 후보를 자동 선별하고, 각 표현에 맞는 눈·입·눈썹·효과·문구 움직임 계획을 함께 구성합니다.")

    report_source = st.radio(
        "표현 후보 출처",
        ["초보자/멀티소재 직접 만들기 결과", "일반 표현 은행"],
        horizontal=True,
        key="v48_candidate_source_radio",
    )

    source_expressions = []
    source_specs = []
    if report_source == "초보자/멀티소재 직접 만들기 결과":
        source_report = st.session_state.get("multi_material_creator_report") or st.session_state.get("beginner_creator_report")
        if source_report:
            source_expressions = source_report.get("expression_table", [])
            for item in source_report.get("material_specs", []):
                if isinstance(item, dict):
                    source_specs.append(MaterialSpec(
                        name=item.get("name", "소재"),
                        color=item.get("color", "아이보리"),
                        personality=item.get("personality", "온순함"),
                        tone=item.get("tone", "부드러운 말투"),
                        base_shape=item.get("base_shape", "둥근형"),
                        role=item.get("role", "대화 보조"),
                    ))
            # v11 듀오 리포트는 material_specs가 없을 수 있으므로 최소 2개 기본값 구성
            if not source_specs and source_report.get("input_summary"):
                summary = source_report.get("input_summary", {})
                source_specs = [
                    MaterialSpec(name=summary.get("material_a", "캐릭터A"), color=summary.get("color_a", "연갈색"), personality=summary.get("personality_a", "까칠하지만 은근히 챙김"), tone=summary.get("tone_a", "투덜거림"), base_shape="알갱이형", role="중심"),
                    MaterialSpec(name=summary.get("material_b", "캐릭터B"), color=summary.get("color_b", "아이보리"), personality=summary.get("personality_b", "온순하고 다정함"), tone=summary.get("tone_b", "부드러운 말투"), base_shape="둥근형", role="보조"),
                ]
    else:
        source_expressions = asdict_list(st.session_state.get("expressions", []))
        # 일반 표현 은행만 있을 때도 미리보기 생성을 위해 기본 소재 하나를 둡니다.
        source_specs = [MaterialSpec(name="기본 캐릭터", color="아이보리", personality="온순하고 다정함", tone="부드러운 말투", base_shape="둥근형", role="중심")]

    if not source_expressions:
        st.info("먼저 3번 표현 은행 또는 14번 초보자/멀티소재 직접 만들기에서 표현 후보를 생성하세요.")
    else:
        st.success(f"불러온 표현 후보: {len(source_expressions)}개 / 소재: {len(source_specs)}개")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            gallery_project = st.text_input("갤러리 프로젝트명", value="v18_expression_face_gallery")
        with col_b:
            curation_format = st.selectbox("선별 포맷", options=list(FORMAT_LABELS.keys()), format_func=lambda k: FORMAT_LABELS.get(k, k), index=list(FORMAT_LABELS.keys()).index("static_text"))
        with col_c:
            default_count = PLANNING_COUNTS.get(curation_format, 32)
            curation_count = st.slider("선택할 표현 수", 8, 40, default_count if default_count <= 40 else 32, step=1)

        builder = CandidateGalleryBuilder()
        scored_preview = builder.score_expressions(source_expressions, curation_format)
        for row in scored_preview:
            plan = builder.face_engine.build_plan(row, source_specs, curation_format)
            row["face_summary"] = builder.face_engine.summary(plan)
        scored_preview = sorted(scored_preview, key=lambda r: r.get("candidate_score", 0), reverse=True)[:30]
        st.markdown("### 상위 후보 미리보기 + 표정 자동 배정")
        st.dataframe(pd.DataFrame(scored_preview)[["category", "phrase", "candidate_score", "format_recommendation", "face_summary", "readability_note", "selection_reason"]], use_container_width=True)

        if st.button("후보 갤러리/선택 세트 생성", type="primary"):
            try:
                curation_report = builder.build_gallery_pack(
                    specs=source_specs,
                    expressions=source_expressions,
                    output_dir=BASE_OUTPUT / "candidate_gallery",
                    project_name=gallery_project,
                    format_key=curation_format,
                    target_count=curation_count,
                )
                st.session_state.candidate_gallery_report = curation_report.to_dict()
                st.success("후보 갤러리/선택 세트 생성 완료")
            except Exception as exc:
                st.error(f"후보 갤러리 생성 실패: {exc}")

    curation = st.session_state.get("candidate_gallery_report")
    if curation:
        st.markdown("### 선택 결과 요약")
        c1, c2, c3 = st.columns(3)
        c1.metric("전체 후보", curation.get("total_candidates", 0))
        c2.metric("선택 수량", curation.get("selected_count", 0))
        c3.metric("포맷", FORMAT_LABELS.get(curation.get("format_key", ""), curation.get("format_key", "")))

        st.markdown("### 생성 이미지/GIF 미리보기")
        files = curation.get("generated_files", [])
        cols = st.columns(4)
        for idx, item in enumerate(files[:32]):
            fp = Path(item.get("file_path", ""))
            if fp.exists():
                with cols[idx % 4]:
                    st.image(str(fp), caption=item.get("file_name", ""), width=140)

        st.markdown("### 최종 선택 표현표 + 표정/동작 계획")
        selected_df = pd.DataFrame(curation.get("selected_expressions", []))
        preferred_cols = [c for c in ["selected_no", "category", "phrase", "candidate_score", "face_summary", "motion_hint", "selection_reason", "readability_note"] if c in selected_df.columns]
        if preferred_cols:
            st.dataframe(selected_df[preferred_cols], use_container_width=True)
        else:
            st.dataframe(selected_df, use_container_width=True)
        if curation.get("selected_expressions"):
            st.markdown("### 표정 자동 구성 상세 예시")
            st.json(curation["selected_expressions"][0].get("expression_plan", {}))

        for label, path_key, mime in [
            ("후보 갤러리 HTML 다운로드", "html_path", "text/html"),
            ("후보 갤러리 JSON 다운로드", "json_path", "application/json"),
            ("선택 표현 CSV 다운로드", "csv_path", "text/csv"),
            ("선택 세트 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(curation.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)



if selected_page_index == 15:
    st.subheader("표정·파츠·문구·움직임 편집기")
    st.write("v18에서 자동 구성된 눈·입·몸동작·문구 움직임·효과를 사용자가 직접 확인하고, 일괄 수정한 뒤 새 미리보기와 최종 확인표를 생성합니다.")

    source_report = st.session_state.get("candidate_gallery_report")
    if not source_report:
        st.info("먼저 15번 탭에서 후보 갤러리/선택 세트를 생성하세요. 생성 후 이 탭에서 표정과 움직임을 수정할 수 있습니다.")
    else:
        selected_expressions = source_report.get("selected_expressions", [])
        st.success(f"불러온 최종 선택 표현: {len(selected_expressions)}개")
        editor = PartMotionEditor()
        options = editor.edit_options()

        st.markdown("### 1) 현재 자동 구성 결과")
        current_df = pd.DataFrame(selected_expressions)
        display_cols = [c for c in ["selected_no", "category", "phrase", "face_summary", "motion_hint", "selection_reason"] if c in current_df.columns]
        if display_cols:
            st.dataframe(current_df[display_cols], use_container_width=True)
        else:
            st.dataframe(current_df, use_container_width=True)

        st.markdown("### 2) 전체 표현 일괄 수정")
        st.caption("자동 유지로 두면 v18에서 배정된 값이 그대로 사용됩니다. 특정 표현만 세밀하게 바꾸는 기능은 다음 단계에서 확장하고, v18은 먼저 안전한 일괄 편집/미리보기 중심입니다.")
        e1, e2, e3 = st.columns(3)
        with e1:
            eye_choice = st.selectbox("눈 후보", ["자동 유지"] + options["eye_style"], index=0, key="v48_editor_eye_choice")
            brow_choice = st.selectbox("눈썹 후보", ["자동 유지"] + options["brow_style"], index=0, key="v48_editor_brow_choice")
            mouth_choice = st.selectbox("입 후보", ["자동 유지"] + options["mouth_style"], index=0, key="v48_editor_mouth_choice")
        with e2:
            body_choice = st.selectbox("몸 동작 후보", ["자동 유지"] + options["body_motion"], index=0, key="v48_editor_body_choice")
            text_motion_choice = st.selectbox("문구 움직임 후보", ["자동 유지"] + options["text_motion"], index=0, key="v48_editor_text_motion_choice")
            effect_choice = st.selectbox("효과 후보", ["자동 유지"] + options["effects"], index=0, key="v48_editor_effect_choice")
        with e3:
            font_size = st.slider("문구 글자 크기", 18, 42, 28, key="v48_editor_font_size")
            char_x = st.slider("캐릭터 좌우 위치", 90, 270, 178, key="v48_editor_char_x")
            char_y = st.slider("캐릭터 상하 위치", 80, 220, 142, key="v48_editor_char_y")
            text_y = st.slider("문구 상하 위치", 190, 310, 250, key="v48_editor_text_y")

        st.markdown("### 3) 편집 패키지 생성")
        p1, p2, p3 = st.columns(3)
        with p1:
            edit_project_name = st.text_input("편집 프로젝트명", value="v18_part_motion_editor", key="v48_edit_project_name")
        with p2:
            edit_format = st.selectbox("편집 포맷", list(FORMAT_LABELS.keys()), format_func=lambda k: FORMAT_LABELS.get(k, k), index=list(FORMAT_LABELS.keys()).index(source_report.get("format_key", "static_text")) if source_report.get("format_key", "static_text") in FORMAT_LABELS else 1, key="v48_edit_format")
        with p3:
            preview_limit = st.slider("미리보기 생성 수", 8, min(40, max(8, len(selected_expressions))), min(32, max(8, len(selected_expressions))), key="v48_edit_preview_limit")

        if st.button("표정·파츠 편집 결과 생성", type="primary"):
            try:
                overrides = {
                    "eye_style": eye_choice,
                    "brow_style": brow_choice,
                    "mouth_style": mouth_choice,
                    "body_motion": body_choice,
                    "text_motion": text_motion_choice,
                    "effects": effect_choice,
                    "font_size": font_size,
                    "char_x": char_x,
                    "char_y": char_y,
                    "text_x": 180,
                    "text_y": text_y,
                }
                report = editor.build_edit_pack(
                    expressions=selected_expressions,
                    output_dir=BASE_OUTPUT / "part_motion_editor",
                    project_name=edit_project_name,
                    format_key=edit_format,
                    global_overrides=overrides,
                    preview_limit=preview_limit,
                )
                st.session_state.part_edit_report = report.to_dict()
                st.success("표정·파츠·문구·움직임 편집 결과 생성 완료")
            except Exception as exc:
                st.error(f"표정/파츠 편집 실패: {exc}")

    if st.session_state.get("part_edit_report"):
        report = st.session_state.part_edit_report
        st.markdown("### 편집 결과 요약")
        c1, c2, c3 = st.columns(3)
        c1.metric("원본 표현", report.get("source_count", 0))
        c2.metric("편집 표현", report.get("edited_count", 0))
        c3.metric("포맷", FORMAT_LABELS.get(report.get("format_key", ""), report.get("format_key", "")))

        st.markdown("### 편집 미리보기")
        preview_files = report.get("preview_files", [])
        pcols = st.columns(4)
        for idx, item in enumerate(preview_files[:32]):
            fp = Path(item.get("file_path", ""))
            if fp.exists():
                with pcols[idx % 4]:
                    st.image(str(fp), caption=item.get("phrase", ""), width=140)

        st.markdown("### 최종 확인표")
        st.dataframe(pd.DataFrame(report.get("final_check_table", [])), use_container_width=True)
        st.markdown("### 움직이는 문구 타임라인 예시")
        st.dataframe(pd.DataFrame(report.get("timeline_table", [])), use_container_width=True)
        st.markdown("### 편집 표현표")
        edit_df = pd.DataFrame(report.get("edited_expressions", []))
        show_cols = [c for c in ["selected_no", "category", "phrase", "face_summary", "manual_edited"] if c in edit_df.columns]
        if show_cols:
            st.dataframe(edit_df[show_cols], use_container_width=True)

        for label, path_key, mime in [
            ("표정/파츠 편집 HTML 다운로드", "html_path", "text/html"),
            ("표정/파츠 편집 JSON 다운로드", "json_path", "application/json"),
            ("표정/파츠 편집 CSV 다운로드", "csv_path", "text/csv"),
            ("표정/파츠 편집 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 16:
    st.subheader("카카오톡 채팅창 미리보기 / 최종 검수")
    st.write("v18에서는 선택된 24개/32개 표현을 실제 채팅창처럼 흰 배경·어두운 배경·작은 크기로 확인하고, 문구 가독성/잘림/작은 화면 인식성을 점검합니다.")

    part_report = st.session_state.get("part_edit_report")
    gallery_report = st.session_state.get("candidate_gallery_report")
    source_name = "표정/파츠 편집 결과"
    source_expressions = []
    source_previews = []
    source_format = "static_text"

    if part_report:
        source_expressions = part_report.get("edited_expressions", [])
        source_previews = part_report.get("preview_files", [])
        source_format = part_report.get("format_key", "static_text")
        source_name = "16번 표정/파츠 편집 결과"
    elif gallery_report:
        source_expressions = gallery_report.get("selected_expressions", [])
        source_previews = gallery_report.get("generated_files", [])
        source_format = gallery_report.get("format_key", "static_text")
        source_name = "15번 후보 갤러리 선택 결과"

    if not source_expressions:
        st.info("먼저 15번 후보 갤러리에서 세트를 선택하거나, 16번 표정/파츠 편집 결과를 생성하세요. 그러면 이 탭에서 실제 채팅창 미리보기를 만들 수 있습니다.")
    else:
        st.success(f"불러온 소스: {source_name} · 표현 {len(source_expressions)}개")
        settings_col1, settings_col2, settings_col3 = st.columns(3)
        with settings_col1:
            chat_project_name = st.text_input("채팅 미리보기 프로젝트명", value="v18_chat_preview_final_review")
            preview_limit = st.slider("채팅 미리보기 생성 수", 4, min(40, max(4, len(source_expressions))), min(16, max(4, len(source_expressions))))
        with settings_col2:
            chat_format = st.selectbox("검수 포맷", list(FORMAT_LABELS.keys()), format_func=lambda k: FORMAT_LABELS.get(k, k), index=list(FORMAT_LABELS.keys()).index(source_format) if source_format in FORMAT_LABELS else 1)
            include_dark = st.checkbox("어두운 채팅창 배경도 검사", value=True)
        with settings_col3:
            include_small = st.checkbox("작은 크기 미리보기도 생성", value=True)
            st.caption("작은 화면에서 문구와 표정이 읽히는지 확인하기 위한 옵션입니다.")

        st.markdown("### 불러온 표현 일부")
        source_df = pd.DataFrame(source_expressions[:20])
        show_cols = [c for c in ["selected_no", "category", "phrase", "face_summary", "motion_hint"] if c in source_df.columns]
        if show_cols:
            st.dataframe(source_df[show_cols], use_container_width=True)
        else:
            st.dataframe(source_df, use_container_width=True)

        if st.button("채팅창 미리보기/최종검수 생성", type="primary"):
            try:
                report = ChatPreviewReviewer().build_preview_pack(
                    expressions=source_expressions,
                    output_dir=BASE_OUTPUT / "chat_preview_final_review",
                    project_name=chat_project_name,
                    format_key=chat_format,
                    preview_files=source_previews,
                    preview_limit=preview_limit,
                    include_dark=include_dark,
                    include_small=include_small,
                )
                st.session_state.chat_preview_report = report.to_dict()
                st.success("채팅창 미리보기/최종검수 리포트 생성 완료")
            except Exception as exc:
                st.error(f"채팅창 미리보기 생성 실패: {exc}")

    if st.session_state.get("chat_preview_report"):
        report = st.session_state.chat_preview_report
        st.markdown("### v18 최종 검수 요약")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("채팅 사용성 점수", report.get("chat_usability_score", 0))
        c2.metric("판정", report.get("final_status", ""))
        c3.metric("검사 표현", report.get("source_count", 0))
        c4.metric("미리보기 이미지", report.get("preview_count", 0))

        st.markdown("### 표현별 최종 검수표")
        st.dataframe(pd.DataFrame(report.get("review_table", [])), use_container_width=True)

        st.markdown("### 카카오톡 채팅창 미리보기")
        preview_files = report.get("preview_files", [])
        cols = st.columns(3)
        for idx, item in enumerate(preview_files[:24]):
            fp = Path(item.get("file_path", ""))
            if fp.exists():
                with cols[idx % 3]:
                    st.image(str(fp), caption=f"{item.get('phrase','')} · {item.get('theme','')} · {item.get('scale','')}", use_container_width=True)

        for label, path_key, mime in [
            ("채팅 미리보기 HTML 다운로드", "html_path", "text/html"),
            ("채팅 미리보기 JSON 다운로드", "json_path", "application/json"),
            ("최종 검수 CSV 다운로드", "csv_path", "text/csv"),
            ("채팅 미리보기 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 17:
    st.subheader("첫 실제 샘플 세트 제작 모드")
    st.write("v18에서는 보리와 쌀 같은 소재를 기준으로 표현 후보 생성부터 24개/32개 세트 선별, 표정/파츠 편집, 채팅창 미리보기, 제출 패키지, 품질검사까지 한 번에 실행합니다.")

    builder = SampleSetBuilder()
    st.markdown("### 1) 샘플 캐릭터 소재 설정")
    use_default_sample = st.checkbox("기본 예시 사용: 보리와 쌀", value=True)

    sample_specs = []
    if use_default_sample:
        sample_specs = builder.default_materials()
        st.info("기본값: 보리 = 까칠하지만 은근히 챙김 / 쌀 = 온순하고 다정함")
    else:
        material_count = st.slider("소재 수", 1, 5, 2, key="sample_material_count")
        for i in range(material_count):
            with st.expander(f"소재 {i+1} 설정", expanded=(i < 2)):
                c1, c2, c3 = st.columns(3)
                with c1:
                    name = st.text_input(f"소재 {i+1} 이름", value=["보리","쌀","감자","고구마","메모지"][i], key=f"sample_name_{i}")
                    color = st.text_input(f"소재 {i+1} 색상", value=["연갈색","아이보리","연노랑","주황","회색"][i], key=f"sample_color_{i}")
                with c2:
                    personality = st.text_input(f"소재 {i+1} 성격", value=["까칠하지만 은근히 챙김","온순하고 다정함","피곤하지만 성실함","느긋하고 포근함","업무에 눌려 구겨짐"][i], key=f"sample_personality_{i}")
                    tone = st.text_input(f"소재 {i+1} 말투", value=["투덜거림, 짧게 말함","부드럽고 위로하는 말투","작게 한숨 섞인 말투","느긋하고 둥근 말투","짧은 업무 답장 말투"][i], key=f"sample_tone_{i}")
                with c3:
                    shape = st.selectbox(f"소재 {i+1} 기본 도형", ["둥근형","알갱이형","길쭉형","납작형","네모형"], index=min(i,4), key=f"sample_shape_{i}")
                    role = st.text_input(f"소재 {i+1} 역할", value=["중심","보조","리액션","확장","문구 담당"][i], key=f"sample_role_{i}")
                sample_specs.append(MaterialSpec(name=name, color=color, personality=personality, tone=tone, base_shape=shape, role=role))

    st.markdown("### 2) 샘플 세트 포맷 선택")
    a, b, c, d = st.columns(4)
    with a:
        sample_project_name = st.text_input("샘플 프로젝트명", value="보리와쌀_첫샘플세트", key="v48_sample_project_name")
    with b:
        sample_format = st.selectbox("샘플 포맷", ["static_text", "animated_text", "static", "animated", "big"], format_func=lambda k: FORMAT_LABELS.get(k, k), index=0, key="v48_sample_format")
    with c:
        default_count = PLANNING_COUNTS.get(sample_format, 32)
        sample_target_count = st.number_input("최종 표현 수", min_value=4, max_value=40, value=int(default_count), key="v48_sample_target_count")
    with d:
        sample_expression_count = st.number_input("표현 후보 수", min_value=40, max_value=140, value=80, step=10, key="v48_sample_expression_count")

    e1, e2, e3 = st.columns(3)
    with e1:
        sample_preview_limit = st.slider("채팅/편집 미리보기 수", 4, 24, 12, key="v48_sample_preview_limit")
    with e2:
        sample_include_dark = st.checkbox("어두운 배경 미리보기 포함", value=True, key="sample_dark")
    with e3:
        sample_include_small = st.checkbox("작은 크기 미리보기 포함", value=True, key="sample_small")

    st.markdown("### 3) 한 번에 샘플 세트 생성")
    if st.button("첫 실제 샘플 세트 생성", type="primary"):
        try:
            report = builder.build_sample_set(
                specs=sample_specs,
                output_dir=BASE_OUTPUT / "sample_sets",
                project_name=sample_project_name,
                format_key=sample_format,
                target_count=int(sample_target_count),
                expression_count=int(sample_expression_count),
                preview_limit=int(sample_preview_limit),
                include_dark=sample_include_dark,
                include_small=sample_include_small,
            )
            st.session_state.sample_set_report = report.to_dict()
            st.success("첫 실제 샘플 세트 생성 완료")
        except Exception as exc:
            st.error(f"샘플 세트 생성 실패: {exc}")

    if st.session_state.get("sample_set_report"):
        report = st.session_state.sample_set_report
        st.markdown("### v18 샘플 세트 결과")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("샘플 점수", report.get("sample_score", 0))
        r2.metric("판정", report.get("sample_status", ""))
        r3.metric("선택 표현", report.get("selected_count", 0))
        r4.metric("포맷", FORMAT_LABELS.get(report.get("format_key", ""), report.get("format_key", "")))

        st.markdown("### 생성 단계")
        st.dataframe(pd.DataFrame(report.get("pipeline_steps", [])), use_container_width=True)
        st.markdown("### 최종 선택 표현/표정/움직임")
        st.dataframe(pd.DataFrame(report.get("selected_expression_table", [])), use_container_width=True)

        # 채팅 미리보기 일부를 바로 표시
        chat = report.get("chat_preview_report", {})
        preview_files = chat.get("preview_files", [])
        if preview_files:
            st.markdown("### 채팅창 미리보기 일부")
            cols = st.columns(3)
            for idx, item in enumerate(preview_files[:12]):
                fp = Path(item.get("file_path", ""))
                if fp.exists():
                    with cols[idx % 3]:
                        st.image(str(fp), caption=f"{item.get('phrase','')} · {item.get('theme','')} · {item.get('scale','')}", use_container_width=True)

        for label, path_key, mime in [
            ("v18 샘플 세트 HTML 다운로드", "html_path", "text/html"),
            ("v18 샘플 세트 JSON 다운로드", "json_path", "application/json"),
            ("선택 표현 CSV 다운로드", "csv_path", "text/csv"),
            ("전체 샘플 세트 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)

        output_files = report.get("output_files", {})
        for label, key, mime in [
            ("제출 준비 ZIP 다운로드", "submission_zip", "application/zip"),
            ("최종 품질검사 HTML 다운로드", "quality_html", "text/html"),
            ("채팅 미리보기 HTML 다운로드", "chat_preview_html", "text/html"),
        ]:
            fp = Path(output_files.get(key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 18:
    st.subheader("데이터 보호 / 백업 / 마이그레이션")
    st.write("기능 추가·수정·버전업 전에 기존 프로젝트, outputs, 심사 기록, 리포트, API 설정 자료가 날아가지 않도록 백업과 검증을 수행합니다.")
    manager = DataSafetyManager()
    dirs = manager.ensure_user_data_dirs(Path.cwd())
    st.markdown("### 보호 기준")
    st.info("코드 폴더와 사용자 데이터 폴더를 분리하고, 업데이트 전 자동 백업 ZIP + SHA-256 검증값을 생성합니다. 복구는 기본적으로 별도 폴더에 안전 복원하여 기존 데이터를 바로 덮어쓰지 않습니다.")
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.markdown("#### 사용자 데이터 폴더")
        st.code("\n".join([f"{k}: {v}" for k, v in dirs.items()]), language="text")
    with dcol2:
        st.markdown("#### 보호 대상")
        st.markdown("- outputs 폴더\n- projects/data/settings/user_data 폴더\n- 심사/판매 기록 JSON/CSV\n- 제출 패키지 ZIP\n- 품질검사/저작권/채팅 미리보기 리포트\n- 사용자가 추가 지정한 폴더")

    backup_project_name = st.text_input("백업 이름", value="kakao_emoticon_v19_backup")
    extra_backup_path = st.text_input("추가로 백업할 폴더/파일 경로선택사항", value="")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("업데이트 전 백업 생성", type="primary"):
            extras = [extra_backup_path] if extra_backup_path.strip() else []
            try:
                report = manager.create_backup(
                    root=Path.cwd(),
                    project_name=backup_project_name,
                    extra_paths=extras,
                    output_dir=BASE_OUTPUT / "data_safety",
                )
                st.session_state.data_safety_report = report.to_dict()
                st.success("백업 생성 완료")
            except Exception as exc:
                st.error(f"백업 생성 실패: {exc}")
    with b2:
        backup_to_verify = st.text_input("검증할 백업 ZIP 경로", value="", key="verify_backup_path")
        if st.button("백업 무결성 검증"):
            try:
                path = backup_to_verify or (st.session_state.get("data_safety_report") or {}).get("backup_zip_path", "")
                report = manager.verify_backup(path, output_dir=BASE_OUTPUT / "data_safety", project_name=backup_project_name)
                st.session_state.data_safety_report = report.to_dict()
                st.success("백업 검증 완료")
            except Exception as exc:
                st.error(f"백업 검증 실패: {exc}")
    with b3:
        backup_to_restore = st.text_input("안전 복원할 백업 ZIP 경로", value="", key="restore_backup_path")
        if st.button("별도 폴더에 안전 복원"):
            try:
                path = backup_to_restore or (st.session_state.get("data_safety_report") or {}).get("backup_zip_path", "")
                report = manager.restore_backup_safe(path, output_dir=BASE_OUTPUT / "data_safety", project_name=backup_project_name)
                st.session_state.data_safety_report = report.to_dict()
                st.success("안전 복원 완료 · 기존 파일은 덮어쓰지 않았습니다")
            except Exception as exc:
                st.error(f"안전 복원 실패: {exc}")

    st.markdown("### 구버전 데이터 이전")
    old_version_path = st.text_input("구버전 프로그램 폴더 경로", value="")
    if st.button("구버전 데이터 백업 후 이전"):
        try:
            report = manager.migrate_from_old_version(
                old_root=old_version_path,
                new_root=Path.cwd(),
                output_dir=BASE_OUTPUT / "data_safety",
                project_name="v19_migration",
            )
            st.session_state.data_safety_report = report.to_dict()
            st.success("구버전 데이터 이전 점검 완료")
        except Exception as exc:
            st.error(f"마이그레이션 실패: {exc}")

    if st.session_state.get("data_safety_report"):
        report = st.session_state.data_safety_report
        st.markdown("### 데이터 보호 리포트")
        c1, c2, c3 = st.columns(3)
        c1.metric("상태", report.get("overall_status", ""))
        c2.metric("점수", report.get("score", 0))
        c3.metric("작업", report.get("action", ""))
        if report.get("backup_zip_path"):
            st.code(f"백업 ZIP: {report.get('backup_zip_path')}\nSHA-256: {report.get('backup_sha256')}", language="text")
        items = report.get("items", [])
        if items:
            st.dataframe(pd.DataFrame(items), use_container_width=True)
        for label, key, mime in [
            ("데이터 보호 HTML 다운로드", "html_path", "text/html"),
            ("데이터 보호 JSON 다운로드", "json_path", "application/json"),
            ("데이터 보호 CSV 다운로드", "csv_path", "text/csv"),
            ("백업 ZIP 다운로드", "backup_zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 19:
    st.subheader("누적 데이터 성장형 추천 엔진")
    st.write("트렌드·제작·품질검사·채팅 미리보기·저작권 방어·심사/판매 기록을 계속 누적해 다음 캐릭터/포맷/문구 추천을 보정합니다.")
    engine = GrowthLearningEngine()
    c1, c2 = st.columns([1, 1])
    with c1:
        growth_project_name = st.text_input("학습 저장 프로젝트명", value="kakao_growth_learning")
        concept_text = st.text_area("현재 프로젝트 핵심 콘셉트", value="보리와 쌀, 문구 결합형 이모티콘, 직접 창작 기반", height=90)
        if st.button("현재 세션 데이터를 학습 데이터로 저장", type="primary"):
            save_result = engine.record_snapshot(
                project_name=growth_project_name,
                concept_text=concept_text,
                profile=st.session_state.profile,
                expressions=st.session_state.expressions,
                format_scores=st.session_state.format_scores,
                trend_result=st.session_state.trend_result,
                api_trend_report=st.session_state.api_trend_report,
                candidate_gallery_report=st.session_state.candidate_gallery_report,
                quality_review=st.session_state.quality_review,
                chat_preview_report=st.session_state.chat_preview_report,
                copyright_report=st.session_state.copyright_defense_report,
                sample_set_report=st.session_state.sample_set_report,
            )
            st.session_state.growth_learning_save_result = save_result
            st.success("현재 세션 데이터가 성장형 학습 데이터에 누적 저장되었습니다.")
    with c2:
        st.markdown("#### 심사/판매 결과 수동 기록")
        outcome_character = st.text_input("캐릭터명", value="보리와 쌀")
        outcome_format = st.selectbox("포맷", options=["static_text", "animated_text", "static", "animated", "big"], format_func=lambda x: GrowthLearningEngine.FORMAT_KEYS.get(x, x))
        outcome_status = st.selectbox("상태", options=["준비", "제출", "승인", "반려", "수정 후 재제출", "출시", "판매 반응 양호", "판매 반응 낮음"])
        outcome_reason = st.text_area("반려/수정/판매 메모", value="", height=80)
        outcome_revenue = st.number_input("누적 수익 메모용 금액", min_value=0.0, value=0.0, step=1000.0)
        outcome_sales = st.number_input("판매/다운로드/반응 수치", min_value=0, value=0, step=1)
        if st.button("심사/판매 결과 누적 저장"):
            saved = engine.record_outcome(
                project_name=growth_project_name,
                character_name=outcome_character,
                format_key=outcome_format,
                status=outcome_status,
                rejection_reason=outcome_reason,
                revenue_amount=outcome_revenue,
                downloads_or_sales_count=outcome_sales,
            )
            st.session_state.growth_learning_save_result = saved
            st.success("심사/판매 결과가 성장형 학습 데이터에 저장되었습니다.")

    st.divider()
    if st.button("성장형 학습 리포트 생성"):
        report = engine.build_growth_report(project_name="growth_learning_report", output_dir=BASE_OUTPUT / "growth_learning_reports")
        st.session_state.growth_learning_report = report.to_dict()
        st.success("성장형 학습 리포트 생성 완료")

    if st.session_state.get("growth_learning_save_result"):
        st.markdown("### 최근 저장 결과")
        st.code(json.dumps(st.session_state.growth_learning_save_result, ensure_ascii=False, indent=2), language="json")

    if st.session_state.get("growth_learning_report"):
        report = st.session_state.growth_learning_report
        st.markdown("### 성장형 학습 리포트")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("학습 단계", report.get("learning_level", ""))
        m2.metric("신뢰도", report.get("confidence_score", 0))
        m3.metric("스냅샷", report.get("total_events", 0))
        m4.metric("결과 기록", report.get("total_outcomes", 0))
        if report.get("recommended_formats"):
            st.markdown("#### 추천 포맷")
            st.dataframe(pd.DataFrame(report.get("recommended_formats", [])), use_container_width=True)
        if report.get("recommended_keywords"):
            st.markdown("#### 반복 키워드")
            st.dataframe(pd.DataFrame(report.get("recommended_keywords", [])), use_container_width=True)
        for action in report.get("improvement_actions", []):
            st.info(action)
        for label, key, mime in [
            ("성장 리포트 HTML 다운로드", "html_path", "text/html"),
            ("성장 리포트 JSON 다운로드", "json_path", "application/json"),
            ("성장 점수 CSV 다운로드", "csv_path", "text/csv"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 20:
    st.subheader("초보자 전체 제작 마법사")
    st.write("처음 사용하는 사람이 순서대로 진행할 수 있도록, 소재 선택부터 샘플 세트 생성·채팅 미리보기·제출 패키지·품질검사까지 한 화면에서 안내합니다.")
    st.info("기존 기능은 삭제하지 않고, 전체 흐름을 한 번에 묶어주는 안내/자동 실행 모드입니다. 결과물은 제출 보조용이며 승인이나 수익을 보장하지 않습니다.")

    wizard = WorkflowWizard()
    wc1, wc2, wc3 = st.columns([1, 1, 1])
    with wc1:
        wiz_project = st.text_input("마법사 프로젝트명", value="보리와쌀_초보자_마법사", key="wizard_project")
        wiz_format = st.selectbox(
            "목표 포맷",
            options=["static_text", "animated_text", "static", "animated", "big"],
            format_func=lambda x: FORMAT_LABELS.get(x, x),
            index=0,
            key="wizard_format",
        )
    with wc2:
        wiz_target = st.number_input("최종 세트 수", min_value=8, max_value=40, value=int(PLANNING_COUNTS.get(st.session_state.get('wizard_format', 'static_text'), 32)), step=1, key="wizard_target")
        wiz_expression_count = st.number_input("표현 후보 수", min_value=40, max_value=140, value=80, step=10, key="wizard_expression_count")
    with wc3:
        run_sample = st.checkbox("첫 샘플 세트까지 자동 생성", value=True, key="wizard_run_sample")
        include_dark = st.checkbox("어두운 배경 미리보기 포함", value=True, key="wizard_dark")
        include_small = st.checkbox("작은 크기 미리보기 포함", value=True, key="wizard_small")

    st.markdown("### 소재 설정")
    use_existing_specs = st.checkbox("14번 탭의 멀티소재 설정이 있으면 사용", value=True)
    wizard_specs = []
    if use_existing_specs and st.session_state.get("multi_material_creator_report"):
        saved_specs = st.session_state.multi_material_creator_report.get("material_specs", [])
        if saved_specs:
            wizard_specs = saved_specs
            st.success(f"저장된 멀티소재 {len(saved_specs)}개를 불러왔습니다.")
            st.dataframe(pd.DataFrame(saved_specs), use_container_width=True)
    if not wizard_specs:
        st.caption("기본값은 보리와 쌀 듀오입니다. 필요하면 아래에서 최대 5개까지 바꿔서 실행하세요.")
        count = st.slider("마법사용 소재 수", 1, 5, 2, key="wizard_material_count")
        default_names = ["보리", "쌀", "감자", "고구마", "메모지"]
        default_colors = ["연갈색", "아이보리", "연노랑", "주황", "회색"]
        default_personalities = ["까칠하지만 은근히 챙김", "온순하고 다정함", "피곤하지만 성실함", "느긋하고 포근함", "업무에 눌려 구겨짐"]
        default_tones = ["투덜거림, 짧게 말함", "부드럽고 위로하는 말투", "작게 한숨 섞인 말투", "느긋하고 둥근 말투", "짧은 업무 답장 말투"]
        default_shapes = ["알갱이형", "둥근형", "둥근형", "길쭉형", "네모형"]
        default_roles = ["중심", "보조", "리액션", "확장", "문구 담당"]
        for i in range(count):
            with st.expander(f"마법사 소재 {i+1}", expanded=i < 2):
                cols = st.columns(6)
                name = cols[0].text_input("소재", value=default_names[i], key=f"wizard_name_{i}")
                color = cols[1].text_input("색상", value=default_colors[i], key=f"wizard_color_{i}")
                personality = cols[2].text_input("성격", value=default_personalities[i], key=f"wizard_personality_{i}")
                tone = cols[3].text_input("말투", value=default_tones[i], key=f"wizard_tone_{i}")
                shape = cols[4].selectbox("도형", ["둥근형", "알갱이형", "길쭉형", "납작형", "네모형"], index=["둥근형", "알갱이형", "길쭉형", "납작형", "네모형"].index(default_shapes[i]) if default_shapes[i] in ["둥근형", "알갱이형", "길쭉형", "납작형", "네모형"] else 0, key=f"wizard_shape_{i}")
                role = cols[5].text_input("역할", value=default_roles[i], key=f"wizard_role_{i}")
                wizard_specs.append({"name": name, "color": color, "personality": personality, "tone": tone, "base_shape": shape, "role": role})

    st.markdown("### 마법사 진행 단계 미리보기")
    preview_steps = []
    for no, title, desc, output_hint, next_action in WorkflowWizard.DEFAULT_STEPS:
        preview_steps.append({"번호": no, "단계": title, "설명": desc, "생성/확인": output_hint})
    st.dataframe(pd.DataFrame(preview_steps), use_container_width=True, hide_index=True)

    if st.button("초보자 전체 제작 마법사 실행", type="primary"):
        try:
            report = wizard.build_wizard_report(
                specs=wizard_specs,
                output_dir=BASE_OUTPUT / "workflow_wizard",
                project_name=wiz_project,
                format_key=wiz_format,
                target_count=int(wiz_target),
                expression_count=int(wiz_expression_count),
                completed_step_count=0,
                run_sample_generation=run_sample,
                include_dark=include_dark,
                include_small=include_small,
            )
            st.session_state.workflow_wizard_report = report.to_dict()
            if report.sample_set_report:
                st.session_state.sample_set_report = report.sample_set_report
            st.success("초보자 전체 제작 마법사 실행 완료")
        except Exception as exc:
            st.error(f"마법사 실행 실패: {exc}")

    if st.session_state.get("workflow_wizard_report"):
        report = st.session_state.workflow_wizard_report
        st.markdown("### 마법사 결과")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("진행률", f"{report.get('progress_percent', 0)}%")
        m2.metric("현재 단계", report.get("current_phase", "-"))
        m3.metric("소재 수", report.get("material_count", 0))
        m4.metric("목표 수", report.get("target_count", 0))
        st.info(report.get("next_recommended_step", ""))
        st.dataframe(pd.DataFrame(report.get("wizard_steps", [])), use_container_width=True)
        if report.get("sample_set_report"):
            st.markdown("#### 자동 생성된 첫 샘플 세트 요약")
            sr = report["sample_set_report"]
            s1, s2, s3 = st.columns(3)
            s1.metric("상태", sr.get("sample_status", "-"))
            s2.metric("점수", sr.get("sample_score", 0))
            s3.metric("선택 표현", sr.get("selected_count", 0))
        for label, key, mime in [
            ("마법사 HTML 다운로드", "html_path", "text/html"),
            ("마법사 JSON 다운로드", "json_path", "application/json"),
            ("마법사 CSV 다운로드", "csv_path", "text/csv"),
            ("마법사 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 21:
    st.subheader("직접 그리기 캔버스 / 레이어 편집기")
    st.write("사진이나 스케치 첨부 없이도 프로그램 안에서 도형·눈·입·팔·효과·문구를 선택해 360×360 투명 PNG 원본을 만들 수 있습니다.")
    st.info("이 기능은 AI 완성본을 숨기는 방식이 아니라, 사용자가 직접 선택한 파츠와 색상으로 창작 출발점을 기록하는 기능입니다. 레이어별 PNG와 체크섬도 같이 저장합니다.")

    canvas_editor = DrawingCanvasLayerEditor()
    dc1, dc2, dc3 = st.columns([1, 1, 1])
    with dc1:
        canvas_project = st.text_input("캔버스 프로젝트명", value="보리쌀_직접도형원본", key="canvas_project")
        canvas_label = st.text_input("캐릭터/문구 라벨", value="보리쌀", key="canvas_label")
        base_color = st.color_picker("몸통/얼굴 기본색", value="#D1A164", key="canvas_base_color")
    with dc2:
        face_preset = st.selectbox("얼굴/몸통 기본형", options=["둥근 얼굴+알갱이 몸통", "둥근 얼굴+쌀알 몸통", "둥근 얼굴+길쭉 몸통", "동그라미 얼굴만"], index=0)
        eye_preset = st.selectbox("눈 후보", options=["점눈", "반눈"], index=0, key="v48_canvas_eye_preset")
        mouth_preset = st.selectbox("입 후보", options=["웃는 입", "무표정 입", "삐죽 입"], index=0, key="v48_canvas_mouth_preset")
    with dc3:
        add_arms = st.checkbox("팔 추가", value=True)
        add_sweat = st.checkbox("땀 효과", value=False)
        add_heart = st.checkbox("하트 효과", value=False)
        add_bubble = st.checkbox("말풍선/라벨 영역", value=True)

    preset_names = []
    if "둥근 얼굴" in face_preset:
        preset_names.append("둥근 얼굴")
    if "알갱이 몸통" in face_preset:
        preset_names.append("알갱이 몸통")
    elif "쌀알 몸통" in face_preset:
        preset_names.append("쌀알 몸통")
    elif "길쭉 몸통" in face_preset:
        preset_names.append("길쭉 몸통")
    if eye_preset == "점눈":
        preset_names.extend(["점눈 왼쪽", "점눈 오른쪽"])
    else:
        preset_names.extend(["반눈 왼쪽", "반눈 오른쪽"])
    preset_names.append(mouth_preset)
    if add_arms:
        preset_names.extend(["왼팔", "오른팔"])
    if add_sweat:
        preset_names.append("땀 효과")
    if add_heart:
        preset_names.append("하트 효과")
    if add_bubble:
        preset_names.append("말풍선")

    layers = canvas_editor.build_layers_from_presets(preset_names, base_color=base_color, label_text=canvas_label if add_bubble else "")

    st.markdown("### 레이어 미세 조정")
    edited_layers = []
    layer_rows = []
    for i, layer in enumerate(layers):
        with st.expander(f"{i+1}. {layer.layer_id} · {layer.layer_type}/{layer.shape}", expanded=False):
            cols = st.columns(6)
            visible = cols[0].checkbox("표시", value=layer.visible, key=f"canvas_vis_{i}")
            x = cols[1].slider("X", 0, 360, int(layer.x), key=f"canvas_x_{i}")
            y = cols[2].slider("Y", 0, 360, int(layer.y), key=f"canvas_y_{i}")
            w = cols[3].slider("W", 4, 320, int(layer.w), key=f"canvas_w_{i}")
            h = cols[4].slider("H", 4, 320, int(layer.h), key=f"canvas_h_{i}")
            fill = cols[5].color_picker("색", value=layer.fill_color if str(layer.fill_color).startswith("#") else "#D1A164", key=f"canvas_fill_{i}")
            text_val = layer.text
            if layer.layer_type == "text":
                text_val = st.text_input("표시 문구", value=layer.text, key=f"canvas_text_{i}")
            new_layer = CanvasLayer(
                layer_id=layer.layer_id,
                layer_type=layer.layer_type,
                shape=layer.shape,
                x=int(x), y=int(y), w=int(w), h=int(h),
                fill_color=fill,
                outline_color=layer.outline_color,
                stroke_width=layer.stroke_width,
                text=text_val,
                opacity=layer.opacity,
                visible=visible,
                note=layer.note,
            )
            edited_layers.append(new_layer)
            layer_rows.append(new_layer.to_dict())
    st.dataframe(pd.DataFrame(layer_rows), use_container_width=True)

    preview_img = canvas_editor.render_canvas(edited_layers, background=(250, 250, 250, 255))
    transparent_img = canvas_editor.render_canvas(edited_layers)
    pc1, pc2 = st.columns(2)
    with pc1:
        st.markdown("#### 배경 포함 미리보기")
        st.image(preview_img, width=260)
    with pc2:
        st.markdown("#### 투명 PNG 미리보기")
        st.image(transparent_img, width=260)

    if st.button("직접 그리기 원본/레이어 저장", type="primary"):
        try:
            report = canvas_editor.build_canvas_project(
                layers=edited_layers,
                output_dir=BASE_OUTPUT / "direct_canvas_layer_editor",
                project_name=canvas_project,
            )
            st.session_state.drawing_canvas_report = report.to_dict()
            st.success("직접 그리기 캔버스 원본과 레이어가 저장되었습니다.")
        except Exception as exc:
            st.error(f"저장 실패: {exc}")

    if st.session_state.get("drawing_canvas_report"):
        report = st.session_state.drawing_canvas_report
        st.markdown("### 직접 그리기 캔버스 저장 결과")
        m1, m2, m3 = st.columns(3)
        m1.metric("레이어 수", report.get("layer_count", 0))
        m2.metric("원본 SHA-256", str(report.get("checksum_sha256", ""))[:12] + "...")
        m3.metric("상태", "저장 완료")
        png_path = Path(report.get("transparent_png_path", ""))
        if png_path.exists():
            st.image(str(png_path), width=220)
        for label, key, mime in [
            ("투명 PNG 다운로드", "transparent_png_path", "image/png"),
            ("리포트 HTML 다운로드", "html_path", "text/html"),
            ("레이어 CSV 다운로드", "csv_path", "text/csv"),
            ("전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 22:
    st.subheader("캐릭터 일관성 검사 / 자동 보정")
    st.write("24개/32개 최종 세트가 같은 캐릭터처럼 보이는지 색상·중심·크기·문구 길이·표정 계획 기준으로 검사합니다.")
    source_options = {
        "표정/파츠 편집 결과": st.session_state.get("part_edit_report"),
        "후보 갤러리 선택 결과": st.session_state.get("candidate_gallery_report"),
        "첫 샘플 세트 결과": st.session_state.get("sample_set_report"),
        "표현 은행 전체": None,
    }
    selected_source = st.selectbox("검사 대상", list(source_options.keys()), key="v48_consistency_source")
    format_key = st.selectbox("포맷", list(FORMAT_LABELS.keys()), format_func=lambda x: FORMAT_LABELS.get(x, x), index=1, key="v48_consistency_format_key")
    preview_limit = st.slider("보정 미리보기 생성 개수", 4, 32, 16, key="v48_consistency_preview_limit")
    auto_correct = st.checkbox("중심/크기/대표색 자동 보정 미리보기 생성", value=True, key="v48_consistency_auto_correct")
    project_name_consistency = st.text_input("일관성 검사 프로젝트명", value="barley_rice_consistency_check", key="v48_consistency_project_name")

    def _resolve_consistency_source():
        report = source_options.get(selected_source)
        expressions = []
        previews = []
        if isinstance(report, dict):
            if report.get("edited_expressions"):
                expressions = report.get("edited_expressions") or []
                previews = report.get("preview_files") or []
            elif report.get("selected_expressions"):
                expressions = report.get("selected_expressions") or []
                previews = report.get("generated_files") or []
            elif report.get("selected_expressions"):
                expressions = report.get("selected_expressions") or []
            elif report.get("candidate_gallery_report"):
                c = report.get("candidate_gallery_report") or {}
                expressions = c.get("selected_expressions") or []
                previews = c.get("generated_files") or []
        if not expressions and selected_source == "표현 은행 전체":
            expressions = st.session_state.get("expressions") or []
        # Convert dataclass objects if necessary.
        converted = []
        for e in expressions:
            if hasattr(e, "to_dict"):
                converted.append(e.to_dict())
            elif isinstance(e, dict):
                converted.append(e)
        return converted, previews

    exprs, previews = _resolve_consistency_source()
    c1, c2, c3 = st.columns(3)
    c1.metric("검사 후보 수", len(exprs))
    c2.metric("미리보기 파일 수", len(previews))
    c3.metric("자동 보정", "ON" if auto_correct else "OFF")
    if exprs:
        st.dataframe(pd.DataFrame(exprs[:20]), use_container_width=True)
    else:
        st.info("먼저 15 후보 갤러리, 16 표정/파츠 편집기, 18 첫 샘플 세트 또는 3 표현 은행을 실행하세요.")

    if st.button("세트 일관성 검사 실행", type="primary", disabled=not bool(exprs)):
        try:
            report = SetConsistencyReviewer().build_consistency_pack(
                expressions=exprs,
                preview_files=previews,
                output_dir=BASE_OUTPUT / "set_consistency_review",
                project_name=project_name_consistency,
                format_key=format_key,
                auto_correct=auto_correct,
                preview_limit=preview_limit,
            )
            st.session_state.consistency_report = report.to_dict()
            st.success("세트 일관성 검사와 자동 보정 미리보기 생성이 완료되었습니다.")
        except Exception as exc:
            st.error(f"일관성 검사 실패: {exc}")

    if st.session_state.get("consistency_report"):
        report = st.session_state.consistency_report
        st.markdown("### 일관성 검사 결과")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("일관성 점수", report.get("consistency_score", 0))
        m2.metric("판정", report.get("final_status", ""))
        m3.metric("검사 수", report.get("source_count", 0))
        m4.metric("보정 제안", len(report.get("correction_table", [])))
        st.dataframe(pd.DataFrame(report.get("review_table", [])), use_container_width=True)
        for label, key, mime in [
            ("일관성 리포트 HTML 다운로드", "html_path", "text/html"),
            ("일관성 JSON 다운로드", "json_path", "application/json"),
            ("검사표 CSV 다운로드", "csv_path", "text/csv"),
            ("일관성 보정 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 23:
    st.subheader("자유 드로잉 캔버스 강화")
    st.write("마우스, 태블릿 펜, 터치 화면 손그림으로 직접 원·눈·입·몸통을 그리고 360×360 투명 PNG 원본으로 저장합니다.")
    st.info("브라우저 자유 드로잉 도구가 설치되어 있으면 직접 그릴 수 있고, 없으면 좌표 입력/샘플 스트로크 방식으로도 원본을 만들 수 있습니다. 이 기능은 사용자의 직접 창작 출발점을 기록하기 위한 기능입니다.")

    free_canvas = FreeDrawingCanvas()
    fd1, fd2, fd3 = st.columns([1, 1, 1])
    with fd1:
        free_project = st.text_input("자유 드로잉 프로젝트명", value="보리쌀_자유손그림원본", key="free_project")
        free_color = st.color_picker("펜 색상", value="#2E2924", key="free_pen_color")
    with fd2:
        free_width = st.slider("펜 굵기", 2, 30, 8, key="free_pen_width")
        use_sample = st.checkbox("대충 원/눈/입/몸통 샘플로 시작", value=True, key="free_use_sample")
    with fd3:
        st.markdown("**지원 입력**")
        st.caption("마우스 · 태블릿 펜 · 터치 화면 · 좌표 입력 · 직접 스케치 파일")

    canvas_strokes = []
    canvas_image = None
    drawable_available = False
    try:
        from streamlit_drawable_canvas import st_canvas  # type: ignore
        drawable_available = True
    except Exception:
        drawable_available = False

    if drawable_available:
        st.markdown("### 브라우저 직접 그리기")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=int(free_width),
            stroke_color=free_color,
            background_color="rgba(255, 255, 255, 0)",
            height=360,
            width=360,
            drawing_mode="freedraw",
            key="free_drawing_canvas_widget",
        )
        if canvas_result.image_data is not None:
            try:
                from PIL import Image
                import numpy as np
                arr = canvas_result.image_data.astype("uint8")
                canvas_image = Image.fromarray(arr, mode="RGBA")
            except Exception:
                canvas_image = None
        if canvas_result.json_data:
            canvas_strokes = free_canvas.strokes_from_canvas_json(canvas_result.json_data, fallback_color=free_color, fallback_width=int(free_width))
    else:
        st.warning("선택형 브라우저 드로잉 패키지(streamlit-drawable-canvas)가 설치되어 있지 않으면 좌표 입력/샘플 스트로크로 저장됩니다. 실제 PC 설치 시 requirements에 포함되어 자동 설치를 시도합니다.")

    st.markdown("### 좌표 입력 보조")
    coord_text = st.text_area(
        "직접 좌표 입력 또는 보정용 스트로크",
        value="face: 108,125 125,80 180,55 235,80 252,125 235,170 180,195 125,170 108,125\nbody: 110,230 150,195 210,195 250,230 220,280 140,280 110,230\neye: 150,120 151,120\neye2: 210,120 211,120\nsmile: 150,150 165,165 180,172 195,165 210,150",
        height=120,
        help="예: face: 120,120 180,70 240,120 180,190 120,120",
    )
    text_strokes = free_canvas.parse_strokes_from_text(coord_text, color=free_color, width=int(free_width))
    sample_strokes = free_canvas.sample_strokes("보리쌀", color=free_color) if use_sample else []
    strokes = canvas_strokes or text_strokes or sample_strokes
    if use_sample and text_strokes:
        strokes = text_strokes + sample_strokes[:2]

    preview_img = canvas_image if canvas_image is not None else free_canvas.render_strokes(strokes, background=(250, 250, 250, 255))
    clean_preview = free_canvas.auto_clean_line_art(canvas_image if canvas_image is not None else free_canvas.render_strokes(strokes))
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("#### 배경 포함 미리보기")
        st.image(preview_img, width=260)
    with p2:
        st.markdown("#### 360×360 자동 정리 미리보기")
        st.image(clean_preview, width=260)

    st.markdown("### 스트로크 기록")
    if strokes:
        st.dataframe(pd.DataFrame([s.to_dict() | {"point_count": len(s.points)} for s in strokes]), use_container_width=True)
    else:
        st.caption("아직 저장할 스트로크가 없습니다. 브라우저 캔버스에 그리거나 좌표/샘플을 사용하세요.")

    if st.button("자유 드로잉 원본 저장", type="primary"):
        try:
            if canvas_image is not None and not strokes:
                # 브라우저에서 이미지 데이터만 들어온 경우 최소 기록용 샘플 스트로크를 함께 저장합니다.
                strokes_to_save = sample_strokes or free_canvas.sample_strokes("보리쌀", color=free_color)
            else:
                strokes_to_save = strokes or sample_strokes or free_canvas.sample_strokes("보리쌀", color=free_color)
            report = free_canvas.build_project(
                strokes=strokes_to_save,
                output_dir=BASE_OUTPUT / "free_drawing_canvas",
                project_name=free_project,
            )
            st.session_state.free_drawing_report = report.to_dict()
            st.success("자유 드로잉 원본이 저장되었습니다.")
        except Exception as exc:
            st.error(f"자유 드로잉 저장 실패: {exc}")

    if st.session_state.get("free_drawing_report"):
        report = st.session_state.free_drawing_report
        st.markdown("### 자유 드로잉 저장 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("스트로크 수", report.get("stroke_count", 0))
        c2.metric("포인트 수", report.get("point_count", 0))
        c3.metric("SHA-256", str(report.get("checksum_sha256", ""))[:12] + "...")
        img_path = Path(report.get("auto_clean_png_path", ""))
        if img_path.exists():
            st.image(str(img_path), width=220)
        for label, key, mime in [
            ("자동 정리 PNG 다운로드", "auto_clean_png_path", "image/png"),
            ("원본 투명 PNG 다운로드", "canvas_png_path", "image/png"),
            ("자유 드로잉 HTML 다운로드", "html_path", "text/html"),
            ("스트로크 CSV 다운로드", "csv_path", "text/csv"),
            ("전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)



if selected_page_index == 24:
    st.subheader("자유 드로잉 자동 정리 / 파츠 추정 / 표정 확장")
    st.write("마우스·태블릿 펜·손가락으로 대충 그린 원본을 360×360으로 정리하고, 얼굴/몸통/눈/입 후보와 표정 변형 PNG를 생성합니다.")

    refine_col1, refine_col2 = st.columns([1.1, 0.9])
    with refine_col1:
        refine_project = st.text_input("v25 프로젝트명", value="barley_rice_drawing_refine")
        refine_count = st.selectbox("스타터 표현 연결 수", [24, 32], index=1, help="표정 변형을 24개 또는 32개 제작 흐름에 연결하는 CSV/JSON을 만듭니다.")
        refine_source = st.radio(
            "원본 선택",
            ["최근 자유 드로잉 자동 정리 PNG 사용", "직접 이미지 업로드", "샘플 원/눈/입 원본 사용"],
            horizontal=False,
            key="v48_refine_source_radio",
        )
        refine_upload = None
        if refine_source == "직접 이미지 업로드":
            refine_upload = st.file_uploader("직접 그린 원본 PNG/JPG 업로드", type=["png", "jpg", "jpeg", "webp"], key="v25_refine_upload")
        run_refine = st.button("자유 드로잉 정리/파츠 추정 실행", type="primary")

    with refine_col2:
        st.markdown("### v25 처리 내용")
        st.markdown(
            """
            - 360×360 원본 자동 정리
            - 얼굴/몸통/눈/입/팔 후보 추정
            - 파츠 영역 오버레이 이미지 생성
            - 기본/웃음/감사/사과/화남/당황/피곤 등 표정 변형 생성
            - 24개/32개 세트 제작용 표정 연결표 생성
            - 원본 덮어쓰기 없이 별도 ZIP 저장
            """
        )

    if run_refine:
        try:
            engine = DrawingRefineEngine()
            source_path = None
            temp_dir = Path(tempfile.gettempdir())
            if refine_source == "최근 자유 드로잉 자동 정리 PNG 사용":
                prev = st.session_state.get("free_drawing_report") or {}
                candidate = Path(prev.get("auto_clean_png_path", ""))
                if candidate.exists():
                    source_path = candidate
                else:
                    st.warning("최근 자유 드로잉 결과가 없어 샘플 원/눈/입 원본으로 대체합니다.")
            if refine_source == "직접 이미지 업로드" and refine_upload is not None:
                suffix = Path(refine_upload.name).suffix or ".png"
                source_path = temp_dir / f"v25_uploaded_refine_source{suffix}"
                source_path.write_bytes(refine_upload.getvalue())
            if source_path is None:
                from modules.free_drawing import FreeDrawingCanvas
                sample_engine = FreeDrawingCanvas()
                sample_strokes = sample_engine.sample_strokes("보리쌀", color="#2E2924")
                sample_img = sample_engine.render_strokes(sample_strokes)
                source_path = temp_dir / "v25_sample_circle_eye_mouth.png"
                sample_img.save(source_path)
            report = engine.build_project(
                input_image_path=Path(source_path),
                output_dir=BASE_OUTPUT / "drawing_refine_v25",
                project_name=refine_project,
                starter_expression_count=int(refine_count),
                variant_count=12,
            )
            st.session_state.drawing_refine_report = report.to_dict()
            st.success("자유 드로잉 정리/파츠 추정/표정 확장이 완료되었습니다.")
        except Exception as exc:
            st.error(f"v25 처리 실패: {exc}")

    if st.session_state.get("drawing_refine_report"):
        report = st.session_state.drawing_refine_report
        st.markdown("### v25 결과")
        m1, m2, m3 = st.columns(3)
        m1.metric("파츠 후보", report.get("part_count", 0))
        m2.metric("표정 변형", report.get("variant_count", 0))
        m3.metric("표현 연결", report.get("starter_expression_count", 0))
        c1, c2 = st.columns(2)
        with c1:
            fp = Path(report.get("normalized_png_path", ""))
            if fp.exists():
                st.image(str(fp), caption="자동 정리 원본", width=220)
        with c2:
            fp = Path(report.get("parts_overlay_path", ""))
            if fp.exists():
                st.image(str(fp), caption="파츠 추정 오버레이", width=220)
        st.markdown("#### 표정 변형 미리보기")
        variant_files = report.get("variant_files", [])[:6]
        if variant_files:
            cols = st.columns(min(6, len(variant_files)))
            for idx, item in enumerate(variant_files):
                fp = Path(item.get("file_path", ""))
                if fp.exists():
                    with cols[idx % len(cols)]:
                        st.image(str(fp), caption=item.get("label", "표정"), width=120)
        if report.get("warnings"):
            st.warning(" / ".join(report.get("warnings", [])))
        for label, key, mime in [
            ("정리 원본 PNG 다운로드", "normalized_png_path", "image/png"),
            ("파츠 오버레이 PNG 다운로드", "parts_overlay_path", "image/png"),
            ("표현 연결 CSV 다운로드", "expression_csv_path", "text/csv"),
            ("v25 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v25 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 25:
    st.subheader("감정 하위표현 / 행동모션 확장 엔진")
    st.write("슬픔 하나도 눈물 한 방울·훌쩍임·엉엉·오열처럼 나누고, 따봉 하나도 한손·양손·큰손 강조·통통 모션처럼 여러 방식으로 분화합니다.")

    v26_col1, v26_col2 = st.columns([1.1, 0.9])
    with v26_col1:
        v26_project = st.text_input("v26 프로젝트명", value="barley_rice_emotion_motion", key="v48_v26_project")
        v26_character = st.text_input("캐릭터명/그룹명", value="보리와 쌀", key="v48_v26_character")
        v26_personality = st.text_area("성격 설명", value="보리는 까칠하지만 은근히 챙김, 쌀은 온순하고 다정함", height=80, key="v48_v26_personality")
        v26_tone = st.text_area("말투 설명", value="보리는 짧게 투덜거리고, 쌀은 부드럽게 위로하는 말투", height=80, key="v48_v26_tone")
        v26_format = st.selectbox("포맷", ["static_text", "animated_text", "static", "animated", "big"], index=1, format_func=lambda x: FORMAT_LABELS.get(x, x), key="v48_v26_format_key")
        v26_emotion_intensity = st.slider("감정 강도", 1, 5, 3, help="슬픔/감사/화남 같은 감정 표현을 얼마나 강하게 보일지 선택합니다.", key="v48_v26_emotion_intensity")
        v26_motion_intensity = st.slider("모션 강도", 1, 5, 3, help="따봉/꾸벅/박수/손흔들기 같은 행동모션을 얼마나 크게 보일지 선택합니다.", key="v48_v26_motion_intensity")
        v26_preview_count = st.slider("미리보기 생성 수", 6, 24, 12, key="v48_v26_preview_count")
        v26_use_existing = st.checkbox("현재 표현 은행/후보 갤러리 표현 사용", value=True, key="v48_v26_use_existing")
        run_v26 = st.button("감정/모션 확장 계획 생성", type="primary", key="v48_v26_run")
    with v26_col2:
        st.markdown("### 확장 예시")
        st.markdown("""
        **슬픔 하위표현**  
        - 눈물 한 방울 / 조용히 눈물 / 훌쩍임 / 참다가 터짐 / 엉엉 울음 / 오열 / 민망한 눈물 / 감동 눈물

        **따봉 행동모션**  
        - 한손 따봉 / 무표정 대충 따봉 / 양손 따봉 / 큰손 강조 / 통통 따봉 / 앞으로 튀어나오는 따봉

        **기준**  
        - 감정 강도, 모션 강도, 캐릭터 성격, 말투, 정지형/움직이는 문구형 포맷을 같이 반영합니다.
        """)

    if run_v26:
        try:
            engine = EmotionMotionVariationEngine()
            exprs = []
            if v26_use_existing and st.session_state.get("expressions"):
                exprs = [e if isinstance(e, dict) else e.to_dict() for e in st.session_state.expressions][:32]
            if not exprs and st.session_state.get("candidate_gallery_report"):
                exprs = st.session_state.candidate_gallery_report.get("selected_expressions", [])[:32]
            report = engine.build_project(
                output_dir=BASE_OUTPUT / "emotion_motion_variation_v26",
                project_name=v26_project,
                expressions=exprs or None,
                character_name=v26_character,
                personality=v26_personality,
                tone=v26_tone,
                format_key=v26_format,
                emotion_intensity=int(v26_emotion_intensity),
                motion_intensity=int(v26_motion_intensity),
                preview_count=int(v26_preview_count),
            )
            st.session_state.emotion_motion_report = report.to_dict()
            st.success("감정 하위표현/행동모션 확장 계획이 생성되었습니다.")
        except Exception as exc:
            st.error(f"v26 생성 실패: {exc}")

    if st.session_state.get("emotion_motion_report"):
        report = st.session_state.emotion_motion_report
        st.markdown("### v26 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("계획 수", report.get("plan_count", 0))
        c2.metric("미리보기", report.get("preview_count", 0))
        c3.metric("체크섬", str(report.get("checksum_sha256", ""))[:12] + "...")
        p1, p2 = st.columns(2)
        with p1:
            fp = Path(report.get("sample_static_path", ""))
            if fp.exists():
                st.image(str(fp), caption="정지형 샘플 미리보기", width=220)
        with p2:
            fp = Path(report.get("sample_gif_path", ""))
            if fp.exists():
                st.image(str(fp), caption="움직이는 모션 샘플", width=220)
        plans = report.get("plans", [])
        if plans:
            st.dataframe(pd.DataFrame(plans)[["index", "phrase", "family", "variation_label", "body_motion", "text_motion", "reason"]], use_container_width=True)
        for label, key, mime in [
            ("v26 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v26 JSON 다운로드", "json_path", "application/json"),
            ("v26 CSV 다운로드", "csv_path", "text/csv"),
            ("v26 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 26:
    st.subheader("텍스트 설명만으로 이모티콘 초안 만들기")
    st.write("예: ‘팽이버섯 한 묶음을 얼굴로 형상화해주고, 성격은 다정하고, 예의 바르게 인사하며 \"안녕하세요\"라고 한다’처럼 자연어로 입력하면 소재·성격·문구·행동을 분해해 360×360 시안과 표현 계획을 만듭니다.")

    default_prompt = st.session_state.get("active_text_prompt") or "팽이버섯 한 묶음을 얼굴로 형상화해주고 성격은 다정하고 예의 바르게 인사하며 \"안녕하세요\" 라고 한다"
    if st.session_state.get("active_generation_profile"):
        st.success("v48에서 적용한 후보/품질 프로필이 이 텍스트 초안 기본값에 반영되어 있습니다.")
    prompt_text = st.text_area("만들고 싶은 이모티콘 설명", value=default_prompt, height=150, key="v48_v27_prompt_text")
    c1, c2, c3 = st.columns(3)
    with c1:
        project_name = st.text_input("v27 프로젝트명", value="enoki_hello_text_prompt", key="v48_v27_project_name")
    with c2:
        format_key = st.selectbox(
            "제작 포맷",
            options=["static_text", "animated_text", "static", "animated", "big"],
            format_func=lambda x: FORMAT_LABELS.get(x, x),
            index=1,
            key="v27_format_key",
        )
    with c3:
        expr_count = st.slider("표현 계획 수", 12, 80, 32, 4, key="v48_v27_expr_count")

    st.markdown("#### 입력 예시")
    st.code('팽이버섯 한 묶음을 얼굴로 형상화해주고 성격은 다정하고 예의 바르게 인사하며 "안녕하세요" 라고 한다')
    st.code('작은 돌멩이를 무표정 캐릭터로 만들고 성격은 시크하며 "봤다"라고 한다')
    st.code('고구마를 느긋한 친구처럼 만들고 양손 따봉을 하며 "좋아요"라고 한다')

    if st.button("텍스트 설명으로 이모티콘 초안 생성", type="primary"):
        engine = TextPromptEmoticonEngine()
        report = engine.build_project(
            BASE_OUTPUT / "text_prompt_emoticon",
            prompt=prompt_text,
            project_name=project_name,
            format_key=format_key,
            expression_count=expr_count,
        )
        st.session_state.text_prompt_report = report.to_dict()
        st.success("텍스트 설명 기반 이모티콘 초안 생성 완료")

    report = st.session_state.text_prompt_report
    if report:
        spec = report.get("spec", {})
        st.markdown("### v27 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("소재", spec.get("material", ""))
        c2.metric("대표 문구", spec.get("phrase", ""))
        c3.metric("표현 계획", report.get("expression_count", 0))
        st.info(spec.get("concept_summary", ""))
        if spec.get("safety_notes"):
            st.warning(" / ".join(spec.get("safety_notes", [])))
        p1, p2 = st.columns(2)
        with p1:
            fp = Path(report.get("preview_png_path", ""))
            if fp.exists():
                st.image(str(fp), caption="360×360 정지형 초안", width=260)
        with p2:
            fp = Path(report.get("preview_gif_path", ""))
            if fp.exists():
                st.image(str(fp), caption="움직이는 문구형 초안", width=260)
        parsed = spec.get("parsed_fields", {})
        if parsed:
            st.dataframe(pd.DataFrame([parsed]), use_container_width=True)
        csv_fp = Path(report.get("csv_path", ""))
        if csv_fp.exists():
            try:
                st.dataframe(pd.read_csv(csv_fp), use_container_width=True)
            except Exception:
                pass
        for label, key, mime in [
            ("v27 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v27 JSON 다운로드", "json_path", "application/json"),
            ("v27 CSV 다운로드", "csv_path", "text/csv"),
            ("v27 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 27:
    st.subheader("누락 정보 후보 제안 / 입력 그대로 만들기")
    st.write("텍스트 설명에서 빠진 다리·팔·색상·성격·말투·표정·동작·포맷 등을 감지하고, 후보를 선택해 재구성하거나 입력한 그대로 초안을 만들 수 있습니다.")

    default_missing_prompt = '팽이버섯 한 묶음을 얼굴로 형상화해주고 예의 바르게 인사하며 "안녕하세요"라고 한다'
    missing_prompt = st.text_area("이모티콘 설명", value=default_missing_prompt, height=130, key="v28_missing_prompt")
    c1, c2, c3 = st.columns(3)
    with c1:
        missing_project = st.text_input("v28 프로젝트명", value="enoki_missing_info_rebuild")
    with c2:
        missing_mode = st.radio("생성 방식", ["후보 선택으로 보완", "입력 그대로 만들기"], horizontal=False, key="v48_missing_mode_radio")
    with c3:
        missing_expr_count = st.slider("표현 계획 수", 12, 80, 32, 4, key="v28_expr_count")

    assistant = MissingInfoAssistant()
    if st.button("누락 정보 분석", type="primary"):
        analysis = assistant.analyze_prompt(missing_prompt)
        st.session_state.missing_info_analysis = analysis.to_dict()
        st.success("누락 정보 분석 완료")

    analysis = st.session_state.get("missing_info_analysis")
    selected_values = {}
    if analysis:
        st.markdown("### 감지된 정보")
        detected = analysis.get("detected", {})
        if detected:
            st.dataframe(pd.DataFrame([detected]), use_container_width=True)
        else:
            st.info("명확히 감지된 정보가 적습니다. 아래 후보에서 선택하거나 입력 그대로 만들 수 있습니다.")

        missing_fields = analysis.get("missing_fields", [])
        label_map = assistant.FIELD_LABELS
        st.markdown("### 누락 항목")
        if missing_fields:
            st.warning(" / ".join(label_map.get(f, f) for f in missing_fields))
        else:
            st.success("주요 항목이 대부분 입력되어 있습니다.")

        candidates = analysis.get("candidates", {})
        if missing_mode == "후보 선택으로 보완" and candidates:
            st.markdown("### 후보 선택")
            for field, opts in candidates.items():
                if not opts:
                    continue
                labels = [f"{o.get('label')} · {o.get('value')}" for o in opts]
                choice = st.selectbox(label_map.get(field, field), options=list(range(len(opts))), format_func=lambda i, labels=labels: labels[i], key=f"v28_candidate_{field}")
                selected_values[field] = opts[choice].get("value", "")
                st.caption(opts[choice].get("reason", ""))
        elif missing_mode == "입력 그대로 만들기":
            st.info("후보 보완 없이 입력한 문장 그대로 초안을 생성합니다. 단, 리포트에는 누락 항목과 후보가 참고용으로 남습니다.")

        final_preview = assistant.reconstruct_prompt(missing_prompt, detected, selected_values, mode="keep_as_is" if missing_mode == "입력 그대로 만들기" else "candidate")
        st.markdown("### 최종 생성 문장 미리보기")
        st.code(final_preview)

        if st.button("v48 선택 후보를 현재 제작 흐름에 적용", key="v48_apply_missing_candidates", type="secondary"):
            st.session_state.active_text_prompt = final_preview
            st.session_state.applied_missing_info_profile = {
                "source": "v28_missing_info_candidates",
                "detected": detected,
                "selected_values": selected_values,
                "final_prompt": final_preview,
            }
            st.session_state.active_generation_profile = st.session_state.applied_missing_info_profile
            try:
                applied_report = TextPromptEmoticonEngine().build_project(
                    BASE_OUTPUT / "v48_applied_missing_candidates",
                    prompt=final_preview,
                    project_name=f"{missing_project}_applied",
                    format_key=(selected_values.get("format") or detected.get("format") or "static_text"),
                    expression_count=int(missing_expr_count),
                )
                st.session_state.text_prompt_report = applied_report.to_dict()
                csv_fp = Path(applied_report.csv_path)
                if csv_fp.exists():
                    rows = pd.read_csv(csv_fp).fillna("").to_dict("records")
                    st.session_state.expressions = [
                        {"no": int(row.get("index", idx + 1)), "category": row.get("category", "후보적용"), "phrase": row.get("phrase", ""), "usage_score": 84, "emotion": row.get("category", "후보적용"), "format_hint": selected_values.get("format", "static_text"), "motion_hint": row.get("motion_direction", "정지형 포즈 차별화")}
                        for idx, row in enumerate(rows)
                    ]
                st.success("선택한 후보를 v27 텍스트 초안, 표현 은행, 다음 후보 갤러리 입력값에 적용했습니다.")
            except Exception as exc:
                st.warning(f"후보 적용은 저장했지만 즉시 초안 생성은 실패했습니다: {exc}")

        if analysis.get("warnings"):
            st.warning(" / ".join(analysis.get("warnings", [])))

        if st.button("v28 재구성 초안 생성", type="primary"):
            report = assistant.build_project(
                BASE_OUTPUT / "missing_info_rebuild_v28",
                prompt=missing_prompt,
                project_name=missing_project,
                selected_values=selected_values,
                mode="keep_as_is" if missing_mode == "입력 그대로 만들기" else "candidate",
                expression_count=int(missing_expr_count),
            )
            st.session_state.missing_info_report = report.to_dict()
            st.success("v28 누락 정보 후보/재구성 초안 생성 완료")

    report = st.session_state.get("missing_info_report")
    if report:
        st.markdown("### v28 결과")
        c1, c2, c3 = st.columns(3)
        analysis = report.get("analysis", {})
        c1.metric("누락 항목 수", len(analysis.get("missing_fields", [])))
        c2.metric("생성 모드", report.get("mode", ""))
        c3.metric("체크섬", str(report.get("checksum_sha256", ""))[:12] + "...")
        st.info(report.get("final_prompt", ""))
        preview = report.get("preview_report") or {}
        p1, p2 = st.columns(2)
        with p1:
            fp = Path(preview.get("preview_png_path", ""))
            if fp.exists():
                st.image(str(fp), caption="재구성 정지형 초안", width=260)
        with p2:
            fp = Path(preview.get("preview_gif_path", ""))
            if fp.exists():
                st.image(str(fp), caption="재구성 움직이는 초안", width=260)
        for label, key, mime in [
            ("v28 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v28 JSON 다운로드", "json_path", "application/json"),
            ("v28 CSV 다운로드", "csv_path", "text/csv"),
            ("v28 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 28:
    st.subheader("반려 사유 기반 자동 개선 엔진")
    st.write("심사 반려 사유나 품질검사 문제점을 입력하면, 원인을 분류하고 문구·표정·모션·포맷·저작권 방어 방향의 개선안을 생성합니다.")

    default_reason = "캐릭터성이 약하고 대화 활용성이 낮으며 문구가 작아서 잘 안 읽힌다는 피드백을 받았습니다. 세트가 반복적이고 감정 전달도 약합니다."
    reason_text = st.text_area("반려/보완 사유 또는 문제점", value=default_reason, height=140, key="v29_reason_text")
    c1, c2, c3 = st.columns(3)
    with c1:
        v29_project = st.text_input("v29 프로젝트명", value="rejection_improvement_project")
    with c2:
        source_mode = st.selectbox("분석할 표현 데이터", ["기본 32개 개선 후보", "현재 표현 은행", "후보 갤러리 결과 우선"], index=0)
    with c3:
        st.caption("리포트 생성물")
        st.write("HTML / JSON / CSV / ZIP")

    expressions_for_review = None
    if source_mode == "현재 표현 은행" and st.session_state.expressions:
        expressions_for_review = asdict_list(st.session_state.expressions)
    elif source_mode == "후보 갤러리 결과 우선" and st.session_state.candidate_gallery_report:
        expressions_for_review = st.session_state.candidate_gallery_report.get("selected_expressions") or st.session_state.candidate_gallery_report.get("expressions")

    if st.button("v29 개선 리포트 생성", type="primary"):
        engine = RejectionImprovementEngine()
        report = engine.build_report(
            BASE_OUTPUT / "rejection_improvement_v29",
            project_name=v29_project,
            reason_text=reason_text,
            expressions=expressions_for_review,
        )
        st.session_state.rejection_improvement_report = report.to_dict()
        st.success("v29 반려 사유 기반 자동 개선 리포트 생성 완료")

    report = st.session_state.rejection_improvement_report
    if report:
        st.markdown("### v29 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("보완 점수", f"{report.get('severity_score', 0)} / 100")
        c2.metric("판정", report.get("verdict", ""))
        c3.metric("개선 액션", len(report.get("action_plan", [])))
        categories = report.get("detected_categories", [])
        if categories:
            st.info("자동 분류: " + " / ".join(categories))
        if report.get("action_plan"):
            st.markdown("#### 우선 개선 액션")
            st.dataframe(pd.DataFrame(report.get("action_plan")), use_container_width=True)
        if report.get("risky_items"):
            st.markdown("#### 수정 필요 가능 표현")
            st.dataframe(pd.DataFrame(report.get("risky_items")), use_container_width=True)
        st.markdown("#### 재구성 표현 세트 후보")
        if report.get("revised_expressions"):
            st.dataframe(pd.DataFrame(report.get("revised_expressions")), use_container_width=True)
        st.markdown("#### 재제출 전 체크리스트")
        if report.get("checklist"):
            st.dataframe(pd.DataFrame(report.get("checklist")), use_container_width=True)
        for label, key, mime in [
            ("v29 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v29 JSON 다운로드", "json_path", "application/json"),
            ("v29 개선 액션 CSV 다운로드", "csv_path", "text/csv"),
            ("v29 수정 표현 CSV 다운로드", "revised_csv_path", "text/csv"),
            ("v29 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 29:
    st.subheader("제출 전 잠금 체크리스트")
    st.write("최종 제출 패키지를 만들기 전에 직접 창작, AI 정책, 저작권, 품질검사, 채팅 미리보기, 백업 여부를 잠금 방식으로 확인합니다.")

    lock_project = st.text_input("v30 프로젝트명", value="submission_lock_project")
    st.markdown("### 필수 체크")
    st.caption("연결된 리포트가 없어도 사용자가 직접 확인할 수 있지만, 실제 제출 전에는 관련 탭을 실행해 리포트를 남기는 것을 권장합니다.")

    required_labels = {
        "origin_evidence": "직접 창작 원본/스케치/자유 드로잉/도형 생성 기록이 있음",
        "ai_no_final": "제출용 완성 이미지를 생성형 AI로 만들거나 AI 사용을 은폐하지 않았음",
        "copyright_report": "저작권/상표권 방어 리포트를 생성하고 고위험 표현을 제거했음",
        "quality_review": "최종 품질검사에서 크기·용량·투명 배경·문구 잘림을 확인했음",
        "chat_preview": "카카오톡 채팅창 미리보기에서 작은 화면·흰/어두운 배경 가독성을 확인했음",
        "count_format": "선택 포맷의 24개/32개 등 기획 수량과 파일명이 맞음",
        "backup_done": "제출 전 현재 프로젝트와 사용자 데이터를 백업했음",
    }
    optional_labels = {
        "consistency": "세트 전체 캐릭터 크기·색상·위치 일관성을 검사했음",
        "rejection_review": "반려 사유/문제점이 있다면 v29 개선 리포트로 보완했음",
        "growth_saved": "성장형 학습 엔진에 결과를 저장해 다음 제작 개선에 반영했음",
        "api_trend": "30일 트렌드/시장성 분석을 확인했음",
        "expression_balance": "표현 후보의 감정/상황 균형과 반복감을 확인했음",
    }
    manual_checks = {}
    cols = st.columns(2)
    for idx, (key, label) in enumerate(required_labels.items()):
        with cols[idx % 2]:
            manual_checks[key] = st.checkbox(label, key=f"v30_req_{key}")
    st.markdown("### 선택/권장 체크")
    cols = st.columns(2)
    for idx, (key, label) in enumerate(optional_labels.items()):
        with cols[idx % 2]:
            manual_checks[key] = st.checkbox(label, key=f"v30_opt_{key}")
    notes = st.text_area("제출 전 메모", value="제출 전 공식 카카오 이모티콘 스튜디오 최신 기준을 다시 확인한다.", height=90)

    if st.button("v30 잠금 체크리스트 생성", type="primary"):
        context_reports = {
            "human_origin_report": st.session_state.human_origin_report,
            "drawing_canvas_report": st.session_state.drawing_canvas_report,
            "free_drawing_report": st.session_state.free_drawing_report,
            "drawing_refine_report": st.session_state.drawing_refine_report,
            "text_prompt_report": st.session_state.text_prompt_report,
            "copyright_defense_report": st.session_state.copyright_defense_report,
            "quality_review": st.session_state.quality_review,
            "chat_preview_report": st.session_state.chat_preview_report,
            "submission_result": st.session_state.submission_result,
            "candidate_gallery_report": st.session_state.candidate_gallery_report,
            "sample_set_report": st.session_state.sample_set_report,
            "data_safety_report": st.session_state.data_safety_report,
            "consistency_report": st.session_state.consistency_report,
            "rejection_improvement_report": st.session_state.rejection_improvement_report,
            "growth_learning_report": st.session_state.growth_learning_report,
            "growth_learning_save_result": st.session_state.growth_learning_save_result,
            "api_trend_report": st.session_state.api_trend_report,
            "trend_result": st.session_state.trend_result,
            "balance": st.session_state.get("balance"),
        }
        report = SubmissionLockChecklistEngine().build_report(
            BASE_OUTPUT / "submission_lock_v30",
            project_name=lock_project,
            manual_checks=manual_checks,
            context_reports=context_reports,
            notes=notes,
        )
        st.session_state.submission_lock_report = report.to_dict()
        st.success("v30 제출 전 잠금 체크리스트 리포트 생성 완료")

    report = st.session_state.submission_lock_report
    if report:
        st.markdown("### v30 결과")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("잠금 상태", report.get("unlock_status", ""))
        c2.metric("필수 통과", f"{report.get('passed_required', 0)} / {report.get('total_required', 0)}")
        c3.metric("선택 통과", f"{report.get('passed_optional', 0)} / {report.get('total_optional', 0)}")
        c4.metric("위험 점수", f"{report.get('risk_score', 0)} / 100")
        if report.get("blockers"):
            st.error("필수 항목이 남아 있어 최종 ZIP 생성 잠금 상태입니다.")
            st.dataframe(pd.DataFrame(report.get("blockers")), use_container_width=True)
        else:
            st.success("필수 항목이 통과되었습니다. 단, 제출 전 카카오 공식 최신 기준은 다시 확인하세요.")
        if report.get("checklist_items"):
            st.markdown("#### 전체 체크리스트")
            st.dataframe(pd.DataFrame(report.get("checklist_items")), use_container_width=True)
        if report.get("next_actions"):
            st.markdown("#### 다음 행동")
            for action in report.get("next_actions", []):
                st.write("- " + str(action))
        for label, key, mime in [
            ("v30 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v30 JSON 다운로드", "json_path", "application/json"),
            ("v30 체크리스트 CSV 다운로드", "csv_path", "text/csv"),
            ("v30 전체 ZIP 다운로드", "zip_path", "application/zip"),
            ("v30 잠금 해제 인증서 다운로드", "unlock_certificate_path", "application/json"),
        ]:
            fp = Path(report.get(key, "")) if report.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)



if selected_page_index == 30:
    st.subheader("최종 제출 패키지 생성 마법사")
    st.write("v30 잠금 체크리스트를 기준으로 최종 ZIP 생성을 통제하고, 제출용 파일·리포트·증거자료를 하나의 최종 번들로 묶습니다.")

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        v31_project = st.text_input("v31 프로젝트명", value="final_submission_project")
    with c2:
        v31_format = st.selectbox("최종 포맷", options=["static_text", "static", "animated_text", "animated", "big"], format_func=lambda k: FORMAT_LABELS.get(k, k), index=0)
    with c3:
        v31_count = st.number_input("목표 수량", min_value=1, max_value=64, value=int(PLANNING_COUNTS.get("static_text", 32)), step=1)

    allow_draft = st.checkbox("v30 잠금 미통과 상태에서도 초안 ZIP만 생성", value=False, help="제출용 최종 ZIP이 아니라 내부 확인용 초안 ZIP입니다.")

    st.markdown("### 연결 상태")
    lock = st.session_state.submission_lock_report
    if lock:
        st.info(f"v30 잠금 상태: {lock.get('unlock_status')} · 필수 통과 {lock.get('passed_required')}/{lock.get('total_required')} · 위험점수 {lock.get('risk_score')}")
    else:
        st.warning("v30 제출 전 잠금 체크리스트 리포트가 아직 없습니다. 최종 제출 ZIP은 잠금 상태로 처리됩니다.")

    selected_spec = None
    try:
        if st.session_state.prototype_results:
            idx = int(st.session_state.get("selected_prototype_index", 0) or 0)
            idx = max(0, min(idx, len(st.session_state.prototype_results) - 1))
            spec_dict = st.session_state.prototype_results[idx].get("spec") if isinstance(st.session_state.prototype_results[idx], dict) else None
            if spec_dict:
                selected_spec = PrototypeSpec(**spec_dict)
        elif st.session_state.prototype_specs:
            spec_raw = st.session_state.prototype_specs[0]
            if isinstance(spec_raw, dict):
                selected_spec = PrototypeSpec(**spec_raw)
            elif hasattr(spec_raw, "to_dict"):
                selected_spec = PrototypeSpec(**spec_raw.to_dict())
    except Exception as exc:
        st.warning(f"선택된 시안을 불러오지 못했습니다. 기본 시안으로 대체됩니다: {exc}")
        selected_spec = None

    if selected_spec:
        st.success(f"연결된 캐릭터 시안: {selected_spec.name}")
    else:
        st.warning("연결된 캐릭터 시안이 없습니다. 기본 절차형 시안으로 초안 생성됩니다.")

    expressions_for_final = []
    if st.session_state.candidate_gallery_report and st.session_state.candidate_gallery_report.get("selected_expressions"):
        expressions_for_final = st.session_state.candidate_gallery_report.get("selected_expressions") or []
    elif st.session_state.expressions:
        expressions_for_final = asdict_list(st.session_state.expressions)
    st.caption(f"연결된 표현 수: {len(expressions_for_final)}개")

    if st.button("v31 최종 제출 패키지 마법사 실행", type="primary"):
        linked_reports = {
            "submission_lock_report": st.session_state.submission_lock_report,
            "submission_result": st.session_state.submission_result,
            "quality_review": st.session_state.quality_review,
            "chat_preview_report": st.session_state.chat_preview_report,
            "copyright_defense_report": st.session_state.copyright_defense_report,
            "human_origin_report": st.session_state.human_origin_report,
            "data_safety_report": st.session_state.data_safety_report,
            "consistency_report": st.session_state.consistency_report,
            "candidate_gallery_report": st.session_state.candidate_gallery_report,
            "part_edit_report": st.session_state.part_edit_report,
            "rejection_improvement_report": st.session_state.rejection_improvement_report,
            "growth_learning_report": st.session_state.growth_learning_report,
        }
        report = FinalSubmissionWizard().build(
            BASE_OUTPUT / "final_submission_wizard_v31",
            project_name=v31_project,
            format_key=v31_format,
            target_count=int(v31_count),
            spec=selected_spec,
            expressions=expressions_for_final,
            lock_report=st.session_state.submission_lock_report,
            linked_reports=linked_reports,
            allow_draft_when_locked=allow_draft,
        )
        st.session_state.final_submission_wizard_report = report.to_dict()
        st.success("v31 최종 제출 패키지 생성 마법사 리포트 생성 완료")

    report = st.session_state.final_submission_wizard_report
    if report:
        st.markdown("### v31 결과")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("잠금 게이트", report.get("gate_status", ""))
        c2.metric("최종 ZIP 상태", report.get("final_zip_status", ""))
        c3.metric("포맷", report.get("format_label", ""))
        c4.metric("목표 수량", report.get("target_count", 0))
        if report.get("blockers"):
            st.error("차단 항목이 있습니다.")
            st.dataframe(pd.DataFrame({"차단 항목": report.get("blockers")}), use_container_width=True)
        if report.get("warnings"):
            st.warning("경고 항목을 확인하세요.")
            st.dataframe(pd.DataFrame({"경고": report.get("warnings")}), use_container_width=True)
        if report.get("included_files"):
            st.markdown("#### 최종 번들 포함 파일")
            st.dataframe(pd.DataFrame(report.get("included_files")), use_container_width=True)
        if report.get("next_actions"):
            st.markdown("#### 다음 행동")
            for action in report.get("next_actions", []):
                st.write("- " + str(action))
        for label, key, mime in [
            ("v31 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v31 JSON 다운로드", "json_path", "application/json"),
            ("v31 체크리스트 CSV 다운로드", "checklist_csv_path", "text/csv"),
            ("v31 매니페스트 다운로드", "manifest_path", "application/json"),
            ("v31 최종 번들 ZIP 다운로드", "final_zip_path", "application/zip"),
            ("v31 내부 제출 패키지 ZIP 다운로드", "package_zip_path", "application/zip"),
        ]:
            fp = Path(report.get(key, "")) if report.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 31:
    st.subheader("유튜브 참고영상/자막 분석기")
    st.write("YouTube URL 또는 iframe을 넣고, 자막 텍스트/SRT/VTT/TXT 파일을 제공하면 이모티콘 제작·승인·수익화 관련 주장과 위험 주장, 프로그램 반영 후보를 분리해 분석합니다.")

    st.markdown("### 학습형 자료 수집/진화")
    st.info("영상·이미지·캐릭터를 다운로드하지 않고, 링크·제목·메타데이터·키워드·위험신호·안전한 제작 원칙만 저장합니다.")
    learning_collector = EvolutionLearningCollector()
    schedule_path = BASE_OUTPUT / "evolution_learning" / "collection_schedule.json"
    due_status = learning_collector.due_status(schedule_path)
    st.session_state.evolution_learning_due_status = due_status
    st.caption(due_status.get("message", ""))

    learn_left, learn_right = st.columns([1.15, 0.85])
    with learn_left:
        learning_queries = st.text_area(
            "수집 검색어 · 줄바꿈 구분",
            value="\n".join(EvolutionLearningCollector.DEFAULT_QUERIES),
            height=130,
            help="YouTube API 키가 있을 때 최근 영상 메타데이터 검색에 사용합니다.",
        )
        reference_urls_text = st.text_area(
            "공식/참고 URL · 줄바꿈 구분",
            value="\n".join(EvolutionLearningCollector.OFFICIAL_REFERENCE_URLS),
            height=105,
            help="공식 가이드, FAQ, 약관처럼 주기적으로 확인할 URL입니다.",
        )
        youtube_channel_ids_text = st.text_area(
            "YouTube 채널 ID RSS · 선택",
            value="",
            height=70,
            help="채널 ID를 줄바꿈으로 넣으면 API 키 없이도 해당 채널의 공개 RSS 제목/링크를 수집합니다.",
        )
    with learn_right:
        learning_api_key = st.text_input("YouTube Data API 키 · 선택", value="", type="password", key="evolution_learning_youtube_api_key")
        learning_days = st.slider("최근 영상 검색 기간", min_value=7, max_value=180, value=30, step=1)
        max_results_per_query = st.slider("검색어당 영상 수", min_value=1, max_value=15, value=5, step=1)
        schedule_days = st.slider("수집 주기", min_value=1, max_value=30, value=7, step=1, help="프로그램이 다음 수집 시점을 판단하는 기준입니다.")
        st.markdown(
            """
            **저장 원칙**
            - 원본 영상/이미지 저장 안 함
            - 자막 원문 대량 저장 안 함
            - 위험 항목은 창작 참고가 아니라 차단 데이터로만 사용
            """
        )

    if st.button("학습형 자료 수집/분석 실행", type="primary", key="run_evolution_learning_collection"):
        queries = [line.strip() for line in learning_queries.splitlines() if line.strip()]
        reference_urls = [line.strip() for line in reference_urls_text.splitlines() if line.strip()]
        channel_ids = [line.strip() for line in youtube_channel_ids_text.splitlines() if line.strip()]
        try:
            learning_report = learning_collector.collect(
                BASE_OUTPUT / "evolution_learning",
                queries=queries,
                youtube_api_key=learning_api_key,
                max_results_per_query=int(max_results_per_query),
                days=int(learning_days),
                reference_urls=reference_urls,
                youtube_channel_ids=channel_ids,
                schedule_days=int(schedule_days),
            )
            st.session_state.evolution_learning_report = learning_report
            st.success("학습형 자료 수집/분석 리포트와 주기 설정 파일을 생성했습니다.")
        except Exception as exc:
            st.error(f"학습형 자료 수집 실패: {exc}")

    learning_report = st.session_state.get("evolution_learning_report")
    if learning_report:
        st.markdown("#### 학습 수집 결과")
        l1, l2, l3 = st.columns(3)
        l1.metric("수집 항목", learning_report.get("source_count", 0))
        l2.metric("차단/경고 전용", learning_report.get("blocked_or_warning_only_count", 0))
        l3.metric("수집 주기", f"{learning_report.get('schedule_days', 7)}일")
        if learning_report.get("warnings"):
            st.warning(" / ".join(str(x) for x in learning_report.get("warnings", [])))
        signal_counts = learning_report.get("safe_signal_counts", {})
        if signal_counts:
            st.markdown("#### 누적 안전 신호")
            st.dataframe(pd.DataFrame([{"신호": k, "횟수": v} for k, v in signal_counts.items()]), use_container_width=True)
        items = learning_report.get("items", [])
        if items:
            st.markdown("#### 수집 자료")
            st.dataframe(
                pd.DataFrame([
                    {
                        "유형": item.get("source_type"),
                        "제목": item.get("title"),
                        "출처": item.get("source_name"),
                        "사용 방식": item.get("learning_use"),
                        "안전 신호": ", ".join(item.get("safe_signals", [])),
                        "위험 수": len(item.get("risk_flags", [])),
                        "URL": item.get("url"),
                    }
                    for item in items
                ]),
                use_container_width=True,
                height=260,
            )
        for label, key, mime in [
            ("학습 DB JSON 다운로드", "json_path", "application/json"),
            ("수집 자료 CSV 다운로드", "csv_path", "text/csv"),
            ("학습 리포트 HTML 다운로드", "html_path", "text/html"),
            ("수집 주기 설정 JSON 다운로드", "schedule_path", "application/json"),
        ]:
            fp = Path((learning_report.get("files") or {}).get(key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"download_learning_{key}")

    col_a, col_b = st.columns([1.2, 0.8])
    with col_a:
        yt_url = st.text_area(
            "YouTube URL 또는 iframe",
            value="https://youtu.be/J7YLGUtzTHc?si=0CsbmSas7JFZed49",
            height=90,
            help="예: https://youtu.be/... 또는 <iframe src=\"https://www.youtube.com/embed/...\"></iframe>",
        )
        transcript_text = st.text_area(
            "자막/스크립트 직접 붙여넣기",
            value="",
            height=180,
            help="YouTube 자막을 복사하거나 영상 속 자막을 직접 적어 넣으면 더 정확히 분석합니다. SRT/VTT 형식도 붙여넣을 수 있습니다.",
        )
        uploaded_caption_files = st.file_uploader(
            "자막 파일 업로드 · TXT/SRT/VTT",
            type=["txt", "srt", "vtt"],
            accept_multiple_files=True,
        )
        manual_title = st.text_input("수동 제목/메모 제목", value="")
        manual_notes = st.text_area("추가 메모", value="", height=90, help="영상에서 기억나는 핵심 주장, 자막 캡처 내용, 댓글 반응 등을 적어도 됩니다.")
    with col_b:
        st.markdown("### API/댓글 옵션")
        yt_api_key = st.text_input("YouTube Data API 키 · 선택", value="", type="password", help="없어도 자막/수동 메모 중심 분석은 가능합니다.")
        include_comments = st.checkbox("API 키가 있을 때 상위 댓글도 분석", value=False)
        comments_per_video = st.slider("댓글 수", min_value=1, max_value=20, value=8)
        st.markdown("### 분석 원칙")
        st.markdown(
            """
            - 영상 파일 다운로드/재사용 없음  
            - 자막/제목/설명/댓글 메타 분석 중심  
            - AI 은폐·검수 우회 주장은 기능화하지 않고 위험 신호로 분리  
            - 안전한 기능 아이디어만 프로그램 개선 후보로 추출
            """
        )

    if st.button("v32 유튜브 참고영상/자막 분석 실행", type="primary"):
        uploaded_pairs = []
        for f in uploaded_caption_files or []:
            try:
                uploaded_pairs.append((f.name, f.read().decode("utf-8", errors="ignore")))
            except Exception:
                uploaded_pairs.append((f.name, ""))
        report = YoutubeReferenceAnalyzer().analyze(
            BASE_OUTPUT / "youtube_reference_v32",
            url_or_iframe=yt_url,
            transcript_text=transcript_text,
            uploaded_transcripts=uploaded_pairs,
            api_key=yt_api_key,
            include_comments=include_comments,
            comments_per_video=int(comments_per_video),
            manual_title=manual_title,
            manual_notes=manual_notes,
        )
        st.session_state.youtube_reference_report = report.to_dict()
        st.success("v32 유튜브 참고영상/자막 분석 리포트 생성 완료")

    report = st.session_state.youtube_reference_report
    if report:
        st.markdown("### v32 결과")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("videoId", report.get("video_id") or "미확인")
        c2.metric("조회수", report.get("view_count") if report.get("view_count") is not None else "API 없음")
        c3.metric("위험 주장", len(report.get("risky_claims", [])))
        c4.metric("기능 후보", len(report.get("safe_feature_ideas", [])))
        if report.get("warnings"):
            st.warning(" / ".join(str(x) for x in report.get("warnings", [])))
        if report.get("core_claims"):
            st.markdown("#### 핵심 주장 분류")
            st.dataframe(pd.DataFrame(report.get("core_claims")), use_container_width=True)
        if report.get("risky_claims"):
            st.markdown("#### 위험 주장/차단 대상")
            st.dataframe(pd.DataFrame(report.get("risky_claims")), use_container_width=True)
        if report.get("safe_feature_ideas"):
            st.markdown("#### 안전한 기능 반영 후보")
            st.dataframe(pd.DataFrame(report.get("safe_feature_ideas")), use_container_width=True)
        if report.get("extracted_keywords"):
            st.markdown("#### 추출 키워드")
            st.dataframe(pd.DataFrame(report.get("extracted_keywords")), use_container_width=True)
        if report.get("recommendations"):
            st.markdown("#### 프로그램 반영 방향")
            for rec in report.get("recommendations", []):
                st.write("- " + str(rec))
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v32 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v32 JSON 다운로드", "json_path", "application/json"),
            ("v32 분석 CSV 다운로드", "csv_path", "text/csv"),
            ("v32 정리 자막 TXT 다운로드", "transcript_path", "text/plain"),
            ("v32 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 32:
    st.subheader("지역 특성·사투리 실생활 문구 엔진")
    st.write("지역어 자료와 사용자 실제 생활 말투를 참고해, 과장·비하 없이 자연스러운 사투리형 이모티콘 문구와 제목 후보를 만듭니다.")

    col_a, col_b = st.columns([1.0, 1.0])
    with col_a:
        dialect_region = st.selectbox("지역/생활권", ["충청권", "강원권", "경상권", "전라권", "제주권", "수도권", "직접 입력"], index=0)
        dialect_material = st.text_input("캐릭터 소재", value="청주 감자")
        dialect_personality = st.text_input("캐릭터 성격", value="느긋하지만 성실하고 예의 바름")
        dialect_tone = st.text_input("말투 방향", value="부드러운 생활형 사투리, 짧고 부담 없는 답장")
        dialect_context = st.text_input("주 사용 상황", value="직장인/일상 답장용")
        dialect_format = st.selectbox("추천 포맷", ["static_text", "animated_text", "mini", "static"], format_func=lambda x: {"static_text":"문구형 정지", "animated_text":"움직이는 문구형", "mini":"미니 이모티콘", "static":"정지형"}.get(x, x))
    with col_b:
        dialect_personal = st.text_area("내가 실제로 쓰는 사투리/생활 말투", value="그려유, 괜찮아유, 천천히 해유, 고맙슈, 어쩐대유", height=160, help="가족/친구/직장 동료 사이에서 실제로 쓰는 표현을 쉼표나 줄바꿈으로 입력하세요.")
        dialect_count = st.slider("문구 후보 개수", min_value=24, max_value=42, value=32)
        dialect_politeness = st.selectbox("존댓말/친근함", ["부드러운 존댓말", "친구용 반말", "직장용 정중 표현", "가족용 친근 표현"], index=0)
        st.markdown("#### 자료 참고 원칙")
        st.markdown("- 국립국어원 지역어/말뭉치 자료는 검증 참고 구조로 사용\n- 원문 대량 복제 없이 사용자 경험 말투와 안전한 후보를 결합\n- 지역 비하·희화화 표현은 경고/순화")

    if st.button("v33 지역·사투리 문구 리포트 생성", type="primary"):
        report = DialectLifeExpressionEngine().build_report(
            BASE_OUTPUT / "dialect_life_expression_v33",
            region=dialect_region,
            material=dialect_material,
            personality=dialect_personality,
            tone=dialect_tone,
            context=dialect_context,
            personal_dialect_text=dialect_personal,
            target_count=int(dialect_count),
            format_key=dialect_format,
            politeness=dialect_politeness,
        )
        st.session_state.dialect_life_expression_report = report.to_dict()
        st.success("v33 지역·사투리 실생활 문구 리포트 생성 완료")

    report = st.session_state.dialect_life_expression_report
    if report:
        st.markdown("### v33 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("지역", report.get("region"))
        c2.metric("문구 수", len(report.get("phrase_set", [])))
        c3.metric("제목 후보", len(report.get("title_candidates", [])))
        st.markdown("#### 콘셉트")
        st.info(report.get("concept_summary"))
        if report.get("safety_warnings"):
            st.markdown("#### 안전 경고/검수")
            for w in report.get("safety_warnings", []):
                st.write("- " + str(w))
        st.markdown("#### 제목 후보")
        st.dataframe(pd.DataFrame(report.get("title_candidates", [])), use_container_width=True)
        st.markdown("#### 사투리/생활 문구 세트")
        st.dataframe(pd.DataFrame(report.get("phrase_set", [])), use_container_width=True)
        if report.get("recommendations"):
            st.markdown("#### 추천")
            for r in report.get("recommendations", []):
                st.write("- " + str(r))
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v33 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v33 JSON 다운로드", "json_path", "application/json"),
            ("v33 문구 CSV 다운로드", "csv_path", "text/csv"),
            ("v33 자료 참고 TXT 다운로드", "source_notes_path", "text/plain"),
            ("v33 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)




if selected_page_index == 35:
    st.subheader("카카오 공식 규격/용량 최종 검수")
    st.write("업로드한 규격 영상과 카카오 가이드 기준을 반영해 포맷별 수량·파일 형식·크기·용량·프레임·투명 배경을 사전 점검합니다. 최종 제출 전 공식 스튜디오에서 한 번 더 확인해야 합니다.")

    spec_options = {k: v["label"] for k, v in KAKAO_SPEC_TABLE.items()}
    col_a, col_b = st.columns([1, 1])
    with col_a:
        product_type = st.selectbox("검수할 이모티콘 유형", list(spec_options.keys()), format_func=lambda k: spec_options[k])
        source_dir_text = st.text_input("검수할 폴더 경로", value=str(BASE_OUTPUT))
        st.caption("파일명 또는 폴더명에 icon/아이콘, share/공유/banner, sound/mp3 등이 들어가면 역할을 자동 분류합니다. 나머지 PNG/WebP/GIF는 이모티콘 이미지로 검사합니다.")
    with col_b:
        st.markdown("### 현재 선택 규격")
        selected_spec = KAKAO_SPEC_TABLE[product_type]
        st.write(f"**유형:** {selected_spec['label']}")
        item = selected_spec["items"]
        st.write(f"**이모티콘 이미지:** {item.get('count')}개 / {', '.join(item.get('formats', []))} / {', '.join([str(w)+'x'+str(h) for w,h in item.get('sizes', [])])}")
        if item.get("min_webp"):
            st.write(f"**움직이는 WebP 최소:** {item.get('min_webp')}개 이상")
        st.write(f"**최대 용량:** {round(item.get('max_bytes', 0)/1024)}KB 이하" if item.get('max_bytes', 0) < 1024*1024 else f"**최대 용량:** {round(item.get('max_bytes', 0)/(1024*1024), 1)}MB 이하")
        if item.get("max_frames"):
            st.write(f"**프레임:** {item.get('max_frames')}프레임 이하 / 반복 {item.get('loop_count', 4)}회 기준")

    st.markdown("### 영상/가이드 반영 체크 포인트")
    st.markdown(
        """
        - 멈춰있는 이모티콘: PNG 32개, 360×360, 150KB 이하, 아이콘 78×78, 공유 이미지 600×166 기준 검사  
        - 움직이는 이모티콘: 24개, 움직이는 WebP 3개 이상, 360×360, 650KB 이하, 24프레임 이하/4회 반복 기준 검사  
        - 큰 이모티콘: 16개, 540×540/300×540/540×300, 1MB 이하 기준 검사  
        - 미니 이모티콘: 멈춰있는 42개 PNG 180×180 100KB 이하, 움직이는 35개 180×180 500KB 이하 기준 검사  
        - 공통: 72dpi/RGB, 배경 투명, 다크모드 대비, 마지막 프레임 대표성, 미니 이모티콘 순서/조합성 확인
        """
    )

    if st.button("v36 규격/용량 검수 실행", type="primary"):
        report = KakaoSpecValidator().build_report(
            BASE_OUTPUT / "kakao_spec_v36",
            Path(source_dir_text),
            product_type,
        )
        st.session_state.kakao_spec_report = report
        st.success("v36 카카오 규격/용량 검수 리포트 생성 완료")

    report = st.session_state.kakao_spec_report
    if report:
        st.markdown("### v36 검수 결과")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("판정", report.get("decision", "-"))
        c2.metric("점수", report.get("score", 0))
        c3.metric("이미지 수", report.get("counts", {}).get("item", 0))
        c4.metric("WebP 수", report.get("counts", {}).get("webp_items", 0))
        if report.get("failures"):
            st.error("수정 필요 항목이 있습니다.")
            for f in report.get("failures", []):
                st.write("- " + str(f))
        if report.get("warnings"):
            st.warning("주의/확인 항목")
            for w in report.get("warnings", [])[:25]:
                st.write("- " + str(w))
        st.markdown("#### 파일별 검사표")
        st.dataframe(pd.DataFrame(report.get("checks", [])), use_container_width=True)
        st.markdown("#### 수동 확인 메모")
        for note in report.get("manual_notes", []):
            st.write("- " + str(note))
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v36 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v36 JSON 다운로드", "json_path", "application/json"),
            ("v36 파일 검사 CSV 다운로드", "csv_path", "text/csv"),
            ("v36 수동 확인 TXT 다운로드", "notes_path", "text/plain"),
            ("v36 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 36:
    st.subheader("1차 포맷 추천 + 단계별 확장 전략")
    st.write("처음부터 모든 포맷을 한꺼번에 만들지 않고, 현재 캐릭터와 데이터 수준에 맞는 1차 제작 포맷 1개를 추천합니다. 나머지는 시리즈/미니/큰/움직이는 확장 후보로 보관합니다.")

    col_a, col_b = st.columns([1.1, 0.9])
    with col_a:
        v37_project_name = st.text_input("프로젝트명", value="보리와 쌀 1차 세트", key="v37_project_name")
        v37_concept = st.text_area(
            "캐릭터 콘셉트/세계관",
            value="까칠하지만 은근히 챙기는 보리와 온순하고 다정한 쌀 듀오. 짧은 답장과 직장인 리액션 중심.",
            height=120,
            key="v37_concept",
        )
        v37_phrases = st.text_area(
            "대표 문구/키워드 예시",
            value="넵, 확인했습니다, 뭐... 고맙다, 괜찮아유, 퇴근하고 싶어요, 좋아요, 죄송합니다, 파이팅",
            height=90,
            key="v37_phrases",
        )
        v37_personality = st.text_input("성격/말투 요약", value="보리=투덜/까칠, 쌀=다정/부드러움, 직장인 답장형", key="v37_personality")
        v37_goal = st.text_input("현재 목표", value="첫 제출용 1개 포맷 추천", key="v37_goal")
    with col_b:
        v37_motion_strength = st.slider("모션 필요성/강도", 1, 5, 2, help="1=거의 필요 없음, 5=동작 자체가 핵심 매력", key="v37_motion_strength")
        v37_expression_variety = st.slider("표정/표현 다양성 점수", 0, 100, 75, key="v37_expression_variety")
        v37_chat_readability = st.slider("채팅창 문구 가독성 점수", 0, 100, 80, key="v37_chat_readability")
        v37_quality_score = st.slider("현재 품질검사 점수", 0, 100, 75, key="v37_quality_score")
        v37_review_status = st.selectbox(
            "현재 심사/출시 상태",
            ["아직 제출 전", "제출 준비", "반려됨", "승인됨", "출시됨"],
            index=0,
            key="v37_review_status",
        )
        c1, c2 = st.columns(2)
        with c1:
            v37_approval_count = st.number_input("누적 승인 수", min_value=0, max_value=99, value=0, step=1, key="v37_approval_count")
        with c2:
            v37_rejection_count = st.number_input("누적 반려 수", min_value=0, max_value=99, value=0, step=1, key="v37_rejection_count")
        v37_sales_signal = st.selectbox(
            "판매/사용 반응 데이터",
            ["아직 데이터 없음", "반응 낮음", "반응 보통", "반응 양호", "판매/사용 반응 좋음"],
            index=0,
            key="v37_sales_signal",
        )

    st.markdown("### v37 판단 원칙")
    st.markdown(
        """
        - 초기에는 가장 적합한 **1개 포맷만 실제 제작**합니다.  
        - 미니/큰/움직이는 포맷은 **확장 후보로만 저장**합니다.  
        - 심사 결과, 반려 사유, 품질 점수, 채팅 사용성, 판매 반응이 쌓인 뒤 시리즈/포맷 확장을 재판단합니다.  
        - 전체 포맷 자동 변환은 선택형 도구로만 유지하고, 기본 흐름은 1차 포맷 집중입니다.
        """
    )

    if st.button("v37 1차 포맷/확장 전략 리포트 생성", type="primary"):
        report = FormatStrategyEngine().build_report(
            BASE_OUTPUT / "format_strategy_v37",
            project_name=v37_project_name,
            character_concept=v37_concept,
            phrase_examples=v37_phrases,
            personality=v37_personality,
            motion_strength=int(v37_motion_strength),
            expression_variety_score=int(v37_expression_variety),
            chat_readability_score=int(v37_chat_readability),
            quality_score=int(v37_quality_score),
            review_status=v37_review_status,
            approval_count=int(v37_approval_count),
            rejection_count=int(v37_rejection_count),
            sales_signal=v37_sales_signal,
            user_goal=v37_goal,
        )
        st.session_state.format_strategy_report = report.to_dict()
        st.success("v37 1차 포맷 추천/단계별 확장 전략 리포트 생성 완료")

    report = st.session_state.format_strategy_report
    if report:
        st.markdown("### v37 결과")
        primary = report.get("primary_format", {}) or {}
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("1차 추천", primary.get("format_label", "-"))
        c2.metric("추천 점수", primary.get("score", 0))
        c3.metric("데이터 단계", report.get("data_stage", "-"))
        c4.metric("확장 후보", len(report.get("hold_formats", [])))
        st.info(primary.get("why", ""))
        if primary.get("caution"):
            st.warning(primary.get("caution"))
        st.markdown("#### 포맷별 점수")
        st.dataframe(pd.DataFrame(report.get("format_scores", [])), use_container_width=True)
        st.markdown("#### 단계별 확장 로드맵")
        st.dataframe(pd.DataFrame(report.get("expansion_roadmap", [])), use_container_width=True)
        st.markdown("#### 확장 판단에 필요한 데이터")
        st.dataframe(pd.DataFrame(report.get("data_requirements", [])), use_container_width=True)
        st.markdown("#### 시리즈 후보")
        st.dataframe(pd.DataFrame(report.get("series_candidates", [])), use_container_width=True)
        st.markdown("#### 보류 포맷")
        st.dataframe(pd.DataFrame(report.get("hold_formats", [])), use_container_width=True)
        if report.get("decision_rules"):
            st.markdown("#### 판단 규칙")
            for note in report.get("decision_rules", []):
                st.write("- " + str(note))
        if report.get("next_actions"):
            st.markdown("#### 다음 액션")
            for note in report.get("next_actions", []):
                st.write("- " + str(note))
        if report.get("safety_notes"):
            st.markdown("#### 안전 노트")
            for note in report.get("safety_notes", []):
                st.write("- " + str(note))
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v37 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v37 JSON 다운로드", "json_path", "application/json"),
            ("v37 포맷 점수 CSV 다운로드", "scores_csv_path", "text/csv"),
            ("v37 확장 로드맵 CSV 다운로드", "roadmap_csv_path", "text/csv"),
            ("v37 필요 데이터 CSV 다운로드", "data_requirements_csv_path", "text/csv"),
            ("v37 판단 노트 TXT 다운로드", "notes_txt_path", "text/plain"),
            ("v37 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 37:
    st.subheader("CSV/캡처 데이터 가져오기 + 학습 데이터 입력")
    st.write("카카오 심사 결과, 판매/정산 메모, 반려 사유, 문구 반응, 품질검사 결과를 CSV 또는 캡처 이미지로 가져와 성장형 학습 데이터에 누적 저장합니다.")

    data_type_labels = {k: v["label"] for k, v in CSV_CAPTURE_TYPES.items()}
    v38_type = st.selectbox("가져올 데이터 종류", list(data_type_labels.keys()), format_func=lambda k: data_type_labels[k])
    v38_pipeline = DataIngestionPipeline()

    st.markdown("### 1) CSV 템플릿 다운로드")
    st.caption("엑셀에서 열기 쉽도록 UTF-8-SIG 형식으로 저장됩니다. 컬럼명은 한글로 써도 일부 자동 매칭됩니다.")
    if st.button("v38 CSV 템플릿 전체 생성", type="secondary"):
        paths = v38_pipeline.generate_templates(BASE_OUTPUT / "data_ingestion_v38")
        st.session_state.v38_template_paths = paths
        st.success("CSV 템플릿 생성 완료")
    if st.session_state.get("v38_template_paths"):
        for key, fp in st.session_state.v38_template_paths.items():
            path = Path(fp)
            if path.exists():
                mime = "application/zip" if key == "zip" else "text/csv"
                label = "CSV 템플릿 전체 ZIP 다운로드" if key == "zip" else f"{data_type_labels.get(key, key)} 템플릿 다운로드"
                st.download_button(label, data=path.read_bytes(), file_name=path.name, mime=mime)

    st.divider()
    st.markdown("### 2) CSV 가져오기")
    csv_file = st.file_uploader("CSV 파일 업로드", type=["csv"], key="v38_csv_upload")
    st.caption("예: 카카오 심사 결과, 월별 정산 메모, 문구 반응 점수, 반려 사유 수정 이력 등")
    if st.button("CSV 분석/정리/저장", type="primary"):
        if not csv_file:
            st.error("CSV 파일을 먼저 업로드하세요.")
        else:
            temp_dir = Path(tempfile.gettempdir()) / "kakao_v38_csv"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / csv_file.name
            temp_path.write_bytes(csv_file.getvalue())
            report = v38_pipeline.import_csv(temp_path, v38_type, BASE_OUTPUT / "data_ingestion_v38")
            st.session_state.data_ingestion_report = report.to_dict()
            st.success("CSV 가져오기 완료")

    st.divider()
    st.markdown("### 3) 캡처 이미지 가져오기")
    capture_files = st.file_uploader("캡처 이미지 업로드", type=["png", "jpg", "jpeg", "webp", "bmp"], accept_multiple_files=True, key="v38_capture_upload")
    capture_text = st.text_area(
        "캡처에서 보이는 핵심 텍스트/숫자를 붙여넣기 또는 메모",
        value="",
        height=140,
        help="캡처 인식은 오차가 생길 수 있으므로, 중요한 날짜/승인·반려/매출 숫자/반려 사유는 여기에 직접 적어두면 더 정확합니다.",
    )
    if st.button("캡처 보존/메모 추출/저장", type="primary"):
        temp_paths = []
        temp_dir = Path(tempfile.gettempdir()) / "kakao_v38_captures"
        temp_dir.mkdir(parents=True, exist_ok=True)
        for idx, uploaded in enumerate(capture_files or [], start=1):
            suffix = Path(uploaded.name).suffix or ".png"
            fp = temp_dir / f"capture_{idx:02d}{suffix}"
            fp.write_bytes(uploaded.getvalue())
            temp_paths.append(fp)
        if not temp_paths and not capture_text.strip():
            st.error("캡처 이미지 또는 메모 텍스트를 입력하세요.")
        else:
            report = v38_pipeline.import_captures(temp_paths, v38_type, BASE_OUTPUT / "data_ingestion_v38", manual_text=capture_text)
            st.session_state.data_ingestion_report = report.to_dict()
            st.success("캡처/메모 가져오기 완료")

    report = st.session_state.data_ingestion_report
    if report:
        st.markdown("### v38 가져오기 결과")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("판정", report.get("decision", "-"))
        c2.metric("가져온 행", report.get("imported_rows", 0))
        c3.metric("경고", report.get("warning_count", 0))
        c4.metric("오류", report.get("error_count", 0))
        if report.get("errors"):
            st.error("오류가 있습니다. CSV/메모를 수정한 뒤 다시 가져오세요.")
            for err in report.get("errors", [])[:30]:
                st.write("- " + str(err))
        if report.get("warnings"):
            st.warning("확인 필요 항목")
            for warn in report.get("warnings", [])[:30]:
                st.write("- " + str(warn))
        if report.get("cleaned_records"):
            st.markdown("#### 정리된 데이터 미리보기")
            st.dataframe(pd.DataFrame(report.get("cleaned_records", [])), use_container_width=True)
        if report.get("extracted_candidates"):
            st.markdown("#### 캡처 후보 추출/메타데이터")
            st.dataframe(pd.DataFrame(report.get("extracted_candidates", [])), use_container_width=True)
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v38 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v38 JSON 다운로드", "json_path", "application/json"),
            ("v38 정리 CSV 다운로드", "cleaned_csv_path", "text/csv"),
            ("v38 캡처 후보 CSV 다운로드", "candidate_csv_path", "text/csv"),
            ("v38 학습 JSONL 다운로드", "learning_jsonl_path", "application/jsonl"),
            ("v38 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 38:
    st.subheader("카카오 스튜디오 엑셀 자동 가져오기 / 성과 학습")
    st.write("카카오 이모티콘 스튜디오에서 내려받은 이모티콘 플러스 발신 통계 엑셀과 판매내역 엑셀을 업로드해 작품별 성과를 정리하고 성장형 학습 데이터로 누적 저장합니다.")

    col_a, col_b = st.columns([1.0, 1.0])
    with col_a:
        v39_project_name = st.text_input("프로젝트/작품명", value="kakao_studio_performance", key="v39_project_name")
        plus_file = st.file_uploader("이모티콘 플러스 발신 통계 엑셀 업로드", type=["xlsx"], key="v39_plus_xlsx")
        sales_file = st.file_uploader("판매내역 엑셀 업로드", type=["xlsx"], key="v39_sales_xlsx")
        v39_confirm_save = st.checkbox("확인 후 성장형 학습 데이터로 누적 저장", value=True, help="체크하면 UserData/growth_learning/kakao_studio_excel/*.jsonl에 누적 저장합니다. 체크 해제 시 초안 JSON만 저장합니다.")
    with col_b:
        st.markdown("### 지원하는 카카오 엑셀 양식")
        st.markdown(
            """
            **1) 이모티콘 플러스 발신 통계**  
            - 조회기간, 날짜, 이모티콘명, 시리즈명, 발신수, 이용자수

            **2) 판매내역**  
            - 판매기간, 국내/일본/글로벌 판매 요약
            - 판매일, 유형, 이모티콘 제목, 시리즈명, 구분, 건수, 통화, 금액

            **학습 활용**  
            - 발신수/이용자수 반복률
            - 판매 건수/금액
            - 시리즈화·미니·움직이는 버전 확장 추천
            - 데이터가 0이면 확장 판단보다 누적 저장 우선
            """
        )

    if st.button("v39 카카오 엑셀 분석/정리/학습 저장", type="primary"):
        if not plus_file and not sales_file:
            st.error("플러스 발신 통계 또는 판매내역 엑셀 중 하나 이상을 업로드하세요.")
        else:
            temp_dir = Path(tempfile.gettempdir()) / "kakao_v39_studio_excel"
            temp_dir.mkdir(parents=True, exist_ok=True)
            plus_path = None
            sales_path = None
            if plus_file:
                plus_path = temp_dir / plus_file.name
                plus_path.write_bytes(plus_file.getvalue())
            if sales_file:
                sales_path = temp_dir / sales_file.name
                sales_path.write_bytes(sales_file.getvalue())
            report = KakaoStudioExcelLearningEngine().build_report(
                BASE_OUTPUT / "kakao_studio_excel_v39",
                plus_xlsx=plus_path,
                sales_xlsx=sales_path,
                project_name=v39_project_name,
                confirm_save=bool(v39_confirm_save),
            )
            st.session_state.kakao_studio_excel_report = report.to_dict()
            st.success("v39 카카오 스튜디오 엑셀 성과 학습 리포트 생성 완료")

    report = st.session_state.kakao_studio_excel_report
    if report:
        st.markdown("### v39 가져오기 결과")
        health = report.get("data_health", {}) or {}
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("데이터 건강도", health.get("level", "-"))
        c2.metric("발신수", health.get("total_sent", 0))
        c3.metric("이용자수", health.get("total_users", 0))
        c4.metric("판매금액", f"{health.get('total_sales_amount', 0):,.0f}")

        period = report.get("period", {}) or {}
        st.info(f"분석 기간: {period.get('start_date', '')} ~ {period.get('end_date', '')}")

        if report.get("warnings"):
            st.warning("확인 필요 항목")
            for warn in report.get("warnings", [])[:30]:
                st.write("- " + str(warn))

        st.markdown("#### 작품별 성과 점수")
        st.dataframe(pd.DataFrame(report.get("performance_scores", [])), use_container_width=True)

        st.markdown("#### 확장/시리즈 추천")
        st.dataframe(pd.DataFrame(report.get("extension_recommendations", [])), use_container_width=True)

        with st.expander("이모티콘 플러스 발신 원본 정리 보기"):
            st.dataframe(pd.DataFrame(report.get("plus_rows", [])), use_container_width=True)
        with st.expander("판매 요약/상세 정리 보기"):
            st.markdown("##### 판매 요약")
            st.dataframe(pd.DataFrame(report.get("sales_summary", [])), use_container_width=True)
            st.markdown("##### 판매 상세")
            st.dataframe(pd.DataFrame(report.get("sales_details", [])), use_container_width=True)

        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v39 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v39 JSON 다운로드", "json_path", "application/json"),
            ("v39 플러스 발신 CSV 다운로드", "plus_rows_csv_path", "text/csv"),
            ("v39 판매 요약 CSV 다운로드", "sales_summary_csv_path", "text/csv"),
            ("v39 판매 상세 CSV 다운로드", "sales_details_csv_path", "text/csv"),
            ("v39 작품별 성과 점수 CSV 다운로드", "performance_scores_csv_path", "text/csv"),
            ("v39 확장 추천 CSV 다운로드", "extension_recommendations_csv_path", "text/csv"),
            ("v39 학습 JSONL 다운로드", "learning_jsonl_path", "application/jsonl"),
            ("v39 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 39:
    st.subheader("성과 데이터 대시보드 + 다음 제작 방향 자동 추천")
    st.write("v39 카카오 스튜디오 엑셀 성과 데이터를 바탕으로 작품별 성과를 대시보드로 정리하고, 시리즈화·포맷 확장·다음 4주 제작 계획을 추천합니다.")

    col_a, col_b = st.columns([1.0, 1.0])
    with col_a:
        v40_project_name = st.text_input("v40 대시보드 프로젝트명", value="kakao_performance_dashboard", key="v40_project_name")
        v40_source_mode = st.radio("데이터 소스", ["현재 v39 분석 결과 사용", "v39 JSON 리포트 업로드", "학습 JSONL 파일 업로드", "샘플/빈 데이터로 구조 확인"], horizontal=False, key="v48_v40_source_mode_radio")
        uploaded_v39_json = None
        uploaded_jsonl = None
        if v40_source_mode == "v39 JSON 리포트 업로드":
            uploaded_v39_json = st.file_uploader("v39 JSON 리포트 업로드", type=["json"], key="v40_v39_json_upload")
        if v40_source_mode == "학습 JSONL 파일 업로드":
            uploaded_jsonl = st.file_uploader("kakao_studio_excel_imports.jsonl 업로드", type=["jsonl", "txt"], key="v40_jsonl_upload")
    with col_b:
        st.markdown("### v40 판단 기준")
        st.markdown(
            """
            - 발신수/이용자수로 구독형 반복 사용성 판단  
            - 판매건수/판매금액으로 구매 전환 판단  
            - 데이터가 부족하면 확장 보류  
            - 처음부터 모든 포맷 제작 금지  
            - 1차 포맷 → 데이터 축적 → 시리즈/미니/움직이는 확장 순서 유지
            """
        )

    if st.button("v40 성과 대시보드/다음 방향 생성", type="primary"):
        try:
            source_report = {}
            learning_records = []
            if v40_source_mode == "현재 v39 분석 결과 사용":
                source_report = st.session_state.get("kakao_studio_excel_report") or {}
                if not source_report:
                    st.warning("현재 세션에 v39 분석 결과가 없습니다. 샘플/빈 데이터 구조로 대시보드를 생성합니다.")
            elif v40_source_mode == "v39 JSON 리포트 업로드" and uploaded_v39_json is not None:
                source_report = json.loads(uploaded_v39_json.getvalue().decode("utf-8"))
            elif v40_source_mode == "학습 JSONL 파일 업로드" and uploaded_jsonl is not None:
                raw = uploaded_jsonl.getvalue().decode("utf-8")
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        learning_records.append(json.loads(line))
                    except Exception:
                        pass
            report = PerformanceDashboardEngine().build_report(
                BASE_OUTPUT / "performance_dashboard_v40",
                project_name=v40_project_name,
                kakao_excel_report=source_report,
                learning_records=learning_records,
            )
            st.session_state.performance_dashboard_report = report.to_dict()
            st.success("v40 성과 대시보드와 다음 제작 방향 리포트 생성 완료")
        except Exception as exc:
            st.error(f"v40 대시보드 생성 실패: {exc}")

    report = st.session_state.performance_dashboard_report
    if report:
        st.markdown("### v40 성과 대시보드")
        metrics = report.get("portfolio_metrics", {}) or {}
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("작품 수", metrics.get("project_count", 0))
        c2.metric("총 발신수", metrics.get("total_sent", 0))
        c3.metric("총 이용자수", metrics.get("total_users", 0))
        c4.metric("총 판매건수", metrics.get("total_sales_count", 0))
        c5.metric("총 판매금액", f"{metrics.get('total_sales_amount', 0):,.0f}")
        st.info(f"데이터 단계: {metrics.get('data_stage', '-')}")

        st.markdown("#### 작품별 성과")
        st.dataframe(pd.DataFrame(report.get("dashboard_rows", [])), use_container_width=True)
        st.markdown("#### 전략 추천")
        st.dataframe(pd.DataFrame(report.get("strategy_recommendations", [])), use_container_width=True)
        st.markdown("#### 시리즈 후보")
        st.dataframe(pd.DataFrame(report.get("series_candidates", [])), use_container_width=True)
        st.markdown("#### 포맷 확장 후보")
        st.dataframe(pd.DataFrame(report.get("format_expansion_candidates", [])), use_container_width=True)
        st.markdown("#### 다음 4주 제작 계획")
        st.dataframe(pd.DataFrame(report.get("next_production_plan", [])), use_container_width=True)
        st.markdown("#### 추가로 필요한 데이터")
        st.dataframe(pd.DataFrame(report.get("data_needs", [])), use_container_width=True)
        if report.get("safety_notes"):
            st.markdown("#### 안전 노트")
            for note in report.get("safety_notes", []):
                st.write("- " + str(note))
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v40 HTML 대시보드 다운로드", "html_path", "text/html"),
            ("v40 JSON 다운로드", "json_path", "application/json"),
            ("v40 작품별 성과 CSV 다운로드", "dashboard_rows_csv_path", "text/csv"),
            ("v40 전략 추천 CSV 다운로드", "strategy_recommendations_csv_path", "text/csv"),
            ("v40 시리즈 후보 CSV 다운로드", "series_candidates_csv_path", "text/csv"),
            ("v40 포맷 확장 후보 CSV 다운로드", "format_expansion_candidates_csv_path", "text/csv"),
            ("v40 다음 제작 계획 CSV 다운로드", "next_production_plan_csv_path", "text/csv"),
            ("v40 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 40:
    st.subheader("리포트/프로젝트 패키지 저장")
    project_name = st.text_input("프로젝트명", value="kakao_emoticon_project", key="v48_export_project_name")
    if st.button("분석 리포트 저장", type="primary"):
        exporter = ProjectExporter(BASE_OUTPUT)
        project_dir = exporter.create_project_dir(project_name)
        data = {
            "title": "카카오 이모티콘 수익화 시스템 v40 분석 리포트",
            "캐릭터 분석": st.session_state.profile,
            "독창 후보": st.session_state.concepts,
            "대표 이미지 분석": st.session_state.image_profile,
            "첨부 이미지별 분석": st.session_state.image_profiles,
            "복합 이미지 결합 분석": st.session_state.multi_image_blend,
            "복수 단어/소재 분석": st.session_state.material_tokens,
            "복합 소재 독창 후보": st.session_state.blend_concepts,
            "30일 트렌드 분석": st.session_state.trend_result,
            "v7 무료 API 통합 분석": st.session_state.api_trend_report,
            "v8 저작권 방어 리포트": st.session_state.copyright_defense_report,
            "v25 설치/실행 진단": st.session_state.install_diag_report,
            "v25 직접 창작 기준 리포트": st.session_state.human_origin_report,
            "v25 초보자/멀티소재 직접 캐릭터 만들기": st.session_state.beginner_creator_report,
            "v25 색상/성격/말투 후보 및 실시간 미리보기": "도형 직접 만들기, 스케치/첨부파일 선택 입력, 색상 후보·성격 후보·말투 후보 선택, 360x360 미리보기 지원",
            "v25 후보 갤러리/세트 선택/표정 자동 구성": st.session_state.candidate_gallery_report,
            "v25 표정/파츠/문구/움직임 편집기": st.session_state.part_edit_report,
            "v25 카카오톡 채팅창 미리보기/최종검수": st.session_state.chat_preview_report,
            "v25 첫 실제 샘플 세트 제작": st.session_state.sample_set_report,
            "v25 데이터 보호/백업/마이그레이션": st.session_state.data_safety_report,
            "v25 누적 데이터 성장형 추천 엔진": st.session_state.growth_learning_report,
            "v21 초보자 전체 제작 마법사": st.session_state.workflow_wizard_report,
            "v22 직접 그리기 캔버스/레이어 편집기": st.session_state.drawing_canvas_report,
            "v23 캐릭터 일관성 검사/자동 보정": st.session_state.consistency_report,
            "v24 자유 드로잉 캔버스 강화": st.session_state.free_drawing_report,
            "v25 자유 드로잉 자동 정리/파츠 추정/표정 확장": st.session_state.drawing_refine_report,
            "v26 감정 하위표현/행동모션 확장": st.session_state.emotion_motion_report,
            "v27 텍스트 설명 기반 이모티콘 초안 생성": st.session_state.text_prompt_report,
            "v28 누락 정보 후보 제안/재구성": st.session_state.missing_info_report,
            "v29 반려 사유 기반 자동 개선": st.session_state.rejection_improvement_report,
            "v30 제출 전 잠금 체크리스트": st.session_state.submission_lock_report,
            "v31 최종 제출 패키지 생성 마법사": st.session_state.final_submission_wizard_report,
            "v32 유튜브 참고영상/자막 분석기": st.session_state.youtube_reference_report,
            "v33 지역 특성/사투리 실생활 문구 엔진": st.session_state.dialect_life_expression_report,
            "v34 구체 콘셉트/멘트/모션 템플릿 전략 엔진": st.session_state.concept_strategy_report,
            "v35 취향/경험 기반 아이디어 발굴·모션 템플릿 고도화": st.session_state.taste_experience_report,
            "v36 카카오 공식 규격/용량 검수": st.session_state.kakao_spec_report,
            "v37 1차 포맷 추천/단계별 확장 전략": st.session_state.format_strategy_report,
            "v38 CSV/캡처 데이터 가져오기": st.session_state.data_ingestion_report,
            "v39 카카오 스튜디오 엑셀 성과 학습": st.session_state.kakao_studio_excel_report,
            "v40 성과 대시보드/다음 제작 방향": st.session_state.performance_dashboard_report,
            "v41 선택 포맷 자동 변환/압축": st.session_state.selected_format_autofix_report,
            "v42 플랫폼별 재패키징": st.session_state.platform_repackaging_report,
            "표현 은행 요약": st.session_state.get("balance"),
            "포맷 추천": st.session_state.format_scores,
            "캐릭터 시안": st.session_state.prototype_results,
            "표현 PNG 세트": st.session_state.expression_pack_files,
            "제출 패키지": st.session_state.submission_result,
            "수익 파이프라인": st.session_state.pipeline_plan,
            "심사/판매 기록": st.session_state.submission_history,
            "최종 품질 검사": st.session_state.quality_review,
            "주의": "이 결과는 법적 판단 또는 승인/수익 보장이 아니라 제작 전 검토 자료입니다.",
        }
        exporter.save_json(data, project_dir / "analysis_data.json")
        if st.session_state.expressions:
            exporter.save_expressions_csv(st.session_state.expressions, project_dir / "expression_bank.csv")
        report_path = HtmlReporter().write_report(data, project_dir / "analysis_report.html")
        st.session_state.report_path = str(report_path)
        st.success(f"리포트 저장 완료: {report_path}")
    if st.session_state.report_path and Path(st.session_state.report_path).exists():
        st.download_button("HTML 리포트 다운로드", data=Path(st.session_state.report_path).read_bytes(), file_name="analysis_report.html", mime="text/html")

if selected_page_index == 33:
    st.subheader("구체 콘셉트·멘트·모션 템플릿 전략 엔진")
    st.write("막연한 소재를 구체 콘셉트로 바꾸고, 제목 후보·32문구 선기획·이모티콘 플러스 키워드·모션 템플릿 전략을 먼저 잡습니다.")

    col_a, col_b = st.columns([1.15, 0.85])
    with col_a:
        v34_concept_text = st.text_area(
            "초기 아이디어/텍스트 설명",
            value="게으르고 나른한 뚱냥이 캐릭터. 누워서 나른하다냥이라고 말한다.",
            height=130,
            help="예: 귀여운 고양이보다 '게으르고 나른한 뚱냥이', '예의 바른 팽이버섯 묶음'처럼 구체적으로 적을수록 좋습니다.",
        )
        v34_material = st.text_input("소재/본체 · 비워두면 자동 추정", value="")
        v34_personality = st.text_input("성격 · 비워두면 자동 추정", value="")
        v34_tone = st.text_input("말투 · 비워두면 자동 추정", value="")
        v34_target_user = st.text_input("주 대상/사용 상황", value="일상 카톡 답장/리액션")
    with col_b:
        v34_format_focus = st.selectbox(
            "우선 검토 포맷",
            ["auto", "static_text", "animated_text", "mini", "static", "animated"],
            format_func=lambda x: {
                "auto":"자동 추천", "static_text":"문구형 정지", "animated_text":"움직이는 문구형", "mini":"미니 이모티콘", "static":"정지형", "animated":"움직이는 이모티콘"
            }.get(x, x),
            key="v48_v34_format_focus",
        )
        v34_count = st.radio("문구 선기획 수량", [24, 32], index=1, horizontal=True, key="v48_v34_count_radio")
        v34_mini = st.checkbox("미니 이모티콘 전략도 함께 검토", value=True, key="v48_v34_mini")
        st.markdown("### 반영 원칙")
        st.markdown(
            """
            - 막연한 '귀여운 캐릭터'를 구체 성격/상황으로 바꿈  
            - 제목에 콘셉트가 드러나는지 점수화  
            - 24/32개 문구를 그림보다 먼저 기획  
            - 멘트는 크고 짧게, 상황이 바로 보이게 구성  
            - 모션 템플릿은 캐릭터 비율에 맞춰 변형  
            - 움직이는 이모티콘이 무조건 우위라는 전제는 사용하지 않음
            """
        )

    if st.button("v34 콘셉트·멘트·모션 전략 리포트 생성", type="primary"):
        report = ConceptStrategyEngine().build_report(
            BASE_OUTPUT / "concept_strategy_v34",
            concept_text=v34_concept_text,
            material=v34_material,
            target_user=v34_target_user,
            personality=v34_personality,
            tone=v34_tone,
            format_focus=v34_format_focus,
            target_count=int(v34_count),
            include_mini_strategy=v34_mini,
        )
        st.session_state.concept_strategy_report = report.to_dict()
        st.success("v34 콘셉트·멘트·모션 템플릿 전략 리포트 생성 완료")

    report = st.session_state.concept_strategy_report
    if report:
        st.markdown("### v34 결과")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("구체성 점수", report.get("specificity_score", 0))
        c2.metric("제목 후보", len(report.get("title_candidates", [])))
        c3.metric("문구 수", len(report.get("phrase_plan", [])))
        c4.metric("모션 템플릿", len(report.get("motion_templates", [])))
        st.info(report.get("concrete_concept", ""))
        if report.get("weakness_flags"):
            st.warning(" / ".join(str(x) for x in report.get("weakness_flags", [])))
        st.markdown("#### 제목 후보")
        st.dataframe(pd.DataFrame(report.get("title_candidates", [])), use_container_width=True)
        st.markdown("#### 24/32문구 선기획")
        st.dataframe(pd.DataFrame(report.get("phrase_plan", [])), use_container_width=True)
        st.markdown("#### 이모티콘 플러스 키워드 후보")
        st.dataframe(pd.DataFrame(report.get("plus_keywords", [])), use_container_width=True)
        st.markdown("#### 모션 템플릿 후보")
        st.dataframe(pd.DataFrame(report.get("motion_templates", [])), use_container_width=True)
        st.markdown("#### 포맷 추천")
        st.dataframe(pd.DataFrame(report.get("format_recommendation", [])), use_container_width=True)
        if report.get("revision_notes"):
            st.markdown("#### 보완 노트")
            for note in report.get("revision_notes", []):
                st.write("- " + str(note))
        if report.get("safety_notes"):
            st.markdown("#### 안전 노트")
            for note in report.get("safety_notes", []):
                st.write("- " + str(note))
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v34 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v34 JSON 다운로드", "json_path", "application/json"),
            ("v34 32문구 CSV 다운로드", "phrase_csv_path", "text/csv"),
            ("v34 제목 후보 CSV 다운로드", "title_csv_path", "text/csv"),
            ("v34 모션 템플릿 CSV 다운로드", "motion_csv_path", "text/csv"),
            ("v34 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)



if selected_page_index == 34:
    st.subheader("취향·경험 기반 아이디어 발굴 + 모션 템플릿 고도화")
    st.write("내가 좋아하는 것, 취미, 일상 경험, 관찰 메모를 독창 캐릭터 콘셉트·32문구·모션 템플릿·다중 플랫폼 재활용 계획으로 연결합니다.")

    col_a, col_b = st.columns([1.1, 0.9])
    with col_a:
        v35_favorites = st.text_area(
            "내가 좋아하는 것/감성/장르",
            value="낙서형 캐릭터, 직장인 공감, 소박한 음식, 사투리 말투",
            height=100,
            help="기존 캐릭터를 모방하기보다, 좋아하는 분위기·상황·취향을 독창 소재로 바꾸는 용도입니다.",
        )
        v35_hobbies = st.text_input("취미/관심사", value="수영, 산책, 유튜브 쇼츠 보기")
        v35_experience = st.text_area(
            "내 경험/생활권/직장·가족·지역 이야기",
            value="직장인이라 짧은 답장과 피곤한 리액션을 자주 쓴다. 충청권 생활 말투도 조금 넣고 싶다.",
            height=100,
        )
        v35_observation = st.text_area(
            "일상 관찰/릴스·쇼츠 메모",
            value="점심시간에 다들 지친 표정, 퇴근 직전 영혼 없는 답장, 귀찮지만 예의는 지키는 상황",
            height=100,
        )
    with col_b:
        v35_persona = st.text_input("캐릭터 방향/페르소나", value="피곤하지만 예의 바른 작은 감자 캐릭터")
        v35_count = st.radio("문구 선기획 수량", [24, 32], index=1, horizontal=True, key="v48_v35_count_radio")
        v35_motion_difficulty = st.selectbox(
            "모션 난이도",
            ["2컷 간단 모션", "4컷 기본 모션", "6컷 자연스러운 모션", "10컷 템플릿 모션"],
            index=1,
            help="초보자는 2~4컷부터 시작하고, 중요한 표현만 6~10컷으로 확장하는 구조가 안전합니다.",
            key="v48_v35_motion_difficulty",
        )
        v35_reuse = st.checkbox("카카오 외 플랫폼 재활용 계획 포함", value=True, key="v48_v35_reuse")
        st.markdown("### 반영 원칙")
        st.markdown(
            """
            - 내가 좋아하는 것/취미/일상에서 콘셉트 발굴  
            - 24개/32개 멘트를 먼저 정리  
            - 2컷/4컷/6컷/10컷 모션 난이도 선택  
            - 캐릭터 비율에 맞춘 모션 템플릿 계획  
            - 카카오 이후 인스타툰·릴스·OGQ·라인·굿즈 재활용 검토  
            - 기존 캐릭터 모방이 아니라 개인 경험 기반 독창화 유지
            """
        )

    if st.button("v35 취향·경험/모션 템플릿 리포트 생성", type="primary"):
        report = TasteExperienceMotionEngine().build_report(
            BASE_OUTPUT / "taste_experience_v35",
            favorites=v35_favorites,
            hobbies=v35_hobbies,
            life_experience=v35_experience,
            daily_observation=v35_observation,
            persona=v35_persona,
            target_count=int(v35_count),
            motion_difficulty=v35_motion_difficulty,
            include_platform_reuse=v35_reuse,
        )
        st.session_state.taste_experience_report = report.to_dict()
        st.success("v35 취향·경험 기반 아이디어/모션 템플릿 리포트 생성 완료")

    report = st.session_state.taste_experience_report
    if report:
        st.markdown("### v35 결과")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("콘셉트 후보", len(report.get("concept_candidates", [])))
        c2.metric("문구 수", len(report.get("phrase_plan", [])))
        c3.metric("모션 템플릿", len(report.get("motion_template_plan", [])))
        c4.metric("재활용 계획", len(report.get("platform_reuse_plan", [])))
        st.markdown("#### 개인 콘셉트 질문")
        st.dataframe(pd.DataFrame(report.get("personal_concept_questions", [])), use_container_width=True)
        st.markdown("#### 콘셉트 후보")
        st.dataframe(pd.DataFrame(report.get("concept_candidates", [])), use_container_width=True)
        st.markdown("#### 일상 경험/관찰 스토리 씨앗")
        st.dataframe(pd.DataFrame(report.get("story_seeds", [])), use_container_width=True)
        st.markdown("#### 24/32문구 계획")
        st.dataframe(pd.DataFrame(report.get("phrase_plan", [])), use_container_width=True)
        st.markdown("#### 모션 템플릿 계획")
        st.dataframe(pd.DataFrame(report.get("motion_template_plan", [])), use_container_width=True)
        st.markdown("#### 다중 플랫폼 재활용 계획")
        st.dataframe(pd.DataFrame(report.get("platform_reuse_plan", [])), use_container_width=True)
        st.markdown("#### 4주 제작 캘린더")
        st.dataframe(pd.DataFrame(report.get("content_calendar", [])), use_container_width=True)
        if report.get("safety_notes"):
            st.markdown("#### 안전 노트")
            for note in report.get("safety_notes", []):
                st.write("- " + str(note))
        if report.get("next_actions"):
            st.markdown("#### 다음 액션")
            for note in report.get("next_actions", []):
                st.write("- " + str(note))
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v35 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v35 JSON 다운로드", "json_path", "application/json"),
            ("v35 콘셉트 CSV 다운로드", "concept_csv_path", "text/csv"),
            ("v35 문구 CSV 다운로드", "phrase_csv_path", "text/csv"),
            ("v35 모션 CSV 다운로드", "motion_csv_path", "text/csv"),
            ("v35 플랫폼 CSV 다운로드", "platform_csv_path", "text/csv"),
            ("v35 제작 캘린더 CSV 다운로드", "calendar_csv_path", "text/csv"),
            ("v35 안전/액션 TXT 다운로드", "notes_txt_path", "text/plain"),
            ("v35 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)

if selected_page_index == 41:
    st.subheader("선택된 1차 포맷 자동 변환/압축")
    st.write("v37/v40에서 추천된 1개 포맷만 대상으로 원본을 보존한 채 규격 맞춤, 용량 최적화, 아이콘/공유 이미지 생성을 수행합니다. 다른 포맷은 확장 후보로만 남깁니다.")

    col_left, col_right = st.columns([1.1, 0.9])
    with col_left:
        v41_project_name = st.text_input("v41 프로젝트명", value="selected_format_autofix", key="v41_project_name")
        v41_title = st.text_input("작품/시리즈 제목", value="보리와 쌀", key="v41_title")
        format_options = list(SELECTED_FORMAT_SPECS.keys())
        format_labels = {k: SELECTED_FORMAT_SPECS[k].label for k in format_options}
        v41_selected_format = st.selectbox(
            "1차 제작 포맷 1개만 선택",
            format_options,
            index=0,
            format_func=lambda k: format_labels[k],
            key="v41_selected_format",
        )
        v41_uploaded_files = st.file_uploader(
            "자동 보정할 원본 이미지/WebP/GIF 업로드",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=True,
            key="v41_upload_files",
        )
        v41_placeholder = st.checkbox("원본이 부족하면 샘플 플레이스홀더로 구조 확인", value=True, key="v41_placeholder")
    with col_right:
        spec = SELECTED_FORMAT_SPECS[v41_selected_format]
        st.markdown("### 선택 포맷 기준")
        st.json({
            "포맷": spec.label,
            "수량": spec.count,
            "크기": f"{spec.canvas_size[0]}x{spec.canvas_size[1]}",
            "본문 최대 용량 KB": spec.max_kb,
            "WebP 최소 개수": spec.min_animated_webp,
            "최대 프레임": spec.max_frames,
            "메모": spec.note,
        })
        st.info("원본 파일은 original 폴더에 보존하고, 제출용 보정본은 fixed_selected_format_only 폴더에 따로 생성합니다.")

    if st.button("v41 선택 포맷 자동 변환/압축 실행", type="primary"):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            input_dir = tmp_dir / "v41_input"
            input_dir.mkdir(parents=True, exist_ok=True)
            for uploaded in v41_uploaded_files or []:
                safe_name = uploaded.name.replace("/", "_").replace("\\", "_")
                (input_dir / safe_name).write_bytes(uploaded.getbuffer())
            try:
                engine = SelectedFormatAutoFixEngine(BASE_OUTPUT / "selected_format_autofix_v41")
                report = engine.run(
                    input_dir=input_dir,
                    selected_format=v41_selected_format,
                    project_name=v41_project_name,
                    title=v41_title,
                    use_placeholders_when_empty=v41_placeholder,
                )
                st.session_state.selected_format_autofix_report = report
                st.success("v41 선택 포맷 자동 변환/압축 완료")
            except Exception as exc:
                st.error(f"v41 자동 변환/압축 실패: {exc}")

    if st.session_state.selected_format_autofix_report:
        report = st.session_state.selected_format_autofix_report
        st.markdown("### v41 자동 수정 결과")
        st.write(f"선택 포맷: **{report.get('selected_format_label')}**")
        st.write(f"통과: {report.get('pass_count')}건 / 주의: {report.get('warn_count')}건")
        records = report.get("records", [])
        if records:
            st.dataframe(pd.DataFrame(records), use_container_width=True)
        files = {
            "HTML 리포트": (report.get("html_path"), "text/html"),
            "JSON 리포트": (report.get("json_path"), "application/json"),
            "수정 전후 CSV": (report.get("csv_path"), "text/csv"),
            "주의사항 TXT": (report.get("notes_path"), "text/plain"),
            "전체 ZIP": (report.get("zip_path"), "application/zip"),
        }
        for label, (path_value, mime) in files.items():
            fp = Path(path_value or "")
            if fp.exists() and fp.is_file():
                st.download_button(f"v41 {label} 다운로드", data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 42:
    st.subheader("플랫폼별 재패키징 엔진")
    st.write("카카오 1차 포맷을 우선 유지하고, 반려·승인·성과 데이터 이후 선택적으로 네이버 OGQ/라인/밴드/SNS/굿즈용 초안을 생성합니다. 이 출력물은 공식 제출 보장본이 아니라 재활용 검토용입니다.")

    col_left, col_right = st.columns([1.1, 0.9])
    with col_left:
        v42_project_name = st.text_input("v42 프로젝트명", value="platform_repackaging", key="v42_project_name")
        v42_title = st.text_input("작품/시리즈 제목", value="보리와 쌀", key="v42_title")
        v42_source_format = st.selectbox(
            "현재 1차 포맷",
            ["문구 결합형 멈춰있는 이모티콘", "멈춰있는 이모티콘", "움직이는 문구 결합형", "움직이는 이모티콘", "미니 이모티콘", "큰 이모티콘"],
            index=0,
            key="v42_source_format",
        )
        platform_options = list(PLATFORM_TARGETS.keys())
        v42_platforms = st.multiselect(
            "재패키징할 플랫폼/용도 선택",
            platform_options,
            default=["naver_ogq", "line_sticker", "band_sticker", "sns_square"],
            format_func=lambda k: PLATFORM_TARGETS[k].label,
            key="v42_platforms",
        )
        v42_files = st.file_uploader(
            "재패키징할 원본 이미지 업로드",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=True,
            key="v42_upload_files",
        )
        v42_placeholder = st.checkbox("원본이 부족하면 샘플 이미지로 구조 확인", value=True, key="v42_placeholder")
        v42_max_assets = st.slider("플랫폼별 최대 초안 수", min_value=1, max_value=32, value=12, key="v42_max_assets")
    with col_right:
        st.markdown("### 선택 플랫폼 기준")
        if v42_platforms:
            st.dataframe(pd.DataFrame([
                {
                    "플랫폼": PLATFORM_TARGETS[k].label,
                    "초안 크기": f"{PLATFORM_TARGETS[k].draft_size[0]}x{PLATFORM_TARGETS[k].draft_size[1]}",
                    "용도": PLATFORM_TARGETS[k].role,
                    "주의": PLATFORM_TARGETS[k].official_check_note,
                }
                for k in v42_platforms
            ]), use_container_width=True)
        st.warning("v42 출력물은 타 플랫폼 재활용 초안입니다. 각 플랫폼의 최신 공식 규격·권리·폰트·용량 기준은 제출 직전에 다시 확인해야 합니다.")
        st.markdown("### 운영 원칙")
        st.markdown("""
        - 카카오 1차 포맷을 먼저 검증  
        - 다른 플랫폼은 확장 후보로만 선택  
        - 원본은 original 폴더에 보존  
        - 재패키징 파일은 draft_repackaged 폴더에 분리 저장  
        - 반려 사유 개선 없이 무리한 복붙 제출 금지
        """)

    if st.button("v42 플랫폼별 재패키징 초안 생성", type="primary"):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            input_dir = tmp_dir / "v42_input"
            input_dir.mkdir(parents=True, exist_ok=True)
            for uploaded in v42_files or []:
                safe_name = uploaded.name.replace("/", "_").replace("\\", "_")
                (input_dir / safe_name).write_bytes(uploaded.getbuffer())
            try:
                report = PlatformRepackagingEngine(BASE_OUTPUT / "platform_repackaging_v42").run(
                    input_dir=input_dir,
                    project_name=v42_project_name,
                    title=v42_title,
                    selected_platforms=v42_platforms,
                    source_format=v42_source_format,
                    max_assets_per_platform=int(v42_max_assets),
                    use_placeholders_when_empty=v42_placeholder,
                )
                st.session_state.platform_repackaging_report = report
                st.success("v42 플랫폼별 재패키징 초안 생성 완료")
            except Exception as exc:
                st.error(f"v42 재패키징 실패: {exc}")

    report = st.session_state.platform_repackaging_report
    if report:
        st.markdown("### v42 재패키징 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("플랫폼 수", len(report.get("platform_summaries", [])))
        c2.metric("생성 파일", len(report.get("records", [])))
        c3.metric("로드맵 단계", len(report.get("roadmap", [])))
        st.markdown("#### 플랫폼 요약")
        st.dataframe(pd.DataFrame(report.get("platform_summaries", [])), use_container_width=True)
        st.markdown("#### 생성 파일")
        st.dataframe(pd.DataFrame(report.get("records", [])), use_container_width=True)
        st.markdown("#### 확장 로드맵")
        st.dataframe(pd.DataFrame(report.get("roadmap", [])), use_container_width=True)
        if report.get("risk_notes"):
            st.markdown("#### 주의 노트")
            for note in report.get("risk_notes", []):
                st.write("- " + str(note))
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v42 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v42 JSON 다운로드", "json_path", "application/json"),
            ("v42 생성 파일 CSV 다운로드", "records_csv_path", "text/csv"),
            ("v42 확장 로드맵 CSV 다운로드", "roadmap_csv_path", "text/csv"),
            ("v42 주의사항 TXT 다운로드", "notes_path", "text/plain"),
            ("v42 전체 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 43:
    st.subheader("설치형 안정화/실행 오류 진단 강화")
    st.write("초보자가 설치·실행 중 막혔을 때 Python/패키지/권한/포트/필수 파일/데이터 폴더를 점검하고, 복구 순서와 지원용 ZIP을 생성합니다.")

    col_left, col_right = st.columns([1.1, 0.9])
    with col_left:
        v43_project_root = st.text_input("프로젝트 루트 경로", value=str(Path.cwd()), key="v43_project_root")
        v43_mode = st.selectbox("진단 모드", ["full", "quick", "support"], index=0, key="v43_mode", format_func=lambda x: {"full":"전체 진단", "quick":"빠른 진단", "support":"지원 패키지 생성"}.get(x, x))
        v43_make_backup = st.checkbox("경량 백업 생성", value=True, key="v43_make_backup")
        v43_outputs_summary = st.checkbox("outputs 폴더 크기/파일 수 확인", value=True, key="v43_outputs_summary")
        v43_ports = st.text_input("확인할 포트", value="8520,8521,8522,8501", key="v43_ports")
    with col_right:
        st.markdown("### v43 점검 항목")
        st.markdown("""
        - Python 버전 / 운영체제
        - 필수 파일과 실행 BAT 존재 여부
        - requirements.txt / 핵심 패키지 감지
        - outputs 쓰기 권한
        - 사용자 데이터 분리 폴더 확인
        - Streamlit 포트 충돌 확인
        - .venv 존재 여부
        - 설치 경로 길이/특수문자 위험
        - 오류 시 복구 순서 자동 생성
        """)
        st.info("자동 복구는 원본 삭제 없이 진단·포트 정리·패키지 재설치 안내·로그/리포트 수집 중심으로 동작합니다.")

    if st.button("v43 설치형 안정화 진단 실행", type="primary"):
        try:
            ports = [int(x.strip()) for x in v43_ports.split(",") if x.strip().isdigit()]
            report = InstallerStabilityEngine(BASE_OUTPUT / "installer_stability_v43").run(
                project_root=Path(v43_project_root),
                run_mode=v43_mode,
                app_version=APP_VERSION,
                ports=ports,
                make_backup=v43_make_backup,
                include_outputs_summary=v43_outputs_summary,
            )
            st.session_state.installer_stability_report = report
            st.success("v43 설치형 안정화 진단 완료")
        except Exception as exc:
            st.error(f"v43 설치형 안정화 진단 실패: {exc}")

    report = st.session_state.installer_stability_report
    if report:
        st.markdown("### v43 진단 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("상태", report.get("overall_status"))
        c2.metric("점수", report.get("score"))
        c3.metric("점검 항목", len(report.get("checks", [])))
        checks = report.get("checks", [])
        if checks:
            st.dataframe(pd.DataFrame(checks), use_container_width=True)
        if report.get("repair_steps"):
            st.markdown("#### 권장 복구 순서")
            for idx, step in enumerate(report.get("repair_steps", []), start=1):
                st.write(f"{idx}. {step}")
        files = report.get("files", {}) or {}
        for label, key, mime in [
            ("v43 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v43 JSON 다운로드", "json_path", "application/json"),
            ("v43 점검 CSV 다운로드", "csv_path", "text/csv"),
            ("v43 복구 순서 TXT 다운로드", "notes_path", "text/plain"),
            ("v43 지원 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(files.get(key, "")) if files.get(key) else Path("")
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 44:
    st.subheader("v48 후보 적용 / 정지형 캐릭터 품질 진화")
    st.write("후보를 표로만 보여주지 않고, 선택한 후보·트렌드·유튜브/인터넷 참고 메모를 실제 제작 흐름에 적용하는 탭입니다. 수집 자료는 캐릭터 복제가 아니라 감정 빈도, 문구 길이, 포즈 유형, 선명도 같은 추상 신호로만 사용합니다.")
    st.warning("자동 무단 크롤링이 아니라 사용자가 입력한 URL/제목/댓글 메모/CSV와 공식 API 기반 수집을 우선합니다. 기존 캐릭터를 비슷하게 만드는 용도로 사용하지 않습니다.")

    col_left, col_right = st.columns([1.1, 0.9])
    with col_left:
        v48_project_name = st.text_input("v48 프로젝트명", value="static_character_quality_evolution", key="v48_evolution_project_name")
        v48_character_concept = st.text_area(
            "현재 캐릭터 콘셉트/문제 상황",
            value=(st.session_state.get("active_text_prompt") or "피곤하지만 예의 바른 작은 캐릭터. 정지형 이미지가 아직 밋밋하고, 후보 선택이 실제 제작에 바로 이어지지 않는다."),
            height=110,
            key="v48_evolution_concept",
        )
        v48_issue_text = st.text_area(
            "개선하고 싶은 점",
            value="후보를 선택하면 바로 적용되게 하고, 멈춰있는 캐릭터도 외곽선·실루엣·표정·포즈가 더 선명해서 퀄리티가 좋아지면 좋겠다.",
            height=90,
            key="v48_evolution_issue",
        )
        v48_source_text = st.text_area(
            "유튜브/인터넷 참고 메모, 영상 제목, 댓글 경향, 캡처에서 읽은 문구",
            value="직장인 공감, 퇴근, 넵 확인했습니다, 죄송합니다, 피곤, 살려주세요, 짧은 답장, 큰 문구, 단순한 표정, 포즈가 귀여운 캐릭터",
            height=145,
            key="v48_evolution_source_text",
        )
        v48_source_urls = st.text_area(
            "참고 URL 목록 또는 출처 메모",
            value="",
            height=80,
            key="v48_evolution_source_urls",
            help="URL은 그대로 복제하지 않고 출처/관찰 메모로 기록합니다.",
        )
    with col_right:
        v48_target_format = st.selectbox(
            "우선 개선 포맷",
            ["static_text", "static", "animated_text", "mini", "big"],
            index=0,
            format_func=lambda k: {"static_text":"문구형 정지", "static":"정지형", "animated_text":"움직이는 문구형", "mini":"미니", "big":"큰 이모티콘"}.get(k, k),
            key="v48_evolution_target_format",
        )
        v48_priority = st.selectbox(
            "개선 우선순위",
            ["정지형 품질 우선", "문구/사용성 우선", "표정 다양성 우선", "시리즈 확장 우선"],
            index=0,
            key="v48_evolution_priority",
        )
        st.markdown("### 적용될 흐름")
        st.markdown(
            """
            1. 참고 메모/URL에서 추상 신호 추출  
            2. 정지형 품질 개선 액션 생성  
            3. 적용 프로필과 32개 표현 씨앗 생성  
            4. 버튼을 누르면 표현 은행과 텍스트 초안 기본값에 적용  
            5. 15번 후보 갤러리, 16번 편집기, 17번 채팅 미리보기로 연결
            """
        )

    if st.button("v48 진화형 품질 분석 실행", type="primary", key="v48_run_evolution_analysis"):
        try:
            report = CharacterTrendEvolutionEngine().build_report(
                BASE_OUTPUT / "v48_character_evolution",
                project_name=v48_project_name,
                character_concept=v48_character_concept,
                issue_text=v48_issue_text,
                source_text=v48_source_text,
                source_urls=v48_source_urls,
                target_format=v48_target_format,
                priority=v48_priority,
            )
            st.session_state.v48_evolution_report = report.to_dict()
            st.success("v48 진화형 캐릭터 품질 분석 완료")
        except Exception as exc:
            st.error(f"v48 진화형 품질 분석 실패: {exc}")

    report = st.session_state.get("v48_evolution_report")
    if report:
        st.markdown("### v48 분석 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("정지형 품질 점수", report.get("static_quality_score", 0))
        c2.metric("독창성 방어 점수", report.get("originality_guard_score", 0))
        c3.metric("추출 신호", len(report.get("extracted_signals", [])))

        board = Path(report.get("board_png_path", ""))
        if board.exists():
            st.image(str(board), caption="정지형 캐릭터 품질 진화 보드", use_container_width=True)

        st.markdown("#### 적용 프로필")
        st.json(report.get("applied_profile", {}))
        st.markdown("#### 품질 개선 액션")
        st.dataframe(pd.DataFrame(report.get("quality_actions", [])), use_container_width=True)
        st.markdown("#### 32개 표현 씨앗")
        st.dataframe(pd.DataFrame(report.get("expression_seed_phrases", [])), use_container_width=True)

        if st.button("이 진화형 품질 프로필을 현재 제작 흐름에 적용", type="secondary", key="v48_apply_evolution_profile"):
            profile = report.get("applied_profile", {})
            seeds = report.get("expression_seed_phrases", [])
            st.session_state.active_generation_profile = {"source": "v48_character_evolution", **profile}
            st.session_state.v48_evolution_applied = st.session_state.active_generation_profile
            st.session_state.active_text_prompt = profile.get("recommended_prompt", "")
            st.session_state.expressions = seeds
            try:
                applied_report = TextPromptEmoticonEngine().build_project(
                    BASE_OUTPUT / "v48_applied_evolution_profile",
                    prompt=profile.get("recommended_prompt", ""),
                    project_name=f"{report.get('project_name', 'v48')}_applied",
                    format_key=profile.get("target_format", "static_text"),
                    expression_count=min(32, max(12, len(seeds) or 32)),
                )
                st.session_state.text_prompt_report = applied_report.to_dict()
                st.success("진화형 품질 프로필을 텍스트 초안, 표현 은행, 후보 갤러리 입력값에 적용했습니다.")
            except Exception as exc:
                st.warning(f"프로필은 적용했지만 즉시 텍스트 초안 생성은 실패했습니다: {exc}")

        for label, path_key, mime in [
            ("v48 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v48 JSON 다운로드", "json_path", "application/json"),
            ("v48 표현 씨앗 CSV 다운로드", "csv_path", "text/csv"),
            ("v48 품질 보드 PNG 다운로드", "board_png_path", "image/png"),
            ("v48 전체 패키지 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(report.get(path_key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime)


if selected_page_index == 45:
    st.markdown(
        """
        <div class="v49-hero">
          <h2>후보 적용 / 정지형 / 움직이는형 품질 진화 하기</h2>
          <p>후보를 보는 단계에서 끝내지 않고, 선택한 콘셉트와 업로드 자료를 실제 제작 흐름에 적용합니다. 정지형 캐릭터를 기준으로 같은 외형을 유지한 움직이는형 초안까지 연결합니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.warning(
        "유튜브/인터넷 참고자료는 기존 캐릭터 복제용이 아니라 감정 빈도, 문구 길이, 포즈 유형, 모션 리듬, 색 대비 같은 추상 신호 분석용으로만 사용합니다."
    )

    top_cols = st.columns(4)
    top_cols[0].metric("흐름", "후보→적용")
    top_cols[1].metric("정지형", "품질 진화")
    top_cols[2].metric("움직이는형", "자동 변환")
    top_cols[3].metric("파일", "다중/ZIP")

    col_left, col_right = st.columns([1.05, 0.95])
    with col_left:
        st.markdown("<div class='v49-card'>", unsafe_allow_html=True)
        v49_project_name = st.text_input("v49 프로젝트명", value="static_animated_quality_evolution", key="v49_project_name")
        default_concept = st.session_state.get("active_text_prompt") or "피곤하지만 예의 바르고 짧은 답장이 편한 독창 캐릭터. 정지형 캐릭터를 먼저 만들고, 같은 외형을 유지해서 움직이는 캐릭터까지 확장하고 싶다."
        v49_character_concept = st.text_area("현재 캐릭터 콘셉트 / 후보 선택 내용", value=default_concept, height=115, key="v49_character_concept")
        v49_issue_text = st.text_area(
            "개선하고 싶은 점",
            value="창이 더 세련돼 보이고, 후보를 선택하면 실제 제작 흐름에 적용되며, 안움직이는 캐릭터와 움직이는 캐릭터 모두 퀄리티가 진화하면 좋겠다.",
            height=95,
            key="v49_issue_text",
        )
        v49_source_text = st.text_area(
            "유튜브/인터넷 참고 메모, 제목, 댓글 경향, 캡처에서 읽은 문구",
            value="직장인 공감, 짧은 답장, 넵 확인했습니다, 퇴근, 피곤, 살려주세요, 큰 실루엣, 굵은 외곽선, 표정이 선명한 캐릭터, 통통 움직임, 눈깜빡임, 말풍선 팝업",
            height=135,
            key="v49_source_text",
        )
        v49_source_urls = st.text_area(
            "참고 URL / 출처 메모",
            value="",
            height=75,
            key="v49_source_urls",
            help="URL 자체를 무단 복제하지 않고 출처/관찰 메모로만 기록합니다.",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='v49-card'>", unsafe_allow_html=True)
        v49_target_formats = st.multiselect(
            "동시에 개선할 포맷",
            ["static", "static_text", "animated", "animated_text", "mini", "big"],
            default=["static", "animated"],
            format_func=lambda k: {
                "static": "멈춰있는 캐릭터",
                "static_text": "문구형 멈춰있는 캐릭터",
                "animated": "움직이는 캐릭터",
                "animated_text": "움직이는 문구형",
                "mini": "미니 이모티콘",
                "big": "큰 이모티콘",
            }.get(k, k),
            key="v49_target_formats",
        )
        v49_target_style = st.selectbox(
            "화면/캐릭터 스타일 방향",
            ["귀엽고 세련된 카카오톡형", "직장인용 깔끔한 문구형", "낙서형이지만 완성도 있는 스타일", "미니멀하고 고급스러운 스타일"],
            index=0,
            key="v49_target_style",
        )
        v49_uploaded_files = st.file_uploader(
            "이미지/텍스트/CSV/JSON/ZIP 여러 개 첨부",
            type=["png", "jpg", "jpeg", "webp", "bmp", "gif", "txt", "md", "csv", "json", "srt", "vtt", "zip"],
            accept_multiple_files=True,
            key="v49_multi_zip_uploads",
            help="정지형 PNG, 움직이는 GIF/WebP, 참고 메모 TXT/CSV, 여러 자료를 묶은 ZIP을 함께 올릴 수 있습니다.",
        )
        st.markdown("### 실행 단계")
        for i, text in enumerate([
            "후보/메모/업로드 자료 분석",
            "정지형 품질 규칙 생성",
            "정지형을 기준으로 움직이는형 모션 계획 생성",
            "표현 은행/텍스트 초안/갤러리에 적용",
        ], start=1):
            st.markdown(f"<div class='v49-step'><b>{i}</b> · {text}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("v49 후보 적용/정지형/움직이는형 품질 진화 실행", type="primary", key="v49_run_static_animated_evolution"):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                saved_paths = []
                for uploaded in v49_uploaded_files or []:
                    safe_name = uploaded.name.replace("/", "_").replace("\\", "_")
                    path = tmp_dir / safe_name
                    path.write_bytes(uploaded.getbuffer())
                    saved_paths.append(path)
                report = StaticAnimatedEvolutionEngine().build_report(
                    BASE_OUTPUT / "v49_static_animated_evolution",
                    project_name=v49_project_name,
                    character_concept=v49_character_concept,
                    issue_text=v49_issue_text,
                    source_text=v49_source_text,
                    source_urls=v49_source_urls,
                    target_formats=v49_target_formats or ["static", "animated"],
                    target_style=v49_target_style,
                    input_paths=saved_paths,
                )
            st.session_state.v49_static_animated_evolution_report = report.to_dict()
            st.success("v49 정지형/움직이는형 통합 품질 진화 분석이 완료되었습니다.")
        except Exception as exc:
            st.error(f"v49 품질 진화 실행 실패: {exc}")

    v49_report = st.session_state.get("v49_static_animated_evolution_report")
    if v49_report:
        st.markdown("### v49 분석 결과")
        result_cols = st.columns(5)
        result_cols[0].metric("정지형 품질", v49_report.get("static_quality_score", 0))
        result_cols[1].metric("움직이는형 품질", v49_report.get("animated_quality_score", 0))
        result_cols[2].metric("독창성 방어", v49_report.get("originality_guard_score", 0))
        result_cols[3].metric("이미지", v49_report.get("image_count", 0))
        result_cols[4].metric("ZIP", v49_report.get("zip_count", 0))

        board_path = Path(v49_report.get("board_png_path", ""))
        gif_path = Path(v49_report.get("animated_preview_gif_path", ""))
        media_cols = st.columns([1, 1])
        if board_path.exists():
            media_cols[0].image(str(board_path), caption="v49 품질 진화 보드", use_container_width=True)
        if gif_path.exists():
            media_cols[1].image(str(gif_path), caption="정지형을 기준으로 만든 움직이는형 미리보기 GIF", use_container_width=True)

        st.markdown("#### 캐릭터 정체성 프로필")
        st.json(v49_report.get("identity_profile", {}))

        st.markdown("#### 업로드/ZIP 분석 요약")
        uploaded_summary = v49_report.get("uploaded_source_summary", [])
        if uploaded_summary:
            st.dataframe(pd.DataFrame(uploaded_summary), use_container_width=True)
        else:
            st.info("업로드 파일이 없으면 입력한 메모/URL만 분석합니다.")

        tab_a, tab_b, tab_c, tab_d = st.tabs(["정지형 개선", "움직이는형 개선", "모션 변환 계획", "표현 씨앗"])
        with tab_a:
            st.dataframe(pd.DataFrame(v49_report.get("static_quality_actions", [])), use_container_width=True)
        with tab_b:
            st.dataframe(pd.DataFrame(v49_report.get("animated_quality_actions", [])), use_container_width=True)
        with tab_c:
            st.dataframe(pd.DataFrame(v49_report.get("static_to_animated_plan", [])), use_container_width=True)
        with tab_d:
            st.dataframe(pd.DataFrame(v49_report.get("expression_seed_phrases", [])), use_container_width=True)

        if st.button("v49 결과를 현재 제작 흐름에 적용", type="secondary", key="v49_apply_to_workflow"):
            identity = v49_report.get("identity_profile", {}) or {}
            expressions = v49_report.get("expression_seed_phrases", []) or []
            motion_plan = v49_report.get("static_to_animated_plan", []) or []
            recommended_prompt = (
                f"{identity.get('material', '독창 캐릭터')}를 기준으로 정지형과 움직이는형을 함께 제작한다. "
                f"{identity.get('base_silhouette', '큰 실루엣')}을 유지하고, {identity.get('line_weight', '굵은 외곽선')}을 적용한다. "
                f"정지형은 표정/포즈/문구를 선명하게 구분하고, 움직이는형은 정지형 시안을 기준 프레임으로 삼아 눈깜빡임·통통 움직임·말풍선 팝업만 추가한다. "
                f"말투는 {identity.get('tone_rule', '짧은 카톡 답장')} 중심으로 한다."
            )
            st.session_state.active_generation_profile = {
                "source": "v49_static_animated_evolution",
                "identity_profile": identity,
                "static_to_animated_plan": motion_plan,
                "target_formats": v49_report.get("identity_profile", {}).get("target_formats", v49_target_formats),
            }
            st.session_state.v49_static_animated_evolution_applied = st.session_state.active_generation_profile
            st.session_state.active_text_prompt = recommended_prompt
            st.session_state.expressions = expressions
            try:
                applied_report = TextPromptEmoticonEngine().build_project(
                    BASE_OUTPUT / "v49_applied_static_animated_evolution",
                    prompt=recommended_prompt,
                    project_name=f"{v49_report.get('project_name', 'v49')}_applied",
                    format_key="animated" if "animated" in (v49_target_formats or []) else "static",
                    expression_count=min(32, max(12, len(expressions) or 32)),
                )
                st.session_state.text_prompt_report = applied_report.to_dict()
                st.success("v49 결과를 텍스트 초안, 표현 은행, 정지형/움직이는형 제작 흐름에 적용했습니다.")
            except Exception as exc:
                st.warning(f"프로필과 표현은 적용했지만 즉시 초안 생성은 실패했습니다: {exc}")

        for label, path_key, mime in [
            ("v49 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v49 JSON 다운로드", "json_path", "application/json"),
            ("v49 표현 씨앗 CSV 다운로드", "csv_path", "text/csv"),
            ("v49 품질 보드 PNG 다운로드", "board_png_path", "image/png"),
            ("v49 움직이는형 미리보기 GIF 다운로드", "animated_preview_gif_path", "image/gif"),
            ("v49 전체 패키지 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(v49_report.get(path_key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v49_download_{path_key}")


if selected_page_index == 46:
    st.markdown(
        """
        <div class="v49-hero">
          <h2>v53 설치/정리/바탕화면 아이콘 안정화 · v52 정지형 기반 움직이는형 생성/제안 반영 · v51 API 키/쿼터 장부 안전모드</h2>
          <p>API 키는 선택 입력, 수집은 최근 30일 기준, 쿼터 카운터와 유료 호출 차단을 기본값으로 둡니다. 로컬 파일/ZIP 분석을 가장 먼저 실행합니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("기본값은 비용 0원 모드입니다. 외부 API 키는 세션 입력값으로만 사용하고 리포트에는 원문을 저장하지 않습니다.")

    guard_cols = st.columns(5)
    guard_cols[0].metric("기본 모드", "무료")
    guard_cols[1].metric("수집 기준", "최근 30일")
    guard_cols[2].metric("유료 호출", "차단")
    guard_cols[3].metric("우선순위", "로컬/ZIP")
    guard_cols[4].metric("OpenAI", "선택형")

    left, right = st.columns([1.05, 0.95])
    with left:
        st.markdown("<div class='v49-card'>", unsafe_allow_html=True)
        v50_project_name = st.text_input("v50 프로젝트명", value="v50_free_api_safety_mode", key="v50_project_name")
        v50_keywords = st.text_area(
            "30일 수집 키워드 / 분석 키워드",
            value="직장인 공감 이모티콘, 짧은 답장, 퇴근, 피곤, 넵, 확인했습니다, 카카오톡 문구",
            height=90,
            key="v50_keywords",
        )
        v50_manual_notes = st.text_area(
            "로컬 분석용 메모 / 유튜브 제목·댓글 경향 / 인터넷 참고 메모",
            value="정지형 캐릭터는 외곽선이 굵고 표정 차이가 커야 한다. 움직이는형은 정지형 시안을 그대로 기준 프레임으로 유지하고 눈깜빡임, 통통 점프, 말풍선 팝업만 추가한다.",
            height=145,
            key="v50_manual_notes",
        )
        v50_local_files = st.file_uploader(
            "로컬 파일/ZIP 여러 개 업로드",
            type=["png", "jpg", "jpeg", "webp", "bmp", "gif", "txt", "md", "csv", "json", "srt", "vtt", "zip"],
            accept_multiple_files=True,
            key="v50_local_files",
            help="ZIP 안의 이미지/텍스트/CSV/JSON/SRT/VTT를 안전 한도 안에서 분석합니다.",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='v49-card'>", unsafe_allow_html=True)
        st.markdown("### API 키 입력 / 안전 제한")
        v50_youtube_key = st.text_input("YouTube API Key 선택 입력", type="password", key="v50_youtube_key")
        v50_openai_key = st.text_input("OpenAI API Key 선택 입력", type="password", key="v50_openai_key")
        v50_google_key = st.text_input("Google Search API Key 선택 입력", type="password", key="v50_google_key")
        v50_youtube_enabled = st.checkbox("YouTube API 무료 쿼터 수집 사용", value=False, key="v50_youtube_enabled")
        v50_google_enabled = st.checkbox("Google 검색 API 사용", value=False, key="v50_google_enabled", help="기본 OFF. 실제 과금/제공 조건은 사용자 프로젝트 설정을 따릅니다.")
        v50_openai_enabled = st.checkbox("OpenAI 고급 분석 사용", value=False, key="v50_openai_enabled", help="기본 OFF. 사용자가 직접 켠 경우에만 고급 분석 단계로 표시합니다.")
        v50_paid_allowed = st.checkbox("유료 호출을 허용합니다", value=False, key="v50_paid_allowed")
        if not v50_paid_allowed:
            st.success("유료 호출 차단 ON: 예상 비용 0원 모드")
        else:
            st.warning("유료 호출 허용 상태입니다. 실제 호출 전 별도 확인창을 두는 구조로 사용하세요.")
        st.markdown("</div>", unsafe_allow_html=True)

    limits = st.expander("쿼터/무료 제한 설정", expanded=False)
    with limits:
        c1, c2, c3, c4 = st.columns(4)
        v50_days = c1.slider("수집 기간", 1, 30, 30, key="v50_days")
        v50_yt_search_limit = c2.slider("YouTube 검색/일", 0, 100, 20, key="v50_yt_search_limit")
        v50_yt_video_limit = c3.slider("YouTube 영상상세/일", 0, 500, 200, key="v50_yt_video_limit")
        v50_openai_limit = c4.slider("OpenAI 분석/일", 0, 50, 0, key="v50_openai_limit")

    if st.button("v50 무료 API 안전모드 실행", type="primary", key="v50_run_free_api_safety"):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                saved_paths = []
                for uploaded in v50_local_files or []:
                    safe_name = uploaded.name.replace("/", "_").replace("\\", "_")
                    target = tmp_dir / safe_name
                    target.write_bytes(uploaded.getbuffer())
                    saved_paths.append(target)
                config = FreeApiSafetyConfig(
                    project_name=v50_project_name,
                    days=v50_days,
                    youtube_enabled=bool(v50_youtube_enabled),
                    google_search_enabled=bool(v50_google_enabled),
                    openai_enabled=bool(v50_openai_enabled),
                    paid_calls_allowed=bool(v50_paid_allowed),
                    daily_youtube_search_limit=int(v50_yt_search_limit),
                    daily_youtube_video_limit=int(v50_yt_video_limit),
                    daily_youtube_comment_limit=100,
                    daily_openai_call_limit=int(v50_openai_limit),
                    monthly_budget_limit_krw=0 if not v50_paid_allowed else 10000,
                    local_first=True,
                    store_raw_api_keys=False,
                )
                report = FreeApiSafetyEngine().build_report(
                    BASE_OUTPUT / "v50_free_api_safety",
                    config=config,
                    local_input_paths=saved_paths,
                    manual_notes=v50_manual_notes,
                    youtube_api_key=v50_youtube_key,
                    google_api_key=v50_google_key,
                    openai_api_key=v50_openai_key,
                    search_keywords=v50_keywords,
                )
            st.session_state.v50_free_api_safety_report = report.to_dict()
            st.success("v50 무료 API 안전모드 분석이 완료되었습니다.")
        except Exception as exc:
            st.error(f"v50 무료 API 안전모드 실행 실패: {exc}")

    v50_report = st.session_state.get("v50_free_api_safety_report")
    if v50_report:
        st.markdown("### v50 결과")
        qcols = st.columns(5)
        qcols[0].metric("모드", v50_report.get("mode", ""))
        qcols[1].metric("분석 기간", f"{v50_report.get('days', 30)}일")
        qcols[2].metric("로컬 파일", len(v50_report.get("local_source_summary", [])))
        qcols[3].metric("개선 액션", len(v50_report.get("quality_actions", [])))
        qcols[4].metric("유료 허용", str(v50_report.get("paid_call_guard", {}).get("paid_calls_allowed", False)))

        st.markdown("#### 쿼터 카운터")
        st.dataframe(pd.DataFrame(v50_report.get("quota_snapshots", [])), use_container_width=True)

        st.markdown("#### API 키 상태")
        st.json(v50_report.get("api_key_status", {}))

        st.markdown("#### 수집 계획")
        st.dataframe(pd.DataFrame(v50_report.get("collection_plan", [])), use_container_width=True)

        st.markdown("#### 로컬 파일/ZIP 분석")
        local_rows = v50_report.get("local_source_summary", [])
        if local_rows:
            st.dataframe(pd.DataFrame(local_rows), use_container_width=True)
        else:
            st.info("업로드 파일이 없어서 메모/키워드 중심으로 분석했습니다.")

        st.markdown("#### 품질 개선 액션")
        st.dataframe(pd.DataFrame(v50_report.get("quality_actions", [])), use_container_width=True)

        st.markdown("#### 제작 흐름 적용값")
        st.json(v50_report.get("workflow_application", {}))

        if st.button("v50 결과를 현재 제작 흐름에 적용", type="secondary", key="v50_apply_to_workflow"):
            workflow = v50_report.get("workflow_application", {}) or {}
            st.session_state.active_generation_profile = workflow.get("active_generation_profile", {})
            st.session_state.active_text_prompt = workflow.get("recommended_prompt", "")
            st.session_state.expressions = workflow.get("expression_seed_phrases", [])
            st.session_state.v50_free_api_safety_applied = workflow
            st.success("v50 결과를 표현 은행/텍스트 초안/정지형·움직이는형 제작 흐름에 적용했습니다.")

        board_path = Path(v50_report.get("board_png_path", ""))
        if board_path.exists() and board_path.stat().st_size > 0:
            st.image(str(board_path), caption="v50 무료 API 안전모드 보드", use_container_width=True)

        for label, path_key, mime in [
            ("v50 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v50 JSON 다운로드", "json_path", "application/json"),
            ("v50 품질 액션 CSV 다운로드", "csv_path", "text/csv"),
            ("v50 보드 PNG 다운로드", "board_png_path", "image/png"),
            ("v50 전체 패키지 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(v50_report.get(path_key, ""))
            if fp.exists() and fp.is_file() and fp.stat().st_size > 0:
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v50_download_{path_key}")


if selected_page_index == 47:
    st.markdown(
        """
        <div class="v49-hero">
          <h2>v51 API 키/쿼터 장부/유료차단</h2>
          <p>실제 외부 API 호출 전에 키 입력 상태, 30일 제한, 오늘 사용량, 계획 수집량, 유료 호출 차단 여부를 먼저 점검합니다. 기본값은 비용 0원 사전검증입니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("v51은 외부 API를 직접 호출하지 않는 사전검증/계획/장부 단계입니다. API 키 원문은 리포트·CSV·ZIP에 저장하지 않습니다.")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("기본 모드", "비용 0원")
    k2.metric("수집 기간", "최대 30일")
    k3.metric("키 원문 저장", "안 함")
    k4.metric("쿼터 장부", "JSON")
    k5.metric("외부 호출", "사전 차단")

    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown("<div class='v49-card'>", unsafe_allow_html=True)
        v51_project_name = st.text_input("v51 프로젝트명", value="v51_api_guardrail_ledger", key="v51_project_name")
        v51_keywords = st.text_area(
            "최근 30일 수집/분석 키워드",
            value="직장인 공감 이모티콘, 짧은 답장, 퇴근, 피곤, 넵, 확인했습니다, 움직이는 문구형",
            height=90,
            key="v51_keywords",
        )
        v51_manual_notes = st.text_area(
            "로컬 분석 메모 / 영상 제목·댓글 경향 / 참고자료 요약",
            value="후보만 보여주지 말고 선택하면 표현 은행과 정지형/움직이는형 제작 흐름에 적용한다. 정지형 캐릭터의 외형과 색상을 기준 프레임으로 유지하고 움직이는형은 눈깜빡임, 통통점프, 말풍선 팝업을 추가한다.",
            height=140,
            key="v51_manual_notes",
        )
        v51_local_files = st.file_uploader(
            "로컬 파일/ZIP 여러 개 업로드",
            type=["png", "jpg", "jpeg", "webp", "bmp", "gif", "txt", "md", "csv", "json", "srt", "vtt", "zip"],
            accept_multiple_files=True,
            key="v51_local_files",
            help="로컬 파일 분석이 1순위입니다. ZIP 안의 지원 파일도 안전 한도 안에서 분석합니다.",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='v49-card'>", unsafe_allow_html=True)
        st.markdown("### API 키 입력 / 기본 차단")
        v51_youtube_key = st.text_input("YouTube API Key 선택 입력", type="password", key="v51_youtube_key")
        v51_google_key = st.text_input("Google Search API Key 선택 입력", type="password", key="v51_google_key")
        v51_openai_key = st.text_input("OpenAI API Key 선택 입력", type="password", key="v51_openai_key")
        v51_youtube_enabled = st.checkbox("YouTube API 수집 계획 켜기", value=False, key="v51_youtube_enabled")
        v51_google_enabled = st.checkbox("Google 검색 API 수집 계획 켜기", value=False, key="v51_google_enabled")
        v51_openai_enabled = st.checkbox("OpenAI 고급 분석 계획 켜기", value=False, key="v51_openai_enabled")
        v51_paid_allowed = st.checkbox("유료 호출 허용", value=False, key="v51_paid_allowed")
        v51_reserve_plan = st.checkbox("이번 계획량을 오늘 쿼터 장부에 예약 기록", value=False, key="v51_reserve_plan", help="실제 API 호출은 아니지만, 중복 수집 방지를 위해 오늘 계획량을 장부에 더합니다.")
        if v51_paid_allowed:
            st.warning("유료 호출 허용 상태입니다. v51은 그래도 직접 호출하지 않고 사전검증만 합니다.")
        else:
            st.success("유료 호출 차단 ON: 비용 0원 사전검증")
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("v51 쿼터/무료 제한 설정", expanded=False):
        c1, c2, c3, c4, c5 = st.columns(5)
        v51_days = c1.slider("수집 기간", 1, 30, 30, key="v51_days")
        v51_yt_search_limit = c2.slider("YouTube 검색/일", 0, 100, 20, key="v51_yt_search_limit")
        v51_yt_video_limit = c3.slider("영상상세/일", 0, 500, 200, key="v51_yt_video_limit")
        v51_comment_limit = c4.slider("댓글 샘플/일", 0, 300, 100, key="v51_comment_limit")
        v51_openai_limit = c5.slider("OpenAI 분석/일", 0, 50, 0, key="v51_openai_limit")
        c6, c7 = st.columns(2)
        v51_google_limit = c6.slider("Google 검색/일", 0, 100, 0, key="v51_google_limit")
        v51_budget = c7.number_input("월 예산 한도 KRW", min_value=0, max_value=1000000, value=0, step=1000, key="v51_budget")

    if st.button("v51 API 키/쿼터 사전검증 실행", type="primary", key="v51_run_guardrail"):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                saved_paths = []
                for uploaded in v51_local_files or []:
                    safe_name = uploaded.name.replace("/", "_").replace("\\", "_")
                    target = tmp_dir / safe_name
                    target.write_bytes(uploaded.getbuffer())
                    saved_paths.append(target)
                config = V51ApiGuardrailConfig(
                    project_name=v51_project_name,
                    days=int(v51_days),
                    free_mode=not bool(v51_paid_allowed),
                    youtube_enabled=bool(v51_youtube_enabled),
                    google_search_enabled=bool(v51_google_enabled),
                    openai_enabled=bool(v51_openai_enabled),
                    paid_calls_allowed=bool(v51_paid_allowed),
                    local_first=True,
                    reserve_quota_plan=bool(v51_reserve_plan),
                    daily_youtube_search_limit=int(v51_yt_search_limit),
                    daily_youtube_video_limit=int(v51_yt_video_limit),
                    daily_youtube_comment_limit=int(v51_comment_limit),
                    daily_google_search_limit=int(v51_google_limit),
                    daily_openai_analysis_limit=int(v51_openai_limit),
                    monthly_budget_limit_krw=int(v51_budget),
                )
                report = V51ApiGuardrailLedgerEngine().build_report(
                    BASE_OUTPUT / "v51_api_guardrail_ledger",
                    config=config,
                    local_input_paths=saved_paths,
                    manual_notes=v51_manual_notes,
                    search_keywords=v51_keywords,
                    youtube_api_key=v51_youtube_key,
                    google_api_key=v51_google_key,
                    openai_api_key=v51_openai_key,
                )
            st.session_state.v51_api_guardrail_report = report.to_dict()
            st.success("v51 API 키/쿼터 사전검증이 완료되었습니다.")
        except Exception as exc:
            st.error(f"v51 API 키/쿼터 사전검증 실패: {exc}")

    v51_report = st.session_state.get("v51_api_guardrail_report")
    if v51_report:
        st.markdown("### v51 결과")
        r1, r2, r3, r4, r5 = st.columns(5)
        r1.metric("모드", v51_report.get("mode", ""))
        r2.metric("분석 기간", f"{v51_report.get('days', 30)}일")
        r3.metric("계획 작업", len(v51_report.get("planned_jobs", [])))
        r4.metric("로컬 파일", len(v51_report.get("local_source_summary", [])))
        r5.metric("경고", len(v51_report.get("safety_warnings", [])))

        st.markdown("#### API 키 상태")
        st.json(v51_report.get("api_key_status", {}))

        st.markdown("#### 쿼터 장부")
        st.dataframe(pd.DataFrame(v51_report.get("quota_ledger", [])), use_container_width=True)

        st.markdown("#### 수집 계획")
        st.dataframe(pd.DataFrame(v51_report.get("planned_jobs", [])), use_container_width=True)

        st.markdown("#### 안전 경고")
        for warning in v51_report.get("safety_warnings", []):
            st.warning(warning) if "위험" in warning or "초과" in warning or "차단" in warning else st.info(warning)

        st.markdown("#### 로컬 파일/ZIP 분석")
        local_rows = v51_report.get("local_source_summary", [])
        if local_rows:
            st.dataframe(pd.DataFrame(local_rows), use_container_width=True)
        else:
            st.info("업로드 파일 없이 메모/키워드 중심으로 사전검증했습니다.")

        st.markdown("#### 제작 흐름 적용값")
        st.json(v51_report.get("workflow_application", {}))

        if st.button("v51 결과를 현재 제작 흐름에 적용", type="secondary", key="v51_apply_to_workflow"):
            workflow = v51_report.get("workflow_application", {}) or {}
            st.session_state.active_generation_profile = workflow.get("active_generation_profile", {})
            st.session_state.active_text_prompt = workflow.get("recommended_prompt", "")
            st.session_state.expressions = workflow.get("expression_seed_phrases", [])
            st.session_state.v51_api_guardrail_applied = workflow
            st.success("v51 결과를 표현 은행/텍스트 초안/정지형·움직이는형 제작 흐름에 적용했습니다.")

        board_path = Path(v51_report.get("board_png_path", ""))
        if board_path.exists() and board_path.stat().st_size > 0:
            st.image(str(board_path), caption="v51 API 키/쿼터 장부 보드", use_container_width=True)

        for label, path_key, mime in [
            ("v51 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v51 JSON 다운로드", "json_path", "application/json"),
            ("v51 계획 CSV 다운로드", "csv_path", "text/csv"),
            ("v51 보드 PNG 다운로드", "board_png_path", "image/png"),
            ("v51 전체 패키지 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            fp = Path(v51_report.get(path_key, ""))
            if fp.exists() and fp.is_file() and fp.stat().st_size > 0:
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v51_download_{path_key}")

if selected_page_index == 48:
    st.subheader("정지형 캐릭터 기반 움직이는형 생성 + 선택 제안 반영 재생성")
    st.write("정지형 캐릭터를 먼저 만들고, 사용자가 선택한 개선 제안을 실제 정지형 재생성과 움직이는형 GIF 생성에 반영합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v52 Static → Animated Apply Flow</h2>
      <p>정지형 identity를 잠그고, 선택한 제안만 반영해서 캐릭터를 다시 생성한 뒤 같은 외형으로 움직이는형을 만듭니다.</p>
    </div>
    """, unsafe_allow_html=True)

    v52_engine = StaticToAnimatedApplyEngine()
    default_concept = "보리와 쌀, 예의 바른 직장인 듀오 캐릭터, 짧은 답장 문구와 같이 움직이는 이모티콘"
    if st.session_state.get("multi_material_creator_report"):
        try:
            materials = st.session_state.multi_material_creator_report.get("input_summary", {}).get("materials", [])
            if materials:
                default_concept = ", ".join([m.get("material", "") for m in materials if isinstance(m, dict)]) + ", 정지형 기반 움직이는형 캐릭터"
        except Exception:
            pass

    c1, c2 = st.columns([1.3, 0.7])
    with c1:
        concept_text = st.text_area(
            "정지형 캐릭터 콘셉트",
            value=default_concept,
            height=90,
            key="v52_concept_text",
        )
        main_phrase = st.text_input("대표 문구", value="넵", key="v52_main_phrase")
    with c2:
        st.markdown("### 적용 흐름")
        st.markdown("""
        1. 정지형 identity 생성  
        2. 개선 제안 선택  
        3. 선택값 반영 재생성  
        4. 같은 외형으로 GIF 생성  
        5. 제작 흐름에 적용
        """)

    suggestions = v52_engine.get_suggestions(concept_text)
    suggestion_labels = {f"[{row['category']}] {row['label']}": row["id"] for row in suggestions}
    default_labels = [label for label, sid in suggestion_labels.items() if sid in {"bold_outline", "face_contrast", "animated_identity_lock", "text_motion_sync", "series_ready"}]
    st.markdown("### 선택하면 실제 재생성에 반영되는 제안")
    selected_labels = st.multiselect(
        "적용할 제안을 선택하세요",
        list(suggestion_labels.keys()),
        default=default_labels,
        key="v52_selected_suggestion_labels",
    )
    selected_ids = [suggestion_labels[label] for label in selected_labels]
    st.dataframe(pd.DataFrame(suggestions), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        run_v52 = st.button("선택 제안 반영해서 정지형 재생성 + 움직이는형 생성", type="primary", key="v52_run_regenerate")
    with col_b:
        apply_v52 = st.button("생성 결과를 현재 제작 흐름에 적용", key="v52_apply_to_flow")

    if run_v52:
        try:
            report_obj = v52_engine.build_report(
                project_name="v52_static_to_animated_apply",
                concept_text=concept_text,
                selected_suggestion_ids=selected_ids,
                phrase=main_phrase,
                out_dir=BASE_OUTPUT / "v52_static_to_animated_apply",
            )
            st.session_state.v52_static_to_animated_report = report_obj.to_dict()
            st.success("선택한 제안을 실제로 반영해 정지형 PNG와 움직이는형 GIF를 다시 생성했습니다.")
        except Exception as exc:
            st.error(f"v52 정지형→움직이는형 생성 실패: {exc}")

    report = st.session_state.get("v52_static_to_animated_report")
    if report:
        st.markdown("### 생성 결과")
        p1, p2 = st.columns(2)
        with p1:
            st.image(report.get("static_png_path"), caption="선택 제안 반영 정지형 PNG", width=260)
        with p2:
            st.image(report.get("animated_gif_path"), caption="정지형 identity 기반 움직이는형 GIF", width=260)

        m1, m2, m3 = st.columns(3)
        m1.metric("선택 제안", len(report.get("selected_suggestions", [])))
        m2.metric("표현 씨앗", len(report.get("expression_table", [])))
        m3.metric("모션 프레임", len(report.get("apply_payload", {}).get("motion_plan", [])))

        st.markdown("### 실제 반영 계획")
        st.dataframe(pd.DataFrame(report.get("regeneration_plan", [])), use_container_width=True)
        st.markdown("### 정지형/움직이는형 공통 identity lock")
        st.json(report.get("identity_lock", {}))
        st.markdown("### 24개 표현/모션 씨앗")
        st.dataframe(pd.DataFrame(report.get("expression_table", [])), use_container_width=True)

        if apply_v52:
            payload = report.get("apply_payload", {})
            st.session_state.prototype_results = payload.get("prototype_results", [])
            st.session_state.expressions = payload.get("expressions", [])
            st.session_state.last_gif = payload.get("last_gif")
            st.session_state.v52_static_to_animated_applied = payload
            st.success("v52 생성 결과를 현재 제작 흐름에 적용했습니다. 이제 15번 후보 갤러리, 16번 편집기, 17번 채팅창 미리보기, 18번 샘플 제작으로 이어갈 수 있습니다.")

        for label, path_key, mime in [
            ("v52 리포트 HTML 다운로드", "html_path", "text/html"),
            ("v52 리포트 JSON 다운로드", "json_path", "application/json"),
            ("v52 패키지 ZIP 다운로드", "zip_path", "application/zip"),
        ]:
            file_path = report.get(path_key)
            if file_path and Path(file_path).exists():
                with open(file_path, "rb") as f:
                    st.download_button(label, data=f, file_name=Path(file_path).name, mime=mime, key=f"v52_download_{path_key}")

    st.warning("제출 전에는 카카오 이모티콘 스튜디오의 최신 공식 규격과 저작권/상표권 위험을 반드시 다시 확인하세요.")



if selected_page_index == 49:
    st.subheader("API 키 안전보관/교체 · OpenAI 선택형 분석 준비")
    st.write("업로드된 키 파일은 OpenAI 프로젝트 API 키 형식으로 보입니다. 노출된 키는 실사용 전 교체하고, 프로그램에는 원문을 저장하지 않는 방식으로 연결합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v58 API Key Safety Mode</h2>
      <p>로컬/ZIP 분석을 우선하고, OpenAI는 선택형 고급 분석으로만 둡니다. 키 원문은 리포트·ZIP·CSV에 저장하지 않습니다.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        st.markdown("### 현재 결론")
        st.info("v56 설치/진단은 PASS, v57 좌측 메뉴 UI 개선은 반영, v58은 API 키 보안·교체·원문 미저장 흐름을 추가하는 단계입니다.")
        st.warning("이미 채팅/파일로 노출된 API 키는 안전하게 새 키로 교체한 뒤 사용하는 것을 권장합니다.")
        v58_notes = st.text_area(
            "분석 메모/키 관련 주의사항",
            value="OpenAI API 키는 선택형 고급 분석에만 사용한다. 기본값은 로컬 파일/ZIP 분석 우선, 30일 무료 수집 제한, 쿼터 카운터, 유료 호출 차단이다.",
            height=130,
            key="v58_notes",
        )
        v58_uploaded_files = st.file_uploader(
            "키 노출 위험 검사할 로컬 파일/ZIP 선택",
            type=["txt", "env", "md", "json", "csv", "zip", "bat", "ps1", "py"],
            accept_multiple_files=True,
            key="v58_uploaded_files",
            help="파일 내부에 API 키처럼 보이는 문자열이 있는지 마스킹 형태로만 점검합니다.",
        )
    with c2:
        st.markdown("### OpenAI API 키 검증")
        v58_openai_key = st.text_input("OpenAI API Key 선택 입력", type="password", key="v58_openai_key")
        v58_use_env = st.checkbox("환경변수 OPENAI_API_KEY 방식 사용", value=True, key="v58_use_env")
        v58_paid_allowed = st.checkbox("유료 호출 허용", value=False, key="v58_paid_allowed")
        v58_openai_limit = st.slider("OpenAI 분석 호출 제한/일", 0, 50, 0, key="v58_openai_limit")
        v58_budget = st.number_input("월 예산 한도 KRW", min_value=0, max_value=1000000, value=0, step=1000, key="v58_budget")
        if v58_paid_allowed or v58_openai_limit > 0 or v58_budget > 0:
            st.warning("OpenAI 호출 가능성이 생깁니다. 초기 테스트에서는 0원 모드를 권장합니다.")
        else:
            st.success("0원 안전모드: OpenAI 호출 기본 차단")

    if st.button("v58 API 키 안전검사/환경변수 템플릿 생성", type="primary", key="v58_run_key_guard"):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                saved_paths = []
                for uploaded in v58_uploaded_files or []:
                    safe_name = uploaded.name.replace("/", "_").replace("\\", "_")
                    target = tmp_dir / safe_name
                    target.write_bytes(uploaded.getbuffer())
                    saved_paths.append(target)
                config = ApiKeySafetyConfig(
                    project_name="kakao_emoticon_v58",
                    paid_calls_allowed=bool(v58_paid_allowed),
                    daily_openai_analysis_limit=int(v58_openai_limit),
                    monthly_budget_krw=int(v58_budget),
                    use_environment_variable=bool(v58_use_env),
                )
                report = OpenAIKeySafetyEngine().build_report(
                    BASE_OUTPUT / "v58_api_key_safety",
                    config=config,
                    openai_api_key=v58_openai_key,
                    uploaded_paths=saved_paths,
                    notes=v58_notes,
                )
            st.session_state.v58_api_key_safety_report = report
            st.success("v58 API 키 안전검사가 완료되었습니다. 키 원문은 저장하지 않았습니다.")
        except Exception as exc:
            st.error(f"v58 API 키 안전검사 실패: {exc}")

    report = st.session_state.get("v58_api_key_safety_report")
    if report:
        st.markdown("### v58 검사 결과")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("키 입력", "있음" if report.get("key_status", {}).get("provided") else "없음")
        k2.metric("키 종류", report.get("key_status", {}).get("type", "none"))
        k3.metric("유료 호출", "허용" if report.get("quota_policy", {}).get("paid_calls_allowed") else "차단")
        k4.metric("OpenAI 일일 제한", report.get("quota_policy", {}).get("daily_openai_analysis_limit", 0))

        st.markdown("#### 키 상태")
        st.json(report.get("key_status", {}))
        st.markdown("#### 안전 경고")
        for warning in report.get("safety_warnings", []):
            st.warning(warning)
        st.markdown("#### 파일/메모 키 노출 점검")
        file_hits = report.get("file_secret_hits_masked", [])
        note_hits = report.get("note_secret_hits_masked", [])
        if file_hits:
            st.dataframe(pd.DataFrame(file_hits), use_container_width=True)
        elif note_hits:
            st.write({"note_secret_hits_masked": note_hits})
        else:
            st.success("입력 메모/업로드 파일에서 키 형식 문자열은 감지되지 않았습니다.")

        st.markdown("#### 생성된 안전 템플릿")
        st.json(report.get("templates", {}))
        st.markdown("#### 다음 제작 흐름 적용")
        st.json(report.get("workflow_application", {}))
        if st.button("v58 안전정책을 현재 제작 흐름에 적용", key="v58_apply_policy"):
            st.session_state.v58_api_key_safety_applied = report.get("workflow_application", {})
            st.session_state.v51_api_guardrail_applied = report.get("quota_policy", {})
            st.success("v58 안전정책을 현재 제작 흐름에 적용했습니다. 기본은 로컬/ZIP 우선 + 유료 호출 차단입니다.")

        for label, path_key, mime in [
            ("v58 HTML 리포트 다운로드", "html_path", "text/html"),
            ("v58 JSON 리포트 다운로드", "json_path", "application/json"),
        ]:
            fp = Path(report.get(path_key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v58_download_{path_key}")

    st.caption("이 화면은 API 키를 실제 호출하지 않습니다. 키 형식 확인, 노출 위험 점검, 환경변수 템플릿 생성, 유료 호출 차단 정책만 처리합니다.")


if selected_page_index == 50:
    st.subheader("카카오형 GIF 미리보기/트렌드 개선 · 정지형→움직이는형 바로 확인")
    st.write("정지형 캐릭터가 생성된 뒤 움직이는 캐릭터가 실제로 화면에 보여야 한다는 문제를 해결하는 강화 탭입니다. 대표 GIF, 3개 모션 후보, 24개 구성 초안을 같이 만듭니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v61 Kakao Motion Preview Improver</h2>
      <p>정지형 identity를 고정하고, 카카오형 24개 구성 초안과 GIF 미리보기를 동시에 생성합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    v61_engine = KakaoMotionPreviewImprover()
    left, right = st.columns([1.15, 0.85])
    with left:
        v61_project_name = st.text_input("v61 프로젝트명", value="v61_kakao_motion_preview", key="v61_project_name")
        v61_concept = st.text_area(
            "원하는 이모티콘 방식/캐릭터 콘셉트",
            value="하찮고 공감되는 직장인 답장형 캐릭터. 정지형은 굵은 외곽선과 큰 표정, 움직이는형은 통통 튐·꾸벅·부들부들 모션이 바로 보여야 한다.",
            height=120,
            key="v61_concept",
        )
        v61_main_phrase = st.text_input("대표 문구", value="넵", key="v61_main_phrase")
        v61_style = st.selectbox(
            "스타일 프리셋",
            ["하찮은 공감형", "직장인 답장형", "미니 리액션형", "귀여운 단순형"],
            key="v61_style",
        )
        v61_notes = st.text_area(
            "인터넷/유튜브/온라인 참고 메모 또는 수집 요약",
            value="최근 카카오톡은 미니 리액션과 짧은 공감형 문구가 중요하다. 잘 그린 그림보다 채팅창에서 바로 이해되는 표정, 짧은 답장, 하찮은 일상 공감, 움직임 미리보기가 중요하다.",
            height=150,
            key="v61_online_notes",
        )
    with right:
        st.markdown("### 적용할 개선 제안")
        selected_suggestions = st.multiselect(
            "선택한 항목은 정지형/움직이는형 생성 규칙에 실제 반영됩니다.",
            v61_engine.STYLE_SUGGESTIONS,
            default=[
                "굵은 외곽선과 큰 실루엣",
                "눈·입 대비 강화",
                "정지형 identity를 움직이는형에도 고정",
                "3개 GIF 모션 샘플을 바로 미리보기",
                "24개 구성: 21 PNG + 3 GIF 계획 생성",
            ],
            key="v61_selected_suggestions",
        )
        st.markdown("### 기준")
        st.info("온라인 정보는 기존 인기 캐릭터 복제가 아니라 문구 길이, 포즈 리듬, 감정 분포, 가독성 같은 추상 신호만 사용합니다.")
        st.warning("카카오 공식 제출 기준은 변경될 수 있으므로 실제 제출 직전에는 스튜디오에서 다시 확인해야 합니다.")

    if st.button("v61 정지형 + 움직이는 GIF 미리보기 생성", type="primary", key="v61_run_motion_preview"):
        try:
            report_obj = v61_engine.build_report(
                project_name=v61_project_name,
                concept_text=v61_concept,
                style_preset=v61_style,
                selected_style_suggestions=selected_suggestions,
                online_notes=v61_notes,
                main_phrase=v61_main_phrase,
                out_dir=BASE_OUTPUT / "v61_kakao_motion_preview",
            )
            st.session_state.v61_kakao_motion_preview_report = report_obj.to_dict()
            st.success("정지형 PNG, 움직이는 대표 GIF, 3개 모션 후보, 24개 구성 초안을 생성했습니다.")
        except Exception as exc:
            st.error(f"v61 GIF 미리보기 생성 실패: {exc}")

    report = st.session_state.get("v61_kakao_motion_preview_report")
    if report:
        st.markdown("### 바로 보이는 생성 결과")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.image(report.get("static_preview_png"), caption="정지형 PNG", width=240)
        with c2:
            # st.image가 GIF 첫 프레임만 보이는 환경을 대비해 base64 HTML도 함께 제공합니다.
            gif_path = Path(report.get("animated_preview_gif", ""))
            if gif_path.exists():
                import base64
                encoded = base64.b64encode(gif_path.read_bytes()).decode("ascii")
                st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='240' style='border-radius:18px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                st.caption("대표 움직이는 GIF · 화면에서 바로 재생")
            else:
                st.warning("대표 GIF 파일을 찾지 못했습니다.")
        with c3:
            st.image(report.get("contact_sheet_path"), caption="미리보기 시트", width=300)

        st.markdown("### 3개 움직임 후보")
        variant_cols = st.columns(3)
        for idx, variant in enumerate(report.get("animated_variants", [])):
            with variant_cols[idx % 3]:
                p = Path(variant.get("path", ""))
                if p.exists():
                    import base64
                    encoded = base64.b64encode(p.read_bytes()).decode("ascii")
                    st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='210' style='border-radius:16px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                    st.caption(f"{variant.get('label')} · {variant.get('phrase')}")

        q1, q2, q3, q4, q5 = st.columns(5)
        qs = report.get("quality_scores", {})
        q1.metric("GIF 표시", qs.get("gif_preview_visible", 0))
        q2.metric("일관성", qs.get("identity_consistency", 0))
        q3.metric("가독성", qs.get("small_chat_readability", 0))
        q4.metric("트렌드 적합", qs.get("trend_fit", 0))
        q5.metric("24개 준비", qs.get("kakao_pack_readiness", 0))

        st.markdown("### 카카오형 24개 구성 초안")
        plan_json = Path(report.get("kakao_24_plan_json", ""))
        if plan_json.exists():
            st.dataframe(pd.DataFrame(json.loads(plan_json.read_text(encoding="utf-8"))), use_container_width=True)

        st.markdown("### 정지형/움직이는형 공통 identity lock")
        st.json(report.get("identity_lock", {}))
        st.markdown("### 온라인 참고 반영 기준")
        st.json(report.get("reference_basis", {}))

        if st.button("v61 생성 결과를 현재 제작 흐름에 적용", key="v61_apply_payload"):
            payload = report.get("apply_payload", {})
            st.session_state.prototype_results = payload.get("prototype_results", [])
            st.session_state.expressions = payload.get("expressions", [])
            st.session_state.last_gif = payload.get("last_gif")
            st.session_state.v61_kakao_motion_preview_applied = payload
            st.success("v61 결과를 현재 제작 흐름에 적용했습니다. 이제 15번 후보 갤러리, 17번 채팅창 미리보기, 49번 정지형 기반 움직이는형 흐름으로 이어갈 수 있습니다.")

        for label, path_key, mime in [
            ("v61 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v61 JSON 리포트 다운로드", "json_report_path", "application/json"),
            ("v61 24개 계획 CSV 다운로드", "kakao_24_plan_csv", "text/csv"),
            ("v61 패키지 ZIP 다운로드", "package_zip_path", "application/zip"),
        ]:
            fp = Path(report.get(path_key, ""))
            if fp.exists() and fp.is_file():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v61_download_{path_key}")

    st.caption("v61은 실제 외부 API 호출 없이도 로컬에서 정지형/움직이는형 미리보기 산출물을 생성합니다. 유튜브/인터넷 자료는 사용자가 입력한 메모나 향후 API 수집 요약을 추상 신호로만 반영합니다.")


if selected_page_index == 51:
    st.subheader("v62 Jinja2 템플릿 리포트/프롬프트 엔진")
    st.write("HTML 리포트, 프롬프트 팩, 모션 계획 CSV를 Jinja2 템플릿으로 분리해서 관리합니다. 프로그램 본체는 Python/Streamlit을 유지합니다.")

    v62_engine = JinjaTemplateEngine()
    with st.container():
        c1, c2 = st.columns([1.1, 0.9])
        with c1:
            v62_project_name = st.text_input("v62 프로젝트명", value="v62_jinja_template_project", key="v62_project_name")
            v62_concept = st.text_area(
                "콘셉트 설명",
                value="하찮고 공감되는 직장인 캐릭터. 짧은 답장형 문구와 단순한 통통 튐 모션을 사용한다.",
                height=120,
                key="v62_concept",
            )
            v62_style = st.selectbox(
                "스타일 프리셋",
                ["하찮은 공감형", "짧은 답장형", "미니 리액션형", "직장인 현실형", "사투리 생활형"],
                key="v62_style_preset",
            )
        with c2:
            st.markdown("#### 템플릿 출력물")
            st.markdown(
                """
                - HTML 리포트
                - 프롬프트 팩 Markdown
                - 모션 계획 CSV
                - manifest JSON
                - ZIP 패키지
                """
            )
            st.info("API 키처럼 보이는 문자열은 저장 전에 마스킹하고, ZIP 안에도 원문이 남지 않도록 검사합니다.")

    v62_suggestions = st.multiselect(
        "적용할 선택 제안",
        [
            "외곽선 굵게 + 채팅창 축소에서도 잘 보이게",
            "눈/입 대비 강화 + 감정이 한눈에 보이게",
            "정지형 외형/색상/얼굴 비율을 움직이는형에서도 고정",
            "캐릭터 동작과 문구 움직임 동기화",
            "24개 움직이는형 구성 중 3개 GIF 후보를 먼저 생성",
            "짧은 답장형 문구 우선",
        ],
        default=["정지형 외형/색상/얼굴 비율을 움직이는형에서도 고정", "캐릭터 동작과 문구 움직임 동기화"],
        key="v62_suggestions",
    )
    v62_trend_notes = st.text_area(
        "온라인/유튜브/메모 기반 추상 트렌드 신호",
        value="짧은 답장, 하찮은 공감, 미니 리액션, 단순한 실루엣, 과한 디테일보다 가독성",
        height=100,
        key="v62_trend_notes",
    )

    if st.button("v62 Jinja2 템플릿 리포트 생성", type="primary", key="v62_run_jinja_template"):
        try:
            trend_signals = [x.strip() for x in v62_trend_notes.replace("\n", ",").split(",") if x.strip()]
            report_obj = v62_engine.render_bundle(
                project_name=v62_project_name,
                concept_text=v62_concept,
                style_preset=v62_style,
                selected_suggestions=v62_suggestions,
                trend_signals=trend_signals,
                v61_report=st.session_state.get("v61_kakao_motion_preview_report"),
                out_dir=BASE_OUTPUT / "v62_jinja_template_engine",
            )
            st.session_state.v62_jinja_template_report = report_obj.to_dict()
            st.success("v62 Jinja2 템플릿 출력물을 생성했습니다.")
        except Exception as exc:
            st.error(f"v62 Jinja2 템플릿 생성 실패: {exc}")

    v62_report = st.session_state.get("v62_jinja_template_report")
    if v62_report:
        st.markdown("### 생성 결과")
        st.json(v62_report)
        if v62_report.get("warnings"):
            for warning in v62_report["warnings"]:
                st.warning(warning)
        if st.button("v62 템플릿 결과를 현재 제작 흐름에 적용", key="v62_apply_template_payload"):
            st.session_state.active_generation_profile = {
                "source": "v62_jinja_template_engine",
                "project_name": v62_report.get("project_name"),
                "html_report_path": v62_report.get("html_report_path"),
                "prompt_path": v62_report.get("prompt_path"),
                "motion_plan_path": v62_report.get("motion_plan_path"),
            }
            st.session_state.v62_jinja_template_applied = st.session_state.active_generation_profile
            st.success("v62 Jinja2 템플릿 결과를 현재 제작 흐름에 적용했습니다.")

        for label, path_key, mime in [
            ("v62 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v62 프롬프트 팩 다운로드", "prompt_path", "text/markdown"),
            ("v62 모션 계획 CSV 다운로드", "motion_plan_path", "text/csv"),
            ("v62 manifest JSON 다운로드", "manifest_path", "application/json"),
            ("v62 템플릿 ZIP 다운로드", "package_zip_path", "application/zip"),
        ]:
            value = v62_report.get(path_key)
            if value:
                fp = Path(value)
                if fp.exists():
                    st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v62_download_{path_key}")

    st.caption("v62는 화면 UI를 Jinja2로 바꾸는 것이 아니라, 리포트/프롬프트/모션 계획 같은 산출물 템플릿을 Jinja2로 분리하는 단계입니다.")


if selected_page_index == 52:
    st.subheader("v63 템플릿 엔진 관리/분리 구조")
    st.write("Jinja2를 주 템플릿 엔진으로 사용하고, Mako는 고급 텍스트/프롬프트 템플릿용 선택 보조 엔진으로 준비합니다. Django/Chameleon/Handlebars 계열은 비교·검토만 하고 현재 로컬 Streamlit 구조에 맞지 않는 의존성은 넣지 않습니다.")

    v63_engine = TemplateEngineManager()
    st.markdown("### 템플릿 엔진 선택 기준")
    st.dataframe(pd.DataFrame([x.to_dict() for x in v63_engine.engine_choices]), use_container_width=True)

    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        v63_project_name = st.text_input("v63 프로젝트명", value="v63_template_engine_project", key="v63_project_name")
        v63_concept = st.text_area(
            "콘셉트/제작 방향",
            value="정지형 캐릭터와 움직이는형 GIF 미리보기를 같은 identity lock으로 관리하고, 리포트/프롬프트/모션 계획은 템플릿 파일로 분리한다.",
            height=120,
            key="v63_concept",
        )
        v63_policy = st.selectbox(
            "템플릿 관리 정책",
            [
                "Jinja2 primary + Mako optional adapter",
                "Jinja2 only safe local mode",
                "Jinja2 report + Mako prompt optional",
            ],
            key="v63_policy",
        )
    with c2:
        st.markdown("#### v63 출력물")
        v63_outputs = st.multiselect(
            "분리 관리할 템플릿 산출물",
            ["HTML report", "Prompt template", "Style rulebook", "Motion template", "Engine matrix", "Manifest JSON", "ZIP bundle"],
            default=["HTML report", "Prompt template", "Style rulebook", "Motion template", "Engine matrix", "Manifest JSON", "ZIP bundle"],
            key="v63_outputs",
        )
        st.info("Mako는 requirements에 포함되지만, 현재 실행환경에 설치되지 않았으면 Jinja2로 안전하게 fallback합니다.")

    v63_trend_notes = st.text_area(
        "온라인/유튜브/카카오 참고자료 기반 추상 신호",
        value="짧은 답장, GIF 즉시 미리보기, 단순 실루엣, 하찮은 공감, 미니 리액션, 문구 가독성, 움직임 3종 우선",
        height=100,
        key="v63_trend_notes",
    )

    if st.button("v63 템플릿 관리 리포트 생성", type="primary", key="v63_run_template_manager"):
        try:
            trend_signals = [x.strip() for x in v63_trend_notes.replace("\n", ",").split(",") if x.strip()]
            result_obj = v63_engine.render_manager_bundle(
                project_name=v63_project_name,
                concept_text=v63_concept,
                intended_outputs=v63_outputs,
                selected_template_policy=v63_policy,
                trend_signals=trend_signals,
                out_dir=BASE_OUTPUT / "v63_template_engine_manager",
            )
            st.session_state.v63_template_engine_manager_report = result_obj.to_dict()
            st.success("v63 템플릿 엔진 관리 출력물을 생성했습니다.")
        except Exception as exc:
            st.error(f"v63 템플릿 관리 생성 실패: {exc}")

    v63_report = st.session_state.get("v63_template_engine_manager_report")
    if v63_report:
        st.markdown("### 생성 결과")
        st.json(v63_report)
        if v63_report.get("warnings"):
            for warning in v63_report["warnings"]:
                st.warning(warning)
        if st.button("v63 템플릿 관리 결과를 제작 흐름에 적용", key="v63_apply_template_manager"):
            st.session_state.active_generation_profile = {
                "source": "v63_template_engine_manager",
                "project_name": v63_report.get("project_name"),
                "primary_engine": v63_report.get("selected_primary_engine"),
                "html_report_path": v63_report.get("html_report_path"),
                "prompt_template_path": v63_report.get("prompt_template_path"),
                "motion_template_path": v63_report.get("motion_template_path"),
                "style_rulebook_path": v63_report.get("style_rulebook_path"),
            }
            st.session_state.v63_template_engine_manager_applied = st.session_state.active_generation_profile
            st.success("v63 템플릿 관리 결과를 현재 제작 흐름에 적용했습니다.")

        for label, path_key, mime in [
            ("v63 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v63 프롬프트 템플릿 다운로드", "prompt_template_path", "text/markdown"),
            ("v63 스타일 룰북 JSON 다운로드", "style_rulebook_path", "application/json"),
            ("v63 모션 템플릿 CSV 다운로드", "motion_template_path", "text/csv"),
            ("v63 엔진 매트릭스 다운로드", "engine_matrix_path", "application/json"),
            ("v63 manifest 다운로드", "manifest_path", "application/json"),
            ("v63 템플릿 관리 ZIP 다운로드", "package_zip_path", "application/zip"),
        ]:
            value = v63_report.get(path_key)
            if value:
                fp = Path(value)
                if fp.exists():
                    st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v63_download_{path_key}")

    st.caption("v63은 템플릿 엔진을 무조건 많이 넣는 단계가 아니라, 현재 프로그램에 맞는 Jinja2 중심 구조를 유지하면서 Mako 등 다른 템플릿 엔진은 필요할 때만 어댑터로 붙일 수 있게 분리한 단계입니다.")



if selected_page_index == 53:
    st.subheader("v67 실제 제작 품질 개선 · 영상 기준 정지형→움직이는형")
    st.write("업로드 영상에서 확인한 카카오 이모티콘샵/미니 리액션/작은 썸네일 기준을 반영해, 정지형 PNG와 움직이는 GIF를 같은 identity로 만들고 화면에서 바로 재생합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v67 Video Reference Quality Engine</h2>
      <p>코딩 프로그램 소개 메뉴가 아니라, 실제 이모티콘 제작 품질 개선에 개발 도구를 활용하는 단계입니다.</p>
    </div>
    """, unsafe_allow_html=True)

    v67_engine = VideoReferenceQualityEngine()
    left, right = st.columns([1.1, 0.9])
    with left:
        v67_project_name = st.text_input("v67 프로젝트명", value="v67_kakao_quality_direction", key="v67_project_name")
        v67_concept = st.text_area(
            "원하는 이모티콘 방향",
            value="영상에서 본 카카오 이모티콘처럼 작은 썸네일에서도 바로 보이는 하찮은 손그림 공감형 캐릭터. 정지형 생성 후 같은 캐릭터로 움직이는 GIF가 바로 재생되어야 한다.",
            height=140,
            key="v67_concept",
        )
        v67_phrase = st.text_input("대표 문구", value="넵", key="v67_phrase")
        v67_style = st.selectbox("스타일 프리셋", v67_engine.STYLE_PRESETS, key="v67_style")
        v67_video_notes = st.text_area(
            "영상 검토 메모",
            value="카카오 이모티콘샵 화면에서 작은 썸네일, 손그림 느낌, 짧은 문구, 비슷한 스타일 추천, 미니 이모티콘 리액션성이 중요해 보임. 후보만 보여주지 말고 GIF가 실제로 움직여야 함.",
            height=120,
            key="v67_video_notes",
        )
    with right:
        st.markdown("### 실제 반영할 개선 제안")
        v67_suggestions = st.multiselect(
            "선택한 제안은 정지형 재생성/GIF 모션/24개·32개 구성에 실제 반영됩니다.",
            v67_engine.QUALITY_SUGGESTIONS,
            default=[
                "작은 썸네일에서도 보이는 굵은 외곽선",
                "캐릭터보다 문구가 먼저 읽히는 짧은 말풍선",
                "정지형 identity를 움직이는형에서도 고정",
                "GIF가 화면에서 바로 움직이게 표시",
                "3개 이상 모션 후보를 동시에 비교",
                "하찮은 표정과 공감 상황을 우선",
                "기존 인기 캐릭터 복제 금지",
            ],
            key="v67_suggestions",
        )
        v67_online_notes = st.text_area(
            "온라인/유튜브/카카오 자료에서 추상 신호만 입력",
            value="미니 리액션, 짧은 답장형 문구, 하찮은 공감, 손그림 스타일, 다크모드 대비, 작은 썸네일 가독성",
            height=130,
            key="v67_online_notes",
        )
        st.info("특정 인기 캐릭터를 따라 만들지 않고, 문구 길이·실루엣·모션 리듬·가독성 같은 추상 기준만 반영합니다.")

    if st.button("v67 정지형 + 움직이는 GIF 실제 미리보기 생성", type="primary", key="v67_run_quality_direction"):
        try:
            result_obj = v67_engine.build_bundle(
                project_name=v67_project_name,
                concept_text=v67_concept,
                selected_style=v67_style,
                selected_suggestions=v67_suggestions,
                main_phrase=v67_phrase,
                video_notes=v67_video_notes,
                online_notes=v67_online_notes,
                out_dir=BASE_OUTPUT / "v67_video_reference_quality",
            )
            st.session_state.v67_quality_direction_report = result_obj.to_dict()
            st.success("v67 정지형 PNG, 움직이는 GIF 후보 6개, 24개/32개 구성 초안, Jinja2 HTML 리포트를 생성했습니다.")
        except Exception as exc:
            st.error(f"v67 품질 개선 생성 실패: {exc}")

    v67_report = st.session_state.get("v67_quality_direction_report")
    if v67_report:
        st.markdown("### 바로 보이는 결과")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.image(v67_report.get("static_png"), caption="정지형 PNG", width=240)
        with c2:
            gif_path = Path(v67_report.get("animated_preview_gif", ""))
            if gif_path.exists():
                import base64
                encoded = base64.b64encode(gif_path.read_bytes()).decode("ascii")
                st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='240' style='border-radius:18px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                st.caption("대표 움직이는 GIF · 실제 재생")
            else:
                st.warning("대표 GIF 파일을 찾지 못했습니다.")
        with c3:
            st.image(v67_report.get("contact_sheet_png"), caption="정지형/모션 비교 시트", width=310)

        st.markdown("### 모션 후보 6개")
        cols = st.columns(3)
        for idx, variant in enumerate(v67_report.get("motion_variants", [])):
            with cols[idx % 3]:
                p = Path(variant.get("path", ""))
                if p.exists():
                    import base64
                    encoded = base64.b64encode(p.read_bytes()).decode("ascii")
                    st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='210' style='border-radius:16px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                    st.caption(f"{variant.get('label')} · {variant.get('phrase')}")

        st.markdown("### 품질 점수")
        score_cols = st.columns(7)
        for idx, (k, v) in enumerate(v67_report.get("quality_scores", {}).items()):
            with score_cols[idx % 7]:
                st.metric(k, v)

        st.markdown("### 선택 제안이 실제 반영된 identity lock")
        st.json(v67_report.get("identity_lock", {}))

        st.markdown("### 영상/온라인 기준 반영")
        st.json(v67_report.get("video_reference_summary", {}))
        st.json(v67_report.get("online_reference_basis", {}))

        tab1, tab2 = st.tabs(["32개 정지형 구성", "24개 움직이는형 구성"])
        with tab1:
            fp = Path(v67_report.get("static_32_plan_json", ""))
            if fp.exists():
                st.dataframe(pd.DataFrame(json.loads(fp.read_text(encoding="utf-8"))), use_container_width=True)
        with tab2:
            fp = Path(v67_report.get("animated_24_plan_json", ""))
            if fp.exists():
                st.dataframe(pd.DataFrame(json.loads(fp.read_text(encoding="utf-8"))), use_container_width=True)

        if st.button("v67 생성 결과를 현재 제작 흐름에 적용", key="v67_apply_quality_direction"):
            payload = v67_report.get("apply_payload", {})
            st.session_state.prototype_results = payload.get("prototype_results", [])
            st.session_state.expressions = payload.get("expressions", [])
            st.session_state.last_gif = payload.get("last_gif")
            st.session_state.v67_quality_direction_applied = payload
            st.success("v67 결과를 현재 제작 흐름에 적용했습니다. 선택한 제안과 identity lock이 다음 제작 단계에 반영됩니다.")

        for label, path_key, mime in [
            ("v67 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v67 프롬프트 팩 다운로드", "prompt_pack_path", "text/markdown"),
            ("v67 정지형 32개 CSV 다운로드", "static_32_plan_csv", "text/csv"),
            ("v67 움직이는형 24개 CSV 다운로드", "animated_24_plan_csv", "text/csv"),
            ("v67 manifest 다운로드", "manifest_path", "application/json"),
            ("v67 품질 개선 ZIP 다운로드", "package_zip_path", "application/zip"),
        ]:
            fp = Path(v67_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v67_download_{path_key}")

    st.caption("v67은 코딩 프로그램을 소개 메뉴로 늘리지 않고, Python/Jinja2/Pillow/Streamlit/Inno Setup 등을 실제 제작 품질 개선에 활용하는 버전입니다.")




if selected_page_index == 54:
    st.subheader("v68 지속 진화형 품질개선 · 온라인 추상 트렌드 분석")
    st.write("v67의 정지형→움직이는 GIF 미리보기 구조 위에, 유튜브/카카오/온라인 자료를 원본 복제 없이 추상 신호로 누적하고 사용자 만족도까지 기록해 다음 생성 품질을 개선합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v68 Continuous Quality Evolution Engine</h2>
      <p>로컬 파일/ZIP 분석 우선 · 최근 30일 무료 수집 모드 · 유료 API 기본 차단 · 사용자 만족도 기반 품질 진화</p>
    </div>
    """, unsafe_allow_html=True)

    v68_engine = ContinuousQualityEvolutionEngine()
    left, right = st.columns([1.08, 0.92])
    with left:
        v68_project_name = st.text_input("v68 프로젝트명", value="v68_continuous_quality_evolution", key="v68_project_name")
        v68_concept = st.text_area(
            "원하는 이모티콘 방향",
            value="초기 v67 결과처럼 정지형과 움직이는형이 같은 캐릭터로 보이되, 앞으로 유튜브와 카카오 이모티콘 흐름을 추상 분석해서 계속 품질이 좋아지는 손그림 공감형 캐릭터.",
            height=125,
            key="v68_concept",
        )
        v68_phrase = st.text_input("대표 문구", value="넵", key="v68_phrase")
        v68_style = st.selectbox("스타일 프리셋", v68_engine.v67.STYLE_PRESETS, key="v68_style")
        v68_satisfaction = st.slider("이번 결과 만족도 기록", min_value=0, max_value=100, value=78, step=1, key="v68_satisfaction")
        v68_motion = st.selectbox("다음에 우선 반영할 모션", ["통통 튐", "꾸벅 인사", "부들부들", "손 흔들기", "말풍선 동기화", "작아졌다 커짐"], key="v68_motion")
    with right:
        st.markdown("### 실제 반영할 품질 제안")
        v68_suggestions = st.multiselect(
            "선택한 제안은 정지형 재생성/GIF 모션/품질 점수/다음 생성 메모리에 반영됩니다.",
            v68_engine.v67.QUALITY_SUGGESTIONS,
            default=[
                "작은 썸네일에서도 보이는 굵은 외곽선",
                "캐릭터보다 문구가 먼저 읽히는 짧은 말풍선",
                "정지형 identity를 움직이는형에서도 고정",
                "GIF가 화면에서 바로 움직이게 표시",
                "3개 이상 모션 후보를 동시에 비교",
                "미니 리액션처럼 즉시 이해되는 실루엣",
                "기존 인기 캐릭터 복제 금지",
            ],
            key="v68_suggestions",
        )
        st.info("온라인 자료는 캐릭터 외형·문구·애니메이션 원본을 저장하지 않고, 감정/문구 길이/모션 리듬/가독성 같은 추상 신호만 저장합니다.")

    st.markdown("### 온라인/로컬 자료 추상 신호 입력")
    c1, c2, c3 = st.columns(3)
    with c1:
        v68_youtube_notes = st.text_area(
            "YouTube/영상 분석 메모",
            value="최근 30일 무료 수집 기준. 이모티콘 제작 강의, 승인/반려 사례, 작가 인터뷰에서 짧은 문구, 공감형 콘셉트, 손그림 느낌, 모션 난이도, 댓글 반복 니즈만 추상 신호로 사용.",
            height=145,
            key="v68_youtube_notes",
        )
    with c2:
        v68_kakao_notes = st.text_area(
            "카카오/이모티콘 흐름 메모",
            value="미니 이모티콘 리액션, 짧은 답장형 문구, 작은 썸네일 가독성, 다크모드 대비, 굵은 외곽선, 말풍선 선명도, 24개/32개 세트 확장성.",
            height=145,
            key="v68_kakao_notes",
        )
    with c3:
        v68_local_notes = st.text_area(
            "로컬 파일/ZIP/사용자 자료 메모",
            value="사용자가 만족한 초기 v67 결과를 기반으로 정지형 identity 유지. 앞으로 만족한 결과/버린 결과/선택한 문구/선택한 모션을 누적 저장.",
            height=145,
            key="v68_local_notes",
        )
    v68_feedback = st.text_area(
        "사용자 피드백/다음 생성 선호",
        value="초기단계로 만족하지만 계속 진화하는 품질개선이 필요하다. 움직이는 GIF가 바로 보여야 하고, 유튜브/카카오/온라인 분석을 통해 문구와 모션 품질이 좋아져야 한다.",
        height=100,
        key="v68_feedback",
    )

    if st.button("v68 지속 진화형 품질개선 실행", type="primary", key="v68_run_evolution"):
        try:
            result_obj = v68_engine.build_bundle(
                project_name=v68_project_name,
                concept_text=v68_concept,
                selected_style=v68_style,
                selected_suggestions=v68_suggestions,
                main_phrase=v68_phrase,
                youtube_notes=v68_youtube_notes,
                kakao_notes=v68_kakao_notes,
                user_feedback=v68_feedback,
                local_uploaded_notes=v68_local_notes,
                satisfaction_score=int(v68_satisfaction),
                preferred_motion=v68_motion,
                out_dir=BASE_OUTPUT / "v68_continuous_quality_evolution",
            )
            st.session_state.v68_evolution_report = result_obj.to_dict()
            st.success("v68 지속 진화형 품질개선 리포트, SQLite 학습 DB, 추상 트렌드 신호, 정지형/GIF 결과를 생성했습니다.")
        except Exception as exc:
            st.error(f"v68 지속 진화형 품질개선 실패: {exc}")

    v68_report = st.session_state.get("v68_evolution_report")
    if v68_report:
        st.markdown("### 바로 보이는 결과")
        a, b, c = st.columns(3)
        with a:
            st.image(v68_report.get("static_png"), caption="정지형 PNG", width=240)
        with b:
            gif_path = Path(v68_report.get("animated_preview_gif", ""))
            if gif_path.exists():
                import base64
                encoded = base64.b64encode(gif_path.read_bytes()).decode("ascii")
                st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='240' style='border-radius:18px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                st.caption("대표 움직이는 GIF · 실제 재생")
        with c:
            st.metric("v68 패키지 SHA-256 앞 12자리", str(v68_report.get("checksum_sha256", ""))[:12])
            st.metric("만족도 반영", st.session_state.get("v68_satisfaction", 0))

        st.markdown("### 진화형 품질 점수")
        score_cols = st.columns(6)
        for idx, (k, v) in enumerate(v68_report.get("evolution_scores", {}).items()):
            with score_cols[idx % 6]:
                st.metric(k, v)

        st.markdown("### 모션 후보")
        cols = st.columns(3)
        for idx, variant in enumerate(v68_report.get("motion_variants", [])[:6]):
            with cols[idx % 3]:
                p = Path(variant.get("path", ""))
                if p.exists():
                    import base64
                    encoded = base64.b64encode(p.read_bytes()).decode("ascii")
                    st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='210' style='border-radius:16px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                    st.caption(f"{variant.get('label')} · {variant.get('phrase')}")

        st.markdown("### 저장된 추상 트렌드 신호")
        st.json(v68_report.get("abstract_trend_signals", {}))
        st.markdown("### 안전 원칙")
        for note in v68_report.get("safety_notes", []):
            st.write("- " + note)

        if st.button("v68 결과를 현재 제작 흐름에 적용", key="v68_apply_evolution"):
            st.session_state.prototype_results = [{"label": "v68 정지형", "path": v68_report.get("static_png"), "format": "png"}]
            st.session_state.last_gif = v68_report.get("animated_preview_gif")
            st.session_state.v68_evolution_applied = v68_report
            st.success("v68 결과를 현재 제작 흐름에 적용했습니다. 다음 생성에서 사용자 만족도와 추상 트렌드 신호를 우선 반영합니다.")

        for label, path_key, mime in [
            ("v68 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v68 추상 트렌드 JSON 다운로드", "trend_signal_json", "application/json"),
            ("v68 품질 점수 CSV 다운로드", "quality_score_csv", "text/csv"),
            ("v68 피드백 메모리 JSON 다운로드", "feedback_memory_json", "application/json"),
            ("v68 진화 계획 JSON 다운로드", "evolution_plan_json", "application/json"),
            ("v68 SQLite 학습 DB 다운로드", "quality_history_db", "application/octet-stream"),
            ("v68 다음 생성 프롬프트 다운로드", "prompt_template_path", "text/markdown"),
            ("v68 품질 진화 ZIP 다운로드", "package_zip_path", "application/zip"),
        ]:
            fp = Path(v68_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v68_download_{path_key}")

    st.caption("v68은 온라인 정보를 직접 베끼는 단계가 아니라, 로컬/유튜브/카카오 자료를 추상 신호로 바꿔 누적하고 사용자 만족도를 다음 생성 품질에 반영하는 단계입니다.")



if selected_page_index == 55:
    st.subheader("v69 실제 그림체/모션 품질 고도화")
    st.write("v68의 지속 학습 구조 위에 캐릭터 그림체, 표정 다양성, 움직임 자연스러움, 다크모드 대비를 더 강화합니다. 코딩 도구 소개 메뉴가 아니라 실제 제작 품질 개선에 Python/Jinja2/Pillow/SQLite를 사용합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v69 Actual Quality Upgrade Engine</h2>
      <p>손그림 질감 · 표정 다양성 · 자연스러운 GIF 모션 · 지속 학습 메모리</p>
    </div>
    """, unsafe_allow_html=True)

    v69_engine = V69ActualQualityUpgradeEngine()
    left, right = st.columns([1.05, 0.95])
    with left:
        v69_project_name = st.text_input("v69 프로젝트명", value="v69_actual_quality_upgrade", key="v69_project_name")
        v69_concept = st.text_area(
            "원하는 이모티콘 방향",
            value="v67 초기 결과는 만족하지만 앞으로 계속 진화해야 한다. 작은 썸네일에서도 보이는 손그림 공감형 캐릭터, 짧은 말풍선, 같은 캐릭터 기반 움직이는 GIF, 자연스러운 모션 후보를 원한다.",
            height=125,
            key="v69_concept",
        )
        v69_phrase = st.text_input("대표 문구", value="넵", key="v69_phrase")
        v69_style = st.selectbox("스타일 프리셋", v69_engine.STYLE_PRESETS, key="v69_style")
        v69_feedback = st.text_area(
            "사용자 만족/개선 피드백",
            value="초기단계지만 만족한다. 앞으로 유튜브와 카카오 이모티콘 등 온라인 추상 신호를 반영해 계속 품질이 좋아져야 한다. 캐릭터가 더 귀엽고 손그림 느낌이 나야 하며 움직임도 더 자연스러워야 한다.",
            height=130,
            key="v69_feedback",
        )
    with right:
        st.markdown("### 실제 반영할 품질 개선 규칙")
        v69_rules = st.multiselect(
            "선택한 규칙은 정지형 PNG, 움직이는 GIF, 품질 점수, 다음 생성 메모리에 실제 반영됩니다.",
            v69_engine.QUALITY_RULES,
            default=[
                "손그림 질감 외곽선 강화",
                "얼굴 크기 확대와 썸네일 가독성 강화",
                "문구 2~7자 답장형 우선",
                "정지형 identity를 모든 GIF에 고정",
                "모션 시작-중간-끝 리듬을 부드럽게",
                "표정 다양성 32개 세트 확장성 강화",
                "말풍선과 캐릭터 동작 동기화",
                "다크모드 대비 흰색 외곽선 유지",
                "기존 인기 캐릭터 복제 금지",
                "사용자가 만족한 스타일을 다음 생성 메모리에 저장",
            ],
            key="v69_rules",
        )
        v69_online_notes = st.text_area(
            "온라인/유튜브/카카오 자료 추상 신호 메모",
            value="최근 30일 무료 수집 모드. 원본 캐릭터를 저장하거나 복제하지 않고, 짧은 답장형 문구, 하찮은 공감, 손그림 느낌, 미니 리액션성, 작은 썸네일 가독성, 자연스러운 루프 모션만 추상 신호로 사용.",
            height=150,
            key="v69_online_notes",
        )
        st.info("특정 인기 캐릭터를 따라 만드는 요청은 차단하고, 품질 신호만 다음 생성에 반영합니다.")

    if st.button("v69 실제 품질 고도화 생성", type="primary", key="v69_run_quality_upgrade"):
        try:
            result_obj = v69_engine.build_bundle(
                project_name=v69_project_name,
                concept_text=v69_concept,
                selected_style=v69_style,
                selected_rules=v69_rules,
                main_phrase=v69_phrase,
                user_feedback=v69_feedback,
                online_abstract_notes=v69_online_notes,
                out_dir=BASE_OUTPUT / "v69_actual_quality_upgrade",
            )
            st.session_state.v69_quality_upgrade_report = result_obj.to_dict()
            st.success("v69 정지형/다크모드/GIF 모션 후보/품질 리포트/학습 DB/다음 생성 메모리를 생성했습니다.")
        except Exception as exc:
            st.error(f"v69 실제 품질 고도화 실패: {exc}")

    v69_report = st.session_state.get("v69_quality_upgrade_report")
    if v69_report:
        st.markdown("### 바로 보이는 결과")
        a, b, c = st.columns(3)
        with a:
            st.image(v69_report.get("static_png"), caption="정지형 PNG", width=240)
        with b:
            st.image(v69_report.get("darkmode_preview_png"), caption="다크모드 대비 미리보기", width=240)
        with c:
            gif_path = Path(v69_report.get("motion_preview_gif", ""))
            if gif_path.exists():
                import base64
                encoded = base64.b64encode(gif_path.read_bytes()).decode("ascii")
                st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='240' style='border-radius:18px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                st.caption("대표 움직이는 GIF · 실제 재생")

        st.markdown("### 모션 후보")
        cols = st.columns(4)
        for idx, variant in enumerate(v69_report.get("motion_variants", [])[:8]):
            with cols[idx % 4]:
                p = Path(variant.get("path", ""))
                if p.exists():
                    import base64
                    encoded = base64.b64encode(p.read_bytes()).decode("ascii")
                    st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='190' style='border-radius:16px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                    st.caption(f"{variant.get('label')} · {variant.get('phrase')}")

        st.markdown("### 품질 점수")
        score_cols = st.columns(8)
        for idx, (k, v) in enumerate(v69_report.get("quality_scores", {}).items()):
            with score_cols[idx % 8]:
                st.metric(k, v)

        st.markdown("### Identity Lock / 다음 생성 계획")
        x, y = st.columns(2)
        with x:
            st.json(v69_report.get("identity_lock", {}))
        with y:
            for item in v69_report.get("next_generation_plan", []):
                st.write("- " + item)

        if st.button("v69 결과를 현재 제작 흐름에 적용", key="v69_apply_quality_upgrade"):
            st.session_state.prototype_results = [{"label": "v69 정지형", "path": v69_report.get("static_png"), "format": "png"}]
            st.session_state.last_gif = v69_report.get("motion_preview_gif")
            st.session_state.v69_quality_upgrade_applied = v69_report
            st.success("v69 결과를 현재 제작 흐름에 적용했습니다. 다음 생성에서 품질 고도화 규칙과 style memory를 우선 반영합니다.")

        for label, path_key, mime in [
            ("v69 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v69 스타일 메모리 JSON 다운로드", "style_memory_json", "application/json"),
            ("v69 품질 지표 JSON 다운로드", "quality_metrics_json", "application/json"),
            ("v69 학습 DB 다운로드", "learning_db", "application/octet-stream"),
            ("v69 정지형 32개 CSV 다운로드", "static_32_plan_csv", "text/csv"),
            ("v69 움직이는형 24개 CSV 다운로드", "animated_24_plan_csv", "text/csv"),
            ("v69 다음 생성 프롬프트 다운로드", "prompt_pack_path", "text/markdown"),
            ("v69 품질 고도화 ZIP 다운로드", "package_zip_path", "application/zip"),
        ]:
            fp = Path(v69_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v69_download_{path_key}")

    st.caption("v69는 도구 소개 메뉴가 아니라 실제 이모티콘 생성 품질을 올리는 단계입니다. 온라인 자료는 원본 복제 없이 추상 품질 신호만 사용합니다.")



if selected_page_index == 56:
    st.subheader("v70 세트 완성도 강화/24·32 구성")
    st.write("v69가 캐릭터 하나의 정지형·움직이는형 품질을 올린 단계라면, v70은 32개 정지형과 24개 움직이는형 세트 전체의 감정·문구·포즈 다양성을 점검하고 제출 후보 패키지를 만듭니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v70 Set Completeness Engine</h2>
      <p>32개 정지형 · 24개 움직이는형 · 감정/문구/포즈 중복 점검 · 제출 후보 패키지</p>
    </div>
    """, unsafe_allow_html=True)

    v70_engine = V70SetCompletenessEngine()
    left, right = st.columns([1.05, 0.95])
    with left:
        v70_project_name = st.text_input("v70 프로젝트명", value="v70_set_completeness", key="v70_project_name")
        v70_concept = st.text_area(
            "세트로 완성하고 싶은 방향",
            value="작은 썸네일에서도 보이는 손그림 공감형 캐릭터. 정지형 32개와 움직이는형 24개가 서로 다른 감정, 문구, 포즈로 보이게 만들고 싶다.",
            height=120,
            key="v70_concept",
        )
        v70_phrase = st.text_input("대표 문구", value="넵", key="v70_phrase")
        v70_style = st.selectbox("스타일 프리셋", v70_engine.STYLE_PRESETS, key="v70_style")
        v70_feedback = st.text_area(
            "세트 품질 피드백",
            value="초기 캐릭터 방향은 만족한다. 이제 32개/24개 전체가 반복적으로 보이지 않고, 감정과 문구와 모션이 다양해야 한다.",
            height=120,
            key="v70_feedback",
        )
    with right:
        st.markdown("### 세트 완성도 규칙")
        v70_rules = st.multiselect(
            "선택한 규칙은 세트 구성, 품질 점수, 패키지 생성에 실제 반영됩니다.",
            v70_engine.SET_RULES,
            default=v70_engine.SET_RULES,
            key="v70_rules",
        )
        v70_online_notes = st.text_area(
            "온라인/유튜브/카카오 자료 추상 신호 메모",
            value="최근 30일 무료 수집 모드. 원본 캐릭터를 저장하거나 복제하지 않고, 짧은 답장형 문구, 하찮은 공감, 미니 리액션성, 썸네일 가독성, 세트 감정 분산만 추상 신호로 사용.",
            height=145,
            key="v70_online_notes",
        )
        st.info("v70은 기존 인기 캐릭터를 따라 만드는 기능이 아니라, 세트 전체가 덜 반복적으로 보이도록 구성 점수를 매기는 단계입니다.")

    if st.button("v70 세트 완성도 패키지 생성", type="primary", key="v70_run_set_completion"):
        try:
            # v70 SET_RULES는 세트 관리 규칙이고, 실제 캐릭터 렌더링에는 v69 QUALITY_RULES를 함께 사용합니다.
            selected_quality_rules = list(dict.fromkeys(v69_engine.QUALITY_RULES if 'v69_engine' in globals() else V69ActualQualityUpgradeEngine().QUALITY_RULES))
            result_obj = v70_engine.build_bundle(
                project_name=v70_project_name,
                concept_text=v70_concept,
                selected_style=v70_style,
                selected_rules=selected_quality_rules,
                main_phrase=v70_phrase,
                user_feedback=v70_feedback,
                online_abstract_notes=v70_online_notes + "\n" + "\n".join(v70_rules),
                out_dir=BASE_OUTPUT / "v70_set_completeness",
            )
            st.session_state.v70_set_completion_report = result_obj.to_dict()
            st.success("v70 정지형 32개/움직이는형 24개 세트 후보와 제출 후보 패키지를 생성했습니다.")
        except Exception as exc:
            st.error(f"v70 세트 완성도 생성 실패: {exc}")

    v70_report = st.session_state.get("v70_set_completion_report")
    if v70_report:
        st.markdown("### 세트 전체 미리보기")
        a, b, c = st.columns(3)
        with a:
            st.image(v70_report.get("static_gallery_png"), caption="정지형 32개 갤러리", use_container_width=True)
        with b:
            st.image(v70_report.get("animated_gallery_png"), caption="움직이는형 24개 갤러리", use_container_width=True)
        with c:
            gif_path = Path(v70_report.get("representative_gif", ""))
            if gif_path.exists():
                import base64
                encoded = base64.b64encode(gif_path.read_bytes()).decode("ascii")
                st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='240' style='border-radius:18px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                st.caption("대표 움직이는 GIF · 실제 재생")
            st.metric("제출 후보 ZIP SHA-256 앞 12자리", str(v70_report.get("checksum_sha256", ""))[:12])

        st.markdown("### 세트 품질 점수")
        score_cols = st.columns(8)
        for idx, (k, v) in enumerate(v70_report.get("set_scores", {}).items()):
            with score_cols[idx % 8]:
                st.metric(k, v)

        st.markdown("### 중복/안전 경고 및 개선 계획")
        x, y = st.columns(2)
        with x:
            warnings = v70_report.get("duplicate_warnings", [])
            if warnings:
                for item in warnings:
                    st.warning(item)
            else:
                st.success("현재 기준 중복 위험은 크게 발견되지 않았습니다.")
        with y:
            for item in v70_report.get("improvement_plan", []):
                st.write("- " + item)

        if st.button("v70 세트 결과를 현재 제작 흐름에 적용", key="v70_apply_set_completion"):
            st.session_state.prototype_results = [{"label": "v70 대표 정지형", "path": v70_report.get("representative_static_png"), "format": "png"}]
            st.session_state.last_gif = v70_report.get("representative_gif")
            st.session_state.v70_set_completion_applied = v70_report
            st.success("v70 세트 결과를 현재 제작 흐름에 적용했습니다. 다음 생성에서 세트 다양성 점수를 우선 반영합니다.")

        for label, path_key, mime in [
            ("v70 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v70 정지형 32개 CSV 다운로드", "static_32_plan_csv", "text/csv"),
            ("v70 움직이는형 24개 CSV 다운로드", "animated_24_plan_csv", "text/csv"),
            ("v70 세트 품질 매트릭스 JSON 다운로드", "set_quality_matrix_json", "application/json"),
            ("v70 정지형 32개 ZIP 다운로드", "static_32_package_zip", "application/zip"),
            ("v70 움직이는형 24개 ZIP 다운로드", "animated_24_package_zip", "application/zip"),
            ("v70 제출 후보 패키지 ZIP 다운로드", "candidate_submission_zip", "application/zip"),
            ("v70 학습 DB 다운로드", "learning_db", "application/octet-stream"),
            ("v70 다음 생성 프롬프트 다운로드", "prompt_pack_path", "text/markdown"),
        ]:
            fp = Path(v70_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v70_download_{path_key}")

    st.caption("v70은 캐릭터 하나의 품질보다 세트 전체 완성도를 보는 단계입니다. 온라인 자료는 복제하지 않고 추상 신호로만 사용합니다.")



if selected_page_index == 57:
    st.subheader("v71 제출 전 규격/용량/프레임 QC")
    st.write("v70에서 만든 32개 정지형/24개 움직이는형 세트 후보를 제출 전 기준으로 사전 검사합니다. 360×360, 용량, GIF 프레임 수, 투명 배경, 파일명 정규화, 중복 문구/감정, 공식 재확인 필요 항목을 한 번에 점검합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v71 Pre-submission QC Engine</h2>
      <p>수량 · 크기 · 용량 · 프레임 · 투명 배경 · 파일명 · 다크모드 · 공식 재확인 잠금</p>
    </div>
    """, unsafe_allow_html=True)

    v71_engine = V71PreSubmissionQCEngine()
    left, right = st.columns([1.05, 0.95])
    with left:
        v71_project_name = st.text_input("v71 프로젝트명", value="v71_pre_submission_qc", key="v71_project_name")
        v71_concept = st.text_area(
            "이모티콘 세트 방향",
            value="작은 썸네일에서도 읽히는 굵은 외곽선, 짧은 말풍선, 정지형 identity를 유지한 움직이는형, 세트 전체가 반복적으로 보이지 않는 손그림 공감형 캐릭터.",
            height=125,
            key="v71_concept",
        )
        v71_phrase = st.text_input("대표 문구", value="넵", key="v71_phrase")
        v71_style = st.selectbox("스타일 프리셋", v71_engine.STYLE_PRESETS, key="v71_style")
        v71_feedback = st.text_area(
            "사용자 피드백/수정 방향",
            value="초기 품질은 만족하지만 실제 제출 전 규격, 용량, 프레임, 투명 배경, 파일명, 다크모드 가독성을 더 철저하게 검사해야 한다.",
            height=110,
            key="v71_feedback",
        )
    with right:
        st.markdown("### 사전 QC 규칙")
        v71_rules = st.multiselect(
            "체크할 규칙",
            v71_engine.QC_RULES,
            default=v71_engine.QC_RULES,
            key="v71_rules",
        )
        v71_online_notes = st.text_area(
            "온라인/공식 기준 참고 메모",
            value="공식 기준은 제출 직전 다시 확인한다. 온라인 자료는 기존 캐릭터 복제가 아니라 문구 길이, 모션 리듬, 썸네일 가독성, 다크모드 대비 같은 추상 신호만 반영한다.",
            height=160,
            key="v71_online_notes",
        )
        st.warning("v71은 최종 승인을 보장하지 않습니다. FAIL 항목은 제출 후보 ZIP 잠금 사유로 보고, 공식 기준은 제출 직전 재확인해야 합니다.")

    if st.button("v71 제출 전 QC 패키지 생성", type="primary", key="v71_run_pre_submission_qc"):
        try:
            result_obj = v71_engine.build_bundle(
                project_name=v71_project_name,
                concept_text=v71_concept,
                selected_style=v71_style,
                selected_rules=v71_rules,
                main_phrase=v71_phrase,
                user_feedback=v71_feedback,
                online_abstract_notes=v71_online_notes + "\n" + "\n".join(v71_rules),
                out_dir=BASE_OUTPUT / "v71_pre_submission_qc",
            )
            st.session_state.v71_pre_submission_qc_report = result_obj.to_dict()
            st.success("v71 제출 전 QC 리포트, 규격 검사표, 파일명 정규화 계획, 체크리스트, QC 패키지를 생성했습니다.")
        except Exception as exc:
            st.error(f"v71 제출 전 QC 생성 실패: {exc}")

    v71_report = st.session_state.get("v71_pre_submission_qc_report")
    if v71_report:
        st.markdown("### QC 요약")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("전체 상태", v71_report.get("overall_status"))
        with c2:
            st.metric("PASS", v71_report.get("pass_count"))
        with c3:
            st.metric("WARN", v71_report.get("warn_count"))
        with c4:
            st.metric("FAIL", v71_report.get("fail_count"))

        a, b, c = st.columns(3)
        with a:
            st.image(v71_report.get("static_gallery_png"), caption="정지형 32개 갤러리", use_container_width=True)
        with b:
            st.image(v71_report.get("animated_gallery_png"), caption="움직이는형 24개 갤러리", use_container_width=True)
        with c:
            gif_path = Path(v71_report.get("representative_gif", ""))
            if gif_path.exists():
                import base64
                encoded = base64.b64encode(gif_path.read_bytes()).decode("ascii")
                st.markdown(f"<img src='data:image/gif;base64,{encoded}' width='240' style='border-radius:18px;border:1px solid #e5e7eb;background:white;'>", unsafe_allow_html=True)
                st.caption("대표 GIF · 실제 재생")

        st.markdown("### QC 점수")
        score_cols = st.columns(6)
        for idx, (k, v) in enumerate(v71_report.get("qc_scores", {}).items()):
            with score_cols[idx % 6]:
                st.metric(k, v)

        st.markdown("### 중요 경고/개선 계획")
        warns = v71_report.get("critical_warnings", [])
        if warns:
            for item in warns[:12]:
                st.write("- " + item)
        else:
            st.write("- 치명적인 FAIL 항목은 없습니다. 단, 제출 직전 공식 기준은 다시 확인해야 합니다.")
        with st.expander("개선 계획 보기"):
            for item in v71_report.get("improvement_plan", []):
                st.write("- " + item)

        if st.button("v71 QC 결과를 제출 전 잠금 흐름에 적용", key="v71_apply_qc"):
            st.session_state.v71_qc_applied = v71_report
            st.session_state.submission_lock_required = v71_report.get("fail_count", 0) > 0
            st.success("v71 QC 결과를 제출 전 잠금 흐름에 적용했습니다. FAIL이 있으면 최종 제출 패키지를 잠금 처리해야 합니다.")

        for label, path_key, mime in [
            ("v71 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v71 QC 매트릭스 CSV 다운로드", "qc_matrix_csv", "text/csv"),
            ("v71 QC 매트릭스 JSON 다운로드", "qc_matrix_json", "application/json"),
            ("v71 파일명 정규화 계획 CSV 다운로드", "normalized_export_plan_csv", "text/csv"),
            ("v71 체크리스트 JSON 다운로드", "checklist_json", "application/json"),
            ("v71 manifest JSON 다운로드", "pre_submission_manifest_json", "application/json"),
            ("v71 학습 DB 다운로드", "learning_db", "application/octet-stream"),
            ("v71 사전 QC 패키지 ZIP 다운로드", "pre_submission_qc_zip", "application/zip"),
        ]:
            fp = Path(v71_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v71_download_{path_key}")

    st.caption("v71은 로컬 사전 검사 단계입니다. 카카오 공식 기준은 변경될 수 있으므로 제출 직전 반드시 다시 확인해야 합니다.")


if selected_page_index == 58:
    st.subheader("v72 제출 패키지 자동보정/잠금")
    st.write("v71 QC 결과를 기반으로 원본을 보존한 채 final_export 폴더에 보정본을 만들고, FAIL/WARN 상태에 따라 최종 제출 후보 ZIP을 잠금 또는 해제합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v72 Submission Autofix & Lock Engine</h2>
      <p>QC 결과 기반 자동 보정 · 파일명 정규화 · 원본 보존 · 최종 ZIP 잠금/해제</p>
    </div>
    """, unsafe_allow_html=True)

    v72_engine = V72SubmissionAutofixLockEngine()
    left, right = st.columns([1.05, 0.95])
    with left:
        v72_project_name = st.text_input("v72 프로젝트명", value="v72_submission_autofix_lock", key="v72_project_name")
        v72_concept = st.text_area(
            "최종 제출 후보 방향",
            value="작은 썸네일에서도 보이는 손그림 공감형 이모티콘 세트를 제출 전 자동 보정하고, 문제가 있으면 최종 ZIP을 잠금 처리한다.",
            height=125,
            key="v72_concept",
        )
        v72_phrase = st.text_input("대표 문구", value="넵", key="v72_phrase")
        v72_style = st.selectbox("스타일 프리셋", v72_engine.STYLE_PRESETS, key="v72_style")
        v72_feedback = st.text_area(
            "사용자 피드백/보정 방향",
            value="검사는 끝났으니 이제 용량, 프레임, 파일명, 패키지 잠금/해제까지 자동으로 연결해 최종 제출 후보 ZIP을 만들고 싶다.",
            height=120,
            key="v72_feedback",
        )
    with right:
        st.markdown("### 자동보정/잠금 규칙")
        v72_rules = st.multiselect(
            "적용할 규칙",
            v72_engine.AUTOFIX_RULES,
            default=v72_engine.AUTOFIX_RULES,
            key="v72_rules",
        )
        v72_online_notes = st.text_area(
            "공식/온라인 기준 참고 메모",
            value="공식 기준은 제출 직전 다시 확인한다. 기존 캐릭터 복제 없이 추상 품질 신호만 반영하고, 원본 파일은 덮어쓰지 않는다.",
            height=160,
            key="v72_online_notes",
        )
        st.warning("v72는 제출 후보 패키지 자동보정/잠금 단계입니다. 최종 승인을 보장하지 않으며, 공식 기준 재확인은 계속 필요합니다.")

    if st.button("v72 제출 패키지 자동보정/잠금 실행", type="primary", key="v72_run_submission_autofix_lock"):
        try:
            result_obj = v72_engine.build_bundle(
                project_name=v72_project_name,
                concept_text=v72_concept,
                selected_style=v72_style,
                selected_rules=v72_rules,
                main_phrase=v72_phrase,
                user_feedback=v72_feedback,
                online_abstract_notes=v72_online_notes + "\n" + "\n".join(v72_rules),
                out_dir=BASE_OUTPUT / "v72_submission_autofix_lock",
            )
            st.session_state.v72_submission_autofix_lock_report = result_obj.to_dict()
            st.success("v72 자동보정 로그, 최종 manifest, 잠금 manifest, 제출 후보 ZIP/검토 ZIP, HTML 리포트를 생성했습니다.")
        except Exception as exc:
            st.error(f"v72 자동보정/잠금 생성 실패: {exc}")

    v72_report = st.session_state.get("v72_submission_autofix_lock_report")
    if v72_report:
        st.markdown("### 최종 패키지 상태")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("상태", v72_report.get("package_status"))
        with c2:
            st.metric("정지형", v72_report.get("exported_static_count"))
        with c3:
            st.metric("움직이는형", v72_report.get("exported_animated_count"))
        with c4:
            st.metric("GIF", v72_report.get("exported_gif_count"))

        st.markdown("### 최종 점수")
        score_cols = st.columns(6)
        for idx, (k, v) in enumerate(v72_report.get("final_scores", {}).items()):
            with score_cols[idx % 6]:
                st.metric(k, v)

        st.markdown("### 잠금 사유 / 자동보정 작업")
        x, y = st.columns(2)
        with x:
            reasons = v72_report.get("lock_reasons", [])
            if reasons:
                for item in reasons:
                    st.warning(item)
            else:
                st.success("현재 로컬 샘플 기준 최종 제출 후보 ZIP 잠금 사유는 없습니다. 단, 공식 기준은 제출 직전 재확인해야 합니다.")
        with y:
            for item in v72_report.get("autofix_actions", []):
                st.write("- " + item)

        if st.button("v72 결과를 최종 제출 후보 흐름에 적용", key="v72_apply_submission_autofix_lock"):
            st.session_state.submission_lock_required = bool(v72_report.get("submission_lock_required"))
            st.session_state.v72_submission_autofix_lock_applied = v72_report
            st.success("v72 결과를 최종 제출 후보 흐름에 적용했습니다. 잠금 상태는 manifest 기준으로 유지됩니다.")

        for label, path_key, mime in [
            ("v72 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v72 자동보정 로그 CSV 다운로드", "autofix_log_csv", "text/csv"),
            ("v72 자동보정 로그 JSON 다운로드", "autofix_log_json", "application/json"),
            ("v72 최종 manifest JSON 다운로드", "final_manifest_json", "application/json"),
            ("v72 잠금 manifest JSON 다운로드", "lock_manifest_json", "application/json"),
            ("v72 정지형 최종 ZIP 다운로드", "static_export_zip", "application/zip"),
            ("v72 움직이는형 최종 ZIP 다운로드", "animated_export_zip", "application/zip"),
            ("v72 최종 제출 후보 ZIP 다운로드", "final_submission_zip", "application/zip"),
            ("v72 잠금 검토 ZIP 다운로드", "locked_review_zip", "application/zip"),
            ("v72 학습 DB 다운로드", "learning_db", "application/octet-stream"),
        ]:
            fp = Path(v72_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v72_download_{path_key}")

    st.caption("v72는 원본을 보존하면서 제출 후보 파일명을 정리하고, 실패 항목이 있으면 최종 제출 ZIP을 잠금 처리합니다.")


if selected_page_index == 59:
    st.subheader("v73 제출 전 최종 사용자 확인/수동 승인")
    st.write("v72 자동보정 결과를 바로 제출용으로 내보내지 않고, 사용자가 32개/24개/GIF/문구/저작권/공식 기준을 직접 확인해야 최종 승인 후보 ZIP을 생성합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v73 Final User Approval Workflow</h2>
      <p>자동 제출 금지 · 사용자 수동 승인 · 공식 기준 재확인 · 최종 후보 ZIP 잠금/해제</p>
    </div>
    """, unsafe_allow_html=True)

    v73_engine = V73FinalUserApprovalWorkflow()
    left, right = st.columns([1.02, 0.98])
    with left:
        v73_project_name = st.text_input("v73 프로젝트명", value="v73_final_user_approval", key="v73_project_name")
        v73_concept = st.text_area(
            "최종 확인할 이모티콘 방향",
            value="작은 썸네일에서도 보이는 손그림 공감형 캐릭터 세트를 사용자 최종 확인 후 제출 후보 ZIP으로 잠금 해제한다.",
            height=125,
            key="v73_concept",
        )
        v73_phrase = st.text_input("대표 문구", value="넵", key="v73_phrase")
        v73_style = st.selectbox("스타일 프리셋", v73_engine.STYLE_PRESETS, key="v73_style")
        v73_feedback = st.text_area(
            "사용자 확인 메모",
            value="최종 제출 전 32개/24개/GIF/문구/저작권/공식 기준을 직접 보고 승인해야 한다.",
            height=120,
            key="v73_feedback",
        )
    with right:
        st.markdown("### 필수 확인 체크리스트")
        confirmations = {}
        for key, label in v73_engine.REQUIRED_CONFIRMATIONS:
            confirmations[key] = st.checkbox(label, value=(key != "official_spec_rechecked" and key != "user_final_approval"), key=f"v73_req_{key}")
        st.markdown("### 선택 확인")
        for key, label in v73_engine.OPTIONAL_CONFIRMATIONS:
            confirmations[key] = st.checkbox(label, value=False, key=f"v73_opt_{key}")
        v73_online_notes = st.text_area(
            "공식/온라인 기준 참고 메모",
            value="제출 직전 공식 기준을 다시 확인한다. 온라인 자료는 추상 품질 신호로만 사용하고 기존 캐릭터 복제는 금지한다.",
            height=120,
            key="v73_online_notes",
        )
        st.warning("최종 승인 체크가 모두 완료되지 않으면 승인 후보 ZIP 대신 수동 검토 ZIP 상태로 유지됩니다.")

    if st.button("v73 최종 사용자 확인/수동 승인 실행", type="primary", key="v73_run_final_user_approval"):
        try:
            result_obj = v73_engine.build_bundle(
                project_name=v73_project_name,
                concept_text=v73_concept,
                selected_style=v73_style,
                main_phrase=v73_phrase,
                user_feedback=v73_feedback,
                online_abstract_notes=v73_online_notes,
                user_confirmations=confirmations,
                out_dir=BASE_OUTPUT / "v73_final_user_approval",
            )
            st.session_state.v73_final_user_approval_report = result_obj.to_dict()
            st.success("v73 사용자 승인 체크리스트, 승인 manifest, HTML 리포트, 승인 후보 ZIP/수동 검토 ZIP을 생성했습니다.")
        except Exception as exc:
            st.error(f"v73 최종 사용자 승인 워크플로우 실패: {exc}")

    v73_report = st.session_state.get("v73_final_user_approval_report")
    if v73_report:
        st.markdown("### 승인 상태")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("상태", v73_report.get("approval_status"))
        c2.metric("승인 점수", v73_report.get("approval_score"))
        c3.metric("필수 확인", f"{v73_report.get('required_checked_count')}/{v73_report.get('required_total_count')}")
        c4.metric("선택 확인", v73_report.get("optional_checked_count"))

        reasons = v73_report.get("blocking_reasons", [])
        if reasons:
            st.markdown("### 남은 차단 사유")
            for item in reasons:
                st.warning(item)
        else:
            st.success("현재 사용자 확인 기준으로 최종 승인 후보 ZIP 생성이 가능합니다. 단, 실제 제출 전 공식 기준은 다시 확인해야 합니다.")

        if st.button("v73 결과를 최종 승인 흐름에 적용", key="v73_apply_final_user_approval"):
            st.session_state.final_user_approved_submission = bool(v73_report.get("final_submission_allowed"))
            st.session_state.v73_final_user_approval_applied = v73_report
            st.success("v73 결과를 최종 승인 흐름에 적용했습니다.")

        for label, path_key, mime in [
            ("v73 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v73 사용자 확인 체크리스트 CSV 다운로드", "approval_checklist_csv", "text/csv"),
            ("v73 승인 manifest JSON 다운로드", "approval_manifest_json", "application/json"),
            ("v73 사용자 승인 최종 후보 ZIP 다운로드", "final_approved_zip", "application/zip"),
            ("v73 수동 검토 ZIP 다운로드", "manual_review_zip", "application/zip"),
            ("v73 학습 DB 다운로드", "learning_db", "application/octet-stream"),
        ]:
            fp = Path(v73_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v73_download_{path_key}")

    st.caption("v73은 자동 제출이 아니라 사용자 최종 확인/수동 승인 단계입니다. 공식 기준 재확인과 저작권/유사성 확인은 사용자가 직접 완료해야 합니다.")


if selected_page_index == 60:
    st.subheader("v74 반려 대비/재제출 개선 루프")
    st.write("카카오 심사 반려 사유나 사용자 검토 메모를 입력하면, 원본을 복제하지 않고 추상 개선 신호로 분류해 다음 재생성·재제출 액션 플랜을 만듭니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v74 Rejection → Resubmission Loop</h2>
      <p>반려 사유 분류 · 수정 액션 · 32/24 재구성 계획 · 재제출 잠금 체크리스트</p>
    </div>
    """, unsafe_allow_html=True)

    v74_engine = V74RejectionResubmissionLoop()
    left, right = st.columns([1.02, 0.98])
    with left:
        v74_project_name = st.text_input("v74 프로젝트명", value="v74_rejection_resubmission", key="v74_project_name")
        v74_concept = st.text_area(
            "재제출할 이모티콘 방향",
            value="작은 썸네일에서도 보이는 손그림 공감형 캐릭터 세트를 반려 사유에 맞춰 수정하고 재제출 준비한다.",
            height=125,
            key="v74_concept",
        )
        v74_phrase = st.text_input("대표 문구", value="넵", key="v74_phrase")
        v74_style = st.selectbox("스타일 프리셋", v74_engine.STYLE_PRESETS, key="v74_style")
        v74_feedback = st.text_area(
            "사용자 검토/만족도 메모",
            value="초기 방향은 만족하지만, 캐릭터 개성·문구·모션·세트 다양성은 계속 진화해야 한다.",
            height=120,
            key="v74_feedback",
        )
    with right:
        v74_rejection_text = st.text_area(
            "반려 사유/재제출 개선 메모",
            value=v74_engine.DEFAULT_REJECTION_TEXT,
            height=220,
            key="v74_rejection_text",
        )
        v74_upload = st.file_uploader(
            "반려 사유 TXT/CSV 업로드 선택",
            type=["txt", "csv"],
            accept_multiple_files=True,
            key="v74_rejection_upload",
        )
        uploaded_notes = []
        if v74_upload:
            for f in v74_upload:
                try:
                    uploaded_notes.append(f.read().decode("utf-8", errors="ignore"))
                except Exception:
                    uploaded_notes.append("")
        v74_online_notes = st.text_area(
            "온라인/공식 기준 추상 신호 메모",
            value="온라인 자료는 캐릭터/문구/애니메이션을 복제하지 않고, 문구 길이·감정 유형·모션 리듬·가독성 같은 추상 신호만 반영한다.",
            height=120,
            key="v74_online_notes",
        )
        st.warning("v74는 반려 대비 개선 루프입니다. 재제출 승인이나 수익을 보장하지 않으며, HIGH 항목은 재생성 후 v71/v72/v73 재검사를 요구합니다.")

    if st.button("v74 반려 대비/재제출 개선 루프 실행", type="primary", key="v74_run_rejection_resubmission"):
        try:
            combined_rejection_text = v74_rejection_text + "\n" + "\n".join(uploaded_notes)
            result_obj = v74_engine.build_bundle(
                project_name=v74_project_name,
                concept_text=v74_concept,
                selected_style=v74_style,
                main_phrase=v74_phrase,
                user_feedback=v74_feedback,
                online_abstract_notes=v74_online_notes,
                rejection_text=combined_rejection_text,
                out_dir=BASE_OUTPUT / "v74_rejection_resubmission",
            )
            st.session_state.v74_rejection_resubmission_report = result_obj.to_dict()
            st.success("v74 반려 사유 분석, 수정 액션 플랜, 32/24 재구성 계획, 재제출 패키지, HTML 리포트를 생성했습니다.")
        except Exception as exc:
            st.error(f"v74 반려 대비/재제출 루프 실패: {exc}")

    v74_report = st.session_state.get("v74_rejection_resubmission_report")
    if v74_report:
        st.markdown("### 재제출 개선 상태")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("상태", v74_report.get("rejection_status"))
        c2.metric("개선 준비 점수", v74_report.get("overall_revision_score"))
        c3.metric("분석 항목", v74_report.get("rejection_count"))
        c4.metric("HIGH", v74_report.get("high_priority_count"))

        categories = v74_report.get("detected_categories", [])
        if categories:
            st.markdown("### 감지된 개선 카테고리")
            st.write(", ".join(categories))

        if v74_report.get("revision_lock_required"):
            st.warning("유사성/규격/원본성 등 HIGH 항목이 포함되어 재제출 전 재검사 잠금이 필요합니다.")
        else:
            st.success("현재 입력 기준 고위험 잠금 항목은 없지만, 재생성 후 v71/v72/v73 재검사가 필요합니다.")

        if st.button("v74 결과를 다음 재생성/재제출 흐름에 적용", key="v74_apply_rejection_resubmission"):
            st.session_state.v74_rejection_resubmission_applied = v74_report
            st.session_state.resubmission_revision_lock_required = bool(v74_report.get("revision_lock_required"))
            st.success("v74 결과를 다음 재생성/재제출 흐름에 적용했습니다.")

        for label, path_key, mime in [
            ("v74 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v74 반려 입력 CSV 다운로드", "rejection_input_csv", "text/csv"),
            ("v74 수정 액션 플랜 CSV 다운로드", "action_plan_csv", "text/csv"),
            ("v74 수정 액션 플랜 JSON 다운로드", "action_plan_json", "application/json"),
            ("v74 정지형 32개 재구성 CSV 다운로드", "revised_static_32_plan_csv", "text/csv"),
            ("v74 움직이는형 24개 재구성 CSV 다운로드", "revised_animated_24_plan_csv", "text/csv"),
            ("v74 재제출 프롬프트 팩 다운로드", "prompt_pack_md", "text/markdown"),
            ("v74 추상 신호 메모리 JSON 다운로드", "trend_signal_memory_json", "application/json"),
            ("v74 재제출 체크리스트 CSV 다운로드", "resubmission_checklist_csv", "text/csv"),
            ("v74 manifest JSON 다운로드", "manifest_json", "application/json"),
            ("v74 재제출 작업 ZIP 다운로드", "resubmission_work_package_zip", "application/zip"),
            ("v74 잠금 검토 ZIP 다운로드", "locked_review_zip", "application/zip"),
            ("v74 학습 DB 다운로드", "learning_db", "application/octet-stream"),
        ]:
            fp = Path(v74_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v74_download_{path_key}")

    st.caption("v74는 반려 사유를 다음 재생성·재검사·재승인 루프로 연결합니다. 자동 제출은 하지 않습니다.")

if selected_page_index == 61:
    st.subheader("v75 캡처 이미지 반려 사유 입력/OCR 보조")
    st.write("카카오 심사 결과 캡처 이미지를 원본 보존하고, 선택형 OCR/수동 교정 텍스트를 v74 반려 대비 개선 루프로 연결합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v75 Capture → Rejection Text → Resubmission Loop</h2>
      <p>캡처 원본 보존 · OCR 보조 · 수동 교정 · v74 재제출 액션 플랜 자동 연결</p>
    </div>
    """, unsafe_allow_html=True)

    v75_engine = V75CaptureRejectionIngestionEngine()
    left, right = st.columns([1.02, 0.98])
    with left:
        v75_project_name = st.text_input("v75 프로젝트명", value="v75_capture_rejection", key="v75_project_name")
        v75_concept = st.text_area(
            "재제출할 이모티콘 방향",
            value="작은 썸네일에서도 보이는 손그림 공감형 캐릭터 세트를 캡처 반려 사유 기반으로 개선한다.",
            height=125,
            key="v75_concept",
        )
        v75_phrase = st.text_input("대표 문구", value="넵", key="v75_phrase")
        v75_style = st.selectbox("스타일 프리셋", v75_engine.v74.STYLE_PRESETS, key="v75_style")
        v75_feedback = st.text_area(
            "사용자 검토/만족도 메모",
            value="초기 방향은 만족하지만, 캡처된 반려 사유를 바탕으로 캐릭터성·문구·모션·세트 다양성을 개선한다.",
            height=120,
            key="v75_feedback",
        )
    with right:
        v75_capture_upload = st.file_uploader(
            "카카오 심사 결과/반려 사유 캡처 이미지 업로드",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            accept_multiple_files=True,
            key="v75_capture_upload",
        )
        v75_enable_ocr = st.checkbox("선택형 OCR 보조 시도", value=False, key="v75_enable_ocr")
        v75_manual_text = st.text_area(
            "수동 교정 반려 사유 텍스트",
            value=v75_engine.SAMPLE_REJECTION_TEXT,
            height=190,
            key="v75_manual_text",
        )
        v75_online_notes = st.text_area(
            "온라인/공식 기준 추상 신호 메모",
            value="온라인 자료는 캐릭터/문구/애니메이션을 복제하지 않고, 문구 길이·감정 유형·모션 리듬·가독성 같은 추상 신호만 반영한다.",
            height=110,
            key="v75_online_notes",
        )
        st.warning("OCR은 보조 기능입니다. 한글 캡처는 반드시 수동 교정 텍스트로 확인한 뒤 v74 개선 루프로 넘기세요.")

    if st.button("v75 캡처 반려 사유 입력/OCR 보조 실행", type="primary", key="v75_run_capture_rejection"):
        try:
            image_inputs = []
            if v75_capture_upload:
                for f in v75_capture_upload:
                    image_inputs.append((f.name, f.read()))
            result_obj = v75_engine.build_bundle(
                project_name=v75_project_name,
                concept_text=v75_concept,
                selected_style=v75_style,
                main_phrase=v75_phrase,
                user_feedback=v75_feedback,
                online_abstract_notes=v75_online_notes,
                manual_rejection_text=v75_manual_text,
                image_inputs=image_inputs,
                out_dir=BASE_OUTPUT / "v75_capture_rejection_ingestion",
                enable_ocr=v75_enable_ocr,
            )
            st.session_state.v75_capture_rejection_report = result_obj.to_dict()
            st.success("v75 캡처 보존, OCR 후보/수동 교정 텍스트, v74 개선 루프 연결, HTML 리포트, 작업 ZIP을 생성했습니다.")
        except Exception as exc:
            st.error(f"v75 캡처 반려 사유 입력 실패: {exc}")

    v75_report = st.session_state.get("v75_capture_rejection_report")
    if v75_report:
        st.markdown("### 캡처 입력 상태")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("상태", v75_report.get("capture_status"))
        c2.metric("캡처 수", v75_report.get("image_count"))
        c3.metric("OCR 가능", "YES" if v75_report.get("ocr_available") else "NO")
        c4.metric("추출 텍스트", v75_report.get("extracted_text_count"))

        contact_sheet = Path(v75_report.get("capture_contact_sheet_png", ""))
        if contact_sheet.exists():
            st.image(str(contact_sheet), caption="v75 캡처 미리보기 시트", use_container_width=True)

        st.markdown("### v74로 전달된 반려 사유 텍스트")
        st.text_area("combined_rejection_text", value=v75_report.get("combined_rejection_text", ""), height=180, disabled=True)

        if st.button("v75 결과를 v74 재제출 개선 흐름에 적용", key="v75_apply_capture_rejection"):
            st.session_state.v75_capture_rejection_applied = v75_report
            st.session_state.v74_rejection_text_from_capture = v75_report.get("combined_rejection_text", "")
            st.success("v75 캡처 입력 결과를 v74 재제출 개선 흐름에 적용했습니다.")

        for label, path_key, mime in [
            ("v75 HTML 리포트 다운로드", "v75_html_report_path", "text/html"),
            ("v75 캡처 분석 CSV 다운로드", "capture_analysis_csv", "text/csv"),
            ("v75 OCR 후보 CSV 다운로드", "ocr_candidates_csv", "text/csv"),
            ("v75 manifest JSON 다운로드", "capture_manifest_json", "application/json"),
            ("v75 캡처 이미지 보관 ZIP 다운로드", "image_archive_zip", "application/zip"),
            ("v75 → v74 작업 ZIP 다운로드", "v75_work_package_zip", "application/zip"),
            ("v75 학습 DB 다운로드", "learning_db", "application/octet-stream"),
            ("연결된 v74 HTML 리포트 다운로드", "v74_html_report_path", "text/html"),
            ("연결된 v74 액션 플랜 CSV 다운로드", "v74_action_plan_csv", "text/csv"),
            ("연결된 v74 재제출 작업 ZIP 다운로드", "v74_resubmission_work_package_zip", "application/zip"),
        ]:
            fp = Path(v75_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v75_download_{path_key}")

    st.caption("v75는 캡처를 반려 개선 루프로 연결하는 보조 단계입니다. OCR 결과는 보조 후보이며 수동 교정 텍스트를 기준으로 사용하세요.")



if selected_page_index == 62:
    st.subheader("v76 캡처 반려 사유 → 실제 재생성 자동 연결")
    st.write("v75 캡처/OCR/수동 교정 결과와 v74 액션 플랜을 실제 정지형 32개·움직이는형 24개 재생성으로 연결합니다.")

    st.markdown("""
    <div class='v49-hero'>
      <h2>v76 Rejection/Capture → Actual Regeneration</h2>
      <p>캡처 보존 · v74 액션 플랜 · 선택 제안 실제 반영 · 정지형 32개/움직이는형 24개 재생성 · 다음 QC 루프 연결</p>
    </div>
    """, unsafe_allow_html=True)

    v76_engine = V76RejectionToRegenerationEngine()
    left, right = st.columns([1.02, 0.98])
    with left:
        v76_project_name = st.text_input("v76 프로젝트명", value="v76_rejection_to_regeneration", key="v76_project_name")
        v76_concept = st.text_area(
            "재생성할 이모티콘 방향",
            value="작은 썸네일에서도 보이는 손그림 공감형 캐릭터 세트를 캡처/반려 사유 기반으로 실제 재생성한다.",
            height=125,
            key="v76_concept",
        )
        v76_phrase = st.text_input("대표 문구", value="넵", key="v76_phrase")
        v76_style = st.selectbox("스타일 프리셋", v76_engine.v70.STYLE_PRESETS, key="v76_style")
        v76_feedback = st.text_area(
            "사용자 검토/만족도 메모",
            value="초기 방향은 만족하지만, 문구 가독성·표정 다양성·모션 차이를 실제 결과물에 반영해서 다시 생성한다.",
            height=120,
            key="v76_feedback",
        )
    with right:
        v76_capture_upload = st.file_uploader(
            "카카오 심사 결과/반려 사유 캡처 이미지 업로드",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            accept_multiple_files=True,
            key="v76_capture_upload",
        )
        v76_enable_ocr = st.checkbox("선택형 OCR 보조 시도", value=False, key="v76_enable_ocr")
        v76_manual_text = st.text_area(
            "수동 교정 반려 사유/개선 메모",
            value=v76_engine.DEFAULT_REJECTION_TEXT,
            height=185,
            key="v76_manual_text",
        )
        v76_rules = st.multiselect(
            "추가로 실제 반영할 재생성 규칙",
            [
                "외곽선 더 굵게",
                "얼굴 크기 확대",
                "문구 2~7자 우선",
                "표정 차이 크게",
                "GIF 모션 차이 크게",
                "말풍선과 캐릭터 동작 동기화",
                "다크모드 대비 강화",
                "32개/24개 중복감 줄이기",
            ],
            default=["문구 2~7자 우선", "표정 차이 크게", "GIF 모션 차이 크게", "32개/24개 중복감 줄이기"],
            key="v76_rules",
        )
        v76_online_notes = st.text_area(
            "온라인/공식 기준 추상 신호 메모",
            value="온라인 자료는 캐릭터/문구/애니메이션을 복제하지 않고, 문구 길이·감정 유형·모션 리듬·가독성 같은 추상 신호만 반영한다.",
            height=100,
            key="v76_online_notes",
        )
        st.warning("v76은 실제 재생성까지 연결하지만 자동 제출은 하지 않습니다. 생성 후 v71→v72→v73 재검사가 필요합니다.")

    if st.button("v76 캡처/반려 사유 기반 실제 재생성 실행", type="primary", key="v76_run_rejection_to_regeneration"):
        try:
            image_inputs = []
            if v76_capture_upload:
                for f in v76_capture_upload:
                    image_inputs.append((f.name, f.read()))
            result_obj = v76_engine.build_bundle(
                project_name=v76_project_name,
                concept_text=v76_concept,
                selected_style=v76_style,
                main_phrase=v76_phrase,
                user_feedback=v76_feedback,
                online_abstract_notes=v76_online_notes,
                manual_rejection_text=v76_manual_text,
                image_inputs=image_inputs,
                out_dir=BASE_OUTPUT / "v76_rejection_to_regeneration",
                enable_ocr=v76_enable_ocr,
                user_selected_rules=v76_rules,
            )
            st.session_state.v76_rejection_to_regeneration_report = result_obj.to_dict()
            st.success("v76 캡처/반려 사유 → v74 액션 플랜 → 실제 32/24 재생성 → HTML 리포트/작업 ZIP까지 생성했습니다.")
        except Exception as exc:
            st.error(f"v76 실제 재생성 연결 실패: {exc}")

    v76_report = st.session_state.get("v76_rejection_to_regeneration_report")
    if v76_report:
        st.markdown("### 실제 재생성 결과")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("상태", v76_report.get("pipeline_status"))
        c2.metric("정지형", v76_report.get("regenerated_static_count"))
        c3.metric("움직이는형", v76_report.get("regenerated_animated_count"))
        c4.metric("GIF", v76_report.get("regenerated_gif_count"))

        st.markdown("### 감지된 반려/개선 카테고리")
        cats = v76_report.get("detected_categories", [])
        st.write(", ".join(cats) if cats else "기본 품질 개선 카테고리로 재생성했습니다.")

        st.markdown("### 적용된 재생성 규칙")
        for rule in v76_report.get("applied_regeneration_rules", [])[:20]:
            st.write("- " + rule)

        gallery1 = Path(v76_report.get("regenerated_static_32_gallery", ""))
        gallery2 = Path(v76_report.get("regenerated_animated_24_gallery", ""))
        gif_sheet = Path(v76_report.get("regenerated_gif_contact_sheet", ""))
        if gallery1.exists():
            st.image(str(gallery1), caption="v76 재생성 정지형 32개 갤러리", use_container_width=True)
        if gallery2.exists():
            st.image(str(gallery2), caption="v76 재생성 움직이는형 24개 갤러리", use_container_width=True)
        if gif_sheet.exists():
            st.image(str(gif_sheet), caption="v76 재생성 GIF 후보 비교", use_container_width=True)

        st.markdown("### 다음 필수 단계")
        for step in v76_report.get("next_required_steps", []):
            st.warning(step)

        if st.button("v76 결과를 v71 QC 재검사 흐름에 적용", key="v76_apply_to_qc_flow"):
            st.session_state.v76_rejection_to_regeneration_applied = v76_report
            st.session_state.v76_requires_qc_recheck = True
            st.success("v76 재생성 결과를 다음 v71 QC 재검사 흐름에 적용했습니다.")

        for label, path_key, mime in [
            ("v76 HTML 리포트 다운로드", "html_report_path", "text/html"),
            ("v76 적용 액션 플랜 CSV 다운로드", "regeneration_action_plan_csv", "text/csv"),
            ("v76 재생성 프롬프트 팩 다운로드", "regeneration_prompt_md", "text/markdown"),
            ("v76 manifest JSON 다운로드", "regeneration_manifest_json", "application/json"),
            ("v76 재생성 세트 ZIP 다운로드", "regenerated_set_package_zip", "application/zip"),
            ("v76 전체 작업 ZIP 다운로드", "work_package_zip", "application/zip"),
            ("v76 학습 DB 다운로드", "learning_db", "application/octet-stream"),
            ("연결된 v75 HTML 리포트 다운로드", "capture_v75_report_html", "text/html"),
            ("연결된 v74 액션 플랜 CSV 다운로드", "connected_v74_action_plan_csv", "text/csv"),
            ("재생성 v70 HTML 리포트 다운로드", "regenerated_v70_html_report", "text/html"),
        ]:
            fp = Path(v76_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v76_download_{path_key}")

    st.caption("v76은 반려/캡처 입력을 실제 재생성까지 연결합니다. 재생성 이후에는 반드시 v71 QC, v72 자동보정/잠금, v73 사용자 승인 흐름을 다시 실행해야 합니다.")


if selected_page_index == 63:
    st.subheader("v80 최종 통합 납품/재검사")
    st.write("v77 재생성 QC 재연결 → v78 자동보정/잠금/사용자 승인 → v79 설치/데이터 보호 최종화 → v80 마스터 납품 ZIP을 한 번에 실행합니다.")
    st.warning("자동 제출 기능은 없습니다. 최종 업로드는 사용자가 최신 카카오 공식 기준을 직접 확인한 뒤 수동으로 진행해야 합니다.")

    with st.expander("v90 이전 버전 안전 정리 · C드라이브/설치 폴더 청소", expanded=False):
        st.write("C드라이브 루트나 LocalAppData에 남은 이전 버전 폴더를 검사합니다. v90 설치 흐름에서는 이전 버전 백업 후 정리를 자동으로 실행하고, 이 화면에서는 먼저 미리보기 리포트를 확인합니다.")
        st.code("00_STEP_4_SAFE_CLEAN_OLD_VERSIONS.bat", language="text")
        st.markdown("- 1번: 검사만 실행\n- 2번: 안전 격리 폴더로 이동\n- 3번: 사용자 데이터 후보 백업 후 영구 삭제")
        if st.button("이전 버전 미리보기 검사 실행", key="v90_cleanup_preview_button"):
            try:
                proc = subprocess.run(
                    [sys.executable, "scripts/cleanup_old_versions_v90.py", "--mode", "preview", "--current-version", "90", "--current-path", str(Path.cwd())],
                    cwd=str(Path.cwd()),
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if proc.returncode == 0:
                    data = json.loads(proc.stdout)
                    st.success(f"검사 완료: 이전 버전 후보 {data.get('candidate_count', 0)}개")
                    st.json(data.get("summary", {}))
                    st.caption(data.get("report_path", ""))
                else:
                    st.error("이전 버전 미리보기 검사에서 확인이 필요합니다.")
                    st.text(proc.stdout[-3000:] + proc.stderr[-3000:])
            except Exception as exc:
                st.error(f"이전 버전 검사 실행 실패: {exc}")
        st.caption("수동 정리/삭제는 BAT 파일에서 확인 문구를 입력해야 진행됩니다. 설치/업그레이드 흐름에서는 현재 v90 이상을 제외하고 v89 이하만 백업 후 정리합니다.")

    c1, c2 = st.columns([1.2, 0.8])
    with c1:
        v80_project = st.text_input("프로젝트명", value="v80_final_integrated_delivery", key="v80_project_name")
        v80_concept = st.text_area("최종 콘셉트", value=V80FinalDeliveryPipelineEngine.DEFAULT_CONCEPT, height=120, key="v80_concept")
        v80_rejection = st.text_area("반려/개선 메모 또는 캡처 교정 텍스트", value=V80FinalDeliveryPipelineEngine.DEFAULT_REJECTION_TEXT, height=110, key="v80_rejection")
        v80_confirm = st.checkbox("사용자 최종 확인을 모두 완료한 것으로 테스트 실행", value=True, key="v80_confirm_all")
        run_v80 = st.button("v80 최종 통합 납품 패키지 생성", type="primary", key="v80_run_final_delivery")
    with c2:
        st.markdown("### 실행되는 통합 단계")
        st.markdown("""
        - v76 재생성 결과 생성
        - v71 QC 재검사 흐름 연결
        - v72 자동보정/잠금 연결
        - v73 사용자 수동 승인 후보 생성
        - v80 최종 마스터 ZIP/가이드/manifest 생성
        - API 키 원문 누출 검사
        """)

    if run_v80:
        try:
            result = V80FinalDeliveryPipelineEngine().build_bundle(
                project_name=v80_project,
                concept_text=v80_concept,
                rejection_text=v80_rejection,
                out_dir=BASE_OUTPUT / "v80_final_delivery",
                user_confirmed_final=v80_confirm,
            )
            st.session_state.v80_final_delivery_report = result.to_dict()
            st.success("v80 최종 통합 납품 패키지를 생성했습니다.")
        except Exception as exc:
            st.error(f"v80 최종 통합 납품 실패: {exc}")

    v80_report = st.session_state.get("v80_final_delivery_report")
    if v80_report:
        st.markdown("### 최종 통합 결과")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("최종 상태", v80_report.get("final_status"))
        m2.metric("단계 통과", f"{v80_report.get('passed_pipeline_steps')}/{v80_report.get('total_pipeline_steps')}")
        m3.metric("공식 기준 재확인", "필수" if v80_report.get("official_recheck_required") else "완료")
        m4.metric("API 키 원문", "없음" if not v80_report.get("api_key_plaintext_found") else "확인 필요")

        if v80_report.get("blocking_reasons"):
            st.error("차단/확인 필요 항목이 있습니다.")
            for reason in v80_report.get("blocking_reasons", []):
                st.write("- " + reason)
        else:
            st.success("로컬 패키지 생성 기준 차단 사유는 없습니다. 단, 제출 전 공식 기준 재확인은 필수입니다.")

        st.markdown("### 다음 실행 순서")
        for step in v80_report.get("final_next_steps", []):
            st.write("- " + step)

        html = Path(v80_report.get("final_html_report", ""))
        if html.exists():
            st.components.v1.html(html.read_text(encoding="utf-8"), height=720, scrolling=True)

        for label, path_key, mime in [
            ("v80 최종 HTML 리포트 다운로드", "final_html_report", "text/html"),
            ("v80 최종 운영 가이드 다운로드", "final_operator_guide_md", "text/markdown"),
            ("v80 최종 Manifest JSON 다운로드", "final_manifest_json", "application/json"),
            ("v80 최종 체크리스트 CSV 다운로드", "final_checklist_csv", "text/csv"),
            ("v80 마스터 납품 ZIP 다운로드", "final_master_delivery_zip", "application/zip"),
            ("v73 사용자 승인 후보 ZIP 다운로드", "v73_final_approved_zip", "application/zip"),
            ("v76 재생성 작업 ZIP 다운로드", "v76_regenerated_work_package_zip", "application/zip"),
            ("v80 학습 DB 다운로드", "final_learning_db", "application/octet-stream"),
        ]:
            fp = Path(v80_report.get(path_key, ""))
            if fp.exists():
                st.download_button(label, data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"v80_download_{path_key}")

    st.caption("v80은 최종 납품 파일을 만들지만 자동 제출은 하지 않습니다. 제출 전 최신 공식 기준과 사용권리/유사성은 사용자가 직접 다시 확인해야 합니다.")
