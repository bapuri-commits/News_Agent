"""브리핑 테마 결정 로직 — html_renderer와 deployer에서 공용."""

from __future__ import annotations

from collections import Counter


THEMES = {
    "tech_blue": {
        "bg": "#f0f4ff", "accent": "#1a73e8", "accent_light": "#e8f0fe",
        "header_gradient": "linear-gradient(135deg, #1a73e8 0%, #4285f4 100%)",
        "label": "Tech Focus",
    },
    "infra_purple": {
        "bg": "#f5f0ff", "accent": "#7c3aed", "accent_light": "#ede9fe",
        "header_gradient": "linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)",
        "label": "Infra Focus",
    },
    "deal_green": {
        "bg": "#f0fdf4", "accent": "#16a34a", "accent_light": "#dcfce7",
        "header_gradient": "linear-gradient(135deg, #16a34a 0%, #4ade80 100%)",
        "label": "Deal Flow",
    },
    "risk_red": {
        "bg": "#fef2f2", "accent": "#dc2626", "accent_light": "#fee2e2",
        "header_gradient": "linear-gradient(135deg, #dc2626 0%, #f87171 100%)",
        "label": "Risk Alert",
    },
    "sk_orange": {
        "bg": "#fff7ed", "accent": "#ea580c", "accent_light": "#ffedd5",
        "header_gradient": "linear-gradient(135deg, #ea580c 0%, #fb923c 100%)",
        "label": "SK Focus",
    },
    "market_teal": {
        "bg": "#f0fdfa", "accent": "#0891b2", "accent_light": "#ccfbf1",
        "header_gradient": "linear-gradient(135deg, #0891b2 0%, #22d3ee 100%)",
        "label": "Market Watch",
    },
}


def pick_theme(briefing: dict) -> dict:
    """브리핑 내용을 분석하여 오늘의 테마를 결정한다."""
    categories = briefing.get("by_category", {})
    risks = briefing.get("risks", [])
    sk = briefing.get("sk_ecoplant")
    top5 = briefing.get("top5", [])

    cat_counts: Counter[str] = Counter()
    for cat_key, cat_data in categories.items():
        cat_counts[cat_key] = len(cat_data.get("items", []))

    top_cat = cat_counts.most_common(1)[0][0] if cat_counts else "other"

    if len(risks) >= 4:
        return THEMES["risk_red"]

    if sk and (cat_counts.get("sk_ecoplant", 0) >= 5 or
               any("SK에코플랜트" in str(item.get("headline", "")) for item in top5)):
        return THEMES["sk_orange"]

    if top_cat in ("fab_capex", "cleanroom", "equipment_supply", "packaging", "capex_guidance"):
        return THEMES["tech_blue"]
    if top_cat in ("dc_build", "dc_power", "dc_cooling", "construction_tech", "urban_smartcity"):
        return THEMES["infra_purple"]
    if top_cat in ("epc_award", "ma_restructure", "schedule_cost", "material_labor",
                   "permit", "talent_hr", "milestone"):
        return THEMES["deal_green"]
    if top_cat in ("pf_finance", "esg_regulation", "contingent", "policy_subsidy",
                   "safety"):
        return THEMES["market_teal"]

    return THEMES["tech_blue"]
