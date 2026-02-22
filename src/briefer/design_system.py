"""다층 디자인 시스템 — Theme + Layout Variant + Component Variant.

매일 다른 에디토리얼 느낌을 주기 위해 8개 큐레이팅된 프리셋을 정의하고,
콘텐츠 시그니처 기반으로 적절한 프리셋을 선택한다.
LLM 호출 없이 알고리즘만으로 동작한다.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DESIGN_PRESETS: dict[str, dict[str, Any]] = {
    # ── 1. Hero Bold ── urgency / 중대 뉴스
    "hero_bold": {
        "bg": "#ffffff",
        "surface": "#ffffff",
        "text": "#1f2937",
        "text_secondary": "#6b7280",
        "border": "#e5e7eb",
        "accent": "#1a73e8",
        "accent_light": "#e8f0fe",
        "header_gradient": "linear-gradient(135deg, #1e3a5f 0%, #1a73e8 50%, #3b82f6 100%)",
        "label": "Deep Dive",
        "layout": "hero",
        "card_style": "elevated",
        "number_highlight": True,
        "dark": False,
    },
    # ── 2. Noir Data ── 수치 밀도 높을 때, 다크 테마
    "noir_data": {
        "bg": "#0f172a",
        "surface": "#1e293b",
        "text": "#e2e8f0",
        "text_secondary": "#94a3b8",
        "border": "#334155",
        "accent": "#38bdf8",
        "accent_light": "#0c4a6e",
        "header_gradient": "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
        "label": "Data Pulse",
        "layout": "hero",
        "card_style": "glass",
        "number_highlight": True,
        "dark": True,
    },
    # ── 3. Journal Classic ── 기본/혼합 콘텐츠
    "journal_classic": {
        "bg": "#fafaf9",
        "surface": "#ffffff",
        "text": "#1c1917",
        "text_secondary": "#78716c",
        "border": "#e7e5e4",
        "accent": "#44403c",
        "accent_light": "#f5f5f4",
        "header_gradient": "linear-gradient(135deg, #292524 0%, #44403c 100%)",
        "label": "Morning Brief",
        "layout": "editorial",
        "card_style": "flat",
        "number_highlight": False,
        "dark": False,
    },
    # ── 4. Grid Tech ── 반도체/장비
    "grid_tech": {
        "bg": "#f0f4ff",
        "surface": "#ffffff",
        "text": "#1f2937",
        "text_secondary": "#6b7280",
        "border": "#dbeafe",
        "accent": "#2563eb",
        "accent_light": "#eff6ff",
        "header_gradient": "linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)",
        "label": "Tech Focus",
        "layout": "grid",
        "card_style": "bordered",
        "number_highlight": True,
        "dark": False,
    },
    # ── 5. Warm Earth ── Deal Flow / 건설 / EPC
    "warm_earth": {
        "bg": "#fef7ee",
        "surface": "#ffffff",
        "text": "#1c1917",
        "text_secondary": "#78716c",
        "border": "#fde68a",
        "accent": "#b45309",
        "accent_light": "#fef3c7",
        "header_gradient": "linear-gradient(135deg, #92400e 0%, #d97706 100%)",
        "label": "Deal Flow",
        "layout": "editorial",
        "card_style": "bordered",
        "number_highlight": False,
        "dark": False,
    },
    # ── 6. Risk Crimson ── 리스크 많을 때
    "risk_crimson": {
        "bg": "#fef2f2",
        "surface": "#ffffff",
        "text": "#1f2937",
        "text_secondary": "#6b7280",
        "border": "#fecaca",
        "accent": "#dc2626",
        "accent_light": "#fee2e2",
        "header_gradient": "linear-gradient(135deg, #991b1b 0%, #dc2626 50%, #ef4444 100%)",
        "label": "Risk Alert",
        "layout": "hero",
        "card_style": "elevated",
        "number_highlight": True,
        "dark": False,
    },
    # ── 7. Ocean Depth ── 데이터센터 / 인프라 / 시장
    "ocean_depth": {
        "bg": "#f0fdfa",
        "surface": "#ffffff",
        "text": "#134e4a",
        "text_secondary": "#5f7a76",
        "border": "#ccfbf1",
        "accent": "#0891b2",
        "accent_light": "#cffafe",
        "header_gradient": "linear-gradient(135deg, #164e63 0%, #0891b2 100%)",
        "label": "Market Watch",
        "layout": "grid",
        "card_style": "glass",
        "number_highlight": False,
        "dark": False,
    },
    # ── 8. Dawn Gradient ── SK 에코플랜트 / IPO
    "dawn_gradient": {
        "bg": "#fffbeb",
        "surface": "#ffffff",
        "text": "#1c1917",
        "text_secondary": "#92400e",
        "border": "#fed7aa",
        "accent": "#ea580c",
        "accent_light": "#ffedd5",
        "header_gradient": "linear-gradient(135deg, #9a3412 0%, #ea580c 50%, #fb923c 100%)",
        "label": "SK Focus",
        "layout": "editorial",
        "card_style": "elevated",
        "number_highlight": True,
        "dark": False,
    },
}

_TOPIC_GROUPS = {
    "tech": {"fab_capex", "cleanroom", "equipment_supply", "packaging",
             "capex_guidance", "memory_foundry", "ai_trend"},
    "infra": {"dc_build", "dc_power", "dc_cooling", "construction_tech",
              "urban_smartcity"},
    "deal": {"epc_award", "ma_restructure", "schedule_cost", "material_labor",
             "permit", "talent_hr", "milestone"},
    "market": {"pf_finance", "esg_regulation", "contingent", "policy_subsidy",
               "safety"},
}

_HISTORY_PATH = Path(__file__).resolve().parent.parent.parent / "output" / "design_history.json"


def _load_history() -> dict[str, str]:
    try:
        with open(_HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_history(history: dict[str, str]) -> None:
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def analyze_signature(briefing: dict) -> dict[str, Any]:
    """콘텐츠 시그니처를 알고리즘으로 추출한다."""
    risks = briefing.get("risks", [])
    top5 = briefing.get("top5", [])
    categories = briefing.get("by_category", {})
    sk = briefing.get("sk_ecoplant")

    all_text = json.dumps(briefing, ensure_ascii=False)
    number_hits = len(re.findall(r"\d[\d,.]*\s*(?:조원?|억원?|만원?|%|MW|GW|달러|원|건|배|분기|년)(?![가-힣])", all_text))

    cat_counts: Counter[str] = Counter()
    for cat_key, cat_data in categories.items():
        cat_counts[cat_key] = len(cat_data.get("items", []))
    top_cat = cat_counts.most_common(1)[0][0] if cat_counts else "other"

    dominant = "mixed"
    for group_name, group_cats in _TOPIC_GROUPS.items():
        if top_cat in group_cats:
            dominant = group_name
            break

    sk_heavy = bool(
        sk and (cat_counts.get("sk_ecoplant", 0) >= 3
                or any("SK에코플랜트" in str(item.get("headline", "")) for item in top5))
    )

    return {
        "urgency": "high" if len(risks) >= 4 else "normal",
        "data_density": "high" if number_hits > 12 else "normal",
        "topic_focus": dominant,
        "sk_heavy": sk_heavy,
        "risk_count": len(risks),
        "top_cat": top_cat,
    }


def _candidate_presets(sig: dict) -> list[str]:
    """시그니처 기반 후보 프리셋을 우선순위 리스트로 반환한다."""
    ordered: list[str] = []
    seen: set[str] = set()

    def _add(*keys: str) -> None:
        for k in keys:
            if k not in seen:
                ordered.append(k)
                seen.add(k)

    if sig["urgency"] == "high":
        _add("risk_crimson", "hero_bold")

    if sig["sk_heavy"]:
        _add("dawn_gradient")

    if sig["data_density"] == "high":
        _add("noir_data", "grid_tech")

    focus = sig["topic_focus"]
    if focus == "tech":
        _add("grid_tech", "noir_data", "hero_bold")
    elif focus == "infra":
        _add("ocean_depth", "grid_tech")
    elif focus == "deal":
        _add("warm_earth", "journal_classic")
    elif focus == "market":
        _add("ocean_depth", "journal_classic")
    else:
        _add("journal_classic", "hero_bold", "warm_earth")

    for key in DESIGN_PRESETS:
        _add(key)

    return ordered


def pick_design(briefing: dict, *, save_history: bool = True) -> dict[str, Any]:
    """콘텐츠 시그니처 + 최근 이력 기반으로 디자인 프리셋을 선택한다.

    save_history=False로 호출하면 디스크 쓰기 없이 읽기만 수행한다.
    index_generator 등 부작용이 불필요한 호출에서 사용.
    """
    sig = analyze_signature(briefing)
    candidates = _candidate_presets(sig)
    date = briefing.get("date", "")

    history = _load_history()
    recent_values = []
    for d in sorted(history.keys(), reverse=True)[:3]:
        if d != date:
            recent_values.append(history[d])

    chosen = candidates[0]
    for c in candidates:
        if c not in recent_values:
            chosen = c
            break

    result = {**DESIGN_PRESETS[chosen], "preset_key": chosen}

    if save_history and date:
        history[date] = chosen
        _save_history(history)

    return result
