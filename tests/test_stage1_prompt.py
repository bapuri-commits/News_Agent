"""Stage 1 프롬프트에 이전 Top5 주입 단위 테스트."""

from __future__ import annotations

import pytest

from src.briefer.prompts import build_stage1_prompt


SAMPLE_ARTICLES = [
    {
        "id": "art_001",
        "title": "Intel 18A 양산 시작",
        "source_name": "EE Times",
        "source_group": "S1",
        "categories": ["fab_capex"],
        "relevance_score": 0.85,
        "language": "en",
        "url": "https://eetimes.com/intel-18a",
    },
    {
        "id": "art_002",
        "title": "현대차 새만금 데이터센터 투자",
        "source_name": "조선일보",
        "source_group": "S7",
        "categories": ["dc_build"],
        "relevance_score": 0.70,
        "language": "ko",
        "url": "https://news.google.com/rss/123",
    },
]

SAMPLE_PROFILE = "- 핵심 관심사: 반도체(score:3)\n- 요약 언어: 한국어"


class TestBuildStage1Prompt:

    def test_no_previous_top5(self):
        result = build_stage1_prompt(SAMPLE_ARTICLES, SAMPLE_PROFILE)
        assert "## 독자 프로필 요약" in result
        assert "## 오늘의 기사 (2건)" in result
        assert "이전 Top 5" not in result

    def test_empty_previous_top5(self):
        result = build_stage1_prompt(SAMPLE_ARTICLES, SAMPLE_PROFILE, {})
        assert "이전 Top 5" not in result

    def test_previous_top5_injected(self):
        prev = {
            "2026-02-26": ["메타-AMD AI칩 계약", "SK에코플랜트 졸업"],
            "2026-02-25": ["신성이엔지 AIO 출시", "브이엠 장비 공급"],
        }
        result = build_stage1_prompt(SAMPLE_ARTICLES, SAMPLE_PROFILE, prev)

        assert "## 이전 Top 5 (중복 회피용)" in result
        assert "메타-AMD AI칩 계약" in result
        assert "SK에코플랜트 졸업" in result
        assert "신성이엔지 AIO 출시" in result
        assert "### 2026-02-26" in result
        assert "### 2026-02-25" in result

    def test_previous_top5_date_order(self):
        prev = {
            "2026-02-24": ["h_24"],
            "2026-02-26": ["h_26"],
            "2026-02-25": ["h_25"],
        }
        result = build_stage1_prompt(SAMPLE_ARTICLES, SAMPLE_PROFILE, prev)
        idx_26 = result.index("### 2026-02-26")
        idx_25 = result.index("### 2026-02-25")
        idx_24 = result.index("### 2026-02-24")
        assert idx_26 < idx_25 < idx_24

    def test_previous_top5_before_articles(self):
        prev = {"2026-02-26": ["headline"]}
        result = build_stage1_prompt(SAMPLE_ARTICLES, SAMPLE_PROFILE, prev)
        idx_prev = result.index("## 이전 Top 5")
        idx_articles = result.index("## 오늘의 기사")
        assert idx_prev < idx_articles

    def test_article_crawlable_flag(self):
        result = build_stage1_prompt(SAMPLE_ARTICLES, SAMPLE_PROFILE)
        assert "crawlable:yes" in result  # eetimes.com
        assert "crawlable:no" in result   # news.google.com

    def test_exclusion_instruction_in_prompt(self):
        prev = {"2026-02-26": ["some headline"]}
        result = build_stage1_prompt(SAMPLE_ARTICLES, SAMPLE_PROFILE, prev)
        assert "제외하세요" in result
        assert "후속 보도" in result
