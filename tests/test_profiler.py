"""Phase 4 Profile Builder 테스트."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.profiler.survey_loader import load_survey
from src.profiler.profile_builder import build_profile, _aggregate_export


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SURVEY = {
    "basic": {
        "purpose": "all",
        "reading_time": "20min",
        "schedule": "early_morning_5_6",
        "weekend": True,
        "format": "리스트",
        "language": "summary_kr",
        "paywall": False,
    },
    "industries": {
        "fab_capex": 3,
        "cleanroom": 3,
        "dc_build": 3,
        "urban_smartcity": 3,
        "carbon_esg": 2,
    },
    "themes": {
        "epc_award": 3,
        "schedule_cost": 3,
        "ma_restructure": 3,
        "esg_regulation": 3,
        "talent_hr": 3,
    },
    "companies": {
        "sk_ecoplant": 3,
        "sk_group": 3,
        "infra_equip": 3,
    },
    "regions": ["korea", "us", "asia"],
    "triggers": ["large_award", "refinance"],
    "sk_lens": ["order_mix", "cashflow"],
    "avoid_style": ["too_basic", "biased"],
}


def _make_summary(
    conv_id: str = "test-001",
    topics: list[str] | None = None,
    entities: list[str] | None = None,
    formats: list[str] | None = None,
    avoid: list[str] | None = None,
    decision_lens: list[str] | None = None,
    confidence: float = 0.7,
    km_industries: dict | None = None,
    km_entities: list[str] | None = None,
    km_themes: list[str] | None = None,
) -> dict:
    return {
        "conversation_id": conv_id,
        "title": f"Test Conv {conv_id}",
        "time_range": {"start": "2025-04-01T00:00:00+00:00", "end": "2025-04-01T01:00:00+00:00"},
        "business_relevant": True,
        "relevance_category": "technology",
        "signals": {
            "topics_top": topics or ["반도체"],
            "entities_top": entities or ["SK하이닉스"],
            "preferred_format": formats or ["표"],
            "avoid": avoid or [],
            "decision_lens": decision_lens or ["기술 트렌드"],
            "confidence": confidence,
        },
        "keyword_matches": {
            "industries": km_industries or {"반도체": 3},
            "entities": km_entities or ["SK하이닉스"],
            "themes": km_themes or ["CapEx"],
        },
        "evidence_refs": [{"msg_index": 0, "quote": "test quote"}],
    }


# ---------------------------------------------------------------------------
# Tests: survey_loader
# ---------------------------------------------------------------------------

class TestSurveyLoader:
    def test_load_valid_json(self, tmp_path: Path) -> None:
        data = {"basic": {"format": "리스트"}, "industries": {"fab_capex": 3}}
        p = tmp_path / "survey.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        result = load_survey(p)
        assert result == data

    def test_load_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_survey(tmp_path / "nonexistent.json")

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_survey(p)


# ---------------------------------------------------------------------------
# Tests: _aggregate_export
# ---------------------------------------------------------------------------

class TestAggregateExport:
    def test_industry_counts_per_conversation(self) -> None:
        """industry_freq는 키워드 빈도가 아니라 대화 건수로 카운팅"""
        summaries = [
            _make_summary("001", km_industries={"반도체": 5}),
            _make_summary("002", km_industries={"반도체": 3, "데이터센터": 2}),
        ]
        agg = _aggregate_export(summaries)
        assert agg["industry_freq"]["fab_capex"] == 2  # 2개 대화 (빈도합 8이 아님)
        assert agg["industry_freq"]["dc_build"] == 1   # 1개 대화
        assert agg["conversation_count"] == 2

    def test_topic_counting(self) -> None:
        summaries = [
            _make_summary("001", topics=["반도체", "HBM"]),
            _make_summary("002", topics=["반도체", "DC"]),
        ]
        agg = _aggregate_export(summaries)
        assert agg["topics_freq"]["반도체"] == 2

    def test_dedup_within_conversation(self) -> None:
        """같은 대화 내 같은 mapped key는 1회만 카운팅"""
        summaries = [
            _make_summary("001", km_themes=["수주", "EPC"]),  # 둘 다 epc_award로 매핑
        ]
        agg = _aggregate_export(summaries)
        assert agg["theme_freq"]["epc_award"] == 1  # 대화당 1회

    def test_entity_case_insensitive(self) -> None:
        """대소문자 변형도 매핑"""
        summaries = [
            _make_summary("001", km_entities=["NVIDIA"]),
            _make_summary("002", km_entities=["nvidia"]),
        ]
        agg = _aggregate_export(summaries)
        assert agg["entity_company_freq"]["hyperscalers"] == 2

    def test_format_union(self) -> None:
        summaries = [
            _make_summary("001", formats=["표", "리스트"]),
            _make_summary("002", formats=["비교분석"]),
        ]
        agg = _aggregate_export(summaries)
        assert agg["format_set"] == {"표", "리스트", "비교분석"}

    def test_high_confidence_evidence(self) -> None:
        summaries = [
            _make_summary("001", confidence=0.9),
            _make_summary("002", confidence=0.5),
        ]
        agg = _aggregate_export(summaries)
        assert len(agg["high_confidence_evidence"]) == 1
        assert agg["high_confidence_evidence"][0]["conversation_id"] == "001"

    def test_empty_summaries(self) -> None:
        agg = _aggregate_export([])
        assert agg["conversation_count"] == 0
        assert len(agg["topics_freq"]) == 0


# ---------------------------------------------------------------------------
# Tests: build_profile
# ---------------------------------------------------------------------------

class TestBuildProfile:
    def _summaries_with_export_data(self) -> list[dict]:
        return [
            _make_summary(
                "001",
                km_industries={"반도체": 5},
                km_entities=["SK하이닉스", "SK ecoplant"],
                km_themes=["CapEx", "수주"],
            ),
            _make_summary(
                "002",
                km_industries={"반도체": 3, "데이터센터": 4},
                km_entities=["SK하이닉스", "현대건설"],
                km_themes=["M&A", "경영진 인사"],
            ),
            _make_summary(
                "003",
                km_industries={"건설수주": 3},
                km_entities=["SK에코플랜트", "삼성물산"],
                km_themes=["수주", "EPC"],
            ),
        ]

    def test_profile_type(self) -> None:
        summaries = self._summaries_with_export_data()
        profile = build_profile(summaries, SAMPLE_SURVEY)
        from src.models.summary import StableProfile
        assert isinstance(profile, StableProfile)

    def test_user_intent(self) -> None:
        profile = build_profile(self._summaries_with_export_data(), SAMPLE_SURVEY)
        assert "8am every day" in profile.user_intent

    def test_survey_3_export_strong_is_both(self) -> None:
        """설문 3점 + export 빈출 → source: 'both'"""
        summaries = self._summaries_with_export_data()
        profile = build_profile(summaries, SAMPLE_SURVEY)
        fab = next((p for p in profile.top_priorities if p["name"] == "반도체 Fab/CapEx"), None)
        assert fab is not None
        assert fab["source"] == "both"
        assert fab["score"] == 3

    def test_survey_3_export_weak_has_open_question(self) -> None:
        """설문 3점 + export 약함 → open_questions에 기록"""
        summaries = self._summaries_with_export_data()
        profile = build_profile(summaries, SAMPLE_SURVEY)
        smartcity = next(
            (p for p in profile.top_priorities if "스마트시티" in p["name"]), None
        )
        assert smartcity is not None
        assert smartcity["source"] == "survey"
        oq_match = [q for q in profile.open_questions if "스마트시티" in q]
        assert len(oq_match) >= 1

    def test_survey_2_export_strong_upgraded(self) -> None:
        """설문 2점 + export 빈출 → score 3으로 격상"""
        survey = {**SAMPLE_SURVEY, "industries": {**SAMPLE_SURVEY["industries"], "carbon_esg": 2}}
        summaries = [
            _make_summary("001", km_themes=["ESG", "ESG", "ESG"]),
            _make_summary("002", km_themes=["ESG"]),
            _make_summary("003", km_themes=["탄소규제", "탄소규제"]),
        ]
        profile = build_profile(summaries, survey)
        # esg_regulation이 themes에서 score 3으로 격상 확인
        esg = next((p for p in profile.top_priorities if "ESG" in p["name"]), None)
        assert esg is not None
        assert esg["score"] == 3
        assert esg["source"] == "both"

    def test_preferred_format_union(self) -> None:
        """빈출 포맷(2건+) + 설문 포맷 합집합"""
        summaries = [
            _make_summary("001", formats=["표", "비교분석"]),
            _make_summary("002", formats=["표", "리스트"]),
        ]
        profile = build_profile(summaries, SAMPLE_SURVEY)
        assert "리스트" in profile.preferred_format["detail_preferences"]
        assert "표" in profile.preferred_format["detail_preferences"]
        # 1건만 등장한 "비교분석"은 미포함
        assert "비교분석" not in profile.preferred_format["detail_preferences"]

    def test_avoid_union(self) -> None:
        """avoid 합집합"""
        summaries = [_make_summary("001", avoid=["no_source"])]
        profile = build_profile(summaries, SAMPLE_SURVEY)
        assert "too_basic" in profile.avoid
        assert "no_source" in profile.avoid

    def test_schedule(self) -> None:
        profile = build_profile([], SAMPLE_SURVEY)
        assert profile.schedule["timezone"] == "Asia/Seoul"
        assert profile.schedule["weekends"] is True

    def test_to_dict_has_generated_at(self) -> None:
        profile = build_profile([], SAMPLE_SURVEY)
        d = profile.to_dict()
        assert "generated_at" in d["metadata"]

    def test_triggers_from_survey(self) -> None:
        profile = build_profile([], SAMPLE_SURVEY)
        assert profile.must_include_triggers == ["large_award", "refinance"]

    def test_sk_ecoplant_lens(self) -> None:
        profile = build_profile([], SAMPLE_SURVEY)
        assert "order_mix" in profile.sk_ecoplant_lens
        assert "cashflow" in profile.sk_ecoplant_lens

    def test_metadata(self) -> None:
        summaries = self._summaries_with_export_data()
        profile = build_profile(summaries, SAMPLE_SURVEY)
        assert profile.metadata["business_relevant_count"] == 3
        assert profile.metadata["export_conversation_count"] == 65

    def test_cross_section_freq_merged(self) -> None:
        """industry_freq와 theme_freq에 같은 key가 걸치면 합산 반영"""
        summaries = [
            _make_summary("001", km_industries={"건설수주": 3}, km_themes=[]),
            _make_summary("002", km_industries={}, km_themes=["수주"]),
        ]
        survey = {**SAMPLE_SURVEY}
        profile = build_profile(summaries, survey)
        epc = next((p for p in profile.top_priorities if "EPC" in p["name"]), None)
        assert epc is not None
        assert epc["export_mentions"] == 2  # industry 1 + theme 1
        assert epc["source"] == "both"

    def test_single_conv_high_keyword_not_strong(self) -> None:
        """1개 대화에서 키워드 여러번 나와도 1건 — threshold=2 미달"""
        summaries = [
            _make_summary("001", km_industries={"스마트시티": 5}),
        ]
        survey = {
            **SAMPLE_SURVEY,
            "industries": {"urban_smartcity": 3},
        }
        profile = build_profile(summaries, survey)
        sc = next((p for p in profile.top_priorities if "스마트시티" in p["name"]), None)
        assert sc is not None
        assert sc["source"] == "survey"  # 1건이므로 survey only
        assert sc["export_mentions"] == 1

    def test_open_questions_for_export_only_strong(self) -> None:
        """export에만 빈출하고 설문 미선택 → open_questions"""
        summaries = [
            _make_summary("001", km_entities=["AWS", "Meta"]),
            _make_summary("002", km_entities=["AWS"]),
        ]
        survey_no_hyperscalers = {
            **SAMPLE_SURVEY,
            "companies": {"sk_ecoplant": 3, "sk_group": 3},
        }
        profile = build_profile(summaries, survey_no_hyperscalers)
        oq = [q for q in profile.open_questions if "하이퍼스케일러" in q]
        assert len(oq) >= 1
