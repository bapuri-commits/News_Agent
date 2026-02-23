"""정적 사이트 빌더 — briefings/ → web/ 변환 오케스트레이터.

1. briefings/*.html + web/ 기존 HTML에서 전체 날짜 목록 추출 (정렬)
2. 새 브리핑만 nav 주입 후 web/에 추가 (기존 파일 보존)
3. 날짜 목록 변동 시 기존 파일의 nav도 갱신
4. index.html 생성 (날짜 목록 카드)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.deployer.nav_injector import inject_nav, strip_nav
from src.deployer.index_generator import generate_index
from src.deployer.text_page_generator import generate_text_page

logger = logging.getLogger("deploy")

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _scan_dates(*dirs: Path) -> list[str]:
    """여러 디렉토리에서 HTML 파일명 기반으로 날짜 목록을 추출한다(중복 제거)."""
    dates: set[str] = set()
    for d in dirs:
        if not d.exists():
            continue
        for html_file in d.glob("*.html"):
            stem = html_file.stem
            if _DATE_PATTERN.match(stem):
                dates.add(stem)
    return sorted(dates)


def build_site(briefings_dir: Path, output_dir: Path) -> None:
    """briefings/ 폴더의 새 HTML을 web/에 추가하고, 전체 인덱스와 nav를 갱신한다."""
    new_dates = _scan_dates(briefings_dir)
    if not new_dates:
        logger.warning("빌드할 HTML 브리핑이 없습니다: %s", briefings_dir)
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    for date in new_dates:
        src_path = briefings_dir / f"{date}.html"
        dst_path = output_dir / f"{date}.html"
        html_content = src_path.read_text(encoding="utf-8")
        dst_path.write_text(html_content, encoding="utf-8")

        md_path = briefings_dir / f"{date}.md"
        if md_path.exists():
            md_content = md_path.read_text(encoding="utf-8")
            text_dst = output_dir / f"{date}-text.html"
            generate_text_page(md_content, date, text_dst)
            logger.info("  텍스트 페이지 생성: %s", text_dst.name)

    all_dates = _scan_dates(output_dir)
    logger.info("전체 브리핑: %d건 (신규 %d건)", len(all_dates), len(new_dates))

    for i, date in enumerate(all_dates):
        prev_date = all_dates[i - 1] if i > 0 else None
        next_date = all_dates[i + 1] if i < len(all_dates) - 1 else None

        dst_path = output_dir / f"{date}.html"
        raw_html = strip_nav(dst_path.read_text(encoding="utf-8"))
        html_with_nav = inject_nav(raw_html, prev_date, next_date, date)
        dst_path.write_text(html_with_nav, encoding="utf-8")

    logger.info("  nav 주입 완료 (%d건)", len(all_dates))

    index_path = output_dir / "index.html"
    generate_index(briefings_dir, all_dates, index_path)
    logger.info("  index.html 생성 완료 (%d건)", len(all_dates))

    logger.info("빌드 완료: %s", output_dir)
