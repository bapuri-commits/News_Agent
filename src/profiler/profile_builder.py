"""Profile Builder — micro-summary 집계 + 설문 병합 → StableProfile 생성."""

from __future__ import annotations

from collections import Counter
from typing import Any

from src.models.summary import StableProfile


# ---------------------------------------------------------------------------
# 설문 industry key → 한글 표시명 매핑
# ---------------------------------------------------------------------------
INDUSTRY_LABELS: dict[str, str] = {
    "fab_capex": "반도체 Fab/CapEx",
    "cleanroom": "클린룸/공정 인프라",
    "equipment_supply": "장비/소재 공급",
    "packaging": "첨단패키징(HBM/CoWoS)",
    "memory_foundry": "메모리/파운드리",
    "dc_build": "데이터센터 신축",
    "dc_power": "DC 전력",
    "dc_cooling": "DC 냉각",
    "dc_cloud": "DC 클라우드",
    "power_grid": "전력 그리드",
    "renewable": "신재생 에너지",
    "nuclear": "원자력",
    "carbon_esg": "ESG/탄소규제",
    "petrochemical": "석유화학",
    "battery_ev": "배터리/EV",
    "bio_pharma": "바이오/제약",
    "defense": "방산",
    "transport_logistics": "물류/운송",
    "urban_smartcity": "도시개발/스마트시티",
}

THEME_LABELS: dict[str, str] = {
    "epc_award": "EPC/수주",
    "schedule_cost": "공기/원가/변경관리",
    "permit": "인허가",
    "material_labor": "자재/노무",
    "safety": "안전",
    "milestone": "마일스톤",
    "capex_guidance": "CapEx 가이던스",
    "pf_finance": "프로젝트 파이낸싱",
    "contingent": "우발채무",
    "ipo": "IPO",
    "ma_restructure": "M&A/사업재편",
    "credit_bond": "신용/채권",
    "policy_subsidy": "정책/보조금",
    "geopolitics": "지정학",
    "macro": "거시경제",
    "trade_supply": "무역/공급망",
    "esg_regulation": "ESG/규제",
    "ai_trend": "AI 트렌드",
    "construction_tech": "건설기술(모듈러/DfMA)",
    "talent_hr": "인력/인사",
}

COMPANY_LABELS: dict[str, str] = {
    "sk_ecoplant": "SK에코플랜트",
    "sk_group": "SK그룹/하이닉스",
    "kr_construction": "국내 건설사",
    "semi_makers": "반도체 메이커",
    "hyperscalers": "하이퍼스케일러",
    "semi_equip": "반도체 장비",
    "infra_equip": "인프라장비(Schneider/Vertiv)",
}


# ---------------------------------------------------------------------------
# Export 집계에 사용할 키워드 → 설문 industry key 매핑
# ---------------------------------------------------------------------------
EXPORT_INDUSTRY_MAP: dict[str, str] = {
    "반도체": "fab_capex",
    "패키징": "packaging",
    "데이터센터": "dc_build",
    "DC전력": "dc_power",
    "DC냉각": "dc_cooling",
    "스마트시티": "urban_smartcity",
    "건설수주": "epc_award",
    "투자정책": "capex_guidance",
}

EXPORT_THEME_MAP: dict[str, str] = {
    "CapEx": "capex_guidance",
    "수주": "epc_award",
    "EPC": "epc_award",
    "M&A": "ma_restructure",
    "지분매각": "ma_restructure",
    "사업구조 재편": "ma_restructure",
    "경영진 인사": "talent_hr",
    "조직 개편": "talent_hr",
    "인허가": "permit",
    "건설 기술": "construction_tech",
    "냉각 기술": "dc_cooling",
    "어닝콜": "capex_guidance",
    "PF": "pf_finance",
    "우발채무": "contingent",
    "디지털 트윈": "construction_tech",
    "ESG": "esg_regulation",
    "탄소규제": "esg_regulation",
    "착공": "milestone",
    "준공": "milestone",
    "지연": "schedule_cost",
    "공기": "schedule_cost",
    "마일스톤": "milestone",
    "모듈러": "construction_tech",
    "엔지니어링 인력": "talent_hr",
}

# 빈출 entity → 설문 company key 매핑 (대소문자 변형 포함)
_ENTITY_MAP_RAW: dict[str, str] = {
    "SK에코플랜트": "sk_ecoplant",
    "SK ecoplant": "sk_ecoplant",
    "SK하이닉스": "sk_group",
    "SK hynix": "sk_group",
    "SK그룹": "sk_group",
    "삼성전자": "semi_makers",
    "Samsung": "semi_makers",
    "Samsung Electronics": "semi_makers",
    "TSMC": "semi_makers",
    "Intel": "semi_makers",
    "Micron": "semi_makers",
    "현대건설": "kr_construction",
    "삼성물산": "kr_construction",
    "GS건설": "kr_construction",
    "DL이앤씨": "kr_construction",
    "대우건설": "kr_construction",
    "포스코건설": "kr_construction",
    "한화건설": "kr_construction",
    "ASML": "semi_equip",
    "Lam Research": "semi_equip",
    "TEL": "semi_equip",
    "Applied Materials": "semi_equip",
    "AMAT": "semi_equip",
    "Advantest": "semi_equip",
    "Teradyne": "semi_equip",
    "AWS": "hyperscalers",
    "Meta": "hyperscalers",
    "Nvidia": "hyperscalers",
    "NVIDIA": "hyperscalers",
    "Microsoft": "hyperscalers",
    "AMD": "semi_makers",
}
EXPORT_ENTITY_MAP: dict[str, str] = {}
for _k, _v in _ENTITY_MAP_RAW.items():
    EXPORT_ENTITY_MAP[_k] = _v
    EXPORT_ENTITY_MAP[_k.lower()] = _v


