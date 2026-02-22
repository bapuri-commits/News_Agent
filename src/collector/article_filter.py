"""프로필 기반 기사 관련도 스코어링 및 필터링.

스코어링 규칙:
- top_priorities score 3 키워드 매치: +0.3
- score 2 키워드 매치: +0.1
- SK에코플랜트 직접 언급: +0.5
- must_include_triggers 매치: +0.5 (무조건 포함)
- avoid 항목 해당: -0.5
- 소스 다양성 보너스: 미출현 소스군에서 오면 +0.1
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone, timedelta

from src.models.article import Article

_SK_ECOPLANT_PATTERNS = re.compile(
    r"SK\s*에코플랜트|SK\s*ecoplant|sk\s*ecoplant", re.IGNORECASE
)

MAX_SOURCE_GROUP_RATIO = 0.4


MAX_ARTICLE_AGE_DAYS = 3


def score_article(article: Article, profile: dict) -> float:
    """기사를 프로필 기준으로 관련도 스코어링한다 (0.0 ~ 1.0)."""
    score = 0.0
    text = f"{article.title} {article.snippet}".lower()

    score += _score_priorities(text, profile)
    score += _score_sk_ecoplant(text)
    score += _score_triggers(text, profile)
    score += _score_avoid(text, profile)
    score += _score_freshness(article)

    return max(0.0, min(1.0, score))


def filter_articles(
    articles: list[Article],
    profile: dict,
    max_count: int = 50,
) -> list[Article]:
    """스코어링 후 상위 max_count개를 선별한다."""
    for article in articles:
        article.relevance_score = score_article(article, profile)
        article.categories = _match_categories(article, profile)

    must_include = _extract_must_include(articles, profile)

    scored = sorted(articles, key=lambda a: a.relevance_score, reverse=True)

    selected: list[Article] = list(must_include)
    selected_urls = {a.url for a in selected}

    for article in scored:
        if article.url in selected_urls:
            continue
        if article.relevance_score < 0.1:
            continue
        selected.append(article)
        selected_urls.add(article.url)
        if len(selected) >= max_count:
            break

    selected = _ensure_source_minimum(selected, scored, max_count)
    selected = _rebalance_sources(selected, max_count)

    return selected


def _score_priorities(text: str, profile: dict) -> float:
    """top_priorities 키워드 매칭 점수."""
    score = 0.0
    for item in profile.get("top_priorities", []):
        name = item.get("name", "").lower()
        item_score = item.get("score", 0)
        keywords = _name_to_keywords(name)

        if any(kw in text for kw in keywords):
            if item_score >= 3:
                score += 0.3
            elif item_score >= 2:
                score += 0.1

    return min(score, 0.8)


def _score_sk_ecoplant(text: str) -> float:
    if _SK_ECOPLANT_PATTERNS.search(text):
        return 0.5
    return 0.0


def _score_triggers(text: str, profile: dict) -> float:
    """must_include_triggers 매칭."""
    triggers = profile.get("must_include_triggers", [])
    trigger_keywords = {
        "large_award": ["대형 수주", "mega contract", "large award", "대규모 계약"],
        "refinance": ["차환", "리파이낸싱", "refinanc", "차입금"],
    }
    for trigger in triggers:
        keywords = trigger_keywords.get(trigger, [trigger])
        if any(kw in text for kw in keywords):
            return 0.5
    return 0.0


def _score_avoid(text: str, profile: dict) -> float:
    avoid_items = profile.get("avoid", [])
    avoid_keywords = {
        "biased": ["opinion", "editorial", "사설", "칼럼"],
        "no_source": ["unverified", "미확인", "루머"],
        "too_basic": ["beginner", "입문", "기초 강좌"],
    }
    for item in avoid_items:
        keywords = avoid_keywords.get(item, [item])
        if any(kw in text for kw in keywords):
            return -0.5
    return 0.0


def _score_freshness(article: Article) -> float:
    """최근 기사에 보너스, 오래된 기사에 패널티."""
    if not article.published_at:
        return 0.0
    try:
        pub = datetime.fromisoformat(article.published_at)
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - pub
        if age.days <= 1:
            return 0.15
        if age.days <= MAX_ARTICLE_AGE_DAYS:
            return 0.0
        return -0.4
    except (ValueError, TypeError):
        return 0.0


def _extract_must_include(articles: list[Article], profile: dict) -> list[Article]:
    """must_include_triggers에 해당하는 기사는 무조건 포함."""
    must = []
    for article in articles:
        text = f"{article.title} {article.snippet}".lower()
        if _SK_ECOPLANT_PATTERNS.search(text):
            must.append(article)
            continue
        if _score_triggers(text, profile) > 0:
            must.append(article)
    return must


def _match_categories(article: Article, profile: dict) -> list[str]:
    """기사에 매칭되는 프로필 카테고리를 반환한다."""
    text = f"{article.title} {article.snippet}".lower()
    matched = set(article.categories)

    for key, score in profile.get("industries", {}).items():
        keywords = _name_to_keywords(key)
        if any(kw in text for kw in keywords):
            matched.add(key)

    for key, score in profile.get("themes", {}).items():
        keywords = _name_to_keywords(key)
        if any(kw in text for kw in keywords):
            matched.add(key)

    return list(matched)


MINORITY_GROUPS = {"S1", "S2", "S5"}
MINORITY_MIN = 1


def _ensure_source_minimum(
    selected: list[Article],
    all_scored: list[Article],
    max_count: int,
) -> list[Article]:
    """전문매체(S1/S2/S5)가 선택에 없으면 최소 1건씩 넣어준다."""
    selected_urls = {a.url for a in selected}
    present_groups = {a.source_group for a in selected}

    for group in MINORITY_GROUPS:
        if group in present_groups:
            continue
        candidates = [
            a for a in all_scored
            if a.source_group == group
            and a.url not in selected_urls
            and a.relevance_score >= 0
        ]
        for cand in candidates[:MINORITY_MIN]:
            if len(selected) < max_count:
                selected.append(cand)
                selected_urls.add(cand.url)

    return selected


def _rebalance_sources(articles: list[Article], max_count: int) -> list[Article]:
    """단일 소스군이 전체의 40%를 초과하지 않도록 리밸런싱한다."""
    if not articles:
        return articles

    soft_cap = max(int(max_count * MAX_SOURCE_GROUP_RATIO), 3)
    hard_cap = max(int(max_count * 0.6), soft_cap + 1)

    group_counts: Counter[str] = Counter()
    result: list[Article] = []
    overflow: list[Article] = []

    for article in articles:
        group = article.source_group
        if group_counts[group] < soft_cap:
            result.append(article)
            group_counts[group] += 1
        else:
            overflow.append(article)

    if len(result) < max_count and overflow:
        overflow.sort(key=lambda a: group_counts[a.source_group])
        for article in overflow:
            if len(result) >= max_count:
                break
            group = article.source_group
            if group_counts[group] < hard_cap:
                result.append(article)
                group_counts[group] += 1

    return result[:max_count]


_KEYWORD_MAP: dict[str, list[str]] = {
    "fab_capex": ["fab", "팹", "반도체", "semiconductor", "capex", "증설"],
    "cleanroom": ["클린룸", "cleanroom", "clean room"],
    "equipment_supply": ["장비", "equipment", "asml", "amat", "lam"],
    "packaging": ["패키징", "packaging", "hbm", "cowos"],
    "memory_foundry": ["메모리", "파운드리", "memory", "foundry"],
    "dc_build": ["데이터센터", "data center", "hyperscale", "하이퍼스케일"],
    "dc_power": ["전력", "power", "변전", "substation", "grid"],
    "dc_cooling": ["냉각", "cooling", "액침", "immersion", "수랭"],
    "epc_award": ["epc", "수주", "계약", "contract", "award"],
    "schedule_cost": ["공기", "원가", "schedule", "cost", "delay"],
    "permit": ["인허가", "permit", "zoning"],
    "material_labor": ["자재", "노무", "material", "labor"],
    "milestone": ["마일스톤", "milestone", "준공", "착공"],
    "capex_guidance": ["capex", "투자 전망", "guidance", "실적"],
    "pf_finance": ["프로젝트 파이낸스", "project finance", "pf", "리파이낸싱"],
    "ma_restructure": ["m&a", "인수", "매각", "acquisition"],
    "esg_regulation": ["esg", "탄소", "carbon", "배출권"],
    "construction_tech": ["모듈러", "modular", "dfma", "프리팹"],
    "talent_hr": ["인력", "인사", "talent", "hr", "채용"],
    "urban_smartcity": ["스마트시티", "smart city", "도시개발", "neom"],
    "contingent": ["우발채무", "contingent", "자금보충"],
    "sk_ecoplant_order": ["sk에코플랜트", "sk ecoplant"],
    "infra_equip": ["schneider", "vertiv", "인프라장비"],
}


def _name_to_keywords(name: str) -> list[str]:
    name_lower = name.lower().replace("/", "_").replace(" ", "_")
    if name_lower in _KEYWORD_MAP:
        return _KEYWORD_MAP[name_lower]
    parts = re.split(r"[/_\s()+]", name.lower())
    return [p for p in parts if len(p) >= 2]
