"""브리핑 JSON → Markdown 텍스트 렌더링.

카톡/이메일로 바로 보낼 수 있는 형식.
"""

from __future__ import annotations

from src.briefer.constants import CATEGORY_LABELS, SOURCE_GROUP_LABELS


def render_markdown(briefing: dict) -> str:
    """브리핑 JSON을 Markdown 문자열로 렌더링한다."""
    date = briefing.get("date", "")
    lines = [
        f"# 임원 뉴스 브리핑 — {date}",
        "",
        f"> 읽기 시간: 약 {briefing.get('reading_time_min', 15)}분",
        "",
    ]

    lines.extend(_render_top5(briefing.get("top5", [])))
    lines.extend(_render_sk_ecoplant(briefing.get("sk_ecoplant")))
    lines.extend(_render_categories(briefing.get("by_category", {})))
    lines.extend(_render_risks(briefing.get("risks", [])))
    lines.extend(_render_next_signals(briefing.get("next_signals", [])))
    lines.extend(_render_source_diversity(briefing.get("source_diversity", {})))

    lines.append("")
    lines.append(f"---\n*생성: {briefing.get('generated_at', '')}*")

    return "\n".join(lines)


def _render_top5(items: list[dict]) -> list[str]:
    if not items:
        return []

    lines = ["## Top 5", ""]
    for i, item in enumerate(items, 1):
        headline = item.get("headline", item.get("title", ""))
        lines.append(f"### {i}. {headline}")
        lines.append("")

        if item.get("fact"):
            lines.append(f"**Fact**: {item['fact']}")
        if item.get("impact"):
            lines.append(f"**Impact**: {item['impact']}")
        if item.get("risk") and item["risk"] != "특이사항 없음":
            lines.append(f"**Risk**: {item['risk']}")
        if item.get("next_signal"):
            lines.append(f"**Next**: {item['next_signal']}")

        sources = item.get("sources", [])
        if sources:
            src_text = ", ".join(
                f"[{s.get('name', '')}]({s.get('url', '')})" for s in sources
            )
            lines.append(f"*출처: {src_text}*")

        lines.append("")

    return lines


def _render_sk_ecoplant(sk: dict | None) -> list[str]:
    if not sk:
        return []

    lines = [
        "## SK에코플랜트 렌즈",
        "",
        f"**{sk.get('headline', '')}**",
        "",
    ]

    lens_items = [
        ("수주·믹스", "order_mix"),
        ("현금흐름·차입", "cashflow"),
        ("PF/우발채무", "pf_contingent"),
        ("IPO/경쟁사", "competitor"),
    ]

    for label, key in lens_items:
        value = sk.get(key, "")
        if value and value != "해당 기간 특이사항 없음":
            lines.append(f"- **{label}**: {value}")

    lines.append("")
    return lines


def _render_categories(categories: dict) -> list[str]:
    if not categories:
        return []

    lines = ["## 카테고리별 동향", ""]

    for cat_key, cat_data in categories.items():
        label = CATEGORY_LABELS.get(cat_key, cat_key)
        summary = cat_data.get("summary", "")
        impact = cat_data.get("impact", "")
        items = cat_data.get("items", [])

        lines.append(f"### {label}")
        if summary:
            lines.append(f"{summary}")
            lines.append("")
        if impact:
            lines.append(f"**Impact**: {impact}")
            lines.append("")

        for item in items:
            headline = item.get("headline", "")
            fact = item.get("fact", "")
            if headline:
                lines.append(f"- **{headline}**")
                if fact:
                    lines.append(f"  {fact}")

        lines.append("")

    return lines


def _render_risks(risks: list[str]) -> list[str]:
    if not risks:
        return []

    lines = ["## 리스크 종합", ""]
    for risk in risks:
        lines.append(f"- {risk}")
    lines.append("")
    return lines


def _render_next_signals(signals: list[str]) -> list[str]:
    if not signals:
        return []

    lines = ["## Next Signals (향후 확인)", ""]
    for signal in signals:
        lines.append(f"- {signal}")
    lines.append("")
    return lines


def _render_source_diversity(dist: dict) -> list[str]:
    if not dist:
        return []

    lines = ["## 소스 분포", ""]
    total = sum(dist.values())
    for group, count in sorted(dist.items()):
        label = SOURCE_GROUP_LABELS.get(group, group)
        pct = count / total * 100 if total else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        lines.append(f"- {label} ({group}): {bar} {count}건 ({pct:.0f}%)")
    lines.append("")
    return lines
