"""브리핑 JSON → 정적 HTML 렌더링 (다층 디자인 시스템).

단일 HTML 파일로 생성 — CSS/JS 인라인 포함.
모바일 반응형, 카드 기반, 접이식 상세.
Layout Variant(hero/grid/editorial) × Card Style(elevated/glass/flat/bordered)로
매일 다른 에디토리얼 느낌을 제공한다.
"""

from __future__ import annotations

import html
import re

from src.briefer.constants import (
    CATEGORY_LABELS, CATEGORY_COLORS, SOURCE_GROUP_LABELS,
)
from src.briefer.design_system import pick_design

_NUM_PATTERN = re.compile(
    r"(\d[\d,.]*\s*(?:조원?|억원?|만원?|%|MW|GW|달러|원|건|배|분기|년)(?![가-힣]))"
)


def _highlight_numbers(text: str, enabled: bool) -> str:
    """숫자+단위 패턴을 강조 태그로 감싼다."""
    if not enabled:
        return text
    return _NUM_PATTERN.sub(r'<strong class="num-hl">\1</strong>', text)


def render_html(briefing: dict) -> str:
    """브리핑 JSON을 완전한 HTML 문자열로 렌더링한다."""
    date = html.escape(briefing.get("date", ""))
    generated = briefing.get("generated_at", "")
    design = pick_design(briefing)
    num_hl = design.get("number_highlight", False)

    top5_html = _render_top5(briefing.get("top5", []), design)
    sk_html = _render_sk_ecoplant(briefing.get("sk_ecoplant"), num_hl)
    cat_html = _render_categories(briefing.get("by_category", {}), num_hl)
    risks_html = _render_risks(briefing.get("risks", []))
    signals_html = _render_next_signals(briefing.get("next_signals", []))
    source_html = _render_source_diversity(briefing.get("source_diversity", {}))

    layout = design.get("layout", "hero")
    card_style = design.get("card_style", "elevated")
    is_dark = design.get("dark", False)

    theme_css = (
        f":root {{\n"
        f"  --theme-bg: {design['bg']};\n"
        f"  --theme-surface: {design.get('surface', '#ffffff')};\n"
        f"  --theme-text: {design.get('text', '#1f2937')};\n"
        f"  --theme-text-secondary: {design.get('text_secondary', '#6b7280')};\n"
        f"  --theme-border: {design.get('border', '#e5e7eb')};\n"
        f"  --theme-accent: {design['accent']};\n"
        f"  --theme-accent-light: {design['accent_light']};\n"
        f"}}"
    )
    theme_label = html.escape(design.get("label", ""))
    header_gradient = design["header_gradient"]
    preset_key = html.escape(design.get("preset_key", ""))

    dark_class = " theme-dark" if is_dark else ""
    reading_meta = ""

    return f"""\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Executive Briefing — {date}</title>
{_CSS}
<style>{theme_css}</style>
</head>
<body>
<div class="container layout-{layout} cards-{card_style}{dark_class}" data-preset="{preset_key}">
  <header class="header" style="background: {header_gradient};">
    <div class="header-top">
      <h1 class="logo">Executive Briefing</h1>
      <span class="date-badge">{date}</span>
    </div>
    <p class="subtitle">건설 · 반도체 · 데이터센터 · 인프라</p>
    <div class="header-meta">
      <span class="theme-badge">{theme_label}</span>
      {reading_meta}
    </div>
  </header>

  <section class="section section-top5">
    <h2 class="section-title">
      <span class="section-icon">⚡</span> Top 5
    </h2>
    <div class="top5-grid">
      {top5_html}
    </div>
  </section>

  {sk_html}

  <section class="section">
    <h2 class="section-title">
      <span class="section-icon">📊</span> 카테고리별 동향
    </h2>
    {cat_html}
  </section>

  {risks_html}
  {signals_html}
  {source_html}

  <footer class="footer">
    <p>Generated {generated}</p>
  </footer>
</div>

<script>
document.querySelectorAll('.card-header').forEach(h => {{
  h.addEventListener('click', () => {{
    const card = h.closest('.card');
    card.classList.toggle('expanded');
  }});
}});
</script>
</body>
</html>"""


