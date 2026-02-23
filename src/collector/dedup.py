"""제목/URL 기반 중복 제거.

- 완전 동일 URL 제거
- 제목 유사도(Jaccard 토큰 겹침) > 0.7이면 중복 판정
- S7 내부 2차 중복 제거: 제목+스니펫 토큰, 임계값 0.45
- 중복 시 소스 랭크가 높은 쪽 유지 (점수 동점 시)
"""

from __future__ import annotations

import logging
import re
from src.models.article import Article

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[\w가-힣]+", re.UNICODE)

SOURCE_GROUP_RANK = {
    "S1": 6, "S2": 6, "S3": 5, "S4": 5,
    "S5": 6, "S6": 3, "S7": 4,
}

S7_INTERNAL_THRESHOLD = 0.45


def deduplicate(articles: list[Article], similarity_threshold: float = 0.7) -> list[Article]:
    """기사 리스트에서 중복을 제거한다.

    1차: 전체 대상, 제목 기반 Jaccard 0.7
    2차: S7 내부만, 제목+스니펫 기반 Jaccard 0.45 (같은 보도자료 재작성 포착)
    """
    result = _dedup_pass(articles, similarity_threshold)

    before_s7 = sum(1 for a in result if a.source_group == "S7")
    result = _dedup_s7_internal(result)
    after_s7 = sum(1 for a in result if a.source_group == "S7")

    if before_s7 != after_s7:
        logger.info("S7 internal dedup: %d -> %d (-%d)",
                     before_s7, after_s7, before_s7 - after_s7)

    return result


def _dedup_pass(
    articles: list[Article], similarity_threshold: float,
) -> list[Article]:
    """1차 중복 제거: URL + 제목 유사도."""
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


def _dedup_s7_internal(articles: list[Article]) -> list[Article]:
    """2차 중복 제거: S7 기사끼리 제목+스니펫 합산 토큰으로 비교.

    한국 매체들이 같은 보도자료를 살짝 다르게 쓰는 패턴을 잡기 위해
    더 낮은 임계값(0.45)과 넓은 텍스트(제목+스니펫)를 사용한다.
    """
    s7_articles: list[Article] = []
    non_s7: list[Article] = []

    for a in articles:
        if a.source_group == "S7":
            s7_articles.append(a)
        else:
            non_s7.append(a)

    if len(s7_articles) <= 1:
        return articles

    kept: list[Article] = []
    kept_tokens: list[set[str]] = []

    for article in s7_articles:
        tokens = _tokenize(f"{article.title} {article.snippet}")
        dup_idx = _find_similar(tokens, kept_tokens, S7_INTERNAL_THRESHOLD)

        if dup_idx is not None:
            if _should_replace(kept[dup_idx], article):
                kept[dup_idx] = article
                kept_tokens[dup_idx] = tokens
            continue

        kept.append(article)
        kept_tokens.append(tokens)

    return non_s7 + kept


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
    if candidate.relevance_score < existing.relevance_score:
        return False
    e_rank = SOURCE_GROUP_RANK.get(existing.source_group, 1)
    c_rank = SOURCE_GROUP_RANK.get(candidate.source_group, 1)
    return c_rank > e_rank
