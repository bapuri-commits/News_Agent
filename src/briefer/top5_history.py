"""이전 날짜 Top5 헤드라인 영속화.

web/top5-history.json에 매일 Top5 헤드라인을 누적 저장한다.
GitHub Actions에서 git add web/ 시 자동으로 커밋되어 런 간 영속.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src import config

logger = logging.getLogger(__name__)


def load_history(path: Path | None = None) -> dict[str, list[str]]:
    """top5-history.json을 로드한다. 파일 없으면 빈 dict."""
    path = path or config.TOP5_HISTORY_PATH
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("top5-history.json 로드 실패: %s", e)
        return {}


def save_history(
    date: str,
    headlines: list[str],
    path: Path | None = None,
    max_days: int | None = None,
) -> None:
    """당일 Top5 헤드라인을 history에 추가하고 저장한다."""
    path = path or config.TOP5_HISTORY_PATH
    max_days = max_days or config.TOP5_HISTORY_DAYS

    history = load_history(path)
    history[date] = headlines

    sorted_dates = sorted(history.keys(), reverse=True)
    if len(sorted_dates) > max_days:
        for old_date in sorted_dates[max_days:]:
            del history[old_date]

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    logger.info("top5-history 저장: %s (%d일분)", date, len(history))


def get_recent_top5(
    exclude_date: str | None = None,
    max_days: int = 3,
    path: Path | None = None,
) -> dict[str, list[str]]:
    """최근 N일 Top5 헤드라인을 반환한다 (오늘 날짜 제외)."""
    history = load_history(path)
    sorted_dates = sorted(history.keys(), reverse=True)
    result: dict[str, list[str]] = {}
    for d in sorted_dates:
        if d == exclude_date:
            continue
        result[d] = history[d]
        if len(result) >= max_days:
            break
    return result