def _aggregate_export(summaries: list[dict]) -> dict[str, Any]:
    """28개 비즈니스 micro-summary에서 빈도 집계.

    Returns dict with keys:
        topics_freq, entities_freq, decision_lens_freq,
        industry_freq, theme_freq, entity_company_freq,
        format_set, avoid_set, high_confidence_evidence,
        conversation_count
    """
    topics: Counter[str] = Counter()
    entities: Counter[str] = Counter()
    decision_lens: Counter[str] = Counter()
    industry_freq: Counter[str] = Counter()
    theme_freq: Counter[str] = Counter()
    entity_company_freq: Counter[str] = Counter()
    format_freq: Counter[str] = Counter()
    format_set: set[str] = set()
    avoid_set: set[str] = set()
    high_conf_evidence: list[dict] = []

    for s in summaries:
        sig = s.get("signals", {})

        for t in sig.get("topics_top", []):
            topics[t] += 1
        for e in sig.get("entities_top", []):
            entities[e] += 1
        for d in sig.get("decision_lens", []):
            decision_lens[d] += 1
        for fmt in sig.get("preferred_format", []):
            format_set.add(fmt)
            format_freq[fmt] += 1
        for av in sig.get("avoid", []):
            avoid_set.add(av)

        km = s.get("keyword_matches", {})

        km_ind = km.get("industries", {})
        ind_seen_this_conv: set[str] = set()
        if isinstance(km_ind, dict):
            for ind_key, count in km_ind.items():
                if isinstance(count, (int, float)) and count > 0:
                    mapped = EXPORT_INDUSTRY_MAP.get(ind_key)
                    if mapped and mapped not in ind_seen_this_conv:
                        ind_seen_this_conv.add(mapped)
                        industry_freq[mapped] += 1

        theme_seen_this_conv: set[str] = set()
        for theme_val in km.get("themes", []):
            mapped = EXPORT_THEME_MAP.get(theme_val)
            if mapped and mapped not in theme_seen_this_conv:
                theme_seen_this_conv.add(mapped)
                theme_freq[mapped] += 1

        ent_seen_this_conv: set[str] = set()
        for ent_val in km.get("entities", []):
            mapped = EXPORT_ENTITY_MAP.get(ent_val)
            if not mapped:
                mapped = EXPORT_ENTITY_MAP.get(ent_val.lower())
            if mapped and mapped not in ent_seen_this_conv:
                ent_seen_this_conv.add(mapped)
                entity_company_freq[mapped] += 1

        conf = sig.get("confidence", 0)
        if conf >= 0.8:
            for ref in s.get("evidence_refs", []):
                high_conf_evidence.append({
                    "conversation_id": s.get("conversation_id", ""),
                    "title": s.get("title", ""),
                    "confidence": conf,
                    "quote": ref.get("quote", ""),
                })

    return {
        "topics_freq": topics,
        "entities_freq": entities,
        "decision_lens_freq": decision_lens,
        "industry_freq": industry_freq,
        "theme_freq": theme_freq,
        "entity_company_freq": entity_company_freq,
        "format_freq": format_freq,
        "format_set": format_set,
        "avoid_set": avoid_set,
        "high_confidence_evidence": high_conf_evidence,
        "conversation_count": len(summaries),
    }


def _is_export_strong(key: str, freq_counter: Counter, threshold: int = 2) -> bool:
    return freq_counter.get(key, 0) >= threshold


