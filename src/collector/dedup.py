"""제목/URL 기반 중복 제거.

- 완전 동일 URL 제거
- 제목 유사도(Jaccard 토큰 겹침) > 0.7이면 중복 판정
- 중복 시 relevance_score가 높은 쪽 유지
"""

from __future__ import annotations

import re
from src.models.article import Article

_TOKEN_RE = re.compile(r"[\w가-힣]+", re.UNICODE)

SOURCE_GROUP_RANK = {
    "S1": 3, "S2": 3, "S3": 4, "S4": 4,
    "S5": 3, "S6": 5, "S7": 3,
}


def deduplicate(articles: list[Article], similarity_threshold: float = 0.7) -> list[Article]:
    """기사 리스트에서 중복을 제거한다."""
    seen_urls: dict[str, int] = {}
    result: list[Article] = []
    title_tokens_list: list[set[str]] = []

    for article in articles:
        url_norm = _normalize_url(article.url)

        if url_norm in seen_urls:
            idx = seen_urls[url_norm]
            if _should_replace(result[idx], article):
                result[idx] = article
            continue

        tokens = _tokenize(article.title)
        dup_idx = _find_similar(tokens, title_tokens_list, similarity_threshold)

        if dup_idx is not None:
            if _should_replace(result[dup_idx], article):
                result[dup_idx] = article
                title_tokens_list[dup_idx] = tokens
            continue

        seen_urls[url_norm] = len(result)
        result.append(article)
        title_tokens_list.append(tokens)

    return result


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    url = re.sub(r"\?utm_[^&]*(&|$)", "", url)
    return url.lower()


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _find_similar(
    tokens: set[str],
    existing: list[set[str]],
    threshold: float,
) -> int | None:
    for i, existing_tokens in enumerate(existing):
        if _jaccard(tokens, existing_tokens) > threshold:
            return i
    return None


def _should_replace(existing: Article, candidate: Article) -> bool:
    """candidate가 기존 기사보다 나은지 판단한다."""
    if candidate.relevance_score > existing.relevance_score:
        return True
    e_rank = SOURCE_GROUP_RANK.get(existing.source_group, 1)
    c_rank = SOURCE_GROUP_RANK.get(candidate.source_group, 1)
    return c_rank > e_rank
