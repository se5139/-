from __future__ import annotations

TEXT_MOTION_PRESETS = {
    "도장처럼 등장": {
        "description": "확인/완료/접수 계열 문구에 적합합니다.",
        "scale_sequence": [0.4, 0.7, 1.2, 1.0, 1.0, 1.0, 1.0, 1.0],
        "y_offset_sequence": [8, 4, -3, 0, 0, 0, 0, 0],
    },
    "살짝 떨림": {
        "description": "죄송/당황/분노 계열 문구에 적합합니다.",
        "x_offset_sequence": [0, -2, 2, -2, 2, -1, 1, 0],
        "scale_sequence": [1.0] * 8,
    },
    "천천히 나타남": {
        "description": "감사/잘자요/위로 계열 문구에 적합합니다.",
        "alpha_sequence": [50, 90, 130, 170, 210, 255, 255, 255],
        "scale_sequence": [0.9, 0.92, 0.95, 0.98, 1.0, 1.0, 1.0, 1.0],
    },
    "축 처짐": {
        "description": "피곤/퇴근/번아웃 계열 문구에 적합합니다.",
        "y_offset_sequence": [-8, -4, 0, 4, 8, 6, 4, 0],
        "scale_sequence": [1.0, 1.0, 0.98, 0.96, 0.94, 0.96, 0.98, 1.0],
    },
    "점 세 개 순차 등장": {
        "description": "넵..., 기다림, 어색함 표현에 적합합니다.",
        "scale_sequence": [1.0] * 8,
    },
}