def _render_top5(items: list[dict], design: dict) -> str:
    if not items:
        return "<p class='empty'>수집된 Top 5 기사가 없습니다.</p>"

    num_hl = design.get("number_highlight", False)
    cards = []
    for i, item in enumerate(items, 1):
        headline = html.escape(item.get("headline", item.get("title", "")))
        fact = _highlight_numbers(html.escape(item.get("fact", "")), num_hl)
        impact = _highlight_numbers(html.escape(item.get("impact", "")), num_hl)
        risk = html.escape(item.get("risk", ""))
        next_sig = html.escape(item.get("next_signal", ""))

        cat = item.get("category", "other")
        if isinstance(cat, list):
            cat = cat[0] if cat else "other"
        color = CATEGORY_COLORS.get(cat, "#6b7280")
        cat_label = CATEGORY_LABELS.get(cat, cat)

        sources = item.get("sources", [])
        src_html = ""
        if sources:
            links = [
                f'<a href="{html.escape(s.get("url", ""))}" target="_blank" rel="noopener">'
                f'{html.escape(s.get("name", ""))}</a>'
                for s in sources
            ]
            src_html = f'<div class="sources">{" · ".join(links)}</div>'

        detail_rows = []
        if fact:
            detail_rows.append(
                f'<div class="detail-row"><span class="detail-label">Fact</span>'
                f'<span class="detail-text">{fact}</span></div>'
            )
        if impact:
            detail_rows.append(
                f'<div class="detail-row"><span class="detail-label impact">Impact</span>'
                f'<span class="detail-text">{impact}</span></div>'
            )
        if risk and risk != "특이사항 없음":
            detail_rows.append(
                f'<div class="detail-row"><span class="detail-label risk">Risk</span>'
                f'<span class="detail-text">{risk}</span></div>'
            )
        if next_sig:
            detail_rows.append(
                f'<div class="detail-row"><span class="detail-label next">Next</span>'
                f'<span class="detail-text">{next_sig}</span></div>'
            )

        hero_class = " hero-card" if i == 1 else ""

        cards.append(f"""\
    <div class="card top5-card{hero_class}" style="--accent: {color}">
      <div class="card-header">
        <span class="rank">#{i}</span>
        <div class="card-title-group">
          <h3 class="card-title">{headline}</h3>
          <span class="cat-badge" style="background: {color}15; color: {color}">{cat_label}</span>
        </div>
        <span class="chevron">▾</span>
      </div>
      <div class="card-body">
        {"".join(detail_rows)}
        {src_html}
      </div>
    </div>""")

    return "\n".join(cards)


def _render_sk_ecoplant(sk: dict | None, num_hl: bool) -> str:
    if not sk:
        return ""

    headline = html.escape(sk.get("headline", ""))

    lens_items = [
        ("수주·믹스", "order_mix", "#f97316"),
        ("현금흐름", "cashflow", "#ef4444"),
        ("PF/우발채무", "pf_contingent", "#dc2626"),
        ("IPO/경쟁사", "competitor", "#8b5cf6"),
    ]

    lens_cards = []
    for label, key, color in lens_items:
        value = _highlight_numbers(
            html.escape(sk.get(key, "해당 기간 특이사항 없음")), num_hl
        )
        lens_cards.append(f"""\
      <div class="lens-card" style="border-left: 3px solid {color}">
        <div class="lens-label" style="color: {color}">{label}</div>
        <div class="lens-text">{value}</div>
      </div>""")

    return f"""\
  <section class="section sk-section">
    <h2 class="section-title">
      <span class="section-icon">🏢</span> SK에코플랜트 렌즈
    </h2>
    <div class="sk-headline">{headline}</div>
    <div class="lens-grid">
      {"".join(lens_cards)}
    </div>
  </section>"""


