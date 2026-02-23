"""Phase 5: collector 모듈 테스트."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.models.article import Article
from src.collector.query_builder import build_queries, _extract_score3_categories
from src.collector.dedup import deduplicate
from src.collector.article_filter import score_article, filter_articles


SAMPLE_PROFILE_PATH = Path(__file__).parent.parent / "output" / "stable_profile.json"


def _load_profile() -> dict:
    if SAMPLE_PROFILE_PATH.exists():
        with open(SAMPLE_PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "top_priorities": [
            {"name": "반도체 Fab/CapEx", "score": 3, "source": "both"},
            {"name": "EPC/수주", "score": 3, "source": "both"},
            {"name": "SK에코플랜트", "score": 3, "source": "both"},
        ],
        "must_include_triggers": ["large_award", "refinance"],
        "avoid": ["biased", "no_source", "too_basic"],
        "industries": {"fab_capex": 3, "dc_build": 3, "dc_power": 3},
        "themes": {"epc_award": 3, "capex_guidance": 3, "esg_regulation": 3},
        "companies": {"sk_ecoplant": 3},
    }


def _make_article(**kwargs) -> Article:
    defaults = {
        "title": "Test Article",
        "url": "https://example.com/test",
        "source_name": "TestSource",
        "source_group": "S6",
        "published_at": "2026-02-22T00:00:00Z",
        "language": "en",
        "snippet": "Test snippet content",
    }
    defaults.update(kwargs)
    return Article(**defaults)


class TestArticleModel:
    def test_to_dict_roundtrip(self):
        article = _make_article(title="Roundtrip Test")
        d = article.to_dict()
        restored = Article.from_dict(d)
        assert restored.title == article.title
        assert restored.url == article.url
        assert restored.source_group == article.source_group

    def test_default_id_generated(self):
        a = _make_article()
        b = _make_article()
        assert a.id != b.id
        assert len(a.id) == 12


class TestQueryBuilder:
    def test_build_queries_returns_list(self):
        profile = _load_profile()
        queries = build_queries(profile)
        assert isinstance(queries, list)
        assert len(queries) > 0

    def test_sk_ecoplant_queries_always_included(self):
        profile = _load_profile()
        queries = build_queries(profile)
        categories = [q["category"] for q in queries]
        assert any("sk_ecoplant" in c for c in categories)

    def test_trigger_queries_included(self):
        profile = _load_profile()
        queries = build_queries(profile)
        modes = [q.get("mode") for q in queries]
        assert "trigger" in modes

    def test_each_query_has_en_and_kr(self):
        profile = _load_profile()
        queries = build_queries(profile)
        for q in queries:
            assert "query_en" in q
            assert "query_kr" in q
            assert q["query_en"]
            assert q["query_kr"]

    def test_extract_score3_categories(self):
        profile = _load_profile()
        cats = _extract_score3_categories(profile)
        assert "fab_capex" in cats
        assert "epc_award" in cats


class TestDedup:
    def test_exact_url_dedup(self):
        articles = [
            _make_article(title="A", url="https://example.com/1"),
            _make_article(title="B", url="https://example.com/1"),
        ]
        result = deduplicate(articles)
        assert len(result) == 1

    def test_similar_title_dedup(self):
        articles = [
            _make_article(
                title="TSMC Arizona Fab 2 Expansion on Track for 2027",
                url="https://a.com/1",
            ),
            _make_article(
                title="TSMC Arizona Fab 2 Expansion on Track for 2027 Update",
                url="https://b.com/2",
            ),
        ]
        result = deduplicate(articles)
        assert len(result) == 1

    def test_different_articles_kept(self):
        articles = [
            _make_article(title="TSMC fab expansion news", url="https://a.com/1"),
            _make_article(title="Samsung memory chip shortage", url="https://b.com/2"),
        ]
        result = deduplicate(articles)
        assert len(result) == 2

    def test_utm_params_normalized(self):
        articles = [
            _make_article(title="A", url="https://example.com/page?utm_source=twitter"),
            _make_article(title="B", url="https://example.com/page"),
        ]
        result = deduplicate(articles)
        assert len(result) == 1

    def test_s7_internal_same_press_release(self):
        """같은 보도자료를 다르게 쓴 S7 기사 → 1건으로 합침."""
        shared_snippet = (
            "SK하이닉스 HBM 생산량 올해 대폭 확대 계획 발표 "
            "반도체 메모리 시장 AI 수요 증가 대응 투자 확대"
        )
        articles = [
            _make_article(
                title="SK하이닉스 HBM 생산 확대 계획 발표",
                url="https://a.kr/1",
                source_group="S7",
                source_name="매일경제",
                snippet=shared_snippet + " 매일경제 취재 결과",
            ),
            _make_article(
                title="SK하이닉스 HBM 생산 대폭 확대 발표",
                url="https://b.kr/2",
                source_group="S7",
                source_name="한국경제",
                snippet=shared_snippet + " 한국경제 단독 보도",
            ),
        ]
        result = deduplicate(articles)
        assert len(result) == 1

    def test_s7_internal_keeps_different(self):
        """제목/스니펫이 완전히 다른 S7 기사는 유지."""
        articles = [
            _make_article(
                title="SK하이닉스 HBM 생산 증가 발표",
                url="https://a.kr/1",
                source_group="S7",
                snippet="SK하이닉스가 HBM 생산량을 늘린다",
            ),
            _make_article(
                title="삼성전자 갤럭시 신제품 출시 예정",
                url="https://b.kr/2",
                source_group="S7",
                snippet="삼성전자가 하반기 갤럭시 신제품을 출시한다",
            ),
        ]
        result = deduplicate(articles)
        assert len(result) == 2

    def test_s7_dedup_preserves_non_s7(self):
        """S7 내부 dedup이 S1/S2/S6 기사에 영향 주지 않음."""
        s1_article = _make_article(
            title="DatacenterDynamics exclusive report",
            url="https://dcd.com/1",
            source_group="S1",
        )
        s7_articles = [
            _make_article(
                title="SK하이닉스 HBM 생산 확대 발표",
                url="https://a.kr/1",
                source_group="S7",
                snippet="SK하이닉스가 HBM 생산량을 대폭 늘린다고 발표했다",
            ),
            _make_article(
                title="SK하이닉스 HBM 생산 증가 계획 공개",
                url="https://b.kr/2",
                source_group="S7",
                snippet="SK하이닉스가 HBM 생산량을 대폭 늘리겠다고 밝혔다",
            ),
        ]
        result = deduplicate([s1_article] + s7_articles)
        s1_count = sum(1 for a in result if a.source_group == "S1")
        assert s1_count == 1

    def test_s7_dedup_preserves_order(self):
        """S7 dedup 후에도 원래 기사 순서가 유지됨."""
        articles = [
            _make_article(title="First S6", url="https://s6.com/1", source_group="S6"),
            _make_article(title="First S7 unique", url="https://a.kr/1", source_group="S7",
                          snippet="완전히 다른 내용의 기사"),
            _make_article(title="Second S6", url="https://s6.com/2", source_group="S6"),
            _make_article(title="Second S7 unique", url="https://b.kr/2", source_group="S7",
                          snippet="또 다른 주제의 기사"),
        ]
        result = deduplicate(articles)
        assert len(result) == 4
        assert result[0].source_group == "S6"
        assert result[1].source_group == "S7"
        assert result[2].source_group == "S6"
        assert result[3].source_group == "S7"


class TestArticleFilter:
    def test_high_score_for_fab_article(self):
        profile = _load_profile()
        article = _make_article(
            title="TSMC fab expansion $40B capex announced",
            snippet="TSMC confirmed semiconductor plant expansion with major capex investment",
        )
        score = score_article(article, profile)
        assert score >= 0.3

    def test_sk_ecoplant_boost(self):
        profile = _load_profile()
        article = _make_article(
            title="SK에코플랜트 대형 수주 계약 체결",
            snippet="SK에코플랜트가 데이터센터 EPC 대형 수주를 체결했다",
        )
        score = score_article(article, profile)
        assert score >= 0.5

    def test_avoid_penalty(self):
        profile = _load_profile()
        clean_article = _make_article(
            title="TSMC fab expansion capex announced",
            snippet="semiconductor fab investment plan",
        )
        clean_score = score_article(clean_article, profile)

        penalized_article = _make_article(
            title="TSMC fab expansion capex announced",
            snippet="beginner editorial column about semiconductor fab basics",
        )
        penalized_score = score_article(penalized_article, profile)
        assert penalized_score < clean_score

    def test_filter_returns_max_count(self):
        profile = _load_profile()
        articles = [
            _make_article(
                title=f"TSMC fab news #{i}",
                url=f"https://example.com/{i}",
                snippet="semiconductor fab capex expansion",
            )
            for i in range(100)
        ]
        filtered = filter_articles(articles, profile, max_count=20)
        assert len(filtered) <= 20

    def test_source_rebalancing(self):
        profile = _load_profile()
        articles = [
            _make_article(
                title=f"Fab news #{i}",
                url=f"https://example.com/{i}",
                source_group="S7",
                snippet="반도체 팹 증설 투자",
            )
            for i in range(20)
        ] + [
            _make_article(
                title=f"DC news #{i}",
                url=f"https://other.com/{i}",
                source_group="S1",
                snippet="data center hyperscale campus",
            )
            for i in range(15)
        ] + [
            _make_article(
                title=f"EPC news #{i}",
                url=f"https://third.com/{i}",
                source_group="S6",
                snippet="EPC contract award semiconductor",
            )
            for i in range(10)
        ]
        filtered = filter_articles(articles, profile, max_count=20)
        s7_count = sum(1 for a in filtered if a.source_group == "S7")
        assert s7_count <= int(20 * 0.6)
