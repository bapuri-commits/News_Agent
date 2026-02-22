"""브리핑 JSON → 정적 HTML 렌더링 (Google Opal 스타일).

단일 HTML 파일로 생성 — CSS/JS 인라인 포함.
모바일 반응형, 카드 기반, 접이식 상세.
"""

from __future__ import annotations

import html

from src.briefer.constants import (
    CATEGORY_LABELS, CATEGORY_COLORS, SOURCE_GROUP_LABELS,
)
from src.briefer.themes import pick_theme as _pick_theme


def render_html(briefing: dict) -> str:
    """브리핑 JSON을 완전한 HTML 문자열로 렌더링한다."""
    date = html.escape(briefing.get("date", ""))
    generated = briefing.get("generated_at", "")
    theme = _pick_theme(briefing)

    top5_html = _render_top5(briefing.get("top5", []))
    sk_html = _render_sk_ecoplant(briefing.get("sk_ecoplant"))
    cat_html = _render_categories(briefing.get("by_category", {}))
    risks_html = _render_risks(briefing.get("risks", []))
    signals_html = _render_next_signals(briefing.get("next_signals", []))
    source_html = _render_source_diversity(briefing.get("source_diversity", {}))

    theme_css = (
        f":root {{\n"
        f"  --theme-bg: {theme['bg']};\n"
        f"  --theme-accent: {theme['accent']};\n"
        f"  --theme-accent-light: {theme['accent_light']};\n"
        f"}}"
    )
    theme_label = html.escape(theme.get("label", ""))
    header_gradient = theme["header_gradient"]

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
<div class="container">
  <header class="header" style="background: {header_gradient}; color: white; border-radius: var(--radius); padding: 28px 24px; margin-bottom: 24px;">
    <div class="header-top">
      <h1 class="logo" style="color: white;">Executive Briefing</h1>
      <span class="date-badge" style="background: rgba(255,255,255,0.25); color: white;">{date}</span>
    </div>
    <p class="subtitle" style="color: rgba(255,255,255,0.85);">건설 · 반도체 · 데이터센터 · 인프라</p>
    <span class="theme-badge">{theme_label}</span>
  </header>

  <section class="section">
    <h2 class="section-title">
      <span class="section-icon">⚡</span> Top 5
    </h2>
    {top5_html}
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


