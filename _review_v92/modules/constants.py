from __future__ import annotations

APP_NAME = "카카오 이모티콘 직접 제작 도우미 v92"
APP_VERSION = "92.0.0"

FORMAT_LABELS = {
    "static": "멈춰있는 이모티콘",
    "static_text": "문구 결합형 멈춰있는 이모티콘",
    "animated": "움직이는 이모티콘",
    "animated_text": "움직이는 문구 결합형 이모티콘",
    "big": "큰 이모티콘",
    "series": "시리즈형 캐릭터 확장",
}

# 카카오 공식 세부 제출 수량은 시점/포맷별 변경 가능성이 있으므로,
# 프로그램 내부에서는 '기획 기준 수량'으로만 사용하고 제출 직전 공식 스튜디오에서 재확인하도록 안내합니다.
PLANNING_COUNTS = {
    "static": 32,
    "static_text": 32,
    "animated": 24,
    "animated_text": 24,
    "big": 16,
    "series": 2,
}

FORBIDDEN_STYLE_KEYWORDS = [
    "춘식이", "라이언", "어피치", "카카오프렌즈", "카카오 프렌즈",
    "라인프렌즈", "라인 프렌즈", "브라운", "코니", "산리오", "헬로키티",
    "포켓몬", "피카츄", "디즈니", "미키", "짱구", "스누피", "도라에몽",
    "마블", "아이언맨", "스파이더맨", "웹툰 캐릭터", "연예인 얼굴",
    "비슷하게", "똑같이", "따라", "따라서", "스타일로", "느낌으로",
]

AI_RISK_KEYWORDS = [
    "AI 생성", "생성형 AI", "미드저니", "스테이블디퓨전", "stable diffusion",
    "midjourney", "dalle", "dall-e", "AI 그림", "완성본 자동생성",
    "자동생성으로 제출", "AI로 만든 완성본", "AI 티 안나게", "검수 우회",
    "프롬프트만으로 완성", "이미지 생성기로 완성",
]

TARGET_GROUPS = ["직장인", "커플", "가족", "친구", "자취생", "학생", "반려동물", "덕후", "운동", "다이어트"]
CORE_EMOTIONS = [
    "인사", "감사", "사과", "확인", "수락", "거절", "부탁", "응원", "축하",
    "피곤", "당황", "분노", "슬픔", "기쁨", "민망", "기다림", "퇴근", "출근",
]

DEFAULT_CHARACTER_BASES = [
    "감자", "고구마", "보리", "쌀", "쌀알", "메모지", "돌멩이", "무", "양말", "얼음", "먼지", "만두", "종이컵",
    "연필", "버섯", "콩", "스티커", "작은 구름", "물방울",
]

PHRASE_GROUPS = {
    "기본 답장": ["넵", "확인했습니다", "알겠습니다", "잠시만요", "바로 볼게요", "완료했습니다", "접수했습니다", "가능합니다", "어렵습니다", "괜찮습니다"],
    "감사/사과": ["감사합니다", "고맙습니다", "죄송합니다", "미안해요", "부탁드립니다", "도와주세요", "신경 써주셔서 감사합니다", "다음엔 더 잘할게요", "마음만 받겠습니다", "정말 죄송합니다"],
    "직장/일상": ["출근했습니다", "퇴근하고 싶습니다", "회의 중입니다", "야근입니다", "월요일입니다", "오늘도 버팁니다", "커피는 못 살립니다", "이미 구겨졌습니다", "살려주세요", "업무에 눌렸습니다"],
    "감정 리액션": ["좋아요", "최고예요", "대박", "감동입니다", "울컥", "당황했습니다", "부들부들", "기절", "민망합니다", "눈물 납니다", "화났습니다", "행복합니다"],
    "관계/대화": ["잘자요", "보고 싶어요", "괜찮아요", "조심히 와요", "축하해요", "파이팅", "응원합니다", "기다릴게요", "밥 먹었어요?", "주말 잘 보내요"],
    "시그니처/확장": ["접혀있겠습니다", "펴지면 답장할게요", "칭찬받으면 싹납니다", "마음은 출근 안 했습니다", "영혼은 퇴근했습니다", "잠시 녹는 중", "작아지는 중", "오늘도 납작합니다", "조용히 파이팅", "구겨져도 갑니다"],
}

V54_INSTALLER_HOTFIX = True

V56_INNO_INSTALLER_WIZARD = True

V58_API_KEY_SAFETY = True
V59_SAFE_CLEANUP_INSTALLER = True
V60_ROBUST_INSTALLER_BUILD_FIX = True
V61_KAKAO_MOTION_PREVIEW_IMPROVER = True
V62_JINJA_TEMPLATE_ENGINE = True

V63_TEMPLATE_ENGINE_MANAGER = True

V64_CODING_TOOLCHAIN_MANAGER = True

V65_PROFESSIONAL_IDE_TOOLCHAIN = True

V66_MULTI_TOOL_EXECUTION_PIPELINE = True

V67_VIDEO_QUALITY_DIRECTION = True
V68_CONTINUOUS_QUALITY_EVOLUTION = True
V69_ACTUAL_QUALITY_UPGRADE = True

V70_SET_COMPLETENESS_UPGRADE = True

V73_FINAL_USER_APPROVAL_WORKFLOW = True

V77_REGENERATED_QC_RECONNECT = True
V78_AUTOFIX_APPROVAL_RECONNECT = True
V79_INSTALLER_DATA_PROTECTION_FINAL = True
V80_FINAL_DELIVERY_PIPELINE = True

V84_FIRST_RUN_RUNTIME_HOTFIX = True

V90_SAFE_OLD_VERSION_CLEANUP = True
V90_SIMPLE_PNG_GIF_OUTPUT = True
V92_SAFE_ERROR_DIAGNOSTICS = True
