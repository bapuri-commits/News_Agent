"""MD 브리핑을 정제된 HTML 레퍼런스 페이지로 변환한다.

원본 소스를 잘 정리한 신뢰도 있는 자료 형태.
링크 클릭 가능, "전체 복사" 버튼 포함.
"""

from __future__ import annotations

import html
import re
from pathlib import Path


def generate_text_page(
    md_content: str,
    date: str,
    output_path: Path,
) -> None:
    """MD 텍스트를 정제된 HTML 레퍼런스 페이지로 생성한다."""
    body_html = _md_to_html(md_content)
    date_esc = html.escape(date)

    page = f"""\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Executive Briefing — {date_esc} (Reference)</title>
{_TEXT_CSS}
</head>
<body>
<div class="ref-container">
  <header class="ref-header">
    <div class="ref-nav-row">
      <a href="{date_esc}.html" class="ref-link">&larr; 카드 버전</a>
      <a href="index.html" class="ref-link">목록</a>
    </div>
    <h1 class="ref-title">Executive Briefing</h1>
    <p class="ref-date">{date_esc}</p>
    <button class="ref-copy-btn" onclick="copyAll()">전체 복사</button>
  </header>
  <article class="ref-body" id="briefing-body">
{body_html}
  </article>
  <div class="ref-toast" id="toast">클립보드에 복사되었습니다</div>
</div>
<script>
function copyAll() {{
  var el = document.getElementById('briefing-body');
  var text = el.innerText || el.textContent;
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(text).then(showToast).catch(fallbackCopy);
  }} else {{
    fallbackCopy();
  }}
  function fallbackCopy() {{
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try {{ document.execCommand('copy'); showToast(); }}
    catch(e) {{ alert('복사에 실패했습니다. 직접 텍스트를 선택해 복사해주세요.'); }}
    document.body.removeChild(ta);
  }}
  function showToast() {{
    var toast = document.getElementById('toast');
    toast.classList.add('show');
    setTimeout(function() {{ toast.classList.remove('show'); }}, 2000);
  }}
}}
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)


def _md_to_html(md: str) -> str:
    """간이 MD → HTML 변환. 외부 라이브러리 없이 핵심 문법만 처리."""
    lines = md.split("\n")
    result: list[str] = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append("")
            continue

        if stripped.startswith("# "):
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(f'<h1>{_inline(stripped[2:])}</h1>')
        elif stripped.startswith("## "):
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(f'<h2>{_inline(stripped[3:])}</h2>')
        elif stripped.startswith("### "):
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(f'<h3>{_inline(stripped[4:])}</h3>')
        elif stripped.startswith("> "):
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(f'<blockquote>{_inline(stripped[2:])}</blockquote>')
        elif stripped.startswith("- "):
            if not in_list:
                result.append("<ul>")
                in_list = True
            content = stripped[2:]
            bold_label = re.match(r"^\*\*(.+?)\*\*[:\s]*(.*)", content)
            if bold_label:
                label = bold_label.group(1)
                rest = bold_label.group(2)
                result.append(f'<li><strong>{html.escape(label)}</strong> {_inline(rest)}</li>')
            else:
                result.append(f"<li>{_inline(content)}</li>")
        elif stripped.startswith("---"):
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append("<hr>")
        else:
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(f"<p>{_inline(stripped)}</p>")

    if in_list:
        result.append("</ul>")

    return "\n".join(result)


_UNSAFE_SCHEMES = re.compile(r"^(javascript|data|vbscript):", re.IGNORECASE)


def _safe_link(match: re.Match) -> str:
    """링크 변환 시 위험한 URL 스킴을 차단한다."""
    label = match.group(1)
    url = match.group(2)
    if _UNSAFE_SCHEMES.match(url):
        return label
    return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'


def _inline(text: str) -> str:
    """인라인 MD 문법 처리: bold, italic, links, inline code."""
    text = html.escape(text)

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _safe_link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)

    return text


_TEXT_CSS = """\
<style>
:root {
  --bg: #fafaf9;
  --surface: #ffffff;
  --text: #1c1917;
  --text-secondary: #57534e;
  --border: #e7e5e4;
  --accent: #1a73e8;
  --radius: 12px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Pretendard', 'Noto Sans KR', -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.8;
  -webkit-font-smoothing: antialiased;
}
.ref-container {
  max-width: 680px;
  margin: 0 auto;
  padding: 20px 16px;
}
.ref-header {
  text-align: center;
  padding: 24px 20px 20px;
  margin-bottom: 24px;
  border-bottom: 2px solid var(--text);
}
.ref-nav-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
.ref-link {
  color: var(--accent);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
}
.ref-link:hover { text-decoration: underline; }
.ref-title {
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: -0.5px;
  margin-bottom: 4px;
}
.ref-date {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 16px;
}
.ref-copy-btn {
  display: inline-block;
  background: var(--text);
  color: var(--bg);
  border: none;
  padding: 8px 24px;
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  letter-spacing: 0.3px;
  transition: opacity 0.2s;
}
.ref-copy-btn:hover { opacity: 0.8; }
.ref-copy-btn:active { transform: scale(0.97); }

.ref-body {
  font-size: 0.92rem;
  line-height: 1.9;
}
.ref-body h1 {
  font-size: 1.2rem;
  font-weight: 800;
  margin: 32px 0 12px;
  padding-bottom: 6px;
  border-bottom: 2px solid var(--text);
}
.ref-body h2 {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 28px 0 10px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}
.ref-body h3 {
  font-size: 0.95rem;
  font-weight: 700;
  margin: 20px 0 8px;
  color: var(--text);
}
.ref-body p {
  margin: 8px 0;
}
.ref-body ul {
  margin: 8px 0;
  padding-left: 20px;
}
.ref-body li {
  margin: 6px 0;
}
.ref-body li strong {
  color: var(--text);
}
.ref-body blockquote {
  margin: 12px 0;
  padding: 10px 16px;
  border-left: 3px solid var(--border);
  color: var(--text-secondary);
  font-size: 0.88rem;
  background: #f5f5f4;
  border-radius: 0 6px 6px 0;
}
.ref-body hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 24px 0;
}
.ref-body a {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.15s;
}
.ref-body a:hover {
  border-bottom-color: var(--accent);
}
.ref-body strong {
  font-weight: 700;
}
.ref-body em {
  font-style: italic;
  color: var(--text-secondary);
}
.ref-body code {
  font-family: 'SF Mono', 'Fira Code', monospace;
  background: #f5f5f4;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.85em;
}
.ref-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  background: var(--text);
  color: var(--bg);
  padding: 10px 28px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.3s, transform 0.3s;
  pointer-events: none;
}
.ref-toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
@media (max-width: 480px) {
  .ref-container { padding: 12px; }
  .ref-header { padding: 16px 12px; }
  .ref-body { font-size: 0.88rem; }
}
</style>"""