def _render_top5(items: list[dict]) -> str:
    if not items:
        return "<p class='empty'>수집된 Top 5 기사가 없습니다.</p>"

    cards = []
    for i, item in enumerate(items, 1):
        headline = html.escape(item.get("headline", item.get("title", "")))
        fact = html.escape(item.get("fact", ""))
        impact = html.escape(item.get("impact", ""))
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
            links = [f'<a href="{html.escape(s.get("url", ""))}" target="_blank">{html.escape(s.get("name", ""))}</a>' for s in sources]
            src_html = f'<div class="sources">{" · ".join(links)}</div>'

        detail_rows = []
        if fact:
            detail_rows.append(f'<div class="detail-row"><span class="detail-label">Fact</span><span class="detail-text">{fact}</span></div>')
        if impact:
            detail_rows.append(f'<div class="detail-row"><span class="detail-label impact">Impact</span><span class="detail-text">{impact}</span></div>')
        if risk and risk != "특이사항 없음":
            detail_rows.append(f'<div class="detail-row"><span class="detail-label risk">Risk</span><span class="detail-text">{risk}</span></div>')
        if next_sig:
            detail_rows.append(f'<div class="detail-row"><span class="detail-label next">Next</span><span class="detail-text">{next_sig}</span></div>')

        cards.append(f"""\
    <div class="card top5-card" style="--accent: {color}">
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


def _render_sk_ecoplant(sk: dict | None) -> str:
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
        value = html.escape(sk.get(key, "해당 기간 특이사항 없음"))
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


def _render_categories(categories: dict) -> str:
    if not categories:
        return "<p class='empty'>카테고리별 데이터가 없습니다.</p>"

    groups = []
    for cat_key, cat_data in categories.items():
        label = html.escape(CATEGORY_LABELS.get(cat_key, cat_key))
        color = CATEGORY_COLORS.get(cat_key, "#6b7280")
        summary = html.escape(cat_data.get("summary", ""))
        items = cat_data.get("items", [])

        item_rows = []
        for item in items:
            h = html.escape(item.get("headline", ""))
            f = html.escape(item.get("fact", ""))
            row = f'<li><strong>{h}</strong>'
            if f:
                row += f'<br><span class="cat-fact">{f}</span>'
            row += "</li>"
            item_rows.append(row)

        groups.append(f"""\
    <div class="card cat-card" style="--accent: {color}">
      <div class="card-header">
        <span class="cat-badge" style="background: {color}15; color: {color}">{label}</span>
        <span class="item-count">{len(items)}건</span>
        <span class="chevron">▾</span>
      </div>
      <div class="card-body">
        <p class="cat-summary">{summary}</p>
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
    <div class="source-chart">
      {"".join(bars)}
    </div>
  </section>"""


_CSS = """\
<style>
:root {
  --bg: var(--theme-bg, #f8f9fa);
  --surface: #ffffff;
  --text: #1f2937;
  --text-secondary: #6b7280;
  --border: #e5e7eb;
  --radius: 16px;
  --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
  --shadow-lg: 0 4px 12px rgba(0,0,0,0.1);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, 'Pretendard', 'Noto Sans KR', sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}

.container {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 16px;
}

.header {
  text-align: center;
  padding: 32px 0 24px;
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.date-badge {
  background: #1a73e8;
  color: white;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-top: 8px;
}

.theme-badge {
  display: inline-block;
  margin-top: 10px;
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 0.72rem;
  font-weight: 700;
  background: rgba(255,255,255,0.3);
  color: white;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-icon { font-size: 1.2rem; }

.card {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 12px;
  overflow: hidden;
  border-left: 3px solid var(--accent, #e5e7eb);
  transition: box-shadow 0.2s;
}

.card:hover { box-shadow: var(--shadow-lg); }

.card-header {
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.rank {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--accent, #1a73e8);
  min-width: 32px;
}

.card-title-group { flex: 1; }

.card-title {
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.4;
}

.cat-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-top: 4px;
  white-space: nowrap;
}

.chevron {
  font-size: 1rem;
  color: var(--text-secondary);
  transition: transform 0.2s;
}

.card.expanded .chevron { transform: rotate(180deg); }

.card-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease, padding 0.3s ease;
  padding: 0 18px;
}

.card.expanded .card-body {
  max-height: 600px;
  padding: 0 18px 16px;
}

.detail-row {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
  align-items: flex-start;
}

.detail-label {
  flex-shrink: 0;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: #e8f0fe;
  color: #1a73e8;
  text-transform: uppercase;
  min-width: 52px;
  text-align: center;
}

.detail-label.impact { background: #fef3c7; color: #b45309; }
.detail-label.risk { background: #fee2e2; color: #dc2626; }
.detail-label.next { background: #dbeafe; color: #2563eb; }

.detail-text {
  font-size: 0.88rem;
  color: var(--text);
  line-height: 1.5;
}

.sources {
  margin-top: 8px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.sources a {
  color: #1a73e8;
  text-decoration: none;
}

.sources a:hover { text-decoration: underline; }

.item-count {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-left: auto;
}

.sk-section {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border-radius: var(--radius);
  padding: 20px;
}

.sk-headline {
  font-size: 1.05rem;
  font-weight: 700;
  color: #c2410c;
  margin-bottom: 14px;
}

.lens-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

@media (max-width: 600px) {
  .lens-grid { grid-template-columns: 1fr; }
}

.lens-card {
  background: white;
  border-radius: 12px;
  padding: 14px;
  box-shadow: var(--shadow);
}

.lens-label {
  font-size: 0.78rem;
  font-weight: 700;
  margin-bottom: 6px;
  text-transform: uppercase;
}

.lens-text {
  font-size: 0.85rem;
  color: var(--text);
  line-height: 1.5;
}

.cat-summary {
  font-size: 0.88rem;
  color: var(--text-secondary);
  margin-bottom: 10px;
  line-height: 1.5;
}

.cat-list {
  list-style: none;
  padding: 0;
}

.cat-list li {
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.88rem;
}

.cat-list li:last-child { border-bottom: none; }

.cat-fact {
  color: var(--text-secondary);
  font-size: 0.82rem;
}

.risk-list, .signal-list {
  list-style: none;
  padding: 0;
}

.risk-list li, .signal-list li {
  background: var(--surface);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 8px;
  font-size: 0.88rem;
  box-shadow: var(--shadow);
}

.risk-list li { border-left: 3px solid #dc2626; }
.signal-list li { border-left: 3px solid #2563eb; }

.source-chart { padding: 4px 0; }

.source-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.source-label {
  font-size: 0.82rem;
  font-weight: 600;
  min-width: 80px;
}

.bar-track {
  flex: 1;
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.source-count {
  font-size: 0.8rem;
  color: var(--text-secondary);
  min-width: 40px;
  text-align: right;
}

.footer {
  text-align: center;
  padding: 20px 0;
  color: var(--text-secondary);
  font-size: 0.78rem;
}

.empty {
  color: var(--text-secondary);
  font-style: italic;
  padding: 16px;
}
</style>"""
