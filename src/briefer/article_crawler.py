"""기사 URL에서 본문 텍스트를 추출한다.

Top 5 + SK에코플랜트 관련 기사만 크롤링하고,
나머지는 기존 스니펫을 그대로 사용한다.
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from src.models.article import Article

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 12
MAX_RETRIES = 2
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
MAX_BODY_CHARS = 3000


def crawl_articles(articles: list[Article]) -> dict[str, str]:
    """기사 리스트의 본문을 크롤링하여 {article_id: full_text} 딕셔너리를 반환한다."""
    results: dict[str, str] = {}
    for article in articles:
        article_id = article.id
        url = resolve_google_news_url(article.url)

        if not url or _is_uncrawlable(url):
            results[article_id] = article.snippet
            logger.info("Crawl skip [%s]: uncrawlable domain", article_id)
            time.sleep(0.1)
            continue

        logger.info("Crawling [%s]: %s", article_id, url[:80])
        body = fetch_body(url)
        if body and len(body) > len(article.snippet):
            results[article_id] = body[:MAX_BODY_CHARS]
            logger.info("  -> %d chars", len(results[article_id]))
        else:
            results[article_id] = article.snippet
            logger.info("  -> fallback to snippet (%d chars)", len(article.snippet))

        time.sleep(0.3)

    return results


def fetch_body(url: str) -> str | None:
    """URL에서 기사 본문 텍스트를 추출한다."""
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True,
            )
            if resp.status_code != 200:
                logger.debug("HTTP %d for %s", resp.status_code, url[:60])
                return None
            return _extract_text(resp.text)
        except requests.RequestException as e:
            logger.debug("Crawl attempt %d failed for %s: %s", attempt, url[:60], e)
            if attempt < MAX_RETRIES:
                time.sleep(1)
        except Exception as e:
            logger.debug("Parse failed for %s: %s", url[:60], e)
            return None
    return None


def resolve_google_news_url(url: str) -> str:
    """Google News redirect URL을 실제 기사 URL로 변환한다.

    Strategy:
      1) googlenewsdecoder 라이브러리
      2) requests redirect 추적 (HEAD → GET 폴백)
      3) 원본 URL 반환 (최후 수단)
    """
    if not _is_google_news_url(url):
        return url

    decoded = _decode_via_library(url)
    if decoded:
        return decoded

    decoded = _resolve_via_redirect(url)
    if decoded:
        return decoded

    decoded = _resolve_via_playwright(url)
    if decoded:
        return decoded

    logger.warning("Google News URL decode failed, returning original: %s", url[:80])
    return url


def _decode_via_library(url: str) -> str | None:
    """googlenewsdecoder 라이브러리로 URL을 디코딩한다."""
    try:
        from googlenewsdecoder import gnewsdecoder

        result = gnewsdecoder(url, interval=0.5)
        if result and result.get("status"):
            decoded = result.get("decoded_url", "")
            if decoded and "news.google.com" not in decoded:
                logger.debug("Decoded via library: %s -> %s", url[:60], decoded[:80])
                return decoded
    except Exception as e:
        logger.debug("googlenewsdecoder failed for %s: %s", url[:60], e)
    return None


def _resolve_via_redirect(url: str) -> str | None:
    """HTTP redirect chain을 따라가 최종 URL을 추출한다."""
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(
            url, headers=headers, timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        final_url = resp.url
        if final_url and not _is_google_news_url(final_url):
            logger.debug("Resolved via redirect: %s -> %s", url[:60], final_url[:80])
            return final_url
    except requests.RequestException as e:
        logger.debug("Redirect resolve failed for %s: %s", url[:60], e)
    return None


def _resolve_via_playwright(url: str) -> str | None:
    """Playwright headless browser로 JS redirect를 따라가 실제 URL을 획득한다."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            final_url = page.url
            browser.close()

            if final_url and not _is_google_news_url(final_url):
                logger.info("Resolved via Playwright: %s -> %s", url[:60], final_url[:80])
                return final_url
    except Exception as e:
        logger.debug("Playwright resolve failed for %s: %s", url[:60], e)
    return None


def _is_google_news_url(url: str) -> bool:
    """Google News 도메인인지 확인한다 (지역 변형 포함)."""
    hostname = (urlparse(url).hostname or "").lower()
    return hostname.startswith("news.google.")


def _is_uncrawlable(url: str) -> bool:
    """크롤링 불가능한 도메인인지 확인한다."""
    hostname = (urlparse(url).hostname or "").lower()
    if hostname.startswith("news.google.") or hostname == "consent.google.com":
        return True
    return False


def _extract_text(html: str) -> str | None:
    """HTML에서 기사 본문 텍스트를 추출한다."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "iframe", "noscript", "form"]):
        tag.decompose()

    article_tag = soup.find("article")
    if article_tag:
        text = _clean_text(article_tag.get_text(separator="\n"))
        if len(text) > 200:
            return text

    for selector in [
        {"class": re.compile(r"article[_-]?(body|content|text)", re.I)},
        {"class": re.compile(r"post[_-]?(body|content)", re.I)},
        {"class": re.compile(r"entry[_-]?(content|body)", re.I)},
        {"id": re.compile(r"article[_-]?(body|content)", re.I)},
        {"class": "story-body"},
        {"class": "articleCont"},
        {"id": "articleBody"},
        {"id": "newsEndContents"},
        {"class": "news_cnt_detail_wrap"},
    ]:
        container = soup.find("div", selector)
        if container:
            text = _clean_text(container.get_text(separator="\n"))
            if len(text) > 200:
                return text

    paragraphs = soup.find_all("p")
    if paragraphs:
        texts = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 40]
        if texts:
            return _clean_text("\n".join(texts))

    return None


def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)
