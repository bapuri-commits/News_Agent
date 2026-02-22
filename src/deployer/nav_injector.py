"""기존 브리핑 HTML에 날짜 네비게이션 바를 주입한다.

</header> 태그 뒤에 sticky nav 바를 삽입하여
이전/다음 날짜 이동 + 목록 링크를 제공한다.
"""

from __future__ import annotations

import html as html_mod
import re


_NAV_CSS = """\
<style>
.briefing-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  padding: 10px 16px;
  font-family: -apple-system, 'Pretendard', 'Noto Sans KR', sans-serif;
  font-size: 0.85rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.briefing-nav a,
.briefing-nav span {
  padding: 6px 14px;
  text-decoration: none;
  color: #1a73e8;
  font-weight: 600;
  border-radius: 8px;
  transition: background 0.15s;
  white-space: nowrap;
}
.briefing-nav a:hover {
  background: #e8f0fe;
}
.briefing-nav .nav-current {
  color: #1f2937;
  font-weight: 700;
}
.briefing-nav .nav-disabled {
  color: #d1d5db;
  pointer-events: none;
}
.briefing-nav .nav-sep {
  color: #e5e7eb;
  padding: 0 2px;
  user-select: none;
}
@media (max-width: 480px) {
  .briefing-nav { font-size: 0.78rem; gap: 0; padding: 8px 8px; }
  .briefing-nav a, .briefing-nav span { padding: 6px 8px; }
}
</style>"""


def inject_nav(
    html_content: str,
    prev_date: str | None,
    next_date: str | None,
    current_date: str,
) -> str:
    """기존 HTML의 </header> 뒤에 날짜 네비게이션 바를 삽입한다."""
    if prev_date:
        prev_link = f'<a href="{html_mod.escape(prev_date)}.html">\u2190 {html_mod.escape(prev_date)}</a>'
    else:
        prev_link = '<span class="nav-disabled">\u2190</span>'

    if next_date:
        next_link = f'<a href="{html_mod.escape(next_date)}.html">{html_mod.escape(next_date)} \u2192</a>'
    else:
        next_link = '<span class="nav-disabled">\u2192</span>'

    current_label = html_mod.escape(current_date)

    nav_html = (
        f'\n{_NAV_CSS}\n'
        f'<nav class="briefing-nav">'
        f'{prev_link}'
        f'<span class="nav-sep">|</span>'
        f'<span class="nav-current">{current_label}</span>'
        f'<span class="nav-sep">|</span>'
        f'{next_link}'
        f'<span class="nav-sep">|</span>'
        f'<a href="index.html">목록</a>'
        f'</nav>\n'
    )

    pattern = re.compile(r"</header>", re.IGNORECASE)
    match = pattern.search(html_content)

    if match:
        insert_pos = match.end()
        result = html_content[:insert_pos] + nav_html + html_content[insert_pos:]
    else:
        result = nav_html + html_content

    return result
