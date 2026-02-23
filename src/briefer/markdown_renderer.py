"""브리핑 JSON → 레퍼런스 문서 렌더링.

HTML 카드 버전과는 다른 목적:
- 원본 소스를 잘 정리한 신뢰도 있는 참고 자료
- 기사별 출처 링크 명시
- 전달/보관/검토용 (카톡, 이메일, 아카이브)
"""

from __future__ import annotations

from src.briefer.constants import CATEGORY_LABELS, SOURCE_GROUP_LABELS


def render_markdown(briefing: dict) -> str:
    """브리핑 JSON을 레퍼런스 문서로 렌더링한다."""
    date = briefing.get("date", "")
    top5 = briefing.get("top5", [])
    categories = briefing.get("by_category", {})

    lines = [
        f"# Executive Briefing — {date}",
        "",
    ]

    lines.extend(_render_overview(top5))
    lines.append("")
    lines.extend(_render_main_stories(top5))
    lines.extend(_render_sk_ecoplant(briefing.get("sk_ecoplant")))
    lines.extend(_render_category_references(categories))
    lines.extend(_render_risks(briefing.get("risks", [])))
    lines.extend(_render_next_signals(briefing.get("next_signals", [])))
    lines.extend(_render_source_summary(briefing))

    lines.append("")
    lines.append(f"---\n*생성: {briefing.get('generated_at', '')}*")

    return "\n".join(lines)


def _render_overview(top5: list[dict]) -> list[str]:
    """1~2줄 핵심 요약."""
    if not top5:
        return []
    headlines = [item.get("headline", "") for item in top5[:3] if item.get("headline")]
    if not headlines:
        return []
    return [
        "> " + " / ".join(headlines),
        "",
    ]


def _render_main_stories(items: list[dict]) -> list[str]:
    """주요 뉴스 — 상세 분석 + 출처."""
    if not items:
        return []

    lines = ["---", "", "## 주요 뉴스", ""]

    for i, item in enumerate(items, 1):
        headline = item.get("headline", item.get("title", ""))
        lines.append(f"### {i}. {headline}")
        lines.append("")

        if item.get("fact"):
            lines.append(item["fact"])
            lines.append("")

        details = []
        if item.get("impact"):
            details.append(f"**영향**: {item['impact']}")
        if item.get("risk") and item["risk"] != "특이사항 없음":
            details.append(f"**리스크**: {item['risk']}")
        if item.get("next_signal"):
            details.append(f"**확인 필요**: {item['next_signal']}")

        if details:
            for d in details:
                lines.append(d)
            lines.append("")

        sources = item.get("sources", [])
        if sources:
            for s in sources:
                name = s.get("name", "")
                url = s.get("url", "")
                if url:
                    lines.append(f"📎 출처: [{name}]({url})")
                else:
                    lines.append(f"📎 출처: {name}")
            lines.append("")

    return lines


def _render_sk_ecoplant(sk: dict | None) -> list[str]:
    """SK에코플랜트 동향."""
    if not sk:
        return []

    lines = [
        "---", "",
        "## SK에코플랜트 동향",
        "",
    ]

    headline = sk.get("headline", "")
    if headline:
        lines.append(f"**{headline}**")
        lines.append("")

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

    sources = sk.get("sources", [])
    if sources:
        lines.append("")
        for s in sources:
            name = s.get("name", "")
            url = s.get("url", "")
            if url:
                lines.append(f"📎 [{name}]({url})")

    lines.append("")
    return lines


def _render_category_references(categories: dict) -> list[str]:
    """카테고리별 기사 레퍼런스 — 출처 링크 포함."""
    if not categories:
        return []

    lines = ["---", "", "## 카테고리별 기사", ""]

    for cat_key, cat_data in categories.items():
        label = CATEGORY_LABELS.get(cat_key, cat_key)
        summary = cat_data.get("summary", "")
        items = cat_data.get("items", [])

        lines.append(f"### {label}")
        if summary:
            lines.append(summary)
        lines.append("")

        for item in items:
            headline = item.get("headline", "")
            fact = item.get("fact", "")
            url = item.get("url", "")
            source_name = item.get("source_name", "")

            if headline:
                if url:
                    lines.append(f"- [{headline}]({url})")
                else:
                    lines.append(f"- {headline}")

                detail_parts = []
                if fact:
                    detail_parts.append(fact)
                if source_name and not url:
                    detail_parts.append(f"출처: {source_name}")

                if detail_parts:
                    lines.append(f"  {' — '.join(detail_parts)}")

        lines.append("")

    return lines


def _render_risks(risks: list[str]) -> list[str]:
    if not risks:
        return []

    lines = ["---", "", "## 리스크 모니터링", ""]
    for risk in risks:
        lines.append(f"- {risk}")
    lines.append("")
    return lines


def _render_next_signals(signals: list[str]) -> list[str]:
    if not signals:
        return []

    lines = ["## 향후 확인 사항", ""]
    for signal in signals:
        lines.append(f"- {signal}")
    lines.append("")
    return lines


def _render_source_summary(briefing: dict) -> list[str]:
    """전체 출처 요약."""
    dist = briefing.get("source_diversity", {})
    meta = briefing.get("metadata", {})
    if not dist:
        return []

    total = sum(dist.values())
    parts = []
    for group in sorted(dist.keys()):
        count = dist[group]
        label = SOURCE_GROUP_LABELS.get(group, group)
        parts.append(f"{label} {count}건")

    lines = [
        "---", "",
        "## 출처 요약",
        "",
        f"전체 {total}개 기사 분석 | {' · '.join(parts)}",
    ]

    crawl_success = meta.get("crawl_success", 0)
    crawl_attempted = meta.get("crawl_attempted", 0)
    if crawl_attempted:
        lines.append(f"본문 크롤링: {crawl_success}/{crawl_attempted}건 성공")

    lines.append("")
    return lines
