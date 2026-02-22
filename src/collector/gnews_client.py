"""Google News RSS를 통한 키워드 뉴스 검색.

NewsAPI를 완전히 대체한다.
- 무료, API 키 불필요
- 키워드 쿼리 → Google News RSS → Article 리스트
- 한국어/영어 양방향 검색 지원
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import requests

from src.models.article import Article

logger = logging.getLogger(__name__)

GNEWS_RSS_BASE = "https://news.google.com/rss/search"
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

LANG_CONFIG = {
    "en": {"hl": "en", "gl": "US", "ceid": "US:en"},
    "ko": {"hl": "ko", "gl": "KR", "ceid": "KR:ko"},
}


class GNewsClient:
    """Google News RSS 기반 뉴스 검색 클라이언트."""

    def search(
        self,
        query: str,
        language: str = "en",
        source_group: str = "S6",
        categories: list[str] | None = None,
        max_results: int = 30,
        recent_days: int = 2,
    ) -> list[Article]:
        """키워드 쿼리로 Google News를 검색하여 Article 리스트를 반환한다."""
        lang_conf = LANG_CONFIG.get(language, LANG_CONFIG["en"])
        when_param = f"+when:{recent_days}d" if recent_days else ""
        url = (
            f"{GNEWS_RSS_BASE}?q={quote(query)}{when_param}"
            f"&hl={lang_conf['hl']}&gl={lang_conf['gl']}"
            f"&ceid={lang_conf['ceid']}"
        )

        raw = self._download(url)
        if raw is None:
            return []

        parsed = feedparser.parse(raw)
        if parsed.bozo and not parsed.entries:
            logger.warning("Google News parse error for query %r: %s",
                           query[:50], parsed.bozo_exception)
            return []

        articles: list[Article] = []
        for entry in parsed.entries[:max_results]:
            article = self._to_article(entry, language, source_group, categories)
            if article:
                articles.append(article)

        return articles

    def search_queries(self, queries: list[dict]) -> list[Article]:
        """query_builder가 생성한 쿼리 세트를 순회하며 수집한다."""
        all_articles: list[Article] = []
        seen_queries: set[str] = set()

        for q in queries:
            category = q["category"]
            cats = [category]

            for lang_key, lang_code in [("query_en", "en"), ("query_kr", "ko")]:
                query_str = q.get(lang_key, "")
                if not query_str or query_str in seen_queries:
                    continue
                seen_queries.add(query_str)

                src_group = "S7" if lang_code == "ko" else "S6"

                logger.info("GNews search [%s/%s]: %s",
                            category, lang_code, query_str[:80])
                results = self.search(
                    query=query_str,
                    language=lang_code,
                    source_group=src_group,
                    categories=cats,
                )
                all_articles.extend(results)
                logger.info("  -> %d articles", len(results))

                time.sleep(0.5)

        return all_articles

    def _download(self, url: str) -> str | None:
        headers = {"User-Agent": USER_AGENT}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                logger.warning("GNews download attempt %d/%d failed: %s",
                               attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
        return None

    @staticmethod
    def _to_article(
        entry: dict,
        language: str,
        source_group: str,
        categories: list[str] | None,
    ) -> Article | None:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            return None

        source_name = ""
        source = entry.get("source")
        if source:
            source_name = source.get("title", "")

        published_at = ""
        pp = entry.get("published_parsed")
        if pp:
            try:
                published_at = datetime(*pp[:6], tzinfo=timezone.utc).isoformat()
            except (TypeError, ValueError):
                pass

        snippet = _strip_html(entry.get("summary", ""))[:500]

        return Article(
            title=title,
            url=link,
            source_name=source_name,
            source_group=source_group,
            published_at=published_at,
            language=language,
            snippet=snippet,
            categories=list(categories or []),
        )


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()
