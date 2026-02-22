"""RSS 피드 구독 및 파싱.

feedparser를 사용하여 전문매체 RSS 피드에서 기사를 수집한다.
피드별 마지막 수집 시점을 기록하여 중복 수집을 방지한다.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

from src.models.article import Article

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
USER_AGENT = (
    "NewsAgent/1.0 (+https://github.com/news-agent; family briefing bot)"
)


class RSSClient:
    """RSS 피드에서 기사를 수집하는 클라이언트."""

    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path
        self._state: dict[str, str] = {}
        if state_path and state_path.exists():
            with open(state_path, "r", encoding="utf-8") as f:
                self._state = json.load(f)

    def fetch_all(self, feeds: list[dict]) -> list[Article]:
        """모든 피드에서 기사를 수집한다."""
        all_articles: list[Article] = []
        for feed_info in feeds:
            name = feed_info["name"]
            url = feed_info["url"]
            source_group = feed_info.get("source_group", "S0")
            lang = feed_info.get("lang", "en")
            categories = feed_info.get("categories", [])
            since = self._state.get(url)

            logger.info("Fetching RSS: %s (%s)", name, url)
            try:
                articles = self.fetch_feed(
                    feed_url=url,
                    source_name=name,
                    source_group=source_group,
                    lang=lang,
                    categories=categories,
                    since=since,
                )
                all_articles.extend(articles)
                logger.info("  -> %d articles from %s", len(articles), name)

                self._state[url] = datetime.now(timezone.utc).isoformat()
            except Exception:
                logger.exception("  -> FAILED: %s", name)

        self._save_state()
        return all_articles

    def fetch_feed(
        self,
        feed_url: str,
        source_name: str = "",
        source_group: str = "S0",
        lang: str = "en",
        categories: list[str] | None = None,
        since: str | None = None,
    ) -> list[Article]:
        """단일 RSS 피드에서 기사를 수집한다."""
        raw_content = self._download_feed(feed_url)
        if raw_content is None:
            return []

        parsed = feedparser.parse(raw_content)
        if parsed.bozo and not parsed.entries:
            logger.warning("Feed parse error for %s: %s", feed_url, parsed.bozo_exception)
            return []

        since_dt = _parse_iso(since) if since else None
        articles: list[Article] = []

        for entry in parsed.entries:
            published = _extract_published(entry)
            if since_dt and published and published <= since_dt:
                continue

            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            snippet = _extract_snippet(entry)

            articles.append(Article(
                title=title,
                url=link,
                source_name=source_name or parsed.feed.get("title", ""),
                source_group=source_group,
                published_at=published.isoformat() if published else "",
                language=lang,
                snippet=snippet[:500],
                categories=list(categories or []),
            ))

        return articles

    def _download_feed(self, url: str) -> str | None:
        """HTTP로 피드 원문을 다운로드한다. 재시도 포함."""
        headers = {"User-Agent": USER_AGENT}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                logger.warning("RSS download attempt %d/%d failed for %s: %s",
                               attempt, MAX_RETRIES, url, e)
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
        return None

    def _save_state(self) -> None:
        if self.state_path:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)


def _parse_iso(iso_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return None


def _extract_published(entry: dict) -> datetime | None:
    """feedparser entry에서 발행 시각을 추출한다."""
    for key in ("published_parsed", "updated_parsed"):
        tp = entry.get(key)
        if tp:
            try:
                return datetime(*tp[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    for key in ("published", "updated"):
        raw = entry.get(key, "")
        if raw:
            dt = _parse_iso(raw)
            if dt:
                return dt
    return None


def _extract_snippet(entry: dict) -> str:
    """entry의 summary 또는 content에서 텍스트를 추출한다."""
    summary = entry.get("summary", "")
    if summary:
        return _strip_html(summary)

    content_list = entry.get("content", [])
    if content_list:
        return _strip_html(content_list[0].get("value", ""))

    return ""


def _strip_html(text: str) -> str:
    """간단한 HTML 태그 제거."""
    import re
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()
