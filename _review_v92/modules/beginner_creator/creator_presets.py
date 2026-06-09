from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class PresetOption:
    label: str
    value: str
    note: str = ""

    def to_dict(self):
        return asdict(self)


COLOR_PALETTES: Dict[str, List[str]] = {
    "따뜻한 곡물톤": ["#C89A5C", "#F4EBCD", "#E9C46A", "#C8783E", "#A88E55"],
    "부드러운 파스텔톤": ["#F7C7D9", "#D9F2E6", "#F7E7A6", "#D4C2FC", "#CDE7F0"],
    "선명한 캐릭터톤": ["#FFB000", "#4FC3F7", "#81C784", "#FF7043", "#BA68C8"],
    "흑백 낙서톤": ["#F8F8F8", "#D9D9D9", "#AFAFAF", "#6B6B6B", "#2F2F2F"],
    "직장인 차분톤": ["#D7C3A1", "#BFC7D5", "#A8B7A1", "#C8B6A6", "#8E8E93"],
    "과일·채소톤": ["#F4D35E", "#EE964B", "#8AB17D", "#E76F51", "#7BC6A4"],
    "밤하늘 감성톤": ["#2D3142", "#4F5D75", "#BFC0C0", "#EF8354", "#FFFFFF"],
}

COLOR_PRESET_LABELS = list(COLOR_PALETTES.keys())

PERSONALITY_PRESETS: List[PresetOption] = [
    PresetOption("직접 입력", "", "사용자가 직접 성격을 입력"),
    PresetOption("까칠하지만 은근히 챙김", "까칠하지만 은근히 챙김", "츤데레/투덜이 계열"),
    PresetOption("온순하고 다정함", "온순하고 다정함", "위로/감사/사과 표현에 유리"),
    PresetOption("피곤하지만 성실함", "피곤하지만 성실함", "직장인/일상 답장형에 유리"),
    PresetOption("느긋하고 포근함", "느긋하고 포근함", "친근한 대화 유지형"),
    PresetOption("소심하지만 반응이 큼", "소심하지만 반응이 큼", "당황/민망/리액션 표현에 유리"),
    PresetOption("무표정하지만 속정 있음", "무표정하지만 속정 있음", "짧은 문구/하찮은 캐릭터에 유리"),
    PresetOption("밝고 과장된 리액션", "밝고 과장된 리액션", "큰 이모티콘/움직이는 이모티콘에 유리"),
    PresetOption("업무에 눌려 구겨짐", "업무에 눌려 구겨짐", "메모지/직장인/문구형에 유리"),
]

TONE_PRESETS: List[PresetOption] = [
    PresetOption("직접 입력", "", "사용자가 직접 말투를 입력"),
    PresetOption("투덜거림, 짧게 말함", "투덜거림, 짧게 말함", "보리/돌멩이/까칠 캐릭터"),
    PresetOption("부드럽고 위로하는 말투", "부드럽고 위로하는 말투", "쌀/구름/온순 캐릭터"),
    PresetOption("작게 한숨 섞인 말투", "작게 한숨 섞인 말투", "감자/직장인/피곤 캐릭터"),
    PresetOption("느긋하고 둥근 말투", "느긋하고 둥근 말투", "고구마/포근 캐릭터"),
    PresetOption("짧은 업무 답장 말투", "짧은 업무 답장 말투", "메모지/직장인 문구형"),
    PresetOption("무표정 단답 말투", "무표정 단답 말투", "돌멩이/먼지/하찮은 캐릭터"),
    PresetOption("밝고 크게 리액션하는 말투", "밝고 크게 리액션하는 말투", "큰 이모티콘/축하/응원형"),
    PresetOption("말끝이 작아지는 소심한 말투", "말끝이 작아지는 소심한 말투", "민망/사과/부탁형"),
]

ROLE_PRESETS: List[str] = [
    "중심",
    "보조/반응",
    "리액션 담당",
    "위로 담당",
    "문구 담당",
    "갈등/반전 담당",
    "시그니처 담당",
]


def color_from_palette(palette_name: str, index: int) -> str:
    colors = COLOR_PALETTES.get(palette_name) or COLOR_PALETTES["따뜻한 곡물톤"]
    return colors[index % len(colors)]


def preset_value(options: List[PresetOption], label: str, fallback: str = "") -> str:
    for option in options:
        if option.label == label:
            return option.value or fallback
    return fallback


def palette_swatch_html(palette_name: str) -> str:
    colors = COLOR_PALETTES.get(palette_name, [])
    chips = "".join(
        f"<span style='display:inline-block;width:32px;height:20px;border:1px solid #999;background:{c};margin-right:5px;border-radius:4px'></span>"
        for c in colors
    )
    return f"<div style='margin:4px 0'><b>{palette_name}</b><br>{chips}</div>"
