"""_dedup_top5 Jaccard 기반 중복 제거 단위 테스트."""

from __future__ import annotations

import pytest

from src.briefer.briefing_generator import BriefingGenerator


def _make_articles(titles: list[str]) -> tuple[list[str], list[dict]]:
    articles = []
    ids = []
    for i, title in enumerate(titles):
        aid = f"art_{i:03d}"
        ids.append(aid)
        articles.append({"id": aid, "title": title})
    return ids, articles


class TestDedupTop5:

    def test_no_duplicates(self):
        ids, articles = _make_articles([
            "Intel 18A 양산 시작",
            "삼성전자 HBM4 엔비디아 출하",
            "현대차 새만금 데이터센터 투자",
        ])
        result = BriefingGenerator._dedup_top5(ids, articles)
        assert result == ids

    def test_identical_titles_removed(self):
        """2/22 실제 버그: 동일 헤드라인이 Top5에 2번 등장."""
        ids, articles = _make_articles([
            "최태원 HBM 마진 60%, 데이터센터에 원전급 전력 필요",
            "삼성전자 HBM4 엔비디아 출하",
            "최태원 HBM 마진 60%, 데이터센터에 원전급 전력 필요",
        ])
        result = BriefingGenerator._dedup_top5(ids, articles)
        assert len(result) == 2
        assert result == ["art_000", "art_001"]

    def test_similar_titles_removed(self):
        """살짝 다른 제목도 Jaccard로 잡아야 함."""
        ids, articles = _make_articles([
            "최태원 회장 HBM 마진 60% 공개, 대폭 증산 발표",
            "최태원 회장, HBM 대폭 증산 계획 발표, 마진율 60% 공개",
            "Intel 18A 양산 시작, 백사이드 전력공급 30% 개선",
        ])
        result = BriefingGenerator._dedup_top5(ids, articles)
        assert len(result) == 2
        assert "art_000" in result
        assert "art_002" in result

    def test_different_topics_kept(self):
        ids, articles = _make_articles([
            "메타-AMD 5년간 최대 85.9조원 AI칩 공급계약",
            "SK에코플랜트 반도체 전문 석사 3기 8명 배출",
            "폴란드 Bełchatów에 500MW 대형 DC 캠퍼스 계획",
            "데이터센터 프리팹 모듈 구축방식 백서 발간",
            "무디스 하이퍼스케일러 AI DC 단기계약 리스크 경고",
        ])
        result = BriefingGenerator._dedup_top5(ids, articles)
        assert len(result) == 5

    def test_missing_article_id_skipped(self):
        _, articles = _make_articles(["테스트 기사"])
        result = BriefingGenerator._dedup_top5(
            ["nonexistent_id", "art_000"], articles
        )
        assert result == ["art_000"]

    def test_empty_input(self):
        assert BriefingGenerator._dedup_top5([], []) == []

    def test_jaccard_threshold(self):
        """Jaccard 0.5 경계 테스트 — 공통 토큰이 절반 미만이면 통과."""
        ids, articles = _make_articles([
            "삼성전자 반도체 파운드리 매출 급증 전망",
            "삼성전자 갤럭시 스마트폰 시장 점유율 확대",
        ])
        result = BriefingGenerator._dedup_top5(ids, articles)
        assert len(result) == 2