def _render_categories(categories: dict, num_hl: bool) -> str:
    if not categories:
        return "<p class='empty'>카테고리별 데이터가 없습니다.</p>"

    groups = []
    for cat_key, cat_data in categories.items():
        label = html.escape(CATEGORY_LABELS.get(cat_key, cat_key))
        color = CATEGORY_COLORS.get(cat_key, "#6b7280")
        summary = _highlight_numbers(
            html.escape(cat_data.get("summary", "")), num_hl
        )
        impact = _highlight_numbers(
            html.escape(cat_data.get("impact", "")), num_hl
        )
        items = cat_data.get("items", [])

        item_rows = []
        for item in items:
            h = html.escape(item.get("headline", ""))
            f = _highlight_numbers(html.escape(item.get("fact", "")), num_hl)
            row = f'<li><strong>{h}</strong>'
            if f:
                row += f'<br><span class="cat-fact">{f}</span>'
            row += "</li>"
            item_rows.append(row)

        impact_html = ""
        if impact:
            impact_html = f'<p class="cat-impact"><span class="detail-label impact">Impact</span> {impact}</p>'

        groups.append(f"""\
    <div class="card cat-card" style="--accent: {color}">
      <div class="card-header">
        <span class="cat-badge" style="background: {color}15; color: {color}">{label}</span>
        <span class="item-count">{len(items)}건</span>
        <span class="chevron">▾</span>
      </div>
      <div class="card-body">
        <p class="cat-summary">{summary}</p>
        {impact_html}
        <ul class="cat-list">{"".join(item_rows)}</ul>
      </div>
    </div>""")

    return "\n".join(groups)


def _render_risks(risks: list[str]) -> str:
    if not risks:
        return ""

    items = "\n".join(f"<li>{html.escape(r)}</li>" for r in risks)
    return f"""\
  <section class="section">
    <h2 class="section-title">
      <span class="section-icon">⚠️</span> 리스크 종합
    </h2>
    <ul class="risk-list">{items}</ul>
  </section>"""


def _render_next_signals(signals: list[str]) -> str:
    if not signals:
        return ""

    items = "\n".join(f"<li>{html.escape(s)}</li>" for s in signals)
    return f"""\
  <section class="section">
    <h2 class="section-title">
      <span class="section-icon">🔭</span> Next Signals
    </h2>
    <ul class="signal-list">{items}</ul>
  </section>"""


def _render_source_diversity(dist: dict) -> str:
    if not dist:
        return ""

    total = sum(dist.values())
    bars = []
    for group in sorted(dist.keys()):
        count = dist[group]
        pct = count / total * 100 if total else 0
        label = SOURCE_GROUP_LABELS.get(group, group)
        color = {"S1": "#7c3aed", "S2": "#1a73e8", "S5": "#16a34a",
                 "S6": "#ea580c", "S7": "#0891b2"}.get(group, "#6b7280")
        bars.append(f"""\
      <div class="source-bar">
        <span class="source-label">{label}</span>
        <div class="bar-track">
          <div class="bar-fill" style="width: {pct}%; background: {color}"></div>
        </div>
        <span class="source-count">{count}건</span>
      </div>""")

    return f"""\
  <section class="section">
    <h2 class="section-title">
      <span class="section-icon">📰</span> 소스 분포
    </h2>
    <p class="source-total">총 {total}건</p>
    <div class="source-chart">
      {"".join(bars)}
    </div>
  </section>"""


# ═══════════════════════════════════════════════════════════════
# CSS — Base + Layout Variants + Card Styles + Pro Details
# ═══════════════════════════════════════════════════════════════

