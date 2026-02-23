"""MD 브리핑을 복사 가능한 HTML 텍스트 페이지로 변환한다.

카톡/이메일 전달용. "전체 복사" 버튼 + "웹 버전" 링크 포함.
"""

from __future__ import annotations

import html
from pathlib import Path


def generate_text_page(
    md_content: str,
    date: str,
    output_path: Path,
) -> None:
    """MD 텍스트를 복사 가능한 HTML 페이지로 생성한다."""
    escaped = html.escape(md_content)
    date_esc = html.escape(date)

    page = f"""\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Executive Briefing — {date_esc} (텍스트)</title>
{_TEXT_CSS}
</head>
<body>
<div class="txt-container">
  <header class="txt-header">
    <div class="txt-header-top">
      <a href="{date_esc}.html" class="txt-back">&larr; 웹 버전</a>
      <a href="index.html" class="txt-home">목록</a>
    </div>
    <h1 class="txt-title">텍스트 브리핑 — {date_esc}</h1>
    <p class="txt-desc">카톡 · 이메일 전달용 텍스트</p>
    <button class="txt-copy-btn" onclick="copyAll()">📋 전체 복사</button>
  </header>
  <pre class="txt-content" id="briefing-text">{escaped}</pre>
  <div class="txt-toast" id="toast">복사되었습니다</div>
</div>
<script>
function copyAll() {{
  var el = document.getElementById('briefing-text');
  navigator.clipboard.writeText(el.textContent).then(function() {{
    var toast = document.getElementById('toast');
    toast.classList.add('show');
    setTimeout(function() {{ toast.classList.remove('show'); }}, 2000);
  }});
}}
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)


_TEXT_CSS = """\
<style>
:root {
  --bg: #fafaf9;
  --surface: #ffffff;
  --text: #1c1917;
  --text-secondary: #78716c;
  --border: #e7e5e4;
  --accent: #1a73e8;
  --radius: 12px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, 'Pretendard', 'Noto Sans KR', sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
}
.txt-container {
  max-width: 720px;
  margin: 0 auto;
  padding: 16px;
}
.txt-header {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 20px 24px;
  margin-bottom: 16px;
  border: 1px solid var(--border);
}
.txt-header-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}
.txt-header-top a {
  color: var(--accent);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
}
.txt-header-top a:hover { text-decoration: underline; }
.txt-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 4px;
}
.txt-desc {
  font-size: 0.82rem;
  color: var(--text-secondary);
  margin-bottom: 14px;
}
.txt-copy-btn {
  display: inline-block;
  background: var(--accent);
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
}
.txt-copy-btn:hover { background: #1557b0; }
.txt-copy-btn:active { transform: scale(0.97); }
.txt-content {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 24px;
  font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
  font-size: 0.88rem;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: keep-all;
  overflow-x: auto;
  color: var(--text);
}
.txt-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  background: #1f2937;
  color: white;
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.3s, transform 0.3s;
  pointer-events: none;
}
.txt-toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
@media (max-width: 480px) {
  .txt-container { padding: 12px; }
  .txt-header { padding: 16px; }
  .txt-content { padding: 16px; font-size: 0.82rem; }
}
</style>"""
