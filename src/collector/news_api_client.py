"""NewsAPI(newsapi.org) 또는 GNews를 통한 뉴스 검색 클라이언트.

API_KEY는 .env에서 로드 (NEWS_API_KEY).
키가 없으면 경고 로그만 남기고 빈 결과를 반환한다.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

import requests

from src.models.article import Article

logger = logging.getLogger(__name__)

NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
USER_AGENT = (
    "NewsAgent/1.0 (+https://github.com/news-agent; family briefing bot)"
)


class NewsAPIClient:
    """NewsAPI를 통한 뉴스 검색.

    - 일일 요청 제한 관리 (무료 100회/일)
    - 페이지네이션 처리
    - 결과를 Article 형태로 정규화
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("NEWS_API_KEY", "")
        self._request_count = 0

    def search(
        self,
        query: str,
        language: str = "en",
        from_date: str | None = None,
        to_date: str | None = None,
        page_size: int = 30,
        max_pages: int = 1,
        source_group: str = "S6",
        categories: list[str] | None = None,
    ) -> list[Article]:
        """키워드 쿼리로 뉴스를 검색하여 Article 리스트를 반환한다."""
        if not self.api_key:
            logger.warning("NEWS_API_KEY not set - skipping API search")
            return []

        articles: list[Article] = []
        for page in range(1, max_pages + 1):
            params = {
                "q": query,
                "language": language,
                "pageSize": page_size,
                "page": page,
                "sortBy": "publishedAt",
                "apiKey": self.api_key,
            }
            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date

            data = self._request(params)
            if data is None:
                break

            raw_articles = data.get("articles", [])
            if not raw_articles:
                break

            for raw in raw_articles:
                article = self._normalize(raw, source_group, language, categories)
                if article:
                    articles.append(article)

            total_results = data.get("totalResults", 0)
            if page * page_size >= total_results:
                break

        return articles

    def search_queries(
        self,
        queries: list[dict],
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[Article]:
        """query_builder가 생성한 쿼리 세트를 순회하며 수집한다."""
        all_articles: list[Article] = []
        for q in queries:
            for lang_key, lang_code in [("query_en", "en"), ("query_kr", "ko")]:
                query_str = q.get(lang_key, "")
                if not query_str:
                    continue

                logger.info("NewsAPI search [%s]: %s", q["category"], query_str[:80])
                results = self.search(
                    query=query_str,
                    language=lang_code,
                    from_date=from_date,
                    to_date=to_date,
                    categories=[q["category"]],
                )
                all_articles.extend(results)

        return all_articles

    def _request(self, params: dict) -> dict | None:
        """NewsAPI에 GET 요청을 보낸다. 재시도 포함."""
        headers = {"User-Agent": USER_AGENT}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._request_count += 1
                resp = requests.get(
                    NEWSAPI_BASE_URL,
                    params=params,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                if resp.status_code == 429:
                    logger.warning("NewsAPI rate limit hit — stopping")
                    return None
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                logger.warning(
                    "NewsAPI request attempt %d/%d failed: %s",
                    attempt, MAX_RETRIES, e,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
        return None

    @staticmethod
    def _normalize(
        raw: dict,
        source_group: str,
        language: str,
        categories: list[str] | None,
    ) -> Article | None:
        """NewsAPI 응답의 단일 기사를 Article로 변환한다."""
        title = (raw.get("title") or "").strip()
        url = (raw.get("url") or "").strip()
        if not title or not url:
            return None

        source_name = ""
        if raw.get("source"):
            source_name = raw["source"].get("name", "")

        published_at = raw.get("publishedAt", "")
        snippet = (raw.get("description") or raw.get("content") or "")[:500]

        return Article(
            title=title,
            url=url,
            source_name=source_name,
            source_group=source_group,
            published_at=published_at,
            language=language,
            snippet=snippet,
            categories=list(categories or []),
        )