_CSS = """\
<style>
/* ─── Design Tokens ─── */
:root {
  --bg: var(--theme-bg, #f8f9fa);
  --surface: var(--theme-surface, #ffffff);
  --text: var(--theme-text, #1f2937);
  --text-secondary: var(--theme-text-secondary, #6b7280);
  --border: var(--theme-border, #e5e7eb);
  --accent: var(--theme-accent, #1a73e8);
  --accent-light: var(--theme-accent-light, #e8f0fe);
  --radius: 16px;
  --radius-sm: 10px;
  --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
  --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, 'Pretendard', 'Noto Sans KR', sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ─── Container ─── */
.container {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 16px;
}

/* ─── Header ─── */
.header {
  text-align: center;
  color: white;
  border-radius: var(--radius);
  padding: 32px 24px 24px;
  margin-bottom: 32px;
  position: relative;
  overflow: hidden;
}

.header::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 60%, rgba(0,0,0,0.15) 100%);
  pointer-events: none;
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
  position: relative;
  z-index: 1;
}

.logo {
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: white;
}

.date-badge {
  background: rgba(255,255,255,0.22);
  color: white;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  backdrop-filter: blur(4px);
}

.subtitle {
  color: rgba(255,255,255,0.8);
  font-size: 0.88rem;
  margin-top: 8px;
  position: relative;
  z-index: 1;
}

.header-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 12px;
  position: relative;
  z-index: 1;
}

.theme-badge {
  display: inline-block;
  padding: 3px 14px;
  border-radius: 12px;
  font-size: 0.72rem;
  font-weight: 700;
  background: rgba(255,255,255,0.25);
  color: white;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  backdrop-filter: blur(4px);
}

.reading-time {
  font-size: 0.72rem;
  color: rgba(255,255,255,0.7);
  font-weight: 500;
}

/* ─── Sections ─── */
.section {
  margin-bottom: 36px;
}

.section-title {
  font-size: 1.2rem;
  font-weight: 800;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text);
  letter-spacing: -0.3px;
}

.section-icon { font-size: 1.2rem; }

/* ─── Base Card ─── */
.card {
  background: var(--surface);
  border-radius: var(--radius);
  margin-bottom: 14px;
  overflow: hidden;
  transition: box-shadow var(--transition), transform var(--transition);
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.card-header {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.rank {
  font-size: 1.15rem;
  font-weight: 900;
  color: var(--accent, #1a73e8);
  min-width: 32px;
  opacity: 0.8;
}

.card-title-group { flex: 1; min-width: 0; }

.card-title {
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.45;
  color: var(--text);
}

.cat-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.72rem;
  font-weight: 700;
  margin-top: 4px;
  white-space: nowrap;
}

.chevron {
  font-size: 1rem;
  color: var(--text-secondary);
  transition: transform var(--transition);
  flex-shrink: 0;
}

.card.expanded .chevron { transform: rotate(180deg); }

/* ─── Card Body (accordion) ─── */
.card-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.35s ease, padding 0.35s ease;
  padding: 0 20px;
}

.card.expanded .card-body {
  max-height: 800px;
  padding: 0 20px 18px;
}

/* ─── Detail Rows ─── */
.detail-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  align-items: flex-start;
}

.detail-label {
  flex-shrink: 0;
  font-size: 0.7rem;
  font-weight: 800;
  padding: 2px 10px;
  border-radius: 6px;
  background: var(--accent-light);
  color: var(--accent);
  text-transform: uppercase;
  min-width: 54px;
  text-align: center;
  letter-spacing: 0.3px;
}

.detail-label.impact { background: #fef3c7; color: #b45309; }
.detail-label.risk { background: #fee2e2; color: #dc2626; }
.detail-label.next { background: #dbeafe; color: #2563eb; }

.detail-text {
  font-size: 0.88rem;
  color: var(--text);
  line-height: 1.55;
}

.sources {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.sources a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
}

.sources a:hover { text-decoration: underline; }

/* ─── Number Highlight ─── */
.num-hl {
  color: var(--accent);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

/* ─── Item Count ─── */
.item-count {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-left: auto;
  background: var(--border);
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 600;
}

/* ─── SK Section ─── */
.sk-section {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border-radius: var(--radius);
  padding: 24px;
}

.sk-headline {
  font-size: 1.05rem;
  font-weight: 800;
  color: #c2410c;
  margin-bottom: 16px;
  line-height: 1.5;
}

.lens-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.lens-card {
  background: white;
  border-radius: var(--radius-sm);
  padding: 16px;
  box-shadow: var(--shadow);
  transition: transform var(--transition);
}

.lens-card:hover { transform: translateY(-1px); }

.lens-label {
  font-size: 0.75rem;
  font-weight: 800;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.lens-text {
  font-size: 0.85rem;
  color: var(--text);
  line-height: 1.55;
}

/* ─── Category Cards ─── */
.cat-summary {
  font-size: 0.88rem;
  color: var(--text-secondary);
  margin-bottom: 12px;
  line-height: 1.55;
}

.cat-impact {
  font-size: 0.85rem;
  color: var(--text);
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #fef3c7;
  border-radius: 8px;
  line-height: 1.5;
}

.cat-impact .detail-label {
  margin-right: 6px;
  vertical-align: middle;
}

.cat-list {
  list-style: none;
  padding: 0;
}

.cat-list li {
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.88rem;
  line-height: 1.5;
}

.cat-list li:last-child { border-bottom: none; }

.cat-fact {
  color: var(--text-secondary);
  font-size: 0.82rem;
}

/* ─── Risks & Signals ─── */
.risk-list, .signal-list {
  list-style: none;
  padding: 0;
}

.risk-list li, .signal-list li {
  background: var(--surface);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  margin-bottom: 10px;
  font-size: 0.88rem;
  line-height: 1.55;
  box-shadow: var(--shadow);
  transition: transform var(--transition);
}

.risk-list li:hover, .signal-list li:hover {
  transform: translateX(4px);
}

.risk-list li { border-left: 4px solid #dc2626; }
.signal-list li { border-left: 4px solid #2563eb; }

/* ─── Source Chart ─── */
.source-total {
  font-size: 0.82rem;
  color: var(--text-secondary);
  margin-bottom: 12px;
  font-weight: 600;
}

.source-chart { padding: 4px 0; }

.source-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.source-label {
  font-size: 0.82rem;
  font-weight: 700;
  min-width: 80px;
  color: var(--text);
}

.bar-track {
  flex: 1;
  height: 10px;
  background: var(--border);
  border-radius: 5px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.source-count {
  font-size: 0.78rem;
  color: var(--text-secondary);
  min-width: 40px;
  text-align: right;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* ─── Footer ─── */
.footer {
  text-align: center;
  padding: 28px 0;
  color: var(--text-secondary);
  font-size: 0.75rem;
  border-top: 1px solid var(--border);
  margin-top: 16px;
}

.empty {
  color: var(--text-secondary);
  font-style: italic;
  padding: 16px;
}

/* ═══════════════════════════════════════════════════════════
   LAYOUT VARIANTS
   ═══════════════════════════════════════════════════════════ */

/* ─── Top5 Grid wrapper ─── */
.top5-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* ── Hero Layout: Top 1 대형 카드 ── */
.layout-hero .hero-card {
  border-left: none;
  border-radius: var(--radius);
  position: relative;
  overflow: hidden;
}

.layout-hero .hero-card .card-header {
  padding: 22px 24px;
}

.layout-hero .hero-card .rank {
  opacity: 1;
  background: var(--accent);
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
}

.layout-hero .hero-card .card-title {
  font-size: 1.15rem;
  font-weight: 800;
}

/* ── Grid Layout: 2열 그리드 ── */
.layout-grid .top5-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.layout-grid .top5-grid .hero-card {
  grid-column: 1 / -1;
}

/* ── Editorial Layout: 좌측 강조 ── */
.layout-editorial .header {
  text-align: left;
  border-radius: var(--radius);
}

.layout-editorial .header-top {
  justify-content: flex-start;
}

.layout-editorial .header-meta {
  justify-content: flex-start;
}

.layout-editorial .section-title {
  padding-bottom: 10px;
  border-bottom: 2px solid var(--accent);
  margin-bottom: 20px;
}

/* ═══════════════════════════════════════════════════════════
   CARD STYLE VARIANTS
   ═══════════════════════════════════════════════════════════ */

/* ── Elevated: 강한 그림자 + 왼쪽 보더 ── */
.cards-elevated .card {
  box-shadow: var(--shadow-md);
  border-left: 4px solid var(--accent, #e5e7eb);
}

.cards-elevated .card:hover {
  box-shadow: var(--shadow-lg);
}

/* ── Glass: 반투명 + backdrop blur ── */
.cards-glass .card {
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.4);
  border-left: 3px solid var(--accent, #e5e7eb);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

/* ── Flat: 최소 장식 ── */
.cards-flat .card {
  box-shadow: none;
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent, #e5e7eb);
}

.cards-flat .card:hover {
  box-shadow: none;
  transform: none;
  border-color: var(--accent);
}

/* ── Bordered: 깔끔한 보더 ── */
.cards-bordered .card {
  box-shadow: none;
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent, #e5e7eb);
}

.cards-bordered .card:hover {
  box-shadow: var(--shadow);
}

/* ── Editorial + Card Style 합성 (specificity 보장) ── */
.layout-editorial .card {
  border-left: none !important;
  border-right: none;
  border-top: 1px solid var(--border);
  border-bottom: none;
  border-radius: 0;
  box-shadow: none !important;
  margin-bottom: 0;
}

.layout-editorial .card:first-child {
  border-top: none;
}

.layout-editorial .card:hover {
  transform: none !important;
  background: var(--accent-light);
}

/* ═══════════════════════════════════════════════════════════
   DARK THEME
   ═══════════════════════════════════════════════════════════ */

.theme-dark {
  --bg: var(--theme-bg);
  --surface: var(--theme-surface);
  --text: var(--theme-text);
  --text-secondary: var(--theme-text-secondary);
  --border: var(--theme-border);
}

.theme-dark .sk-section {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
}

.theme-dark .sk-headline { color: #fb923c; }

.theme-dark .lens-card {
  background: #1e293b;
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}

.theme-dark .risk-list li,
.theme-dark .signal-list li {
  background: var(--surface);
}

.theme-dark .detail-label {
  background: rgba(56,189,248,0.15);
  color: #38bdf8;
}

.theme-dark .detail-label.impact {
  background: rgba(251,191,36,0.15);
  color: #fbbf24;
}

.theme-dark .detail-label.risk {
  background: rgba(248,113,113,0.15);
  color: #f87171;
}

.theme-dark .detail-label.next {
  background: rgba(96,165,250,0.15);
  color: #60a5fa;
}

.theme-dark .item-count {
  background: var(--border);
  color: var(--text-secondary);
}

.theme-dark .num-hl {
  color: #38bdf8;
}

.theme-dark.cards-glass .card {
  background: rgba(30,41,59,0.8);
  border-color: rgba(51,65,85,0.6);
}

/* ═══════════════════════════════════════════════════════════
   MOBILE RESPONSIVE
   ═══════════════════════════════════════════════════════════ */

@media (max-width: 600px) {
  .lens-grid { grid-template-columns: 1fr; }
  .layout-grid .top5-grid { grid-template-columns: 1fr; }
  .container { padding: 16px 12px; }
  .header { padding: 24px 16px 20px; margin-bottom: 24px; }
  .logo { font-size: 1.35rem; }
  .section { margin-bottom: 28px; }
}

@media (max-width: 480px) {
  .card-header { padding: 14px 16px; }
  .card.expanded .card-body { padding: 0 16px 14px; }
  .detail-row { flex-direction: column; gap: 4px; }
  .detail-label { align-self: flex-start; }
  .source-label { min-width: 60px; font-size: 0.75rem; }
  .risk-list li, .signal-list li { padding: 12px 14px; }
}

/* ─── Smooth scroll + selection ─── */
::selection {
  background: var(--accent-light);
  color: var(--text);
}

html { scroll-behavior: smooth; }
</style>"""