def _build_top_priorities(
    survey: dict,
    agg: dict[str, Any],
) -> tuple[list[dict], list[str]]:
    """병합 규칙에 따라 top_priorities와 open_questions를 생성."""
    priorities: list[dict] = []
    open_questions: list[str] = []

    industry_freq = agg["industry_freq"]
    theme_freq = agg["theme_freq"]
    entity_freq = agg["entity_company_freq"]

    all_freq: Counter[str] = Counter()
    all_freq.update(industry_freq)
    all_freq.update(theme_freq)
    all_freq.update(entity_freq)

    seen_keys: set[str] = set()

    def _add_priority(name: str, score: int, source: str, mentions: int, key: str) -> None:
        if key in seen_keys:
            return
        seen_keys.add(key)
        priorities.append({
            "name": name,
            "score": score,
            "source": source,
            "export_mentions": mentions,
        })

    for section_name, labels in [
        ("industries", INDUSTRY_LABELS),
        ("themes", THEME_LABELS),
        ("companies", COMPANY_LABELS),
    ]:
        section_data = survey.get(section_name, {})
        for key, survey_score in section_data.items():
            label = labels.get(key, key)
            export_count = all_freq.get(key, 0)
            strong = _is_export_strong(key, all_freq)

            if survey_score == 3 and strong:
                _add_priority(label, 3, "both", export_count, key)
            elif survey_score == 3 and not strong:
                _add_priority(label, 3, "survey", export_count, key)
                open_questions.append(
                    f"{label}: 설문 3점이나 export에서 {export_count}건만 - 실제 관심도 확인 필요"
                )
            elif survey_score == 2 and strong:
                _add_priority(label, 3, "both", export_count, key)
            elif survey_score == 2 and not strong:
                pass  # industries/themes에 score 2로 유지 (top_priorities 미포함)

    export_only_keys = set(all_freq.keys()) - seen_keys
    for key in export_only_keys:
        count = all_freq[key]
        if count >= 2:
            label = (
                INDUSTRY_LABELS.get(key)
                or THEME_LABELS.get(key)
                or COMPANY_LABELS.get(key)
                or key
            )
            in_survey = False
            for sec in ("industries", "themes", "companies"):
                if key in survey.get(sec, {}):
                    in_survey = True
                    break
            if not in_survey:
                open_questions.append(
                    f"{label}: export에서 {count}건 등장하나 설문 미선택 - 확인 필요"
                )

    priorities.sort(key=lambda p: (-p["score"], -p["export_mentions"]))
    return priorities, open_questions


def build_profile(summaries: list[dict], survey: dict) -> StableProfile:
    """micro-summary 집계 + 설문 병합 → StableProfile 생성."""
    agg = _aggregate_export(summaries)
    basic = survey.get("basic", {})

    priorities, open_questions = _build_top_priorities(survey, agg)

    # 포맷 선호: export에서 빈출 포맷(2건 이상) + 설문 포맷 합집합
    survey_format = basic.get("format", "리스트")
    SURVEY_FORMAT_MAP = {"list": "리스트"}
    survey_format_kr = SURVEY_FORMAT_MAP.get(survey_format, survey_format)
    format_freq = agg.get("format_freq", Counter())
    top_formats = {fmt for fmt, cnt in format_freq.items() if cnt >= 2}
    top_formats.add(survey_format_kr)
    detail_prefs = sorted(top_formats)

    # avoid 합집합
    survey_avoid = survey.get("avoid_style", [])
    combined_avoid = sorted(set(survey_avoid) | agg["avoid_set"])

    # 포맷 불일치 open_question: export 최빈 포맷이 설문 포맷과 다르면 기록
    if format_freq:
        most_common_fmt = format_freq.most_common(1)[0][0]
        if most_common_fmt != survey_format_kr:
            top3 = [f for f, _ in format_freq.most_common(3)]
            export_top_str = ", ".join(top3)
            open_questions.append(
                f"포맷 선호: 설문 '{survey_format_kr}' vs export '{export_top_str}' - 실사용 시 피드백으로 확정"
            )

    profile = StableProfile(
        user_intent=(
            "매일 아침 5~20분 내 반도체/DC/건설/투자 핵심 동향 파악. "
            "직접 요청 증거: 'Send me semiconductor business news at 8am every day'"
        ),
        top_priorities=priorities,
        must_include_triggers=survey.get("triggers", ["large_award", "refinance"]),
        avoid=combined_avoid,
        preferred_format={
            "reading_time": basic.get("reading_time", "20min"),
            "sections": ["Top5", "ByCategory", "Risks", "NextSignals", "SourceDiversity"],
            "style": "executive_brief",
            "detail_preferences": detail_prefs,
        },
        source_preferences={
            "paywalled_ok": basic.get("paywall", False),
            "language": basic.get("language", "summary_kr"),
        },
        schedule={
            "timezone": "Asia/Seoul",
            "daily_time": "05:00-06:00",
            "weekends": basic.get("weekend", True),
        },
        industries={k: v for k, v in survey.get("industries", {}).items()},
        themes={k: v for k, v in survey.get("themes", {}).items()},
        companies={k: v for k, v in survey.get("companies", {}).items()},
        regions=survey.get("regions", ["korea", "us", "asia"]),
        sk_ecoplant_lens=survey.get("sk_lens", []),
        conversation_hint_policy={"lookback_days": 7, "max_weight_percent": 10},
        risk_guardrails={
            "diversity_enforced": True,
            "require_links": True,
            "separate_fact_inference": True,
        },
        open_questions=open_questions,
        metadata={
            "export_conversation_count": 65,
            "business_relevant_count": agg["conversation_count"],
            "survey_date": "2026-02-18",
            "model_used": "claude-opus-4-6",
            "pipeline_version": "1.0",
        },
    )
    return profile
