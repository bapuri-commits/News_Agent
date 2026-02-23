"""인덱스 페이지 생성 — 날짜별 브리핑 카드 목록.

Google Opal 스타일 유지, 모바일 반응형.
각 카드에 날짜, 테마 라벨, Top 1 헤드라인, SK에코플랜트 헤드라인 표시.
메타 캐시(index-meta.json)로 CI에서도 과거 카드 정보를 보존한다.
"""

from __future__ import annotations

import html
import json
import logging
from pathlib import Path

from src.briefer.themes import pick_theme

logger = logging.getLogger("deploy")


def _load_meta_cache(cache_path: Path) -> dict[str, dict]:
    """기존 메타 캐시를 로드한다. 없으면 빈 dict."""
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_meta_cache(cache_path: Path, cache: dict[str, dict]) -> None:
    """메타 캐시를 저장한다."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _load_briefing_meta(json_path: Path) -> dict | None:
    """JSON 브리핑에서 인덱스 카드에 필요한 메타 정보를 추출한다."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    date = data.get("date", json_path.stem)
    theme = pick_theme(data)
    top5 = data.get("top5", [])
    sk = data.get("sk_ecoplant")
    article_count = data.get("metadata", {}).get("total_articles", 0)

    return {
        "date": date,
        "theme_label": theme.get("label", ""),
        "theme_accent": theme.get("accent", "#1a73e8"),
        "theme_gradient": theme.get("header_gradient", ""),
        "top_headline": top5[0].get("headline", "") if top5 else "",
        "sk_headline": sk.get("headline", "") if sk else "",
        "article_count": article_count,
    }


def generate_index(briefings_dir: Path, dates: list[str], output_path: Path) -> None:
    """날짜 목록으로 인덱스 페이지를 생성한다. 메타 캐시를 활용하여 과거 카드 정보도 보존."""
    cache_path = output_path.parent / "index-meta.json"
    meta_cache = _load_meta_cache(cache_path)

    for date in dates:
        json_path = briefings_dir / f"{date}.json"
        fresh_meta = _load_briefing_meta(json_path)
        if fresh_meta:
            meta_cache[date] = fresh_meta

    _save_meta_cache(cache_path, meta_cache)
    logger.info("  메타 캐시 갱신: %d건 (%s)", len(meta_cache), cache_path.name)

    cards_html_parts = []

    for date in sorted(dates, reverse=True):
        meta = meta_cache.get(date)

        if meta:
            theme_label = html.escape(meta["theme_label"])
            accent = html.escape(meta["theme_accent"])
            top_hl = html.escape(meta["top_headline"])
            sk_hl = html.escape(meta["sk_headline"])
            date_esc = html.escape(meta["date"])
            article_count = meta.get("article_count", 0)
        else:
            theme_label = ""
            accent = "#1a73e8"
            top_hl = ""
            sk_hl = ""
            date_esc = html.escape(date)
            article_count = 0

        sk_row = ""
        if sk_hl:
            sk_row = f'<div class="idx-sk"><span class="idx-sk-tag">SK에코</span> {sk_hl}</div>'

        meta_badge = ""
        if article_count:
            meta_badge = f'<span class="idx-meta">{article_count}건</span>'

        cards_html_parts.append(f"""\
    <a href="{date_esc}.html" class="idx-card" style="--card-accent: {accent}">
      <div class="idx-card-top">
        <span class="idx-date">{date_esc}</span>
        <span class="idx-theme" style="background: {accent}20; color: {accent}">{theme_label}</span>
        {meta_badge}
      </div>
      <div class="idx-headline">{top_hl}</div>
      {sk_row}
    </a>""")

    cards_html = "\n".join(cards_html_parts) if cards_html_parts else '<p class="idx-empty">아직 생성된 브리핑이 없습니다.</p>'

    total_count = len(dates)

    page = f"""\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Executive Briefing Archive</title>
{_INDEX_CSS}
</head>
<body>
<div class="idx-container">
  <header class="idx-header">
    <h1 class="idx-logo">Executive Briefing</h1>
    <p class="idx-sub">건설 · 반도체 · 데이터센터 · 인프라</p>
    <span class="idx-count">{total_count}일분 브리핑</span>
  </header>
  <main class="idx-grid">
{cards_html}
  </main>
  <footer class="idx-footer">
    <p>News Agent — Executive Briefing Archive</p>
  </footer>
</div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)


_INDEX_CSS = """\
<style>
:root {
  --bg: #f8fafc;
  --surface: #ffffff;
  --text: #1f2937;
  --text-secondary: #6b7280;
  --border: #e5e7eb;
  --radius: 16px;
  --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
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
.idx-container {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 16px;
}
.idx-header {
  text-align: center;
  background: linear-gradient(135deg, #1e3a5f 0%, #1a73e8 50%, #3b82f6 100%);
  color: white;
  border-radius: var(--radius);
  padding: 36px 24px 32px;
  margin-bottom: 28px;
  box-shadow: var(--shadow-md);
}
.idx-logo {
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: -0.5px;
}
.idx-sub {
  margin-top: 8px;
  font-size: 0.88rem;
  color: rgba(255,255,255,0.8);
  letter-spacing: 0.5px;
}
.idx-count {
  display: inline-block;
  margin-top: 12px;
  background: rgba(255,255,255,0.2);
  padding: 3px 14px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.3px;
}
.idx-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.idx-card {
  display: block;
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 18px 20px;
  text-decoration: none;
  color: var(--text);
  border-left: 3px solid var(--card-accent, #1a73e8);
  transition: box-shadow var(--transition), transform var(--transition);
}
.idx-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
.idx-card-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.idx-date {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
}
.idx-theme {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 20px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.idx-meta {
  margin-left: auto;
  font-size: 0.72rem;
  color: var(--text-secondary);
  white-space: nowrap;
}
.idx-headline {
  font-size: 0.9rem;
  color: var(--text);
  line-height: 1.5;
  margin-bottom: 4px;
}
.idx-sk {
  font-size: 0.82rem;
  color: var(--text-secondary);
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.idx-sk-tag {
  display: inline-block;
  background: #fff7ed;
  color: #ea580c;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  flex-shrink: 0;
}
.idx-footer {
  text-align: center;
  padding: 28px 0 8px;
  color: var(--text-secondary);
  font-size: 0.75rem;
}
.idx-empty {
  text-align: center;
  color: var(--text-secondary);
  font-style: italic;
  padding: 40px 16px;
}
@media (max-width: 480px) {
  .idx-container { padding: 16px 12px; }
  .idx-card { padding: 14px 16px; }
  .idx-header { padding: 28px 16px 24px; }
  .idx-logo { font-size: 1.35rem; }
}
</style>"""
