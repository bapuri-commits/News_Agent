"""브리핑 테마 결정 로직 — html_renderer와 deployer에서 공용.

design_system.py의 디자인 프리셋에서 테마 정보(색상/라벨)만 추출하여
기존 호출자(index_generator 등)와 하위 호환을 유지한다.
"""

from __future__ import annotations

from src.briefer.design_system import DESIGN_PRESETS, pick_design

THEMES = {
    key: {
        "bg": preset["bg"],
        "accent": preset["accent"],
        "accent_light": preset["accent_light"],
        "header_gradient": preset["header_gradient"],
        "label": preset["label"],
    }
    for key, preset in DESIGN_PRESETS.items()
}


def pick_theme(briefing: dict) -> dict:
    """브리핑 내용을 분석하여 오늘의 테마를 결정한다.

    design_system.pick_design()을 호출하고, 기존 호출자가 기대하는
    {bg, accent, accent_light, header_gradient, label} 형태로 반환한다.
    디스크 쓰기 부작용 없이 읽기만 수행한다 (index_generator 호환).
    """
    design = pick_design(briefing, save_history=False)
    return {
        "bg": design["bg"],
        "accent": design["accent"],
        "accent_light": design["accent_light"],
        "header_gradient": design["header_gradient"],
        "label": design["label"],
    }
