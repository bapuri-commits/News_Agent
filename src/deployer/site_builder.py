"""정적 사이트 빌더 — briefings/ → web/ 변환 오케스트레이터.

1. briefings/*.html 스캔 → 날짜 목록 추출 (정렬)
2. 각 HTML에 이전/다음 날짜 네비게이션 바 주입
3. index.html 생성 (날짜 목록 카드)
4. web/ 폴더에 출력
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.deployer.nav_injector import inject_nav
from src.deployer.index_generator import generate_index

logger = logging.getLogger("deploy")

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _scan_dates(briefings_dir: Path) -> list[str]:
    """briefings/ 폴더에서 HTML 파일명 기반으로 날짜 목록을 추출한다."""
    dates = []
    for html_file in briefings_dir.glob("*.html"):
        stem = html_file.stem
        if _DATE_PATTERN.match(stem):
            dates.append(stem)
    return sorted(dates)


def build_site(briefings_dir: Path, output_dir: Path) -> None:
    """briefings/ 폴더의 HTML을 web/ 폴더로 빌드한다."""
    dates = _scan_dates(briefings_dir)
    if not dates:
        logger.warning("빌드할 HTML 브리핑이 없습니다: %s", briefings_dir)
        return

    logger.info("발견된 브리핑: %d건 (%s ~ %s)", len(dates), dates[0], dates[-1])

    if output_dir.exists():
        for old_file in output_dir.glob("*.html"):
            old_file.unlink()

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, date in enumerate(dates):
        prev_date = dates[i - 1] if i > 0 else None
        next_date = dates[i + 1] if i < len(dates) - 1 else None

        src_path = briefings_dir / f"{date}.html"
        html_content = src_path.read_text(encoding="utf-8")

        html_with_nav = inject_nav(html_content, prev_date, next_date, date)

        dst_path = output_dir / f"{date}.html"
        dst_path.write_text(html_with_nav, encoding="utf-8")
        logger.info("  [%d/%d] %s.html → nav 주입 완료", i + 1, len(dates), date)

    index_path = output_dir / "index.html"
    generate_index(briefings_dir, dates, index_path)
    logger.info("  index.html 생성 완료 (%d건)", len(dates))

    logger.info("빌드 완료: %s", output_dir)
